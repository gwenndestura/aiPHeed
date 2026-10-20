"""
tests/quality/test_functional_consistency.py
--------------------------------------------
ISO/IEC 25010 Functional suitability (functional correctness, consistency). For every served quarter, each
province's score is identical across /provinces, /forecast (province), /ranking, the PDF payload (/report/data figure
series, and Table 1 for the latest quarter) and /explainability's riskScore; the region score equals the mean of the
five. Throwaway database (no review rows, so nothing is withheld), never aipheed.db.
"""
from __future__ import annotations

import pytest

from app.services import dashboard as svc
from tests.integration.test_api_admin import api  # noqa: F401  (throwaway-DB client)

PROVINCES = ["cavite", "laguna", "quezon", "rizal", "batangas"]
NAMES = {"cavite": "Cavite", "laguna": "Laguna", "quezon": "Quezon", "rizal": "Rizal", "batangas": "Batangas"}


@pytest.fixture(autouse=True)
def _now(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-18T09:00:00")


def _qlabel(q: str) -> str:
    return q.replace("-", " ")


def test_every_quarter_scores_agree_across_endpoints(api):
    quarters = svc.available_quarters()
    assert len(quarters) >= 14
    report = api.get(f"/api/v1/report/data?type=trend&scope=region&from={quarters[0]}&to={quarters[-1]}").json()
    fig = next(b for b in report["blocks"] if b["kind"] == "figure" and b["chart"]["type"] == "line")["chart"]
    series = {s["name"]: dict(zip(fig["quarters"], s["values"])) for s in fig["series"]}
    checked = 0
    for q in quarters:
        prov = {p["id"]: p["riskScore"] for p in api.get(f"/api/v1/provinces?quarter={q}").json()["data"]}
        rank = {p["id"]: p["riskScore"] for p in api.get(f"/api/v1/ranking?quarter={q}").json()["data"]}
        assert set(prov) == set(PROVINCES) and rank == prov, q
        for s in PROVINCES:
            f = api.get(f"/api/v1/forecast?scope=province&id={s}&quarter={q}").json()["riskScore"]
            e = api.get(f"/api/v1/explainability?scope=province&id={s}&quarter={q}").json()["riskScore"]
            assert f == prov[s] and e == prov[s], (q, s, prov[s], f, e)
            assert series[NAMES[s]][_qlabel(q)] == prov[s], (q, s)
            checked += 1
        region = api.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={q}").json()["riskScore"]
        assert region == round(sum(prov.values()) / 5, 4), q
        rx = api.get(f"/api/v1/explainability?scope=region&id=calabarzon&quarter={q}").json()["riskScore"]
        assert rx == region, q
    assert checked == 5 * len(quarters)
    # Table 1 of the PDF payload (latest quarter, two decimals as printed)
    last = quarters[-1]
    prov = {p["id"]: p["riskScore"] for p in api.get(f"/api/v1/provinces?quarter={last}").json()["data"]}
    t1 = next(b for b in report["blocks"] if b["kind"] == "table")
    printed = {r[0]: r[1] for r in t1["rows"]}
    for s in PROVINCES:
        assert printed[NAMES[s]] == f"{prov[s]:.2f}", s


def test_driver_report_matches_explainability(api):
    q = svc.available_quarters()[-1]
    d = api.get(f"/api/v1/report/data?type=shap&scope=province&id=quezon&to={q}").json()
    bars = next(b for b in d["blocks"] if b["kind"] == "figure" and b["chart"]["type"] == "bars")["chart"]["bars"]
    ex = api.get(f"/api/v1/explainability?scope=province&id=quezon&quarter={q}").json()["triggers"]
    assert len(ex) == 5 and sum(t["pct"] for t in ex) == 100            # the API lists all five groups
    # the PDF figure lists the drivers with an effect (its renderer labels every bar "raises" or "lowers risk")
    assert [(b["pct"], b["direction"]) for b in bars] == [(t["pct"], t["direction"]) for t in ex if t["pct"] > 0]
