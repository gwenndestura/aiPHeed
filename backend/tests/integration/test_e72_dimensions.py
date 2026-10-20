"""E72: the served FIRI v2 estimate explained along the food-security dimensions, through existing fields only.
The served number, class, ranks and colours are unchanged; these tests check that the explanation is exact, faithful
(no SHAP label on an index breakdown), discloses the unobserved utilization dimension and keeps outcomes separate."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import dimensions as D
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import thesis_system as T

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
E72 = ROOT / "aipheed-backend-aligned" / "experiments" / "E72_Final_Thesis_System"
SLUGS = ("cavite", "laguna", "quezon", "rizal", "batangas")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return monkeypatch


def _summary(q, slug, scope="province"):
    r = client.get("/api/v1/explainability", params={"scope": scope, "id": slug, "quarter": q})
    assert r.status_code == 200, r.text[:300]
    return r.json()["summary"]


@pytest.mark.parametrize("quarter", ["2027-Q1", "2026-Q3", "2024-Q2"])
def test_dimension_pushes_reconstruct_the_served_index(thesis, quarter):
    for slug in SLUGS:
        ro = _summary(quarter, slug)["riskOutlook"]
        dims = {d["key"]: d for d in ro["dimensions"]}
        assert list(dims) == list(D.ORDER)
        total = sum(d["push"] for d in dims.values() if d["push"] is not None)
        assert math.isclose(total, ro["index"] - 0.5, abs_tol=5e-4)          # index rounded to 4 dp in the API
        assert dims["UTILIZATION"]["status"] == "not_observed" and dims["UTILIZATION"]["push"] is None
        assert dims["OUTCOME"]["kind"] == "outcome evidence (regional)"
        assert dims["VULNERABILITY"]["kind"] == "cross-cutting risk factor"
        assert "exploratory proxy risk index" in ro["estimateType"]


def test_every_indicator_has_one_role():
    from app.ml.inference import firi as FI
    assert set(D.ROLE_OF) == set(FI.LABELS)


def test_summary_text_is_dimensional_and_labelled_as_proxy(thesis):
    for slug in SLUGS:
        s = _summary("2027-Q1", slug)["sentence"]
        assert "exploratory proxy risk index" in s.split(".")[0] + s.split(".")[1]
        assert "BY FOOD-SECURITY DIMENSION" in s and "Utilization (nutrition, water, health): not observed" in s
        assert "not measured outcomes" in s


def test_factor_cards_do_not_call_the_index_breakdown_shap(thesis):
    rec = LEAD2.record()
    for code in rec["provinces"]:
        for key in T.FIVE_GROUPS:
            txt = T.group_evidence(rec, rec["targetQuarter"], code, key)
            assert "not TreeSHAP values" in txt and "not what causes food insecurity" in txt


def test_without_outcome_diagnostic_is_not_served_as_the_estimate(thesis):
    rec = LEAD2.record()
    for code in rec["provinces"]:
        f = T.firi_for(rec, rec["targetQuarter"], code)
        pub = T.firi_public(f)
        assert pub["index"] == pytest.approx(round(f["firi"], 4))            # served number unchanged
        assert pub["indexWithoutRegionalHunger"] is None or 0 <= pub["indexWithoutRegionalHunger"] <= 1


def test_e72_sentence_matches_its_evidence_files():
    e = T.e72_summary()
    reg = json.loads((E72 / "out" / "regional_outcome.json").read_text())["2"]["metrics"]["C3"]
    assert (e["regional_lead2"]["correct"], e["regional_lead2"]["n"]) == (reg["correct"], reg["n"])
    s = next(x for x in T.performance_tables()["sentences"] if x.startswith("E72"))
    assert f"{reg['correct']} of {reg['n']}" in s and "development quarters" in s and "not credibly better" in s
    assert "utilization is not observed" in s and T.E72_SUMMARY in T.REQUIRED
    assert e["firi_reconstruction_error"] < 1e-5


def test_archive_separates_issued_from_backtest(thesis):
    assert "Back-test estimate" in _summary("2025-Q2", "quezon")["sentence"]
    assert "Back-test estimate" not in _summary("2027-Q1", "quezon")["sentence"]


def test_region_cards_name_the_method(thesis):
    from app.services import dashboard as DB
    assert "not TreeSHAP" in DB.THESIS_REGION_EVIDENCE_NOTE
