"""E29 DA brief record: consistency (API = copies = PDF), E28 content preserved, observed vs experimental separation,
target wording, and sealed records untouched."""
import hashlib
import json
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import _paths  # noqa: F401
from _paths import EXP

BD = _paths.BD
REC = BD / "data" / "e29" / "da_brief_record.json"
PDF = BD / "data" / "e29" / "aiPHeed_E29_DA_brief.pdf"
pytestmark = pytest.mark.skipif(not REC.exists(), reason="E29 record not built yet")


def _c(monkeypatch, rec=REC):
    import app.api.v1.quarterly as Q

    monkeypatch.setattr(Q, "E29_RECORD", rec)
    monkeypatch.setattr(Q, "E29_PDF", PDF)
    a = FastAPI()
    a.include_router(Q.router, prefix="/api/v1")
    return TestClient(a)


def test_copies_api_and_pdf_agree(monkeypatch):
    blobs = [p.read_bytes() for p in (REC, EXP / "dashboard_dev" / "public" / "e29_da_brief_record.json",
                                      EXP / "runs" / "e29_da_brief_record.json")]
    assert blobs[0] == blobs[1] == blobs[2]
    rec = json.loads(blobs[0])
    c = _c(monkeypatch)
    assert c.get("/api/v1/quarterly/e29/brief").json() == rec
    r = c.get("/api/v1/quarterly/e29/brief.pdf")
    assert r.status_code == 200
    assert re.search(rb"/Subject \(([0-9a-f]{64})\)", r.content).group(1).decode() == rec["content_sha256"]
    t = c.get("/api/v1/quarterly/targets").json()
    assert t["T2"]["status"] == "EXPLORATORY_INDICATOR"


def test_e28_content_is_preserved_inside_e29():
    rec = json.loads(REC.read_text(encoding="utf-8"))
    e28 = json.loads((EXP.parent / "E28_Objectives_1_4" / "runs" / "e28_da_brief_record.json").read_text(encoding="utf-8"))
    assert rec["e28_record_sha256"] == e28["content_sha256"]
    for code, b in e28["forecast_quarter"]["provinces"].items():
        x = rec["forecast_quarter"]["provinces"][code]
        assert x["estimate"] == b["estimate"] and x["drivers"] == b["drivers"] and x["attention"] == b["attention"]
    assert [r["risk_index"] for r in rec["lgu_ranking"]["rows"]] == [r["risk_index"] for r in e28["lgu_ranking"]["rows"]]


def test_observed_evidence_is_separated_from_estimates_and_shared_hunger_is_regional():
    from app.quarterly.targets import wording_violations

    rec = json.loads(REC.read_text(encoding="utf-8"))
    ro = rec["regional_observation"]
    assert ro["kind"] == "MEASURED" and "shared by all five provinces" in ro["geographic_level"]
    assert not wording_violations("H", ro["geographic_level"])
    for b in rec["forecast_quarter"]["provinces"].values():
        kinds = {e["kind"] for e in b["evidence_table"]}
        assert {"MEASURED", "EXPERIMENTAL", "UNAVAILABLE"} <= kinds
        assert not any(e["kind"] == "ESTIMATED" for e in b["evidence_table"])        # nothing is validated
        assert b["suitability"].startswith("MONITORING ONLY") and b["category"] is None
        assert not wording_violations("T2", b["observed_price_pressure"]["text"])
        assert "not food insecurity" in b["observed_price_pressure"]["text"]
        hunger_rows = [e for e in b["evidence_table"] if e["item"].startswith("Regional hunger")]
        assert hunger_rows and "regional" in hunger_rows[0]["level"]
    subs = [r for r in rec["lgu_ranking"]["rows"] if r["poverty_lgu_estimate"] is None]
    assert len(subs) == 126 and all(r["ordering_basis"].startswith("population density only") for r in subs)


def test_sealed_records_and_ledgers_are_unchanged():
    import guard29

    seal = guard29.E25 / "runs" / "SEAL_E25_20261014T002548Z"
    meta = json.loads((seal / "SEAL.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((seal / "prospective_forecasts.csv").read_bytes()).hexdigest() == meta["sha256_forecasts"]
    for f in ("T1_A.jsonl", "T2.jsonl"):
        assert (BD / "data" / "ledger" / f).read_bytes() == (guard29.E28 / "backend_dev" / "data" / "ledger" / f).read_bytes()
