"""
v6 Stage 6: run the pre-registered v6 procedure (docs/aipheed/v6/PREREGISTRATION.md) on the DEVELOPMENT tiers. Scoring
helpers (metrics, moving-block superiority, N1-N7) are the v4 ones, so baselines and statistics stay identical. Every
number is DEVELOPMENT. Tier 3 (future quarters) is not touched here.

    python -I backend/scripts/v6_validate.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "backend" / "scripts"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v2 import models as V  # noqa: E402
from app.forecasting.v2 import select as S2  # noqa: E402
from app.forecasting.v2 import verdict as VD2  # noqa: E402
from app.forecasting.v4 import features as F  # noqa: E402
from app.forecasting.v4 import verdict as VD  # noqa: E402
from app.forecasting.v6 import select as S6  # noqa: E402
import v4_validate as V4V  # noqa: E402

V6 = REPO / "docs" / "aipheed" / "v6"
OUT = V6 / "results"
V4TIERS = REPO / "docs" / "aipheed" / "v4" / "tiers"
V4OUT = REPO / "docs" / "aipheed" / "v4" / "results" / "v4_devtest_predictions.csv"
LAST = date(2026, 10, 1)
SURGE, POST = T.qi("2024-Q1"), T.qi("2025-Q1")
BASELINES = ["PERSIST", "TREND-D", "CLIM", "RIDGE-ALL", "HFM-X", "SEAS-LLM", "V2", "V4"]


def procedure(rr, feats):
    wf2 = S2.walk_forward(rr, LAST)
    wf = S6.walk_forward(rr, feats, LAST, wf2)
    logs, picks, rows = [], [], []
    for I in S2.issues(LAST):
        chosen, log = S6.select(wf, rr, I)
        logs += log
        picks.append({"issue": I.isoformat(), "selected": chosen})
        g = wf[wf.issue == I.isoformat()]
        for k in S2.LEADS:
            for m in (*S6.CANDIDATES, "V6"):
                mm = chosen if m == "V6" else m
                half, _ = S2.conformal_halfwidth(wf, rr, I, mm, k)
                for r in g[(g.model == mm) & (g.lead == k)].itertuples():
                    lo, hi, _ = S2.interval(r.f, r.sd, half)
                    rows.append({"issue": r.issue, "area": r.area, "lead": k, "tqi": r.tqi, "model": m, "f": r.f,
                                 "lo80": lo, "hi80": hi, "n_obs": r.n_obs, "h": r.h, "y_latest": r.latest})
    return wf2, wf, pd.DataFrame(logs), pd.DataFrame(picks), pd.DataFrame(rows)


def dm_hln(SU, model="V6"):
    """Secondary: Diebold-Mariano on squared error (quarter-mean loss differentials, Newey-West with h-1 lags) with the
    Harvey-Leybourne-Newbold correction, t with T-1 df; one-sided p for the model having lower loss."""
    out = []
    for k in S2.LEADS:
        G = SU[SU.lead == k]
        h = int(G.h.median())
        for b in BASELINES:
            g = G[G[f"f_{b}"].notna()]
            d = ((g[f"f_{model}"] - g.y) ** 2 - (g[f"f_{b}"] - g.y) ** 2).groupby(g.tqi).mean().sort_index().to_numpy()
            T_ = len(d)
            u = d - d.mean()
            var = float(u @ u) / T_
            for j in range(1, min(h, T_)):
                var += 2 * (1 - j / h) * float(u[j:] @ u[:-j]) / T_
            rec = {"lead": k, "model": model, "baseline": b, "T": T_, "h": h, "mean_loss_diff": float(d.mean())}
            if np.allclose(d, 0) or var <= 0:
                rec.update({"hln_t": None, "p_one_sided": None, "note": "identical forecasts or non-positive variance"})
            else:
                c = np.sqrt((T_ + 1 - 2 * h + h * (h - 1) / T_) / T_)
                t = c * d.mean() / np.sqrt(var / T_)
                rec.update({"hln_t": float(t), "p_one_sided": float(stats.t.cdf(t, T_ - 1))})
            out.append(rec)
    return pd.DataFrame(out)


def by_period(SU, models):
    g = SU[SU.lead == 2].copy()
    g["period"] = np.where(g.tqi < SURGE, "pre-surge", np.where(g.tqi < POST, "surge 2024", "2025-26"))
    return pd.DataFrame([{"period": p, "model": m, "n": len(x), "within_frozen": float(V4V.hits(x, m).mean()),
                          "mae": float(np.abs(x[f"f_{m}"] - x.y).mean()), "bias": float((x[f"f_{m}"] - x.y).mean())}
                         for p, x in g.groupby("period") for m in models])


def overfit(rr, wf, picks, SU):
    out = []
    issues = set(SU[SU.lead == 2].issue)
    for m in (*S6.CANDIDATES, "V6"):
        tr, inn = [], []
        for p in picks.itertuples():
            if p.issue not in issues:
                continue
            mm = p.selected if m == "V6" else m
            g = S2.inner_rows(wf, rr, date.fromisoformat(p.issue), 2)
            inn.append(float(np.abs(g[g.model == mm].f - g[g.model == mm].y).mean()))
            if mm.startswith("LGBM"):
                x = wf[(wf.issue == p.issue) & (wf.lead == 2) & (wf.model == mm)]
                tr.append(float(x.train_mae.iloc[0]))
        o = SU[SU.lead == 2]
        out.append({"model": m, "train_mae_change_lgbm_only": float(np.nanmean(tr)) if tr else None,
                    "inner_lead2_mae": float(np.mean(inn)), "outer_lead2_mae": float(np.abs(o[f"f_{m}"] - o.y).mean())})
    return pd.DataFrame(out)


def window_sensitivity(rr, feats, SU):
    """Estimation restricted to rounds of 2022-Q1 onward; scored on the same 40 Lead-2 rows."""
    rr22 = rr[rr.quarter >= "2022-Q1"].copy()
    _, _, _, picks, fc = procedure(rr22, feats)
    g2 = SU[SU.lead == 2][["issue", "area", "y", "tol"]]
    x = fc[fc.lead == 2].merge(g2, on=["issue", "area"])
    r = x.groupby("model").apply(lambda g: pd.Series({"n": len(g), "within_frozen": float((np.abs(g.f - g.y) <= g.tol).mean()),
                                                      "mae": float(np.abs(g.f - g.y).mean())}), include_groups=False)
    return r.reset_index(), picks.selected.value_counts().to_dict()


def loao(rr, feats, wf2, SU):
    g2 = SU[SU.lead == 2]
    rows, cache = [], {}
    for I in sorted(g2.issue.unique()):
        for a in sorted(g2.area.unique()):
            d = S6.lgbm_at(rr, feats, wf2, date.fromisoformat(I), cache, exclude_area=a)
            d = d[(d.lead == 2) & (d.area == a)].set_index("model")
            r = g2[(g2.issue == I) & (g2.area == a)].iloc[0]
            rows.append({"issue": I, "area": a, "y": r.y, "tol": r.tol, "LGBM-D_loao": d.loc["LGBM-D", "f"],
                         "LGBM-D-S_loao": d.loc["LGBM-D-S", "f"], "LGBM-D_pooled": r["f_LGBM-D"],
                         "LGBM-D-S_pooled": r["f_LGBM-D-S"], "PERSIST": r.f_PERSIST})
    d = pd.DataFrame(rows)
    cols = ["LGBM-D_loao", "LGBM-D-S_loao", "LGBM-D_pooled", "LGBM-D-S_pooled", "PERSIST"]
    res = {c: float((np.abs(d[c] - d.y) <= d.tol).mean()) for c in cols}
    res["by_area"] = {a: {c: float((np.abs(g[c] - g.y) <= g.tol).mean()) for c in cols} for a, g in d.groupby("area")}
    return d, res


def leakage(rr, feats, SU):
    rng = np.random.default_rng(S2.SEED)
    sh = rr.copy()
    for a in sh.area.unique():
        ix = sh.index[sh.area == a]
        sh.loc[ix, ["value", "se"]] = sh.loc[rng.permutation(ix), ["value", "se"]].to_numpy()
    _, _, _, picks, fc = procedure(sh, feats)
    full = T.quarter_table(sh)[["area", "qi", "y", "tol"]].rename(columns={"qi": "tqi"})
    g = fc[(fc.lead == 2) & (fc.n_obs >= 8)].merge(full, on=["area", "tqi"])
    shuffle = {m: float((np.abs(x.f - x.y) <= x.tol).mean()) for m, x in g.groupby("model")}
    real = T.quarter_table(rr).set_index(["area", "qi"])
    fut = []
    for r in SU[SU.lead == 2].itertuples():
        known = T.known_at(rr, real.loc[(r.area, r.tqi), "published"] + timedelta(days=1))
        fut.append(abs(V.forecast(known, V.fit("PERSIST", known), r.tqi)[r.area]["f"] - r.y) <= r.tol)
    return {"shuffle_target_lead2_within": shuffle, "shuffle_selected": picks.selected.value_counts().to_dict(),
            "future_shift_persist_lead2_within": float(np.mean(fut))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rr, feats = T.load_rounds(), F.table()
    wf2, wf, logs, picks, fc = procedure(rr, feats)
    W = V4V.outer(rr, fc)
    v4 = pd.read_csv(V4OUT)[["area", "issue", "lead", "f_V4"]]
    W = W.merge(v4, on=["area", "issue", "lead"], how="left")
    SU = W[W.n_obs >= 8].reset_index(drop=True)
    # the outer rows must be exactly the hashed v4 DEVELOPMENT-TEST tier
    tier = pd.read_csv(V4TIERS / "DEVTEST_rows.csv")
    k = ["issue", "area", "lead", "target"]
    assert SU[k].sort_values(k).reset_index(drop=True).equals(tier.sort_values(k).reset_index(drop=True)), "tier mismatch"
    assert SU.f_V4.notna().all()
    wf.drop(columns=["contributions"]).to_csv(OUT / "v6_walk_forward.csv", index=False)
    logs.to_csv(OUT / "v6_selection_log.csv", index=False)
    picks.to_csv(OUT / "v6_selected_by_issue.csv", index=False)
    SU.to_csv(OUT / "v6_devtest_predictions.csv", index=False)
    fits = wf[wf.model == "LGBM-D-S"].groupby(["issue", "lead"]).agg(best_iter=("best_iter", "first"), w=("w", "first"),
                                                                    n_train=("n_train", "first"), exog=("exog", "first")).reset_index()
    fits.to_csv(OUT / "v6_lgbm_fits.csv", index=False)
    models = ["V6", *S6.CANDIDATES, *V4V.CONTEXT, "V2", "V4"]
    met = V4V.metrics(SU, models)
    met.to_csv(OUT / "v6_metrics.csv", index=False)
    rel = V4V.reliability(SU, ["V6", *S6.CANDIDATES])
    rel.to_csv(OUT / "v6_reliability.csv", index=False)
    V4V.BASELINES = BASELINES
    bt = V4V.beats(SU, "V6")
    bt_lgbm = {m: V4V.beats(SU, m) for m in ("LGBM-D", "LGBM-D-S")}
    dm = pd.concat([dm_hln(SU, m) for m in ("V6", "LGBM-D", "LGBM-D-S")], ignore_index=True)
    dm.to_csv(OUT / "v6_dm_hln.csv", index=False)
    ov = overfit(rr, wf, picks, SU)
    ov.to_csv(OUT / "v6_overfitting.csv", index=False)
    per = by_period(SU, ["V6", *S6.CANDIDATES, "HFM-X", "SEAS-LLM"])
    per.to_csv(OUT / "v6_by_period.csv", index=False)
    sens, sens_sel = window_sensitivity(rr, feats, SU)
    sens.to_csv(OUT / "v6_window_sensitivity.csv", index=False)
    lo_d, lo = loao(rr, feats, wf2, SU)
    lo_d.to_csv(OUT / "v6_loao_lead2.csv", index=False)
    g2 = SU[SU.lead == 2]
    served, served_log = S6.select(wf, rr, LAST)
    dev = {int(x): rel[(rel.model == "V6") & (rel.lead == x)].label.iloc[0] for x in S2.LEADS}
    entered = fits[fits.exog != "[]"]
    verdict = {
        "status": "DEVELOPMENT ONLY: every row was seen before v6; sealed tier (future quarters) has 0 scorable rows",
        "preregistration_sha256_lf": V4V.sha(V6 / "PREREGISTRATION.md", lf=True), "data_sha256": V4V.sha(T.SWS_ROUNDS),
        "features_sha256": V4V.sha(F.SNAPSHOTS), "selected_by_issue_counts": picks.selected.value_counts().to_dict(),
        "served_model": served, "served_selection_log": served_log,
        "lgbm_fits": {"total": int(len(fits)), "with_exogenous_feature": int(len(entered)),
                      "no_model_fallback": int((fits.best_iter == 0).sum()), "w_counts": fits.w.value_counts().to_dict()},
        "claim_75_frozen_development": VD.claim_75(V4V.hits(g2, "V6"), g2.tqi.to_numpy(), sealed=False),
        "claim_75_proposed_development": VD.claim_75(V4V.hits(g2, "V6", "tol_amended"), g2.tqi.to_numpy(), sealed=False),
        "claim_75_lgbm_d_frozen_development": VD.claim_75(V4V.hits(g2, "LGBM-D"), g2.tqi.to_numpy(), sealed=False),
        "claim_75_lgbm_d_s_frozen_development": VD.claim_75(V4V.hits(g2, "LGBM-D-S"), g2.tqi.to_numpy(), sealed=False),
        "beats_all_development": bt, "beats_all_development_lgbm": bt_lgbm,
        "claim_75_sealed": {"frozen": VD.claim_75(np.array([]), np.array([]), sealed=True),
                            "proposed": VD.claim_75(np.array([]), np.array([]), sealed=True)},
        "beats_all_sealed": VD.beats_all({}, testable=False),
        "development_label_by_lead": dev,
        "served_reliability_status_by_lead": {x: VD2.served_status(v, "NOT_YET_TESTABLE") for x, v in dev.items()},
        "window_2022_selected": sens_sel, "loao_lead2": lo, "leakage_controls": leakage(rr, feats, SU),
    }
    (OUT / "v6_verdict.json").write_text(json.dumps(verdict, indent=1, default=float) + "\n", encoding="utf-8", newline="\n")
    pd.set_option("display.width", 250)
    print(picks.selected.value_counts().to_string())
    print(logs.dropna(subset=["ci_lo"]).round(3).to_string())
    c = ["lead", "model", "n", "within_frozen", "block_ci_lo_frozen", "block_ci_hi_frozen", "within_amended_proposed", "mae", "rmse",
         "bias", "high_tercile_bias", "sharp_within", "sharp_increases", "var_ratio", "corr", "coverage80"]
    print(met[c].round(3).to_string())
    print(rel[["lead", "model", "N1_data", "N2_within_tolerance_75", "N3_beats_every_baseline_mae_rmse",
               "N4_squared_error_vs_persistence_and_climatology", "N5_stability", "N6_no_province_below_persistence",
               "N7_interval_coverage_80", "label"]].to_string())
    print(ov.round(3).to_string())
    print(per.round(3).to_string())
    print(sens.round(3).to_string())
    print(dm[dm.lead == 2].round(3).to_string())
    print(json.dumps(verdict, indent=1, default=float))


if __name__ == "__main__":
    main()
