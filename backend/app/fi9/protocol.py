"""The FI9 evaluation protocol, written and locked before any FI9 number was computed (2026-11-03).

    python -m app.fi9.protocol lock      # writes data/fi9/out/PROTOCOL_LOCK.json (refuses to overwrite)

Known before the lock (disclosed in the reports): the FI7 full-period Lead-1 results (persistence best, LightGBM
not reliable), the FI8 diagnosis, and the class counts per era. The development/test split therefore cannot be
"untouched" in the strict sense: test quarters were already scored by FI7. The split still separates the quarters
used to SELECT the FI9 forecaster from the quarters used to CHECK it; the only untouched evidence is prospective.
"""
from __future__ import annotations

import hashlib
import json
import sys

from app.fi9 import OUT, VERSION

PROTOCOL = {
    "version": VERSION,
    "target": {
        "outcome": "SWS involuntary hunger (% of families), Balance Luzon (Luzon outside Metro Manila)",
        "label": "HIGH when the quarter's hunger exceeds its preceding-20-quarter normal by more than the round's margin "
                 "of error (FI6 label, app/fi6/target.py); numeric outcome: the quarter's hunger level",
        "geography": "regional (Balance Luzon); CALABARZON is ~34% of it; never assigned to provinces or LGUs",
    },
    "horizon": "Lead 1: target = calendar quarter after the issue quarter; issue = last day of the issue quarter's 2nd month",
    "training_rule": "at each issue date train only on rows whose target was published on or before that date",
    "evaluation_targets": "2010-Q1 .. latest published SWS quarter (walk-forward, expanding window)",
    "split": {"development_target_years": [2010, 2017], "test_target_years": [2018, 2100]},
    "candidates": ["Always LOW (reference)", "Naive persistence (latest reading)", "Damped persistence (statistical)",
                   "Logistic regression", "LightGBM (proposed, FI7)", "Government + latest reading (no news)",
                   "PSA/government-only (no SWS, no news)", "NLP/news-only (no SWS)"],
    "no_tuning": "every candidate keeps its FI7 configuration; no hyperparameter or threshold is chosen on FI9 results",
    "reliability_rule_fi7": {"accuracy": 0.75, "recall": 0.50, "precision": 0.50, "auc": 0.70,
                             "brier_below_climatology": True, "every_era_accuracy": 0.60},
    "selection": "on DEVELOPMENT targets only: among candidates passing the reliability rule, lowest Brier; a candidate "
                 "other than naive/damped persistence must also beat naive persistence on development Brier with "
                 "moving-block bootstrap P(diff < 0) >= 0.90. If none passes, the persistence-family member with the "
                 "lower development Brier is served and the forecast is labelled provisional.",
    "validated_lead1_requires": ["passes the reliability rule on the full walk-forward period (>= 10 HIGH quarters)",
                                 "passes it on the test period",
                                 "passes it without the survey-alternation (sawtooth) quarters",
                                 "expected calibration error (5 equal-width bins) <= 0.10 on the full period"],
    "probability_display": "the probability is shown only if Brier < climatology on the test period and ECE <= 0.10; "
                           "otherwise the class is shown with 'probability not calibrated'",
    "ablation": "LightGBM (FI7 features) leaving out one domain's government indicators at a time, and all news; "
                "a domain 'contributes' when removing it raises Lead-1 Brier with bootstrap P >= 0.90",
    "bootstrap": {"block": 4, "reps": 5000, "seed": 7},
}


def digest() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def check() -> str:
    p = OUT / "PROTOCOL_LOCK.json"
    if not p.exists():
        raise RuntimeError("protocol not locked: run python -m app.fi9.protocol lock")
    lock = json.loads(p.read_text())
    if lock["sha256"] != digest():
        raise RuntimeError("PROTOCOL changed after it was locked; evaluation refused")
    return lock["sha256"]


if __name__ == "__main__" and sys.argv[1:] == ["lock"]:
    from datetime import datetime, timezone
    p = OUT / "PROTOCOL_LOCK.json"
    if p.exists():
        sys.exit(f"already locked: {json.loads(p.read_text())['sha256']}")
    p.write_text(json.dumps({"sha256": digest(), "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "protocol": PROTOCOL}, indent=1))
    print(digest())
