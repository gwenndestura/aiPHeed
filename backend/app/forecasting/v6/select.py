"""
v6 walk-forward forecasts for the pre-registered candidates (PERSIST, LL-K from the v2 walk-forward; LGBM-D and LGBM-D-S
fitted at each issue I on lead-k rows of earlier issues whose truth is known at I) and the inner-fold selection rule.
History features (last change, deviation from the expanding mean) are computed with as_of at each row's own issue.
"""
from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from app.forecasting import sws as T
from app.forecasting.v2 import select as S2
from app.forecasting.v4 import features as F
from app.forecasting.v6 import lgbm as LG

CANDIDATES = ("PERSIST", "LL-K", "LGBM-D", "LGBM-D-S")


def history(rr: pd.DataFrame, issue: str) -> pd.DataFrame:
    k = T.known_at(rr, date.fromisoformat(issue))
    out = []
    for a, g in k.sort_values("qi").groupby("area"):
        y = g.y.to_numpy()
        out.append({"area": a, "last_change": float(y[-1] - y[-2]) if len(y) > 1 else 0.0, "dev_mean": float(y[-1] - y.mean())})
    return pd.DataFrame(out).assign(issue=issue)


def rows_at(rr, feats, wf, issue: str, lead: int, hist_cache: dict) -> pd.DataFrame:
    base = wf[(wf.issue == issue) & (wf.model == "PERSIST") & (wf.lead == lead)][["issue", "area", "lead", "tqi", "h", "f", "sd",
                                                                                     "latest", "latest_qi", "n_obs", "q", "kappa",
                                                                                     "noise_adjustment"]]
    if base.empty:                      # no round published yet at this issue
        return base
    if issue not in hist_cache:
        hist_cache[issue] = history(rr, issue)
    snap = F.snapshot(feats, issue, used_at=issue).reset_index()[["area", *F.FEATURES]]
    return base.merge(hist_cache[issue], on=["issue", "area"]).merge(snap, on="area", how="left")


def training(rr, feats, wf, I: date, lead: int, hist_cache: dict, exclude_area: str | None = None,
             min_issue: str | None = None) -> pd.DataFrame:
    g = S2.inner_rows(wf[wf.model == "PERSIST"], rr, I, lead)
    if exclude_area:
        g = g[g.area != exclude_area]
    if min_issue:
        g = g[g.issue >= min_issue]
    if g.empty:
        return pd.DataFrame()
    parts = [rows_at(rr, feats, wf, j, lead, hist_cache) for j in sorted(g.issue.unique())]
    X = pd.concat(parts, ignore_index=True)
    X = X.merge(g[["issue", "area", "y"]], on=["issue", "area"])
    return X.assign(change=X.y - X.f)


def lgbm_at(rr, feats, wf, I: date, hist_cache: dict, exclude_area: str | None = None, min_issue: str | None = None,
            keep_fits: dict | None = None) -> pd.DataFrame:
    out = []
    for k in S2.LEADS:
        fit = LG.fit(training(rr, feats, wf, I, k, hist_cache, exclude_area, min_issue))
        if keep_fits is not None:
            keep_fits[k] = fit
        X = rows_at(rr, feats, wf, I.isoformat(), k, hist_cache)
        if X.empty:
            continue
        chg, contrib = LG.predict(fit, X)
        for (_, r), c, ex in zip(X.iterrows(), chg, contrib):
            for name, w in (("LGBM-D", 1.0), ("LGBM-D-S", fit.w)):
                out.append({"issue": r.issue, "area": r.area, "lead": k, "tqi": r.tqi, "n_obs": r.n_obs, "q": r.q,
                            "kappa": r.kappa, "latest": r.latest, "sd": r.sd, "h": r.h, "latest_qi": r.latest_qi,
                            "noise_adjustment": 0.0, "model": name, "anchor": r.f, "predicted_change": w * c,
                            "f": r.f + w * c, "w": w, "features": json.dumps(fit.features), "exog": json.dumps(fit.exog),
                            "best_iter": fit.best_iter, "n_train": fit.n_train,
                            "train_mae": fit.train_mae if name == "LGBM-D" else fit.train_mae_s,
                            "contributions": json.dumps({g: round(w * v, 8) for g, v in ex.items()})})
    return pd.DataFrame(out)


def walk_forward(rr, feats, last: date, wf2: pd.DataFrame | None = None, start_issue: str | None = None) -> pd.DataFrame:
    wf2 = S2.walk_forward(rr, last) if wf2 is None else wf2
    base = wf2[wf2.model.isin(["PERSIST", "LL-K"])].copy()
    base["predicted_change"], base["anchor"] = 0.0, base["f"]
    cache: dict = {}
    d = pd.concat([lgbm_at(rr, feats, wf2, i, cache, min_issue=start_issue) for i in S2.issues(last)], ignore_index=True)
    return pd.concat([base, d], ignore_index=True)


def select(wf: pd.DataFrame, rr: pd.DataFrame, I: date) -> tuple[str, list[dict]]:
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
