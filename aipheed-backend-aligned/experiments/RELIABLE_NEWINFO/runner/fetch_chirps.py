"""RELIABLE_NEWINFO PLAN section 2: download CHIRPS daily rainfall, area average over the CALABARZON box, once.

    python fetch_chirps.py   # -> ../data/chirps_raw/<year-range>.json, ../data/chirps_monthly.csv, ../data/chirps_hashes.json

Source: CHIRPS (Climate Hazards Center, UCSB) daily, as served by SERVIR ClimateSERV (datatype 0), operation 5 =
spatial average over the polygon 120.6-122.5 E, 13.6-14.9 N (sea cells are NaN and do not count). Today's vintage.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
RAW = HERE / "data" / "chirps_raw"
API = "https://climateserv.servirglobal.net/api/"
BOX = {"type": "Polygon", "coordinates": [[[120.6, 13.6], [122.5, 13.6], [122.5, 14.9], [120.6, 14.9], [120.6, 13.6]]]}
FIRST, LAST = 1981, 2026
LAST_DAY = "09/30/2026"
CHUNK = 5


def _get(path: str, **params) -> bytes:
    url = API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "aiPHeed-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch(y0: int, y1: int) -> bytes:
    end = LAST_DAY if y1 == LAST else f"12/31/{y1}"
    job = json.loads(_get("submitDataRequest/", datatype=0, begintime=f"01/01/{y0}", endtime=end, intervaltype=0,
                          operationtype=5, geometry=json.dumps(BOX)))[0]
    for _ in range(120):
        p = json.loads(_get("getDataRequestProgress/", id=job))[0]
        if p >= 100:
            break
        time.sleep(5)
    else:
        raise TimeoutError(f"ClimateSERV job {job} did not finish")
    return _get("getDataFromRequest/", id=job)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    hashes, rows = {}, []
    for y0 in range(FIRST, LAST + 1, CHUNK):
        y1 = min(y0 + CHUNK - 1, LAST)
        p = RAW / f"chirps_daily_{y0}_{y1}.json"
        if not p.exists():
            p.write_bytes(fetch(y0, y1))
        b = p.read_bytes()
        hashes[p.name] = hashlib.sha256(b).hexdigest()
        for d in json.loads(b)["data"]:
            rows.append({"date": pd.Timestamp(year=d["year"], month=d["month"], day=d["day"]),
                         "mm": d["value"]["avg"], "nan_share": d.get("NaN")})
        print(p.name, "ok")
    D = pd.DataFrame(rows).sort_values("date").drop_duplicates("date")
    D["ym"] = D["date"].dt.year * 12 + D["date"].dt.month - 1
    M = D.groupby("ym").agg(mm=("mm", "sum"), days=("mm", "size"), bad=("mm", lambda s: int((s < -1).sum()))) \
        .reset_index()
    M["month"] = M["ym"].map(lambda i: f"{i // 12}-{i % 12 + 1:02d}")
    full = M["days"] == pd.to_datetime(M["month"] + "-01").dt.days_in_month
    M["complete"] = full & (M["bad"] == 0)
    M.to_csv(HERE / "data" / "chirps_monthly.csv", index=False)
    out = {"source": "CHIRPS daily (Climate Hazards Center, UCSB) via SERVIR ClimateSERV API datatype 0, "
                     "operationtype 5 (spatial average)", "api": API, "polygon": BOX, "fetched_on": date.today().isoformat(),
           "vintage": "today's (not the vintage available at each past issue date)", "raw_sha256": hashes,
           "monthly_sha256": hashlib.sha256((HERE / "data" / "chirps_monthly.csv").read_bytes()).hexdigest(),
           "months": int(len(M)), "incomplete_months": M.loc[~M["complete"], "month"].tolist()}
    (HERE / "data" / "chirps_hashes.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "raw_sha256"}, indent=1))


if __name__ == "__main__":
    main()
