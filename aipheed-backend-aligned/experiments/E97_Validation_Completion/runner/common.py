"""E97 shared helpers: metrics, Wilson interval, quarter bootstrap, sign test. Run every E97 script from backend/."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
E97 = HERE.parent
EXP = E97.parent
BACKEND = EXP.parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
SEED, DRAWS = 97, 5000


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [float("nan")] * 2
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [c - h, c + h]


def auc(y, s):
    y, s = np.asarray(y, int), np.asarray(s, float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def metrics(y, score, thr: float = 0.5) -> dict:
    y, s = np.asarray(y, int), np.clip(np.asarray(score, float), 0, 1)
    yh = (s >= thr).astype(int)
    TP, TN = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    FP, FN = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    n = len(y)
    rec = TP / (TP + FN) if TP + FN else None
    recl = TN / (TN + FP) if TN + FP else None
    prec = TP / (TP + FP) if TP + FP else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else 0.0
    ps = np.clip(s, 1e-3, 1 - 1e-3)
    return {"n": n, "positives": int(y.sum()), "accuracy": (TP + TN) / n, "accuracy_wilson95": wilson(TP + TN, n),
            "balanced_accuracy": None if rec is None or recl is None else (rec + recl) / 2,
            "precision_HIGH": prec, "recall_HIGH": rec, "recall_LOW": recl, "f1_HIGH": f1, "auc_roc": auc(y, s),
            "brier": float(np.mean((s - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(ps) + (1 - y) * np.log(1 - ps))),
            "confusion": {"TP": TP, "FP": FP, "FN": FN, "TN": TN}}


def sign_test(d) -> float:
    d = np.asarray(d, float)
    d = d[np.abs(d) > 1e-12]
    n, k = len(d), int((d > 0).sum())
    if n == 0:
        return 1.0
    from scipy.stats import binomtest
    return float(binomtest(k, n, 0.5).pvalue)


def boot_ci(groups: np.ndarray, stat, draws: int = DRAWS, seed: int = SEED) -> list[float]:
    """Cluster bootstrap over quarters: `groups` = array of quarter labels per row; `stat(idx)` -> float or None."""
    rng = np.random.default_rng(seed)
    uq = np.unique(groups)
    idx_of = {g: np.flatnonzero(groups == g) for g in uq}
    vals = []
    for _ in range(draws):
        pick = rng.choice(uq, size=len(uq), replace=True)
        v = stat(np.concatenate([idx_of[g] for g in pick]))
        if v is not None and np.isfinite(v):
            vals.append(v)
    if not vals:
        return [None, None]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]
