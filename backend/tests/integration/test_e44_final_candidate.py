"""
tests/integration/test_e44_final_candidate.py
---------------------------------------------
E44 final five-trigger candidate (AIPHEED_LEAD2_MODEL=e44): serves exactly the frozen I2 forecast, traces every one
of the five trigger groups to model features and contributions, states the lead/target convention, reports that
forecasting acceptance was NOT met, and refuses an expired target. The E38 default is untouched.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

client = TestClient(app)
FROZEN = Path("..") / "aipheed-backend-aligned" / "experiments" / "E44_Five_Trigger_Optimization" / "frozen"
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture
def e44(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e44")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


def test_serves_the_frozen_i2_forecast(e44):
    f = FROZEN / "E44_PROSPECTIVE_2027Q1.json"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == (FROZEN / "E44_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    frozen = json.loads(f.read_text())
    assert frozen["final_candidate"] == "I2" and frozen["forecasting_acceptance_met"] is False
    rows = {r["provinceCode"]: r for r in client.get("/api/v1/provinces?quarter=2027-Q1&horizon=forecast").json()["data"]}
    for v in frozen["provinces"].values():
        assert rows[v["province_code"]]["riskScore"] == pytest.approx(v["I2_p"], abs=5e-4)
        assert rows[v["province_code"]]["scoreType"] == "food_stress_risk_probability"


def test_every_trigger_is_traceable_to_model_features(e44):
    rec = LEAD2.record()
    assert rec["assessment"]["forecastingAcceptanceMet"] is False and rec["assessment"]["finalCandidate"] == "I2"
    for p in rec["provinces"].values():
        c = p["fiveTriggerContributions"]
        assert set(c) == FIVE and all(c[g]["features"] for g in FIVE)
        for g in FIVE:
            st = p["triggerStatus"][g]["status"]
            big = abs(c[g]["foodInflationPoints"]) >= 0.1 or abs(c[g]["hungerPoints"]) >= 0.1
            assert st == ("contributes" if big else "no_effect")
            assert p["triggerStatus"][g]["evidenceNote"]


def test_cards_show_evidence_and_no_unsupported_direction(e44):
    t = {x["key"]: x for x in client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()["triggers"]}
    assert set(t) == FIVE
    for g, x in t.items():
        assert x["status"] in ("contributes", "no_effect")
        assert x["evidenceNote"]
        if x["status"] != "contributes":
            assert x["pct"] == 0


def test_summary_states_the_lead_convention_and_acceptance(e44, monkeypatch):
    s = client.get("/api/v1/lead2/summary").json()
    assert s["timing"] == s["timing"] | {"originQuarter": "2026-Q3", "currentQuarter": "2026-Q4", "targetQuarter": "2027-Q1",
                                         "leadFromOrigin": 2}
    assert s["assessment"]["forecastingAcceptanceMet"] is False
    ind = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2027-Q1&horizon=forecast").json()["indicator"]
    assert ind["id"] == "food_stress_risk_probability" and "not met" in ind["caveat"]
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-20T09:00:00")
    assert client.get("/api/v1/lead2/summary").status_code == 409
    assert client.get("/api/v1/provinces?quarter=2027-Q2&horizon=forecast").status_code == 404


def test_default_remains_e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    rows = client.get("/api/v1/provinces?quarter=2027-Q1&horizon=forecast").json()["data"]
    assert all(r.get("scoreType") is None for r in rows)
    assert client.get("/api/v1/lead2/summary").status_code == 404


def test_notes_and_config_describe_the_served_candidate(e44):
    body = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()
    assert "Every group has inputs in this model" in body["note"] and "only Market / Prices" not in body["note"]
    cfg = client.get("/api/v1/config").json()
    assert cfg["indicator"]["id"] == "food_stress_risk_probability" and "Lead 2" in cfg["indicator"]["horizon"]
    prov = client.get("/api/v1/provinces?quarter=2027-Q1&horizon=forecast").json()
    assert prov["indicator"]["id"] == "food_stress_risk_probability"
    old = client.get("/api/v1/provinces?quarter=2026-Q3&horizon=forecast").json()
    assert old["indicator"]["id"] == "food_stress_risk_probability"     # E46: one score on every quarter


def test_trend_line_uses_one_score_type(e44):
    """E46: the history line never joins the v1 label probabilities (~0.9) to the candidate's probabilities."""
    rec = LEAD2.record()
    for scope, id_ in (("province", "quezon"), ("region", "calabarzon")):
        body = client.get(f"/api/v1/forecast/timeseries?scope={scope}&id={id_}&horizon=forecast").json()
        types = {p["scoreType"] for p in body["series"]}
        assert types == {"food_stress_risk_probability"} and body["indicator"]["id"] == "food_stress_risk_probability"
        qs = [p["quarter"] for p in body["series"]]
        assert qs == sorted(qs) and qs[-1] == "2027-Q1"
    past = {x["targetQuarter"]: x["probability"] for x in rec["provinces"]["PH040300000"]["pastForecasts"]}
    pts = {p["quarter"]: p["riskScore"] for p in client.get(
        "/api/v1/forecast/timeseries?scope=province&id=quezon&horizon=forecast").json()["series"]}
    for q, v in past.items():
        if q in pts:
            assert pts[q] == pytest.approx(v, abs=1e-3)
