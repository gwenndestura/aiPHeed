"""Path 1 (RESULTS.md, Investigation C): an input-vintage manifest to be written ON each issue day, beside the sealed
forecasts. It records the UTC time, the SHA-256 of every input file the forecast pipeline reads, the newest SWS round
published before the issue, and the git HEAD. A later audit can then prove which data existed at issue time (the gap found
for the 2026-Q2 production files, which carry no fetch date). Read-only on every input; writes out/manifests/ only.

    python issue_manifest.py --issue 2027-01-01
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
ROOT = EXP.parents[1]
INPUT_DIRS = [ROOT / "backend" / "data" / "inputs", ROOT / "backend" / "data" / "news_e31",
              ROOT / "aipheed-backend-aligned" / "data" / "processed",
              EXP / "E41_Lead2_Audit" / "data_acquired", EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "long"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True, help="issue date, YYYY-MM-DD")
    a = ap.parse_args()
    iss = pd.Timestamp(a.issue)
    now = dt.datetime.now(dt.timezone.utc)
    files = {}
    for d in INPUT_DIRS:
        for p in sorted(d.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                files[str(p.relative_to(ROOT)).replace("\\", "/")] = {"sha256": sha(p), "bytes": p.stat().st_size}
    s = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv")
    s["published"] = pd.to_datetime(s["published"])
    k = s[s["published"] < iss]
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    m = {"issueDate": a.issue, "writtenUtc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
         "writtenBeforeIssueEnds": now.date() <= (iss + pd.Timedelta(days=1)).date(),
         "gitHead": head, "newestSwsBeforeIssue": {"quarter": k.iloc[-1]["quarter"], "published": str(k.iloc[-1]["published"].date())}
         if len(k) else None, "roundsPublishedOnOrAfterIssue": int((s["published"] >= iss).sum()), "files": files}
    out = HERE.parent / "out" / "manifests"
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"issue_{a.issue}_written_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    f.write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(f"{f.name}: {len(files)} files, newest SWS before issue {m['newestSwsBeforeIssue']}, "
          f"written on issue day: {m['writtenBeforeIssueEnds']}, sha256 {sha(f)}")


if __name__ == "__main__":
    main()
