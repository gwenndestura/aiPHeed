"""Y12 step 1: download the domestic rice-supply and provincial CPI series from PSA OpenSTAT (PXWeb API).

Every table is saved raw (CSV as served) under data_acquired/, with data_acquired/manifest.json recording for each file:
API path, table title, the exact POST query, UTC fetch time and SHA-256. Re-running overwrites the files and appends a
new manifest entry (the experiment pins the hashes it used in EXPERIMENT_PLAN.md).

    python -B acquire.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import psa

HERE = Path(__file__).resolve().parent
ACQ = HERE.parent / "data_acquired"
GEO_TXT = ["PHILIPPINES", "IV-A", "Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def codes(meta: dict, var: str, keep) -> list[str]:
    for v in meta["variables"]:
        if v["code"] == var:
            return [c for c, x in zip(v["values"], v["valueTexts"]) if keep(x)]
    raise KeyError(var)


def fetch(name: str, path: str, sel: dict[str, list[str]]) -> dict:
    meta = psa.get(path)
    q = {"query": [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in sel.items()],
         "response": {"format": "csv"}}
    b = psa.post(path, q)
    f = ACQ / f"{name}.csv"
    f.write_bytes(b)
    return {"file": f.name, "apiPath": psa.API + path, "title": meta.get("title"), "query": q,
            "fetchedUtc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def main():
    ACQ.mkdir(exist_ok=True)
    out = []
    geo = lambda x: any(g in x for g in GEO_TXT)  # noqa: E731
    palay = lambda x: x.startswith("Palay")  # noqa: E731

    # 1. national monthly rice stocks by sector, 1980-2026
    p = "2E/CS/0032E4ECNV0.px"
    m = psa.get(p)
    out.append(fetch("stocks_national_monthly", p, {"Sector": codes(m, "Sector", lambda x: x.startswith("Rice"))}))
    # regional stocks table (metadata says 2026 only); fetched to document coverage
    p = "2E/CS/0048E4ECNV1.px"
    m = psa.get(p)
    out.append(fetch("stocks_regional_monthly", p, {"Sector": codes(m, "Sector", lambda x: x.startswith("Rice")),
                                                     "Geolocation": codes(m, "Geolocation", geo)}))
    # 2. farmgate palay prices, old series 1990-2020 and new series 2010-2026
    for name, p in (("farmgate_palay_old", "2M/FG/0032M4AFP01.px"), ("farmgate_palay_new", "2M/NFG/0032M4AFN01.px")):
        m = psa.get(p)
        out.append(fetch(name, p, {"Geolocation": codes(m, "Geolocation", geo), "Commodity": codes(m, "Commodity", palay)}))
    # 3. CPI 2012=100: YoY and index, 1994/1995-2011 and 2012-2021; PH, Region IV-A, 5 provinces; all items, food, rice
    com = lambda x: x in ("ALL ITEMS", "Food", "Rice")  # noqa: E731
    for name, p in (("cpi2012_yoy_2012_2021", "2M/PI/CPI/2012/0012M4ACPI2.px"),
                    ("cpi2012_yoy_1995_2011", "2M/PI/CPI/2012/0012M4ACPI6.px"),
                    ("cpi2012_idx_2012_2021", "2M/PI/CPI/2012/0012M4ACPI1.px"),
                    ("cpi2012_idx_1994_2011", "2M/PI/CPI/2012/0012M4ACPI4.px")):
        m = psa.get(p)
        out.append(fetch(name, p, {"Geolocation": codes(m, "Geolocation", geo),
                                   "Commodity Description": codes(m, "Commodity Description", com)}))
    # 4. monthly rice imports (gross kilo, all countries), 2015-2026
    p = "2L/IMT/PMG/0022L4DNDM0.px"
    m = psa.get(p)
    out.append(fetch("imports_rice_monthly_2015_2026", p, {"GROUP": codes(m, "GROUP", lambda x: x == "Rice"),
                                                           "COUNTRY": codes(m, "COUNTRY", lambda x: True),
                                                           "Item": codes(m, "Item", lambda x: x == "Gross Kilo")}))
    mf = ACQ / "manifest.json"
    prev = json.loads(mf.read_text()) if mf.exists() else []
    mf.write_text(json.dumps(prev + out, indent=1), encoding="utf-8")
    for o in out:
        print(o["file"], o["bytes"], o["sha256"][:12], o["title"])


if __name__ == "__main__":
    main()
