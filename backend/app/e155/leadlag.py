"""
E155 lead-lag check: for known shocks, when did news first show it, and when did official data first show it, by publication date? Reads no food-insecurity outcome. Only months up to 2025-06 are read from CPI.

Signal rule, fixed before looking: a series "shows" a shock on the first date in the event window where it exceeds its own mean over the previous 24 months by 2 standard deviations.
News: 30-day rolling share, dated by publication. Official: CPI by month, dated by an assumed release on the 5th of the next month; quarterly farm output dated 45 days after the quarter; LFS round dated 40 days after the survey month.
These release delays are approximations, because past release dates are not held.

    python -m app.e155.leadlag -> data/e155/out/leadlag.json
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from app.e151 import RAW as R151
from app.e151.topics import event_probs
from app.e155.audit import LEX, OUT, SUN
from app.paths import BACKEND_DIR

CPI = BACKEND_DIR / "data" / "e150" / "raw" / "cpi_monthly.csv"
GD = BACKEND_DIR.parent.parent / "aipheed_final" / "aipheed-backend-aligned" / "experiments" / "E114_Final_Run" / "data" / "cov_gdelt_doc.csv"
END = pd.Timestamp("2025-06-30")
EVENTS = {
    "2018 rice price surge": ("2018-05-01", "2018-12-31", "price"),
    "2023 rice price surge": ("2023-06-01", "2023-12-31", "price"),
    "2020 COVID job losses": ("2020-02-01", "2020-08-31", "jobs"),
    "2021 Typhoon Odette (landfall 2021-12-16)": ("2021-11-15", "2022-03-31", "disaster"),
    "2024 Typhoon Kristine (landfall 2024-10-24)": ("2024-09-25", "2025-02-28", "disaster"),
}


def first_signal(s: pd.Series, lo, hi, base_days=730):
    """First date in [lo, hi] where s exceeds mean + 2 sd of the previous base window."""
    s = s.dropna().sort_index()
    for d in s.index[(s.index >= pd.Timestamp(lo)) & (s.index <= pd.Timestamp(hi))]:
        b = s[(s.index < d - pd.Timedelta(days=30)) & (s.index >= d - pd.Timedelta(days=base_days))]
        if len(b) > 10 and b.std() > 0 and s[d] > b.mean() + 2 * b.std():
            return d
    return None


def news_series():
    out = {}
    st = pd.read_parquet(R151 / "stories.parquet", columns=["story", "published", "hash", "geo_level"]).drop_duplicates("story")
    st = st[st["geo_level"] != "international"].merge(event_probs(), on="hash")
    st["price"] = st["pr_purchasing"] + st["pr_supply"]
    st["jobs"] = st["pr_income"]
    st["disaster"] = st["pr_climate"] + st["pr_agri_loss"]
    st = st[st["published"] <= END].set_index("published").sort_index()
    for c in ("price", "jobs", "disaster"):
        out[f"archive_{c}"] = st[c].resample("D").mean().rolling(30, min_periods=10).mean()
    d = pd.read_parquet(SUN)
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["date"] <= END]
    for c in ("price", "jobs", "disaster"):
        d[c] = d["title"].str.contains(LEX[c], flags=re.I, regex=True).astype(float)
        out[f"sunstar_{c}"] = d.groupby("date")[c].mean().asfreq("D").rolling(30, min_periods=10).mean()
    if GD.exists():
        g = pd.read_csv(GD)
        g["Date"] = pd.to_datetime(g["Date"])
        g = g[g["Date"] <= END]
        for c, cat in (("price", "shortage"), ("jobs", "jobs_income"), ("disaster", "agri_supply")):
            out[f"gdelt_{c}"] = g[g["category"] == cat].set_index("Date")["Value"].sort_index().rolling(30, min_periods=10).mean()
    return out


def official_series():
    c = pd.read_csv(CPI)
    c = c[c["year"].astype(int) <= 2025]
    months = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    c = c[c["period"].isin(months)].copy()
    c["month"] = pd.to_datetime(dict(year=c["year"].astype(int), month=c["period"].map(months), day=1))
    c = c[c["month"] <= END]
    out = {}
    for name, rx in (("price", r"rice"), ("food", r"food and non-alcoholic|^food")):
        x = c[c["commodity_text"].str.contains(rx, case=False, regex=True)]
        # one base year at a time: mixing bases breaks the year-on-year change; the newest base wins where both exist
        parts = []
        for _, g in x.groupby("base"):
            m = g.groupby("month")["value"].mean().sort_index()
            parts.append(100 * (m / m.shift(12) - 1))
        yoy = pd.concat(parts).dropna()
        yoy = yoy[~yoy.index.duplicated(keep="last")].sort_index()
        rel = yoy.index + pd.offsets.MonthBegin(1) + pd.Timedelta(days=4)
        out[f"cpi_{name}"] = pd.Series(yoy.values, index=rel)
    return out


def main():
    N, O = news_series(), official_series()
    res = {"rule": "first date the series exceeds its previous-24-month mean by 2 standard deviations; official series dated by assumed release", "events": {}}
    for ev, (lo, hi, kind) in EVENTS.items():
        r = {}
        for k, s in N.items():
            if k.endswith(kind):
                d = first_signal(s, lo, hi)
                r[k] = None if d is None else str(d.date())
        if kind == "price":
            d = first_signal(O["cpi_price"], lo, hi)
            r["official_cpi_rice_release"] = None if d is None else str(d.date())
        elif kind == "jobs":
            r["official_lfs_release"] = "2020-06-05 (April 2020 round; approximate)"
        else:
            q_end = pd.Timestamp(lo).to_period("Q").end_time.normalize() + pd.offsets.QuarterEnd(0)
            r["official_quarterly_farm_output_release"] = f"{(pd.Timestamp(hi).to_period('Q').start_time - pd.Timedelta(days=1) + pd.Timedelta(days=45)).date()} or later (approximate)"
        res["events"][ev] = r
    (OUT / "leadlag.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
