"""
tests/integration/test_api_ch1_risk.py
---------------------------------------
The served Chapter I risk forecast (app.ml.inference.ch1_system; LEAD2_OPTIMIZATION P0H4 on the FIRI_V2_DATA_AUDIT
inputs): province scores are the exported P0H4 probabilities (UNI-FINAL's one LightGBM across leads x the pooled-area
hunger term), the Lead-1 rows equal the evaluated predictions, the trigger statuses and notes describe the served model, the reliability verdict and the 75% statement follow from the evaluation, horizons beyond Lead 1 are
flagged, the LGU layer stays a priority ranking, and AIPHEED_MAP_MODEL=firi restores FIRI v2.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
LEAD2 = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_OPTIMIZATION" / "out"


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.delenv("AIPHEED_MAP_MODEL", raising=False)
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_province_scores_are_the_exported_ch1_probabilities(thesis):
    for q in ("2026-Q4", "2027-Q1", "2024-Q2"):
        d = _get("/api/v1/provinces", quarter=q)
        assert d["indicator"]["id"] == "chapter1_food_insecurity_risk"
        for r in d["data"]:
            code = {v["province"]: k for (k, qq), v in CH1.rows().items() if qq == q}[r["name"]]
            assert r["riskScore"] == pytest.approx(float(CH1.row(code, q)["probability"]), abs=0.01)  # shown to 2 dp
            assert r["riskLevel"] == ("high" if r["riskScore"] >= 0.5 else "low")


def test_served_lead1_rows_equal_the_evaluated_predictions():
    P = pd.read_csv(LEAD2 / "predictions_addendum3.csv", dtype={"province_code": str})
    P = P[P["lead"] == 1]
    assert len(P) == 70
    for p in P.itertuples():
        q = f"{p.q // 4}-Q{p.q % 4 + 1}"
        r = CH1.row(p.province_code, q)
        assert r is not None and float(r["probability"]) == pytest.approx(p.P0H4_p3, abs=1e-5)
        assert float(r["pi_price"]) == pytest.approx(p.P0_price, abs=1e-5)
        assert (r["observed"] == "HIGH") == bool(p.y)


def test_reliability_and_75_percent_follow_from_the_evaluation():
    ev = _get("/api/v1/final/risk/evaluation")
    assert ev["max_reliable_lead"] == 1
    l1 = ev["leads"]["1"]
    assert l1["reliable"] and l1["metrics"]["accuracy"] >= 0.75
    assert l1["metrics"]["accuracy"] > l1["baseline_accuracy"]["ALWAYS-LOW"]
    assert l1["metrics"]["balanced_accuracy"] >= 0.70
    assert not any(ev["leads"][k]["reliable"] for k in ("2", "3", "4"))


def test_forecasts_beyond_the_reliable_horizon_are_flagged(thesis):
    rows = _get("/api/v1/final/risk/rows", kind="forecast")["rows"]
    assert {r["quarter"] for r in rows} == {"2026-Q4", "2027-Q1", "2027-Q2", "2027-Q3"}
    for r in rows:
        assert r["reliable_horizon"] is (int(r["lead"]) <= 1)
    s = _get("/api/v1/explainability", scope="province", id="cavite", quarter="2027-Q1")["summary"]["sentence"]
    assert "experimental" in s and "Lead-2" in s


def test_summary_and_driver_bars_explain_the_served_model(thesis):
    d = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2026-Q4")
    assert d["summary"]["sentence"].startswith("FOOD-INSECURITY RISK for Quezon, 2026-Q4")
    assert "passed the reliability test" in d["summary"]["sentence"]
    market = next(t for t in d["triggers"] if t["key"] == "market")
    assert "chance that food prices" in market["plainEvidence"]
    assert sum(t["pct"] for t in d["triggers"]) == 100


def test_trigger_statuses_follow_the_served_models_own_inputs(thesis):
    """Contributor audit defect: statuses came from the FIRI record and said "no published value" for groups whose
    inputs the served model had (135 of 135 such statuses). They must now follow the exported availability flags."""
    for q in ("2024-Q3", "2025-Q2", "2026-Q4"):
        for code, slug in (("PH040100000", "cavite"), ("PH040300000", "quezon")):
            d = _get("/api/v1/explainability", scope="province", id=slug, quarter=q)
            r = CH1.row(code, q)
            for t in d["triggers"]:
                avail = str(r[f"avail_{t['key']}"]) == "1"
                assert (t["status"] == "insufficient_data") is (not avail)
                if avail:
                    assert t["status"] == ("contributes" if t["pct"] > 0 else "no_effect")


def test_trigger_note_says_the_bars_explain_only_the_price_part(thesis):
    for scope, slug in (("province", "quezon"), ("region", "calabarzon")):
        d = _get("/api/v1/explainability", scope=scope, id=slug, quarter="2024-Q3")
        notes = {t["evidenceNote"] for t in d["triggers"]}
        assert len(notes) == 1
        note = notes.pop()
        assert "food prices rise unusually fast" in note and "leave out the regional hunger condition" in note
        assert "not shares of hunger" in note and "FIRI" not in note


def test_lgus_remain_a_priority_ranking_without_hunger_figures(thesis):
    d = _get("/api/v1/final/lgus")
    assert d["count"] == 142
    from app.services import dashboard as D
    rows = D.municipality_summary("2026-Q4")
    assert len(rows) == 142
    assert all("Not a measured or official municipal food-insecurity rate" in r["riskLevelBasis"] for r in rows)


def test_firi_mode_restores_the_previous_score(thesis):
    thesis.setenv("AIPHEED_MAP_MODEL", "firi")
    d = _get("/api/v1/provinces", quarter="2027-Q1")
    assert d["indicator"]["id"] == "food_insecurity_risk_index"
