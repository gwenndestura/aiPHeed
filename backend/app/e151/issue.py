"""
Traceable provincial forecasts, intervals, SHAP group shares and LGU uncertainty for E151. Research output only: no route, no dashboard.

    python -m app.e151.issue -> data/e151/out/issue/{five_province_forecasts.csv, province_trace.json, shap_groups.json, pairs.json, lgu_priority_*.csv, lgu_validation.json, sealed_forecast_*.json}
"""
from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

from app.e145 import lgu as LGU
from app.e147 import features as Fe
from app.e150 import model as M
from app.e150.issue import expit100
from app.e151 import OUT
from app.e151 import prov as Pv
from app.fi5.target import qindex, qlabel

warnings.filterwarnings("ignore")
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
ROUNDS = Pv.ROUNDS
ISSUE = qindex("2026-Q4")
DIR = OUT / "issue"
SCOPE = {"market": "province, monthly PSA CPI", "climate": "province quarterly; ONI national", "employment": "national (regional annual from 2021)", "remittance": "national", "poverty": "province, by PSA release round", "news": "province, area and national streams, stated per feature"}


def group_of(c: str) -> str:
    for g, cols in M.GROUPS.items():
        if c in cols:
            return g
    if c == "h2":
        return "h2_quarterly_signal"
    if c in Pv.NEWS_ALL:
        return "news"
    return "state"


