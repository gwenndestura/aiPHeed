"""
Forecast models for the SWS area target (numerical hunger %, Leads 1-4).

PERSIST   the latest published quarter value
TREND-D   latest + 0.5 x (latest - previous published quarter); fixed, no fitting (E136)
SEAS-LLM  measurement-aware local level (observation variance = each quarter's sampling SE^2), extra level variance at
          the documented 2025-Q2 respondent-base break, pooled quarter-of-year design effect learned from post-break
          one-step innovations and shrunk n/(n+2). Faithful port of E132 runner/e132_run.py (seas_fit/seas_forecast);
          equality is tested (tests/unit/test_forecasting_core.py).

fit_seas() estimates the 3 quantities (s2, b, quarter effects) from data known at a training cutoff; forecast_seas()
uses given parameters and only runs the filter (no re-estimation), so inference can apply a frozen artifact.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.forecasting.evidence import AREAS
from app.forecasting.sws import qi

T0 = qi("2021-Q2")
BREAK = qi("2025-Q2")
S2_GRID = np.exp(np.linspace(np.log(0.05), np.log(80), 60))
B_GRID = (0.0, 4.0, 9.0, 16.0, 25.0, 49.0)
Z80 = 1.2815515655446004


def series(qt: pd.DataFrame, area: str, upto: int):
    s = qt[(qt.area == area) & (qt.qi <= upto)].set_index("qi")
    idx = np.arange(T0, upto + 1)
    return idx, s["y"].reindex(idx).to_numpy(float), (s["se"] ** 2).reindex(idx).to_numpy(float)


def _kf_break(y, R, s2, bvar, idx, out_innov=False):
    mu, P, ll, started, innov = None, None, 0.0, False, {}
    for t, yt, rt in zip(idx, y, R):
        if not started:
            if yt == yt:
                mu, P, started = yt, rt, True
            continue
        P = P + s2 + (bvar if t == BREAK else 0.0)
        if yt == yt:
            S = P + rt
            ll += -0.5 * (np.log(2 * np.pi * S) + (yt - mu) ** 2 / S)
            innov[t] = yt - mu
            K = P / S
            mu, P = mu + K * (yt - mu), (1 - K) * P
    return (mu, P, ll, innov) if out_innov else (mu, P, ll)


@dataclass
class SeasParams:
    s2: float
    b: float
    seas: dict = field(default_factory=dict)     # quarter-of-year (0-3) -> effect, post-break only
    upto: int = 0                                # last quarter index used to estimate


def _best(data):
    best = (-np.inf, None, None)
    for b in B_GRID:
        for s2 in S2_GRID:
            ll = sum(_kf_break(data[a][1], data[a][2], s2, b, data[a][0])[2] for a in AREAS)
            if ll > best[0]:
                best = (ll, s2, b)
    return float(best[1]), float(best[2])


def fit_seas(qt: pd.DataFrame) -> SeasParams:
    """Pooled maximum likelihood on the quarter table known at the cutoff (E132 seas_fit)."""
    upto = int(qt["qi"].max())
    data = {a: series(qt, a, upto) for a in AREAS}
    s2, b = _best(data)
    resid = {q: [] for q in range(4)}
    for a in AREAS:
        idx, y, R = data[a]
        for t, v in _kf_break(y, R, s2, b, idx, out_innov=True)[3].items():
            if t >= BREAK:
                resid[t % 4].append(v)
    seas = {q: (sum(v) / (len(v) + 2)) for q, v in resid.items()}
    s2b, bb = _best(_adjust(data, seas))
    return SeasParams(s2b, bb, seas, upto)


def _adjust(data, seas):
    out = {}
    for a, (idx, y, R) in data.items():
        out[a] = (idx, np.array([yt - seas[t % 4] if (t >= BREAK and yt == yt) else yt for t, yt in zip(idx, y)]), R)
    return out


def forecast_seas(qt: pd.DataFrame, params: SeasParams, target: int) -> dict:
    """Filter the known data with fixed parameters and forecast the target quarter for each area."""
    upto = int(qt["qi"].max())
    data = _adjust({a: series(qt, a, upto) for a in AREAS}, params.seas)
    out = {}
    for a in AREAS:
        idx, y2, R = data[a]
        obs = np.where(~np.isnan(y2))[0]
        if not len(obs):
            continue
        mu, P, _ = _kf_break(y2[: obs[-1] + 1], R[: obs[-1] + 1], params.s2, params.b, idx[: obs[-1] + 1])
        h = target - idx[obs[-1]]
        extra = params.b if idx[obs[-1]] < BREAK <= target else 0.0
        effect = params.seas.get(target % 4, 0.0) if target >= BREAK else 0.0
        sd = float(np.sqrt(P + h * params.s2 + extra + np.nanmedian(R)))
        out[a] = {"f": float(mu + effect), "sd": sd, "level": float(mu), "design_effect": float(effect),
                  "h": int(h), "lo80": float(mu + effect - Z80 * sd), "hi80": float(mu + effect + Z80 * sd)}
    return out


def persistence(qt: pd.DataFrame) -> dict:
    return {a: float(qt[qt.area == a].sort_values("qi")["y"].iloc[-1]) for a in AREAS if (qt.area == a).any()}


def trend_d(qt: pd.DataFrame) -> dict:
    out = {}
    for a in AREAS:
        s = qt[qt.area == a].sort_values("qi")
        if s.empty:
            continue
        last = float(s["y"].iloc[-1])
        prev = float(s["y"].iloc[-2]) if len(s) > 1 else last
        out[a] = last + 0.5 * (last - prev)
    return out
