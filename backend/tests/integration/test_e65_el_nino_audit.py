"""
tests/integration/test_e65_el_nino_audit.py
-------------------------------------------
E65 (aipheed-backend-aligned/experiments/E65_El_Nino_Risk_Drop_Audit): the 2026-Q4 / 2027-Q1 risk drop under the
2026-27 El Nino.

Dashboard text (backend fields only; no number, model or UI element changes)
  * the E56/E58 forecast summaries state the PAGASA El Nino status known BEFORE the issue date, that it is not a model
    input, and that a LOW score is not evidence of no El Nino risk; later PAGASA items are labelled as published after
    the issue date;
  * the Climate Stress evidence note says the same; the served probabilities are unchanged;
  * D-E65-1: the indicator horizon of a back-test / earlier forecast names that estimate's own issue date;
  * the production default (E38) gets none of this text.
Evidence
  * the stated ENSO facts equal E65's recomputed counterfactuals and split counts;
  * arm A reproduces the sealed E57 forecasts; no climate arm improves on A by the pre-registered rule;
  * the sealed E57/E58 files are unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import enso_context as ENSO

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "aipheed-backend-aligned" / "experiments"
E65 = EXP / "E65_El_Nino_Risk_Drop_Audit"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
needs_e65 = pytest.mark.skipif(not (E65 / "out" / "r3_evaluation.json").exists(), reason="E65 outputs not present")


@pytest.fixture
def e58(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e58")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")


@pytest.fixture
def e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_pagasa_cutoff_is_exclusive_of_the_issue_date():
    assert ENSO.available_at("2026-10-01")[-1][0] == "2026-09-23"
    assert all(d < "2026-10-01" for d, _ in ENSO.available_at("2026-10-01"))
    assert ENSO.published_after("2026-10-01")[0][0] == "2026-10-07"
    assert ENSO.available_at("2026-07-01")[-1][0] == "2026-06-09"
    dates = [d for d, _ in ENSO.PAGASA_ENSO]
    assert dates == sorted(dates)


@needs_e65
def test_stated_enso_facts_equal_the_e65_recomputation():
    cf = pd.read_csv(E65 / "tables" / "r2_enso_counterfactuals.csv")
    piv = cf.pivot_table(index=["target", "province"], columns="scenario", values="P")
    h = cf.groupby(["target", "scenario"])["P_hunger"].first()
    for q, use in ENSO.E65_ENSO_USE.items():
        lo, hi = use["hunger_part"]
        assert abs(h[(q, "ENSO neutral (0, 0)")] - lo) < 1e-4 and abs(h[(q, "as observed")] - hi) < 1e-4
    q1 = piv.loc["2027-Q1"]
    assert (q1["as observed"] - q1["ENSO neutral (0, 0)"]).abs().max() <= 0.0105      # "at most about 1 point"
    q4 = piv.loc["2026-Q4"]
    assert (q4["El Nino both lags (+1, +1)"] - q4["as observed"]).abs().max() < 0.001  # "less than 0.1 point"
    split = json.loads((E65 / "out" / "r1_trace.json").read_text())["split_use"]
    for q in ENSO.E65_ENSO_USE:
        used = split[q]["price_splits"]
        assert not {"enso", "enso_l2", "enso_x_mom"} & set(used), q
        assert ENSO.E65_ENSO_USE[q]["price_part_enso_splits"] == 0


@needs_e65
def test_e65_evaluation_reproduces_a_and_no_arm_passes_the_rule():
    r = json.loads((E65 / "out" / "r3_evaluation.json").read_text())
    assert r["arm_A_reproduction_max_abs_diff"] <= 1e-6
    assert not any(x["improves_by_rule"] for x in r["paired_vs_A"])
    for name in ("E57_E56_Rolling_Origin_Test", "E58_Rising_Stress_Early_Warning"):
        p = EXP / name / "sealed" / "predictions.csv"
        want = (p.parent / "predictions.csv.sha256").read_text().split()[0]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == want


def test_forecast_summaries_carry_the_el_nino_limitation(e58):
    rec = LEAD2.record()
    for code, v in rec["provinces"].items():
        ex = _get("/api/v1/explainability", scope="province", id=SLUG[code], quarter="2027-Q1")
        s = ex["summary"]["sentence"]
        assert "PAGASA's latest ENSO statement (2026-09-23)" in s
        assert "This is not a model input." in s
        assert "A LOW score is therefore not evidence that the El Nino poses no food risk." in s
        assert "Published after the issue date: PAGASA 2026-10-07" in s
        assert abs(ex["summary"]["probability"] - v["forecast"]["probability"]) < 1e-4        # number unchanged
        clim = next(t for t in ex["triggers"] if t["key"] == "climate")
        assert "not a model input" in clim["evidenceNote"] and "PAGASA at the issue date (2026-10-01)" in clim["evidenceNote"]
        assert "2026-10-07" not in clim["evidenceNote"]                       # the card states issue-date knowledge only
        ex4 = _get("/api/v1/explainability", scope="province", id=SLUG[code], quarter="2026-Q4")
        assert "PAGASA's latest ENSO statement (2026-06-09)" in ex4["summary"]["sentence"]
    back = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2026-Q3")
    assert "PAGASA" not in back["summary"]["sentence"]                        # not verified for back-tests: no claim


def test_indicator_horizon_names_each_estimates_own_issue_date(e58):
    h3 = _get("/api/v1/provinces", quarter="2026-Q3")["indicator"]["horizon"]
    h4 = _get("/api/v1/provinces", quarter="2026-Q4")["indicator"]["horizon"]
    h1 = _get("/api/v1/provinces", quarter="2027-Q1")["indicator"]["horizon"]
    assert "back-test" in h3 and "2026-04-01" in h3
    assert "earlier forecast" in h4 and "2026-07-01" in h4
    assert h1 == LEAD2.record()["indicator"]["horizon"]


def test_production_default_gets_no_enso_text(e38):
    ex = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2027-Q1")
    assert ex.get("summary") is None
    clim = next(t for t in ex["triggers"] if t["key"] == "climate")
    assert clim["evidenceNote"] is None and clim["status"] == "no_model_input"
    assert ENSO.forecast_sentence("2027-Q1", "e38") is None and ENSO.climate_evidence("2027-Q1", "e64") is None
