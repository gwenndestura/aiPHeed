"""
v2 candidate models (docs/aipheed/v2/PREREGISTRATION.md section 1.1). Delta form: forecast = latest reading + a
noise-filter adjustment + zero predicted change beyond the anchor.

PERSIST  latest quarter value known at the issue
LL       pooled local level, observation variance SE_t^2 (the frozen binomial quarter SE); 1 parameter (q)
LL-K     as LL with observation variance kappa * SE_t^2; 2 parameters (q, kappa)

fit() estimates the parameters by pooled maximum likelihood on the quarter table known at a cutoff; forecast() only
runs the filter with given parameters (inference never re-estimates).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from app.forecasting.evidence import AREAS
from app.forecasting.models import S2_GRID, T0

CANDIDATES = ("PERSIST", "LL", "LL-K")          # simplest first
N_PARAMS = {"PERSIST": 0, "LL": 1, "LL-K": 2}
KAPPA_GRID = (1.0, 1.5, 2.0, 3.0, 4.0, 6.0)
Z80 = 1.2815515655446004


@dataclass(frozen=True)
class Params:
    model: str
    q: float          # true-level innovation variance per quarter (pp^2); for PERSIST the LL value, used for its sd only
    kappa: float      # observation-variance multiplier on SE^2 (1 for PERSIST and LL)
    upto: int         # last quarter index used to estimate
    loglik: float

    def as_dict(self) -> dict:
        return asdict(self)


def series(qt: pd.DataFrame, area: str, upto: int, start: int = T0):
    s = qt[(qt.area == area) & (qt.qi <= upto) & (qt.qi >= start)].set_index("qi")
    idx = np.arange(start, upto + 1)
    return idx, s["y"].reindex(idx).to_numpy(float), (s["se"] ** 2).reindex(idx).to_numpy(float)


def kalman(y, R, q, kappa):
    """Local-level filter with a diffuse start at the first observation; missing quarters only add q.
    Returns (level, P, loglik, one-step innovations)."""
    mu, P, ll, started, innov = None, None, 0.0, False, []
    for yt, rt in zip(y, R):
        if not started:
            if yt == yt:
                mu, P, started = yt, kappa * rt, True
            continue
        P = P + q
        if yt == yt:
            S = P + kappa * rt
            ll += -0.5 * (np.log(2 * np.pi * S) + (yt - mu) ** 2 / S)
            innov.append(yt - mu)
            K = P / S
            mu, P = mu + K * (yt - mu), (1 - K) * P
    return mu, P, ll, innov


def _data(qt: pd.DataFrame, start: int = T0) -> dict:
    upto = int(qt["qi"].max())
    return {a: series(qt, a, upto, start) for a in AREAS if (qt.area == a).any()}


def fit(model: str, qt: pd.DataFrame, start: int = T0) -> Params:
    if model not in CANDIDATES:
        raise ValueError(f"unknown v2 candidate {model}")
    data = _data(qt, start)
    kappas = KAPPA_GRID if model == "LL-K" else (1.0,)
    best = (-np.inf, None, None)
    for kappa in kappas:                       # ties: the first (smaller kappa, then smaller q) is kept
        for q in S2_GRID:
            ll = sum(kalman(d[1], d[2], q, kappa)[2] for d in data.values())
            if ll > best[0] + 1e-12:
                best = (ll, float(q), float(kappa))
    return Params(model, best[1], best[2], int(qt["qi"].max()), float(best[0]))


def forecast(qt: pd.DataFrame, p: Params, target: int, start: int = T0) -> dict:
    """Per area: score, latest reading, noise-filter adjustment (score - latest), model sd, horizon."""
    data = _data(qt, start)
    out = {}
    for a, (idx, y, R) in data.items():
        obs = np.where(~np.isnan(y))[0]
        if not len(obs):
            continue
        last = obs[-1]
        latest = float(y[last])
        mu, P, _, _ = kalman(y[: last + 1], R[: last + 1], p.q, 1.0 if p.model == "PERSIST" else p.kappa)
        h = int(target - idx[last])
        level = latest if p.model == "PERSIST" else float(mu)
        sd = float(np.sqrt(P + h * p.q + p.kappa * np.nanmedian(R)))
        out[a] = {"f": level, "latest": latest, "noise_adjustment": level - latest, "predicted_change": 0.0,
                  "sd": sd, "h": h, "latest_qi": int(idx[last])}
    return out


def training_mae(qt: pd.DataFrame, p: Params, start: int = T0) -> float:
    """In-sample one-step error at the fitted parameters (PERSIST: consecutive-observation change)."""
    errs = []
    for idx, y, R in _data(qt, start).values():
        if p.model == "PERSIST":
            v = y[~np.isnan(y)]
            errs += list(np.diff(v))
        else:
            errs += kalman(y, R, p.q, p.kappa)[3]
    return float(np.mean(np.abs(errs))) if errs else float("nan")
