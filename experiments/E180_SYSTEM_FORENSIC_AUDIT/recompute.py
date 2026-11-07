"""E180: independent recomputation of headline metrics from saved forecasts with scikit-learn and the C1 formula written out here
(not app.e156.leads). Reads only. cd backend && PYTHONPATH=. python ../experiments/E180_SYSTEM_FORENSIC_AUDIT/recompute.py"""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix, average_precision_score
from app.paths import BACKEND_DIR
H = Path(__file__).resolve().parent
F = pd.read_csv(BACKEND_DIR / "data" / "e172" / "out" / "oof.csv")
rows = []
for a in ("E168", "SIMPLE", "E172", "E166", "PERS"):
    for L, g in F.groupby("lead"):
        y, p = (g["y_high"] == 1).values, g[a].values
        c = p >= 0.5
        tn, fp, fn, tp = confusion_matrix(y, c, labels=[False, True]).ravel()
        n = len(g); acc = (tp + tn) / n; major = max(y.mean(), 1 - y.mean())
        ne = n / (1 + (1.8 - 1) * 0.726); lo = acc - 1.96 * np.sqrt(acc * (1 - acc) / ne)
        rows.append({"model": a, "lead": int(L), "n": n, "HIGH": int(y.sum()), "LOW": int((~y).sum()), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
                     "accuracy": round(acc, 4), "majority_rate": round(major, 4), "n_eff": round(ne, 2), "c1_low_bound": round(lo, 4),
                     "C1_recomputed": bool(acc > major and lo > major), "precision": round(precision_score(y, c), 4), "recall": round(recall_score(y, c), 4),
                     "specificity": round(tn / (tn + fp), 4), "balanced_accuracy": round((recall_score(y, c) + tn / (tn + fp)) / 2, 4), "f1": round(f1_score(y, c), 4),
                     "roc_auc": round(roc_auc_score(y, p), 4), "pr_auc": round(average_precision_score(y, p), 4), "brier_vs_q_true": round(float(np.mean((p - g["q_true"]) ** 2)), 4),
                     "evidence_type": "historical held-out rows, previously inspected (E151-E179); post-hoc for SIMPLE/E172"})
R = pd.DataFrame(rows)
R.to_csv(H / "STATISTICAL_VALIDATION.csv", index=False, lineterminator="\n")
print(R[R["model"].isin(["E168", "SIMPLE"])][["model", "lead", "tp", "fp", "tn", "fn", "accuracy", "c1_low_bound", "C1_recomputed", "f1", "roc_auc", "brier_vs_q_true"]].to_string(index=False))
