"""Timing-aware news features from the FI6-N archive (no rescoring; XLM-R scores are already stored per event).

For an issue date d, every window ends at d (articles and events published on or before d only):
    W30, W60, W90   the last 30 / 60 / 90 days
    QTD             quarter to date: from the first day of the issue quarter to d (the full quarter at quarter end)
    LCQ             the last quarter that had fully ended on or before d
    RW              90 days, each event and article weighted exp(-age_days / 30) (recency weighting)
Per window (unique events, restated official statistics removed, syndicated copies merged by event_id):
    dom_<domain>    risk-increasing events of the domain / articles (FI6-N definition; CALABARZON-located for
                    climate, employment and poverty, any location for market and remittance)
    hard, warn, resp, disr   share of articles that are hardship / warning / government-response / disruption events
                    (XLM-R type with the highest probability; hardship and disruption only when harder > easier)
    netdir          mean(p_harder - p_easier) over relevant events (>= 5 events)
    dmg, fam        log(1 + PHP million damage), log(1 + families affected), CALABARZON events
    vol             log(1 + articles in the window): media attention, kept to test attention vs conditions
Momentum: mom_hard = hard(W30) - hard(days 31-90); mom_dom = mean dom(W30) - mean dom(days 31-90).
A window with fewer than 30 articles gives NaN (coverage gap), never zero.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5.nlp import DOMAINS
from app.fi6.news_events import ARTICLES, EVENTS, LOCAL

MIN_ARTICLES, MIN_EVENTS = 30, 5
TYPES = {"hard": "p_hardship", "warn": "p_warning", "resp": "p_response", "disr": "p_disruption"}


def _load():
    a = pd.read_parquet(ARTICLES, columns=["published", "geo_level", "excluded"])
    a = a[~a["excluded"].fillna(False)]
    e = pd.read_parquet(EVENTS)
    e = e[~e["restated_statistic"] & e["relevant"].fillna(False)].copy()
    e["harder"] = e["p_harder"].fillna(0) > e["p_easier"].fillna(0)
    tp = e[list(TYPES.values())].fillna(0)
    e["etype"] = tp.idxmax(axis=1).map({v: k for k, v in TYPES.items()})
    e = e.sort_values("n_sources_event", ascending=False).drop_duplicates("event_id")      # one row per event
    return a, e


def _window(a, e, lo, hi, w_a=None, w_e=None) -> dict:
    ma = (a["published"] > lo) & (a["published"] <= hi)
    me = (e["published"] > lo) & (e["published"] <= hi)
    aw, ew = a[ma], e[me]
    wa = np.ones(len(aw)) if w_a is None else w_a[ma.to_numpy()]
    we = np.ones(len(ew)) if w_e is None else w_e[me.to_numpy()]
    n_all, n_loc = int(len(aw)), int(aw["geo_level"].isin(LOCAL).sum())
    den_all, den_loc = wa.sum(), wa[aw["geo_level"].isin(LOCAL).to_numpy()].sum()
    r = {"vol": float(np.log1p(n_all))}
    ok_all, ok_loc = n_all >= MIN_ARTICLES, n_loc >= MIN_ARTICLES
    local = ew["geo_level"].isin(LOCAL).to_numpy()
    for d in DOMAINS:
        national = d in ("market", "remittance")
        sel = ew[f"is_{d}"].to_numpy() & ew["harder"].to_numpy() & (national | local)
        ok, den = (ok_all, den_all) if national else (ok_loc, den_loc)
        r[f"dom_{d}"] = float(we[sel].sum() / den) if ok else np.nan
    for k in TYPES:
        sel = (ew["etype"] == k).to_numpy() & (ew["harder"].to_numpy() if k in ("hard", "disr") else True)
        r[k] = float(we[sel].sum() / den_all) if ok_all else np.nan
    r["netdir"] = float(np.average((ew["p_harder"].fillna(0) - ew["p_easier"].fillna(0)), weights=we)) if len(ew) >= MIN_EVENTS else np.nan
    loc = ew[local]
    r["dmg"] = float(np.log1p(loc.loc[loc["is_climate"], "damage_pmillion"].fillna(0).sum())) if ok_loc else np.nan
    r["fam"] = float(np.log1p(loc["families_affected"].fillna(0).sum())) if ok_loc else np.nan
    return r


def _q_start(d: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=d.year, month=3 * ((d.month - 1) // 3) + 1, day=1)


def features(issue_dates) -> pd.DataFrame:
    a, e = _load()
    rows = []
    for d in sorted({pd.Timestamp(x).normalize() for x in issue_dates}):
        r = {"issue_date": d}
        qs = _q_start(d)
        q_end_d = (qs + pd.DateOffset(months=3) - pd.Timedelta(days=1))
        lcq_end = q_end_d if d >= q_end_d else qs - pd.Timedelta(days=1)
        lcq_start = _q_start(lcq_end)
        wins = {"W30": (d - pd.Timedelta(days=30), d), "W60": (d - pd.Timedelta(days=60), d),
                "W90": (d - pd.Timedelta(days=90), d), "QTD": (qs - pd.Timedelta(seconds=1), d),
                "LCQ": (lcq_start - pd.Timedelta(seconds=1), lcq_end)}
        for name, (lo, hi) in wins.items():
            r.update({f"{k}_{name}": v for k, v in _window(a, e, lo, hi).items()})
        age_a = (d - a["published"]).dt.total_seconds().to_numpy() / 86400
        age_e = (d - e["published"]).dt.total_seconds().to_numpy() / 86400
        r.update({f"{k}_RW": v for k, v in _window(a, e, d - pd.Timedelta(days=90), d, np.exp(-age_a / 30), np.exp(-age_e / 30)).items()})
        old = _window(a, e, d - pd.Timedelta(days=90), d - pd.Timedelta(days=30))
        r["mom_hard"] = r["hard_W30"] - old["hard"]
        r["mom_dom"] = np.nanmean([r[f"dom_{x}_W30"] for x in DOMAINS]) - np.nanmean([old[f"dom_{x}"] for x in DOMAINS]) \
            if not (np.all(np.isnan([r[f"dom_{x}_W30"] for x in DOMAINS])) or np.all(np.isnan([old[f"dom_{x}"] for x in DOMAINS]))) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def expanding_z(df: pd.DataFrame, cols: list[str], min_hist: int = 8) -> pd.DataFrame:
    """z-score each column against its values at EARLIER issue dates only (rows must be sorted by issue date)."""
    out = pd.DataFrame(index=df.index)
    for c in cols:
        x = df[c].astype(float).to_numpy()
        z = np.full(len(x), np.nan)
        for i in range(len(x)):
            h = x[:i][~np.isnan(x[:i])]
            if not np.isnan(x[i]) and len(h) >= min_hist:
                sd = h.std(ddof=1)
                z[i] = (x[i] - h.mean()) / sd if sd > 0 else 0.0
        out[f"z_{c}"] = z
    return out
