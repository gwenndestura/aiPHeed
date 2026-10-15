"""E27: the API, the dashboard copy, the PDF and the ledger agree, and the record keeps E25's numbers unchanged."""
import hashlib
import json
import re
import shutil

import pytest

import _paths  # noqa: F401
from _paths import EXP
from app.quarterly.ledger import Ledger

BD = _paths.BD
REC = BD / "data" / "e27" / "timeline_record.json"
PDF = BD / "data" / "e27" / "aiPHeed_E27_forecast_report.pdf"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def e25():
    return json.loads((BD / "data" / "e25" / "e25_forecast_record.json").read_text(encoding="utf-8"))


def _pdf_text(path):
    b = path.read_bytes()
    return " ".join(m.decode("latin-1") for m in re.findall(rb"\(((?:[^()\\]|\\.)*)\) Tj", b))


def test_three_copies_are_byte_identical_and_self_verifying(rec):
    blobs = {p: p.read_bytes() for p in (REC, EXP / "dashboard_dev" / "public" / "e27_timeline_record.json",
                                         EXP / "runs" / "e27_timeline_record.json")}
    assert len(set(blobs.values())) == 1
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == rec["content_sha256"]


def test_backtest_numbers_are_e25_numbers_unchanged(rec, e25):
    old = {q["quarter"]: q for q in e25["quarters"]}
    n = 0
    for q in rec["quarters"]:
        if q["state"] != "BACKTEST":
            continue
        for c in PROVS:
            f = old[q["quarter"]]["provinces"][c].get("forecast")
            r = q["provinces"][c]["risk"]
            assert (f is None) == (r is None)
            if f:
                assert r["p_above_threshold"] == f["p_high"] and r["S1_80pct_interval"] == f["S1_80pct_interval"]
                assert r["approved_label_measured"] == old[q["quarter"]]["provinces"][c]["actual_label"]
                n += 1
    assert n == 20                           # 4 back-test quarters with a forecast (2025-Q2/Q3 have no label)


def test_no_unvalidated_forecast_carries_a_high_low_decision(rec):
    assert rec["evidence_summary"]["status"] == "EXPERIMENTAL"
    for q in rec["quarters"]:
        for d in q["provinces"].values():
            for v in (d.get("risk"), d.get("experimental_estimate")):
                if v:
                    assert v["evidence"]["status"] == "EXPERIMENTAL" and v["decision"] is None
                    assert "not validated" in v["display_label"]


def test_layers_are_separate_and_price_pressure_is_labelled_constructed(rec):
    for q in rec["quarters"]:
        assert "REGIONAL" in q["regional_layer"]["what"]
        for d in q["provinces"].values():
            if d.get("price_pressure"):
                assert "CONSTRUCTED" in d["price_pressure"]["kind"] and "price" not in json.dumps(d.get("risk") or {})


def test_sealed_values_match_the_ledger_entries(rec):
    L = Ledger(BD / "data" / "ledger" / "T1_A.jsonl")
    by_seq = {e["seq"]: e for e in L.entries}
    checked = 0
    for q in rec["quarters"]:
        for c, d in q["provinces"].items():
            items = list(d.get("sealed", []))
            if d.get("experimental_estimate"):
                x = d["experimental_estimate"]
                items.append({"p": x["p_above_threshold"], "ledger": x["ledger"]})
            for s in items:
                if "ledger" in s:
                    e = by_seq[s["ledger"]["seq"]]
                    assert e["entry_hash"] == s["ledger"]["entry_hash"]
                    assert abs(e["payload"]["probabilities"][c] - s["p"]) < 5e-5
                    checked += 1
    assert checked >= 15                     # 2026-Q4: PCF21, B1, B1p x 5 (+ 2027-Q1 experimental estimates)


def test_operational_quarter_lists_the_pipeline_dependencies_and_never_a_forecast(rec):
    pipe = json.loads((BD / "data" / "quarterly_runs" / "2027-Q1" / "forecast_record.json").read_text(encoding="utf-8"))
    op = [q for q in rec["quarters"] if q["quarter"] == "2027-Q1"][0]
    assert op["state"] == "MISSING_INPUTS" and pipe["status"] == "INSUFFICIENT_DATA" and pipe["forecast"] is None
    assert op["dependencies"] == pipe["dependencies"] and op["pipeline_record_sha256"] == pipe["content_sha256"]
    blocking = {d["id"] for d in op["dependencies"] if d["blocking"]}
    assert blocking == {"sws_rounds", "label_history", "provincial_D_quarterly", "information_cutoff"}
    for d in op["provinces"].values():
        assert d["risk"] is None and "not a low-risk state" in d["risk_state"]
        x = d["experimental_estimate"]
        assert x["information_cutoff"].startswith("2026-09-30") and x["lead_quarters"] == 2
        assert "NOT the operational forecast" in x["what"]


def test_pdf_is_rendered_from_this_record_and_shows_the_same_numbers(rec):
    t = _pdf_text(PDF)
    assert rec["content_sha256"] in t and "No forecast is validated" in t
    assert re.search(rb"/Subject \(" + rec["content_sha256"].encode() + rb"\)", PDF.read_bytes())
    for q in rec["quarters"]:
        for d in q["provinces"].values():
            r = d.get("risk") if q["state"] == "BACKTEST" else d.get("experimental_estimate")
            if r:
                assert f"{100 * r['p_above_threshold']:.0f}%" in t
    assert "T1" in t and "T2" in t and "context only" in t and "BLOCKING" in t
    assert "face validity only" in t


def _client(monkeypatch, rec_path, pdf_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1 import quarterly as Q
    monkeypatch.setattr(Q, "E27_RECORD", rec_path)
    monkeypatch.setattr(Q, "E27_PDF", pdf_path)
    app = FastAPI()
    app.include_router(Q.router, prefix="/api/v1")
    return TestClient(app)


def test_api_serves_the_record_and_its_pdf_and_refuses_mismatches(monkeypatch, tmp_path, rec):
    c = _client(monkeypatch, REC, PDF)
    r = c.get("/api/v1/quarterly/timeline")
    assert r.status_code == 200 and r.json() == rec
    p = c.get("/api/v1/quarterly/timeline.pdf")
    assert p.status_code == 200 and p.headers["x-record-sha256"] == rec["content_sha256"] and p.content == PDF.read_bytes()
    # a record edited after rendering: integrity failure, never served as data
    bad = tmp_path / "r.json"
    x = dict(rec)
    x["quarters"] = x["quarters"][:-1]
    bad.write_text(json.dumps(x))
    assert _client(monkeypatch, bad, PDF).get("/api/v1/quarterly/timeline").status_code == 500
    # a stale PDF (rendered from another record) beside the current record: refused
    stale = tmp_path / "old.pdf"
    shutil.copy(PDF, stale)
    stale.write_bytes(stale.read_bytes().replace(rec["content_sha256"].encode(), b"0" * 64))
    assert _client(monkeypatch, REC, stale).get("/api/v1/quarterly/timeline.pdf").status_code == 409
