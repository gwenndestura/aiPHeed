"""
tests/integration/test_foodinsecurity_config_metadata.py
--------------------------------------------------------
AIPHEED_MAP_MODEL=foodinsecurity: /api/v1/config describes the model actually served. The indicator's horizon and
caveat, servingModel and modelPerformance are derived from the served evaluation.json (no hardcoded metric): the C-b
export reports Maximum Reliable Lead Time 2, the C-E2 demo export (AIPHEED_FI_DATA_DIR) reports 3 and none of C-b's
figures; a missing or invalid evaluation gives an explicit "unavailable" statement. Forecast rows are unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import foodinsecurity_system as FI
from app.services import dashboard as svc

client = TestClient(app)
CB_DIR = FI.DATA
CE2_DIR = Path(__file__).resolve().parents[2] / "data" / "foodinsecurity_engine_ce2"


@pytest.fixture
def fi(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "foodinsecurity")
    return monkeypatch


def _ev(d: Path) -> dict:
    return json.loads((d / "evaluation.json").read_text(encoding="utf-8"))


def test_cb_export_reports_its_own_reliable_lead(fi):
    fi.setattr(FI, "DATA", CB_DIR)
    ev = _ev(CB_DIR)
    ind = FI.INDICATOR
    assert ind["evaluationAvailable"] is True
    assert f"Maximum Reliable Lead Time of {ev['max_reliable_lead']} quarters" in ind["horizon"]
    assert "Lead 3 fails the 75% rule (0.726)" in ind["horizon"]
    assert "Lead 1 = that quarter and Lead 2 = the next quarter" in ind["horizon"]
    assert svc.serving_model()["model"] == ev["model"] == "NEWS_V2-CB"
    assert svc.model_performance()["maxReliableLead"] == 2


@pytest.mark.skipif(not (CE2_DIR / "evaluation.json").exists(), reason="C-E2 demo export not present")
def test_ce2_demo_reports_lead_3_and_no_cb_figures(fi):
    fi.setattr(FI, "DATA", CE2_DIR)
    ev = _ev(CE2_DIR)
    assert ev["model"] == "ALLBASE-CE2" and ev["max_reliable_lead"] == 3
    ind = FI.INDICATOR
    assert "Maximum Reliable Lead Time of 3 quarters" in ind["horizon"]
    assert "Lead 4 fails the 75% rule (0.645)" in ind["horizon"]
    assert "served: Lead 2 = the next quarter" in ind["horizon"]
    for cb_text in ("Time of 2 quarters", "0.57", "NEWS_V2-CB", "one LightGBM"):
        assert cb_text not in ind["horizon"] + ind["caveat"] + ind["definition"], cb_text
    assert "mean of 8 LightGBM settings" in ind["definition"]
    assert "PSA Labor Force Survey" in ind["source"]
    sm, mp = svc.serving_model(), svc.model_performance()
    assert sm["model"] == mp["model"] == "ALLBASE-CE2"
    assert sm["planSha256"] == mp["planSha256"] == ev["plan_sha256"]
    assert sm["maxReliableLead"] == mp["maxReliableLead"] == 3 and sm["servedLeads"] == [2]
    assert sm["targetQuarter"] == "2027-Q1" and sm["issued"] == "2026-10-01" and sm["lead"] == 2
    assert mp["leads"]["2"]["accuracy"] == ev["leads"]["2"]["metrics"]["accuracy"]
    assert "FIRI" not in json.dumps(sm) + json.dumps(mp)
    h = FI.horizon()
    assert h["reliable_max_lead"] == 3 and h["why_not_longer"].startswith("Lead 4 is the first lead below 75%")


@pytest.mark.skipif(not (CE2_DIR / "evaluation.json").exists(), reason="C-E2 demo export not present")
def test_config_endpoint_serves_the_derived_metadata(fi):
    fi.setattr(FI, "DATA", CE2_DIR)
    r = client.get("/api/v1/config")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert "Maximum Reliable Lead Time of 3 quarters" in d["indicator"]["horizon"]
    assert d["servingModel"]["model"] == "ALLBASE-CE2"
    assert d["modelPerformance"]["maxReliableLead"] == 3


def test_missing_or_invalid_evaluation_is_explicit(fi, tmp_path):
    fi.setattr(FI, "DATA", tmp_path)                         # no evaluation.json at all
    ind = FI.indicator()
    assert ind["evaluationAvailable"] is False and "unavailable" in ind["horizon"]
    (tmp_path / "evaluation.json").write_text("{not json", encoding="utf-8")
    ind = FI.indicator()
    assert ind["evaluationAvailable"] is False and "unavailable" in ind["caveat"]
    (tmp_path / "evaluation.json").write_text(json.dumps({"model": "X"}), encoding="utf-8")   # no reliability fields
    assert FI.indicator()["evaluationAvailable"] is False


def test_forecast_rows_unchanged_by_the_metadata_fix(fi):
    fi.setattr(FI, "DATA", CB_DIR)
    before = {k: r["probability"] for k, r in FI.rows().items()}
    FI.indicator(), svc.serving_model(), svc.model_performance()
    assert {k: r["probability"] for k, r in FI.rows().items()} == before
