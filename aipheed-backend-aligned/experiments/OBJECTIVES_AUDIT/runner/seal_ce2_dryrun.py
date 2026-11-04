"""DRY RUN ONLY: would C-E2's prospective forecast regenerate exactly, and what would its seal record be?

Refits C-E2 (ce2_model._origin, CE2_PREREGISTRATION.md) at one origin from the current data files and compares every
lead with the stored walk-forward fit. Writes a would-be seal record and its SHA-256 to --out (never to
SENIOR_REVIEW/prospective/, never to any ledger). Real sealing of C-E2 needs (a) your approval to add C-E2 to the
prospective registry (prospective_lib / seal_next.py) and (b) the inputs refreshed to what is published at O(t).

    python seal_ce2_dryrun.py --origin 2026-Q3 --out DIR
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce2_model as CE2  # noqa: E402
import ce_model as CE  # noqa: E402

H, V = CE.H, CE.V
PROS = HERE.parent / "SENIOR_REVIEW" / "prospective"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out).resolve()
    assert PROS.resolve() not in [out, *out.parents], "a dry run never writes into prospective/"
    out.mkdir(parents=True, exist_ok=True)
    pre = CE2.check()
    t = H.qi(a.origin)
    CE._init()
    f = CE2._origin(t)
    stored = pd.read_csv(HERE / "out" / "ce2_fits.csv")
    stored = stored[stored["t"] == t].set_index("lead")["p"]
    diff = {int(k): abs(float(p) - float(stored[int(k)])) for k, p in zip(f["lead"], f["p"])}
    rec = {"model": "C-E2", "plan_sha256": pre, "origin": a.origin, "issue_date": H.issue(t).strftime("%Y-%m-%d")
           if hasattr(H.issue(t), "strftime") else str(H.issue(t)),
           "forecasts": [{"lead": int(r.lead), "target": H.qs(int(r.q)), "p": round(float(r.p), 6),
                          "class": "HIGH" if r.p >= .5 else "LOW"} for r in f.itertuples()],
           "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "dry_run": True}
    body = json.dumps(rec, indent=1, sort_keys=True).encode()
    path = out / f"DRYRUN_C-E2_{a.origin}.json"
    path.write_bytes(body)
    res = {"replay_max_abs_diff": max(diff.values()), "replay_matches": max(diff.values()) < 1e-9,
           "would_be_seal_sha256": hashlib.sha256(body).hexdigest(), "file": str(path),
           "lead2": next(x for x in rec["forecasts"] if x["lead"] == 2)}
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