def main():
    DIR.mkdir(exist_ok=True)
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, ISSUE, ROUNDS, "F")
    tr = Pv.add_inputs(S, P.tr)
    m = Pv.Res2(Pv.GNT_COLS).fit(tr)
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)]
    rows, trace = [], {}
    for h in (1, 2, 3, 4):
        te = Pv.add_inputs(S, M.rows_for(S, five.assign(T=ISSUE + h, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [h], "F")).reset_index(drop=True)
        base_mu, parts = P.hier.predict(te, te["T"].values)
        mu = base_mu + m.predict(te)
        sd, half, meta = m.scale(te["gap_q"].values)
        for k in range(len(te)):
            prov = te["province"].iloc[k]
            pct, lo, hi = float(expit100(mu[k])), float(expit100(mu[k] - half[k])), float(expit100(mu[k] + half[k]))
            rows.append({"province": prov, "issue_date": "2026-10-01", "target_quarter": qlabel(ISSUE + h), "lead": h, "latest_measured_quarter": qlabel(int(te["rq_anchor"].iloc[k])), "latest_measured_pct": round(float(expit100(te["y_anchor"].iloc[k])), 1), "anchor_only_pct": round(float(expit100(base_mu[k])), 1), "score": round(pct, 1), "low90": round(lo, 1), "high90": round(hi, 1), "p_high_ge50": round(float(norm.cdf(mu[k] / sd[k])), 3), "class": "HIGH" if pct >= 50 else "LOW", "interval_includes_50": bool(lo < 50 < hi), "quarters_since_survey": int(te["gap_q"].iloc[k])})
            if h == 1:
                x = te.iloc[[k]]
                c = m.m_.booster_.predict(x[m.use_], pred_contrib=True)[0][:-1]
                sh = {n: round(float(v), 4) for n, v in zip(m.use_, c) if abs(v) > 1e-9}
                gr = {}
                for n, v in sh.items():
                    gr[group_of(n)] = round(gr.get(group_of(n), 0.0) + v, 4)
                trace[prov] = {"measured": S.base[S.base["province"] == prov][["survey", "p", "se_p"]].to_dict(orient="records"),
                               "government_inputs": {g: {n: (None if pd.isna(x[n].iloc[0]) else round(float(x[n].iloc[0]), 3)) for n in cols if n in x} for g, cols in M.GROUPS.items()}, "input_scope": SCOPE,
                               "news_inputs": {n: (None if pd.isna(x[n].iloc[0]) else round(float(x[n].iloc[0]), 3)) for n in Pv.NEWS_ALL}, "h2": None if pd.isna(x["h2"].iloc[0]) else round(float(x["h2"].iloc[0]), 3),
                               "forecast": {"score": round(pct, 1), "interval_90": [round(lo, 1), round(hi, 1)], "anchor_logit": round(float(base_mu[k]), 3), "lightgbm_adjustment_logit": round(float(mu[k] - base_mu[k]), 3), "adjustment_shap_by_group": gr, "adjustment_shap": sh},
                               "note": "Explanations describe the model, not causes. Survey reference quarter approximated as Q3; 2021 SE approximated at 3 points."}
    Lv = pd.DataFrame(rows)
    Lv.to_csv(DIR / "five_province_forecasts.csv", index=False, lineterminator="\n")
    (DIR / "province_trace.json").write_text(json.dumps(trace, indent=1, default=float), newline="\n")
    sf = DIR / f"sealed_forecast_{qlabel(ISSUE + 1)}.json"
    if not sf.exists():
        sf.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), "forecasts": rows}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(sf.read_bytes()).hexdigest())
    print(Lv[Lv["lead"] == 1].drop(columns=["issue_date", "lead"]).to_string(index=False))
    # SHAP over training rows, by group
    C = np.abs(m.m_.booster_.predict(tr[m.use_], pred_contrib=True)[:, :-1]).mean(axis=0)
    gs = {}
    for n, v in zip(m.use_, C):
        gs[group_of(n)] = gs.get(group_of(n), 0.0) + float(v)
    tot = sum(gs.values()) or 1.0
    (DIR / "shap_groups.json").write_text(json.dumps({"share_of_mean_abs_shap": {k: round(v / tot, 4) for k, v in sorted(gs.items(), key=lambda t: -t[1])}, "n_trees": m.n_, "scale": meta, "train_rows": int(len(tr))}, indent=1, default=float), newline="\n")
    # province pairs: separated beyond the uncertainty of the province part
    te1 = M.rows_for(S, five.assign(T=ISSUE + 1, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"]), [1], "F")
    pp = P.hier.province(te1)
    te1 = te1.assign(mu=(pp["level"] + pp["adj"]).values, var=pp["var_prov"].values).set_index("province")
    pairs = {}
    for j, a in enumerate(CAL):
        for c_ in CAL[j + 1:]:
            d = float(te1.at[a, "mu"] - te1.at[c_, "mu"])
            se = float(np.sqrt(te1.at[a, "var"] + te1.at[c_, "var"]))
            pairs[f"{a}-{c_}"] = {"diff_logit": round(d, 3), "se": round(se, 3), "separated_90": bool(abs(d) > 1.645 * se)}
    (DIR / "pairs.json").write_text(json.dumps(pairs, indent=1), newline="\n")
    print(json.dumps(pairs), json.loads((DIR / "shap_groups.json").read_text()))
    # LGU ranking, research only
    q1 = Lv[Lv["lead"] == 1].set_index("province")
    lg = LGU.rank(dict(zip(q1.index, q1["p_high_ge50"])), qlabel(ISSUE + 1))
    rng = np.random.default_rng(151)
    half1 = {p: float(np.log(q1.at[p, "high90"] / (100 - q1.at[p, "high90"])) - np.log(q1.at[p, "score"] / (100 - q1.at[p, "score"]))) / 1.645 for p in CAL}
    draws = {p: expit100(rng.normal(np.log(q1.at[p, "score"] / (100 - q1.at[p, "score"])), half1[p], 5000)) / 100 for p in CAL}
    V = lg["vulnerability"].values
    X = np.column_stack([draws[p] * v for p, v in zip(lg["province_name"], V)])
    ranks = (-X).argsort(axis=1).argsort(axis=1) + 1
    lg["rank_low90"], lg["rank_high90"] = np.percentile(ranks, 5, axis=0).astype(int), np.percentile(ranks, 95, axis=0).astype(int)
    lg["prob_top20"] = (ranks <= 20).mean(axis=0).round(3)
    lg.to_csv(DIR / f"lgu_priority_{qlabel(ISSUE + 1)}.csv", index=False, lineterminator="\n")
    w = {}
    for a, c_ in ((0.5, 0.5), (0.7, 0.3), (1.0, 0.0), (0.0, 1.0)):
        v2 = a * lg["pct_poverty"] + c_ * lg["pct_density"]
        s2 = lg["province_p_high"] * v2
        w[f"{a}/{c_}"] = {"spearman_with_0.6_0.4": float(spearmanr(s2, lg["priority_score"]).statistic), "top20_overlap": len(set(lg.nlargest(20, "priority_score")["lgu_name"]) & set(lg.assign(s=s2).nlargest(20, "s")["lgu_name"]))}
    val = {"status": "research output only: the provincial model has not passed the release gates unless the results file says otherwise", "n_lgus": int(len(lg)), "unique_scores": int(lg["priority_score"].round(6).nunique()), "within_province_score_range": lg.groupby("province_name")["priority_score"].agg(lambda s: round(float(s.max() - s.min()), 3)).to_dict(), "weight_sensitivity": w, "mean_rank_interval_width": float((lg["rank_high90"] - lg["rank_low90"]).mean()), "lgus_with_prob_top20_above_0_9": int((lg["prob_top20"] > 0.9).sum()), "lgus_with_prob_top20_between_0_1_and_0_9": int(((lg["prob_top20"] >= 0.1) & (lg["prob_top20"] <= 0.9)).sum()), "note": "No municipal food-insecurity measurement is held, so this ranking cannot be validated against a municipal outcome. The 0.6/0.4 weights are not validated."}
    (DIR / "lgu_validation.json").write_text(json.dumps(val, indent=1, default=float), newline="\n")
    print(json.dumps(val, default=float))


if __name__ == "__main__":
    main()
