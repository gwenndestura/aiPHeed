"""
E140 step 1: why did E139's inner validation choose zero LightGBM trees? Descriptive diagnostics on E139's rows and
LORO folds (no model is selected here).

    python -m app.e140.diagnose  -> data/e140/out/diagnostics.json

D1 sample: independent units (regions, provinces, re-surveyed provinces).
D2 variance budget: total variance of y, survey-error variance, residual variance after the linear prior (LORO
   out-of-fold); explainable residual variance = residual variance - survey-error variance.
D3 residual structure: Spearman of the prior's OOF residual with every feature (Holm); weighted between-region and
   between-island share of residual variance.
D4 tree curves: LORO OOF expected Brier for fixed tree counts {0,10,30,100,300} with and without the prior, and with
   looser constraints (min_child_samples 5) and without survey weights - is there ANY tree count that helps?
"""
from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

from app.e137 import model as M137
from app.e138.when import holm
from app.e139 import model as M
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e140" / "out"
COUNTS = [0, 10, 30, 100, 300]


def _wvar(x, w):
    m = np.average(x, weights=w)
    return float(np.average((x - m) ** 2, weights=w))


def prior_oof(X):
    r = np.full(len(X), np.nan)
    for reg in X["region"].unique():
        te, tr = (X["region"] == reg).values, (X["region"] != reg).values
        m = M.Ridge_(M.BASE).fit(X[tr])
        r[te] = m.predict_y(X[te])
    return r


def curve(X, use_prior: bool, min_child=15, weighted=True, objective="regression"):
    out = {}
    for n in COUNTS:
        pred = np.full(len(X), np.nan)
        for reg in X["region"].unique():
            te, tr = (X["region"] == reg).values, (X["region"] != reg).values
            T = X[tr]
            base = M.Ridge_(M.BASE).fit(T) if use_prior else None
            b_tr = base.predict_y(T) if base else np.full(len(T), np.average(T["y"], weights=M._w(T)))
            b_te = base.predict_y(X[te]) if base else np.full(te.sum(), b_tr[0])
            if n:
                p = dict(M.LGB_PARAMS, min_child_samples=min_child, objective=objective)
                g = lgb.LGBMRegressor(n_estimators=n, **p)
                g.fit(T[M.ALL], T["y"], sample_weight=M._w(T) if weighted else None, init_score=b_tr)
                pred[te] = b_te + g.predict(X[te][M.ALL])
            else:
                pred[te] = b_te
        sig = float(np.sqrt(max(M137.SIGMA_FLOOR ** 2, np.mean((X["y"] - pred) ** 2 - X["se_y"] ** 2))))
        out[n] = {"expected_brier": M137.expected_brier(norm.cdf(pred / sig), X["q"]),
                  "rmse_y": float(np.sqrt(np.mean((X["y"] - pred) ** 2)))}
    return out


def run() -> dict:
    X = M.data()
    w = M._w(X)
    res = {"D1_sample": {"rows": int(len(X)), "decisive": int(X["status"].isin(["ELEVATED", "LOWER"]).sum()),
                         "regions": int(X["region"].nunique()), "provinces": int(X["key"].nunique()),
                         "resurveyed_provinces": int(X["prev_y"].notna().sum()),
                         "rows_per_feature": round(len(X) / len(M.ALL), 1)}}
    pr = prior_oof(X)
    r = X["y"].values - pr
    se2 = float(np.mean(X["se_y"] ** 2))
    res["D2_variance"] = {"var_y": _wvar(X["y"].values, w), "mean_survey_error_var": se2,
                          "var_residual_after_prior": _wvar(r, w),
                          "explainable_residual_var": _wvar(r, w) - se2,
                          "share_of_residual_that_is_survey_error": se2 / _wvar(r, w)}
    rows = []
    for f in M.ALL:
        s = pd.DataFrame({"r": r, "f": X[f].values}).dropna()
        t = spearmanr(s["r"], s["f"])
        rows.append({"feature": f, "n": len(s), "spearman": float(t.statistic), "p": float(t.pvalue)})
    for row, a in zip(rows, holm([x["p"] for x in rows])):
        row["p_holm"] = a
    res["D3_residual_vs_features"] = rows
    tot = _wvar(r, w)
    for g in ("region", "island", "survey"):
        means = pd.Series(r).groupby(X[g].values).transform("mean").values
        res.setdefault("D3_residual_between_group_share", {})[g] = _wvar(means, w) / tot
    res["D4_tree_curves"] = {
        "with_prior": curve(X, True), "without_prior": curve(X, False),
        "with_prior_min_child_5": curve(X, True, min_child=5), "with_prior_unweighted": curve(X, True, weighted=False),
        "with_prior_huber": curve(X, True, objective="huber")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagnostics.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: v for k, v in r.items() if k != "D3_residual_vs_features"}, indent=1))
    for x in r["D3_residual_vs_features"]:
        print(f"  {x['feature']:22s} rho {x['spearman']:+.3f} p {x['p']:.4f} holm {x['p_holm']:.3f}")
