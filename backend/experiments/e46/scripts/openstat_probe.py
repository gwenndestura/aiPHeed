"""E46 feasibility (read only): which PSA OpenStat tables cover 2015-2020 for provincial food CPI (2012=100 vs
2018=100), provincial rice retail prices, LFS unemployment and fisheries production. Prints table ids, titles, year
ranges and whether CALABARZON provinces are present. Writes backend/experiments/e46/data/openstat_tables.csv."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E46 feasibility)"}
SEARCHES = ["consumer price index food province 2012", "consumer price index food 2018", "retail price rice province",
            "average retail price regular milled rice", "food inflation province"]
KNOWN = ["DB/1B/LFS/0021B3FKEI2.px", "DB/2E/FS/0132E4GVFP1.px"]
PROVS = ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")


def meta(path):
    r = requests.get(f"{API}/{path}", headers=H, timeout=90)
    r.raise_for_status()
    return r.json()


def describe(path):
    m = meta(path)
    out = {"table": path, "title": m.get("title")}
    for v in m["variables"]:
        vals = v["valueTexts"]
        if v["code"].lower().startswith(("year", "period", "time")) or v["code"] in ("Year", "Period"):
            out["years"] = f"{vals[0]} .. {vals[-1]} ({len(vals)})"
        provs = [p for p in PROVS if any(p in x for x in vals)]
        if provs:
            out["calabarzon_provinces"] = len(provs)
    return out


def main():
    hits = {}
    for s in SEARCHES:
        try:
            res = requests.get(f"{API}/DB", headers=H, params={"query": s}, timeout=90).json()
        except Exception as e:  # noqa: BLE001
            print("search failed", s, e)
            continue
        for it in res[:15]:
            path = "DB" + it.get("path", "") + "/" + it.get("id", "")
            t = it.get("title", "")
            if any(k in t.lower() for k in ("price", "cpi", "inflation")):
                hits[path] = t
    rows = []
    for path in list(dict.fromkeys(list(hits) + KNOWN)):
        try:
            d = describe(path)
        except Exception as e:  # noqa: BLE001
            d = {"table": path, "title": hits.get(path), "error": f"{type(e).__name__}"}
        rows.append(d)
        print(d)
    out = Path(__file__).resolve().parents[1] / "data"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "openstat_tables.csv", index=False)


if __name__ == "__main__":
    main()
