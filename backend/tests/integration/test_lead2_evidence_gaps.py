"""
tests/integration/test_lead2_evidence_gaps.py
---------------------------------------------
LEAD2_EVIDENCE_GAPS: no CPI release date is recorded as verified without evidence (UNKNOWN is never replaced by the
day-10 assumption); the target's provincial variation is the price proxy only; the sealed CR forecasts are intact,
reproduce from the committed snapshot, and no outcome of a sealed quarter exists in the data; served model unchanged.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES, EV = LT / "out" / "evidence_gaps.json", LT / "data" / "psa_cpi_release_evidence.csv"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
CR_SEAL = "dd293e2e36c87be26657b98c51184c5b8b1887bb0252ee4aa65a3dc3a1103da6"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="LEAD2_EVIDENCE_GAPS results missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


def test_release_dates_are_never_assumed_verified(res):
    rows = list(csv.DictReader(EV.open(encoding="utf-8")))
    for r in rows:
        if r["status"] == "VERIFIED":                     # a verified date needs a source URL and a publication date
            assert r["source_url"].startswith("https://") and r["publication_date"][:2] == "20", r
        else:
            assert r["publication_date"] == "UNKNOWN", r
    t = res["timing"]
    assert t["months_checked"] == 18 and t["months_verified"] + t["months_unknown"] == 18
    for x in t["rows"]:
        assert (x["verified_release"] == "UNKNOWN") == (x["available_at_issue"] == "UNKNOWN")
        assert x["verified_release"] != x["assumed_release_day10"] or x["verified_release"] == "UNKNOWN" or any(
            r["status"] == "VERIFIED" and r["reference_month"] == x["refreshed_month"] for r in rows)


def test_target_provincial_variation_is_price_proxy(res):
    t = res["target"]
    assert t["components"]["regional_observed_hunger"]["observed"] is True
    assert t["components"]["province_food_price_pressure"]["is_food_insecurity_measure"] is False
    assert t["lead2_rows"]["hunger_identical_across_provinces"] and t["lead2_rows"]["high_rows_in_hunger_quarters_equal_price_rows"]
    assert t["label_equals_price_share_since_2023Q4"] == 1.0 and t["price_hunger_supported"] is False
    assert t["supports_province_specific_food_insecurity_claims"] is False and t["labels_rebuild_mismatch"] == 0


def test_sealed_cr_forecasts_intact_reproducible_and_unscored(res):
    p = res["prospective"]
    assert p["sha256_recorded"] == CR_SEAL == hashlib.sha256((LT / "sealed" / p["file"]).read_bytes()).hexdigest()
    assert p["targets"] == ["2026-Q4", "2027-Q1", "2027-Q2", "2027-Q3"] and p["rows"] == 20
    assert p["reproduced_from_snapshot_max_abs"] < 1e-5 and p["issue_dates_reproduced"]
    assert p["no_sealed_outcome_in_data"]["ok"] and p["no_sealed_outcome_in_data"]["cpi_last_month"] == "2026-09"
    assert len(p["required_outcomes"]) == 4


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    for v in ("AIPHEED_CH1_ENGINE", "AIPHEED_SWS_REISSUE"):
        monkeypatch.delenv(v, raising=False)
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL and CH1.reliable_lead() == 1
