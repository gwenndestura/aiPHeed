"""
tests/integration/test_e42_lead2.py
-----------------------------------
E42: trigger cards carry a status (never a direction for a group with no model input or no data), the E42 record keeps
the E41 forecast and adds variants / signal count / trigger status / backtest, frozen forecasts are preserved, and the
target rule refuses stale forecasts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as E41

client = TestClient(app)
EXP = Path("..") / "aipheed-backend-aligned" / "experiments"
STATUSES = {"contributes", "no_effect", "no_model_input", "no_data"}


def _triggers(scope="province", id_="quezon", quarter="2027-Q1"):
    return {t["key"]: t for t in client.get(f"/api/v1/explainability?scope={scope}&id={id_}&quarter={quarter}").json()["triggers"]}


@pytest.mark.parametrize("mode", ["e38", "e42"])
def test_trigger_status_never_implies_a_direction_without_input(monkeypatch, mode):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", mode)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    for scope, id_ in (("province", "quezon"), ("region", "calabarzon")):
        t = _triggers(scope, id_)
        assert set(t) == {"market", "climate", "fish_kill", "employment", "ofw_remittance"}
        assert all(v["status"] in STATUSES and v["statusNote"] for v in t.values())
        assert t["ofw_remittance"]["status"] == "no_data"
        for k in ("climate", "fish_kill", "employment"):
            assert t[k]["status"] == "no_model_input" and t[k]["pct"] == 0
        assert t["market"]["status"] in ("contributes", "no_effect")
        assert all(v["pct"] == 0 for v in t.values() if v["status"] != "contributes")


@pytest.fixture
def e42(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e42")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


def test_e42_record_keeps_the_e41_forecast_and_adds_evidence(e42):
    e41 = json.loads(Path("data/e41/e41_lead2_record.json").read_text(encoding="utf-8"))
    rec = E41.record()
    assert rec["schema"] == "e42/1" and rec["targetQuarter"] == "2027-Q1"
    for code, p in rec["provinces"].items():
        f = p["forecast"]
        assert f["probabilityAbove4pct"] == e41["provinces"][code]["forecast"]["probabilityAbove4pct"]
        lo, hi = f["variantRange"]
        assert lo <= f["probabilityAbove4pct"] <= hi and len(f["variants"]) == 5
        sc = p["signalCount"]
        assert sc["value"] == sum(sc["components"].values())
        assert set(p["triggerStatus"]) == {"market", "climate", "fish_kill", "employment", "ofw_remittance"}
        assert p["triggerStatus"]["ofw_remittance"]["status"] == "no_data"
        past = p["pastForecasts"]
        assert past and all(x["targetQuarter"] <= "2026-Q3" for x in past)
        assert all(x["observedAbove4pct"] == (x["observedFoodInflation"] > 4.0) for x in past)
        assert "not forecasts issued live" in p["pastForecastsNote"]


def test_e42_summary_reports_the_assessment(e42):
    s = client.get("/api/v1/lead2/summary").json()
    assert s["assessment"]["e42_classification_of_PS"].startswith("Insufficient evidence")
    assert "exploratory_signal_count" in s["scoreTypes"]
    assert all(p["signalCount"] in (0, 1, 2) and p["variantRange"] for p in s["provinces"])


def test_e42_refuses_a_stale_target(e42, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2027-04-02T09:00:00")
    assert client.get("/api/v1/lead2/summary").status_code == 409


@pytest.mark.parametrize("folder,stem", [("E38_Lead2_Diagnosis_Tuning", "E38_PROSPECTIVE_2027Q1"),
                                         ("E41_Lead2_Audit", "E41_PROSPECTIVE_2027Q1"),
                                         ("E42_Lead2_Improvement", "E42_PROSPECTIVE_2027Q1")])
def test_historical_frozen_forecasts_are_preserved(folder, stem):
    f = EXP / folder / "frozen" / f"{stem}.json"
    want = (EXP / folder / "frozen" / f"{stem}.sha256").read_text().split()[0]
    got = hashlib.sha256(f.read_bytes()).hexdigest()
    got_lf = hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert want in (got, got_lf)


def test_indicator_matches_the_score_served(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e42")
    f = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2027-Q1&horizon=forecast").json()
    assert f["indicator"]["id"] == "price_pressure_probability" and "not food insecurity" in f["indicator"]["caveat"]
    old = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2026-Q3&horizon=forecast").json()
    assert old["indicator"]["id"] == "food_insecurity_risk_probability"
    ts = client.get("/api/v1/forecast/timeseries?scope=province&id=quezon&horizon=forecast").json()["series"]
    types = {p["quarter"]: p["scoreType"] for p in ts}
    assert types.get("2027-Q1") == "price_pressure_probability"
    # E46: a trend line carries one score type; past quarters come from the candidate's own backtest
    assert set(types.values()) == {"price_pressure_probability"}
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e38")
    f = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2027-Q1&horizon=forecast").json()
    assert f["indicator"]["id"] == "food_insecurity_risk_probability"
