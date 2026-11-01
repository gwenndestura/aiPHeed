"""Y16 issuance (EXPERIMENT_PLAN.md section 4; Amendment 1 section 4): seal the PERS and KAL Lead-2 forecasts for one
issue date.

    python -B issue.py --issue 2027-01-01             # valid only on 2027-01-01 .. 2027-01-08 (Manila date)
    python -B issue.py --issue 2026-10-01 --dry-run   # test run, written to dry_runs/, never a valid seal

A real issue always uses the canonical overlay (data/sws_rounds_overlay.csv) and the system clock, writes to
prospective/, and records every attempt (failed or sealed) in prospective/ISSUE_ATTEMPTS.log. After a successful seal,
send the one-line attestation payload in prospective/attestations/ out of band on the same day and record the result
with attest.py (nothing is transmitted by this script).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kprospect as K  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overlay", default=str(K.DEFAULT_OVERLAY), help="dry runs only; a real issue uses the canonical overlay")
    a = ap.parse_args(argv)
    if a.dry_run:
        f = K.issue_seal(a.issue, K.Y16 / "dry_runs", Path(a.overlay), dry_run=True)
    else:
        if Path(a.overlay).resolve() != K.DEFAULT_OVERLAY.resolve():
            msg = f"refusing: a real issue must use the canonical overlay {K.DEFAULT_OVERLAY}"
            K.log_failed_attempt(K.Y16 / "prospective", a.issue, "NonCanonicalOverlay", msg)
            raise SystemExit(msg)
        f = K.issue_with_log(a.issue, K.Y16 / "prospective", K.DEFAULT_OVERLAY)
    s = json.loads(f.read_text(encoding="utf-8"))
    print(f.name, K.sha(f)[:16], "validProspective:", s["validProspective"])
    print(json.dumps({k: s[k] for k in ("origin", "target", "newestSwsUsed", "forecasts", "classAt050", "window")}, indent=1))
    if s["validProspective"]:
        print("\nATTESTATION (send out of band today, then record with attest.py):\n" + K.attestation_payload(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
