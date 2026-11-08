"""Re-pull the PSA OpenSTAT sources behind FIRI v2 indicators A1-A3, C3, C4 and E1 (2021+) and record the raw
responses, so every held input file can be checked value by value against the publisher's current table.

    python pull_public.py           # writes data/raw/psa_<table>.csv and data/pull_log.json

Only 2021+ periods are requested (study window). Nothing here is a model input until reconcile.py compares it.
"""
from __future__ import annotations

import io
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB"
UA = "Mozilla/5.0 (aiPHeed thesis research; DLSU-D)"
PROVS = ["Cavite", "Laguna", "Batangas", "Rizal", "Quezon"]
TABLES = {
    "cpi_ACP22": ("2M/PI/CPI/2018NEW/0012M4ACP22.px",
                  {"Commodity Description": ["0 - ALL ITEMS", "01.1 - FOOD"]}),
    "rice_wholesale_AWB01": ("2M/NWSNEW/0052M4AWB01.px", {}),
    "palay_corn_EVCP0": ("2E/CS/0012E4EVCP0.px", {}),
    "fisheries_GVFP1": ("2E/FS/0132E4GVFP1.px", {}),
    "lfs_FKEI2": ("1B/LFS/0021B3FKEI2.px", {}),
}


def curl(url: str, data: str | None = None) -> bytes:
    cmd = ["curl", "-s", "-m", "300", "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def query(path: str, fixed: dict) -> tuple[pd.DataFrame, dict]:
    meta = json.loads(curl(f"{PX}/{path}").decode("utf-8-sig"))
    q, sel_log = [], {}
    for v in meta["variables"]:
        codes, texts = v["values"], [t.strip(". ") for t in v["valueTexts"]]
        name = v["code"]
        if name in fixed:
            keep = [c for c, t in zip(codes, texts) if t in fixed[name] or v["valueTexts"][codes.index(c)] in fixed[name]]
        elif any(t in PROVS for t in texts):                    # geography: the five provinces only
            keep = [c for c, t in zip(codes, texts) if t in PROVS or t.upper() in ("PHILIPPINES", "REGION IV-A (CALABARZON)")]
        elif name.lower() == "year" or all(t[:4].isdigit() for t in texts[:3]):
            keep = [c for c, t in zip(codes, texts) if t[:4].isdigit() and int(t[:4]) >= 2020]
        else:
            keep = codes
        q.append({"code": name, "selection": {"filter": "item", "values": keep}})
        sel_log[name] = len(keep)
    body = json.dumps({"query": q, "response": {"format": "csv"}})
    raw = curl(f"{PX}/{path}", body)
    return pd.read_csv(io.BytesIO(raw), encoding="latin-1"), {"variables": sel_log, "bytes": len(raw)}


def main():
    log = {"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tables": {}}
    for name, (path, fixed) in TABLES.items():
        try:
            d, info = query(path, fixed)
            d.to_csv(RAW / f"psa_{name}.csv", index=False)
            log["tables"][name] = {"path": path, "rows": len(d), "cols": len(d.columns), **info, "status": "ok"}
        except Exception as exc:                                   # record the failure; never fabricate a table
            log["tables"][name] = {"path": path, "status": f"failed: {exc!r}"}
        print(name, log["tables"][name].get("status"), log["tables"][name].get("rows"))
        time.sleep(3)
    (HERE.parent / "data" / "pull_log.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
