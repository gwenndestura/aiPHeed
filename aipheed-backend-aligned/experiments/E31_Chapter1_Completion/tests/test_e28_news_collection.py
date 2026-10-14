"""E28 Objective 1: the quarterly news collector, coverage audit, scoring store and FSSI panel, on CONTROLLED FIXTURES.

These tests prove the software paths only. They do not show that live collection works; the live evidence is
runs/news_live_probe*.json and the real backfill in backend_dev/data/news_e28 (reported separately in the final report).
"""
import json
from datetime import date, datetime, timedelta, timezone

import pytest

import _paths  # noqa: F401  (E28 guard + paths)
from app.news import sources as S
from app.news.audit import coverage_audit, missing_windows, status_view
from app.news.collector import (PROVINCE_QUERIES, PROVINCES, REGION, REGION_QUERIES, Collector, all_quarters,
                                query_text)
from app.news.store import NewsStore
from app.news.timeutil import PH, month_windows

UTC = timezone.utc
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def item(title, when_utc, domain="pna.gov.ph", link=None):
    return {"source_item_id": link or f"id-{title}", "title": title, "link": link or f"https://x/{title}",
            "source_domain": domain, "published_raw": when_utc}


class FakeSource:
    """Answers search(query, a, b) from a list of (title, iso, domain) by window, optionally capped or failing."""
    name = "fake"
    cap = 100

    def __init__(self, items=(), fail=None, cap=100, empty=False, leak=False):
        self.items, self.fail, self.cap, self.empty = list(items), fail or (lambda q, a, b: None), cap, empty
        self.leak = leak             # simulate a source that ignores its date filter
        self.calls = []

    def search(self, query, a, b):
        self.calls.append((query, a, b))
        st = self.fail(query, a, b)
        if st:
            return S.FetchResult(self.name, st, attempts=4, error=st)
        if self.empty:
            return S.FetchResult(self.name, S.EMPTY)
        got = []
        for it in self.items:
            d = datetime.fromisoformat(it["published_raw"]).astimezone(PH).date() if it["published_raw"][:2] == "20" else a
            if (self.leak or a <= d < b) and (it.get("_q") is None or it["_q"] in query):
                got.append(dict(it))
        got = got[: self.cap]
        return S.FetchResult(self.name, S.OK if got else S.EMPTY, items=got, n_raw=len(got),
                             at_cap=len(got) >= self.cap, attempts=1)


def collector(tmp_path, src, au="2026-Q2", now=NOW, cutoff=None, credible=lambda d: d != "spam.example"):
    st = NewsStore(tmp_path / "store")
    return st, Collector(st, [src], authorized_until=au, now=now, cutoff_ph=cutoff, credible=credible,
                         geocode=lambda t: "PH040500000" if "Batangas" in t else ("PH040200000" if "Laguna" in t else None))


# ------------------------------------------------------------------ plan and quarters
def test_every_province_and_both_languages_are_planned():
    assert set(PROVINCES) == {"Batangas", "Cavite", "Laguna", "Quezon", "Rizal"}
    assert {s.lang for s in PROVINCE_QUERIES} == {"en", "fil"} and {s.lang for s in REGION_QUERIES} == {"en", "fil"}
    for p in PROVINCES:
        for s in PROVINCE_QUERIES:
            assert p in query_text(s, p)
    assert '-"Quezon City"' in query_text(PROVINCE_QUERIES[0], "Quezon")


def test_all_22_study_quarters_and_refusal_outside_the_authorization(tmp_path):
    qs = all_quarters("2026-Q2")
    assert qs[0] == "2021-Q1" and qs[-1] == "2026-Q2" and len(qs) == 22
    st, col = collector(tmp_path, FakeSource(empty=True))
    res = col.run("backfill", ["2020-Q4", "2026-Q3"], provinces=["Batangas"])
    start = [r for r in st.read("runs") if r["event"] == "start"][0]
    assert start["refused_quarters"] == ["2020-Q4", "2026-Q3"] and res["requests"] == 0


