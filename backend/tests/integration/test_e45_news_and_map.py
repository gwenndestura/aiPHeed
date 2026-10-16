"""
tests/integration/test_e45_news_and_map.py
------------------------------------------
E45 regressions: the dashboard news feed returns real, food-relevant, correctly timed articles for every province and
the region; every one of the 142 cities and municipalities gets an honest map status (vulnerability band or
insufficient data, never a fabricated forecast); geometry and API records join completely.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as svc

client = TestClient(app)
SUBJECTS = [("province", p) for p in ("cavite", "laguna", "batangas", "rizal", "quezon")] + [("region", "calabarzon")]
GEO = Path("..") / "frontend" / "public" / "calabarzon-municities.json"


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


@pytest.mark.parametrize("scope,id_", SUBJECTS)
def test_news_feed_returns_real_relevant_articles(scope, id_):
    r = client.get(f"/api/v1/news?scope={scope}&id={id_}&quarter=2027-Q1&pageSize=100")
    assert r.status_code == 200
    body = r.json()
    assert body["articleCount"] >= 1 and len(body["data"]) == body["articleCount"]
    assert body["validatedCount"] + body["triggerMatchCount"] == body["articleCount"]
    ev = body["evidenceQuarter"]
    assert all(q <= ev for q in body["windowQuarters"])                       # never news after the evidence quarter
    for a in body["data"]:
        assert a["title"] and a["source"] and a["date"] and a["url"].startswith("http")
        assert a["relevanceStatus"] in ("validated", "trigger_match")
        assert a["quarter"] <= ev and a["date"] < "2026-10-01"                 # published before the forecast origin
        if a["relevanceStatus"] == "trigger_match":
            assert a["triggers"] and svc.FOOD_CONTEXT.search(a["title"])
        if scope == "province":
            assert a["province"] and a["province"].lower() == id_


def test_explainability_count_matches_news_feed():
    for p in ("laguna", "quezon"):
        n = client.get(f"/api/v1/news?scope=province&id={p}&quarter=2027-Q1&pageSize=100").json()["articleCount"]
        e = client.get(f"/api/v1/explainability?scope=province&id={p}&quarter=2027-Q1").json()["articleCount"]
        assert n == e


def test_unrelated_food_titles_are_excluded():
    titles = {a["title"] for a in svc._news_pool()}
    assert not any(re.search(r"where to eat|food trip", t, re.I) for t in titles)


def _key(province, name):
    return province + "::" + re.sub(r"\s+city$", "", re.sub(r"^city of\s+", "", name.lower().strip()))


def test_every_lgu_has_an_honest_map_status_and_joins_its_geometry():
    rows = {}
    for p in ("cavite", "laguna", "batangas", "rizal", "quezon"):
        for x in client.get(f"/api/v1/provinces/{p}/municipalities?quarter=2027-Q1").json()["data"]:
            rows[_key(p, x["name"])] = x
    geo = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    keys = {_key(f["properties"]["province_id"], f["properties"]["name"]) for f in geo}
    assert len(rows) == len(keys) == 142 and set(rows) == keys
    for x in rows.values():
        assert x["mapStatus"] in ("vulnerability", "insufficient_data") and x["mapLabel"]
        assert x["riskLevel"] is None                                          # never banded as a forecast
        if x["mapStatus"] == "vulnerability":
            v = x["vulnerabilityIndex"]
            assert 0 <= v <= 1
            assert x["mapCategory"] == ("low" if v < 1 / 3 else "medium" if v < 2 / 3 else "high")
            assert "not a municipal forecast" in x["mapNote"]
        else:
            assert x["mapCategory"] is None
