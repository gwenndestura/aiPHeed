"""
PSA regional accounts by industry: Agriculture, forestry and fishing (AFF) for every region, from PSA OpenSTAT (DB/2B/GP/IN).

REGIONAL data. Every province in a region takes its region's value; no provincial GRDP is created.

Tables per region (the folder <REG>_OS is the 2000-2023 series, <REG> the current 2018-2025 release; both at constant 2018 prices):
  "Gross Regional Domestic Product, by Industry, Growth Rates"   -> AFF real growth (%), year Y-1 to Y, constant 2018 prices
  "Gross Regional Domestic Product, by Industry, Percent Share"  -> AFF share of GRDP (%), current prices
Years up to 2023 come from the _OS series (the series the model's GRDP-per-person input already uses); 2024 and 2025 from the
current release. Release rule (same as hh_grdp_*): year Y usable from Q3 of Y+1 (app.e154 available_year).

    python -m app.hcw.grdp_industry fetch   -> data/hcw_official/raw/psa_grdp_aff_by_region.csv (+ provenance json)
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from app.paths import BACKEND_DIR

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2B/GP/IN/"
OUT = BACKEND_DIR / "data" / "hcw_official" / "raw"
FILE = OUT / "psa_grdp_aff_by_region.csv"
# model region labels (app.e158 oof 'region') -> OpenSTAT folder
REGIONS = {"ARMM": "ARM", "CAR": "CAR", "NCR": "NCR", "Ilocos": "R1", "Cagayan Valley": "R2", "Central Luzon": "R3", "CALABARZON": "R4A",
           "MIMAROPA": "R4B", "Bicol": "R5", "Western Visayas": "R6", "Central Visayas": "R7", "Eastern Visayas": "R8",
           "Zamboanga Peninsula": "R9", "Northern Mindanao": "R10", "Davao": "R11", "SOCCSKSARGEN": "R12", "Caraga": "R13"}
AFF = "..Agriculture, forestry, and fishing"


def _get(url: str, body: dict | None = None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "aiPHeed-research"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def _table(folder: str, suffix: str, valuation: str) -> dict[str, float]:
    t = next(x for x in _get(API + folder + "/") if x["text"].strip().endswith(suffix))
    meta = _get(API + folder + "/" + t["id"])
    var = {v["code"]: v for v in meta["variables"]}
    ind = var["Industry"]["values"][var["Industry"]["valueTexts"].index(AFF)]
    val = var["Type of Valuation"]["values"][var["Type of Valuation"]["valueTexts"].index(valuation)]
    q = {"query": [{"code": "Industry", "selection": {"filter": "item", "values": [ind]}},
                   {"code": "Type of Valuation", "selection": {"filter": "item", "values": [val]}}], "response": {"format": "json"}}
    res = _get(API + folder + "/" + t["id"], q)
    years = var["Year"]["valueTexts"]
    ymap = dict(zip(var["Year"]["values"], years))
    out = {}
    for row in res["data"]:
        y = ymap[row["key"][-1]]
        v = row["values"][0]
        try:
            out[y.split("-")[-1]] = float(v)
        except ValueError:
            pass
    return out, t["id"], t.get("updated")


def fetch() -> pd.DataFrame:
    rows, prov = [], {"source": API, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tables": {}}
    for reg, code in REGIONS.items():
        old_g, tid1, u1 = _table(code + "_OS", "Growth Rates", "At Constant 2018 Prices")
        new_g, tid2, u2 = _table(code, "Growth Rates", "At Constant 2018 Prices")
        old_s, tid3, u3 = _table(code + "_OS", "Percent Share", "At Current Prices")
        new_s, tid4, u4 = _table(code, "Percent Share", "At Current Prices")
        prov["tables"][reg] = {"growth_old": [tid1, u1], "growth_new": [tid2, u2], "share_old": [tid3, u3], "share_new": [tid4, u4]}
        for y in sorted(set(old_g) | set(new_g) | set(old_s) | set(new_s), key=int):
            yi = int(y)
            g = old_g.get(y) if yi <= 2023 else new_g.get(y)
            s = old_s.get(y) if yi <= 2023 else new_s.get(y)
            rows.append({"region": reg, "year": yi, "aff_growth_pct": g, "aff_share_pct": s,
                         "source_growth": "OS" if yi <= 2023 else "current", "source_share": "OS" if yi <= 2023 else "current"})
    d = pd.DataFrame(rows).sort_values(["region", "year"])
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_csv(FILE, index=False, lineterminator="\n")
    (OUT / "psa_grdp_aff_by_region.provenance.json").write_text(json.dumps(prov, indent=1))
    return d


def load() -> pd.DataFrame:
    return pd.read_csv(FILE)


def aff_inputs(region: str, i: int) -> dict:
    """AFF growth and share for a REGION as of issue quarter index i (year Y usable from Q3 of Y+1, the hh_grdp rule)."""
    from app.e154 import model as E154
    y = E154.available_year(i)
    d = load()
    r = d[(d.region == region) & (d.year == y)]
    if y is None or r.empty:
        return {"aff_g": float("nan"), "aff_share": float("nan")}
    return {"aff_g": float(r.aff_growth_pct.iloc[0]), "aff_share": float(r.aff_share_pct.iloc[0])}


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "fetch":
    print(fetch().groupby("region").agg(first=("year", "min"), last=("year", "max"), n=("year", "size")).to_string())
