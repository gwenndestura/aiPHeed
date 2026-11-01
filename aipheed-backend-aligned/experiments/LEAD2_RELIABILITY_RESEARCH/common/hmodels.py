"""Phase 2 hunger-crossing candidates (EXPERIMENT_PLAN_PHASE2.md section 2). Each returns P(area hunger in quarter
t + k > 11.3) using only SWS rounds and covariates published before O(t). Fitting, standardisation and penalty choice
happen inside the call (inside the fold).

Y2   kalman(area, t, k, fit_areas)   latent AR(1) state with known SWS sampling error
Y3a  h3b(t, k)                        LEAD2_OPTIMIZATION a3.h3 sample b, unchanged (BL only)
Y3b  logit(area, t, k, fit_areas)     pooled L2 logistic on crossing with issue-time covariates
Y3c  ridge(area, t, k, fit_areas)     ridge on the continuous change, Gaussian predictive
"""
from __future__ import annotations

import functools
import math
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import log_loss

import cov
import p2lib as P

R = P.R
H_LINE = R.H_LINE
C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
A_GRID = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
H_MAX = 6
warnings.filterwarnings("ignore", category=RuntimeWarning)


# ================================================================================================ Y2 Kalman
@functools.lru_cache(maxsize=8192)
def _series(area: str, iss: pd.Timestamp) -> tuple:
    """Quarter means and their sampling variances from rounds published before iss."""
    r = R.rounds()
    k = r[(r["area"] == area) & (r["published"] < iss)]
    out = []
    for q, g in k.groupby("q"):
        se = (g["moe"].fillna(6.0) / 1.96) ** 2
        out.append((int(q), float(g["H"].mean()), float(se.mean() / len(g))))
    return tuple(out)


def _filter(obs: tuple, mu: float, phi: float, tau2: float):
    """Kalman filter of x_q - mu = phi (x_{q-1} - mu) + eta over consecutive quarters (gaps = prediction only).
    Returns log-likelihood, last quarter, filtered mean and variance."""
    q0 = obs[0][0]
    m, v = 0.0, tau2 / max(1 - phi ** 2, 1e-6)
    ll, cur = 0.0, q0
    for q, y, s2 in obs:
        for _ in range(q - cur):
            m, v = phi * m, phi ** 2 * v + tau2
        cur = q
        f = v + s2
        e = (y - mu) - m
        ll += -0.5 * (math.log(2 * math.pi * f) + e * e / f)
        g = v / f
        m, v = m + g * e, (1 - g) * v
    return ll, cur, m, v


@functools.lru_cache(maxsize=2048)
def _kfit(areas: tuple, iss: pd.Timestamp) -> tuple[float, float]:
    data = [(_series(a, iss), float(np.mean([x[1] for x in _series(a, iss)]))) for a in areas if len(_series(a, iss)) >= 8]

    def nll(th):
        phi, tau2 = 1 / (1 + math.exp(-th[0])), math.exp(th[1])
        return -sum(_filter(o, mu, phi, tau2)[0] for o, mu in data)

    best = min((minimize(nll, x0, method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-6, "maxiter": 2000})
                for x0 in ([1.0, math.log(4.0)], [2.5, math.log(2.0)], [-0.5, math.log(10.0)])), key=lambda r: r.fun)
    return 1 / (1 + math.exp(-best.x[0])), math.exp(best.x[1])


def kalman(area: str, t: int, k: int, fit_areas: tuple) -> float:
    iss = R.issue(t)
    o = _series(area, iss)
    if len(o) < 8:
        return float("nan")
    phi, tau2 = _kfit(tuple(fit_areas), iss)
    mu = float(np.mean([x[1] for x in o]))
    _, q_last, m, v = _filter(o, mu, phi, tau2)
    h = (t + k) - q_last
    mean = mu + phi ** h * m
    var = phi ** (2 * h) * v + tau2 * sum(phi ** (2 * i) for i in range(h))
    s2_next = (o[-1][2])                                   # one round with the newest round's sampling variance
    return float(norm.cdf((mean - H_LINE) / math.sqrt(var + s2_next)))


# ================================================================================================ Y3a
def h3b(t: int, k: int) -> float:
    import a3
    return a3.h3(int(t), int(k), "b")


