"""
E152 local inputs by province and issue quarter. Reads no outcome.

Monthly PSA farmgate and wholesale prices, and NASA POWER rainfall. A month may be used only if it is at least 3 full months before the issue date: past PSA release dates are not held, so this delay is an assumption, and a cautious one.

    python -m app.e152.panel rain | build -> data/e152/raw/rain_monthly.csv, data/e152/out/local_panel.parquet, panel_audit.json
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

from app.e137 import features as F
from app.e147 import features as Fe
from app.e148 import panel as Pn
from app.paths import BACKEND_DIR

ROOT = BACKEND_DIR / "data" / "e152"
RAW, OUT = ROOT / "raw", ROOT / "out"
LAG_M = 3
URL = ("https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR&community=AG&latitude={lat}&longitude={lon}&start=2000&end=2026&format=JSON")
MON = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])}
ALIAS = {"mountain": "mountain province", "tawi tawi": "tawi-tawi", "compostela valley": "davao de oro", "north cotabato": "cotabato", "western samar": "samar", "cagayan province": "cagayan", "iloilo province": "iloilo", "isabela province": "isabela", "cotabato (north cotabato)": "cotabato", "samar (western samar)": "samar", "davao de oro (compostela valley)": "davao de oro", "tawi-tawi": "tawi-tawi"}


def rain():
    rows, geo = [], F._geo()
    for k, xy in sorted(geo.items()):
        req = urllib.request.Request(URL.format(lat=round(xy[1], 3), lon=round(xy[0], 3)), headers={"User-Agent": "aipheed-research/1.0"})
        js = json.load(urllib.request.urlopen(req, timeout=120))
        for ym, v in js["properties"]["parameter"]["PRECTOTCORR"].items():
            if not ym.endswith("13") and v > -900:
                rows.append((k, ym[:4] + "-" + ym[4:], v))
        time.sleep(1.0)
    pd.DataFrame(rows, columns=["k", "month", "rain"]).to_csv(RAW / "rain_monthly.csv", index=False, lineterminator="\n")
    print(len(geo), len(rows))


def norm_name(s: str) -> str:
    s = re.sub(r"\s+[a-z]/$", "", s.strip(". ").lower())
    return ALIAS.get(s, s)


def load_px(name, want) -> pd.DataFrame:
    """Province-month mean of the commodities whose names contain any of `want`. Each commodity is first scaled to its own mean, so a change in which varieties report does not look like a price change."""
    d = json.loads((RAW / f"{name}.json").read_text())
    c = d["columns"]
    m = d["meta"]
    geo, com, per = m[c[0]], m[c[1]], m[c[3]]
    keep = {a for a, b in com.items() if any(k in b.lower() for k in want)}
    rows = []
    for yr, data in d["data"].items():
        for r in data:
            g, cm, _, p = r["key"]
            if cm not in keep or per[p] not in MON or not geo[g].startswith("...."):
                continue
            try:
                v = float(r["values"][0])
            except ValueError:
                continue
            if v > 0:
                rows.append((norm_name(geo[g]), cm, pd.Period(year=int(yr), month=MON[per[p]], freq="M"), v))
    t = pd.DataFrame(rows, columns=["name", "cm", "p", "v"])
    t["v"] = np.log(t["v"]) - t.groupby("cm")["v"].transform(lambda s: np.log(s).mean())
    return t.groupby(["name", "p"])["v"].mean().reset_index()


def window(s: pd.Series, issue: pd.Timestamp, n: int, back_years: int = 0) -> float:
    """Mean of the n months ending LAG_M months before the issue date, optionally the same months earlier. Later months are never read."""
    end = issue.to_period("M") - LAG_M - 12 * back_years
    v = s.reindex(pd.period_range(end - n + 1, end, freq="M")).dropna()
    return float(v.mean()) if len(v) >= max(1, n - 1) else np.nan


def rain_anom(s: pd.Series, issue: pd.Timestamp, n: int) -> float:
    end = issue.to_period("M") - LAG_M
    months = pd.period_range(end - n + 1, end, freq="M")
    if not all(m in s.index for m in months):
        return np.nan
    clim = [s.reindex([pd.Period(year=y, month=m.month, freq="M") for m in months]).mean() for y in range(2000, 2010)]
    sd = float(np.std(clim, ddof=1))
    return float((s[months].mean() - np.mean(clim)) / sd) if sd > 0 else np.nan


COLS = ["l_fg_yoy", "l_rice_yoy", "l_fish_yoy", "l_rice_rel", "l_fg_rel", "l_terms", "l_rain3", "l_rain6"]


def build():
    base = Fe.base_rows().drop_duplicates("key")
    fg, rc, fs = load_px("farmgate_cereals", ["palay"]), load_px("wholesale_cereals", ["rice"]), load_px("wholesale_fish", ["bangus", "galunggong", "tilapia", "milkfish", "round scad"])
    tab = {n: {k: g.set_index("p")["v"].sort_index() for k, g in t.groupby("name")} for n, t in (("fg", fg), ("rc", rc), ("fs", fs))}
    R = pd.read_csv(RAW / "rain_monthly.csv")
    R["p"] = pd.PeriodIndex(R["month"], freq="M")
    rn = {k: g.set_index("p")["rain"] for k, g in R.groupby("k")}
    rows, miss = [], {}
    for key in base["key"]:
        n = norm_name(key)
        for t in ("fg", "rc", "fs"):
            if n not in tab[t]:
                miss.setdefault(t, []).append(key)
        r_ = rn.get(key.replace(" ", ""), rn.get(key))
        for i in range(Pn.FIRST, Pn.LAST + 1):
            q = Pn.q_start(i)
            o = {"key": key, "qi": i}
            for t, nm in (("fg", "l_fg_yoy"), ("rc", "l_rice_yoy"), ("fs", "l_fish_yoy")):
                s = tab[t].get(n)
                o[nm] = (window(s, q, 3) - window(s, q, 3, 1)) if s is not None else np.nan
                o[nm.replace("_yoy", "_lvl")] = window(s, q, 3) if s is not None else np.nan
            o["l_rain3"], o["l_rain6"] = (rain_anom(r_, q, 3), rain_anom(r_, q, 6)) if r_ is not None else (np.nan, np.nan)
            rows.append(o)
    P = pd.DataFrame(rows)
    # levels relative to all provinces in the same issue quarter; terms of trade is farmgate against wholesale rice
    P["l_rice_rel"] = P["l_rice_lvl"] - P.groupby("qi")["l_rice_lvl"].transform("mean")
    P["l_fg_rel"] = P["l_fg_lvl"] - P.groupby("qi")["l_fg_lvl"].transform("mean")
    P["l_terms"] = P["l_fg_lvl"] - P["l_rice_lvl"]
    reg = base.set_index("key")["region"]
    P["region"] = P["key"].map(reg)
    for c in ("l_fg_yoy", "l_rice_yoy", "l_rain3"):
        P["r" + c[1:]] = P.groupby(["region", "qi"])[c].transform("mean")
    P = P.drop(columns=["region", "l_fg_lvl", "l_rice_lvl", "l_fish_lvl"])
    OUT.mkdir(exist_ok=True)
    P.to_parquet(OUT / "local_panel.parquet", index=False)
    window_rows = P[(P["qi"] >= Pn.FIRST + 12)]
    a = {"lag_months": LAG_M, "rows": int(len(P)), "provinces": int(P["key"].nunique()), "unmatched": miss, "missing_share_from_2016": window_rows[COLS].isna().mean().round(3).to_dict(), "within_quarter_sd": {c: float(window_rows.groupby("qi")[c].std().mean()) for c in COLS}, "between_quarter_sd": {c: float(window_rows.groupby("qi")[c].mean().std()) for c in COLS}}
    (OUT / "panel_audit.json").write_text(json.dumps(a, indent=1, default=float), newline="\n")
    print(json.dumps(a, default=float))


if __name__ == "__main__":
    {"rain": rain, "build": build}[sys.argv[1]]()
