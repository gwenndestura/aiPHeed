"""FI9-R reassessment protocol, locked before any candidate was scored (2026-11-03).

    python -m app.fi9r.protocol lock

Known before the lock: FI9 results (data/fi9/baseline_20261103) and the sawtooth metadata analysis
(data/fi9r/out/sawtooth.json: n=300 rounds read ~5 pp lower since 2023-Q2; no sample sizes before 2021).
"""
from __future__ import annotations

import hashlib
import json
import sys

from app.fi9r import OUT, VERSION

PROTOCOL = {
    "version": VERSION,
    "target": "unchanged FI9 target (SWS Balance Luzon hunger > preceding-20-quarter normal + round MOE), Lead 1",
    "evaluation_categories": {
        "A_development": "targets 2010-2017 (used for FI9 selection)",
        "B_previously_examined": "targets 2018 onward (scored in FI7, FI8, FI9; NOT an untouched test)",
        "C_prospective": "forecasts registered before their outcome is published (data/fi9/out/prospective_register.jsonl)",
    },
    "current_model": "C0 = FI9 damped persistence + training-only threshold tau (production)",
    "candidates": {
        "C1_local_level": "Kalman local-level filter of the published series with the published sampling variance as "
                          "observation noise; state variance by maximum likelihood on training quarters; class by "
                          "training-only tau (same inner-fold rule as C0)",
        "C1b_damped_local_level": "C1 filtered level, then damped toward the five-year normal (phi fitted on training)",
        "C2_recalibrated_damped": "C0 with Platt recalibration of its probability fitted on inner out-of-fold "
                                  "training predictions only; class unchanged",
        "C3_<domain>": "C0 level + ridge correction of its residual using one domain's indicators (market, climate, "
                       "employment, remittance, poverty, news); alpha by inner CV on training; diagnostic of "
                       "incremental value beyond persistence",
    },
    "baselines": ["always LOW", "always HIGH", "climatology (training base rate)", "naive persistence", "C0",
                  "FI9 LightGBM (saved FI9 predictions, same origins)", "FI9 logistic (saved)"],
    "interval_methods": {"gaussian": "level +/- 1.96 sigma (current)",
                         "conformal": "level +/- the finite-sample 95% quantile of inner out-of-fold absolute "
                                      "level errors (training only)"},
    "adoption_rule": {
        "historical": ["passes the FI7 reliability rule on A+B (full) and on B",
                       "passes it without the FI7 sawtooth quarters",
                       "ECE (5 bins) <= 0.10 on full",
                       "train-minus-out-of-sample accuracy gap <= 0.10",
                       "Brier better than C0 on full with block-bootstrap P(diff<0) >= 0.90",
                       "Brier better than naive persistence on full with P >= 0.90",
                       "not worse than C0 on B (mean Brier diff <= 0)"],
        "interval": "replace the gaussian interval only if its full-period 95% coverage is outside [0.90, 0.99] and the "
                    "conformal interval's is inside",
        "status": "an adopted candidate is still 'provisional' until prospective (C) evidence exists",
    },
    "diagnostics_not_for_adoption": ["design-aware adjustment of n=300 rounds (sample sizes known only from 2023)",
                                     "release-date robustness: rule-based pre-2021 SWS release dates delayed by 30 days",
                                     "label stability under 12/16/24/28-quarter normals",
                                     "soft-label (label-uncertainty) Brier", "leave-one-HIGH-out influence"],
    "bootstrap": {"block": 4, "reps": 5000, "seed": 7},
}


def digest() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def check() -> str:
    p = OUT / "PROTOCOL_LOCK.json"
    if not p.exists() or json.loads(p.read_text())["sha256"] != digest():
        raise RuntimeError("FI9-R protocol missing or changed after lock")
    return digest()


if __name__ == "__main__" and sys.argv[1:] == ["lock"]:
    from datetime import datetime, timezone
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists():
        sys.exit(f"already locked: {json.loads(p.read_text())['sha256']}")
    p.write_text(json.dumps({"sha256": digest(), "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "protocol": PROTOCOL}, indent=1))
    print(digest())
