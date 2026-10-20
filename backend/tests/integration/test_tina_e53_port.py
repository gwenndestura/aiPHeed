"""
tests/integration/test_tina_e53_port.py
---------------------------------------
The E53 port onto Angel's system (branch tina-e53-port): E53-A1 + C2 calibration is served by default, the five
drivers are Tina's attribution (all five listed, each "contributes" or "no_effect" under E53), 2027-Q1 is the E53
record's own lead-2 row (E55) with its accuracy stated and no alert, and the news card lists the validated
evidence-quarter articles the estimate used, with the plain sentence. Every number is read from the record.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e31_engine as E31

client = TestClient(app)
REC = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    for v in ("AIPHEED_LEAD2_MODEL", "AIPHEED_MAX_LEAD", "AIPHEED_LEAD2_PREVIEW"):
        monkeypatch.delenv(v, raising=False)


def _row(q, lead):
    return next(r for r in REC["quarters"] if r["quarter"] == q and r.get("lead", 1) == lead)


def test_e53_is_served_by_default_and_named_with_its_accuracy():
    assert E31.DEFAULT_RECORD == "e53" and Path(E31.RECORD_PATH) == Path("data/e53/e53_record.json")
    se = client.get("/api/v1/quarterly/e31/summary").json()["served_engine"]
    assert se["name"].startswith("aiPHeed-E53-A1") and "PREVIEW" not in se["name"]
    assert "0.785 (51/65)" in se["why_served"] and "not demonstrated (95% date-bootstrap interval 0.646 to 0.908)" \
        in se["why_served"]
    m = client.get("/api/v1/config").json()["modelPerformance"]
    assert (m["accuracy"], m["accuracyCi95"], m["rocAuc"], m["f1"]) == (0.7846, [0.646154, 0.907692], 0.8797, 0.8511)


@pytest.mark.parametrize("q,want", [("2026-Q2", 0.7539), ("2026-Q3", 0.896), ("2026-Q4", 0.7894)])
def test_region_is_the_rounded_mean_of_the_records_p_high(q, want):
    row = _row(q, 1)
    assert round(sum(v["p_high"] for v in row["provinces"].values()) / 5, 4) == want
    assert client.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={q}").json()["riskScore"] == want
    prov = {p["name"]: p["riskScore"] for p in client.get(f"/api/v1/provinces?quarter={q}").json()["data"]}
    assert prov == {v["province"]: v["p_high"] for v in row["provinces"].values()}


@pytest.mark.parametrize("q", ["2026-Q3", "2026-Q4", "2027-Q1"])
def test_five_drivers_have_a_model_input_status_under_e53(q):
    for scope, ident in (("region", "calabarzon"), ("province", "quezon"), ("province", "batangas")):
        tr = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter={q}").json()["triggers"]
        assert {t["key"] for t in tr} == FIVE and sum(t["pct"] for t in tr) == 100
        assert all(t["status"] == ("contributes" if t["pct"] > 0 else "no_effect") for t in tr), (q, ident)


def test_2027_q1_is_the_records_own_lead2_row_with_its_accuracy_and_no_alert():
    from app.quarterly import alerts_e31 as A

    row = _row("2027-Q1", 2)
    want = round(sum(v["p_high"] for v in row["provinces"].values()) / 5, 4)
    f = client.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2027-Q1").json()
    assert want == 0.7978 and f["riskScore"] == want and f["isPreview"] is True
    assert "0.673" in f["previewNote"] and "below persistence (0.800)" in f["previewNote"]
    q = client.get("/api/v1/quarters").json()
    assert q["defaultQuarter"] == "2027-Q1" and q["current"] == "2026-Q4"
    assert {c["quarter"] for c in A.candidates(E31.record(), "all")} <= {"2026-Q4"}      # no lead-2 alert


@pytest.mark.parametrize("q,n,line", [
    ("2026-Q3", 15, "These are the 15 validated Q2 2026 news articles this estimate used (published before 1 Jul 2026)."),
    ("2026-Q4", 9, "These are the 9 validated Q3 2026 news articles this estimate used (published before 1 Oct 2026)."),
    ("2027-Q1", 9, "These are the 9 validated Q3 2026 news articles this estimate used (published before 1 Oct 2026)."),
])
def test_news_card_lists_the_evidence_quarter_articles_with_its_sentence(q, n, line):
    card = client.get(f"/api/v1/news?scope=region&id=calabarzon&quarter={q}&pageSize=100").json()
    assert card["articleCount"] == card["total"] == len(card["data"]) == n and card["feedNote"] == line
    ex = client.get(f"/api/v1/explainability?scope=region&id=calabarzon&quarter={q}").json()
    assert ex["articleCount"] == n
    assert all(a["relevanceStatus"] == "validated" for a in card["data"]) and card["triggerMatchCount"] == 0
    zero = client.get(f"/api/v1/news?scope=province&id=quezon&quarter=2026-Q4").json()
    assert zero["articleCount"] == 0
    assert zero["feedNote"] == "This estimate used no validated Q3 2026 news articles (published before 1 Oct 2026)."
