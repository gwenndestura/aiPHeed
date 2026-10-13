"""E24v2 acquisition of PUBLIC, PRE-2026 PSA OpenSTAT tables (FROZEN_EVALUATION_PROTOCOL.md section 2.1 / 2.6).

Hard rules enforced in code:
  * no year >= 2026 is ever requested (assert on the resolved Year selection), and
  * no response may contain a year >= 2026 (assert on every returned key).
Every raw response is stored byte-for-byte with its query; ACQUISITION_MANIFEST.json records URL, query SHA-256,
response SHA-256, retrieval time (UTC) and row counts.  Nothing outside this experiment folder is written.

Usage:  python -I acquisition/fetch_openstat.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
MAX_YEAR = 2025                        # protected boundary: nothing from 2026 onward
PROV = {"33": "Batangas", "34": "Cavite", "35": "Laguna", "36": "Quezon", "37": "Rizal"}
CPI_COMMODITIES = ["0", "2", "5"]      # 0 All items, 2 "01.1 - FOOD", 5 "01.1.1.12 - Rice"
MONTHS = [str(i) for i in range(12)]  # Jan..Dec (excludes "Ave")

S = requests.Session()
S.headers["User-Agent"] = "aiPHeed-E24v2 thesis research (public statistics; polite single requests)"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def meta(table: str) -> dict:
    r = S.get(f"{BASE}/{table}", timeout=90)
    r.raise_for_status()
    time.sleep(0.8)
    return r.json()


def var(md: dict, code: str) -> dict:
    for v in md["variables"]:
        if v["code"] == code:
            return v
    raise KeyError(code)


def years_sel(md: dict, lo: int, hi: int) -> list[str]:
    assert hi <= MAX_YEAR, "refusing to request a year >= 2026"
    v = var(md, "Year")
    out = [c for c, t in zip(v["values"], v["valueTexts"]) if lo <= int(str(t)[:4]) <= hi]
    assert out, f"no years {lo}-{hi}"
    assert all(int(str(t)[:4]) <= MAX_YEAR for c, t in zip(v["values"], v["valueTexts"]) if c in out)
    return out


def post(table: str, query: dict, tag: str, manifest: list) -> dict:
    qb = json.dumps(query, indent=1, sort_keys=True).encode()
    r = S.post(f"{BASE}/{table}", json=query, timeout=180)
    r.raise_for_status()
    time.sleep(0.8)
    body = r.content
    (RAW / f"{tag}_query.json").write_bytes(qb)
    (RAW / f"{tag}_response.json").write_bytes(body)
    js = json.loads(body)
    manifest.append({"tag": tag, "url": f"{BASE}/{table}", "method": "POST", "retrieved_utc":
                     datetime.now(timezone.utc).isoformat(timespec="seconds"), "query_sha256": sha(qb),
                     "response_sha256": sha(body), "response_bytes": len(body), "cells": len(js.get("data", []))})
    return js


def check_years(js: dict, md: dict, tag: str) -> None:
    cols = [c["code"] for c in js["columns"]]
    yi = cols.index("Year")
    yv = var(md, "Year")
    text = dict(zip(yv["values"], yv["valueTexts"]))
    bad = [d["key"] for d in js["data"] if int(str(text.get(d["key"][yi], d["key"][yi]))[:4]) > MAX_YEAR]
    assert not bad, f"{tag}: response contains a year >= 2026; aborting"


def tidy(js: dict, md: dict, tag: str) -> list[dict]:
    cols = [c["code"] for c in js["columns"]]
    names = {v["code"]: dict(zip(v["values"], v["valueTexts"])) for v in md["variables"]}
    rows = []
    for d in js["data"]:
        rec = {"source": tag}
        for c, k in zip(cols, d["key"]):
            rec[c + "_code"] = k
            rec[c] = names.get(c, {}).get(k, k)
        val = d["values"][0]
        rec["value"] = None if val in ("..", "-", "", None) else float(val)
        rows.append(rec)
    return rows


def cpi(table: str, lo: int, hi: int, tag: str, manifest: list) -> list[dict]:
    md = meta(table)
    q = {"query": [
        {"code": "Geolocation", "selection": {"filter": "item", "values": list(PROV)}},
        {"code": "Commodity Description", "selection": {"filter": "item", "values": CPI_COMMODITIES}},
        {"code": "Year", "selection": {"filter": "item", "values": years_sel(md, lo, hi)}},
        {"code": "Period", "selection": {"filter": "item", "values": MONTHS}}],
        "response": {"format": "json"}}
    # sanity: geolocation and commodity texts are what the protocol says
    g = dict(zip(var(md, "Geolocation")["values"], var(md, "Geolocation")["valueTexts"]))
    assert all(PROV[c] in g[c] for c in PROV), g
    cm = dict(zip(var(md, "Commodity Description")["values"], var(md, "Commodity Description")["valueTexts"]))
    assert "ALL ITEMS" in cm["0"] and cm["2"].endswith("01.1 - FOOD") and "Rice" in cm["5"], cm
    js = post(table, q, tag, manifest)
    check_years(js, md, tag)
    return tidy(js, md, tag)


def poverty(table: str, tag: str, manifest: list) -> list[dict]:
    md = meta(table)
    sel = []
    for v in md["variables"]:
        if v["code"] == "Year" or "year" in v["code"].lower():
            vals = [c for c, t in zip(v["values"], v["valueTexts"]) if str(t)[:4].isdigit() and int(str(t)[:4]) <= MAX_YEAR]
        elif "geo" in v["code"].lower() or "region" in v["code"].lower():
            keep = ("calabarzon", "batangas", "cavite", "laguna", "quezon", "rizal", "lucena", "philippines")
            vals = [c for c, t in zip(v["values"], v["valueTexts"]) if any(k in t.lower() for k in keep)]
        else:
            vals = list(v["values"])
        sel.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
    js = post(table, {"query": sel, "response": {"format": "json"}}, tag, manifest)
    cols = [c["code"] for c in js["columns"]]
    yc = [c for c in cols if c == "Year" or "year" in c.lower()]
    if yc:
        yv = var(md, yc[0])
        text = dict(zip(yv["values"], yv["valueTexts"]))
        yi = cols.index(yc[0])
        assert all(int(str(text[d["key"][yi]])[:4]) <= MAX_YEAR for d in js["data"]), tag
    return tidy(js, md, tag)


def main() -> None:
    import csv
    RAW.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    out = {}
    out["cpi_index_1994_2017_ACP28"] = cpi("DB/2M/PI/CPI/2018NEW/0012M4ACP28.px", 1994, 2017, "ACP28_1994_2017", manifest)
    out["cpi_index_2018_2020_ACP22"] = cpi("DB/2M/PI/CPI/2018NEW/0012M4ACP22.px", 2018, 2020, "ACP22_2018_2020", manifest)
    out["cpi_index_2021_2025_ACP22"] = cpi("DB/2M/PI/CPI/2018NEW/0012M4ACP22.px", 2021, 2025, "ACP22_2021_2025", manifest)
    out["cpi_yoy_2019_2020_ACP23"] = cpi("DB/2M/PI/CPI/2018NEW/0012M4ACP23.px", 2019, 2020, "ACP23_2019_2020", manifest)
    out["subsistence_pop_prov_huc_2018_2023"] = poverty("DB/1F/FY/0081F3DF04A.px", "FY_0081F3DF04A", manifest)
    out["poverty_pop_prov_huc_2018_2023"] = poverty("DB/1F/FY/0041F3DF02A.px", "FY_0041F3DF02A", manifest)
    files = {}
    for name, rows in out.items():
        p = RAW.parent / f"{name}.csv"
        keys = sorted({k for r in rows for k in r})
        with open(p, "w", newline="\n", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        files[p.name] = {"rows": len(rows), "sha256": sha(p.read_bytes())}
    man = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "protocol": (HERE.parent / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0],
           "max_year_requested": MAX_YEAR, "requests": manifest, "tidy_files": files,
           "authorization_basis": "Public official PSA statistics, pre-2026 only; Chapter I 1.7 data scope; "
                                  "outside every protected category (2026 outcomes, news, restricted survey rounds). "
                                  "Listed for owner confirmation in ADVISER_AND_AUTHORIZATION_CHECKLIST.md."}
    (HERE / "ACQUISITION_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    for k, v in files.items():
        print(k, v)


if __name__ == "__main__":
    sys.exit(main())
