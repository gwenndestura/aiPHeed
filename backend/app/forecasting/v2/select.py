"""
v2 walk-forward forecasts, nested inner-fold selection and split-conformal intervals
(docs/aipheed/v2/PREREGISTRATION.md sections 2-3). Every quantity at issue I uses only rounds published before I:
inner forecasts at an earlier issue J use parameters estimated at J, and inner truth is the target value known at I.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from app.forecasting import sws as T
from app.forecasting.models import T0
from app.forecasting.v2 import models as V

LEADS = (1, 2, 3, 4)
SEED = 2026
INNER_DRAWS = 2000
MIN_INNER_QUARTERS = 6
INNER_MIN_NOBS = 4
MIN_CONFORMAL = 8
FIRST_ISSUE = "2021-Q3"


def issue_of(D: int) -> date:
    return date(D // 4, 3 * (D % 4) + 1, 1)


def dashboard_quarter(issue: date) -> int:
    return T.qi(f"{issue.year}-Q{(issue.month - 1) // 3 + 1}")


def issues(last: date) -> list[date]:
    return [issue_of(D) for D in range(T.qi(FIRST_ISSUE), dashboard_quarter(last) + 1)]


def forecasts_at(rr: pd.DataFrame, issue: date, models=V.CANDIDATES, start: int = T0, params: dict | None = None) -> pd.DataFrame:
    """Leads 1-4 for every candidate from data known at the issue (parameters fitted there unless given)."""
    known = T.known_at(rr, issue)
    known = known[known.qi >= start]
    if known.empty:
        return pd.DataFrame()
    D = dashboard_quarter(issue)
    nobs = known.groupby("area").size()
    out = []
    for m in models:
        p = params[m] if params else V.fit(m, known, start)
        for k in LEADS:
            fc = V.forecast(known, p, D - 1 + k, start)
            for a, r in fc.items():
                out.append({"issue": issue.isoformat(), "area": a, "lead": k, "tqi": D - 1 + k, "model": m,
                            "n_obs": int(nobs[a]), "q": p.q, "kappa": p.kappa, **r})
    return pd.DataFrame(out)


def walk_forward(rr: pd.DataFrame, last: date, start: int = T0) -> pd.DataFrame:
    return pd.concat([forecasts_at(rr, i, start=start) for i in issues(last)], ignore_index=True)


def truth_known_at(rr: pd.DataFrame, cutoff: date) -> pd.DataFrame:
    """Target values as known at the cutoff (rounds published strictly before it)."""
    return T.known_at(rr, cutoff)[["area", "qi", "y", "se"]].rename(columns={"qi": "tqi"})


def inner_rows(wf: pd.DataFrame, rr: pd.DataFrame, I: date, lead: int) -> pd.DataFrame:
    g = wf[(wf.issue < I.isoformat()) & (wf.lead == lead) & (wf.n_obs >= INNER_MIN_NOBS)]
    return g.merge(truth_known_at(rr, I), on=["area", "tqi"], how="inner")


def paired_ci(a: np.ndarray, b: np.ndarray, clusters: np.ndarray, draws: int = INNER_DRAWS, seed: int = SEED):
    """95 % CI of mean(a - b) resampling whole clusters (target quarters) with replacement."""
    d = pd.Series(np.asarray(a, float) - np.asarray(b, float)).groupby(np.asarray(clusters)).agg(["sum", "count"])
    s, c = d["sum"].to_numpy(), d["count"].to_numpy()
    idx = np.random.default_rng(seed).integers(0, len(d), size=(draws, len(d)))
    boot = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    return float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


def select(wf: pd.DataFrame, rr: pd.DataFrame, I: date) -> tuple[str, list[dict]]:
    """Pre-registered rule: PERSIST is the incumbent; a challenger replaces it only if the paired block-bootstrap
    95 % CI of the Lead-2 within-tolerance difference lies entirely above 0 on >= 6 inner target quarters."""
    g = inner_rows(wf, rr, I, 2)
    w = {m: g[g.model == m].sort_values(["tqi", "area", "issue"]) for m in V.CANDIDATES}
    nq = int(w["PERSIST"]["tqi"].nunique()) if len(w["PERSIST"]) else 0
    inc, log = "PERSIST", []
    for m in V.CANDIDATES[1:]:
        a, b = w[m], w[inc]
        if nq < MIN_INNER_QUARTERS or len(a) != len(b):
            log.append({"issue": I.isoformat(), "challenger": m, "incumbent": inc, "inner_rows": len(a), "inner_quarters": nq,
                        "diff_within": np.nan, "ci_lo": np.nan, "ci_hi": np.nan, "replaces": False})
            continue
        wa = (np.abs(a.f - a.y) <= T.Z90 * a.se).to_numpy()
        wb = (np.abs(b.f.to_numpy() - b.y.to_numpy()) <= T.Z90 * b.se.to_numpy())
        lo, hi = paired_ci(wa, wb, a.tqi.to_numpy())
        rep = bool(lo > 0)
        log.append({"issue": I.isoformat(), "challenger": m, "incumbent": inc, "inner_rows": len(a), "inner_quarters": nq,
                    "diff_within": float(wa.mean() - wb.mean()), "ci_lo": lo, "ci_hi": hi, "replaces": rep})
        if rep:
            inc = m
    return inc, log


def conformal_halfwidth(wf: pd.DataFrame, rr: pd.DataFrame, I: date, model: str, lead: int) -> tuple[float | None, int]:
    g = inner_rows(wf, rr, I, lead)
    r = np.sort(np.abs(g[g.model == model].f - g[g.model == model].y).to_numpy())
    n = len(r)
    if n < MIN_CONFORMAL:
        return None, n
    return float(r[int(np.ceil(0.8 * (n + 1))) - 1]), n


def interval(f: float, sd: float, half: float | None) -> tuple[float, float, str]:
    if half is None:
        return f - V.Z80 * sd, f + V.Z80 * sd, "gaussian (fewer than 8 inner residuals)"
    return f - half, f + half, "split-conformal (inner walk-forward residuals)"
