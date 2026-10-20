"""
tests/integration/test_e55_lead2_preview.py
-------------------------------------------
The E53 record's lead-2 (next_quarter, 2027-Q1) row comes from E55 (E53-A1 at lead 2, shrinkage-calibrated), served
only with AIPHEED_MAX_LEAD=2 as an experimental preview that states its weak accuracy. The E49 and E36 records keep
their E38 row; lead-1 behaviour is unchanged when AIPHEED_MAX_LEAD is unset.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
REC = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
NQ = next(q for q in REC["quarters"] if q.get("role") == "next_quarter")
BUNDLE = json.loads(Path("data/e53/model/E55_SERVING_BUNDLE.json").read_text(encoding="utf-8"))
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
HORIZON = "Next quarter (two quarters ahead) — experimental preview; development accuracy 0.673, below persistence."
NEWS_NOTE = ("This quarter has not started; no news yet. The 2027-Q1 forecast was built on 2026-10-01 from 2026-Q3 news.")


@pytest.fixture
def lead2_e53(serve_e53, lead2, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    yield


def test_e53_lead2_row_is_e55_not_e38():
    assert NQ["quarter"] == "2027-Q1" and NQ["lead"] == 2 and NQ["model_id"] == "aiPHeed-E55"
    assert NQ["model_name"] == "aiPHeed-E55 (E53-A1 at lead 2, shrinkage-calibrated) - EXPERIMENTAL PREVIEW"
    for code, v in NQ["provinces"].items():                       # C2-calibrated E55 probabilities, not raw
        assert v["p_high"] == pytest.approx(BUNDLE["forecast"]["provinces"][code]["p_high"], abs=1e-4)
        assert {d["key"] for d in v["drivers"]} >= {"cond_market", "cond_climate", "cond_fish", "cond_employment",
                                                    "cond_ofw"}
    nqm = REC["next_quarter_model"]
    assert nqm["name"].startswith("aiPHeed-E55") and nqm["file"] == "data/e53/model/E55-LGBM-NQ_O2026-10-01_lead2.txt"
    ev = REC["validation"]["next_quarter_evaluation"]
    assert ev["verdict"] == ("Next-quarter accuracy 0.673 (37/55), balanced accuracy 0.670: below the 75% target and "
                             "below persistence (0.800). It did not meet its adoption rule (E55). Shown as an "
                             "experimental preview only.")
    assert {r["key"] for r in ev["rows"]} == {"E55", "E38-LGBM", "B1_PERSISTENCE", "ALWAYS_HIGH"}
    assert "0.673 (37/55)" in NQ["status"] and any("0.673 (37/55)" in t for t in REC["limitations"])
    assert REC["lgu_ranking"]["probability_source"]["source"].startswith("next-quarter FORECAST 2027-Q1 (aiPHeed-E55")


@pytest.mark.parametrize("name", ["e49", "e36"])
def test_e49_e36_keep_their_e38_row(name):
    rec = json.loads(Path(f"data/{name}/{name}_record.json").read_text(encoding="utf-8"))
    nq = next(q for q in rec["quarters"] if q.get("role") == "next_quarter")
    assert nq["model_id"] == "aiPHeed-E38-LGBM-NQ" and "39/55 = 0.709" in nq["status"] and "model_name" not in nq


def test_lead2_confidence_and_horizon(lead2_e53):
    for code, slug in SLUG.items():
        b = client.get(f"/api/v1/forecast?scope=province&id={slug}&quarter=2027-Q1").json()
        assert b["riskScore"] == pytest.approx(NQ["provinces"][code]["p_high"], abs=1e-4)
        assert b["horizonLabel"] == HORIZON
        cs = b["confidenceStatement"]
        assert "aiPHeed-E55" in cs and "E53-A1 (LightGBM" not in cs
        assert "development accuracy 0.673, below 75% and below persistence (0.800); experimental preview" in cs
    r = client.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2027-Q1").json()
    assert r["horizonLabel"] == HORIZON and "persistence" in r["confidenceStatement"]


def test_lead1_rows_still_name_the_served_model(lead2_e53):
    b = client.get("/api/v1/forecast?scope=province&id=quezon&quarter=2026-Q4").json()
    assert "aiPHeed-E53-A1" in b["confidenceStatement"] and "0.673" not in b["confidenceStatement"]
    r = client.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2026-Q4").json()
    assert r["horizonLabel"] and r["confidenceStatement"]                      # region states its horizon too


def test_measured_condition_complete_for_2027_q1(lead2_e53):
    ex = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()
    conds = {t["key"]: t["measuredCondition"] for t in ex["triggers"]}
    assert set(conds) == {"market", "climate", "fish_kill", "employment", "ofw_remittance"}   # all five, climate (0%) included
    for k, c in conds.items():
        assert c is not None and all(c[f] is not None for f in ("score", "dataQuarter", "summary", "level", "source")), k
        assert c["dataQuarter"] == "2026-Q2", k


def test_quarters_current_stays_calendar_quarter(lead2_e53):
    q = client.get("/api/v1/quarters").json()
    assert q["current"] == "2026-Q4"
    states = {x["id"]: x["state"] for x in q["quarters"]}
    assert states["2027-Q1"] == "forecast"


def test_news_for_2027_q1(lead2_e53):
    for view in ("published", "used"):
        n = client.get(f"/api/v1/news?scope=province&id=quezon&quarter=2027-Q1&view={view}").json()
        assert n["forecastOrigin"] == "2026-10-01"
    n = client.get("/api/v1/news?scope=region&id=calabarzon&quarter=2027-Q1&view=published").json()
    assert n["total"] == 0 and n["data"] == [] and n["windowEnd"] is None
    assert n["evidenceNote"] == NEWS_NOTE and "None" not in n["evidenceNote"]
    q4 = client.get("/api/v1/news?scope=region&id=calabarzon&quarter=2026-Q4&view=published").json()
    assert q4["forecastOrigin"] == "2026-10-01" and q4["total"] == 3 and q4["windowEnd"] == "2026-10-14"


def test_lead1_unchanged_without_max_lead(monkeypatch):
    monkeypatch.delenv("AIPHEED_MAX_LEAD", raising=False)
    monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "0")                 # lead 1 only (the preview is on by default)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    q = client.get("/api/v1/quarters").json()
    assert q["current"] == "2026-Q4" and "2027-Q1" not in {x["id"] for x in q["quarters"] if x["state"] == "forecast"}
    r = client.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2026-Q4").json()
    assert r["riskScore"] == 0.7894                                          # default E53 (record p_high mean)
    assert client.get("/api/v1/provinces?quarter=2027-Q1").status_code == 404
