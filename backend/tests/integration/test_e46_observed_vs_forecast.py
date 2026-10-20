"""
tests/integration/test_e46_observed_vs_forecast.py
--------------------------------------------------
E46 defect: with a Lead-2 candidate enabled, the dashboard's "Observed" quarters showed the E31/E36 probability of the
v1 label (about 0.98) while the forecast quarter showed the candidate's probability of T43 (about 0.2): two models
and two target events on one timeline. Now every quarter shows the candidate's own estimate of its own event (as-of
backtest, earlier Lead-2 forecast, issued forecast) or is unavailable; the default (E38) mode is unchanged.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2
from app.services import reference as ref

# E53 port (tina-e53-port): this E41-E48 candidate test runs under Angel's original configuration (E36 record,
# lead-2 target, no preview); the served default is now E53 (see tests/integration/test_e53_served_model.py).
pytestmark = pytest.mark.usefixtures("angel_original_config")
client = TestClient(app)
WINDOW = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"]
CAND = "food_stress_risk_probability"


@pytest.fixture
def e44(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e44")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def _prov(q):
    return client.get(f"/api/v1/provinces?quarter={q}&horizon=nowcast").json()


def test_every_timeline_quarter_shows_one_score(e44):
    rec = LEAD2.record()
    for q in WINDOW:
        body = _prov(q)
        assert body["indicator"]["id"] == CAND
        assert {r["scoreType"] for r in body["data"]} == {CAND} and len(body["data"]) == 5
    past = {(c, x["targetQuarter"]): x for c, v in rec["provinces"].items() for x in v["pastForecasts"]}
    for r in _prov("2026-Q3")["data"]:
        x = past[(r["provinceCode"], "2026-Q3")]
        assert r["riskScore"] == pytest.approx(x["probability"]) and r["estimateKind"] == "backtest"
        assert r["observedOutcome"] == ("HIGH" if x["observedHigh"] else "LOW")
        assert "Backtest" in r["horizonLabel"] and "Observed outcome" in r["horizonLabel"]
    earlier = {c: v["earlierForecasts"][0] for c, v in rec["provinces"].items()}
    for r in _prov("2026-Q4")["data"]:
        assert r["riskScore"] == pytest.approx(earlier[r["provinceCode"]]["probability"])
        assert r["estimateKind"] == "earlier_forecast" and r["observedOutcome"] is None
    assert {r["estimateKind"] for r in _prov("2027-Q1")["data"]} == {"forecast"}


def test_the_v1_label_probability_never_appears(e44):
    """Before the fix 2026-Q1..Q4 showed 0.65-0.9998 (E36 v1 label); the candidate's values are its own."""
    rec = LEAD2.record()
    allowed = {round(x["probability"], 4) for v in rec["provinces"].values()
               for x in v["pastForecasts"] + v["earlierForecasts"]}
    allowed |= {round(LEAD2.probability(v), 4) for v in rec["provinces"].values()}
    for q in WINDOW:
        assert all(round(r["riskScore"], 4) in allowed for r in _prov(q)["data"])


def test_quarters_without_a_candidate_estimate_are_unavailable(e44):
    qs = {q["id"]: q for q in client.get("/api/v1/quarters?horizon=nowcast").json()["quarters"]}
    have = set(LEAD2.candidate_quarters())
    for qid, q in qs.items():
        if qid not in have:
            assert q["state"] == "unavailable" and "not a low score" in q["reason"]
            assert client.get(f"/api/v1/provinces?quarter={qid}&horizon=nowcast").status_code == 404
    assert all(qs[q]["state"] != "unavailable" for q in WINDOW)


def test_trend_cards_map_and_triggers_agree(e44):
    ts = client.get("/api/v1/forecast/timeseries?scope=province&id=quezon&horizon=nowcast").json()["series"]
    cards = {q: client.get(f"/api/v1/forecast?scope=province&id=quezon&quarter={q}&horizon=nowcast").json()["riskScore"]
             for q in WINDOW}
    pts = {p["quarter"]: p for p in ts}
    for q in WINDOW:
        assert pts[q]["riskScore"] == pytest.approx(cards[q]) and pts[q]["scoreType"] == CAND
    assert [pts[q]["isForecast"] for q in WINDOW] == [False, False, False, True, True]
    lgus = client.get("/api/v1/provinces/quezon/municipalities?quarter=2026-Q3").json()["data"]
    assert len(lgus) == 41 and all(x["riskLevel"] == ref.risk_level(x["riskIndex"]) for x in lgus)
    t = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q3").json()["triggers"]
    assert {x["key"] for x in t} == {"market", "climate", "fish_kill", "employment", "ofw_remittance"}
    assert all(x["status"] == "not_recorded" and x["pct"] == 0 for x in t)


def test_default_mode_is_unchanged(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")
    for q in WINDOW:
        body = _prov(q)
        assert body["indicator"]["id"] == "food_insecurity_risk_probability"
        assert all(r.get("scoreType") is None and r.get("estimateKind") is None for r in body["data"])
