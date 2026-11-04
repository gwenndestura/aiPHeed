"""
Regression tests for the 2026-11-04 audit defects (docs/audit_2026-11-04): D-03 Rule 1 on /final/risk/rows, D-05 the
in-progress quarter, D-06 driver evidence, D-09 /config horizons, D-12 /assessments, D-13 /report/data. None of these may
change a forecast: the last test pins the served probabilities.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import foodinsecurity_system as FI

client = TestClient(app, raise_server_exceptions=False)
QUEZON = "PH040300000"


def _clear_caches():
    """The dashboard's caches are keyed by the mode, not the export: leave none behind for tests of other exports."""
    from app.services import dashboard as D
    for mod in (D, FI):
        for v in vars(mod).values():
            if hasattr(v, "cache_clear"):
                v.cache_clear()


@pytest.fixture
def fi(monkeypatch):
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "foodinsecurity")
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setattr(FI, "DATA", FI.MAIN_DATA)
    monkeypatch.setattr(FI, "LGU_VULNERABILITY", FI.MAIN_DATA / "lgu_vulnerability.csv")
    _clear_caches()
    assert FI.active()
    yield
    _clear_caches()


def _rows(**params):
    r = client.get("/api/v1/final/risk/rows", params=params)
    assert r.status_code == 200
    return r.json()["rows"]


def test_unapproved_forecast_is_withheld_from_final_rows(fi):
    """The review table is empty here, so the issued 2027-Q1 forecast has no approval."""
    assert _rows(quarter="2027-Q1") == []
    assert _rows(kind="forecast") == []
    assert "2027-Q1" not in {r["quarter"] for r in _rows()}
    assert len(_rows(quarter="2026-Q3")) == 5                      # walk-forward quarters are not gated


def test_approved_forecast_is_returned(fi, monkeypatch):
    async def nothing_held(db, quarter=None):
        return set()

    monkeypatch.setattr("app.services.review.rejected_pairs", nothing_held)
    rows = _rows(quarter="2027-Q1")
    assert len(rows) == 5 and {float(r["probability"]) for r in rows} == {0.955803}


def test_unapproved_forecast_is_withheld_from_lgus(fi):
    r = client.get("/api/v1/provinces/quezon/municipalities", params={"quarter": "2027-Q1"})
    assert r.status_code == 200
    data = r.json().get("data", r.json().get("municipalities"))
    assert len(data) == 41
    assert all(x["riskIndex"] is None and x["riskLevel"] is None and x["rankInProvince"] is None
               and x["rankRegion"] is None and x["provinceEstimate"] is None for x in data)
    assert all(x["povertyRate"] is not None for x in data)         # PSA context stays


def test_past_quarter_lgus_are_not_withheld(fi):
    data = client.get("/api/v1/provinces/quezon/municipalities", params={"quarter": "2026-Q3"}).json()["data"]
    assert len(data) == 41 and all(x["riskIndex"] is not None for x in data)


def test_final_lgus_hide_unapproved_values(fi):
    rows = client.get("/api/v1/final/lgus").json()["rows"]
    assert len(rows) == 142 and all(r["priorityScore"] is None and r["priorityLevel"] is None for r in rows)


def test_final_lgus_show_approved_values(fi, monkeypatch):
    async def nothing_held(db, quarter=None):
        return set()

    monkeypatch.setattr("app.services.review.rejected_pairs", nothing_held)
    rows = client.get("/api/v1/final/lgus").json()["rows"]
    assert len(rows) == 142 and all(r["priorityScore"] is not None for r in rows)


def test_region_pdf_of_a_fully_withheld_quarter_is_refused_cleanly(fi):
    r = client.get("/api/v1/report", params={"quarter": "2027-Q1"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "forecast_withheld"


def test_in_progress_quarter_is_not_called_a_missing_round(fi):
    r = FI.row(QUEZON, "2026-Q4")
    assert FI.outcome_pending(r)
    text = FI.past_text(r)
    assert "not yet published" in text and "no regular SWS round" not in text and "past forecast" not in text


def test_a_real_missing_round_keeps_its_text(fi):
    r = FI.row(QUEZON, "2025-Q1")
    assert not FI.outcome_pending(r)
    assert "no regular SWS round" in FI.past_text(r)


def test_observed_quarter_keeps_its_text(fi):
    assert "past forecast; actual:" in FI.past_text(FI.row(QUEZON, "2026-Q3"))


def test_market_card_names_world_rice_and_real_effect(fi):
    t = FI.plain_evidence(QUEZON, "2027-Q1", "market")
    assert "World rice prices (World Bank) were 25.6% higher" in t
    assert "Actual effect on this forecast: +0.88" in t


def test_small_push_shows_its_real_size(fi):
    assert "Actual effect on this forecast: -0.01" in FI.plain_evidence(QUEZON, "2027-Q1", "fish_kill")
    assert "Actual effect on this forecast: -0.01" in FI.plain_evidence(QUEZON, "2027-Q1", "climate")


def test_not_input_groups_stay_without_effect(fi):
    assert FI.plain_evidence(QUEZON, "2027-Q1", "employment") == FI.NOT_INPUT_NOTE


def test_summary_states_what_the_bars_leave_out(fi):
    s = FI.sentence(QUEZON, "Quezon", "2027-Q1")
    assert "not shown in the bars, on this forecast: news +0.84 and past SWS hunger +0.57 log-odds" in s
    assert ". " not in s.rstrip(".").replace("0.", "0_")           # still one sentence: only the first is shown


def test_config_horizons_describe_the_served_model(fi):
    h = client.get("/api/v1/config").json()["horizons"]["forecast"]
    assert h["name"] == "Lead 2 forecasts"
    assert "E36" not in str(h) and "S1 = H" not in str(h) and "lead 1" not in h["name"]
    assert "above 11.3%" in h["definition"]


def test_report_data_without_range_does_not_crash(fi):
    r = client.get("/api/v1/report/data")
    assert r.status_code < 500


@pytest.mark.parametrize("path", ["/api/v1/assessments/quarters", "/api/v1/assessments/methodology",
                                  "/api/v1/assessments?quarter=2027-Q1"])
def test_assessments_say_unavailable(path):
    r = client.get(path)
    assert r.status_code in (200, 404, 503)
    if r.status_code == 503:
        assert "not available" in r.json()["detail"]


def test_fixes_change_no_forecast(fi):
    rows = FI.rows()
    assert len(rows) == 85
    assert float(FI.row(QUEZON, "2027-Q1")["probability"]) == 0.955803
    assert float(FI.row("PH040100000", "2027-Q1")["score"]) == pytest.approx(0.595646, abs=1e-6)
    assert FI.row(QUEZON, "2026-Q4")["class"] == "HIGH" and FI.kind(FI.row(QUEZON, "2026-Q4")) == "retrospective"
