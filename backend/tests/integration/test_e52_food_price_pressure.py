"""
tests/integration/test_e52_food_price_pressure.py
-------------------------------------------------
AIPHEED_LEAD2_MODEL=e52 serves the E52-PS food-price-pressure probability (E46 I7 price component, target PS): the
frozen 2027-Q1 values, the committed development backtest, a faithful five-trigger attribution of exactly that
probability, and a plain-language summary (result, probability, target quarter, top reasons with direction and
evidence, data status, one sentence). The default stays E38 with no summary.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

client = TestClient(app)
EXP = Path("..") / "aipheed-backend-aligned" / "experiments"
E52 = EXP / "E52_Objectives_Acceptance"
I7_RUN = EXP / "E46_Rice_Policy" / "runs" / "i7_20261017T000111Z" / "predictions_i7.csv"
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture
def e52(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e52")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def _qs(t: int) -> str:
    return f"{t // 4}-Q{t % 4 + 1}"


def test_serves_the_frozen_price_pressure_forecast(e52):
    f = E52 / "frozen" / "E52_PS_PROSPECTIVE_2027Q1.json"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == (f.parent / (f.stem + ".sha256")).read_text().split()[0]
    frozen = json.loads(f.read_text())
    i7 = json.loads((EXP / "E46_Rice_Policy" / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json").read_text())
    body = client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()
    assert body["indicator"]["id"] == "food_price_pressure_probability"
    assert "not food insecurity" in body["indicator"]["caveat"]
    rows = {r["name"]: r for r in body["data"]}
    for name, v in frozen["provinces"].items():
        assert rows[name]["riskScore"] == pytest.approx(v["p_price_pressure"], abs=1e-9)
        assert rows[name]["riskScore"] == pytest.approx(i7["provinces"][name]["I7_p_price"], abs=1e-9)
        assert rows[name]["estimateKind"] == "forecast"
    rec = LEAD2.record()
    assert rec["assessment"]["forecastingAcceptanceMet"] is False


def test_backtest_is_the_committed_candidate_and_matches_the_e52_rows(e52):
    rec = LEAD2.record()
    committed = {}
    with I7_RUN.open() as fh:
        for r in csv.DictReader(fh):
            if r["I7_p_price"]:
                committed[(_qs(int(r["t"]) + 2), r["province_code"])] = float(r["I7_p_price"])
    run = sorted((E52 / "runs").glob("2026*/rows.csv"))[0]
    with run.open() as fh:
        e52_rows = {(r["target"], r["province_code"]): (float(r["E52PS_p"]), int(r["y"])) for r in csv.DictReader(fh)}
    n = 0
    for code, v in rec["provinces"].items():
        for x in v["pastForecasts"]:
            k = (x["targetQuarter"], code)
            assert x["probability"] == pytest.approx(committed[k], abs=5e-4)
            if k in e52_rows:
                assert x["observedHigh"] == bool(e52_rows[k][1])
                n += 1
    assert n == rec["assessment"]["E52"]["rows"] == 50
    res = json.loads(sorted((E52 / "runs").glob("2026*/results.json"))[0].read_text())
    assert rec["assessment"]["E52"]["metrics"]["accuracy"] == pytest.approx(res["metrics"]["E52PS"]["accuracy"], abs=1e-3)


def test_attribution_is_of_the_served_probability(e52):
    rec = LEAD2.record()
    for code, v in rec["provinces"].items():
        entries = [v] + list(v["pastDrivers"].values())
        for e in entries:
            assert max(e["checks"].values()) < 1e-8
            contrib = e["fiveTriggerContributions"]
            assert set(contrib) == FIVE and set(e["triggerStatus"]) == FIVE
            for d in e["drivers"]["drivers"]:
                g = d["driver_group"]
                st = e["triggerStatus"][g]["status"]
                assert st in ("contributes", "no_effect", "insufficient_data")
                if st == "contributes":
                    assert d["group_shap"] == contrib[g]["logOddsEffect"]
                    assert (d["direction"] == "increases_risk") == (contrib[g]["logOddsEffect"] >= 0)
                else:
                    assert d["group_shap"] == 0.0
            assert contrib["market"]["hungerPoints"] == 0.0     # the price model has no hunger input
    ex = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()
    assert "food-price pressure" in ex["note"] and "not causes" in ex["note"]
    signed = {t["key"]: t["signedContribution"] for t in ex["triggers"]}
    q = rec["provinces"]["045600000"] if "045600000" in rec["provinces"] else next(
        v for v in rec["provinces"].values() if v["name"] == "Quezon")
    for g, c in q["fiveTriggerContributions"].items():
        if q["triggerStatus"][g]["status"] == "contributes":
            assert signed[g] == pytest.approx(c["logOddsEffect"])


def test_plain_summary_states_result_reasons_evidence_and_data_status(e52):
    rec = LEAD2.record()
    for slug, v in ((v["name"].lower(), v) for v in rec["provinces"].values()):
        ex = client.get(f"/api/v1/explainability?scope=province&id={slug}&quarter=2027-Q1").json()
        s = ex["summary"]
        assert s["targetQuarter"] == "2027-Q1" and s["estimateKind"] == "forecast" and s["issued"] == "2026-10-01"
        assert s["probability"] == pytest.approx(v["forecast"]["probability"], abs=1e-4)
        assert s["result"] == v["forecast"]["decision"] and s["event"] == "food-price pressure"
        assert 1 <= len(s["reasons"]) <= 3
        by_key = {t["key"]: t for t in ex["triggers"]}
        for r in s["reasons"]:
            assert by_key[r["key"]]["status"] == "contributes"
            assert r["direction"] == by_key[r["key"]]["direction"] and r["evidence"]
        assert s["dataStatus"] in ("sufficient", "limited") and s["dataStatusNote"]
        assert s["sentence"].isascii() and s["sentence"].count(".") <= 2 + s["sentence"].count("%")
        assert s["sentence"].startswith(f"Food-price pressure in {v['name']} for 2027-Q1 is forecast {s['result']}")
        assert ex["narrative"].startswith(s["sentence"])


def test_summary_for_backtest_region_and_municipality(e52):
    ex = client.get("/api/v1/explainability?scope=province&id=cavite&quarter=2025-Q3").json()
    s = ex["summary"]
    assert s["estimateKind"] == "backtest" and s["observedOutcome"] in ("HIGH", "LOW")
    assert f"observed {s['observedOutcome']}" in s["sentence"]
    reg = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2027-Q1").json()["summary"]
    rows = client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()["data"]
    assert reg["probability"] == pytest.approx(sum(r["riskScore"] for r in rows) / 5, abs=1e-4)
    assert reg["observedOutcome"] is None
    mun = client.get("/api/v1/explainability?scope=municipality&id=quezon-infanta&quarter=2027-Q1").json()["summary"]
    assert mun["sentence"].startswith("Food-price pressure in Quezon (province of")
    q4 = client.get("/api/v1/explainability?scope=province&id=cavite&quarter=2026-Q4").json()["summary"]
    assert q4["estimateKind"] == "earlier_forecast" and "not yet published" in q4["sentence"]


def test_default_remains_e38_without_summary(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert LEAD2.mode() == "e38" and not LEAD2.active()
    ex = client.get("/api/v1/explainability?scope=province&id=cavite").json()
    assert ex.get("summary") is None
    assert not math.isnan(ex["riskScore"])
