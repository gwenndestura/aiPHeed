"""OLD_NEWS PLAN section 2: the approved 2015-2020 GDELT GKG scan, retrieved without any rescan.

    python fetch_gkg.py scan       # ONE capped query into a destination table (maximum_bytes_billed = 1.0e12)
    python fetch_gkg.py download   # page the destination table with `bq head` (tabledata.list: no scan, no cost)
    python fetch_gkg.py cleanup    # delete the dataset after the parquet hash is recorded

`scan` refuses to run if the destination table already exists (the scan is never repeated without asking).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
PLAN = HERE / "PLAN.md"
SQL = HERE / "data" / "gkg_v1_2015_2020.sql"
SQL_SHA = "68eea3ebd7c27c0b7c704771d0542cb92fc10a3a8ca0f0086f4c0b3773074f4c"
RAW = ROOT / "backend" / "data" / "gdelt_e85" / "gkg_calabarzon_2015_2020.parquet"
CHK = HERE / "out" / "checks_fetch.json"
BQ = shutil.which("bq") or "bq"
PROJECT = subprocess.run([shutil.which("gcloud") or "gcloud", "config", "get-value", "project"], capture_output=True,
                         text=True).stdout.strip()
DATASET = f"{PROJECT}:aipheed_old_news"
TABLE = f"{DATASET}.gkg_2015_2020"
MAX_BYTES = 1_000_000_000_000
PAGE = 5000
COLS = ["DATE", "SourceCommonName", "DocumentIdentifier", "V2Themes", "V2Locations", "V2Tone", "V2Counts"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN.md changed after it was hashed"
    return h


def bq(*args, check=True, stdin: str | None = None) -> subprocess.CompletedProcess:
    # bq (a Python program) writes in the Windows console code page unless told otherwise: names such as "Dasmariñas"
    # then do not decode as UTF-8
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    r = subprocess.run([BQ, "--project_id", PROJECT, *args], capture_output=True, text=True, encoding="utf-8",
                       input=stdin, env=env)
    if check and r.returncode != 0:
        raise SystemExit(f"bq {' '.join(args[:2])} failed: {r.stderr.strip()[-600:]} {r.stdout.strip()[-600:]}")
    return r


def load_chk() -> dict:
    return json.loads(CHK.read_text(encoding="utf-8")) if CHK.exists() else {}


def save_chk(c: dict):
    CHK.parent.mkdir(exist_ok=True)
    CHK.write_text(json.dumps(c, indent=1, default=str), encoding="utf-8")


def scan():
    plan = check_plan()
    assert sha(SQL) == SQL_SHA, "the query file changed"
    exists = bq("show", "--format=json", TABLE, check=False)
    assert exists.returncode != 0, f"{TABLE} already exists: the scan is not repeated (use download)"
    if bq("show", "--format=json", DATASET, check=False).returncode != 0:
        bq("mk", "--dataset", "--location=US", DATASET)
    # attempt 1 (job ..._0914a649) failed with invalidQuery and 0 bytes: Windows bq.cmd cut a multi-line argument at its
    # first line break. The query text is now passed on stdin, byte-for-byte the hashed file.
    job = f"oldnews_gkg_2015_2020_{plan[:8]}_r2"
    r = bq("query", "--use_legacy_sql=false", f"--maximum_bytes_billed={MAX_BYTES}", f"--destination_table={TABLE}",
           f"--job_id={job}", "--format=none", stdin=SQL.read_text(encoding="utf-8"))
    j = json.loads(bq("show", "--format=json", "-j", job).stdout)
    st = j.get("statistics", {})
    q = st.get("query", {})
    c = load_chk()
    c.update({"plan_sha256": plan, "query_sha256": SQL_SHA, "job_id": job, "destination": TABLE,
              "bytes_processed": int(q.get("totalBytesProcessed", st.get("totalBytesProcessed", 0))),
              "bytes_billed": int(q.get("totalBytesBilled", 0)), "cache_hit": q.get("cacheHit"),
              "maximum_bytes_billed": MAX_BYTES, "job_state": j.get("status", {}).get("state"),
              "job_error": j.get("status", {}).get("errorResult")})
    t = json.loads(bq("show", "--format=json", TABLE).stdout)
    c["destination_rows"] = int(t["numRows"])
    c["destination_bytes"] = int(t["numBytes"])
    save_chk(c)
    print(json.dumps({k: c[k] for k in ("bytes_processed", "bytes_billed", "destination_rows", "job_state")}, indent=1))


def download():
    check_plan()
    c = load_chk()
    n = c["destination_rows"]
    rows = []
    for start in range(0, n, PAGE):
        r = bq("head", "--format=json", f"--max_rows={PAGE}", f"--start_row={start}", TABLE)
        part = json.loads(r.stdout)
        rows += part
        print(f"rows {start + len(part)} / {n}", flush=True)
    D = pd.DataFrame(rows)[COLS]
    D["DATE"] = D["DATE"].astype("int64")
    assert len(D) == n, f"downloaded {len(D)} rows, table has {n}"
    RAW.parent.mkdir(parents=True, exist_ok=True)
    D.to_parquet(RAW, index=False)
    c.update({"raw_file": str(RAW.relative_to(ROOT)).replace("\\", "/"), "raw_rows": len(D), "raw_sha256": sha(RAW),
              "date_min": int(D["DATE"].min()), "date_max": int(D["DATE"].max())})
    save_chk(c)
    print(json.dumps({k: c[k] for k in ("raw_rows", "raw_sha256", "date_min", "date_max")}, indent=1))


def cleanup():
    c = load_chk()
    assert c.get("raw_sha256") and RAW.exists() and sha(RAW) == c["raw_sha256"], "parquet missing or changed: keep the table"
    bq("rm", "-r", "-f", "--dataset", DATASET)
    c["dataset_deleted"] = True
    save_chk(c)
    print("dataset deleted:", DATASET)


if __name__ == "__main__":
    {"scan": scan, "download": download, "cleanup": cleanup}[sys.argv[1]]()
