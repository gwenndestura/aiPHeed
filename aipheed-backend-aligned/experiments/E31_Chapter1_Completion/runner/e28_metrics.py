"""E28 metrics with the estimability rules of E28_EVALUATION_PROTOCOL.md section 4, and the E27 paired tests."""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd

SEED = 20261014
B = 2000
EPS = 1e-6
NE = "NOT_ESTIMABLE"


def _auc(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def _ap(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    if y.sum() == 0 or y.sum() == len(y):
        return None
    order = np.argsort(-p, kind="mergesort")
    ys = y[order]
    ps = p[order]
    # average precision over distinct thresholds (ties counted together)
    ap, tp, fp, prev_r = 0.0, 0, 0, 0.0
    i = 0
    P = ys.sum()
    while i < len(ys):
        j = i
        while j + 1 < len(ys) and ps[j + 1] == ps[i]:
            j += 1
        tp += ys[i:j + 1].sum()
        fp += (j + 1 - i) - ys[i:j + 1].sum()
        r = tp / P
        ap += (r - prev_r) * (tp / (tp + fp))
        prev_r = r
        i = j + 1
    return float(ap)


def point_metrics(y, p) -> dict:
    y = np.asarray(y, int)
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    yhat = (p >= 0.5).astype(int)
    tp = int(((yhat == 1) & (y == 1)).sum()); fp = int(((yhat == 1) & (y == 0)).sum())
    tn = int(((yhat == 0) & (y == 0)).sum()); fn = int(((yhat == 0) & (y == 1)).sum())
    n_hi, n_lo = int(y.sum()), int((1 - y).sum())
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    spec = tn / (tn + fp) if (tn + fp) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec is not None and (prec + rec) > 0) else (
        0.0 if (prec is not None and rec is not None) else None)
    bal = (rec + spec) / 2 if (rec is not None and spec is not None) else None
    bins = [(0, .35), (.35, .65), (.65, 1.0001)]
    ece, rel = 0.0, []
    for lo, hi in bins:
        m = (p >= lo) & (p < hi)
        if m.any():
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
            rel.append({"bin": [lo, min(hi, 1.0)], "n": int(m.sum()), "mean_p": float(p[m].mean()),
                        "obs_rate": float(y[m].mean())})
    return {"n": int(len(y)), "HIGH": n_hi, "LOW": n_lo, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "accuracy": float((yhat == y).mean()), "balanced_accuracy": bal, "precision": prec, "recall": rec,
            "specificity": spec, "f1": f1, "roc_auc": _auc(y, p), "pr_auc": _ap(y, p),
            "brier": float(((p - y) ** 2).mean()),
            "log_loss": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
            "calibration_in_the_large": float(p.mean() - y.mean()), "ece_3bin": float(ece), "reliability": rel,
            "share_predicted_HIGH": float(yhat.mean())}


def flags(m: dict, n_dates: int) -> dict:
    minority = min(m["HIGH"], m["LOW"])
    f = {}
    for k in ("roc_auc", "pr_auc"):
        f[k] = NE if m[k] is None else ("UNSTABLE" if minority < 5 or n_dates < 8 else "OK")
    f["precision"] = NE if m["precision"] is None else ("UNSTABLE" if minority < 5 or n_dates < 8 else "OK")
    f["recall"] = NE if m["recall"] is None else ("UNSTABLE" if minority < 5 or n_dates < 8 else "OK")
    f["f1"] = NE if m["f1"] is None else ("UNSTABLE" if minority < 5 or n_dates < 8 else "OK")
    f["balanced_accuracy"] = NE if m["balanced_accuracy"] is None else (
        "UNSTABLE" if minority < 5 or n_dates < 8 else "OK")
    for k in ("accuracy", "brier", "log_loss"):
        f[k] = "UNSTABLE" if n_dates < 8 else "OK"
    return f


def bootstrap(df: pd.DataFrame, date_col="t", b=B, seed=SEED) -> dict:
    """Date-cluster bootstrap 95% intervals for accuracy, Brier, AUC (AUC only from resamples with both classes)."""
    rng = np.random.default_rng(seed)
    dates = sorted(df[date_col].unique())
    groups = {d: df[df[date_col] == d] for d in dates}
    acc, bri, auc = [], [], []
    for _ in range(b):
        pick = rng.choice(len(dates), len(dates), replace=True)
        s = pd.concat([groups[dates[i]] for i in pick])
        y, p = s["y"].to_numpy(int), np.clip(s["p"].to_numpy(float), EPS, 1 - EPS)
        acc.append(((p >= 0.5).astype(int) == y).mean())
        bri.append(((p - y) ** 2).mean())
        a = _auc(y, p)
        if a is not None:
            auc.append(a)

    def ci(v):
        return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if len(v) else None
    return {"accuracy_ci95": ci(acc), "brier_ci95": ci(bri), "auc_ci95": ci(auc),
            "auc_resamples_with_both_classes": len(auc), "n_dates": len(dates)}


def signflip_p(diffs) -> float | None:
    """One-sided exact sign-flip p for mean(diffs) > 0 (diffs = reference loss - arm loss, one per date)."""
    d = np.asarray([x for x in diffs if x == x], float)
    n = len(d)
    if n == 0:
        return None
    obs = d.mean()
    if n <= 20:
        cnt = 0
        tot = 0
        for signs in itertools.product((1, -1), repeat=n):
            tot += 1
            cnt += (np.dot(signs, d) / n) >= obs - 1e-12
        return cnt / tot
    rng = np.random.default_rng(SEED)
    s = rng.choice((1, -1), size=(200000, n))
    return float(((s @ d) / n >= obs - 1e-12).mean())


def holm(pvals: dict) -> dict:
    items = sorted([(k, v) for k, v in pvals.items() if v is not None], key=lambda kv: kv[1])
    m = len(items)
    out, run = {}, 0.0
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    for k, v in pvals.items():
        out.setdefault(k, None)
    return out


def per_date_losses(df: pd.DataFrame) -> pd.DataFrame:
    p = np.clip(df["p"].to_numpy(float), EPS, 1 - EPS)
    y = df["y"].to_numpy(int)
    x = df.assign(err=((p >= 0.5).astype(int) != y).astype(float), bri=(p - y) ** 2)
    return x.groupby("t")[["err", "bri"]].mean()


def math_ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))
