"""
tests/integration/test_e43_five_trigger.py
------------------------------------------
E43 five-trigger food-stress risk candidate (AIPHEED_LEAD2_MODEL=e43): equals its frozen forecast, says what its score
is, exposes all five triggers' evidence and status (never a direction without model input), shows the five-trigger
LightGBM separately, and never serves an expired forecast. The E38 default is untouched.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

# E53 port (tina-e53-port): this E41-E48 candidate test runs under Angel's original configuration (E36 record,
# lead-2 target, no preview); the served default is now E53 (see tests/integration/test_e53_served_model.py).
pytestmark = pytest.mark.usefixtures("angel_original_config")
client = TestClient(app)
E43 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E43_Five_Trigger_Risk" / "frozen"
TRIGGERS = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture
def e43(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e43")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


def test_frozen_forecast_is_intact_and_served_exactly(e43):
    f = E43 / "E43_PROSPECTIVE_2027Q1.json"
    want = (E43 / "E43_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    assert hashlib.sha256(f.read_bytes()).hexdigest() == want
    frozen = json.loads(f.read_text())
    rows = {r["provinceCode"]: r for r in client.get("/api/v1/provinces?quarter=2027-Q1&horizon=forecast").json()["data"]}
    for v in frozen["provinces"].values():
        r = rows[v["province_code"]]
        assert r["riskScore"] == pytest.approx(v[f"{frozen['served_arm']}_p"], abs=5e-4)
        assert r["scoreType"] == "food_stress_risk_probability"


def test_indicator_describes_the_food_stress_target(e43):
    ind = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2027-Q1&horizon=forecast").json()["indicator"]
    assert ind["id"] == "food_stress_risk_probability"
    assert "SWS" in ind["definition"] and "not independently verified household food insecurity" in ind["definition"]
    # E46: a past quarter carries the candidate's own score (backtest) or is unavailable; never the v1 label
    r = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2026-Q3&horizon=forecast")
    assert r.status_code == 404 or r.json()["indicator"]["id"] == "food_stress_risk_probability"


@pytest.mark.parametrize("scope,id_", [("province", "quezon"), ("region", "calabarzon")])
def test_trigger_cards_follow_the_record_status(e43, scope, id_):
    t = {x["key"]: x for x in client.get(f"/api/v1/explainability?scope={scope}&id={id_}&quarter=2027-Q1").json()["triggers"]}
    assert set(t) == TRIGGERS
    assert t["market"]["status"] in ("contributes", "no_effect")
    for g in ("climate", "fish_kill", "employment"):
        assert t[g]["status"] == "data_not_in_model" and t[g]["pct"] == 0
    assert t["ofw_remittance"]["status"] in ("stale", "data_not_in_model") and t["ofw_remittance"]["pct"] == 0
    assert all(x["statusNote"] for x in t.values())


def test_record_exposes_all_five_triggers_and_the_five_trigger_model(e43):
    rec = LEAD2.record()
    assert rec["schema"] == "e43/1"
    for p in rec["provinces"].values():
        assert set(p["triggerStatus"]) == TRIGGERS
        ob = p["observed"]
        assert {"climate", "fisheries", "employment", "ofwRemittance", "foodInflationLatestMonths", "hungerRegional"} <= set(ob)
        assert ob["hungerRegional"]["level"].startswith("region")
        assert ob["employment"]["level"] == "national only" and ob["ofwRemittance"]["level"] == "national only"
        assert set(p["fiveTriggerModel"]["groupContributionsLogOdds"]) >= TRIGGERS
        f = p["forecast"]
        assert abs(f["components"]["regionalHungerAbove11_3"] * f["components"]["provincialPriceSignal"] - f["probability"]) < 0.2
        assert all(x["targetQuarter"] <= "2026-Q3" for x in p["pastForecasts"])


def test_summary_and_expiry(e43, monkeypatch):
    s = client.get("/api/v1/lead2/summary").json()
    assert s["targetQuarter"] == "2027-Q1" and all(p["scoreType"] == "food_stress_risk_probability" for p in s["provinces"])
    assert s["evaluation"]["gates"]["classification"].startswith("insufficient evidence")
    monkeypatch.setenv("AIPHEED_NOW", "2027-04-02T09:00:00")
    assert client.get("/api/v1/lead2/summary").status_code == 409
    assert client.get("/api/v1/provinces?quarter=2027-Q2&horizon=forecast").status_code == 404
