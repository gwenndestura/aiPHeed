"""
tests/integration/test_e168_dashboard.py
----------------------------------------
The approved E168 model (registry e168-lgbm-1.0) drives the dashboard's map, province ranking, LGU ranking, explanation
cards, summary and early warnings (app.ml.inference.map_engine -> e168_system), with exactly the values of the approved
artifact data/e168/out/live_2027.json; AIPHEED_MAP_MODEL=ch1 restores the Chapter I price-pressure index.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e168_system as E
from app.ml.inference import map_engine

client = TestClient(app)
LIVE = json.loads((E.DATA / "live_2027.json").read_text())
pytestmark = pytest.mark.skipif(not E.ROWS.exists(), reason="E168 dashboard export not present")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-11-07T09:00:00")
    monkeypatch.delenv("AIPHEED_MAP_MODEL", raising=False)
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_export_equals_the_approved_artifact():
    live = {(r["province"], r["lead"]): r for r in LIVE["provinces"]}
    rows = list(E.rows().values())
    assert len(rows) == 15
    for r in rows:
        a = live[(r["province"], int(r["lead"]))]
        assert (float(r["score_pct"]), float(r["probability"]), r["class"]) == (a["score_pct"], a["p_high"], a["risk_class"])
        assert r["quarter"] == a["target_quarter"]


def test_group_contributions_add_up_to_the_lightgbm_change():
    for r in E.rows().values():
        parts = sum(float(r[f"shap_{g}"]) for g in E.GROUPS) + sum(float(r[c]) for c in E.OTHER_COLS) + float(r["bias_logit"])
        assert parts == pytest.approx(float(r["change_logit"]), abs=1e-4)


def test_map_engine_selects_e168_and_ch1_on_request(thesis):
    assert map_engine.selected() is E
    thesis.setenv("AIPHEED_MAP_MODEL", "ch1")
    from app.ml.inference import ch1_system
    assert map_engine.selected() is ch1_system


def test_province_map_and_ranking_are_e168(thesis):
    for lead, q in ((1, "2027-Q1"), (2, "2027-Q2"), (3, "2027-Q3")):
        d = _get("/api/v1/provinces", quarter=q)
        assert d["indicator"]["id"] == "e168_food_insecurity_risk"
        live = {r["province"]: r for r in LIVE["provinces"] if r["lead"] == lead}
        assert len(d["data"]) == 5
        for r in d["data"]:
            assert r["riskScore"] == pytest.approx(live[r["name"]]["p_high"], abs=1e-6)
            assert r["riskLevel"] == ("high" if live[r["name"]]["risk_class"] == "HIGH" else "low")
            assert "E168" in r["riskLevelBasis"]
        order = [r["name"] for r in sorted(d["data"], key=lambda r: r["rank"])]
        assert order == [p for p, _ in sorted(((k, v["p_high"]) for k, v in live.items()), key=lambda kv: -kv[1])]


def test_dashboard_opens_on_the_next_quarter(thesis):
    assert _get("/api/v1/quarters")["current"] == "2027-Q1"


def test_timeline_covers_the_three_accepted_leads(thesis):
    q = _get("/api/v1/quarters")
    ids = [t["id"] for t in q.get("timeline", q.get("data", []))] if isinstance(q, dict) else []
    if ids:
        assert {"2027-Q1", "2027-Q2", "2027-Q3"} <= set(ids)


def test_lgu_ranking_starts_from_e168(thesis):
    rows = [r for slug in ("batangas", "cavite", "laguna", "quezon", "rizal")
            for r in _get(f"/api/v1/provinces/{slug}/municipalities", quarter="2027-Q1")["data"]]
    assert len(rows) == 142
    lg = _get("/api/v1/final/lgus")
    assert lg["count"] == 142 and lg["model"] == E.MODEL_ID and lg["quarter"] == "2027-Q1"
    assert lg["label"].startswith("Vulnerability-weighted municipal priority based on the provincial food-insecurity risk forecast")
    same = {r["id"]: r["riskIndex"] for r in rows}
    assert all(r["priorityScore"] == same[r["id"]] for r in lg["rows"])
    prov = {r["province"]: r["p_high"] for r in LIVE["provinces"] if r["lead"] == 1}
    for r in rows:
        assert "E168" in r["riskLevelBasis"] and r["riskLevel"] == "low"
        if r["provinceEstimate"] is not None:
            assert any(r["provinceEstimate"] == pytest.approx(p, abs=1e-6) for p in prov.values())


def test_explanations_are_e168_groups(thesis):
    d = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2027-Q1")
    keys = {t["key"] for t in d["triggers"]}
    assert keys == set(E.GROUPS)
    assert all("E168" in t["statusNote"] for t in d["triggers"])
    assert "validation-pending" not in json.dumps(d)


def test_no_early_warning_when_all_low():
    from app.quarterly import alerts_e168
    assert all(r["risk_class"] == "LOW" for r in LIVE["provinces"])
    assert alerts_e168.candidates() == []
