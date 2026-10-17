"""
tests/integration/test_e46_corrected_candidate.py
-------------------------------------------------
AIPHEED_LEAD2_MODEL=e46 serves the defect-corrected model I7: exactly the frozen 2027-Q1 forecast (sha-checked),
labelled a forecast, with the acceptance status stated as not met, five trigger groups traced, and every dashboard
quarter carrying the same score (I7's own as-of backtest / earlier Lead-2 forecast). The default stays E38.
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
FROZEN = Path("..") / "aipheed-backend-aligned" / "experiments" / "E46_Rice_Policy" / "frozen"
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture
def e46(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e46")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def test_serves_the_frozen_corrected_forecast(e46):
    f = FROZEN / "E46_I7_PROSPECTIVE_2027Q1.json"
    digest = hashlib.sha256(f.read_bytes()).hexdigest()
    assert digest == (FROZEN / "E46_I7_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    frozen = json.loads(f.read_text())
    rec = LEAD2.record()
    assert rec["sources"]["frozen_sha256"] == digest and rec["origin"] == "2026-10-01"
    rows = {r["name"]: r for r in client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()["data"]}
    for name, v in frozen["provinces"].items():
        assert rows[name]["riskScore"] == pytest.approx(v["I7_p"], abs=1e-9)
        assert rows[name]["estimateKind"] == "forecast" and rows[name]["observedOutcome"] is None
    for v in rec["provinces"].values():
        assert v["forecast"]["kind"].startswith("FORECAST") and v["forecast"]["decisionThreshold"] == 0.5


def test_acceptance_is_not_claimed_and_triggers_are_traced(e46):
    rec = LEAD2.record()
    assert rec["assessment"]["forecastingAcceptanceMet"] is False and rec["assessment"]["finalCandidate"] is None
    assert any("ACCEPTANCE NOT MET" in w for v in rec["provinces"].values() for w in v["warnings"])
    for v in rec["provinces"].values():
        assert set(v["fiveTriggerContributions"]) == FIVE and set(v["triggerStatus"]) == FIVE
    t = client.get("/api/v1/explainability?scope=province&id=cavite&quarter=2027-Q1").json()["triggers"]
    assert {x["key"] for x in t} == FIVE and all(x["status"] in ("contributes", "no_effect") for x in t)
    ind = client.get("/api/v1/config").json()["indicator"]
    assert ind["id"] == "food_stress_risk_probability" and "not met" in ind["caveat"]


def test_every_quarter_is_the_same_score(e46):
    rec = LEAD2.record()
    for q in ("2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"):
        body = client.get(f"/api/v1/provinces?quarter={q}&horizon=nowcast").json()
        assert body["indicator"]["id"] == "food_stress_risk_probability" and len(body["data"]) == 5
    q4 = {r["provinceCode"]: r["riskScore"] for r in
          client.get("/api/v1/provinces?quarter=2026-Q4&horizon=nowcast").json()["data"]}
    assert q4 == {c: pytest.approx(v["earlierForecasts"][0]["probability"]) for c, v in rec["provinces"].items()}
    ts = client.get("/api/v1/forecast/timeseries?scope=region&id=calabarzon&horizon=nowcast").json()["series"]
    assert {p["scoreType"] for p in ts} == {"food_stress_risk_probability"} and ts[-1]["quarter"] == "2027-Q1"


def test_default_remains_e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")
    assert client.get("/api/v1/lead2/summary").status_code == 404


def test_past_quarters_carry_their_own_as_of_triggers(e46):
    """E47: every past quarter on the timeline shows the five trigger groups attributed by the model refitted at that
    quarter's own issue date (never 'not recorded', never another quarter's or another model's drivers)."""
    rec = LEAD2.record()
    shown = {r["provinceCode"]: r["riskScore"] for r in
             client.get("/api/v1/provinces?quarter=2026-Q3&horizon=nowcast").json()["data"]}
    for code, v in rec["provinces"].items():
        assert {"2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"} <= set(v["pastDrivers"])
        assert v["pastDrivers"]["2026-Q3"]["origin"] == "2026-04-01"
        assert v["pastDrivers"]["2026-Q3"]["probability"] == pytest.approx(shown[code], abs=1e-3)
    # Lead 2: the target quarter q is issued after quarter q-2, so its evidence names q-2 (typhoons in that quarter)
    for q, origin_q in (("2026-Q2", "2025-Q4"), ("2026-Q3", "2026-Q1"), ("2026-Q4", "2026-Q2")):
        t = client.get(f"/api/v1/explainability?scope=province&id=quezon&quarter={q}").json()["triggers"]
        assert {x["key"] for x in t} == FIVE
        assert all(x["status"] in ("contributes", "no_effect") and x["evidenceNote"] for x in t)
        assert any(x["status"] == "contributes" for x in t)
        climate = next(x for x in t if x["key"] == "climate")
        assert origin_q in climate["evidenceNote"]             # the evidence is that issue date's own inputs
    region = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q2").json()["triggers"]
    assert {x["key"] for x in region} == FIVE and all(x["status"] != "not_recorded" for x in region)
