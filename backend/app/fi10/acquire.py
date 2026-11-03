"""Acquire provincial monthly CPI (PSA OpenSTAT, public API; 2018=100: back-cast 1994-2017 and 2018+) for the five
CALABARZON provinces and the region, items: all items, food, rice. Writes data/fi10/raw/*.csv and MANIFEST.csv.

    python -m app.fi10.acquire
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone

import pandas as pd

from app.fi10 import PROVINCES, RAW

PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TABLES = {"acp28_1994_2017": "2M/PI/CPI/2018NEW/0012M4ACP28.px", "acp22_2018_plus": "2M/PI/CPI/2018NEW/0012M4ACP22.px"}
GEOS = PROVINCES + ["Region IV-A (CALABARZON)", "PHILIPPINES"]
ITEMS = ["0 - ALL ITEMS", "01.1 - FOOD", "01.1.1.12 - Rice"]


def _curl(url, data=None, timeout=240) -> bytes:
    cmd = ["curl", "-s", "-m", str(timeout), "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def _query(path) -> bytes:
    meta = json.loads(_curl(f"{PX}/{path}").decode("utf-8-sig"))
    q = []
    for v in meta["variables"]:
        if v["code"] == "Geolocation":
            vals = [c for c, t in zip(v["values"], v["valueTexts"]) if t.strip(". ") in GEOS]
        elif v["code"] == "Commodity Description":
            vals = [c for c, t in zip(v["values"], v["valueTexts"]) if t.strip(". ") in ITEMS]
        else:
            vals = v["values"]
        q.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
    return _curl(f"{PX}/{path}", json.dumps({"query": q, "response": {"format": "csv"}}))


def run() -> pd.DataFrame:
    rows, frames = [], []
    for name, path in TABLES.items():
        raw = _query(path)
        f = RAW / f"psa_cpi_{name}.csv"
        f.write_bytes(raw)
        rows.append({"file": f.name, "source": f"PSA OpenSTAT {path}", "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        d = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
        id_cols = [c for c in d.columns if not c[:4].isdigit()]
        long = d.melt(id_vars=id_cols, var_name="yp", value_name="value")
        long["year"] = long["yp"].str[:4].astype(int)
        long["mon"] = long["yp"].str[5:].str.strip()
        long = long[long["mon"].isin(MONTHS)].copy()
        long["month"] = long["mon"].map({m: i + 1 for i, m in enumerate(MONTHS)})
        long["value"] = pd.to_numeric(long["value"], errors="coerce")
        long.columns = [c.lower().replace(" ", "_") for c in long.columns]
        long["geolocation"] = long["geolocation"].str.strip(". ")
        long["table"] = name
        frames.append(long.drop(columns=["yp", "mon"]))
    d = pd.concat(frames, ignore_index=True).dropna(subset=["value"])
    d = d.sort_values(["geolocation", "commodity_description", "year", "month", "table"]).drop_duplicates(
        ["geolocation", "commodity_description", "year", "month"], keep="last")      # 2018+ table wins on overlap
    d.to_csv(RAW / "cpi_monthly_long.csv", index=False, lineterminator="\n")
    pd.DataFrame(rows).to_csv(RAW / "MANIFEST.csv", index=False, lineterminator="\n")
    return d


if __name__ == "__main__":
    d = run()
    print(d.groupby(["geolocation", "commodity_description"]).agg(first=("year", "min"), last=("year", "max"), n=("value", "size")).to_string())
