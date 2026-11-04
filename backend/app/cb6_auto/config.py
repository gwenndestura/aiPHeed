"""Paths and fixed rules of the automatic C-B6 operation."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND / "data" / "cb6_auto"
SEED = ROOT / "seed"
FROZEN = ROOT / "frozen"

# Every issue date from this one on is forecast by the job; the 2026-10-01 forecast is already in the served export.
FIRST_AUTO_ISSUE = "2027-01-01"
CATCH_UP_DAYS = 14        # CE_PROSPECTIVE_PLAN section 2: a run is valid up to 14 days after the issue date, then MISSED
RETRY_STALE_DAYS = 7      # a stale source is retried daily for 7 days, then the forecast goes out with it recorded
SERVED_LEAD = 2           # the export serves one forecast per quarter, Lead 2


def state_dir() -> Path:
    """Persistent working folder (the Render disk in production). Read at call time so tests can point it elsewhere."""
    return Path(os.getenv("AIPHEED_CB6_STATE_DIR") or ROOT / "state")


def sources_dir() -> Path:
    return state_dir() / "sources"


def news_dir() -> Path:
    return state_dir() / "news_auto"


def ledger_path() -> Path:
    return state_dir() / "forecast_ledger.jsonl"


def run_log_path() -> Path:
    return state_dir() / "run_log.jsonl"


def news_scoring_enabled() -> bool:
    """XLM-RoBERTa needs more memory and disk than a Render starter instance has, so scoring is opt-in. Without scores the
    news input of a new quarter is left missing and recorded as stale, never invented."""
    return os.getenv("AIPHEED_CB6_NEWS_SCORING", "0").strip() == "1"
