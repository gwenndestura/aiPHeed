"""
E155 audit of the new news: coverage, province matching, and whether the series move with real events. Reads no food-insecurity outcome.

    python -m app.e155.audit -> data/e155/out/{gdelt_monthly.parquet, sunstar_monthly.parquet, audit.json}
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e150 import response as R150
from app.e155.gdelt import RAW as GRAW
from app.e155.gdelt import THEMES
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e155" / "out"
SUN = BACKEND_DIR / "data" / "e155" / "raw" / "sunstar.parquet"
EDITION = {"cebu": "cebu", "davao": "davao del sur", "bacolod": "negros occidental", "pampanga": "pampanga", "baguio": "benguet", "cagayan-de-oro": "misamis oriental", "iloilo": "iloilo province", "zamboanga": "zamboanga del sur", "tacloban": "leyte", "dumaguete": "negros oriental", "general-santos": "south cotabato", "pangasinan": "pangasinan", "bohol": "bohol"}
LEX = {"price": r"\b(price|prices|presyo|inflation|mahal|rice|bigas|sugar|onion|fuel|gasoline|diesel)\b", "shortage": r"\b(shortage|hunger|hungry|gutom|malnutrition|food security|food insecurity|starv)", "agri": r"\b(farmer|farmers|palay|harvest|crop|crops|fisherfolk|fishermen|livestock|asf|swine|pest|agricultur)", "jobs": r"\b(job|jobs|jobless|unemploy|layoff|layoffs|retrench|livelihood|workers)\b",
       "disaster": r"\b(typhoon|bagyo|flood|floods|flooding|landslide|drought|el nino|la nina|storm|calamity|evacuat)", "aid": r"\b(aid|relief|ayuda|food packs|assistance|subsidy|dswd|4ps|donat)"}


def gdelt_monthly() -> pd.DataFrame:
    rows = []
    for f in GRAW.glob("*__*.csv"):
        key, s = f.stem.split("__")
        d = pd.read_csv(f, encoding="utf-8-sig")
        d = d[d["Series"] == "Article Count"].copy()
        d["month"] = pd.to_datetime(d["Date"]).dt.to_period("M")
        m = d.groupby("month")["Value"].sum()
        for mo, v in m.items():
            rows.append({"key": key.replace("_", " "), "series": s, "month": str(mo), "n": float(v)})
    g = pd.DataFrame(rows)
    if g.empty:
        return g
    w = g.pivot_table(index=["key", "month"], columns="series", values="n").reset_index()
    for s in THEMES:
        if s in w and "all" in w:
            w["share_" + s] = w[s] / w["all"].where(w["all"] > 0)
    return w


def sunstar_monthly() -> pd.DataFrame:
    if not SUN.exists():
        return pd.DataFrame()
    d = pd.read_parquet(SUN)
    d["month"] = pd.to_datetime(d["date"]).dt.to_period("M").astype(str)
    d["key"] = d["edition"].map(EDITION)
    for k, rx in LEX.items():
        d[k] = d["title"].str.contains(rx, flags=re.I, regex=True)
    g = d.dropna(subset=["key"]).groupby(["key", "month"]).agg(all=("slug", "size"), **{k: (k, "sum") for k in LEX}).reset_index()
    for k in LEX:
        g["share_" + k] = g[k] / g["all"]
    return g


def construct(g: pd.DataFrame) -> dict:
    """Province-quarter news shares against the matching government series, as of the same quarter."""
    if g.empty:
        return {}
    G = R150.province_inputs()
    g = g.copy()
    p = pd.PeriodIndex(g["month"], freq="M")
    g["qi"] = p.year * 4 + (p.month - 1) // 3
    q = g.groupby(["key", "qi"])[[c for c in g.columns if c.startswith("share_")]].mean().reset_index()
    m = q.merge(G[["key", "qi", "cpi_food_yoy", "c_tc_4q", "c_rain_anom_6m", "unemp_rate"]], on=["key", "qi"])
    out = {}
    for a, b in (("share_price", "cpi_food_yoy"), ("share_disaster", "c_tc_4q"), ("share_agri", "c_rain_anom_6m"), ("share_jobs", "unemp_rate")):
        if a in m:
            z = m[[a, b]].dropna()
            # within-province: remove each province's mean so the check is about timing, not size
            zz = m[["key", a, b]].dropna().copy()
            zz[a] -= zz.groupby("key")[a].transform("mean")
            zz[b] -= zz.groupby("key")[b].transform("mean")
            out[f"{a}~{b}"] = {"n": int(len(z)), "spearman": float(spearmanr(z[a], z[b]).statistic) if len(z) > 10 else None, "within_province_spearman": float(spearmanr(zz[a], zz[b]).statistic) if len(zz) > 10 else None}
    return out


def events(g: pd.DataFrame) -> dict:
    """National monthly shares around known events, against the same calendar months a year earlier."""
    if g.empty or "share_price" not in g:
        return {}
    n = g.groupby("month")[[c for c in g.columns if c.startswith("share_")]].mean()
    checks = {"rice price surge 2018-08 to 2018-10": ("share_price", ["2018-08", "2018-09", "2018-10"]), "rice crisis 2023-08 to 2023-10": ("share_price", ["2023-08", "2023-09", "2023-10"]), "COVID lockdown 2020-04 to 2020-06 jobs": ("share_jobs", ["2020-04", "2020-05", "2020-06"]),
              "COVID aid 2020-04 to 2020-06": ("share_aid", ["2020-04", "2020-05", "2020-06"]), "Odette 2021-12 to 2022-01": ("share_disaster", ["2021-12", "2022-01"]), "Kristine 2024-10 to 2024-11": ("share_disaster", ["2024-10", "2024-11"])}
    out = {}
    for name, (c, ms) in checks.items():
        if c not in n:
            continue
        cur = n.reindex(ms)[c].mean()
        prev = n.reindex([str(pd.Period(x) - 12) for x in ms])[c].mean()
        out[name] = {"share": None if pd.isna(cur) else round(float(cur), 4), "same_months_year_before": None if pd.isna(prev) else round(float(prev), 4), "ratio": None if pd.isna(cur) or pd.isna(prev) or prev == 0 else round(float(cur / prev), 2)}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    g, s = gdelt_monthly(), sunstar_monthly()
    if len(g):
        g.to_parquet(OUT / "gdelt_monthly.parquet", index=False)
    if len(s):
        s.to_parquet(OUT / "sunstar_monthly.parquet", index=False)
    a = {"gdelt": {"provinces": int(g["key"].nunique()) if len(g) else 0, "months": int(g["month"].nunique()) if len(g) else 0, "articles_all": float(g["all"].sum()) if "all" in g else 0, "median_per_province_quarter": float(g.groupby(["key", g["month"].str[:4]])["all"].sum().median() / 4) if "all" in g else None, "calabarzon_total": {k: float(g[g["key"] == k]["all"].sum()) for k in ("batangas", "cavite", "laguna", "quezon", "rizal")} if "all" in g else {}},
         "sunstar": {"editions_matched": int(s["key"].nunique()) if len(s) else 0, "months": int(s["month"].nunique()) if len(s) else 0, "headlines": int(s["all"].sum()) if len(s) else 0, "note": "No CALABARZON edition, so SunStar adds no CALABARZON news; it helps the provinces the model trains on."},
         "construct_gdelt": construct(g), "construct_sunstar": construct(s), "events_gdelt": events(g), "events_sunstar": events(s)}
    (OUT / "audit.json").write_text(json.dumps(a, indent=1, default=float), newline="\n")
    print(json.dumps(a, indent=1, default=float))


if __name__ == "__main__":
    main()
