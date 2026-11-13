r"""Why the long-gap fixes trade calibration against stability. Uses existing Lead 1 forecasts of FINAL, FINAL-SA (cap only, 0.50) and
FINAL-ET; no new fit. Per round: calibration in the large (mean p - HIGH rate), HIGH recall, false alarms, and the implied predictive
spread sd = mu / Phi^-1(p) (outcome-free). DESCRIPTIVE diagnosis of already-scored arms on reused rows; nothing is selected here.
Run: python -I diag_conflict.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
lab = LAB[LAB.lead == 1][["key", "survey", "y_high", "q_true", "y_anchor"]]
def load(pat):
    S = pd.concat([pd.read_csv(f) for f in glob.glob(pat)])
    if "variant" in S:
        S = S[S.variant.isin(["none", "ET"])]
    return S[S.lead == 1]
A = {"FINAL": load(str(RN / "aiPHeed_hcw_final_optimization_20261112/parts_fwd/FINAL__*__1__*.csv")),
     "FINAL-SA(cap)": load(str(RN / "aiPHeed_final_standalone_20261113/parts_sa/FINALSA__*__1__*.csv")),
     "FINAL-ET": load(str(RN / "aiPHeed_final_stability_lead_20261113/parts_et_L13/FINALET__*__1__*.csv"))}
rows = []
for arm, S in A.items():
    S = S.copy()
    z = norm.ppf(np.clip(S.p, 1e-6, 1 - 1e-6))
    S["sd"] = np.where(np.abs(z) > .2, S.mu / np.where(np.abs(z) > .2, z, 1), np.nan)
    M = S.groupby(["key", "survey"], as_index=False).agg(p=("p", "mean"), sd=("sd", "median"), mu=("mu", "mean")).merge(lab, on=["key", "survey"])
    for sv, g in M.groupby("survey"):
        h = g.p >= .5
        rows.append({"arm": arm, "round": sv, "mean_p": round(g.p.mean(), 3), "HIGH_rate": round(g.y_high.mean(), 3), "mean_p_minus_rate": round(g.p.mean() - g.y_high.mean(), 3),
                     "mean_p_minus_q": round(g.p.mean() - g.q_true.mean(), 3), "recall": f"{int((h & (g.y_high == 1)).sum())}/{int(g.y_high.sum())}",
                     "false_alarms": int((h & (g.y_high == 0)).sum()), "median_sd": round(float(g.sd.median()), 3),
                     "mean_pred_change_logit": round(float((g.mu - g.y_anchor).mean()), 3), "brier": round(float(((g.p - g.y_high) ** 2).mean()), 3)})
T = pd.DataFrame(rows)
T.to_csv(HERE / "evidence" / "C1_round_calibration_by_arm.csv", index=False)
pd.set_option("display.width", 220)
print(T.to_string(index=False))
