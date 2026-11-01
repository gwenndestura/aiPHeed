"""Y14 prospective workflow (EXPERIMENT_PLAN.md section 7): issue, side by side, the Lead-2 food-insecurity forecasts
for target quarter t+2 at issue date O(t) and seal them.

Issued: H1 (hunger-persistence probability), the FIRI-analog F1 (equal weights), PERSIST and CLIM, plus every
gate-passing Y14 candidate (none passed; the list is read from out/dev_results.json). The served FIRI v2 and P0H4 are
NOT recomputed here; their own sealed artifacts stay where they are and are never touched.

The sealed file records: issue date, origin and target quarter, the UTC write time, whether it was written on or
before the issue date (only then is it a valid prospective forecast), the newest SWS round used, the forecasts, the
git HEAD, and the SHA-256 of every input file read. It is written to prospective/ under a name containing the UTC
time, refuses to overwrite anything, and records its own SHA-256 in prospective/SEALS.txt (append-only).

    python -B issue_forecast.py --issue 2027-01-01
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pandas as pd  # noqa: E402

import indicators as IND  # noqa: E402
import run as Y  # noqa: E402

R = Y.R
PROS = HERE.parent / "prospective"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inputs() -> list[Path]:
    fs = [R.LONG / f for f in ("cov_cpi.csv", "cov_oni.csv", "cov_ibtracs_par.csv", "cov_lfs.csv", "cov_palay.csv",
                               "sws_area_rounds_full.csv")]
    fs += [R.ROOT / "backend" / "data" / "inputs" / f for f in ("sws_rounds.csv", "lgu_vulnerability.csv")]
    fs += sorted((HERE.parent / "data_acquired").glob("*.csv"))
    return fs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    a = ap.parse_args()
    iss = pd.Timestamp(a.issue)
    assert iss.day == 1 and iss.month in (1, 4, 7, 10), "issue dates are the first day of a quarter"
    t = (iss.year * 4 + (iss.month - 1) // 3) - 1
    now = dt.datetime.now(dt.timezone.utc)
    IND.T_LAST = t
    ind = IND.build()
    d = Y.frame(ind)
    row = d.loc[t]
    kn = R.known("BL", R.issue(t))
    rr = R.rounds()
    q_last = max(kn)
    newest = rr[(rr["area"] == "BL") & (rr["q"] == q_last) & (rr["published"] < R.issue(t))]
    passed = json.loads((HERE.parent / "out" / "dev_results.json").read_text())["passedGate"]
    fc = {"H1": float(row["H1"]), "F1_FIRI_analog": None if pd.isna(row["F1"]) else float(row["F1"]),
          "PERSIST": float(row["PERSIST"]), "CLIM": float(row["CLIM"])}
    for c in passed:
        fc[c] = Y.fit_predict(d, t)[c]
    seal = {"issueDate": a.issue, "origin": R.qs(t), "target": R.qs(t + 2), "targetDefinition": "TFI-2: BL hunger > 11.3",
            "writtenUtc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "validProspective": now.date() <= iss.date(),
            "note": None if now.date() <= iss.date() else "WRITTEN AFTER THE ISSUE DATE: demonstration only, not a prospective forecast",
            "newestSwsUsed": {"quarter": R.qs(q_last), "value": float(kn[q_last]),
                              "lastRoundPublished": str(newest["published"].max().date())},
            "forecasts": fc, "classAt050": {k: (None if v is None else ("HIGH" if v >= 0.5 else "LOW")) for k, v in fc.items()},
            "indicatorsAtIssue": {k: (None if pd.isna(row[k]) else float(row[k])) for k in ("A2", "A3", "C1", "C2", "C3", "C4", "E1", "E2", "H1", "V1")},
            "gatePassingCandidates": passed,
            "gitHead": subprocess.run(["git", "-C", str(R.ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
            "planSha256": (HERE / "PLAN_SHA256.txt").read_text().split()[0],
            "inputs": {str(p.relative_to(R.ROOT)).replace("\\", "/"): sha(p) for p in inputs()}}
    PROS.mkdir(exist_ok=True)
    f = PROS / f"seal_issue_{a.issue}_written_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    assert not f.exists(), "refusing to overwrite"
    f.write_text(json.dumps(seal, indent=1), encoding="utf-8")
    with open(PROS / "SEALS.txt", "a", encoding="utf-8") as g:
        g.write(f"{f.name} {sha(f)} validProspective={seal['validProspective']}\n")
    print(f.name, sha(f)[:16], "valid prospective:", seal["validProspective"])
    print(json.dumps({k: seal[k] for k in ("origin", "target", "newestSwsUsed", "forecasts", "classAt050")}, indent=1))


if __name__ == "__main__":
    main()
