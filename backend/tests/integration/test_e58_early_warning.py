"""
tests/integration/test_e58_early_warning.py
-------------------------------------------
AIPHEED_LEAD2_MODEL=e58 serves the E56 LightGBM forecast unchanged plus the E58 two-signal early warning. Checks: the
probabilities equal E56's; the warning levels follow the frozen rule; the direction is relative to the latest label
known at the issue date (as of that date, not later); the summary carries the warning text and marks it as a model
warning; the default stays E38.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

client = TestClient(app)
E56_REC = Path("data/e56/e56_record.json")


@pytest.fixture
def e58(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e58")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def _level(ph, pp):
    return "ALERT" if ph >= 0.5 else ("EMERGING" if pp >= 0.5 else "NONE")


def test_probabilities_unchanged_and_rule_applied(e58):
    rec, e56 = LEAD2.record(), json.loads(E56_REC.read_text(encoding="utf-8"))
    for code, v in rec["provinces"].items():
        assert v["forecast"]["probability"] == e56["provinces"][code]["forecast"]["probability"]
        w = v["earlyWarning"]
        assert w["level"] == _level(w["probabilityHigh"], w["probabilityPricePressure"])
        for q, e in v["pastDrivers"].items():
            assert e["probability"] == e56["provinces"][code]["pastDrivers"][q]["probability"]
            ew = e["earlyWarning"]
            assert ew["level"] == _level(e["probability"], e["probabilityPricePressure"])
            assert ew["latestKnownLabelQuarter"] is None or ew["latestKnownLabelQuarter"] < e["originQuarter"]  # as of issue
            if ew["direction"] == "rising":
                assert ew["warn"] and ew["latestKnownLabel"] == "LOW"


def test_2024q2_stale_hunger_case_is_an_emerging_warning(e58):
    """The diagnosed E56 failure: price pressure likely, latest posted hunger 10.3% (2023-Q3) -> EMERGING, rising."""
    s = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2024-Q2").json()["summary"]
    w = s["earlyWarning"][0]
    assert w["level"] == "EMERGING" and w["direction"] == "rising" and w["latestHungerQuarter"] == "2023-Q3"
    assert "Early warning EMERGING" in s["sentence"] and "not an official classification" in s["sentence"]


def test_2027q1_has_no_warning_and_region_says_so(e58):
    s = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2027-Q1").json()["summary"]
    assert all(w["level"] == "NONE" for w in s["earlyWarning"])
    assert "No province has an early warning" in s["sentence"]


def test_default_remains_e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert LEAD2.mode() == "e38" and not LEAD2.active()