# ------------------------------------------------------------------ dates, boundaries, cutoffs
def test_quarter_boundary_uses_philippine_time(tmp_path):
    src = FakeSource([item("Batangas rice late Q1", "2021-03-31T15:59:00+00:00"),     # 23:59 PHT 31 Mar
                      item("Batangas rice early Q2", "2021-03-31T16:30:00+00:00")])    # 00:30 PHT 1 Apr
    st, col = collector(tmp_path, src)
    col.run("backfill", ["2021-Q1", "2021-Q2"], provinces=["Batangas"])
    q = {a["title"]: a["quarter"] for a in st.articles.values()}
    assert q == {"Batangas rice late Q1": "2021-Q1", "Batangas rice early Q2": "2021-Q2"}


def test_articles_after_the_authorized_limit_or_cutoff_are_refused_and_never_stored_as_text(tmp_path):
    src = FakeSource([item("Batangas price before limit", "2026-06-30T15:00:00+00:00"),   # 23:00 PHT 30 Jun
                      item("Batangas SECRET after limit", "2026-06-30T16:30:00+00:00")], leak=True)  # 00:30 PHT 1 Jul
    st, col = collector(tmp_path, src)
    col.run("backfill", ["2026-Q2"], provinces=["Batangas"])
    assert [a["title"] for a in st.articles.values()] == ["Batangas price before limit"]
    rej = (tmp_path / "store" / "rejected.jsonl").read_text()
    assert "SECRET" not in rej and "AFTER_AUTHORIZED_LIMIT" in rej
    # forecast cutoff inside the authorized period: an article one minute after it is refused
    src2 = FakeSource([item("Batangas at cutoff", "2026-05-14T16:00:00+00:00"),
                       item("Batangas after cutoff", "2026-05-14T16:01:00+00:00")], leak=True)
    st2, col2 = collector(tmp_path / "b", src2, cutoff=datetime(2026, 5, 15, 0, 0, tzinfo=PH))
    col2.run("backfill", ["2026-Q2"], provinces=["Batangas"])
    assert [a["title"] for a in st2.articles.values()] == ["Batangas at cutoff"]
    assert "AFTER_CUTOFF" in (tmp_path / "b" / "store" / "rejected.jsonl").read_text()


def test_pre_2021_unparseable_and_non_credible_items_are_quarantined(tmp_path):
    src = FakeSource([item("Batangas old", "2020-12-31T15:00:00+00:00"), item("Batangas spam", "2021-01-05T00:00:00+00:00",
                      domain="spam.example"), {**item("Batangas undated", "2021-01-06T00:00:00+00:00"), "published_raw": "Mon, 25 Ma"}])
    src.items[2]["_q"] = None
    st, col = collector(tmp_path, src)
    # the undated item is returned by the first window only
    src.search_orig = src.search
    col.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    reasons = [json.loads(l)["reason"] for l in (tmp_path / "store" / "rejected.jsonl").read_text().splitlines()]
    assert "NON_CREDIBLE_SOURCE" in reasons and "UNPARSEABLE_DATE" in reasons
    assert not st.articles


# ------------------------------------------------------------------ duplicates, idempotence, interruption
def test_duplicates_across_queries_sources_and_runs_become_one_article(tmp_path):
    src = FakeSource([item("Batangas rice price up", "2021-02-10T02:00:00+00:00", link="https://pna/1")])
    st, col = collector(tmp_path, src)
    col.run("backfill", ["2021-Q1"], provinces=["Batangas", "Laguna"])     # 8 queries return the same story
    assert len(st.articles) == 1
    n_sight = len(st.read("sightings"))
    assert n_sight == 8
    # a second source returning the same story under another link is still the same article
    other = FakeSource([item("Batangas  rice price UP!", "2021-02-10T05:00:00+00:00", link="https://gdelt/xyz")])
    other.name = "fake2"
    col2 = Collector(st, [other], authorized_until="2026-Q2", now=NOW, credible=lambda d: True, geocode=lambda t: None)
    col2.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    assert len(NewsStore(tmp_path / "store").articles) == 1


