"""Class-specific metrics: HIGH and LOW evaluated separately (written independently of app.fi9.evaluate).

    python -m app.fi9z.classmetrics       # audits every saved FI9-X / FI9-R prediction -> data/fi9z/out/class_audit.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from app.fi9z import OUT
from app.paths import BACKEND_DIR


def class_metrics(y, cls, p=None) -> dict:
    y, c = np.asarray(y, int), np.asarray(cls, int)
    tp, fp = int(((c == 1) & (y == 1)).sum()), int(((c == 1) & (y == 0)).sum())
    fn, tn = int(((c == 0) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    div = lambda a, b: a / b if b else None
    hp, hr = div(tp, tp + fp), div(tp, tp + fn)
    lp, lr = div(tn, tn + fn), div(tn, tn + fp)
    f = lambda pr, rc: (2 * pr * rc / (pr + rc) if pr and rc else 0.0) if pr is not None and rc is not None else 0.0
    hf, lf = f(hp, hr), f(lp, lr)
    out = {"n": len(y), "n_high": int(y.sum()), "n_low": int(len(y) - y.sum()), "predicted_high": int(c.sum()),
           "tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": (tp + tn) / len(y),
           "high_precision": hp, "high_recall": hr, "high_f1": hf, "low_precision": lp, "low_recall": lr, "low_f1": lf,
           "macro_f1": (hf + lf) / 2, "balanced_accuracy": (hr + lr) / 2 if hr is not None and lr is not None else None,
           "false_high_rate": div(fp, fp + tn), "missed_high_rate": div(fn, fn + tp)}
    if p is not None:
        p = np.asarray(p, float)
        out["brier"] = float(np.mean((p - y) ** 2))
        out["roc_auc"] = float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(np.round(p, 9))) > 1 else None
        out["pr_auc"] = float(average_precision_score(y, p)) if len(set(y)) == 2 else None
        idx = np.minimum((p * 5).astype(int), 4)
        out["ece_5bin"] = float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean() for b in range(5) if (idx == b).any()))
        out["mean_p_when_high"] = float(p[y == 1].mean()) if y.sum() else None        # class-specific calibration
        out["mean_p_when_low"] = float(p[y == 0].mean()) if (y == 0).any() else None
    return out


def audit() -> pd.DataFrame:
    rows = []
    W = pd.read_csv(BACKEND_DIR / "data" / "fi9x" / "out" / "predictions.csv")
    for (o, c), g in W.groupby(["origin", "config"]):
        rows.append({"source": "FI9-X", "origin": o, "config": c, **class_metrics(g["y"], g["cls"], g["p"])})
    R = pd.read_csv(BACKEND_DIR / "data" / "fi9r" / "out" / "wf_predictions.csv")
    for c, g in R.groupby("tag"):
        rows.append({"source": "FI9-R", "origin": "OP1", "config": c, **class_metrics(g["y"], g["cls"], g["p"])})
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "class_audit.csv", index=False, lineterminator="\n")
    return d


if __name__ == "__main__":
    d = audit()
    k = d[(d["origin"] == "OP1") & (d["source"] == "FI9-X")].sort_values("macro_f1", ascending=False)
    cols = ["config", "n", "predicted_high", "high_precision", "high_recall", "low_precision", "low_recall", "macro_f1", "balanced_accuracy", "accuracy", "brier"]
    print(k[cols].head(15).round(3).to_string())
    print(d[(d["config"].isin(["Always LOW", "Always HIGH", "Naive persistence", "C0 damped persistence (production)"])) & (d["origin"] == "OP1")][cols].round(3).to_string())
