"""E70 metric helpers, copied verbatim from audit/2026-10-20_final_validation/audit.py (wilson .. icc) so that the
E70 scoring does not import the audit module, whose constants point at the main checkout. RNG seed 2026 as in the audit.
"""
import math

import numpy as np
import pandas as pd
from scipy.stats import binomtest

RNG = np.random.default_rng(2026)


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def auc(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    s = 0.0
    for a in pos:
        s += (neg < a).sum() + 0.5 * (neg == a).sum()
    return s / (len(pos) * len(neg))


def metrics(y, p, thr=0.5):
    y, p = np.asarray(y, int), np.asarray(p, float)
    d = (p >= thr).astype(int)
    tp, fp = int(((d == 1) & (y == 1)).sum()), int(((d == 1) & (y == 0)).sum())
    fn, tn = int(((d == 0) & (y == 1)).sum()), int(((d == 0) & (y == 0)).sum())
    n = len(y)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    precL = tn / (tn + fn) if tn + fn else None
    recL = tn / (tn + fp) if tn + fp else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    f1L = 2 * tn / (2 * tn + fn + fp) if 2 * tn + fn + fp else None
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": n, "pos": int(y.sum()), "neg": int(n - y.sum()), "correct": tp + tn, "accuracy": (tp + tn) / n,
            "acc_wilson95": wilson(tp + tn, n), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "precision_HIGH": prec, "recall_HIGH": rec, "f1_HIGH": f1, "precision_LOW": precL, "recall_LOW": recL,
            "f1_LOW": f1L, "balanced_accuracy": None if rec is None or recL is None else (rec + recL) / 2,
            "auc_roc": auc(y, p), "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))), "share_pred_HIGH": float(d.mean())}


def cluster_boot_acc(R, col, ycol="y", B=4000):
    qs_ = R["target"].unique()
    g = {q: R[R["target"] == q] for q in qs_}
    out = []
    for _ in range(B):
        s = RNG.choice(qs_, len(qs_), replace=True)
        D = pd.concat([g[q] for q in s])
        out.append(((D[col] >= 0.5).astype(int) == D[ycol]).mean())
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def paired(R, a, b, ycol="y", B=4000):
    """Arm a minus arm b: Brier difference with quarter-cluster bootstrap CI, quarter sign test, McNemar exact."""
    R = R.copy()
    R["la"], R["lb"] = (R[a] - R[ycol]) ** 2, (R[b] - R[ycol]) ** 2
    per_q = R.groupby("target")[["la", "lb"]].mean()
    diff = per_q["la"] - per_q["lb"]
    w, l_ = int((diff < -1e-12).sum()), int((diff > 1e-12).sum())
    qs_ = per_q.index.to_numpy()
    cnt = R.groupby("target").size()
    bs = []
    for _ in range(B):
        s = RNG.choice(qs_, len(qs_), replace=True)
        bs.append(float((per_q.loc[s, "la"] * cnt.loc[s].values).sum() / cnt.loc[s].sum()
                        - (per_q.loc[s, "lb"] * cnt.loc[s].values).sum() / cnt.loc[s].sum()))
    ca = (R[a] >= .5).astype(int) == R[ycol]
    cb = (R[b] >= .5).astype(int) == R[ycol]
    n10, n01 = int((ca & ~cb).sum()), int((~ca & cb).sum())
    acc_q = R.assign(ca=ca, cb=cb).groupby("target")[["ca", "cb"]].mean()
    dq = acc_q["ca"] - acc_q["cb"]
    aw, al = int((dq > 0).sum()), int((dq < 0).sum())
    return {"brier_diff": float(R["la"].mean() - R["lb"].mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "quarter_brier_wins_a": w, "quarter_brier_losses_a": l_,
            "sign_p": float(binomtest(w, w + l_, .5).pvalue) if w + l_ else 1.0,
            "mcnemar_a_right_only": n10, "mcnemar_b_right_only": n01,
            "mcnemar_p": float(binomtest(n10, n10 + n01, .5).pvalue) if n10 + n01 else 1.0,
            "acc_diff": float(ca.mean() - cb.mean()), "quarter_acc_wins_a": aw, "quarter_acc_losses_a": al,
            "acc_quarter_sign_p": float(binomtest(aw, aw + al, .5).pvalue) if aw + al else 1.0}


def calibration(y, p, bins=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001)):
    y, p = np.asarray(y), np.asarray(p, float)
    rows, ece = [], 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum():
            rows.append({"bin": f"[{lo:.1f},{min(hi, 1):.1f})", "n": int(m.sum()), "mean_p": float(p[m].mean()),
                         "obs_rate": float(y[m].mean())})
            ece += m.sum() / len(y) * abs(p[m].mean() - y[m].mean())
    ci = None
    if len(set(y)) > 1:
        lp = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
        # calibration-in-the-large and slope by simple logistic fit (Newton)
        X = np.c_[np.ones_like(lp), lp]
        b = np.zeros(2)
        for _ in range(50):
            mu = 1 / (1 + np.exp(-X @ b))
            W = mu * (1 - mu) + 1e-9
            b = b + np.linalg.solve(X.T @ (X * W[:, None]), X.T @ (y - mu))
        ci = {"intercept": float(b[0]), "slope": float(b[1]), "mean_p": float(p.mean()), "obs_rate": float(y.mean())}
    return {"bins": rows, "ece": float(ece), "logistic_recal": ci}


def icc(R, ycol="y"):
    """One-way ANOVA ICC of the label within target quarters (how much provinces in a quarter move together)."""
    g = R.groupby("target")[ycol]
    k = g.size().mean()
    msb = (g.size() * (g.mean() - R[ycol].mean()) ** 2).sum() / (g.ngroups - 1)
    msw = ((R[ycol] - g.transform("mean")) ** 2).sum() / (len(R) - g.ngroups)
    v = (msb - msw) / (msb + (k - 1) * msw) if (msb + (k - 1) * msw) else float("nan")
    deff = 1 + (k - 1) * v
    return {"icc": float(v), "design_effect": float(deff), "effective_n": float(len(R) / deff) if deff > 0 else None}