# ================================================================================================ Y3b / Y3c
@functools.lru_cache(maxsize=2048)
def _pairs(areas: tuple, iss: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for a in areas:
        d = R.known(a, iss)
        if not d:
            continue
        ma = float(np.mean(list(d.values())))
        for q0, v0 in d.items():
            f = cov.feats(q0 + 1)
            for h in range(1, H_MAX + 1):
                if q0 + h in d:
                    rows.append({"area": a, "q0": q0, "tq": q0 + h, "h": h, "dist": v0 - H_LINE, "dev": v0 - ma,
                                 **dict(zip(cov.FEATS, f)), "y1": d[q0 + h], "dy": d[q0 + h] - v0,
                                 "cross": int(d[q0 + h] > H_LINE)})
    return pd.DataFrame(rows)


XCOLS = ["dist", "dev", "h"] + cov.FEATS


def _design(tr: pd.DataFrame, x0: dict):
    X = tr[XCOLS].to_numpy(float)
    mean = np.nanmean(X, 0)
    mean = np.where(np.isnan(mean), 0.0, mean)
    X = np.where(np.isnan(X), mean, X)
    sd = X.std(0)
    sd[sd == 0] = 1.0
    z0 = np.array([x0[c] for c in XCOLS], float)
    z0 = np.where(np.isnan(z0), mean, z0)
    return (X - mean) / sd, ((z0 - mean) / sd).reshape(1, -1)


def _x0(area: str, t: int, k: int):
    d = R.known(area, R.issue(t))
    if not d:
        return None
    q_last = max(d)
    ma = float(np.mean(list(d.values())))
    return {"dist": d[q_last] - H_LINE, "dev": d[q_last] - ma, "h": (t + k) - q_last,
            **dict(zip(cov.FEATS, cov.feats(t)))}, d[q_last]


def _inner_split(tr: pd.DataFrame):
    cut = tr["tq"].quantile(0.75)
    return tr["tq"] <= cut, tr["tq"] > cut


def logit(area: str, t: int, k: int, fit_areas: tuple, return_cfg: bool = False):
    tr = _pairs(tuple(fit_areas), R.issue(t))
    x = _x0(area, t, k)
    if x is None or len(tr) < 40 or tr["cross"].nunique() < 2:
        return float("nan")
    X, z = _design(tr, x[0])
    y = tr["cross"].to_numpy(int)
    a, b = _inner_split(tr)
    best, bc = np.inf, C_GRID[0]
    if y[a.to_numpy()].min() != y[a.to_numpy()].max() and len(set(y[b.to_numpy()])) > 0:
        for c in C_GRID:
            m = LogisticRegression(C=c, max_iter=2000).fit(X[a.to_numpy()], y[a.to_numpy()])
            ll = log_loss(y[b.to_numpy()], m.predict_proba(X[b.to_numpy()])[:, 1], labels=[0, 1])
            if ll < best:
                best, bc = ll, c
    p = float(LogisticRegression(C=bc, max_iter=2000).fit(X, y).predict_proba(z)[0, 1])
    return (p, bc) if return_cfg else p


def ridge(area: str, t: int, k: int, fit_areas: tuple, return_cfg: bool = False):
    tr = _pairs(tuple(fit_areas), R.issue(t))
    x = _x0(area, t, k)
    if x is None or len(tr) < 40:
        return float("nan")
    X, z = _design(tr, x[0])
    y = tr["dy"].to_numpy(float)
    a, b = (s.to_numpy() for s in _inner_split(tr))
    best, ba = np.inf, A_GRID[0]
    for al in A_GRID:
        e = Ridge(alpha=al).fit(X[a], y[a]).predict(X[b]) - y[b]
        if float(np.mean(e ** 2)) < best:
            best, ba = float(np.mean(e ** 2)), al
    m = Ridge(alpha=ba).fit(X, y)
    # residual sigma at the forecast's true horizon (pairs with the same h), else all pairs
    res = y - m.predict(X)
    hm = tr["h"].to_numpy() == x[0]["h"]
    sig = math.sqrt(float(np.mean(res[hm] ** 2))) if hm.sum() >= 8 else math.sqrt(float(np.mean(res ** 2)))
    mu = x[1] + float(m.predict(z)[0])
    p = float(norm.cdf((mu - H_LINE) / max(sig, 0.5)))
    return (p, ba, mu) if return_cfg else p
