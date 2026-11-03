"""
tests/integration/test_report_data_thesis.py
--------------------------------------------
The Visualization-page report payload (GET /api/v1/report/data, app/services/report_data_e31.py, ported from
backend-e53-final) states what the dashboard states:

  * thesis mode with the Chapter I forecast (P0H4) served: every probability, level and rank in the "Risk at a Glance"
    table equals /provinces and /ranking, the CALABARZON row equals the region forecast, and the driver bars equal the
    right-panel explainability; the report names the served model and never describes FIRI v2 (SYSTEM_FIXES item 1);
  * legacy mode (AIPHEED_LEAD2_MODEL unset): the same requests still return a report.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1
from app.ml.inference import thesis_system as T

client = TestClient(app)
PROVINCES = ("batangas", "cavite", "laguna", "quezon", "rizal")
FACTOR = {"market": "Food prices", "employment": "Jobs and employment", "climate": "Weather and climate",
          "fish_kill": "Fisheries production", "ofw_remittance": "Remittances from OFWs",
          "poverty": "Poverty and vulnerability", "news": "News signals", "hunger_indicator": "Regional hunger (indicator)"}


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "ch1")           # these tests cover the Chapter I map mode (opt-in)
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _glance(payload):
    return next(b for b in payload["blocks"] if b["kind"] == "table" and "Rank" in [c["label"] for c in b["columns"]])


def _bars(payload):
    fig = [b for b in payload["blocks"] if b["kind"] == "figure" and b["chart"]["type"] == "bars"]
    return [(b["label"], b["pct"], b["direction"]) for b in fig[0]["chart"]["bars"]] if fig else []


@pytest.mark.parametrize("quarter", ["2026-Q4", "2027-Q1"])
def test_thesis_region_report_equals_the_dashboard(thesis, quarter):
    pl = _get("/api/v1/report/data", type="trend", scope="region", **{"from": "2026-Q1", "to": quarter})
    prov = {p["name"]: p for p in _get("/api/v1/provinces", quarter=quarter)["data"]}
    rank = {r["name"]: r["rank"] for r in _get("/api/v1/ranking", quarter=quarter)["data"]}
    region = _get("/api/v1/forecast", scope="region", id="calabarzon", quarter=quarter)
    for row in _glance(pl)["rows"]:
        if row[0].startswith("CALABARZON"):
            assert row[1:3] == [T.fmt_index(region["riskScore"]), region["riskLevel"].upper()]
            continue
        p = prov[row[0]]
        assert row[1:4] == [T.fmt_index(p["riskScore"]), p["riskLevel"].upper(),
                            f"{p['rank']} of 5" + (" (tied)" if p["rankTied"] else "")]
        assert rank[row[0]] == p["rank"]
    ex = _get("/api/v1/explainability", scope="region", id="calabarzon", quarter=quarter)
    assert _bars(pl) == [(FACTOR[t["key"]], t["pct"], t["direction"]) for t in ex["triggers"] if t["pct"] > 0]
    assert dict(pl["metadata"])["Model"] == CH1.model_line()
    text = json.dumps(pl)
    assert "estimated chance" not in text and "E53" not in text and "E48" not in text
    assert "FIRI" not in text and "not a probability" not in text and "exact share" not in text


@pytest.mark.parametrize("slug", PROVINCES)
def test_thesis_driver_report_equals_the_right_panel(thesis, slug):
    quarter = "2027-Q1"
    pl = _get("/api/v1/report/data", type="shap", scope="province", id=slug, to=quarter)
    p = next(x for x in _get("/api/v1/provinces", quarter=quarter)["data"] if x["id"] == slug)
    row = _glance(pl)["rows"][0]
    assert row[1:3] == [T.fmt_index(p["riskScore"]), p["riskLevel"].upper()]
    ex = _get("/api/v1/explainability", scope="province", id=slug, quarter=quarter)
    assert _bars(pl) == [(FACTOR[t["key"]], t["pct"], t["direction"]) for t in ex["triggers"] if t["pct"] > 0]
    # the served forecast's own indicator groups and input values, never the FIRI v2 domains or the E36 inputs
    titles = [b.get("title") or "" for b in pl["blocks"] if b["kind"] == "table"]
    assert any(t.startswith("Indicator Groups Behind the Forecast") for t in titles)
    assert not any(t.startswith(("Model Inputs", "FIRI v2 Domains")) for t in titles)
    assert "FIRI" not in json.dumps(pl)


def test_legacy_report_data_still_served(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    for params in ({"type": "trend", "scope": "region", "from": "2021-Q1", "to": "2027-Q1"},
                   {"type": "trend", "scope": "province", "id": "quezon", "from": "2021-Q1", "to": "2027-Q1"},
                   {"type": "shap", "scope": "province", "id": "quezon", "to": "2026-Q4"}):
        pl = _get("/api/v1/report/data", **params)
        assert pl["blocks"] and "None" not in json.dumps(pl)


@pytest.mark.parametrize("scope,id_", [("province", "cavite"), ("province", "batangas")])
def test_firi_report_equals_the_dashboard(thesis, scope, id_):
    """Default map model (FIRI v2, as origin/main): the report's index, level and driver bars equal the dashboard's."""
    thesis.delenv("AIPHEED_MAP_MODEL", raising=False)
    quarter = "2027-Q1"
    pl = _get("/api/v1/report/data", type="shap", scope=scope, **({"id": id_} if scope == "province" else {}), to=quarter)
    f = _get("/api/v1/forecast", scope=scope, id=id_, quarter=quarter, horizon="forecast")
    ex = _get("/api/v1/explainability", scope=scope, id=id_, quarter=quarter)
    if scope == "province":
        assert _glance(pl)["rows"][0][1:3] == [T.fmt_index(f["riskScore"]), f["riskLevel"].upper()]
    assert _bars(pl) == [(FACTOR[t["key"]], t["pct"], t["direction"]) for t in ex["triggers"] if t["pct"] > 0]
