"""
tests/integration/test_api_final_system.py
-------------------------------------------
Contract tests for the final forecasting engine (/api/v1/final/*) and the honesty rules of the completed system:
regional hunger is shown with its dates and age, the LightGBM metrics are recomputable from its own predictions, the
75% verdict and the horizon verdict follow from the frozen criteria, every one of the 142 LGUs is served with a
priority label and never with a hunger figure, sealed forecasts are untouched, and news is cut off by date.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import final_engine as FE

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "aipheed-backend-aligned" / "experiments"


def _get(path: str, **params) -> dict:
    r = client.get(f"/api/v1/final/{path}", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_overview_shows_latest_sws_observation_with_dates_and_age():
    o = _get("overview")
    last = o["regionalHunger"]["latest"]
    assert last["published"] <= o["asOf"]
    assert last["fieldworkEnd"] < last["published"]
    assert last["ageDaysAtAsOf"] == (pd.Timestamp(o["asOf"]) - pd.Timestamp(last["fieldworkEnd"])).days
    assert "Balance Luzon" in o["regionalHunger"]["geography"] and "No province" in o["regionalHunger"]["geography"]
    assert "not a food-insecurity rate or probability" in o["localEvidence"]


def test_latest_observation_is_kept_apart_from_forecasts():
    o = _get("overview")["outlook"]
    last_q = _get("overview")["regionalHunger"]["latest"]["quarter"]
    assert all(r["targetQuarter"] > last_q for r in o["latestReadingOutlook"])
    assert all(r["issueDate"] == "2026-10-01" and r["newestSwsQuarterUsed"] < last_q for r in o["lightgbmForecast"])
    assert "not a calibrated probability" in o["elevatedScoreNote"]


def test_evaluation_verdicts_follow_from_the_criteria():
    e = _get("evaluation")
    leads = e["leads"]
    assert [l["lead"] for l in leads] == [0, 1, 2, 3, 4]
    assert e["accuracyTargetReached"] is (any(l["metrics"]["accuracy"] >= 0.75 and l["reliable"] for l in leads))
    assert e["accuracyTargetReached"] is False
    assert e["maxReliableLead"] is None and not any(l["reliable"] for l in leads)
    for l in leads:
        assert l["criteria"]["R2"] is (l["metrics"]["accuracy"] >= 0.75)


def test_metrics_recompute_from_the_prediction_rows():
    R = pd.read_csv(FE.DATA / "predictions_fil_oa.csv")
    e = _get("evaluation")
    for l in e["leads"]:
        D = R[R["lead"] == l["lead"]]
        acc = float(((D["FIL_p"] > 0.5).astype(int) == D["label"]).mean())
        mae = float((D["FIL_level"] - D["y"]).abs().mean())
        mae_p = float((D["h_last"] - D["y"]).abs().mean())
        assert acc == pytest.approx(l["metrics"]["accuracy"])
        # the CSV stores 6 significant digits
        assert mae == pytest.approx(l["maePts"], abs=1e-3) and mae_p == pytest.approx(l["persistenceMaePts"], abs=1e-3)


def test_predictions_use_only_information_published_before_issue():
    R = pd.read_csv(FE.DATA / "predictions_fil_oa.csv")
    assert (R["sws_newest_published"] < R["issue_date"]).all()
    assert (pd.to_datetime(R["gkg_latest_published"].dropna()) < pd.to_datetime(R.loc[R["gkg_latest_published"].notna(),
                                                                                        "issue_date"])).all()
    assert (R["true_horizon"] >= 1).all()                     # no target was already published at its issue date


def test_twelve_families_are_eligible_and_missingness_is_reported():
    f = _get("families")
    fams = {r["family"] for r in f["families"]}
    assert {"A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"} <= fams
    assert all(0.0 <= r["missing_share"] < 1.0 for r in f["families"])
    groups = f["driverGroups"]
    assert set(groups) >= {"Market and prices", "Climate and food production", "Employment and remittances", "News",
                           "Poverty and vulnerability"}


def test_contributions_are_the_models_own_shares_not_equal_splits():
    c = _get("contributions")["byLead"]
    for lead, shares in c.items():
        assert sum(shares.values()) == pytest.approx(1.0, abs=0.01)
        assert len(set(round(v, 3) for v in shares.values())) > 2      # not a forced equal split


def test_all_142_lgus_are_served_as_priority_scores_without_hunger_figures():
    d = _get("lgus")
    assert d["count"] == 142 and len({r["lguCode"] for r in d["rows"]}) == 142
    assert {r["province"] for r in d["rows"]} == {"cavite", "laguna", "batangas", "rizal", "quezon"}
    assert "Priority score" in d["label"] and "not a measured" in d["label"]
    for r in d["rows"]:
        assert r["localHungerEvidence"] == "insufficient local outcome evidence"
        assert not any("hunger" in k.lower() and k != "localHungerEvidence" for k in r)


def test_archive_separates_retrospective_and_prospective_rows():
    a = _get("archive")
    kinds = {r["kind"].split(" ")[0] for r in a["rows"]}
    assert kinds == {"retrospective", "prospective"}
    for r in a["rows"]:
        if r["kind"].startswith("prospective"):
            assert r["actual_level"] is None
        else:
            assert r["actual_level"] is not None
    assert _get("archive", kind="prospective", area="BL")["rows"]


def test_sealed_forecasts_are_untouched():
    for name in ("FINAL_FOOD_INSECURITY_LIGHTGBM", "FINAL_OBJECTIVE_ACHIEVEMENT", "E113_Final_Model",
                 "E112_Food_Insecurity_Forecasting", "E107_Twelve_Indicator_LightGBM"):
        for p in (EXP / name / "out").glob("sealed_prospective*.csv"):
            want = p.with_name(p.name + ".sha256").read_text().strip()
            assert hashlib.sha256(p.read_bytes()).hexdigest() == want, p


def test_news_is_cut_off_by_date_and_marked_as_context():
    n = _get("news", limit=1000, before="2026-07-01")
    assert n["rows"] and all(r["published"] < "2026-07-01" for r in n["rows"])
    assert n["status"].startswith("Context only")
    assert {r["kind"] for r in _get("news", limit=1000)["rows"]} <= {
        "reported event", "possible future risk (forward-looking wording)"}
    assert all(r["kind"].startswith("possible") for r in _get("news", kind="future", limit=50)["rows"])


def test_news_kind_rule():
    assert FE.news_kind("PH braces for severe El Nino seen to last until May") == FE.FUTURE
    assert FE.news_kind("Typhoon damage to crops reaches P1 billion") == FE.REPORTED
    assert "not evidence that hunger will rise" in FE.news_context_note("Rice prices up")


def test_food_cpi_is_labelled_economic_access_not_hunger():
    c = _get("cpi")
    assert "not a hunger measure" in c["definition"]
    assert {r["province"] for r in c["latest"]} == {"Cavite", "Laguna", "Batangas", "Rizal", "Quezon"}


def test_missing_engine_file_gives_503(monkeypatch, tmp_path):
    monkeypatch.setattr(FE, "DATA", tmp_path)
    FE.engine.cache_clear()
    try:
        r = client.get("/api/v1/final/overview")
        assert r.status_code == 503 and "export_engine.py" in r.json()["detail"]
    finally:
        FE.engine.cache_clear()


def test_every_listed_seal_verifies():
    seals = _get("archive")["seals"]
    assert len(seals) >= 12 and all(s["verified"] for s in seals)