def test_interrupted_run_resumes_without_duplicates_and_rerun_is_idempotent(tmp_path):
    items = [item(f"Batangas story {i}", (datetime(2021, 1, 1, 3, tzinfo=UTC) + timedelta(days=i)).isoformat())
             for i in range(80)]
    src = FakeSource(items)
    st, col = collector(tmp_path, src)
    r1 = col.run("backfill", ["2021-Q1"], provinces=["Batangas"], max_requests=5)
    assert r1["status"] == "INTERRUPTED_BUDGET"
    # a torn last line (crash mid-write) is tolerated on reload
    with open(tmp_path / "store" / "articles.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"article_key": "torn')
    st2 = NewsStore(tmp_path / "store")
    assert st2.torn_lines == {"articles": 1}
    col2 = Collector(st2, [src], authorized_until="2026-Q2", now=NOW, credible=lambda d: True, geocode=lambda t: None)
    r2 = col2.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    assert r2["status"] == "COMPLETED" and r2["requests"] == 12 - 5
    keys = {a["article_key"] for a in st2.articles.values()}
    assert len(keys) == 80
    r3 = Collector(NewsStore(tmp_path / "store"), [src], authorized_until="2026-Q2", now=NOW,
                   credible=lambda d: True, geocode=lambda t: None).run("backfill", ["2021-Q1"], provinces=["Batangas"])
    assert r3["requests"] == 0                                    # nothing left to do: idempotent
    sv = status_view(NewsStore(tmp_path / "store"), "2026-Q2", now=NOW)
    assert sv["torn_lines"] == {"articles": 1}


# ------------------------------------------------------------------ caps, pagination, failures
def test_a_window_at_the_cap_is_split_until_it_fits_and_a_one_day_cap_is_flagged(tmp_path):
    many = [item(f"Batangas daily {i}", (datetime(2021, 1, 1, 3, tzinfo=UTC) + timedelta(days=i // 4)).isoformat())
            for i in range(31 * 4)]                               # 4 stories per day in January
    src = FakeSource(many, cap=10)
    st, col = collector(tmp_path, src)
    col.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    jan = [a for a in st.articles.values() if a["ph_date"].startswith("2021-01")]
    assert len(jan) == 124                                       # nothing lost to the cap
    src2 = FakeSource([item(f"Batangas burst {i}", "2021-01-15T03:00:00+00:00") for i in range(15)], cap=10)
    st2, col2 = collector(tmp_path / "b", src2)
    col2.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    assert any(w["status"] == "TRUNCATED_AT_MIN_WINDOW" for w in st2.windows.values())
    row = [r for r in coverage_audit(st2, ["2021-Q1"], model_key="m") if r["province"] == "Batangas"][0]
    assert row["collection_status"] == "PARTIAL" and row["windows_truncated_at_minimum"] >= 1


def test_empty_answers_and_failed_requests_are_reported_differently(tmp_path):
    st, col = collector(tmp_path, FakeSource(empty=True))
    col.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    row = [r for r in coverage_audit(st, ["2021-Q1"], model_key="m") if r["province"] == "Batangas"][0]
    assert row["collection_status"] == "COMPLETE" and row["coverage_status"] == "COMPLETE_NO_USABLE_EVIDENCE"
    assert "never evidence of zero food insecurity" in row["note"]
    st2, col2 = collector(tmp_path / "f", FakeSource(fail=lambda q, a, b: S.FAILED))
    col2.max_consecutive_failures = 100
    col2.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    row2 = [r for r in coverage_audit(st2, ["2021-Q1"], model_key="m") if r["province"] == "Batangas"][0]
    assert row2["collection_status"] == "FAILED" and row2["coverage_status"] == "NO_USABLE_EVIDENCE_COLLECTION_FAILED"
    assert row2["failed_requests"] == 12
    st3 = NewsStore(tmp_path / "n")
    row3 = [r for r in coverage_audit(st3, ["2021-Q1"], model_key="m") if r["province"] == "Cavite"][0]
    assert row3["coverage_status"] == "NOT_ATTEMPTED"
    assert len(missing_windows(st2, ["2021-Q1"])) >= 12


def test_a_failing_source_stops_the_run_and_a_later_run_retries_only_the_failed_windows(tmp_path):
    state = {"down": True}
    src = FakeSource([item("Batangas x", "2021-02-02T03:00:00+00:00")],
                     fail=lambda q, a, b: S.RATE_LIMITED if state["down"] else None)
    st, col = collector(tmp_path, src)
    col.max_consecutive_failures = 3
    r = col.run("backfill", ["2021-Q1"], provinces=["Batangas"])
    assert r["status"].startswith("STOPPED_SOURCE_UNAVAILABLE") and r["requests"] == 3
    state["down"] = False
    r2 = Collector(NewsStore(tmp_path / "store"), [src], authorized_until="2026-Q2", now=NOW, credible=lambda d: True,
                   geocode=lambda t: None).run("backfill", ["2021-Q1"], provinces=["Batangas"])
    assert r2["status"] == "COMPLETED" and r2["requests"] == 12
    assert not missing_windows(NewsStore(tmp_path / "store"), ["2021-Q1"])[:1] or \
        all(m["province"] != "Batangas" for m in missing_windows(NewsStore(tmp_path / "store"), ["2021-Q1"]))


# ------------------------------------------------------------------ HTTP layer: retries, rate limits, malformed
class R:
    def __init__(self, code, body=b""):
        self.status_code, self.content = code, body
        self.text = body.decode("utf-8", "replace")


RSS = (b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
       b'<item><title>Lipa rice up - PNA</title><link>https://news.google.com/a1</link><guid>g1</guid>'
       b'<pubDate>Tue, 02 Feb 2021 07:00:00 GMT</pubDate><source url="https://www.pna.gov.ph">PNA</source></item>'
       b'</channel></rss>')
EMPTY_RSS = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'


def seq_get(*responses):
    it = iter(responses)

    def get(url, timeout, headers):
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r
    return get


def test_transient_network_errors_and_google_404_are_retried():
    sleeps = []
    g = S.GoogleNewsRSS(http_get=seq_get(TimeoutError("t"), R(404), R(200, RSS)), sleep=sleeps.append)
    res = g.search("q", date(2021, 2, 1), date(2021, 3, 1))
    assert res.status == S.OK and res.attempts == 3 and res.items[0]["title"] == "Lipa rice up"
    assert res.items[0]["source_domain"] == "pna.gov.ph"
    assert sleeps[:2] == [5.0, 15.0]


def test_rate_limits_back_off_and_are_reported_as_rate_limited_not_empty():
    sleeps = []
    g = S.GoogleNewsRSS(http_get=seq_get(R(503), R(429), R(503), R(429)), sleep=sleeps.append)
    res = g.search("q", date(2021, 2, 1), date(2021, 3, 1))
    assert res.status == S.RATE_LIMITED and res.attempts == 4 and sleeps == [60.0, 180.0, 600.0]
    gd = S.GDELTDoc(http_get=seq_get(*[R(200, b"Please limit requests to one every 5 seconds")] * 4), sleep=lambda s: None)
    assert gd.search("q", date(2021, 2, 1), date(2021, 3, 1)).status == S.RATE_LIMITED


def test_empty_feed_malformed_feed_and_permanent_errors():
    e = S.GoogleNewsRSS(http_get=seq_get(R(200, EMPTY_RSS)), sleep=lambda s: None).search("q", date(2021, 1, 1), date(2021, 2, 1))
    assert e.status == S.EMPTY
    m = S.GoogleNewsRSS(http_get=seq_get(R(200, b"<html>captcha</html>")), sleep=lambda s: None).search("q", date(2021, 1, 1), date(2021, 2, 1))
    assert m.status == S.MALFORMED
    f = S.GoogleNewsRSS(http_get=seq_get(R(400)), sleep=lambda s: None).search("q", date(2021, 1, 1), date(2021, 2, 1))
    assert f.status == S.FAILED and f.attempts == 1
    gm = S.GDELTDoc(http_get=seq_get(R(200, b"{not json")), sleep=lambda s: None).search("q", date(2021, 1, 1), date(2021, 2, 1))
    assert gm.status == S.MALFORMED


# ------------------------------------------------------------------ incremental collection of an active quarter
def test_active_quarter_incremental_collection_reopens_until_the_quarter_ends(tmp_path):
    story = [item("Batangas onions dear", "2026-11-03T02:00:00+00:00"), item("Batangas fish kill", "2026-12-20T02:00:00+00:00")]
    src = FakeSource(story)
    # not authorized: refused, nothing requested
    st0, c0 = collector(tmp_path / "x", src, au="2026-Q2", now=datetime(2026, 11, 10, tzinfo=UTC))
    assert c0.run("incremental", ["2026-Q4"], provinces=["Batangas"])["requests"] == 0
    # authorized (simulated future authorization): November window is OPEN, December not yet queried
    st, c1 = collector(tmp_path, src, au="2026-Q4", now=datetime(2026, 11, 10, tzinfo=UTC))
    c1.run("incremental", ["2026-Q4"], provinces=["Batangas"])
    assert [a["title"] for a in st.articles.values()] == ["Batangas onions dear"]
    assert any(w["status"] == "OPEN" for w in st.windows.values())
    st2 = NewsStore(tmp_path / "store")
    Collector(st2, [src], authorized_until="2026-Q4", now=datetime(2027, 1, 2, tzinfo=UTC), credible=lambda d: True,
              geocode=lambda t: None).run("incremental", ["2026-Q4"], provinces=["Batangas"])
    assert sorted(a["title"] for a in st2.articles.values()) == ["Batangas fish kill", "Batangas onions dear"]
    assert not any(w["status"] == "OPEN" for w in st2.windows.values())


# ------------------------------------------------------------------ scoring and FSSI
def _filled_store(tmp_path, n_bat=6, n_lag=2):
    items = [item(f"Batangas rice story {i}", f"2021-0{1 + i % 3}-1{i % 9}T03:00:00+00:00") for i in range(n_bat)]
    items += [item(f"Laguna food story {i}", "2021-05-10T03:00:00+00:00") for i in range(n_lag)]
    st, col = collector(tmp_path, FakeSource(items))
    col.run("backfill", ["2021-Q1", "2021-Q2", "2021-Q3"], provinces=["Batangas", "Laguna"])
    return st


def test_scoring_failure_is_recorded_not_replaced_by_a_keyword_score(tmp_path):
    from app.news.scoring import score_pending

    st = _filled_store(tmp_path)
    def flaky(title, summary):
        if "story 0" in title:
            raise RuntimeError("inference error")
        return {"status": "OK", "score": 0.5, "top_hypothesis": "T1", "all_scores": {"T1": 0.5}}
    r = score_pending(st, scorer=flaky, model_key="m1")
    assert r["failed"] == 2 and r["scored"] == 6
    rows = coverage_audit(st, ["2021-Q1", "2021-Q2"], model_key="m1")
    bat = [x for x in rows if x["province"] == "Batangas" and x["quarter"] == "2021-Q1"][0]
    assert bat["evidence_status"] == "SCORING_INCOMPLETE" and bat["coverage_status"] == "PARTIALLY_COVERED"
    r2 = score_pending(st, scorer=lambda t, s: {"status": "OK", "score": 0.5, "top_hypothesis": "T1", "all_scores": {}},
                       model_key="m1")
    assert r2["scored"] == 2 and r2["already_scored"] == 6          # only the failures are retried


def test_scoring_refuses_the_keyword_fallback(monkeypatch):
    import app.ml.nlp.classifier as C
    from app.news import scoring

    monkeypatch.setattr(C, "load_classifier", lambda: C._KeywordClassifier())
    with pytest.raises(scoring.ScoringUnavailable):
        scoring.xlmr_scorer()


def test_fssi_is_reproducible_missing_is_null_and_lags_follow_the_calendar(tmp_path):
    from app.news.fssi import build_fssi
    from app.news.scoring import score_pending

    st = _filled_store(tmp_path)
    score_pending(st, scorer=lambda t, s: {"status": "OK", "score": 0.6, "top_hypothesis": "T1", "all_scores": {}},
                  model_key="m1")
    a = build_fssi(st, ["2021-Q1", "2021-Q2", "2021-Q3"], model_key="m1")
    b = build_fssi(NewsStore(tmp_path / "store"), ["2021-Q1", "2021-Q2", "2021-Q3"], model_key="m1")
    assert a["summary"]["panel_sha256"] == b["summary"]["panel_sha256"]
    p = a["panel"].set_index(["province", "quarter"])
    assert p.loc[("Batangas", "2021-Q1"), "evidence_status"] == "SUFFICIENT"
    assert p.loc[("Laguna", "2021-Q2"), "evidence_status"] == "LIMITED_SIGNAL"
    assert p.loc[("Cavite", "2021-Q1"), "FSSI"] is None or p.loc[("Cavite", "2021-Q1"), "FSSI"] != p.loc[("Cavite", "2021-Q1"), "FSSI"]
    assert p.loc[("Cavite", "2021-Q1"), "evidence_status"] == "NO_USABLE_EVIDENCE"
    # Batangas has Q1, no Q2, Q3? lag1 of a quarter after a gap must be missing, not the older value
    lag = p.loc[("Batangas", "2021-Q3"), "FSSI_lag1"]
    assert lag is None or lag != lag
