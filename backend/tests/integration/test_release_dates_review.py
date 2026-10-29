"""
tests/integration/test_release_dates_review.py
----------------------------------------------
The owner's PSA release-date collection is kept verbatim; every reported date precedes its forecast issue date; no
date is treated as confirmed without a saved copy; the pre-registered CR-ANC re-score stays locked until every needed
province-month is confirmed; served model unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "release_dates_review.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="release-date review missing")


def test_owner_file_kept_and_rescore_locked():
    r = json.loads(RES.read_text())
    owner = LT / "data" / "psa_cpi_release_dates_owner_research_20261029.csv"
    assert hashlib.sha256(owner.read_bytes()).hexdigest() == r["owner_file_sha256"]
    assert r["needed"]["reference_months"] == 36 and r["needed"]["province_month_checks"] == 180
    assert r["reported"] == 27 and r["reported_rows_all_before_issue"] is True
    assert r["confirmed"] == 0 and r["rescore_can_run"] is False
    tf = pd.read_csv(LT / "data" / "psa_cpi_release_dates_TO_FILL_v2.csv", dtype=str)
    assert len(tf) == 180 and int(tf["release_date_YYYY-MM-DD"].notna().sum()) == 27
    assert not (tf["confirmed_by_owner"].fillna("") == "yes").any()


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL and CH1.reliable_lead() == 1
