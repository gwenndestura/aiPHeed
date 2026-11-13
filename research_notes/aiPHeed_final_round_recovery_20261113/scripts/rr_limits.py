r"""Diagnostics of the 2021 limit (NOT used to select anything):
 (1) ORACLE threshold: for each model, the best cut-off chosen ON the 2021 outcomes themselves (forbidden in practice) -- if even this cannot
     meet all 8 targets in 2021, no threshold or recalibration can; the limit is the ranking (information), not calibration.
 (2) Separability: can ANY single model input (as of the 2021 Lead-1 origin) order the 4 HIGH provinces above the 5 LOW provinces that started
     at similar 2015 levels (persistence p >= .9)? Reported as AUC within that group of 9; descriptive only.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python rr_limits.py"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
R = pd.read_csv(EV / "RR_per_round.csv")
sys.path.insert(0, str(HERE / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("rr", HERE / "scripts" / "rr_eval.py")
# rebuild the 2021 Lead-1 table from rr_eval's inputs without re-running its prints
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
A = pd.read_csv(RN / "aiPHeed_final_etmix_20261113" / "evidence" / "ETMIX_rows_all_leads.csv")
D = LAB[(LAB.lead == 1) & (LAB.survey == "ENNS2021")][["key", "province", "y_high", "PERS"]].merge(A[(A.lead == 1) & (A.survey == "ENNS2021")][["key", "FINAL", "ETMIX"]], on="key")
et = pd.read_csv(RN / "aiPHeed_final_stability_lead_20261113" / "evidence" / "E_FINALET_province_rows.csv"); et = et[et.survey == "ENNS2021"][["province", "1"]].rename(columns={"1": "ET"})
D = D.merge(et, on="province")
def met(y, h, p):
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    r = tp / max(1, tp + fn); pr = tp / (tp + fp) if tp + fp else 0; sp = tn / max(1, tn + fp)
    return dict(recall=r, precision=pr, f1=2 * pr * r / (pr + r) if tp else 0, ba=(r + sp) / 2, acc=(tp + tn) / len(y), tp=tp, fp=fp)
out = []
y = D.y_high.values
for m in ("FINAL", "ET", "ETMIX", "PERS"):
    best = None
    for t in np.unique(np.round(D[m].values, 4)):
        r = met(y, D[m].values >= t, D[m].values)
        if best is None or (r["f1"], r["ba"]) > (best["f1"], best["ba"]): best = {**r, "cutoff": float(t)}
    passes = best["recall"] >= .7 and best["precision"] >= .7 and best["f1"] >= .7 and best["ba"] >= .7 and best["acc"] >= .75
    out.append({"model": m, "auc_2021": round(roc_auc_score(y, D[m]), 3), **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in best.items()}, "oracle_cutoff_passes_recall_prec_f1_ba_acc": passes})
O = pd.DataFrame(out); O.to_csv(EV / "RR_oracle_threshold_2021.csv", index=False, lineterminator="\n")
print(O.to_string(index=False))
# (2) separability among high-starting provinces
sys.path[:0] = [str(RN / "aiPHeed_objective_completion_20261111" / "scripts")]
import run_qs
from app.hcw import engine as H
_, te, _ = run_qs.load("ENNS2021", 1)
grp = D[(D.y_high == 1) | (D.PERS >= .9)][["key", "province", "y_high"]]
T = grp.merge(te, on="key")
cols = sorted({c for v in H.feature_sets().values() for c in v if c in T.columns})
sep = []
for c in cols:
    x = T[c]
    if x.notna().sum() == len(T) and x.nunique() > 1:
        a = roc_auc_score(T.y_high, x); sep.append({"input": c, "auc_HIGH_vs_highstart_LOW": round(max(a, 1 - a), 3), "direction": "+" if a >= .5 else "-"})
S = pd.DataFrame(sep).sort_values("auc_HIGH_vs_highstart_LOW", ascending=False)
S.to_csv(EV / "RR_separability_2021.csv", index=False, lineterminator="\n")
print(grp.to_string(index=False)); print("inputs evaluated", len(S), "| perfectly separating:", int((S.auc_HIGH_vs_highstart_LOW == 1).sum())); print(S.head(12).to_string(index=False))
