"""
tests/integration/test_news_view.py
-----------------------------------
/news?view=: "used" (default) is the news a quarter's estimate was built from; "published" is the quarter's own
news so far. For the 2026-Q4 forecast the two differ: the forecast used 2026-Q3 news (published by 2026-10-01), and
the 2026-Q4 articles collected so far (to 2026-10-14) were not used by it.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _now(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


def get(**params):
    r = client.get("/api/v1/news", params={"pageSize": 100, **params})
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_q4_published_is_the_quarters_own_news_not_used_by_the_forecast():
    b = get(scope="region", id="calabarzon", quarter="2026-Q4", view="published")
    assert b["total"] == 3 and len(b["data"]) == 3
    assert b["evidenceQuarter"] == b["sourceQuarter"] == "2026-Q4" and b["evidenceMode"] == "PUBLISHED_SO_FAR"
    assert b["usedByForecast"] is False and b["forecastEvidenceQuarter"] == "2026-Q3"
    assert b["windowEnd"] == "2026-10-14"
    assert "Not used by the 2026-Q4 forecast" in b["evidenceNote"] and "2026-10-01" in b["evidenceNote"]
    provinces = [client.get("/api/v1/news", params={"scope": "province", "id": p, "quarter": "2026-Q4",
                                                    "view": "published"}).json()["total"]
                 for p in ("batangas", "quezon", "cavite", "laguna", "rizal")]
    assert provinces == [2, 1, 0, 0, 0]


def test_q4_default_view_is_unchanged():
    b = get(scope="region", id="calabarzon", quarter="2026-Q4")
    assert b["total"] == 9 and b["evidenceQuarter"] == "2026-Q3" and b["evidenceMode"] == "FORECAST"
    assert b["usedByForecast"] is True and b["forecastEvidenceQuarter"] == "2026-Q3"
    assert b == get(scope="region", id="calabarzon", quarter="2026-Q4", view="used")


def test_a_backtests_used_news_is_its_evidence_quarter_not_its_own():
    # the 2026-Q3 backtest was built at origin 2026-07-01 from 2026-Q2 news (its record row's evidence quarter)
    used = get(scope="region", id="calabarzon", quarter="2026-Q3", view="used")
    assert used["total"] == 15 and used["sourceQuarter"] == used["evidenceQuarter"] == "2026-Q2"
    assert used["usedByForecast"] is True and used["evidenceMode"] == "BACKTEST"
    assert used["forecastEvidenceQuarter"] == "2026-Q2" and used["forecastOrigin"] == "2026-07-01"
    assert all(a["date"] < "2026-07-01" for a in used["data"])
    # view=published keeps the quarter's own news, which its estimate did not use
    pub = get(scope="region", id="calabarzon", quarter="2026-Q3", view="published")
    assert pub["total"] == 9 and pub["evidenceQuarter"] == "2026-Q3" and pub["usedByForecast"] is False
    assert not ({a["id"] for a in used["data"]} & {a["id"] for a in pub["data"]})


def test_batangas_q4_published():
    b = get(scope="province", id="batangas", quarter="2026-Q4", view="published")
    assert b["total"] == 2 and b["usedByForecast"] is False and b["windowEnd"] == "2026-10-14"


def test_bad_view_is_rejected():
    assert client.get("/api/v1/news", params={"scope": "region", "id": "calabarzon", "view": "other"}).status_code == 422


# ---------------------------------------------------------------- the news card (view=used) = articleCount
def _evidence_set(code, q):
    """Independent: the record's validated articles of the estimate's evidence quarter (the record row's own
    provenance.news_evidence_window.evidence_quarter, for every quarter), de-duplicated (key/link/title)."""
    from app.ml.inference import e31_engine as E31

    row = E31.quarter_row(q, "nowcast")
    ev = row["provenance"]["news_evidence_window"]["evidence_quarter"]
    assert ev < q, (q, ev)                                   # always an earlier quarter (backtests included)
    seen, out = set(), set()
    for a in sorted(E31.record()["news"]["articles"], key=lambda a: a["published_ph"], reverse=True):
        if a["quarter"] != ev or (code is not None and a["province_code"] != code):
            continue
        keys = {("k", a["article_key"]), ("u", a.get("link") or ""), ("t", (a.get("title") or "").strip().lower())}
        if keys & seen:
            continue
        seen |= {k for k in keys if k[1]}
        out.add(a["article_key"])
    return out


def test_card_list_count_and_article_count_are_one_set_for_every_quarter_and_scope():
    from app.services import dashboard as svc

    quarters = [q["id"] for q in client.get("/api/v1/quarters").json()["quarters"]
                if client.get(f"/api/v1/provinces?quarter={q['id']}").status_code == 200]
    assert "2027-Q1" in quarters and "2026-Q4" in quarters                      # lead-2 preview on by default
    scopes = [("region", "calabarzon", None)] + [("province", s, svc.ref.province_code(s)) for s in svc.ref.PROVINCES]
    for q in quarters:
        prov = {p["id"]: p["articleCount"] for p in client.get(f"/api/v1/provinces?quarter={q}").json()["data"]}
        for scope, ident, code in scopes:
            card = get(scope=scope, id=ident, quarter=q, view="used")
            ids = {a["id"] for a in card["data"]}
            want = _evidence_set(code, q)
            assert ids == want and card["articleCount"] == card["total"] == len(want), (q, ident)
            origin = svc.E31.quarter_row(q, "nowcast")["origin"][:10]
            assert all(a["date"] < origin for a in card["data"]), (q, ident)        # published before the origin
            # the same evidence quarter splits the news SHAP across the five drivers
            assert svc._drivers(code or "PH040300000", q)["evidence_quarter"] == card["sourceQuarter"], (q, ident)
            assert svc.article_count(code, q) == len(want), (q, ident)
            ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter={q}").json()
            assert ex["articleCount"] == len(want), (q, ident)
            if code is not None:
                assert prov[ident] == len(want), (q, ident)


@pytest.mark.parametrize("q", ["2026-Q4", "2027-Q1"])
def test_forecast_quarters_card_is_the_evidence_quarters_news_before_the_origin(q):
    card = get(scope="region", id="calabarzon", quarter=q, view="used")
    assert card["evidenceMode"] == "FORECAST" and card["usedByForecast"] is True
    assert card["sourceQuarter"] == card["forecastEvidenceQuarter"] == "2026-Q3" and card["forecastOrigin"] == "2026-10-01"
    assert card["total"] == 9 and all(a["date"] < "2026-10-01" for a in card["data"])
