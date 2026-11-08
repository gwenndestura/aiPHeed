"""
v6 EXPLORATORY controls (docs/aipheed/v6/DEVIATIONS.md #3-4). Written after the pre-registered shuffle control did not
behave as stated (LGBM-D 0.40 vs PERSIST 0.275 on the shuffled series) and leave-one-area-out beat the pooled fit. None of
this changes selection, the served model or any verdict.

  a  fallback census: why LightGBM predicted "no change" (too few rows vs no accepted split)
  b  shuffled series: is LGBM-D doing anything beyond the mean reversion that a shuffled (i.i.d.) series has by construction?
     Compare with the expanding area mean on the same shuffled rows.
  c  label permutation on the REAL series: training changes permuted (20 seeds), features and scoring rows untouched
  d  future-shifted features: each issue uses the NEXT quarter's snapshot. Does a deliberate leak of these indicators help?
  e  leave-one-area-out: share of held-out fits that fell back to no change, and the score on rows with an actual model

    python -I backend/scripts/v6_controls.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v2 import select as S2  # noqa: E402
from app.forecasting.v4 import features as F  # noqa: E402
from app.forecasting.v6 import lgbm as LG  # noqa: E402
from app.forecasting.v6 import select as S6  # noqa: E402

OUT = REPO / "docs" / "aipheed" / "v6" / "results"
LAST = date(2026, 10, 1)


def score(d: pd.DataFrame, g2: pd.DataFrame) -> dict:
    x = d[(d.lead == 2)].merge(g2[["issue", "area", "y", "tol"]], on=["issue", "area"])
    return {m: {"n": int(len(v)), "within": float((np.abs(v.f - v.y) <= v.tol).mean()), "mae": float(np.abs(v.f - v.y).mean())}
            for m, v in x.groupby("model")}


def lgbm_rows(rr, feats, wf2, issues) -> pd.DataFrame:
    cache: dict = {}
    return pd.concat([S6.lgbm_at(rr, feats, wf2, date.fromisoformat(i), cache) for i in issues], ignore_index=True)


def main():
    rr, feats = T.load_rounds(), F.table()
    su = pd.read_csv(OUT / "v6_devtest_predictions.csv")
    g2 = su[su.lead == 2]
    issues = sorted(g2.issue.unique())
    wf2 = S2.walk_forward(rr, LAST)
    res = {"status": "EXPLORATORY: written after seeing the pre-registered control outcome; changes no decision"}

    # a  fallback census
    fits = pd.read_csv(OUT / "v6_lgbm_fits.csv")
    fb = fits[fits.best_iter == 0]
    res["a_fallback"] = {"fits": int(len(fits)), "no_model": int(len(fb)), "no_model_under_30_rows": int((fb.n_train < 30).sum()),
                         "no_model_with_30_plus_rows": int((fb.n_train >= 30).sum()),
                         "lead2_devtest_issues_with_a_model": fits[(fits.lead == 2) & fits.issue.isin(issues) & (fits.best_iter > 0)].issue.tolist()}

    # b  shuffled series against the expanding mean (same permutation as v6_validate.leakage)
    rng = np.random.default_rng(S2.SEED)
    sh = rr.copy()
    for a in sh.area.unique():
        ix = sh.index[sh.area == a]
        sh.loc[ix, ["value", "se"]] = sh.loc[rng.permutation(ix), ["value", "se"]].to_numpy()
    wfs = S2.walk_forward(sh, LAST)
    fulls = T.quarter_table(sh)[["area", "qi", "y", "tol"]].rename(columns={"qi": "tqi"})
    ds = lgbm_rows(sh, feats, wfs, [i.isoformat() for i in S2.issues(LAST)])
    x = ds[(ds.lead == 2) & (ds.n_obs >= 8)].merge(fulls, on=["area", "tqi"])
    rec = {m: float((np.abs(v.f - v.y) <= v.tol).mean()) for m, v in x.groupby("model")}
    mean_f = [float(T.known_at(sh, date.fromisoformat(r.issue)).query("area == @r.area").y.mean())
              for r in x[x.model == "LGBM-D"].itertuples()]
    y = x[x.model == "LGBM-D"]
    rec["expanding_area_mean"] = float((np.abs(np.array(mean_f) - y.y) <= y.tol).mean())
    rec["persist"] = float((np.abs(y.anchor - y.y) <= y.tol).mean())
    res["b_shuffled_series_lead2_within"] = rec

    # c  label permutation on the real series
    real_fit = LG.fit
    out = []
    for seed in range(20):
        r = np.random.default_rng(1000 + seed)

        def permuted(train, _r=r):
            if train.empty:
                return real_fit(train)
            return real_fit(train.assign(change=_r.permutation(train.change.to_numpy())))
        LG.fit = permuted
        try:
            out.append(score(lgbm_rows(rr, feats, wf2, issues), g2)["LGBM-D"]["within"])
        finally:
            LG.fit = real_fit
    res["c_label_permutation_lead2_within"] = {"seeds": 20, "mean": float(np.mean(out)), "min": float(np.min(out)),
                                               "max": float(np.max(out)), "persist": float((np.abs(g2.f_PERSIST - g2.y) <= g2.tol).mean()),
                                               "lgbm_d_honest": float((np.abs(g2["f_LGBM-D"] - g2.y) <= g2.tol).mean())}

    # d  future-shifted features: the snapshot of the next issue is relabelled as this issue's
    order = sorted(feats.issue.unique())
    nxt = {order[i + 1]: order[i] for i in range(len(order) - 1)}
    shifted = feats[feats.issue.isin(nxt)].assign(issue=lambda t: t.issue.map(nxt))
    res["d_future_shifted_features_lead2"] = score(lgbm_rows(rr, shifted, wf2, issues), g2)

    # e  leave-one-area-out: how often the held-out fit has a model at all
    lo = pd.read_csv(OUT / "v6_loao_lead2.csv")
    same = np.isclose(lo["LGBM-D_loao"], lo["PERSIST"])
    has = lo[~same]
    res["e_loao"] = {"rows": int(len(lo)), "rows_identical_to_persistence": int(same.sum()),
                     "rows_with_a_model": int(len(has)),
                     "on_those_rows_within_loao": float((np.abs(has["LGBM-D_loao"] - has.y) <= has.tol).mean()) if len(has) else None,
                     "on_those_rows_within_persist": float((np.abs(has["PERSIST"] - has.y) <= has.tol).mean()) if len(has) else None,
                     "on_those_rows_mae_loao": float(np.abs(has["LGBM-D_loao"] - has.y).mean()) if len(has) else None,
                     "on_those_rows_mae_persist": float(np.abs(has["PERSIST"] - has.y).mean()) if len(has) else None}
    pooled = g2[~np.isclose(g2["f_LGBM-D"], g2.f_PERSIST)]
    res["e_pooled_rows_with_a_model"] = {"rows": int(len(pooled)), "within_lgbm_d": float((np.abs(pooled["f_LGBM-D"] - pooled.y) <= pooled.tol).mean()),
                                         "within_persist": float((np.abs(pooled.f_PERSIST - pooled.y) <= pooled.tol).mean()),
                                         "mae_lgbm_d": float(np.abs(pooled["f_LGBM-D"] - pooled.y).mean()),
                                         "mae_persist": float(np.abs(pooled.f_PERSIST - pooled.y).mean())}
    (OUT / "v6_exploratory_controls.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
