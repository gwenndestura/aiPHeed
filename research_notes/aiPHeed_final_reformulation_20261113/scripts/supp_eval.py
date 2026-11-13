r"""Supplementary evaluation designs (no model fitted or tuned; stored predictions only): continuous prevalence error, measurement-error-aware
(soft-label) Brier, confident-label metrics, for the ABSOLUTE target. FINAL, LG (PROTOCOL_OPT2), persistence. Run: python -I supp_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, spearmanr
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]; RNDS = ["ENNS2018", "ENNS2019", "ENNS2021"]
lg = lambda p: np.log(p / (1 - p)); ex = lambda z: 100 / (1 + np.exp(-z))
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["y_high", "PERS"]]; LAB = LAB[LAB.lead == 1]
GT = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "GT_evaluation_labels.csv")[["key", "survey", "p", "se_p"]].rename(columns={"p": "pct"})
D = LAB.merge(GT, on=["key", "survey"])
f = D.pct / 100; se_logit = (D.se_p / 100) / (f * (1 - f))
D["q_soft"] = norm.cdf(lg(f) / se_logit)                 # P(true prevalence >= 50 % | survey estimate, SE)
D["confident"] = (D.pct - 50).abs() > 1.96 * D.se_p
ST = pd.read_csv(HERE / "parts" / "REL_STAT_all.csv"); RP = ST[(ST.model == "REL_P") & (ST.variant == "main")][K + ["mu"]]
RP = RP.assign(mu=RP.mu + lg(.538))                      # every test anchor is FNRI2015: anchor logit = z_anchor + logit(national 2015)
FI = pd.concat([pd.read_csv(x, usecols=K + ["p", "mu"]) for x in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS20*__1__*.csv"))])
LG = pd.concat([pd.read_csv(x, usecols=K + ["p", "mu"]) for x in glob.glob(str(RN / "aiPHeed_final_model_optimization_20261113" / "parts" / "LG__*.csv"))])
M = {"FINAL": FI.groupby(K, as_index=False)[["p", "mu"]].mean(), "LG": LG.groupby(K, as_index=False)[["p", "mu"]].mean(),
     "PERS": D[K + ["PERS"]].rename(columns={"PERS": "p"}).merge(RP, on=K)}
rows = []
for nm, m in M.items():
    d = D.merge(m, on=K)
    for s, x in list(d.groupby("survey")) + [("POOLED", d)]:
        c = x[x.confident]; h = c.p >= .5
        tp, fp, fn, tn = int((h & (c.y_high == 1)).sum()), int((h & (c.y_high == 0)).sum()), int((~h & (c.y_high == 1)).sum()), int((~h & (c.y_high == 0)).sum())
        rows.append({"model": nm, "round": s, "n": len(x), "MAE_pp": round(float((ex(x.mu) - x.pct).abs().mean()), 2), "bias_pp": round(float((ex(x.mu) - x.pct).mean()), 2),
                     "spearman": round(float(spearmanr(x.mu, x.pct)[0]), 3), "brier_hard": round(float(((x.p - x.y_high) ** 2).mean()), 4),
                     "brier_soft": round(float(((x.p - x.q_soft) ** 2).mean()), 4), "n_borderline": int((~x.confident).sum()),
                     "confident_TP/FP/FN/TN": f"{tp}/{fp}/{fn}/{tn}", "confident_recall": round(tp / max(1, tp + fn), 3),
                     "confident_precision": round(tp / (tp + fp), 3) if tp + fp else None})
R = pd.DataFrame(rows); R.to_csv(EV / "SUPP_absolute_continuous_soft.csv", index=False, lineterminator="\n")
bl = D[~D.confident & (D.survey == "ENNS2021")][["key", "pct", "se_p", "y_high"]]
json.dump({"borderline_2021_rows": bl.to_dict(orient="records")}, open(EV / "SUPP_borderline_2021.json", "w"), indent=1)
pd.set_option("display.width", 250); print(R.to_string(index=False)); print(bl.to_string(index=False))
