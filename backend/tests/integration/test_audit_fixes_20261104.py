"""
Regression tests for the 2026-11-04 audit defects (docs/audit_2026-11-04): D-03 rejected forecasts withheld on /final/risk/rows, automatic release of issued forecasts, D-05 the
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
SLUGS = ("cavite", "laguna", "quezon", "rizal", "batangas")


def _reject_all(monkeypatch, quarter="2027-Q1"):
    """An administrator has rejected the quarter's forecast for every province."""
    async def rejected(db, q=None):
        return {(s, quarter) for s in SLUGS}

    monkeypatch.setattr("app.services.review.rejected_pairs", rejected)


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


def test_issued_forecast_is_released_without_approval(fi):
    """Owner decision 2026-11-04: the review table is empty and the forecast is public anyway."""
    assert {float(r["probability"]) for r in _rows(quarter="2027-Q1")} == {0.955803}
    assert len(_rows(kind="forecast")) == 5
    d = client.get("/api/v1/provinces", params={"quarter": "2027-Q1"}).json()["data"]
    assert all(not x["withheld"] and x["riskScore"] is not None for x in d)
    assert client.get("/api/v1/explainability", params={"scope": "province", "id": "quezon", "quarter": "2027-Q1"}).status_code == 200
    data = client.get("/api/v1/provinces/quezon/municipalities", params={"quarter": "2027-Q1"}).json()["data"]
    assert len(data) == 41 and all(x["riskIndex"] is not None for x in data)


def test_rejected_forecast_is_withheld_from_final_rows(fi, monkeypatch):
    _reject_all(monkeypatch)
    assert _rows(quarter="2027-Q1") == []
    assert len(_rows(quarter="2026-Q3")) == 5


def test_final_rows_without_rejection_are_returned(fi):
    rows = _rows(quarter="2027-Q1")
    assert len(rows) == 5 and {float(r["probability"]) for r in rows} == {0.955803}


def test_rejected_forecast_is_withheld_from_lgus(fi, monkeypatch):
    _reject_all(monkeypatch)
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


def test_final_lgus_hide_rejected_values(fi, monkeypatch):
    from app.services import dashboard as D

    _reject_all(monkeypatch, D.latest_quarter())
    rows = client.get("/api/v1/final/lgus").json()["rows"]
    assert len(rows) == 142 and all(r["priorityScore"] is None and r["priorityLevel"] is None for r in rows)


def test_final_lgus_show_released_values(fi):
    rows = client.get("/api/v1/final/lgus").json()["rows"]
    assert len(rows) == 142 and all(r["priorityScore"] is not None for r in rows)


def test_region_pdf_of_a_fully_withheld_quarter_is_refused_cleanly(fi, monkeypatch):
    _reject_all(monkeypatch)
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


# ---------------------------------------------------------------------------------------------- second audit pass
@pytest.mark.parametrize("path", ["/api/v1/forecast/timeseries?id=cavite&to=x", "/api/v1/forecast/timeseries?id=cavite&from=-1",
                                  "/api/v1/report/data?to=x", "/api/v1/report/data?from=%27%20OR%201=1--"])
def test_bad_quarter_range_is_rejected_not_a_crash(path):
    assert client.get(path).status_code == 422


def test_security_headers_on_every_response():
    h = client.get("/api/v1/health").headers
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "no-referrer"
    assert client.get("/api/v1/nope").headers["x-content-type-options"] == "nosniff"


def test_forged_token_keeps_the_public_withheld_view(fi, monkeypatch):
    _reject_all(monkeypatch)
    r = client.get("/api/v1/provinces/cavite/municipalities", params={"quarter": "2027-Q1"},
                   headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 200 and all(x["riskIndex"] is None for x in r.json()["data"])
    assert client.get("/api/v1/explainability", params={"scope": "province", "id": "cavite", "quarter": "2027-Q1"},
                      headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 404


def test_signed_in_admin_still_sees_a_rejected_forecast(fi, monkeypatch):
    _reject_all(monkeypatch)

    async def admin(request, db):
        return True

    monkeypatch.setattr("app.api.v1.dashboard.is_admin_request", admin)
    monkeypatch.setattr("app.services.security.is_admin_request", admin)
    data = client.get("/api/v1/provinces/cavite/municipalities", params={"quarter": "2027-Q1"}).json()["data"]
    assert len(data) == 23 and all(x["riskIndex"] is not None for x in data)
    assert client.get("/api/v1/explainability", params={"scope": "province", "id": "cavite", "quarter": "2027-Q1"}).status_code == 200


def test_quarter_without_a_published_result_is_not_called_observed(fi):
    from app.services import dashboard as D

    states = {r["id"]: r["state"] for r in D._ch1_timeline()}
    assert states["2026-Q4"] == "forecast" and states["2026-Q3"] == "actual" and states["2027-Q1"] == "forecast"
