"""
tests/integration/test_branch_review_port.py
--------------------------------------------
Items brought from aiPHeed/best-model-methodology-review (BRANCH_REVIEW.md):
  * exact LGU ranks (D-E66-3): ranks use the unrounded index, so 4-dp display rounding creates no artificial ties;
    the displayed index and every score are unchanged; AIPHEED_LGU_EXACT_RANKS=0 restores the rounded-index ranks;
  * LGU traceability (E64, Objective 3): each LGU row states the province estimate it scales, the estimate's source,
    its vulnerability index, the ranking method and the hash of the ranked rows.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as svc
from tests.conftest import _clear_dashboard_caches

client = TestClient(app)
PROVS = ["cavite", "laguna", "batangas", "rizal", "quezon"]


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    monkeypatch.delenv("AIPHEED_LGU_EXACT_RANKS", raising=False)
    _clear_dashboard_caches()
    yield
    _clear_dashboard_caches()


def _rows(q):
    return [m for p in PROVS for m in client.get(f"/api/v1/provinces/{p}/municipalities?quarter={q}").json()["data"]]


@pytest.mark.parametrize("q", ["2026-Q3", "2026-Q4", "2027-Q1"])
def test_exact_ranks_have_no_rounding_ties_and_follow_the_unrounded_index(q):
    rows = _rows(q)
    assert len(rows) == 142 and not any(m["tied"] for m in rows)
    assert len({m["rankRegion"] for m in rows}) == 142
    # within a province, rank order = order of the unrounded index (province estimate x vulnerability)
    for p in PROVS:
        g = sorted((m for m in rows if m["provinceId"] == p), key=lambda m: m["rankInProvince"])
        exact = [m["provinceEstimate"] * m["vulnerabilityIndex"] for m in g]
        assert exact == sorted(exact, reverse=True), (q, p)


def test_the_2026_q4_rounding_tie_is_resolved_without_changing_the_index(monkeypatch):
    by = {m["name"]: m for m in _rows("2026-Q4")}
    pila, sp = by["Pila"], by["San Pablo"]
    assert pila["riskIndex"] == sp["riskIndex"] == 0.1133                    # displayed index unchanged
    assert (pila["rankInProvince"], sp["rankInProvince"]) == (19, 20)        # exact vulnerability decides
    assert pila["vulnerabilityIndex"] > sp["vulnerabilityIndex"]
    monkeypatch.setenv("AIPHEED_LGU_EXACT_RANKS", "0")                       # the rounded-index ranks, as before
    _clear_dashboard_caches()
    by = {m["name"]: m for m in _rows("2026-Q4")}
    assert by["Pila"]["rankInProvince"] == by["San Pablo"]["rankInProvince"] == 19 and by["Pila"]["tied"]


def test_province_scores_and_lgu_indices_are_unchanged_by_exact_ranks(monkeypatch):
    exact = {m["id"]: m["riskIndex"] for m in _rows("2026-Q4")}
    scores = {p["id"]: p["riskScore"] for p in client.get("/api/v1/provinces?quarter=2026-Q4").json()["data"]}
    monkeypatch.setenv("AIPHEED_LGU_EXACT_RANKS", "0")
    _clear_dashboard_caches()
    assert {m["id"]: m["riskIndex"] for m in _rows("2026-Q4")} == exact
    assert {p["id"]: p["riskScore"] for p in client.get("/api/v1/provinces?quarter=2026-Q4").json()["data"]} == scores


def test_every_lgu_row_traces_to_its_province_estimate():
    prov = {p["id"]: p["riskScore"] for p in client.get("/api/v1/provinces?quarter=2026-Q4").json()["data"]}
    for m in _rows("2026-Q4"):
        assert m["provinceEstimate"] is not None and abs(m["provinceEstimate"] - prov[m["provinceId"]]) < 1e-6, m["name"]
        assert m["provinceEstimateSource"]["quarter"] == "2026-Q4"
        assert 0 <= m["vulnerabilityIndex"] <= 1 and len(m["rankingRowsSha256"]) == 64
        assert "ranked on the unrounded index" in m["rankingMethod"]
        assert abs(m["riskIndex"] - round(m["provinceEstimate"] * m["vulnerabilityIndex"], 4)) <= 1e-4
