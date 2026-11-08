"""
v4 walk-forward forecasts for the 4 pre-registered candidates and the inner-fold selection rule (PREREGISTRATION
sections 2-4). PERSIST and LL-K come from the v2 walk-forward (parameters fitted at each issue); DELTA-X and DELTA-X-LLK
are fitted at each issue I on lead-k rows of earlier issues whose truth is known at I, with each row's own feature
snapshot, and predict from the snapshot of I.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from app.forecasting import sws as T
from app.forecasting.v2 import select as S2
from app.forecasting.v4 import features as F
from app.forecasting.v4 import models as DX

CANDIDATES = ("PERSIST", "LL-K", "DELTA-X", "DELTA-X-LLK")
ANCHOR = {"DELTA-X": "PERSIST", "DELTA-X-LLK": "LL-K"}


def training_rows(wf: pd.DataFrame, rr: pd.DataFrame, feats: pd.DataFrame, I: date, lead: int, anchor: str,
                  exclude_area: str | None = None) -> pd.DataFrame:
    g = S2.inner_rows(wf[wf.model == anchor], rr, I, lead)
    if exclude_area:
        g = g[g.area != exclude_area]
    if g.empty:
        return g.assign(change=[])
    g = g.assign(change=g.y - g.f)
    snaps = pd.concat([F.snapshot(feats, j, used_at=j).reset_index().assign(issue=j) for j in g.issue.unique()])
    return g.merge(snaps[["issue", "area", *F.FEATURES]], on=["issue", "area"], how="left")


def delta_at(wf: pd.DataFrame, rr: pd.DataFrame, feats: pd.DataFrame, I: date, exclude_area: str | None = None) -> pd.DataFrame:
    snap = F.snapshot(feats, I.isoformat(), used_at=I.isoformat())
    out = []
    for model, anchor in ANCHOR.items():
        for k in S2.LEADS:
            p = DX.fit_delta(training_rows(wf, rr, feats, I, k, anchor, exclude_area))
            base = wf[(wf.issue == I.isoformat()) & (wf.model == anchor) & (wf.lead == k)]
            for r in base.itertuples():
                chg, contrib = DX.predict_delta(p, snap.loc[r.area] if r.area in snap.index else pd.Series(dtype=float))
                out.append({**{c: getattr(r, c) for c in ("issue", "area", "lead", "tqi", "n_obs", "q", "kappa", "latest",
                                                          "sd", "h", "latest_qi")},
                            "model": model, "anchor": float(r.f), "f": float(r.f) + chg, "noise_adjustment": r.noise_adjustment,
                            "predicted_change": chg, "features": json.dumps(p.features),
                            "contributions": json.dumps({k_: round(v, 6) for k_, v in contrib.items()}),
                            "n_train": p.n_train})
    return pd.DataFrame(out)


def walk_forward(rr: pd.DataFrame, feats: pd.DataFrame, last: date, wf2: pd.DataFrame | None = None) -> pd.DataFrame:
    wf2 = S2.walk_forward(rr, last) if wf2 is None else wf2
    base = wf2[wf2.model.isin(["PERSIST", "LL-K"])].copy()
    base["predicted_change"] = 0.0
    base["anchor"] = base["f"]
    d = pd.concat([delta_at(wf2, rr, feats, i) for i in S2.issues(last)], ignore_index=True)
    return pd.concat([base, d], ignore_index=True)


def select(wf: pd.DataFrame, rr: pd.DataFrame, I: date) -> tuple[str, list[dict]]:
    """Incumbent PERSIST; challengers in CANDIDATES order replace it only with a paired 95 % CI of the Lead-2 within
    difference entirely above 0 on >= 6 inner target quarters (frozen tolerance)."""
    g = S2.inner_rows(wf, rr, I, 2)
    w = {m: g[g.model == m].sort_values(["tqi", "area", "issue"]).reset_index(drop=True) for m in CANDIDATES}
    nq = int(w["PERSIST"]["tqi"].nunique()) if len(w["PERSIST"]) else 0
    inc, log = "PERSIST", []
    for m in CANDIDATES[1:]:
        a, b = w[m], w[inc]
        if nq < S2.MIN_INNER_QUARTERS or len(a) != len(b):
            log.append({"issue": I.isoformat(), "challenger": m, "incumbent": inc, "inner_quarters": nq, "replaces": False,
                        "diff_within": np.nan, "ci_lo": np.nan, "ci_hi": np.nan})
            continue
        wa = (np.abs(a.f - a.y) <= T.Z90 * a.se).to_numpy()
        wb = (np.abs(b.f - b.y) <= T.Z90 * b.se).to_numpy()
        lo, hi = S2.paired_ci(wa, wb, a.tqi.to_numpy())
        rep = bool(lo > 0)
        log.append({"issue": I.isoformat(), "challenger": m, "incumbent": inc, "inner_quarters": nq, "replaces": rep,
                    "diff_within": float(wa.mean() - wb.mean()), "ci_lo": lo, "ci_hi": hi})
        if rep:
            inc = m
    return inc, log
