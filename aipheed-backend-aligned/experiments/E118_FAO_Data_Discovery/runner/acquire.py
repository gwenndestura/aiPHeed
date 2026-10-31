"""E118 acquisition (public data only; raw responses saved unmodified; cleaned copies separate).

PSA OpenSTAT tables (Region IV-A and its five provinces only) and NASA POWER monthly climate at the five province
centroids. Each raw file is saved with its fetch time, query and the table's own "updated" stamp.

    python acquire.py    # ../data/raw/*.csv|json, ../data/acquisition_log.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "data" / "raw"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
GEO = {"CAVITE", "LAGUNA", "BATANGAS", "RIZAL", "QUEZON", "REGION IV-A (CALABARZON)", "IV-A CALABARZON", "CALABARZON"}
TABLES = {  # key: (path, FAO dimension, note)
    "retail_cereals": ("DB/2M/2018NEW/0042M4ARN01.px", "access", "monthly provincial retail prices 2018+"),
    "retail_fish": ("DB/2M/2018NEW/0042M4ARN11.px", "access", ""),
    "retail_poultry": ("DB/2M/2018NEW/0042M4ARN10.px", "access", ""),
    "retail_livestock": ("DB/2M/2018NEW/0042M4ARN09.px", "access", ""),
    "retail_leafy_veg": ("DB/2M/2018NEW/0042M4ARN06.px", "access", ""),
    "retail_fruit_veg": ("DB/2M/2018NEW/0042M4ARN05.px", "access", ""),
    "retail_rootcrops": ("DB/2M/2018NEW/0042M4ARN02.px", "access", ""),
    "farmgate_cereals": ("DB/2M/NFG/0032M4AFN01.px", "availability/access", "monthly provincial farmgate 2010+"),
    "farmgate_livestock_household": ("DB/2M/NFG/0032M4AFN10.px", "availability/access", ""),
    "wholesale_cereals": ("DB/2M/NWSNEW/0052M4AWB01.px", "access", "monthly provincial wholesale 2010+"),
    "wholesale_fish": ("DB/2M/NWSNEW/0052M4AWB10.px", "access", ""),
    "cpi_bottom30_index": ("DB/2M/PI/BIH/2018NEW/0022M4ABIR1.px", "access", "CPI for the poorest 30% of households 2018+"),
    "cpi_bottom30_yoy": ("DB/2M/PI/BIH/2018NEW/0022M4ABIR2.px", "access", ""),
    "cpi_2012base_1994_2018": ("DB/3L/FAC/0013L5ECPI0.px", "access", "2012=100 provincial CPI (vintage before the rebase)"),
    "prod_vegetables_rootcrops": ("DB/2E/CS/0082E4EVCP3.px", "availability", "quarterly provincial 2010+"),
    "prod_chicken": ("DB/2E/LP/PDN/0052E4FPCT0.px", "availability", "quarterly provincial 2023+"),
    "prod_livestock": ("DB/2E/LP/PDN/0082E4FPLS2.px", "availability", "quarterly provincial 2023+"),
    "prod_aquaculture": ("DB/2E/FS/0072E4GVAP0.px", "availability", "quarterly provincial 1996+"),
    "prod_palay_corn": ("DB/2E/CS/0012E4EVCP0.px", "availability", "quarterly provincial 1987+ (already used, refreshed)"),
    "prod_fisheries": ("DB/2E/FS/0132E4GVFP1.px", "availability", "quarterly provincial 1980+ (already used, refreshed)"),
    "subsistence_1991_2015": ("DB/3D/0033C3DP030.px", "access (outcome-type)", "triennial provincial"),
    "subsistence_2018_2021": ("DB/1F/FS/0101F3DS05A.px", "access (outcome-type)", ""),
    "fies_expenditure_groups_2023": ("DB/1E/IE/0071E3ATME0.px", "access", "provincial 2023 expenditure by group"),
}
CENTROIDS = {"Cavite": (14.28, 120.87), "Laguna": (14.17, 121.33), "Batangas": (13.76, 121.06), "Rizal": (14.60, 121.31), "Quezon": (14.03, 122.11)}


def curl(url, data=None, timeout=300):
    cmd = ["curl", "-s", "-m", str(timeout), "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log = {"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tables": {}, "power": {}}
    listing = {t["path"]: t for t in json.load(open(HERE.parent / "out" / "openstat_tables.json"))}
    for key, (path, dim, note) in TABLES.items():
        try:
            meta = json.loads(curl(f"{PX}/{path}").decode("utf-8-sig"))
            q = []
            for v in meta["variables"]:
                if v["code"].lower().startswith("geo") or "region" in v["code"].lower() or "province" in v["code"].lower():
                    vals = [c for c, t in zip(v["values"], v["valueTexts"]) if t.strip(". ").upper() in GEO or any(t.strip(". ").upper().startswith(g + " ") for g in ("CAVITE", "LAGUNA", "BATANGAS", "RIZAL", "QUEZON"))]
                    q.append({"code": v["code"], "selection": {"filter": "item", "values": vals or v["values"]}})
                else:
                    q.append({"code": v["code"], "selection": {"filter": "item", "values": v["values"]}})
            body = json.dumps({"query": q, "response": {"format": "csv"}})
            raw = curl(f"{PX}/{path}", body)
            f = RAW / f"psa_{key}.csv"
            f.write_bytes(raw)
            (RAW / f"psa_{key}_query.json").write_text(body)
            log["tables"][key] = {"path": path, "title": meta.get("title"), "fao_dimension": dim, "note": note,
                                  "table_updated": listing.get(path, {}).get("updated"), "bytes": len(raw),
                                  "sha256": hashlib.sha256(raw).hexdigest(), "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                  "ok": raw[:1] not in (b"{", b"<") and len(raw) > 200}
            print("ok", key, len(raw), flush=True)
        except Exception as e:  # noqa: BLE001
            log["tables"][key] = {"path": path, "error": f"{type(e).__name__}: {e}"}
            print("ERR", key, e, flush=True)
        time.sleep(1)
    for prov, (la, lo) in CENTROIDS.items():
        url = (f"https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR,T2M,T2M_MAX,RH2M"
               f"&community=AG&longitude={lo}&latitude={la}&start=1981&end=2025&format=JSON")
        raw = curl(url)
        f = RAW / f"nasa_power_monthly_{prov}.json"
        f.write_bytes(raw)
        log["power"][prov] = {"url": url, "lat": la, "lon": lo, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        print("ok power", prov, len(raw), flush=True)
        time.sleep(1)
    (HERE.parent / "data" / "acquisition_log.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    sys.exit(main())
