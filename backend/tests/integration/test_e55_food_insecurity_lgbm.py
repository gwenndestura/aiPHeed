"""
tests/integration/test_e55_food_insecurity_lgbm.py
--------------------------------------------------
AIPHEED_LEAD2_MODEL=e55 serves the E55 LightGBM food-insecurity risk forecast (target T43: regional SWS hunger above
11.3% AND provincial food-price pressure) with exact TreeSHAP explanations. The record must reproduce the frozen E55
run and frozen 2027-Q1 file, every explanation must reconstruct the price log-odds, and the API must say what the
probability is of (food-insecurity risk, not price pressure alone, not measured prevalence).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

client = TestClient(app)
EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E55_Food_Insecurity_LightGBM"
FROZEN = EXP / "frozen" / "E55_LGBM_PROSPECTIVE_2027Q1.json"
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture
def e55(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e55")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def test_record_is_lightgbm_and_matches_frozen_forecast(e55):
    rec = LEAD2.record()
    frozen = json.loads(FROZEN.read_text())
    assert rec["modelFamily"] == "LightGBM" and rec["targetQuarter"] == frozen["targetQuarter"] == "2027-Q1"
    assert rec["origin"] == frozen["origin"]
    for code, v in rec["provinces"].items():
        f = v["forecast"]
        assert f["probability"] == pytest.approx(frozen["forecasts"][code]["p"], abs=1e-6)
        assert f["scoreType"] == "food_insecurity_risk_probability"
        c = f["components"]
        assert f["probability"] == pytest.approx(c["probabilityHungerElevated"] * c["probabilityPricePressure"], abs=1e-3)
    assert rec["assessment"]["forecastingAcceptanceMet"] is False              # A1 not met (0.733); stated, not hidden
    assert any("A1-A5" in w for w in next(iter(rec["provinces"].values()))["warnings"])


def test_treeshap_explanations_are_exact_and_complete(e55):
    rec = LEAD2.record()
    for v in rec["provinces"].values():
        for e in [v] + list(v["pastDrivers"].values()):
            assert e["checks"]["treeshap_reconstruction_error"] < 1e-9
            assert e["checks"]["probability_reproduction_error"] < 1e-9
            assert set(e["fiveTriggerContributions"]) == FIVE
            assert "otherContribution" in e and "povertyContribution" in e and "hungerGate" in e
            # baseline + all groups (five + poverty + other) = logit of the price-pressure probability
            total = e["baselineLogOdds"] + sum(c["logOddsEffect"] for c in e["fiveTriggerContributions"].values()) \
                + e["otherContribution"]["logOddsEffect"] + e["povertyContribution"]["logOddsEffect"]
            pp = e.get("probabilityPricePressure") or v["forecast"]["components"]["probabilityPricePressure"]
            assert 1 / (1 + math.exp(-total)) == pytest.approx(pp, abs=2e-3)      # rounding of stored 4-dp values
            for d in e["drivers"]["drivers"]:
                s = e["triggerStatus"][d["driver_group"]]
                if s["status"] == "contributes":
                    assert d["group_shap"] == e["fiveTriggerContributions"][d["driver_group"]]["logOddsEffect"]
                    assert (d["direction"] == "increases_risk") == (d["group_shap"] >= 0)
                else:
                    assert d["group_shap"] == 0.0


def test_api_states_the_target_and_method(e55):
    rows = client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()
    assert rows["indicator"]["id"] == "food_insecurity_risk_probability"
    assert "hunger" in rows["indicator"]["definition"] and "not a measured prevalence" in rows["indicator"]["definition"]
    ex = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()
    assert "TreeSHAP" in ex["note"] and "not causes" in ex["note"]
    s = ex["summary"]
    assert s["sentence"].startswith("Food-insecurity risk (high regional hunger together with provincial food-price "
                                    "pressure) in Quezon for 2027-Q1 is forecast LOW")
    assert s["dataStatus"] == "limited" and "OFW Remittance" in s["dataStatusNote"]   # BSP remittances end 2025-Q4


def test_past_quarters_use_e55_backtest_not_another_model(e55):
    rec = LEAD2.record()
    v = rec["provinces"]["PH040300000"]
    past = {x["targetQuarter"]: x for x in v["pastForecasts"]}
    assert "2025-Q3" in past and "observedHigh" in past["2025-Q3"]
    old = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2025-Q3").json()["summary"]
    assert old["estimateKind"] == "backtest"


def test_default_remains_e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert LEAD2.mode() == "e38" and not LEAD2.active()
