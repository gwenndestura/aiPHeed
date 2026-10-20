"""
tests/integration/test_self_description.py
------------------------------------------
The system describes itself truthfully: indicator horizon and source, the model definition (record-aware), the LGU
disaggregation label, the explanation narrative, the record's evaluation basis and PDF appendix title, and each
driver's measured condition (E53 only; null under E49). Shares and directions are not affected.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HORIZON = ("One quarter ahead (lead 1), issued at the start of the quarter with information published before it; "
           "not validated: no baseline is beaten significantly.")
SOURCE = ("SWS Balance Luzon hunger rounds, PSA provincial food and rice CPI, and relevance-screened Google News titles "
          "(CALABARZON, 2021 to 14 October 2026).")
SOURCE_E53 = SOURCE[:-1] + ("; measured driver conditions from NASA POWER rainfall (reanalysis), NOAA IBTrACS storms, "
                            "PSA fisheries production (proxy), PSA LFS unemployment (national) and BSP remittances "
                            "(national; 2026 provisional).")
NARRATIVE = ("Shares are each driver group's contribution to the estimate (news inputs split by the topic of the news "
             "titles); they are not causes and not measured conditions.")
CODES = re.compile(r"\bE\d{2}\b|E25-E28|E35-D4")
DRIVERS = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture(autouse=True)
def _now(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


def _indicator():
    return client.get("/api/v1/forecast?scope=region&id=calabarzon&quarter=2026-Q4").json()["indicator"]


def test_indicator_texts_e49(serve_e49):
    ind = _indicator()
    assert ind["horizon"] == HORIZON and ind["source"] == SOURCE
    d = client.get("/api/v1/config").json()["horizons"]["forecast"]["definition"]
    assert "five trigger proportions, shrinkage-calibrated" in d                      # E49 text kept


def test_indicator_texts_default_e53():
    ind = _indicator()
    assert ind["horizon"] == HORIZON and ind["source"] == SOURCE_E53
    d = client.get("/api/v1/config").json()["horizons"]["forecast"]["definition"]
    assert d.startswith("LightGBM (trigger proportions and measured driver conditions; fixed grid with nested "
                        "walk-forward selection; shrinkage-calibrated)")
    assert d.endswith("Not validated: no baseline is beaten significantly.") and not CODES.search(d)


def test_lgu_label_has_no_experiment_codes():
    rows = client.get("/api/v1/provinces/quezon/municipalities?quarter=2026-Q4").json()["data"]
    label = rows[0]["disaggregationLabel"]
    assert "experimental (not validated against baselines), so the ranking is EXPERIMENTAL" in label
    assert not CODES.search(label)


def test_narrative_text():
    ex = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q4").json()
    assert NARRATIVE in ex["narrative"] and "SHAP contributions" not in ex["narrative"]


@pytest.mark.parametrize("scope,ident", [("province", "quezon"), ("province", "batangas"), ("region", "calabarzon")])
def test_measured_condition_e53(serve_e53, scope, ident):
    ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter=2026-Q4").json()
    conds = {t["key"]: t["measuredCondition"] for t in ex["triggers"]}
    assert set(conds) == DRIVERS
    for k, c in conds.items():
        assert c is not None, k
        assert 0 <= c["score"] <= 100 and c["dataQuarter"] == "2026-Q2" and c["summary"] and c["source"], (k, c)
        assert c["level"] == ("national" if k in ("employment", "ofw_remittance") else "province"), (k, c)


def test_measured_condition_matches_the_records_condition_input(serve_e53):
    rec = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
    q4 = next(q for q in rec["quarters"] if q["quarter"] == "2026-Q4")
    vals = {d["key"]: d["value"] for d in q4["provinces"]["PH040300000"]["drivers"]}
    ex = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q4").json()
    conds = {t["key"]: t["measuredCondition"] for t in ex["triggers"]}
    assert conds["climate"]["score"] == pytest.approx(vals["cond_climate"], abs=0.05)
    assert "below the 1991-2020 normal" in conds["climate"]["summary"]
    assert conds["employment"]["score"] == pytest.approx(vals["cond_employment"], abs=0.05)


def test_measured_condition_null_under_e49(serve_e49):
    ex = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q4").json()
    assert all(t["measuredCondition"] is None for t in ex["triggers"])


def test_e53_record_basis_and_builder_appendix_title():
    rec = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
    assert rec["validation"]["model_evaluation"]["basis"].startswith("Nested walk-forward, lead 1, 13 development quarters; run ")
    builder = Path("scripts/build_record_e36.py").read_text(encoding="utf-8")
    assert '"Appendix: lead-2 experiment (not served)"' in builder
    assert "Model evaluation: next quarter (the dashboard target)" not in builder
