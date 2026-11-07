"""E180 (E168 verification): recompute every E168 metric from data/e168/out/oof.csv (column L = E168 P(HIGH), mu_L = score) with
independent code, then compare with app.e156.leads.evaluate. Read-only.
    cd backend && PYTHONPATH=. python ../experiments/E180_E168_FULL_SYSTEM_VERIFICATION/recalculate.py"""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score, confusion_matrix, average_precision_score
from app.e156 import leads as LD
from app.paths import BACKEND_DIR
H = Path(__file__).resolve().parent
F = pd.read_csv(BACKEND_DIR / "data" / "e168" / "out" / "oof.csv")
ref = {r["lead"]: r for r in LD.evaluate(F, "L", "L")["leads"]}
rng = np.random.default_rng(180)
rows = []
for L, g in F.groupby("lead"):
    g = g.reset_index(drop=True)
    y, p = (g["y_high"] == 1).values, g["L"].values
    c = p >= 0.5
    tn, fp, fn, tp = confusion_matrix(y, c, labels=[False, True]).ravel()
    n = len(g); acc = (tp + tn) / n; maj = max(y.mean(), 1 - y.mean())
    ne = n / (1 + (1.8 - 1) * 0.726); lo = acc - 1.96 * np.sqrt(acc * (1 - acc) / ne)
    regs = list(g.groupby("region").indices.values())
    boot = [((c == y)[np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))])]).mean() for _ in range(2000)]
    R = ref[int(L)]
    rows.append({"lead": int(L), "rows": n, "HIGH": int(y.sum()), "LOW": int((~y).sum()), "tp": tp, "fp": fp, "tn": tn, "fn": fn, "correct": tp + tn,
                 "accuracy": round(acc, 4), "majority_rate": round(maj, 4), "n_eff": round(ne, 3), "c1_low_bound": round(lo, 4),
                 "C1_independent": bool(acc > maj and lo > maj), "accuracy_region_bootstrap_95": f"[{np.percentile(boot, 2.5):.3f}, {np.percentile(boot, 97.5):.3f}]",
                 "precision": round(tp / (tp + fp), 4), "recall_HIGH": round(tp / (tp + fn), 4), "specificity": round(tn / (tn + fp), 4),
                 "balanced_accuracy": round((tp / (tp + fn) + tn / (tn + fp)) / 2, 4), "f1": round(f1_score(y, c), 4), "roc_auc": round(roc_auc_score(y, p), 4),
                 "pr_auc": round(average_precision_score(y, p), 4), "brier": round(float(np.mean((p - g["q_true"]) ** 2)), 4),
                 "leads_py_C1..C6": "".join(str(int(v)) for v in R["criteria"].values()), "leads_py_reliable": R["reliable"],
                 "matches_leads_py": bool(abs(R["accuracy"] - acc) < 5e-4 and abs(R["accuracy_95_low_effective_n"] - lo) < 5e-4 and R["criteria"]["C1"] == (acc > maj and lo > maj)),
                 "meets_75pct_rule": acc >= 0.75})
pd.DataFrame(rows).to_csv(H / "STATISTICAL_RECALCULATION.csv", index=False, lineterminator="\n")
print(pd.DataFrame(rows)[["lead", "correct", "accuracy", "c1_low_bound", "C1_independent", "leads_py_C1..C6", "f1", "roc_auc", "brier", "accuracy_region_bootstrap_95", "matches_leads_py"]].to_string(index=False))
