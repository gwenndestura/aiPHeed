"""
E144 data: SWS area labels (2010+), national indicators (FI5 release rules) and GDELT area news, all as-of.

Quarter index qi = year*4 + quarter - 1 (app.fi5.target). Issue at the end of quarter i (d = q_end(i)); the dashboard
viewing quarter is i+1 and the target of horizon h is T = i+1+h.
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from app.e144 import RAW
from app.fi5 import sources as S
from app.fi5.features import _asof, _z_last
from app.fi5.target import BASELINE_Q, MIN_BASELINE_OBS, q_end, qindex, qlabel

AREAS = ["metro_manila", "balance_luzon", "visayas", "mindanao"]
FIRST_LABEL_QI = qindex("2010-Q1")
THEMES = ["market", "climate", "hunger", "jobs"]
NEWS_COLS = [f"news_share_{t}" for t in THEMES] + ["news_attention"]
NAT_COLS = ["oni", "unemp_rate", "unemp_yoy", "remit_yoy"]
HIST_COLS = ["hunger_last", "hunger_last_anom", "hunger_age_q"]


@lru_cache(maxsize=None)
def sws_quarterly() -> pd.DataFrame:
    """One row per area x quarter with a reading: hunger, published (last round of the quarter), qi."""
    r = S.sws_rounds()
    rows = []
    for a in AREAS:
        g = r.groupby("quarter").agg(hunger=(a, "mean"), published=("published", "max")).dropna(subset=["hunger"]).reset_index()
        g["area"], g["qi"] = a, g["quarter"].map(qindex)
        rows.append(g)
    d = pd.concat(rows, ignore_index=True)
    d["published"] = pd.to_datetime(d["published"])
    return d.sort_values(["area", "qi"]).reset_index(drop=True)


def label(area: str, qi: int) -> dict | None:
    """HIGH = hunger above the mean of the area's readings in quarters qi-20..qi-1 (>= 8 readings)."""
    s = sws_quarterly()
    s = s[s["area"] == area]
    cur = s[s["qi"] == qi]
    if cur.empty:
        return None
    win = s[(s["qi"] >= qi - BASELINE_Q) & (s["qi"] < qi)]["hunger"]
    if len(win) < MIN_BASELINE_OBS:
        return None
    h = float(cur["hunger"].iloc[0])
    return {"hunger": h, "baseline": float(win.mean()), "high": int(h > win.mean()), "published": cur["published"].iloc[0]}


def history(area: str, d: pd.Timestamp, target_qi: int) -> dict:
    s = sws_quarterly()
    s = s[(s["area"] == area) & (s["published"] <= d)]
    if s.empty:
        return {}
    last = s.iloc[-1]
    win = s[(s["qi"] >= target_qi - BASELINE_Q) & (s["qi"] < target_qi)]["hunger"]
    base = win.mean() if len(win) >= MIN_BASELINE_OBS else s["hunger"].iloc[-BASELINE_Q:].mean()
    return {"hunger_last": float(last["hunger"]), "hunger_last_anom": float(last["hunger"] - base),
            "hunger_age_q": int(target_qi - last["qi"]), "baseline_asof": float(base), "last_qi": int(last["qi"])}


@lru_cache(maxsize=None)
def _national():
    return S.oni(), S.lfs(), S.remittances()


def national(d: pd.Timestamp) -> dict:
    oni, lfs, rem = _national()
    out = {}
    o = _asof(oni, d)
    if len(o):
        out["oni"] = float(o["oni"].iloc[-1])
    e = _asof(lfs, d)
    if len(e):
        out["unemp_rate"], out["unemp_yoy"] = float(e["unemp_rate"].iloc[-1]), float(e["unemp_yoy"].iloc[-1])
    m = _asof(rem, d)
    if len(m):
        out["remit_yoy"] = float(m["remit_yoy"].iloc[-1])
    return out


# ---------------------------------------------------------------------------------------------------------- news
@lru_cache(maxsize=None)
def news_quarterly() -> pd.DataFrame:
    """Area x quarter news from the E144-P2 Google News RSS collection (data/e144/raw/gnews/items.jsonl): unique credible
    items per theme, theme shares of the area's food-security coverage, and attention = log(1 + unique items)."""
    rows = [json.loads(l) for l in (RAW / "gnews" / "items.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    it = pd.DataFrame(rows).drop_duplicates(["area", "theme", "link"])
    ws = pd.to_datetime(it["window_start"])
    it["qi"] = ws.dt.year * 4 + (ws.dt.month - 1) // 3
    qs = range(qindex("2021-Q1"), qindex("2026-Q3") + 1)
    out = []
    for a in AREAS:
        g = it[it["area"] == a]
        for q in qs:
            gq = g[g["qi"] == q]
            tot = gq["link"].nunique()
            r = {"area": a, "qi": q, "period_end": q_end(q), "news_attention": float(np.log1p(tot))}
            for t in THEMES:
                n = int((gq["theme"] == t).sum())
                r[f"n_{t}"] = n
                r[f"news_share_{t}"] = n / tot if tot else np.nan
            out.append(r)
    return pd.DataFrame(out).sort_values(["area", "qi"]).reset_index(drop=True)


def news(area: str, quarter_qi: int, d: pd.Timestamp) -> dict:
    """News of quarter `quarter_qi` (complete by d), each column z-scored against the area's earlier quarters."""
    n = news_quarterly()
    n = n[(n["area"] == area) & (n["period_end"] <= d) & (n["qi"] <= quarter_qi)]
    if n.empty or int(n["qi"].iloc[-1]) != quarter_qi:
        return {}
    return {c: _z_last(n[c]) for c in NEWS_COLS}
