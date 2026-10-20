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

# E53 port (tina-e53-port): this E41-E48 candidate test runs under Angel's original configuration (E36 record,
# lead-2 target, no preview); the served default is now E53 (see tests/integration/test_e53_served_model.py).
pytestmark = pytest.mark.usefixtures("angel_original_config")
client = TestClient(app)
SUBJECTS = [("province", p) for p in ("cavite", "laguna", "batangas", "rizal", "quezon")] + [("region", "calabarzon")]
GEO = Path("..") / "frontend" / "public" / "calabarzon-municities.json"


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")


@pytest.mark.parametrize("scope,id_", SUBJECTS)
def test_news_feed_returns_real_relevant_articles(scope, id_):
    """E53 port: the card lists exactly the validated (R1.1) evidence-quarter articles the estimate used, with no
    back-extension and no keyword-only matches, so a province can have 0 (Cavite, Batangas and Quezon in 2026-Q3:
    a news-coverage gap, not low risk). The E45 extended feed (_e31_news_e45_feed) is kept but not served."""
    r = client.get(f"/api/v1/news?scope={scope}&id={id_}&quarter=2027-Q1&pageSize=100")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == body["articleCount"] == body["validatedCount"] and body["triggerMatchCount"] == 0
    ev = body["evidenceQuarter"]
    assert ev == "2026-Q3" and body["windowQuarters"] == [ev]                # the evidence quarter only
    if scope == "region":
        assert body["articleCount"] >= 1
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


def test_every_lgu_gets_an_approved_palette_band_and_joins_its_geometry():
    """The approved map colours an LGU with RISK_COLORS[riskLevel]; every LGU must carry a band (or null only when it
    has no index, shown as the approved gray), and every boundary feature must join an API record."""
    from app.services import reference as ref

    rows = {}
    for p in ("cavite", "laguna", "batangas", "rizal", "quezon"):
        for x in client.get(f"/api/v1/provinces/{p}/municipalities?quarter=2027-Q1").json()["data"]:
            rows[_key(p, x["name"])] = x
    geo = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    keys = {_key(f["properties"]["province_id"], f["properties"]["name"]) for f in geo}
    assert len(rows) == len(keys) == 142 and set(rows) == keys
    for x in rows.values():
        if x["riskIndex"] is None:
            assert x["riskLevel"] is None
        else:
            assert x["riskLevel"] == ref.risk_level(x["riskIndex"]) and x["riskLevel"] in ("low", "high")
        assert "not a measured or official municipal" in x["riskLevelBasis"]
    assert sum(x["riskLevel"] is not None for x in rows.values()) == 142
