"""E28 section 8: the API, the dashboard copy, the PDF and the stored outputs agree; the record never classifies an
unvalidated estimate; the ranking and the news coverage served equal the stored ones."""
import hashlib
import json
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from _paths import EXP

BD = EXP / "backend_dev"
REC = BD / "data" / "e28" / "da_brief_record.json"
PDF = BD / "data" / "e28" / "aiPHeed_E28_DA_brief.pdf"
pytestmark = pytest.mark.skipif(not REC.exists(), reason="E28 record not built yet (runner/build_record_e28.py)")


def _client(monkeypatch, rec=REC, pdf=PDF):
    import app.api.v1.quarterly as Q

    monkeypatch.setattr(Q, "E28_RECORD", rec)
    monkeypatch.setattr(Q, "E28_PDF", pdf)
    app = FastAPI()
    app.include_router(Q.router, prefix="/api/v1")
    return TestClient(app)


def test_three_copies_are_byte_identical_and_self_verifying():
    blobs = [p.read_bytes() for p in (REC, EXP / "dashboard_dev" / "public" / "e28_da_brief_record.json",
                                      EXP / "runs" / "e28_da_brief_record.json")]
    assert blobs[0] == blobs[1] == blobs[2]
    rec = json.loads(blobs[0])
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == rec["content_sha256"]


def test_api_serves_the_record_and_the_matching_pdf(monkeypatch):
    c = _client(monkeypatch)
    rec = json.loads(REC.read_text(encoding="utf-8"))
    assert c.get("/api/v1/quarterly/e28/brief").json() == rec
    r = c.get("/api/v1/quarterly/e28/brief.pdf")
    assert r.status_code == 200 and r.headers["X-Record-SHA256"] == rec["content_sha256"]
    assert re.search(rb"/Subject \(([0-9a-f]{64})\)", r.content).group(1).decode() == rec["content_sha256"]
    lr = c.get("/api/v1/quarterly/e28/lgu-ranking").json()
    assert lr["rows"] == rec["lgu_ranking"]["rows"] and len(lr["rows"]) == 142
    assert len(c.get("/api/v1/quarterly/e28/lgu-ranking", params={"province": "Quezon"}).json()["rows"]) == 41
    assert c.get("/api/v1/quarterly/e28/news-coverage").json() == rec["news_coverage"]


def test_tampered_record_is_refused_and_stale_pdf_is_409(monkeypatch, tmp_path):
    rec = json.loads(REC.read_text(encoding="utf-8"))
    bad = dict(rec)
    bad["status_banner"] = "VALIDATED"
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert _client(monkeypatch, rec=p).get("/api/v1/quarterly/e28/brief").status_code == 500
    # a correctly hashed but different record makes the existing PDF stale
    body = {k: v for k, v in bad.items() if k != "content_sha256"}
    bad["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert _client(monkeypatch, rec=p).get("/api/v1/quarterly/e28/brief.pdf").status_code == 409


def test_no_unvalidated_estimate_is_classified_and_missing_inputs_give_no_estimate():
    rec = json.loads(REC.read_text(encoding="utf-8"))
    for b in rec["forecast_quarter"]["provinces"].values():
        assert b["evidence_status"] == "EXPERIMENTAL" and b["category"] is None and b["estimate"] is not None
        assert len(b["drivers"]) == 2 and "not proof of cause" in b["driver_method"]
        assert "Do not allocate" in b["suggested_use"] or b["attention"] in ("MONITOR", "ROUTINE", "UNCERTAIN")
    for b in rec["operational_quarter"]["provinces"].values():
        assert b["estimate"] is None and b["attention"] == "NO_ESTIMATE" and b["missing_inputs"]
    assert "EXPERIMENTAL" in rec["status_banner"]
    assert all(r["evidence_status"] == "EXPERIMENTAL" for r in rec["lgu_ranking"]["rows"])


def test_sealed_probabilities_in_the_record_equal_the_e25_seal():
    import pandas as pd
    import guard28

    seal = pd.read_csv(guard28.E25 / "runs" / "SEAL_E25_20261014T002548Z" / "prospective_forecasts.csv",
                       dtype={"province_code": str})
    s = seal[(seal["target"] == "T1_A") & (seal["arm"] == "PCF21") & (seal["lead"] == 1)].set_index("province_code")
    rec = json.loads(REC.read_text(encoding="utf-8"))
    for code, b in rec["forecast_quarter"]["provinces"].items():
        assert abs(b["estimate"]["p_above_threshold"] - round(float(s.loc[code, "p"]), 4)) < 1e-12
        reg = next(d["contribution"] for d in b["drivers"] if d["factor"].startswith("Regional"))
        prov = next(d["contribution"] for d in b["drivers"] if d["factor"].startswith("Provincial"))
        assert abs(reg + prov - (s.loc[code, "mu_S1"] - s.loc[code, "tau"])) < 2e-3    # exact up to rounding
    lr = {r["province_code"]: r["province_probability"] for r in rec["lgu_ranking"]["rows"]}
    for code in lr:
        assert abs(lr[code] - round(float(s.loc[code, "p"]), 6)) < 1e-9
