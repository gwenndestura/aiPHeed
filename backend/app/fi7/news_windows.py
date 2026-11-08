"""FI6-N news features over the 90 days before any issue date (no rescoring: reads the cached FI6-N articles/events).

For each issue date d the window is (d - 90 days, d]. Same definitions as FI6-N quarterly features:
    risk_share_<domain>   unique risk-increasing events (direction harder > easier; restated official statistics
                          excluded; CALABARZON-located for climate/employment/poverty, any location for market and
                          remittance) / articles collected in the window (CALABARZON-located or all, respectively);
                          NaN when the denominator has fewer than 30 articles
    climate_damage_log    log(1 + P million agricultural/climate damage in CALABARZON climate events)
    displaced_families_log
Also two forward-looking variants used only in the early-warning experiment:
    escalation_<domain>   risk_share in the last 45 days minus the previous 45 days (is it getting worse?)
    persistence_<domain>  share of the window's 3 months (30-day blocks) with at least one risk event
Output: data/fi7/news_windows.csv (one row per issue date; no article text).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5.nlp import DOMAINS
from app.fi6.news_events import ARTICLES, EVENTS, LOCAL
from app.fi7.paths import FI7

OUT = FI7 / "news_windows.csv"
WINDOW_DAYS = 90
MIN_ARTICLES = 30


def _shares(a: pd.DataFrame, ev: pd.DataFrame, lo: pd.Timestamp, hi: pd.Timestamp) -> dict:
    aw = a[(a["published"] > lo) & (a["published"] <= hi)]
    den_local, den_all = int(aw["geo_level"].isin(LOCAL).sum()), int(len(aw))
    e = ev[(ev["published"] > lo) & (ev["published"] <= hi)]
    r = {"articles_window": den_all}
    for d in DOMAINS:
        national_ok = d in ("market", "remittance")
        sc = e[e[f"is_{d}"] & (national_ok | e["geo_level"].isin(LOCAL))]
        den = den_all if national_ok else den_local
        r[f"risk_share_{d}"] = sc["event_id"].nunique() / den if den >= MIN_ARTICLES else np.nan
    return r


def build(issue_dates: list[pd.Timestamp]) -> pd.DataFrame:
    a = pd.read_parquet(ARTICLES, columns=["site", "wp_id", "published", "geo_level"])
    ev = pd.read_parquet(EVENTS)
    ev = ev[~ev["restated_statistic"] & (ev["p_harder"].fillna(0) > ev["p_easier"].fillna(0))]
    rows = []
    for d in sorted(set(issue_dates)):
        d = pd.Timestamp(d)
        lo = d - pd.Timedelta(days=WINDOW_DAYS)
        r = {"issue_date": d.date().isoformat(), **_shares(a, ev, lo, d)}
        loc = ev[(ev["published"] > lo) & (ev["published"] <= d) & ev["geo_level"].isin(LOCAL)].drop_duplicates("event_id")
        ok = r["articles_window"] >= MIN_ARTICLES
        r["climate_damage_log"] = float(np.log1p(loc[loc["is_climate"]]["damage_pmillion"].sum())) if ok else np.nan
        r["displaced_families_log"] = float(np.log1p(loc["families_affected"].sum())) if ok else np.nan
        mid = d - pd.Timedelta(days=WINDOW_DAYS // 2)
        recent, earlier = _shares(a, ev, mid, d), _shares(a, ev, lo, mid)
        for dmn in DOMAINS:
            r[f"escalation_{dmn}"] = recent[f"risk_share_{dmn}"] - earlier[f"risk_share_{dmn}"]
            blocks = [ev[(ev["published"] > d - pd.Timedelta(days=30 * (k + 1))) & (ev["published"] <= d - pd.Timedelta(days=30 * k))
                         & ev[f"is_{dmn}"]] for k in range(3)]
            r[f"persistence_{dmn}"] = float(np.mean([len(b) > 0 for b in blocks])) if ok else np.nan
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False, lineterminator="\n")
    return out
