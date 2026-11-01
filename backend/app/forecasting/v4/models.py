"""
DELTA-X (v4 PREREGISTRATION section 2): predicted change from an anchor (persistence or the LL-K level) as a ridge
combination (alpha = 10, no intercept) of the exogenous features that pass the in-fold stability rule:
>= 6 distinct training issues, |Spearman rho| >= 0.30, and the same sign in the earlier and later halves of the
training issues (each half >= 3 issues). With no feature passing, the predicted change is 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from app.forecasting.v4.features import FEATURES, GROUP

ALPHA = 10.0
RHO_MIN = 0.30
MIN_ISSUES = 6
MIN_HALF = 3


@dataclass
class DeltaParams:
    features: list = field(default_factory=list)
    mean: dict = field(default_factory=dict)
    sd: dict = field(default_factory=dict)
    beta: dict = field(default_factory=dict)
    n_train: int = 0
    screen: dict = field(default_factory=dict)      # feature -> (n_issues, rho, rho_early, rho_late, passed)


def _rho(x, y) -> float:
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(stats.spearmanr(x, y).statistic)


def stable(train: pd.DataFrame, f: str) -> tuple:
    d = train[["issue", "change", f]].dropna()
    iss = sorted(d.issue.unique())
    if len(iss) < MIN_ISSUES:
        return len(iss), float("nan"), float("nan"), float("nan"), False
    med = iss[len(iss) // 2]
    early, late = d[d.issue < med], d[d.issue >= med]
    r, re, rl = _rho(d[f], d.change), _rho(early[f], early.change), _rho(late[f], late.change)
    ok = (early.issue.nunique() >= MIN_HALF and late.issue.nunique() >= MIN_HALF and abs(r) >= RHO_MIN
          and np.sign(re) == np.sign(r) == np.sign(rl) and re == re and rl == rl)
    return len(iss), r, re, rl, bool(ok)


def fit_delta(train: pd.DataFrame) -> DeltaParams:
    """train: one row per (issue, area) with 'issue', 'change' (truth - anchor) and the FEATURES columns."""
    p = DeltaParams(n_train=len(train))
    if train.empty:
        return p
    for f in FEATURES:
        s = stable(train, f)
        p.screen[f] = s
        if s[-1]:
            p.features.append(f)
    if not p.features:
        return p
    Z = []
    for f in p.features:
        v = train[f].astype(float)
        m, sd = float(v.mean()), float(v.std(ddof=0)) or 1.0
        p.mean[f], p.sd[f] = m, sd
        Z.append(((v - m) / sd).fillna(0.0).to_numpy())
    Z = np.column_stack(Z)
    y = train["change"].to_numpy(float)
    b = np.linalg.solve(Z.T @ Z + ALPHA * np.eye(Z.shape[1]), Z.T @ y)
    p.beta = {f: float(x) for f, x in zip(p.features, b)}
    return p


def predict_delta(p: DeltaParams, x: pd.Series) -> tuple[float, dict]:
    """Predicted change and its exact per-feature contributions (missing feature -> z = 0, contribution 0)."""
    contrib = {}
    for f in p.features:
        v = x.get(f)
        z = 0.0 if v is None or v != v else (float(v) - p.mean[f]) / p.sd[f]
        contrib[f] = p.beta[f] * z
    return float(sum(contrib.values())), contrib


def by_group(contrib: dict) -> dict:
    out: dict = {}
    for f, v in contrib.items():
        out[GROUP[f]] = out.get(GROUP[f], 0.0) + v
    return out
