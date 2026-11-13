r"""HIGH-risk detection diagnostics for FINAL (no refit): every HIGH province-round at Leads 1-5, decomposed with the exact TreeSHAP
of the stored fits (../aiPHeed_final_etmix_20261113/parts, hyp g = FINAL, 5 seeds): forecast logit mu = anchor + sum(contributions) +
time term (bias x g). Adds survey-label margin (published SE), persistence, the training gap range, and by-round calibration-in-the-large.
Run: python -I false_negatives.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]
pct = lambda x: 100 / (1 + np.exp(-np.asarray(x, float)))
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
GT = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "GT_evaluation_labels.csv")
REL = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "REL_rows_L1to5.csv")
P = RN / "aiPHeed_final_etmix_20261113" / "parts"
grp = lambda c: (lambda b: "timing" if b in ("gap_q", "lead") else "regional_economy" if b in ("hh_grdp_g", "hh_grdp_rel", "income_growth", "income_rel")
                 else "poverty" if b in ("p_poverty", "p_poverty_gap", "p_subsistence", "p_density") else "market" if b.startswith(("cpi_", "l_fg", "l_rice", "l_terms"))
                 else "climate" if (b.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_", "vu_")) or b == "oni") else "employment" if b.startswith("unemp")
                 else "agri_fish" if b.startswith(("ag_", "agri_", "c_agri", "l_fish")) else "news")(c[3:] if c.startswith("mi_") else c)
SH = pd.concat([pd.read_parquet(f) for f in glob.glob(str(P / "SHAP__*.parquet"))]); SH = SH[(SH.hyp == "g") & (SH.lead <= 5)]
SH["group"] = np.where(SH.input == "bias", "time_trend", SH.input.map(lambda c: grp(c) if c != "bias" else ""))
C = SH.groupby(K + ["group"])["contrib"].sum().div(5).unstack(fill_value=0.0)          # 5-seed mean (0 where not selected)
AN = SH.groupby(K)["anchor"].mean()
FO = pd.concat([pd.read_parquet(f) for f in glob.glob(str(P / "FOLD__*.parquet"))]); FO = FO[(FO.hyp == "g") & (FO.kind == "base") & (FO.lead <= 5)]
MU = FO.groupby(K)["mu"].mean()
D = REL.drop(columns=["gap_q"]).merge(LAB[K + ["y_anchor", "gap_q"]], on=K).set_index(K)
D = D.join(C).join(AN.rename("anchor_used")).join(MU.rename("mu"))
D = D.reset_index().merge(GT[["key", "survey", "p", "se_p"]], on=["key", "survey"], how="left")
D["observed_pct"] = D.p.round(1); D["label_z"] = ((D.p - 50) / D.se_p).round(2)
D["anchor_pct_latest_survey"] = pct(D.y_anchor).round(1); D["forecast_pct"] = pct(D.mu).round(1)
D["predicted_change_pts"] = (D.forecast_pct - D.anchor_pct_latest_survey).round(1)
D["observed_change_pts"] = (D.observed_pct - D.anchor_pct_latest_survey).round(1)
D["detected"] = D.FINAL >= .5
cols = ["survey", "lead", "province", "observed_pct", "label_z", "anchor_pct_latest_survey", "forecast_pct", "predicted_change_pts", "observed_change_pts",
        "gap_q", "FINAL", "PERS", "detected", "time_trend", "market", "poverty", "regional_economy", "agri_fish", "climate", "employment", "news"]
H = D[D.y_high == 1][[c for c in cols if c in D]].sort_values(["lead", "survey", "province"]).round(3)
H.to_csv(EV / "FN_high_rows_L1to5.csv", index=False, lineterminator="\n")
# calibration-in-the-large by round and class; training gap coverage
by = D.groupby(["lead", "survey"]).apply(lambda g: pd.Series({"n": len(g), "high": int(g.y_high.sum()), "mean_p_HIGH_rows": g.FINAL[g.y_high == 1].mean(),
            "mean_p_LOW_rows": g.FINAL[g.y_high == 0].mean(), "mean_predicted_change_pts": g.predicted_change_pts.mean(), "mean_observed_change_pts": g.observed_change_pts.mean(),
            "mean_time_trend_logit": g.time_trend.mean(), "test_gap_q": g.gap_q.iloc[0]}), include_groups=False).round(3)
meta = {(d["survey"], d["lead"]): (d["train_gaps"], d["train_rounds"]) for d in (json.load(open(f)) for f in glob.glob(str(RN / "aiPHeed_final_stability_lead_20261113" / "features_lead" / "FINALL__*__168.json")))}
by["train_gaps"] = [str(meta[(s, int(l))][0]) for l, s in by.index]; by["train_rounds"] = ["+".join(sorted(meta[(s, int(l))][1])) for l, s in by.index]
by["test_gap_outside_training"] = [g > max(meta[(s, int(l))][0]) for (l, s), g in zip(by.index, by.test_gap_q)]
by.to_csv(EV / "FN_by_round_lead.csv", lineterminator="\n")
pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40)
print(H[H.lead == 1].to_string(index=False)); print(by.to_string())
