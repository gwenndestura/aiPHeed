"""
tests/integration/test_e53_corrected_attribution.py
---------------------------------------------------
AIPHEED_LEAD2_MODEL=e53 serves the E52 food-price-pressure probabilities unchanged (no E53 arm was adopted, D-3) with
the corrected attribution (E53 D-1: every residual input attributed; rice policy -> Market, news_<group> -> its group,
news volume -> other) and per-trigger data coverage, so missing inputs show as limited data, not as "no effect".
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

client = TestClient(app)
E52_REC = Path("data/e52/e52_record.json")
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture
def e53(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e53")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def test_probabilities_are_e52s_unchanged(e53):
    rec, e52 = LEAD2.record(), json.loads(E52_REC.read_text(encoding="utf-8"))
    assert rec["assessment"]["arm"] == "R0" and rec["assessment"]["forecastingAcceptanceMet"] is False
    for code, v in rec["provinces"].items():
        w = e52["provinces"][code]
        assert v["forecast"]["probability"] == pytest.approx(w["forecast"]["probability"], abs=1e-9)
        assert [(x["targetQuarter"], x["probability"], x["observedHigh"]) for x in v["pastForecasts"]] == \
               [(x["targetQuarter"], x["probability"], x["observedHigh"]) for x in w["pastForecasts"]]
    rows = client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()
    assert rows["indicator"]["id"] == "food_price_pressure_probability"


def test_every_input_is_attributed_and_reconciles(e53):
    rec = LEAD2.record()
    some_other = False
    for v in rec["provinces"].values():
        for e in [v] + list(v["pastDrivers"].values()):
            assert max(e["checks"].values()) < 1e-8
            assert set(e["fiveTriggerContributions"]) == FIVE and "otherContribution" in e
            some_other |= e["drivers"]["other_pct"] > 0
            for d in e["drivers"]["drivers"]:
                s = e["triggerStatus"][d["driver_group"]]
                assert 0 <= s["inputsPresent"] <= 1
                if s["status"] == "contributes":
                    assert d["group_shap"] == e["fiveTriggerContributions"][d["driver_group"]]["logOddsEffect"]
    assert some_other                      # news volume is reported as other, not hidden behind other_pct = 0
    ex = client.get("/api/v1/explainability?scope=province&id=cavite&quarter=2027-Q1").json()
    assert "rice-policy orders" in ex["note"] and "not causes" in ex["note"]


def test_missing_inputs_show_as_limited_data(e53):
    rec = LEAD2.record()
    v = next(iter(rec["provinces"].values()))
    assert v["triggerStatus"]["ofw_remittance"]["inputsPresent"] < 1          # BSP remittances end 2025-Q4 in the data
    s = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()["summary"]
    assert s["dataStatus"] == "limited" and "OFW Remittance" in s["dataStatusNote"]
    assert s["sentence"].startswith("Food-price pressure in Quezon for 2027-Q1 is forecast LOW")
    old = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2025-Q3").json()["summary"]
    assert old["estimateKind"] == "backtest" and old["dataStatus"] == "sufficient"


def test_default_remains_e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert LEAD2.mode() == "e38" and not LEAD2.active()
