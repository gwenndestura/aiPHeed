"""Y16 external attestation record (Amendment 1 section 4; Y18 X6). Nothing is transmitted by this script.

Same-day manual procedure after a valid seal:
  1. Copy the one-line payload from prospective/attestations/<seal>.attestation.txt (also printed by issue.py).
  2. Send it out of band to an approved independent recipient (e.g. the thesis adviser by e-mail) or an approved
     timestamping service. Which recipient or service is used is the researcher's decision.
  3. Record what happened (append-only):
       python -B attest.py --seal <seal file name> --status completed   --method "e-mail to adviser" --evidence "message id / receipt"
       python -B attest.py --seal <seal file name> --status unavailable --method "none" --evidence "reason"
     A status is never inferred; 'pending' is written automatically at issuance and stays until recorded here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kprospect as K  # noqa: E402


def record(pdir: Path, seal: str, status: str, method: str, evidence: str) -> dict:
    if status not in ("completed", "unavailable"):
        raise ValueError("status must be 'completed' or 'unavailable' ('pending' is set at issuance)")
    if not method.strip() or not evidence.strip():
        raise ValueError("method and evidence are required (what was sent where, and the receipt or the reason)")
    rec = K.reconcile(pdir)
    if not rec["ok"]:
        raise K.IntegrityError("registry inconsistent; resolve before recording attestations")
    f = Path(pdir) / seal
    if not f.exists():
        raise ValueError(f"no such seal: {seal}")
    entry = {"seal": seal, "sealSha256": K.sha(f), "status": status, "method": method, "evidence": evidence,
             "recordedUtc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    K._append_jsonl(Path(pdir) / K.ATTEST_LOG, entry)
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seal", required=True)
    ap.add_argument("--status", required=True, choices=["completed", "unavailable"])
    ap.add_argument("--method", required=True)
    ap.add_argument("--evidence", required=True)
    a = ap.parse_args(argv)
    print(record(K.Y16 / "prospective", a.seal, a.status, a.method, a.evidence))
    return 0


if __name__ == "__main__":
    sys.exit(main())
