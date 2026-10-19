"""
tests/integration/test_e64_news_pipeline.py
-------------------------------------------
E64 (Objective 1): the improved news pipeline (app/news/pipeline_v3.py) that feeds the e64 candidate and its dashboard
feed. Checks that
  * classifier v2 is byte-identical (LF-normalised) to its E60 freeze;
  * every corpus article is inside the study window, unique, and in the quarter of its Philippine-time date;
  * features at origin t use only articles of quarter t published before the issue date (a later article changes nothing);
  * syndicated copies do not inflate the signal;
  * missing news is never read as "no stress": FSSI is None without evidence and the status says so;
  * the features are computable with no news at all;
  * D-E64-1: the scoring model key does not depend on line endings, and FSSI-v2 rebuilds byte-identically;
  * D-E64-2: FSSI-v3 n, status and value describe the same articles;
  * the e64 feed lists classifier-v2 articles and never postdates a forecast's issue date; the E38 feed is unchanged.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.news import pipeline_v3 as P

client = TestClient(app)


def test_classifier_v2_matches_its_freeze():
    assert P.classifier_sha() == P.CLASSIFIER_V2_SHA256


def test_corpus_window_uniqueness_and_quarters():
    c = P.corpus()
    keys = [a["article_key"] for a in c]
    assert len(keys) == len(set(keys)) and len(c) > 9000
    for a in c:
        assert P.FIRST_DATE <= a["ph_date"] <= P.LAST_DATE
        y, m = int(a["ph_date"][:4]), int(a["ph_date"][5:7])
        assert a["quarter"] == f"{y}-Q{(m - 1) // 3 + 1}"
        assert a["province_code"] in (None, *P.PROVINCE_CODES)


def test_e60_store_dates_are_gmt_plus_8():
    path = P.DATA / "news_e60" / "articles.jsonl"
    if not path.exists():
        pytest.skip("E60 store not present")
    for line in path.read_text(encoding="utf-8").splitlines()[:500]:
        a = json.loads(line)
        raw = datetime.strptime(a["published_raw"], "%a, %d %b %Y %H:%M:%S GMT")
        assert (raw + timedelta(hours=8)).strftime("%Y-%m-%d") == a["ph_date"]


@pytest.mark.parametrize("t", [P.qi("2024-Q1"), P.qi("2025-Q3"), P.qi("2026-Q3")])
def test_features_use_only_articles_before_the_issue_date(t):
    O = P.origin(t)
    for a in P.asof(t):
        assert a["quarter"] == P.qs(t) and P._ph(a) < O
    before = P.n3_features(t)
    later = dict(P.admitted()[0])
    later.update({"article_key": "test-after-issue", "published_ph": (O + timedelta(hours=1)).isoformat(),
                  "ph_date": O.strftime("%Y-%m-%d"), "quarter": P.qs(t), "province_code": P.PROVINCE_CODES[0],
                  "trigger": "market", "title": "test article after the issue date"})
    orig = P.admitted
    try:
        P.admitted = lambda: tuple(list(orig()) + [later])
        after = P.n3_features(t)
    finally:
        P.admitted = orig
    strip = lambda rows: [{k: v for k, v in r.items() if k not in ("article_keys",)} for r in rows]  # noqa: E731
    assert json.dumps(strip(before), default=str) == json.dumps(strip(after), default=str)


def test_syndicated_copies_do_not_inflate_the_signal():
    a = {"article_key": "k1", "title": "Fish kill hits Taal Lake - Inquirer", "published_ph": "2025-05-01T08:00:00",
         "trigger": "fish_kill"}
    b = {**a, "article_key": "k2", "title": "Fish kill hits Taal Lake - Philstar", "published_ph": "2025-05-02T09:00:00"}
    c = {**a, "article_key": "k3", "published_ph": "2025-05-20T09:00:00"}
    kept, dropped = P.dedupe([a, b, c])
    assert [x["article_key"] for x in kept] == ["k1", "k3"] and dropped == {"k2": "k1"}


def test_missing_news_is_not_read_as_no_stress():
    for t in range(P.qi("2021-Q3"), P.qi("2026-Q3") + 1):
        for r in P.n3_features(t):
            if r["n_admitted"] == 0:
                assert r["fssi_status"] == "NO_USABLE_EVIDENCE" and math.isnan(r["n3_fssi"])
            else:
                assert r["fssi_status"] in ("SUFFICIENT", "LIMITED_SIGNAL") and not math.isnan(r["n3_fssi"])


def test_features_without_any_news(monkeypatch):
    monkeypatch.setattr(P, "admitted", lambda: tuple())
    rows = P.n3_features(P.qi("2026-Q3"))
    assert len(rows) == 5
    for r in rows:
        assert r["n_admitted"] == 0 and r["n3_cov"] == 0.0 and math.isnan(r["n3_fssi"])


def test_fssi_v3_counts_value_and_status_describe_the_same_articles():
    t = P.qi("2024-Q4")
    arts = P.asof(t)
    for p in P.PROVINCE_CODES:
        f = P.fssi_v3(p, t, arts)
        n = sum(1 for a in arts if a["province_code"] == p)
        assert f["n"] == n
        if n:
            vals = [P.intensities()[a["article_key"]] for a in arts if a["province_code"] == p]
            assert f["mean_intensity"] == pytest.approx(sum(vals) / n, abs=1e-6)


def test_model_key_does_not_depend_on_line_endings():
    import app.ml.nlp.classifier as C
    from app.news.scoring import current_model_key

    key = current_model_key()
    src = Path(C.__file__).read_bytes().replace(b"\r\n", b"\n")
    import hashlib
    assert key.endswith("|clf:" + hashlib.sha256(src).hexdigest()[:16])


def test_fssi_v2_rebuilds_byte_identically():
    from app.news.fssi_v2 import build_fssi_v2
    from app.news.store import NewsStore

    root = P.DATA / "news_e31"
    man = root / "fssi_v2_panel_manifest.json"
    if not man.exists():
        pytest.skip("FSSI-v2 panel not present")
    qs = [f"{y}-Q{q}" for y in range(2021, 2027) for q in range(1, 5)]
    out = build_fssi_v2(NewsStore(root), qs, write=False)
    assert out["manifest"]["panel_sha256"] == json.loads(man.read_text())["panel_sha256"]


def test_e64_feed_lists_classifier_v2_articles_before_the_issue_date(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e64")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")
    from app.ml.inference import e41_lead2 as L2
    try:
        L2.record()
    except L2.RecordError:
        pytest.skip("no e64 record")
    for q in L2.candidate_quarters():
        rows = L2.rows_for(q)
        if rows[0]["estimate_kind"] not in ("forecast", "earlier_forecast"):
            continue
        a = client.get(f"/api/v1/news?scope=province&id=laguna&quarter={q}&pageSize=50").json()
        assert all(x["relevanceStatus"] == "classifier_v2" for x in a["data"])
        assert all(x["date"] < rows[0]["origin"] for x in a["data"])
        assert "classifier v2" in a["feedNote"]


def test_e38_feed_is_unchanged(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")
    a = client.get("/api/v1/news?scope=province&id=laguna&quarter=2026-Q3").json()
    assert all(x["relevanceStatus"] in ("validated", "trigger_match") for x in a["data"])
