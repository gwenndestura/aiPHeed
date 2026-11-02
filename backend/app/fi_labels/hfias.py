"""HFIAS scoring and weighted prevalence.

Scoring (FNRI 2015 Food Security Survey, Table 2 and Table 3, citing the HFIAS Indicator Guide v3, Coates,
Swindale & Bilinsky 2007): nine occurrence questions on the past 30 days; frequency 0 = never, 1 = rarely (1-2
times), 2 = sometimes (3-10 times), 3 = often (>10 times). Score = sum, 0..27.

Category (Guide v3 algorithm, assigned to the most severe level reached):
    severe    Q5 = 3 or Q6 = 3, or any occurrence of Q7, Q8 or Q9
    moderate  Q3 >= 2 or Q4 >= 2 or Q5 in (1, 2) or Q6 in (1, 2)
    mild      Q1 >= 2 or Q2 >= 1 or Q3 = 1 or Q4 = 1
    secure    otherwise (Q1 <= 1 and nothing else)
Q1 worry; Q2 unable to eat preferred foods; Q3 few kinds of foods; Q4 foods not wanted; Q5 smaller meal;
Q6 fewer meals; Q7 no food in the household; Q8 sleep hungry; Q9 whole day and night without eating.
A household with any item missing gets no score and no category (never imputed).

Weighted prevalence: ratio estimator with Taylor-linearised variance for a stratified multi-stage design (PSUs
treated as sampled with replacement within strata), the standard approximation used by survey software.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ITEMS = [f"q{i}" for i in range(1, 10)]
CATEGORIES = ["food_secure", "mildly_food_insecure", "moderately_food_insecure", "severely_food_insecure"]


def score(df: pd.DataFrame) -> pd.Series:
    x = df[ITEMS]
    s = x.sum(axis=1, min_count=9)
    return s.where(x.notna().all(axis=1))


def category(df: pd.DataFrame) -> pd.Series:
    x = df[ITEMS]
    complete = x.notna().all(axis=1)
    if not ((x.isna()) | x.isin([0, 1, 2, 3])).all().all():
        raise ValueError("HFIAS frequencies must be 0, 1, 2 or 3")
    q = {i: x[f"q{i}"] for i in range(1, 10)}
    severe = (q[5] == 3) | (q[6] == 3) | (q[7] >= 1) | (q[8] >= 1) | (q[9] >= 1)
    moderate = (q[3] >= 2) | (q[4] >= 2) | q[5].isin([1, 2]) | q[6].isin([1, 2])
    mild = (q[1] >= 2) | (q[2] >= 1) | (q[3] == 1) | (q[4] == 1)
    cat = np.select([severe, moderate, mild], CATEGORIES[3:0:-1], default=CATEGORIES[0])
    return pd.Series(cat, index=df.index).where(complete)


def weighted_prevalence(y: pd.Series, w: pd.Series, strata: pd.Series | None = None, psu: pd.Series | None = None) -> dict:
    """Weighted mean of a 0/1 indicator with linearised SE, 95 % CI and Kish effective sample size."""
    ok = y.notna() & w.notna() & (w > 0)
    y, w = y[ok].astype(float), w[ok].astype(float)
    n = int(len(y))
    if n == 0:
        return {"n": 0}
    p = float(np.sum(w * y) / np.sum(w))
    z = w * (y - p) / np.sum(w)                     # linearised score of the ratio estimator
    if psu is None:
        var = n / max(n - 1, 1) * float(np.sum(z ** 2))
    else:
        st = (strata[ok] if strata is not None else pd.Series(0, index=y.index)).astype(str)
        ps = psu[ok].astype(str)
        zt = z.groupby([st, ps]).sum()
        var = 0.0
        for _, g in zt.groupby(level=0):
            m = len(g)
            if m > 1:
                var += m / (m - 1) * float(np.sum((g - g.mean()) ** 2))
    se = float(np.sqrt(var))
    n_eff = float(np.sum(w) ** 2 / np.sum(w ** 2))
    return {"n": n, "prevalence": p, "se": se, "ci95": [max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)],
            "n_effective": n_eff, "cv": se / p if p > 0 else None,
            "adequate": bool(n >= 100 and (p == 0 or se / p <= 0.20))}
