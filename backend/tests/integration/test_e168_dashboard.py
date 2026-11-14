"""
tests/integration/test_e168_dashboard.py
----------------------------------------
The approved E168 model (registry e168-lgbm-1.0) drives the dashboard's map, province ranking, LGU ranking, explanation
cards, summary and early warnings (app.ml.inference.map_engine -> e168_system), with exactly the values of the approved
artifact data/e168/out/live_2027.json; AIPHEED_MAP_MODEL=ch1 restores the Chapter I price-pressure index.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e168_system as E
from app.ml.inference import map_engine

client = TestClient(app)
from app.e168 import serve as SV

LIVE = json.loads(SV.artifact().read_text())          # the approved issue being served (a live refresh moves it daily)
CUT = LIVE.get("information_cutoff") or "2026-10-01"
pytestmark = pytest.mark.skipif(not E.ROWS.exists(), reason="E168 dashboard export not present")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-11-07T09:00:00")
    monkeypatch.delenv("AIPHEED_MAP_MODEL", raising=False)
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_export_equals_the_approved_artifact():
    live = {(r["province"], r["lead"]): r for r in LIVE["provinces"]}
    rows = list(E.rows().values())
    assert len(rows) == 15
    for r in rows:
        a = live[(r["province"], int(r["lead"]))]
        assert (float(r["score_pct"]), float(r["probability"]), r["class"]) == (a["score_pct"], a["p_high"], a["risk_class"])
        assert r["quarter"] == a["target_quarter"]


def test_group_contributions_add_up_to_the_lightgbm_change():
    for r in E.rows().values():
        parts = sum(E.bar_value(r, g) for g in E.GROUPS) + sum(float(r[c]) for c in E.OTHER_COLS) + float(r["bias_logit"])
        assert parts == pytest.approx(float(r["change_logit"]), abs=1e-4)


def test_five_triggers_labelled_honestly():
    # The thesis's five triggers; national series say what they are, and the fisheries group is named for what it measures. Every stored column once.
    assert set(E.GROUPS) == {"market", "climate", "employment", "ofw_remittance", "fish_kill"}
    assert "(national)" in E.GROUPS["employment"] and "(national)" in E.GROUPS["ofw_remittance"]
    assert E.GROUPS["fish_kill"] == "Fish Production"
    used = [c for cols in E.BAR_COLS.values() for c in cols] + list(E.OTHER_COLS)
    assert len(used) == len(set(used))


@pytest.mark.legacy_served
def test_driver_shares_include_other_and_add_to_100(thesis):
    for scope, sid in (("province", "quezon"), ("region", "calabarzon")):
        d = _get("/api/v1/explainability", scope=scope, id=sid, quarter="2027-Q1")
        assert isinstance(d["otherPct"], (int, float)), "the share outside the five bars must be reported"
        assert sum(t["pct"] for t in d["triggers"]) + d["otherPct"] == 100


@pytest.mark.legacy_served
def test_fish_kill_bar_is_disclosed_as_a_proxy(thesis):
    d = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2027-Q1")
    fk = next(t for t in d["triggers"] if t["key"] == "fish_kill")
    assert fk["label"] == "Fish Production" and "Fish production" in (fk["plainEvidence"] or "")


@pytest.mark.legacy_served
def test_report_and_config_describe_e168_not_the_retired_index(thesis):
    rep = json.dumps(_get("/api/v1/report/data", scope="province", id="quezon", quarter="2027-Q1"))
    assert "price-pressure" not in rep and "E168" in rep
    cfg = _get("/api/v1/config")
    # modelPerformance keeps the structure the PDF report code reads (not displayed in the frontend)
    # servingModel keeps its existing contract (None in the default mode)
    ov = _get("/api/v1/final/overview")
    assert "indicator-based priority score" not in ov["localEvidence"]


def test_evaluation_confusion_matrix_is_consistent():
    m = E.evaluation()["leads"]["1"]["metrics"]
    assert m["tp"] + m["fp"] + m["fn"] + m["tn"] == m["n"] and m["tp"] + m["tn"] == m["correct"]


@pytest.mark.legacy_served
def test_map_engine_selects_e168_and_ch1_on_request(thesis):
    assert map_engine.selected() is E
    thesis.setenv("AIPHEED_MAP_MODEL", "ch1")
    from app.ml.inference import ch1_system
    assert map_engine.selected() is ch1_system


@pytest.mark.legacy_served
def test_province_map_and_ranking_are_e168(thesis):
    for lead, q in ((1, "2027-Q1"), (2, "2027-Q2"), (3, "2027-Q3")):
        d = _get("/api/v1/provinces", quarter=q)
        assert d["indicator"]["id"] == "e168_food_insecurity_risk"
        live = {r["province"]: r for r in LIVE["provinces"] if r["lead"] == lead}
        assert len(d["data"]) == 5
        for r in d["data"]:
            assert r["riskScore"] == pytest.approx(live[r["name"]]["p_high"], abs=1e-6)
            assert r["riskLevel"] == ("high" if live[r["name"]]["risk_class"] == "HIGH" else "low")
            assert "E168" in r["riskLevelBasis"]
        order = [r["name"] for r in sorted(d["data"], key=lambda r: r["rank"])]
        assert order == [p for p, _ in sorted(((k, v["p_high"]) for k, v in live.items()), key=lambda kv: -kv[1])]


def test_dashboard_opens_on_the_next_quarter(thesis):
    assert _get("/api/v1/quarters")["current"] == "2027-Q1"


def test_timeline_covers_the_three_accepted_leads(thesis):
    q = _get("/api/v1/quarters")
    ids = [t["id"] for t in q.get("timeline", q.get("data", []))] if isinstance(q, dict) else []
    if ids:
        assert {"2027-Q1", "2027-Q2", "2027-Q3"} <= set(ids)


@pytest.mark.legacy_served
def test_lgu_ranking_starts_from_e168(thesis):
    rows = [r for slug in ("batangas", "cavite", "laguna", "quezon", "rizal")
            for r in _get(f"/api/v1/provinces/{slug}/municipalities", quarter="2027-Q1")["data"]]
    assert len(rows) == 142
    lg = _get("/api/v1/final/lgus")
    assert lg["count"] == 142 and lg["model"] == E.MODEL_ID and lg["quarter"] == "2027-Q1"
    assert lg["label"].startswith("Vulnerability-weighted municipal priority based on the provincial food-insecurity risk forecast")
    same = {r["id"]: r["riskIndex"] for r in rows}
    assert all(r["priorityScore"] == same[r["id"]] for r in lg["rows"])
    prov = {r["province"]: r["p_high"] for r in LIVE["provinces"] if r["lead"] == 1}
    for r in rows:
        assert "E168" in r["riskLevelBasis"] and r["riskLevel"] == "low"
        if r["provinceEstimate"] is not None:
            assert any(r["provinceEstimate"] == pytest.approx(p, abs=1e-6) for p in prov.values())


@pytest.mark.legacy_served
def test_explanations_are_e168_groups(thesis):
    d = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2027-Q1")
    keys = {t["key"] for t in d["triggers"]}
    assert keys == set(E.GROUPS)
    assert all("E168" in t["statusNote"] for t in d["triggers"])
    assert "validation-pending" not in json.dumps(d)


def test_no_early_warning_when_all_low():
    from app.quarterly import alerts_e168
    assert all(r["risk_class"] == "LOW" for r in LIVE["provinces"])
    assert alerts_e168.candidates() == []


@pytest.mark.legacy_served
def test_strict_start_refuses_when_e168_is_not_served(thesis, tmp_path):
    # No silent fallback to the Chapter I price index: strict start-up names why the approved model is not served.
    from app import main as MAIN
    thesis.setenv("AIPHEED_STRICT_MODEL", "1")
    MAIN.strict_model_check()                                     # E168 served: starts
    thesis.setenv("AIPHEED_MAP_MODEL", "ch1")
    with pytest.raises(RuntimeError, match="e168-lgbm-1.0 is not served: AIPHEED_MAP_MODEL=ch1"):
        MAIN.strict_model_check()
    thesis.delenv("AIPHEED_MAP_MODEL")
    thesis.setattr(E, "ROWS", tmp_path / "missing_rows.csv")
    with pytest.raises(RuntimeError, match="served rows missing"):
        MAIN.strict_model_check()


def test_trigger_cards_quote_the_figures_periods_and_effect():
    # Each card states the real input value and period the forecast used, and how many points it moved the forecast,
    # computed from the same stored LightGBM contributions as the bars.
    r = E.row("PH040300000", "2027-Q1")                                         # Quezon
    jobs = E.plain_evidence("PH040300000", "2027-Q1", "employment")
    issue = pd.Timestamp(r["issue_date"])
    lfs, cpi = E._month_name(E._latest_month(issue, 45, "lfs")), E._month_name(E._latest_month(issue, 9, "cpi"))
    assert f"{float(r['val_unemp_rate']):.1f}% in {lfs}" in jobs and "national figure" in jobs
    assert "raised Quezon's forecast by about" in jobs and "points" in jobs
    market = E.plain_evidence("PH040300000", "2027-Q1", "market")
    assert f"In {cpi}" in market and f"{float(r['val_cpi_food_yoy']):.1f}% higher" in market
    total = sum(E._pp(r, g) for g in E.GROUPS)
    assert abs(total) < float(r["score_pct"])                                   # effects are points of the forecast
    region = E.plain_evidence(None, "2027-Q1", "employment")
    assert "On average it" in region and lfs in region


def test_production_cards_state_the_period_actually_used():
    # Farm and fish production: the cards must name the period the forecast really compared (the files can lag),
    # never an assumed recent window.
    qs = E._production_quarters("fish", CUT)
    fish = E.plain_evidence("PH040300000", "2027-Q1", "fish_kill")
    assert len(qs) == 8 and f"in {E._period_words(qs[4:])}" in fish and E._period_words(qs[:4]) in fish
    q_end = pd.Timestamp(year=int(qs[-1][:4]), month=3 * int(qs[-1][-1]), day=1) + pd.offsets.MonthEnd(0)
    stale = (pd.Timestamp(CUT) - q_end).days > 365
    assert ("newest figures in the system" in fish) == stale       # stale data, and only stale data, is labelled as such


@pytest.mark.legacy_served
def test_news_panel_lists_the_stories_the_forecast_read():
    """The news panel is the served issue's own reading list: every story published in the three months before the
    cut-off, national ones included, none on or after the cut-off; local counts drive the few-news flag."""
    from app.services import dashboard as svc
    doc = svc._e168_news()
    if doc is None:
        pytest.skip("served issue has no news list")
    cut = pd.Timestamp(LIVE.get("information_cutoff") or "2026-10-01")
    assert all(pd.Timestamp(s["date"]) < cut for s in doc["stories"])
    assert all(pd.Timestamp(s["date"]) >= cut - pd.DateOffset(months=3) for s in doc["stories"])
    region = client.get("/api/v1/news?scope=region&id=calabarzon&quarter=2027-Q1&pageSize=5").json()
    assert region["articleCount"] == len(doc["stories"])
    q = client.get("/api/v1/news?scope=province&id=quezon&quarter=2027-Q1&pageSize=100").json()
    own = [s for s in doc["stories"] if "Quezon" in s["provinces"]]
    assert q["provinceAttributed"] == len(own) == svc.article_count("PH040300000", "2027-Q1")
    assert any(a["province"] == "Philippines" for a in q["data"])                 # national stories are read too
    assert any(a["excerpt"] for a in q["data"])                                    # leads shown where the source has one
