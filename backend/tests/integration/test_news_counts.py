"""News counts. view=published lists and counts the articles published inside the quarter (de-duplicated); a quarter
that has not started has none; the region is the de-duplicated union of the five provinces. The news card
(view=used) and every article count (province summary, explainability, LGUs), limitedSignal and provinceCounts.limited
are the validated articles of the estimate's evidence quarter, de-duplicated: the record row's own
provenance.news_evidence_window.evidence_quarter, for EVERY quarter the quarter before it (a backtest too), i.e. the
news the estimate was built from, published before the row's origin."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as svc

client = TestClient(app)
REC = json.loads(Path("data/e53/e53_record.json").read_text(encoding="utf-8"))
PROV = {"cavite": "PH040100000", "laguna": "PH040200000", "batangas": "PH040500000", "rizal": "PH040400000",
        "quezon": "PH040300000"}
QUARTERS = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"]


@pytest.fixture
def lead2_e53(serve_e53, lead2, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    yield


def _bounds(q):
    y, n = int(q[:4]), int(q[-1])
    return f"{y}-{3 * n - 2:02d}-01", (f"{y + 1}-01-01" if n == 4 else f"{y}-{3 * n + 1:02d}-01")


def _truth(codes, q):
    """Independent count: record articles of these provinces published inside q (Philippine date), by title."""
    s, e = _bounds(q)
    if q == "2027-Q1":                                    # not started on 2026-10-15
        return set()
    return {a["title"].strip().lower() for a in REC["news"]["articles"]
            if a["province_code"] in codes and s <= a["published_ph"][:10] < e}


def _evidence_truth(codes, q):
    """Independent count: validated record articles of these provinces in the estimate's evidence quarter, read from
    the record row's own provenance (backtests included: each was built from the previous quarter's news)."""
    row = next(x for x in REC["quarters"] if x["quarter"] == q)
    ev = row["provenance"]["news_evidence_window"]["evidence_quarter"]
    return {a["title"].strip().lower() for a in REC["news"]["articles"]
            if a["province_code"] in codes and a["quarter"] == ev}


def _all_pages(scope, ident, q):
    out, page = [], 1
    while True:
        b = client.get(f"/api/v1/news?scope={scope}&id={ident}&quarter={q}&page={page}&pageSize=5&view=published").json()
        out += b["data"]
        if len(b["data"]) < 5:
            return out
        page += 1


@pytest.mark.parametrize("q", QUARTERS)
def test_card_count_equals_the_list_and_the_quarters_own_articles(lead2_e53, q):
    s, e = _bounds(q)
    for scope, ident, codes in [("region", "calabarzon", list(PROV.values()))] + \
                               [("province", p, [c]) for p, c in PROV.items()]:
        card = client.get(f"/api/v1/news?scope={scope}&id={ident}&quarter={q}&page=1&pageSize=20&view=published").json()
        listed = _all_pages(scope, ident, q)
        assert card["articleCount"] == card["total"] == len(listed) == len(_truth(codes, q)), (q, ident)
        assert all(s <= a["date"] < e for a in listed), (q, ident)
        assert len({a["url"] for a in listed}) == len({a["title"].strip().lower() for a in listed}) == len(listed)
        assert [a["date"] for a in listed] == sorted((a["date"] for a in listed), reverse=True)   # newest first
        ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter={q}").json()
        assert ex["articleCount"] == len(_evidence_truth(codes, q)), (q, ident)          # the evidence quarter's
        if scope == "province":
            prov = {p["id"]: p for p in client.get(f"/api/v1/provinces?quarter={q}").json()["data"]}
            assert prov[ident]["articleCount"] == len(_evidence_truth(codes, q)), (q, ident)


@pytest.mark.parametrize("q", QUARTERS)
def test_region_is_the_deduplicated_union_of_the_provinces(lead2_e53, q):
    union = set()
    for p in PROV:
        union |= {a["id"] for a in _all_pages("province", p, q)}
    region = client.get(f"/api/v1/news?scope=region&id=calabarzon&quarter={q}&view=published").json()
    assert region["articleCount"] == len(union)


def test_a_quarter_that_has_not_started_has_no_news(lead2_e53):
    for scope, ident in [("region", "calabarzon")] + [("province", p) for p in PROV]:
        card = client.get(f"/api/v1/news?scope={scope}&id={ident}&quarter=2027-Q1&view=published").json()
        assert card["articleCount"] == card["total"] == 0 and card["data"] == [] and card["topics"] == []
        assert card["evidenceNote"].startswith("This quarter has not started; no news yet.")
        assert card["evidenceMode"] == "PUBLISHED_SO_FAR" and card["windowEnd"] is None   # card shows the note as is
        ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}&quarter=2027-Q1").json()
        codes = list(PROV.values()) if scope == "region" else [PROV[ident]]
        assert ex["articleCount"] == len(_evidence_truth(codes, "2027-Q1"))   # its evidence quarter (2026-Q3)
    assert all(p["articleCount"] == len(_evidence_truth([PROV[p["id"]]], "2027-Q1"))
               for p in client.get("/api/v1/provinces?quarter=2027-Q1").json()["data"])


@pytest.mark.parametrize("q", QUARTERS)
def test_limited_signal_is_fewer_than_five_on_the_same_counts(lead2_e53, q):
    prov = {p["id"]: p for p in client.get(f"/api/v1/provinces?quarter={q}").json()["data"]}
    for p, code in PROV.items():
        n = len(_evidence_truth([code], q))                  # the evidence quarter's validated articles
        assert prov[p]["articleCount"] == n
        assert prov[p]["limitedSignal"] is (n < 5), (q, p, n)
    region = client.get(f"/api/v1/forecast?scope=region&id=calabarzon&quarter={q}").json()
    assert region["provinceCounts"]["limited"] == sum(1 for p in prov.values() if p["articleCount"] < 5)
    for p in PROV:                                          # the tag carries over to every LGU of the province
        rows = client.get(f"/api/v1/provinces/{p}/municipalities?quarter={q}").json()["data"]
        assert rows and all(m["limitedSignal"] is prov[p]["limitedSignal"] for m in rows), (q, p)


def test_q3_2026_limited_flags_follow_the_evidence_quarter_q2(lead2_e53):
    """The 2026-Q3 backtest was built at origin 2026-07-01 from 2026-Q2 news (its record row's
    news_evidence_window.evidence_quarter), so its card, article count and limitedSignal count the validated 2026-Q2
    articles, the news the estimate actually used, not the 2026-Q3 articles published after its origin. (Audit item e
    had moved the flag to the quarter's own news; the card now shows what each estimate used, and the flag follows the
    same set.) A province with 0 evidence articles is flagged."""
    prov = {p["id"]: p for p in client.get("/api/v1/provinces?quarter=2026-Q3").json()["data"]}
    for p, code in PROV.items():
        assert prov[p]["articleCount"] == len(_evidence_truth([code], "2026-Q3")), p
    assert prov["rizal"]["articleCount"] == 5 and prov["rizal"]["limitedSignal"] is False      # 2026-Q2: 5 articles
    assert prov["laguna"]["articleCount"] == 2 and prov["laguna"]["limitedSignal"] is True     # 2026-Q2: 2 articles
    q1 = {p["id"]: p for p in client.get("/api/v1/provinces?quarter=2026-Q1").json()["data"]}  # evidence 2025-Q4
    assert q1["quezon"]["articleCount"] == 0 and q1["quezon"]["limitedSignal"] is True


def test_the_same_article_is_counted_once(lead2_e53, monkeypatch):
    arts = REC["news"]["articles"]
    a = next(x for x in arts if x["province_code"] == PROV["laguna"] and x["published_ph"].startswith("2026-0"))
    q = next(q for q in QUARTERS if _bounds(q)[0] <= a["published_ph"][:10] < _bounds(q)[1])
    before = client.get(f"/api/v1/news?scope=province&id=laguna&quarter={q}&view=published").json()["articleCount"]
    copies = [dict(a, article_key="dup-key-1"), dict(a, article_key="dup-key-2", link="https://example.org/x")]
    monkeypatch.setattr(svc, "_e31_articles", lambda: arts + copies)    # same title / same link, new keys
    after = client.get(f"/api/v1/news?scope=province&id=laguna&quarter={q}&view=published").json()
    assert after["articleCount"] == after["total"] == before
    n = svc.article_count(PROV["laguna"], q)                 # evidence-quarter count, still de-duplicated
    monkeypatch.setattr(svc, "_e31_articles", lambda: arts)
    assert svc.article_count(PROV["laguna"], q) == n


def test_the_model_inputs_are_untouched(lead2_e53):
    """Display only: the record's news (what the model used) is not changed by the card counts."""
    assert len(REC["news"]["articles"]) == 140
    used = client.get("/api/v1/news?scope=region&id=calabarzon&quarter=2026-Q4").json()   # view=used
    assert used["sourceQuarter"] == "2026-Q3" and used["articleCount"] == 9


def test_a_running_forecast_quarter_lists_its_own_news_not_the_evidence_quarters(lead2_e53):
    """Option B (E57 news card, step 2): the card's hard-coded text for a forecast quarter (RightAnalyticsPanel.tsx
    lines 259 and 291: "not used by this forecast", "No relevant articles yet for <quarter>") stays true only if the
    list is the quarter's own news, so 2026-Q4 keeps its own articles (Quezon: 1, while 2026-Q3 has none)."""
    card = client.get("/api/v1/news?scope=province&id=quezon&quarter=2026-Q4&view=published").json()
    assert card["articleCount"] == card["total"] == len(card["data"]) == 1
    assert card["data"][0]["date"] == "2026-10-13" and card["usedByForecast"] is False
    assert card["evidenceMode"] == "PUBLISHED_SO_FAR" and card["windowEnd"] == "2026-10-14"
    assert card["forecastEvidenceQuarter"] == "2026-Q3"
