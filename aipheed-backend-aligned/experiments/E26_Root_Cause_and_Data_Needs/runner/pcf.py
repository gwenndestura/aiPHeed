"""PCF: probabilistic component forecaster (FROZEN_EVALUATION_PROTOCOL.md 4.2-4.5). Pure functions, no I/O.

T1 label: S1 = H + 2D > tau.  H = regional SWS hunger (Balance Luzon), D = provincial relative food inflation.
H part  : local-level (random walk + sampling noise) Kalman filter on the SWS rounds published before the origin,
          sampling variance H(100-H)/n (n = 600), level variance q by maximum likelihood on a fixed grid.
D part  : least squares WITHOUT intercept of D(t'+k) on the latest published D (and optionally Dnow), Gaussian errors.
P(HIGH) = 1 - Phi((tau - mu_H - 2 mu_D) / sqrt(V_H + 4 sigma_D^2)).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

SIGMA_ETA_GRID = np.round(np.arange(0.0, 8.0001, 0.1), 1)
N_SWS = 600


def samp_var(h: float, n: int = N_SWS) -> float:
    h = float(np.clip(h, 0.5, 99.5))
    return h * (100.0 - h) / n


def _filter(times: np.ndarray, ys: np.ndarray, q: float, n: int):
    """Sequential Kalman filter for a local level with irregular times (quarters) and known sampling variance.
    Returns (loglik over observations 2..m, filtered level, filtered variance, last time)."""
    order = np.argsort(times, kind="stable")
    t, y = times[order].astype(float), ys[order].astype(float)
    L, P = y[0], samp_var(y[0], n)                      # diffuse start: first observation initialises the level
    ll, last = 0.0, t[0]
    for i in range(1, len(y)):
        P = P + q * (t[i] - last)
        last = t[i]
        s2 = samp_var(y[i], n)
        F = P + s2
        v = y[i] - L
        ll += -0.5 * (np.log(2 * np.pi * F) + v * v / F)
        K = P / F
        L, P = L + K * v, (1 - K) * P
    return ll, L, P, last


def h_forecast(times, ys, target_time: float, n: int = N_SWS) -> dict:
    """Forecast distribution of the published SWS value at target_time from rounds (times, ys)."""
    times, ys = np.asarray(times, float), np.asarray(ys, float)
    assert len(ys) >= 2 and target_time > times.max()
    best = None
    for se in SIGMA_ETA_GRID:
        ll, L, P, last = _filter(times, ys, se * se, n)
        if best is None or ll > best[0] + 1e-12:
            best = (ll, se, L, P, last)
    ll, se, L, P, last = best
    g = target_time - last
    V = P + g * se * se + samp_var(L, n)
    return {"mu_H": float(L), "V_H": float(V), "sigma_eta": float(se), "loglik": float(ll), "gap": float(g),
            "filtered_var": float(P), "n_rounds": int(len(ys))}


def d_fit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    ok = ~(np.isnan(X).any(1) | np.isnan(y))
    X, y = X[ok], y[ok]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return beta, float(np.sqrt((r ** 2).sum() / max(len(y) - 1, 1)))


def p_high(tau: float, mu_H: float, V_H: float, mu_D: float, sigma_D: float) -> float:
    sd = np.sqrt(V_H + 4.0 * sigma_D ** 2)
    return float(1.0 - norm.cdf((tau - mu_H - 2.0 * mu_D) / sd))


def p_pos(mu_D: float, sigma_D: float) -> float:
    return float(norm.cdf(mu_D / max(sigma_D, 1e-9)))
