"""
E133 model library (protocol 9683aad section 2): hierarchical factor state-space models for the 4 SWS areas.

State (n = 10): [c, g, alpha_1..4, d_1..4]
    c_t       = c_{t-1} + g_{t-1} + sum_g beta_g z_{g,t-1} + u_c      var q_c (+ b at the 2025-Q2 break)
    g_t       = phi g_{t-1} + u_g                                    var q_g (HFM-TREND only; else g = 0)
    alpha_a   constant, prior N(0, 25)
    d_{a,t}   = rho d_{a,t-1} + beta_V w_a z_{A,t-1} + u_d             var q_d
    y_{a,t}   = c_t + alpha_a + d_{a,t} (+ s_{q(t)} after the break) + e,   var SE^2 + tau^2
Every fit uses only rounds published before the issue date and drivers available by then.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

NA = 4
N = 10
IC, IG, IA, ID = 0, 1, slice(2, 6), slice(6, 10)
GROUPS = ("A", "C", "E", "N")          # common-level drivers; V acts through the area deviations
H = np.zeros((NA, N))
for _a in range(NA):
    H[_a, IC] = 1.0
    H[_a, 2 + _a] = 1.0
    H[_a, 6 + _a] = 1.0


@dataclass
class Spec:
    tau: bool = False          # estimate non-sampling variance
    trend: bool = False        # damped slope on the common level
    phi: float = 0.0
    drivers: tuple = ()        # subset of GROUPS + ("V",)


@dataclass
class Fit:
    q_c: float
    q_d: float
    rho: float
    b: float
    tau2: float = 0.0
    q_g: float = 0.0
    phi: float = 0.0
    beta: dict = field(default_factory=dict)
    ll: float = -np.inf
    asym: bool = False          # post-hoc PH1: drivers enter as shocks only, max(z, 0)


def _init(y0: np.ndarray, fit: Fit):
    x = np.zeros(N)
    P = np.zeros((N, N))
    x[IC] = float(np.nanmean(y0)) if np.isfinite(y0).any() else 15.0
    P[IC, IC] = 25.0
    P[IG, IG] = fit.q_g / max(1 - fit.phi ** 2, 1e-6) if fit.q_g > 0 else 0.0
    for a in range(NA):
        P[2 + a, 2 + a] = 25.0
        P[6 + a, 6 + a] = fit.q_d / (1 - fit.rho ** 2) if fit.rho < 0.999 else 25.0
    return x, P


def _transition(fit: Fit):
    F = np.eye(N)
    F[IC, IG] = 1.0
    F[IG, IG] = fit.phi
    for a in range(NA):
        F[6 + a, 6 + a] = fit.rho
    return F


def _exog(fit: Fit, z: dict, w: np.ndarray) -> np.ndarray:
    u = np.zeros(N)
    if fit.asym:
        z = {g: max(v, 0.0) for g, v in z.items()}
    for g in GROUPS:
        if g in fit.beta:
            u[IC] += fit.beta[g] * z.get(g, 0.0)
    if "V" in fit.beta:
        u[ID] = fit.beta["V"] * w * z.get("A", 0.0)
    return u


def kfilter(Y: np.ndarray, R: np.ndarray, t_idx: np.ndarray, fit: Fit, brk: int, Z: list | None = None,
            w: np.ndarray | None = None):
    """Y, R: (T, 4) with NaN for missing. Z[t] = driver dict used for the transition INTO period t.
    Returns final state, covariance, log-likelihood and the one-step innovations {(t, a): v}."""
    T = len(Y)
    w = np.zeros(NA) if w is None else w
    F = _transition(fit)
    first = next(t for t in range(T) if np.isfinite(Y[t]).any())
    x, P = _init(Y[first], fit)
    ll, innov = 0.0, {}
    for t in range(first, T):
        if t > first:
            x = F @ x + (_exog(fit, Z[t], w) if Z is not None else 0.0)
            P = F @ P @ F.T
            P[IC, IC] += fit.q_c + (fit.b if t_idx[t] == brk else 0.0)
            P[IG, IG] += fit.q_g
            P[ID, ID] += np.eye(NA) * fit.q_d
        for a in range(NA):
            yt = Y[t, a]
            if yt != yt:
                continue
            h = H[a]
            v = yt - h @ x
            Ph = P @ h
            S = h @ Ph + R[t, a] + fit.tau2
            if t > first:
                ll += -0.5 * (np.log(2 * np.pi * S) + v * v / S)
                innov[(int(t_idx[t]), a)] = float(v)
            K = Ph / S
            x = x + K * v
            P = P - np.outer(K, Ph)
    return x, P, ll, innov


def forecast(x, P, fit: Fit, steps: int, Zf: list, w: np.ndarray | None = None, brk_in: list | None = None):
    """Propagate the filtered state `steps` periods with driver dicts Zf[j] for the j-th transition."""
    w = np.zeros(NA) if w is None else w
    F = _transition(fit)
    x, P = x.copy(), P.copy()
    for j in range(steps):
        x = F @ x + _exog(fit, Zf[j], w)
        P = F @ P @ F.T
        P[IC, IC] += fit.q_c + (fit.b if brk_in and brk_in[j] else 0.0)
        P[IG, IG] += fit.q_g
        P[ID, ID] += np.eye(NA) * fit.q_d
    mean = H @ x
    var = np.einsum("ij,jk,ik->i", H, P, H)
    return mean, var


def _neg_ll(theta, spec: Spec, b, Y, R, t_idx, brk):
    fit = Fit(q_c=np.exp(theta[0]), q_d=np.exp(theta[1]), rho=float(theta[2]), b=b,
              tau2=np.exp(theta[3]) if spec.tau else 0.0,
              q_g=np.exp(theta[4]) if spec.trend else 0.0, phi=spec.phi if spec.trend else 0.0)
    return -kfilter(Y, R, t_idx, fit, brk)[2]


B_GRID = (0.0, 9.0, 25.0, 49.0)
STARTS = ((np.log(2.0), np.log(1.0), 0.6), (np.log(8.0), np.log(4.0), 0.9))


def fit_variances(Y, R, t_idx, brk: int, spec: Spec) -> Fit:
    """Pooled penalty-free maximum likelihood; deterministic fixed starts; b on a grid (0 when the break is not yet
    in the data). theta = [log q_c, log q_d, rho, log tau2, log q_g]; unused entries are pinned."""
    best = Fit(1, 1, 0.5, 0.0)
    bgrid = B_GRID if t_idx.max() >= brk else (0.0,)
    bnds = [(np.log(0.01), np.log(100.0)), (np.log(0.01), np.log(100.0)), (0.0, 1.0),
            (np.log(0.01), np.log(50.0)) if spec.tau else (0.0, 0.0),
            (np.log(0.01), np.log(20.0)) if spec.trend else (0.0, 0.0)]
    for b in bgrid:
        for s in STARTS:
            th0 = np.array(list(s) + [0.0, np.log(0.5) if spec.trend else 0.0], float)
            r = minimize(_neg_ll, th0, args=(spec, b, Y, R, t_idx, brk), method="L-BFGS-B", bounds=bnds,
                         options={"maxiter": 200})
            if -r.fun > best.ll:
                th = r.x
                best = Fit(q_c=float(np.exp(th[0])), q_d=float(np.exp(th[1])), rho=float(th[2]), b=b,
                           tau2=float(np.exp(th[3])) if spec.tau else 0.0,
                           q_g=float(np.exp(th[4])) if spec.trend else 0.0, phi=spec.phi if spec.trend else 0.0,
                           ll=float(-r.fun))
    return best


PRIOR_SD = 1.0      # protocol: beta ~ N(0, 1^2) pp per SD per quarter (changed only by the sensitivity diagnostic)


def fit_beta(Y, R, t_idx, brk, base: Fit, Z, w, groups: tuple, prior_sd: float | None = None, asym: bool = False) -> Fit:
    """Penalized ML for the sign-constrained driver coefficients with the variances of `base` held fixed."""
    if not groups:
        return base
    prior_sd = PRIOR_SD if prior_sd is None else prior_sd

    def obj(bv):
        f = Fit(**{**base.__dict__, "beta": dict(zip(groups, bv)), "asym": asym})
        return -kfilter(Y, R, t_idx, f, brk, Z, w)[2] + 0.5 * float(np.sum(np.square(bv))) / prior_sd ** 2

    r = minimize(obj, np.full(len(groups), 0.1), method="L-BFGS-B", bounds=[(0.0, 10.0)] * len(groups))
    out = Fit(**{**base.__dict__, "beta": dict(zip(groups, map(float, r.x))), "asym": asym})
    out.ll = -float(r.fun)
    return out


def design_effect(innov: dict, brk: int, shrink: float = 2.0) -> dict:
    """E132 SEAS rule on pooled one-step innovations after the break: mean by quarter-of-year shrunk n/(n+2)."""
    res = {q: [] for q in range(4)}
    for (t, a), v in innov.items():
        if t >= brk:
            res[t % 4].append(v)
    return {q: (sum(v) / (len(v) + shrink)) for q, v in res.items()}
