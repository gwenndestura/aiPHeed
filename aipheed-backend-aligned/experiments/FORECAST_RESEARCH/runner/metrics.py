"""FORECAST_RESEARCH metric helpers: classification metrics at the 0.50 rule, Brier, log loss, AUC, quarter-block
bootstrap of Brier differences, calibration summaries, effective sample size."""
from __future__ import annotations

import numpy as np
import pandas as pd

SEED = 2031


def auc(y, p) -> float:
    y, p = np.asarray(y, int), np.asarray(p, float)
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))


def cls(y, p, cut: float = 0.5) -> dict:
    y, p = np.asarray(y, int), np.clip(np.asarray(p, float), 0, 1)
    yh = (p >= cut).astype(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    rec = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "high": int(y.sum()), "accuracy": float((yh == y).mean()),
            "balanced_accuracy": float(np.nanmean([rec, spec])), "precision": tp / (tp + fp) if tp + fp else float("nan"),
            "recall": rec, "specificity": spec, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "brier": float(np.mean((p - y) ** 2)), "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))),
            "auc": auc(y, p), "mean_p": float(p.mean()), "base_rate": float(y.mean())}


def boot_diff(q, a, b, draws: int = 4000, seed: int = SEED) -> dict:
    """Mean of a - b with a quarter-block bootstrap (rows of a target quarter resampled together)."""
    q, a, b = np.asarray(q), np.asarray(a, float), np.asarray(b, float)
    d = a - b
    uq = np.unique(q)
    by = [d[q == u] for u in uq]
    rng = np.random.default_rng(seed)
    bs = np.array([np.concatenate([by[i] for i in rng.integers(0, len(uq), len(uq))]).mean() for _ in range(draws)])
    return {"diff": float(d.mean()), "ci90": [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))],
            "p_less": float((bs >= 0).mean()), "p_two": float(min(1.0, 2 * min((bs >= 0).mean(), (bs <= 0).mean())))}


def acc_ci(q, y, p, draws: int = 4000, seed: int = SEED) -> list[float]:
    c = ((np.asarray(p) >= .5).astype(int) == np.asarray(y)).astype(float)
    q = np.asarray(q)
    uq = np.unique(q)
    by = [c[q == u] for u in uq]
    rng = np.random.default_rng(seed)
    bs = [np.concatenate([by[i] for i in rng.integers(0, len(uq), len(uq))]).mean() for _ in range(draws)]
    return [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))]


def calibration(y, p, bins=(0, .1, .3, .5, .7, 1.0001)) -> dict:
    """Binned reliability table, calibration-in-the-large and the logistic recalibration slope (diagnostic only:
    computed on evaluation rows, never used to change a forecast)."""
    y, p = np.asarray(y, int), np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.any():
            rows.append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "n": int(m.sum()), "mean_p": float(p[m].mean()),
                         "observed": float(y[m].mean())})
    out = {"bins": rows, "citl": float(y.mean() - p.mean())}
    if 0 < y.sum() < len(y):
        from sklearn.linear_model import LogisticRegression
        lg = np.log(p / (1 - p)).reshape(-1, 1)
        lr = LogisticRegression(C=1e6).fit(lg, y)
        out["slope"], out["intercept"] = float(lr.coef_[0][0]), float(lr.intercept_[0])
    out["ece"] = float(sum(r["n"] * abs(r["mean_p"] - r["observed"]) for r in rows) / len(y))
    return out


def n_eff(q, y) -> dict:
    """Design effect of province rows clustered in target quarters (one-way ANOVA ICC of the label)."""
    df = pd.DataFrame({"q": q, "y": np.asarray(y, float)})
    g = df.groupby("q")["y"]
    k = len(g)
    m = len(df) / k
    msb = (g.size() * (g.mean() - df["y"].mean()) ** 2).sum() / max(k - 1, 1)
    msw = ((df["y"] - g.transform("mean")) ** 2).sum() / max(len(df) - k, 1)
    icc = (msb - msw) / (msb + (m - 1) * msw) if (msb + (m - 1) * msw) > 0 else 0.0
    icc = max(icc, 0.0)
    return {"n": len(df), "quarters": k, "icc": float(icc), "n_eff": float(len(df) / (1 + (m - 1) * icc)),
            "high": int(df["y"].sum()), "high_quarters": int((g.max() > 0).sum())}
