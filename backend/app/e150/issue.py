"""
Traceable provincial forecasts, quarterly series and LGU uncertainty for E150. Run after scoring: 2021 joins the anchors. Not promoted to production.

    python -m app.e150.issue -> data/e150/out/issue/{province_trace.json, five_province_forecasts.csv, quarterly_series.csv, lgu_priority_*.csv, lgu_validation.json, sealed_forecast_*.json}
"""
from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm, spearmanr

from app.e145 import lgu as LGU
from app.e147 import features as Fe
from app.e147 import labels as Lb
from app.e148 import model as M8
from app.e150 import OUT
from app.e150 import model as M
from app.fi5.target import qindex, qlabel

warnings.filterwarnings("ignore")
Fe.LT = 0.0
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
ROUNDS = ["NNS2013", "FNRI2015", "ENNS2018", "ENNS2019", "ENNS2021"]
ISSUE = qindex("2026-Q4")
DIR = OUT / "issue"
RES = {"market": "province, monthly PSA CPI", "climate": "province quarterly; ONI national", "employment": "national (regional annual from 2021)", "remittance": "national", "poverty": "province, by PSA release round"}


def extended_base() -> pd.DataFrame:
    Fe.LT = 0.0
    b = Fe.base_rows()
    k = b.drop_duplicates("key").set_index("key")
    L = pd.read_csv(Lb.SEALED)
    e = L[L["fs_survey_category"] == "Food Insecure Households"].drop_duplicates("key")[["key", "pct"]]
    e = e[e["key"].isin(k.index)].copy()
    e["survey"], e["year"], e["ref_quarter"], e["p"], e["se_p"] = "ENNS2021", 2021, "2021-Q3", e["pct"], 3.0
    e["y"] = Fe._logit(e["p"])
    e["se_y"] = 0.03 / (e["p"] / 100 * (1 - e["p"] / 100))
    e["q_high"] = norm.cdf(e["y"] / e["se_y"])
    for c in ("province", "region", "sws_area", "island"):
        e[c] = e["key"].map(k[c])
    return pd.concat([b, e[b.columns]], ignore_index=True)


def expit100(x):
    return 100 / (1 + np.exp(-np.asarray(x, float)))


def _shap(lgb_model, X, cols):
    c = lgb_model.booster_.predict(X[cols], pred_contrib=True)[0][:-1]
    return {k: round(float(v), 4) for k, v in zip(cols, c) if abs(v) > 1e-9}


