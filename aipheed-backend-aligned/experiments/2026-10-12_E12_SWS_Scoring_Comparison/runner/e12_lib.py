"""E12 pure scoring functions (no data access)."""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pandas as pd

N_PROV = 5
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25]
BETAS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
WH = [0.0, 0.25, 0.5, 0.75, 1.0]


def deviations(f: pd.DataFrame) -> pd.DataFrame:
    """f: [province_code, quarter, F]. Adds mean5 and D; both NaN unless all five provinces have F (never zero-filled)."""
    f = f.copy()
    complete = f.groupby("quarter")["F"].transform(lambda v: v.notna().sum() == N_PROV and len(v) == N_PROV)
    f["mean5"] = f.groupby("quarter")["F"].transform("mean").where(complete)
    f["D"] = (f["F"] - f["mean5"]).where(complete)
    return f


def option_a(h: pd.Series, d: pd.Series, alpha: float, beta: float) -> pd.Series:
    """alpha*H + beta*D; NaN propagates."""
    return alpha * h + beta * d


def z_stats(h_train_by_quarter: pd.Series, d_train_rows: pd.Series) -> dict:
    """Training-only statistics. H: one value per training quarter. D: training province rows."""
    hs, ds = h_train_by_quarter.dropna(), d_train_rows.dropna()
    sd_h = float(hs.std(ddof=1)) if len(hs) > 1 else 0.0
    sd_d = float(ds.std(ddof=1)) if len(ds) > 1 else 0.0
    return {"mu_h": float(hs.mean()), "sd_h": sd_h, "mu_d": float(ds.mean()), "sd_d": sd_d,
            "n_h_quarters": int(len(hs)), "n_d_rows": int(len(ds)),
            "zero_var_h": bool(sd_h == 0.0), "zero_var_d": bool(sd_d == 0.0)}


def option_b(h: pd.Series, d: pd.Series, wh: float, st: dict) -> pd.Series:
    """wH*Z(H) + (1-wH)*Z(D) with frozen training stats; a zero-variance component contributes 0 (flagged in st)."""
    zh = (h - st["mu_h"]) / st["sd_h"] if st["sd_h"] > 0 else h * 0.0
    zd = (d - st["mu_d"]) / st["sd_d"] if st["sd_d"] > 0 else d * 0.0
    return wh * zh + (1.0 - wh) * zd


def ratio(alpha: float, beta: float) -> Fraction:
    return Fraction(str(alpha)) / Fraction(str(beta))


def equivalence_groups(alphas=ALPHAS, betas=BETAS) -> dict[Fraction, list[tuple[float, float]]]:
    g: dict[Fraction, list] = {}
    for a in alphas:
        for b in betas:
            g.setdefault(ratio(a, b), []).append((a, b))
    return dict(sorted(g.items()))


def within_quarter_ranks(df: pd.DataFrame, col: str) -> pd.Series:
    """Rank 1 = highest score within the quarter (ties share the lower rank)."""
    return df.groupby("quarter")[col].rank(ascending=False, method="min")


def within_quarter_spread(df: pd.DataFrame, col: str) -> pd.Series:
    return df.groupby("quarter")[col].agg(lambda v: v.max() - v.min() if v.notna().all() else np.nan)


def concordant(pred, obs) -> tuple[float, int]:
    pred, obs = np.asarray(pred, float), np.asarray(obs, float)
    c, n = 0.0, 0
    for i in range(len(obs)):
        for j in range(i + 1, len(obs)):
            if obs[i] == obs[j]:
                continue
            n += 1
            s = np.sign(pred[i] - pred[j]) * np.sign(obs[i] - obs[j])
            c += 1.0 if s > 0 else (0.5 if s == 0 else 0.0)
    return c, n


def ols_map(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Training-only least squares y = a + b*x."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    if len(x) < 3 or np.var(x) == 0:
        return float(np.mean(y)) if len(y) else np.nan, 0.0
    b = float(np.cov(x, y, ddof=0)[0, 1] / np.var(x))
    return float(y.mean() - b * x.mean()), b
