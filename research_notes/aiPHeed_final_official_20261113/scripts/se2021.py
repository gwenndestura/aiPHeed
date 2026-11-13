r"""ENNS 2021 provincial SEs are not published (3.0 pp was assumed). Sensitivity: the 2018/2019 printed provincial SEs give an empirical
range; for each plausible SE, how many 2021 labels are within 1.96 SE of the 50 % line, expected wrong-side labels, and how FINAL's Lead-1
2021 accuracy changes if each label is weighted by P(label side correct). Run: python -I se2021.py"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
G = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "GT_evaluation_labels.csv")
R = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "REL_rows_L1to5.csv"); R = R[R.lead == 1]
emp = G[G.survey.isin(["ENNS2018", "ENNS2019"])].se_p
d = G[G.survey == "ENNS2021"].merge(R[["key", "survey", "FINAL", "y_high"]], on=["key", "survey"])
out = []
for se in [round(float(emp.min()), 2), round(float(emp.quantile(.25)), 2), round(float(emp.median()), 2), 3.0, round(float(emp.quantile(.75)), 2), round(float(emp.max()), 2), 5.0]:
    pc = norm.cdf(np.abs(d.p - 50) / se); hit = ((d.FINAL >= .5) == (d.y_high == 1))
    out.append({"assumed_se_pp": se, "labels_within_1.96se": int((np.abs(d.p - 50) < 1.96 * se).sum()), "expected_wrong_side_labels": round(float((1 - pc).sum()), 2),
                "HIGH_labels_within_1.96se": int(((np.abs(d.p - 50) < 1.96 * se) & (d.y_high == 1)).sum()),
                "FINAL_L1_2021_accuracy_label_weighted": round(float((hit * pc + (~hit) * (1 - pc)).mean()), 4)})
T = pd.DataFrame(out); T.to_csv(EV / "GT_se2021_sensitivity.csv", index=False, lineterminator="\n")
print("2018/2019 printed provincial SE (pp): min %.2f q25 %.2f median %.2f q75 %.2f max %.2f" % (emp.min(), emp.quantile(.25), emp.median(), emp.quantile(.75), emp.max()))
print(T.to_string(index=False)); print(d[d.y_high == 1][["key", "p", "FINAL"]].to_string(index=False))
