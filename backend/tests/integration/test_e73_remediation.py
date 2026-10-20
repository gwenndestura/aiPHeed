"""E73: explanation-method labels (API, PDF), the dimension on every factor-card indicator, the LGU priority-robustness
note and the opt-in province band. Served numbers are unchanged."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import dimensions as D
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import lgu_robustness as LGUR
from app.ml.inference import thesis_system as T
from app.services import report_data as RD

client = TestClient(app)


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return monkeypatch


def test_config_names_the_explanation_method(thesis):
    m = client.get("/api/v1/config").json()["servingModel"]["explanationMethod"]
    assert m["isShap"] is False and "not SHAP" in m["detail"] and "not what causes" in m["detail"]


def test_default_service_keeps_shap(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert client.get("/api/v1/config").json()["servingModel"] is None       # frontend falls back to "SHAP"
    assert RD._m() == "SHAP" and RD._subtitle(RD.SHAP) == "SHAP Explainability of Driver Groups"


def test_pdf_names_index_contribution_in_thesis_mode(thesis):
    assert RD._m() == "Index-contribution" and "SHAP" not in RD._subtitle(RD.SHAP)


def test_factor_cards_carry_the_dimension(thesis):
    rec = LEAD2.record()
    code = next(iter(rec["provinces"]))
    assert "[access dimension]" in T.group_evidence(rec, rec["targetQuarter"], code, "market")
    assert "[stability dimension]" in T.group_evidence(rec, rec["targetQuarter"], code, "climate")
    assert "[availability dimension]" in T.group_evidence(rec, rec["targetQuarter"], code, "fish_kill")


def test_lgu_robustness_covers_all_142_and_is_shown(thesis):
    tab = LGUR.table()
    assert len(tab) == 142 and all(0 <= r["same"] <= r["of"] == 7 for r in tab.values())
    rows = client.get("/api/v1/provinces/batangas/municipalities", params={"quarter": "2027-Q1"}).json()["data"]
    assert len(rows) == 34 and all(r["disaggregationLabel"].startswith("Priority: ") and "alternative poverty/density weightings" in r["disaggregationLabel"] for r in rows)


def test_province_band_flag_is_opt_in(thesis):
    base = client.get("/api/v1/provinces/batangas/municipalities", params={"quarter": "2027-Q1"}).json()["data"]
    thesis.setenv("AIPHEED_LGU_BAND", "province")
    alt = client.get("/api/v1/provinces/batangas/municipalities", params={"quarter": "2027-Q1"}).json()["data"]
    assert [r["riskIndex"] for r in base] == [r["riskIndex"] for r in alt]               # values unchanged
    assert {r["riskLevel"] for r in alt} == {"high"}                                       # Batangas 2027-Q1 is HIGH
    assert any(r["riskLevel"] != "high" for r in base)                                     # default keeps the E45 band


def test_e73_sentences_match_their_evidence():
    import json
    from pathlib import Path
    o = json.loads((Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E73_Objective_Remediation"
                    / "out" / "octa_validation.json").read_text())
    s = next(x for x in T.performance_tables()["sentences"] if x.startswith("E73"))
    c = o["classification"]["FIRI"]
    assert f"agreed in {c['correct']} of {c['n']}" in s and "not supported by independent evidence" in s
    assert T.E73_SUMMARY in T.REQUIRED and "PAGASA typhoon counts" in T.news_validation_sentence()