def series_task(i):
    S = M.Store(extended_base())
    if not M.released(i, ROUNDS):
        return None
    P = M.Pipeline(S, i, ROUNDS, "F")
    if P.tr.empty:
        return None
    b = S.base.drop_duplicates("key")
    b = b[b["province"].isin(CAL)]
    te = M.rows_for(S, b.assign(T=i + 1, survey="SERIES").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")
    if te.empty:
        return None
    o = M.predict_all(P, te, None, news=False)
    r = te[["province", "T", "i", "y_anchor", "h_signal"]].copy()
    for a in ("A-H", "A-Hh", "A-G"):
        r["pct_" + a] = expit100(o["mu_" + a])
    r["loading"], r["sigma_base"] = P.loading, P.sigma_base
    return r


def main():
    DIR.mkdir(exist_ok=True)
    S = M.Store(extended_base())
    P = M.Pipeline(S, ISSUE, ROUNDS, "F")
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)]
    rows, trace = [], {}
    rg = P.residual("G", M.RES)
    q90 = M.q90(P.tr["e"].values)
    for h in (1, 2, 3, 4):
        te = M.rows_for(S, five.assign(T=ISSUE + h, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [h], "F").reset_index(drop=True)
        o = M.predict_all(P, te, None, news=False)
        sig = P.sigma_base
        for k in range(len(te)):
            prov = te["province"].iloc[k]
            mu = float(o["mu_A-H"][k])
            pct = float(expit100(mu))
            lo, hi = float(expit100(mu - q90)), float(expit100(mu + q90))
            rows.append({"province": prov, "issue_date": "2026-10-01", "target_quarter": qlabel(ISSUE + h), "lead": h, "latest_measured_quarter": qlabel(int(te["rq_anchor"].iloc[k])), "latest_measured_pct": round(float(expit100(te["y_anchor"].iloc[k])), 1), "forecast_pct": round(pct, 1), "low90": round(lo, 1), "high90": round(hi, 1),
                         "p_high_ge50": round(float(norm.cdf(mu / sig)), 3), "class": "HIGH" if pct >= 50 else "LOW", "interval_includes_50": bool(lo < 50 < hi), "sensitivity_pct_A-Hh": round(float(expit100(o["mu_A-Hh"][k])), 1), "sensitivity_pct_A-G": round(float(expit100(o["mu_A-G"][k])), 1), "risk_score_B": round(100 * float(o["B-score"][k]), 1), "row_type": "forecast"})
            if h == 1:
                x = te.iloc[[k]]
                fold = next((m for regs, m in P.hier.folds if x["region"].iloc[0] in regs), P.hier.full)
                measured = S.base[S.base["province"] == prov][["survey", "p", "se_p"]].to_dict(orient="records")
                groups = {g: {c: (None if pd.isna(x[c].iloc[0]) else round(float(x[c].iloc[0]), 3)) for c in cols if c in x} for g, cols in M.GROUPS.items()}
                news = {c: (None if c not in x or pd.isna(x[c].iloc[0]) else round(float(x[c].iloc[0]), 3)) for c in M.NEWS if c.startswith("fv2")}
                trace[prov] = {
                    "1_officially_measured": measured,
                    "2_observed_government_indicators": groups, "group_resolution": RES,
                    "3_nlp_derived": news,
                    "4_model_forecast": {"target_quarter": qlabel(ISSUE + 1), "forecast_pct": round(pct, 1), "interval_90_pct": [round(lo, 1), round(hi, 1)], "parts_logit": {"shared_level": round(float(o["part_shared"][k]), 3), "province_structural_level": round(float(o["part_level"][k]), 3), "measured_deviation_after_shrinkage": round(float(o["part_adj"][k]), 3), "weight_on_own_surveys": round(float(o["part_weight"][k]), 3)},
                                         "explanation_structural_level_shap_logit": _shap(fold.m_, x, fold.cols), "quarterly_sensitivity_h_signal": None if pd.isna(x["h_signal"].iloc[0]) else round(float(x["h_signal"].iloc[0]), 3), "residual_sensitivity_shap_logit": _shap(rg.m_, x, rg.use_) if rg.m_ is not None else {}},
                    "5_calibrated_probability": {"p_high_ge50": round(float(norm.cdf(mu / sig)), 3), "class": "HIGH" if pct >= 50 else "LOW", "sigma_logit": round(sig, 3)},
                    "stale_or_missing": {"cpi_age_months_beyond_release": None if pd.isna(x["cpi_age_m"].iloc[0]) else int(x["cpi_age_m"].iloc[0]), "quarters_since_last_survey": int(x["gap_q"].iloc[0]), "missing_inputs": [c for c in M.RES if c in x and pd.isna(x[c].iloc[0])]},
                    "note": "Explanations describe the model, not causes. Reference quarter of surveys approximated as Q3; 2021 SE approximated at 3 points."}
    Lv = pd.DataFrame(rows)
    Lv.to_csv(DIR / "five_province_forecasts.csv", index=False, lineterminator="\n")
    (DIR / "province_trace.json").write_text(json.dumps(trace, indent=1, default=float), newline="\n")
    sf = DIR / f"sealed_forecast_{qlabel(ISSUE + 1)}.json"
    if not sf.exists():
        sf.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), "forecasts": rows}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(sf.read_bytes()).hexdigest())
    print(Lv[Lv["lead"] == 1].drop(columns=["issue_date", "row_type", "lead"]).to_string(index=False))
    # differentiation: pairs separated beyond forecast uncertainty of the province part
    q1 = Lv[Lv["lead"] == 1].set_index("province")
    te1 = M.rows_for(S, five.assign(T=ISSUE + 1, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")
    prov_part = P.hier.province(te1)
    te1 = te1.assign(mu=(prov_part["level"] + prov_part["adj"]).values, var=prov_part["var_prov"].values).set_index("province")
    pairs = {}
    for i_, a in enumerate(CAL):
        for b_ in CAL[i_ + 1:]:
            d = float(te1.at[a, "mu"] - te1.at[b_, "mu"])
            se = float(np.sqrt(te1.at[a, "var"] + te1.at[b_, "var"]))
            pairs[f"{a}-{b_}"] = {"diff_logit": round(d, 3), "se": round(se, 3), "separated_90": bool(abs(d) > 1.645 * se)}
    # LGU ranking and uncertainty
    lg = LGU.rank(dict(zip(q1.index, q1["p_high_ge50"])), qlabel(ISSUE + 1))
    rng = np.random.default_rng(150)
    mu_p = {p: float(np.log(q1.at[p, "forecast_pct"] / (100 - q1.at[p, "forecast_pct"]))) for p in CAL}
    sd = P.sigma_base
    D = 5000
    draws = {p: expit100(rng.normal(mu_p[p], sd, D)) / 100 for p in CAL}
    V = lg["vulnerability"].values
    M_ = np.column_stack([draws[p] * v for p, v in zip(lg["province_name"], V)])
    ranks = (-M_).argsort(axis=1).argsort(axis=1) + 1
    lg["rank_low90"], lg["rank_high90"] = np.percentile(ranks, 5, axis=0).astype(int), np.percentile(ranks, 95, axis=0).astype(int)
    lg["prob_top20"] = (ranks <= 20).mean(axis=0).round(3)
    lg.to_csv(DIR / f"lgu_priority_{qlabel(ISSUE + 1)}.csv", index=False, lineterminator="\n")
    w = {}
    base_s = lg["priority_score"].values
    for a, c in ((0.5, 0.5), (0.7, 0.3), (1.0, 0.0), (0.0, 1.0)):
        v2 = a * lg["pct_poverty"] + c * lg["pct_density"]
        w[f"{a}/{c}"] = {"spearman_with_0.6_0.4": float(spearmanr(lg["province_p_high"] * v2, base_s).statistic), "top20_overlap": len(set(lg.nlargest(20, "priority_score")["lgu_name"]) & set(lg.assign(s=lg["province_p_high"] * v2).nlargest(20, "s")["lgu_name"]))}
    rel = lg.assign(mm=lambda d: (d["vulnerability"] - d["vulnerability"].min()) / (d["vulnerability"].max() - d["vulnerability"].min()))
    agg = lg.groupby("province_name").apply(lambda g: float(np.average(g["poverty_incidence_2021"], weights=g["population_2024"])), include_groups=False)
    last = {p: S.base[S.base["province"] == p].sort_values("year")["p"].iloc[-1] for p in CAL}
    val = {"n_lgus": int(len(lg)), "within_province_score_range": lg.groupby("province_name")["priority_score"].agg(lambda s: round(float(s.max() - s.min()), 3)).to_dict(), "unique_scores": int(lg["priority_score"].round(6).nunique()), "weight_sensitivity": w,
           "mean_rank_interval_width": float((lg["rank_high90"] - lg["rank_low90"]).mean()), "lgus_with_prob_top20_above_0_9": int((lg["prob_top20"] > 0.9).sum()), "lgus_with_prob_top20_between_0_1_and_0_9": int(((lg["prob_top20"] >= 0.1) & (lg["prob_top20"] <= 0.9)).sum()), "province_check_poverty_vs_latest_measured": {"spearman": float(spearmanr([agg[p] for p in CAL], [last[p] for p in CAL]).statistic), "n": 5, "poverty_pop_weighted": agg.round(2).to_dict(), "latest_measured": {p: float(last[p]) for p in CAL}},
           "note": "No municipal food-insecurity measurement is held, so this ranking cannot be validated against a municipal outcome."}
    (DIR / "lgu_validation.json").write_text(json.dumps(val, indent=1, default=float), newline="\n")
    print(json.dumps({"pairs": pairs, "lgu": {k: val[k] for k in ("within_province_score_range", "unique_scores", "mean_rank_interval_width", "lgus_with_prob_top20_above_0_9", "lgus_with_prob_top20_between_0_1_and_0_9", "province_check_poverty_vs_latest_measured", "weight_sensitivity")}}, indent=0, default=float))
    print(lg.head(6)[["lgu_name", "province_name", "priority_score", "rank_low90", "rank_high90", "prob_top20"]].round(3).to_string())
    # quarterly series
    Sr = pd.concat([x for x in Parallel(n_jobs=10)(delayed(series_task)(i) for i in range(qindex("2017-Q1"), ISSUE + 1)) if x is not None], ignore_index=True)
    Sr["quarter"] = Sr["T"].map(lambda t: qlabel(int(t)))
    Sr.round(4).to_csv(DIR / "quarterly_series.csv", index=False, lineterminator="\n")
    mv = {}
    for a in ("A-H", "A-Hh", "A-G"):
        w_ = Sr.pivot_table(index="T", columns="province", values="pct_" + a)
        mv[a] = {"mean_abs_quarter_change_points": w_.diff().abs().mean().round(2).to_dict(), "mean_spread_points": float((w_.max(axis=1) - w_.min(axis=1)).mean()), "pair_corr_mean": float(w_.corr().values[np.triu_indices(5, 1)].mean())}
    (DIR / "quarterly_movement.json").write_text(json.dumps({"movement": mv, "loading_latest": float(Sr["loading"].iloc[-1]), "pairs": pairs}, indent=1, default=float), newline="\n")
    print(json.dumps(mv, indent=0))
    print(Sr[Sr["T"] >= ISSUE - 5].pivot_table(index="quarter", columns="province", values="pct_A-Hh").round(1).to_string())


if __name__ == "__main__":
    main()
