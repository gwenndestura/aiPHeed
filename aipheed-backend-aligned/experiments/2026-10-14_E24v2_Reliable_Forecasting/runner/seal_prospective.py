"""Prospective (untouched-holdout) forecasts: the ONLY valid test of generalization (protocol §7, criterion C9).

Frozen candidates (definitions fixed in run_e24.py, whose hash is in PROTOCOL_SHA256.txt):
  * E24-F            persistence-gated selection (the pre-registered final candidate)
  * ABL_lgbm_P (T1)  LightGBM on the persistence block   - added AFTER seeing development results (disclosed)
  * ABL_lr_P   (T2)  LR on the persistence block         - added AFTER seeing development results (disclosed)
  * B1..B6, PROPOSED  required comparators

Procedure: for each new origin t >= 2026-Q1, predictions are written and SHA-256-sealed BEFORE the target labels are
opened; scoring happens only after the labels are published and authorized; >= 8 new origins and >= 5 LOW rows are
required before any C9 claim.

This script REFUSES to run unless authorized feature files covering the origin quarter are on the allowlist. As of
2026-10-14 none are (2026 news/government features are not authorized), so it exits with the missing items.
Usage: python -B runner/seal_prospective.py --origin-quarter 2026-Q3"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

REQUIRED_FEATURE_COVERAGE = "news (FSSI, triggers) and 36 government features for the origin quarter and the one before"


def authorized_feature_files_for(quarter: str) -> list[Path]:
    """Allowlisted feature files whose read-time filter reaches `quarter`. None exist for 2026 today."""
    out = []
    for p, (_, flt) in guard.ALLOW.items():
        if flt and flt[0] == "quarter" and str(flt[2]) >= quarter and "features" in p.name:
            out.append(p)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin-quarter", required=True)
    a = ap.parse_args(argv)
    files = authorized_feature_files_for(a.origin_quarter)
    if not files:
        print(f"REFUSED: no authorized feature file covers {a.origin_quarter}. Needed: {REQUIRED_FEATURE_COVERAGE}. "
              "Authorize the files (path + SHA-256) and add them to the guard allowlist; then re-run. "
              "Nothing was read or written.")
        return 2
    raise SystemExit("Authorized files found; implement the sealing run under a new frozen protocol amendment.")


if __name__ == "__main__":
    sys.exit(main())
