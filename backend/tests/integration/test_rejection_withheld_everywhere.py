"""
tests/integration/test_rejection_withheld_everywhere.py
-------------------------------------------------------
Thesis p. 60: a rejected province-quarter "will be withheld from the map, the rankings, and the regional mean". With
AIPHEED_REQUIRE_APPROVAL off (the default), a DA administrator rejects Batangas 2026-Q4 on a throwaway database; no
public surface may show its forecast: /provinces, /ranking, /forecast, /explainability (province and region), its LGUs,
/report/data (trend and driver report) and the backend PDF. The other provinces' numbers are unchanged.
"""
from __future__ import annotations

import pytest

from tests.conftest import _clear_dashboard_caches
from tests.integration.test_api_admin import api, auth_headers, make_user  # noqa: F401  (throwaway-DB fixture)

Q = "2026-Q4"


@pytest.fixture
def rejected(api, monkeypatch):
    monkeypatch.delenv("AIPHEED_REQUIRE_APPROVAL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")
    _clear_dashboard_caches()
    before = {p["id"]: p["riskScore"] for p in api.get(f"/api/v1/provinces?quarter={Q}").json()["data"]}
    make_user(api)
    h = auth_headers(api)
    api.get(f"/api/v1/admin/review?quarter={Q}", headers=h)
    r = api.post("/api/v1/admin/review/rv_2026Q4_batangas/reject", headers=h,
                 json={"reason": "Data quality issue", "notes": "test"})
    assert r.status_code == 200, r.text
    _clear_dashboard_caches()
    yield before
    _clear_dashboard_caches()


def test_map_ranking_and_regional_mean_exclude_the_rejected_province(api, rejected):
    prov = {p["id"]: p for p in api.get(f"/api/v1/provinces?quarter={Q}").json()["data"]}
    assert prov["batangas"]["riskScore"] is None and prov["batangas"]["withheld"] is True
    assert {k: v["riskScore"] for k, v in prov.items() if k != "batangas"} == \
        {k: v for k, v in rejected.items() if k != "batangas"}                       # others unchanged
    ranking = [r["id"] for r in api.get(f"/api/v1/ranking?quarter={Q}").json()["data"]]
    assert "batangas" not in ranking
    region = api.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={Q}").json()
    others = [v for k, v in rejected.items() if k != "batangas"]
    assert region["provincesIncluded"] == 4 and region["riskScore"] == round(sum(others) / 4, 4)
    assert api.get(f"/api/v1/forecast?scope=province&id=batangas&quarter={Q}").status_code == 404


def test_explainability_withholds_the_province_and_pools_the_rest(api, rejected):
    assert api.get(f"/api/v1/explainability?scope=province&id=batangas&quarter={Q}").status_code == 404
    rx = api.get(f"/api/v1/explainability?scope=region&id=calabarzon&quarter={Q}").json()
    region = api.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={Q}").json()
    assert rx["riskScore"] == region["riskScore"]                                   # the mean of the four
    assert sum(t["pct"] for t in rx["triggers"]) == 100


def test_its_lgus_have_no_index_and_the_published_ranks_exclude_them(api, rejected):
    lgus = api.get(f"/api/v1/provinces/batangas/municipalities?quarter={Q}").json()["data"]
    assert len(lgus) == 34 and all(m["riskIndex"] is None and m["rankRegion"] is None for m in lgus)
    rest = [m for p in ("cavite", "laguna", "rizal", "quezon")
            for m in api.get(f"/api/v1/provinces/{p}/municipalities?quarter={Q}").json()["data"]]
    assert len(rest) == 108 and sorted(m["rankRegion"] for m in rest) == list(range(1, 109))


def test_reports_never_show_it(api, rejected):
    assert api.get(f"/api/v1/report/data?type=shap&scope=province&id=batangas&to={Q}").status_code == 404
    trend = api.get(f"/api/v1/report/data?type=trend&scope=region&from=2025-Q1&to={Q}")
    assert trend.status_code == 404 and "0.28" not in trend.text                  # refused, never printed
    assert api.get(f"/api/v1/report?scope=province&id=batangas&quarter={Q}").status_code == 404
    # a report that does not include the withheld quarter is still served
    assert api.get("/api/v1/report/data?type=trend&scope=region&from=2025-Q1&to=2026-Q3").status_code == 200
