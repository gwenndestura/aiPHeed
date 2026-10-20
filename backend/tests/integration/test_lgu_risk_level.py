"""
tests/integration/test_lgu_risk_level.py
----------------------------------------
Each LGU's risk level is the display band of its own index (E45, A. Melindo: the map colours every LGU with the
province risk palette, cutoff 0.50); the index and rank give its relative position inside the province, not a
municipal forecast. A withheld province leaves its LGUs without a level (E53 port), and the municipality timeseries
no longer fails on a missing level.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as svc

client = TestClient(app)
PROVINCES = ["cavite", "laguna", "batangas", "rizal", "quezon"]
BASIS = svc.LGU_POSITION_BASIS


@pytest.mark.parametrize("record", ["e49", "e53"])
@pytest.mark.parametrize("quarter", ["2026-Q4", "2026-Q2"])
def test_every_lgu_has_its_own_index_band(record, quarter, request, monkeypatch):
    if record == "e49":
        request.getfixturevalue("serve_e49")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    level = {p["id"]: p["riskLevel"] for p in client.get(f"/api/v1/provinces?quarter={quarter}").json()["data"]}
    assert set(level) == set(PROVINCES) and all(v in ("high", "low") for v in level.values()), level
    n = 0
    for slug in PROVINCES:
        r = client.get(f"/api/v1/provinces/{slug}/municipalities?quarter={quarter}")
        assert r.status_code == 200
        for m in r.json()["data"]:
            assert m["riskLevel"] == svc.ref.risk_level(m["riskIndex"]), (record, quarter, m["id"])
            assert m["riskIndex"] is not None and m["riskLevelBasis"] == BASIS
            n += 1
    assert n == 142


def test_withheld_province_leaves_its_lgus_without_a_level():
    rows = svc.municipality_summary("2026-Q4", withheld=frozenset({"cavite"}))
    assert all(m["riskLevel"] is None for m in rows if m["provinceId"] == "cavite")
    assert all(m["riskLevel"] in ("high", "low") for m in rows if m["provinceId"] != "cavite")


def test_municipality_timeseries_returns_a_series(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    r = client.get("/api/v1/forecast/timeseries?scope=municipality&id=cavite-gen-mariano-alvarez")
    assert r.status_code == 200, r.text[:300]
    series = r.json()["series"]
    assert len(series) > 0 and all(p["riskLevel"] in ("high", "low") for p in series)
