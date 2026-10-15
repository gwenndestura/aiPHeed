"""E41: fetch official PSA OpenStat series for the five-trigger audit, 2021-2026 only.

    python -B runner/e41_fetch_gov.py   -> data_acquired/<table>_{query,raw}.json, *.csv, acquisition.json

Only years 2021..2026 are requested (study-window rule): no pre-2021 value is downloaded.
Tables (PSA OpenStat PX-Web API, https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB):
  CPI index levels (2018=100), provinces, All items + 01.1 Food      2M/PI/CPI/2018NEW/0012M4ACP22.px
  Palay and corn production (metric tons), provinces, quarterly     2E/CS/0012E4EVCP0.px
  Fisheries production (metric tons) by subsector, provinces        2E/FS/0132E4GVFP1.px
  LFS unemployment and underemployment rate, Philippines, monthly   1B/LFS/0021B3FKEI2.px
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.dont_write_bytecode = True
E41 = Path(__file__).resolve().parents[1]
OUT = E41 / "data_acquired"
BASE = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/"
YEARS = [str(y) for y in range(2021, 2027)]
PROV = {"Batangas": "PH041000000", "Cavite": "PH042100000", "Laguna": "PH043400000",
        "Quezon": "PH045600000", "Rizal": "PH045800000"}


def _get(path: str):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "aiPHeed-E41-audit"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read().decode("utf-8-sig"))


def _post(path: str, query: dict) -> bytes:
    req = urllib.request.Request(BASE + path, data=json.dumps(query).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "aiPHeed-E41-audit"})
    return urllib.request.urlopen(req, timeout=180).read()


def _codes(var: dict, keep) -> list[str]:
    return [c for c, t in zip(var["values"], var["valueTexts"]) if keep(t.strip(". ").strip())]


def fetch(name: str, path: str, picks: dict) -> pd.DataFrame:
    meta = _get(path)
    query, texts = [], {}
    for v in meta["variables"]:
        texts[v["code"]] = dict(zip(v["values"], [t.strip(". ").strip() for t in v["valueTexts"]]))
        keep = picks.get(v["code"])
        if v["code"] == "Year":
            keep = lambda t: t in YEARS                                   # noqa: E731
        sel = _codes(v, keep) if keep else v["values"]
        if not sel:
            raise SystemExit(f"{name}: nothing selected for {v['code']}")
        query.append({"code": v["code"], "selection": {"filter": "item", "values": sel}})
    q = {"query": query, "response": {"format": "json"}}
    raw = _post(path, q)
    (OUT / f"{name}_query.json").write_text(json.dumps(q, indent=1))
    (OUT / f"{name}_raw.json").write_bytes(raw)
    d = json.loads(raw.decode("utf-8-sig"))
    dims = [c["code"] for c in d["columns"] if c["type"] in ("d", "t")]
    rows = []
    for r in d["data"]:
        row = {k: texts[k][c] for k, c in zip(dims, r["key"])}
        v = r["values"][0]
        row["value"] = None if v.strip() in ("", ".", "..", "-", "...") else float(v)
        rows.append(row)
    df = pd.DataFrame(rows)
    assert df["Year"].astype(int).min() >= 2021, "pre-2021 row returned"
    df.to_csv(OUT / f"{name}.csv", index=False)
    return df, hashlib.sha256(raw).hexdigest(), meta.get("title")


def main():
    OUT.mkdir(exist_ok=True)
    prov = lambda t: t in PROV or t.upper().startswith("REGION IV-A")          # noqa: E731
    jobs = {
        "cpi_index_ACP22": ("2M/PI/CPI/2018NEW/0012M4ACP22.px",
                            {"Geolocation": lambda t: t in PROV,
                             "Commodity Description": lambda t: t in ("0 - ALL ITEMS", "01.1 - FOOD")}),
        "palay_corn_production": ("2E/CS/0012E4EVCP0.px",
                                  {"Geolocation": prov, "Ecosystem/Croptype": lambda t: t in ("Palay", "Corn"),
                                   "Period": lambda t: t.startswith("Quarter")}),
        "fisheries_production": ("2E/FS/0132E4GVFP1.px",
                                 {"Geolocation": prov, "Quarter": lambda t: t.startswith("Quarter")}),
        "lfs_rates_national": ("1B/LFS/0021B3FKEI2.px",
                               {"Rates": lambda t: t in ("Unemployment Rate", "Underemployment Rate"),
                                "Sex": lambda t: t == "Both sexes"}),
    }
    log = {"retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "years_requested": YEARS, "tables": {}}
    for name, (path, picks) in jobs.items():
        df, sha, title = fetch(name, path, picks)
        log["tables"][name] = {"url": BASE + path, "title": title, "raw_sha256": sha, "rows": int(len(df)),
                               "non_missing": int(df["value"].notna().sum())}
        print(name, len(df), "rows,", int(df["value"].notna().sum()), "non-missing")
    (OUT / "acquisition.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
