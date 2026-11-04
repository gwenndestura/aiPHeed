"""
app/cb6_auto/news.py
--------------------
News for the C-B6 input z_N1R. N1R(t) is the mean XLM-RoBERTa intensity of the admitted articles of quarter t published
before O(t), and is missing below 5 scored articles (iv2_lib.n1r, on pipeline_v3's classifier, de-duplication and score key).
New articles go to their own store under the persistent folder; the historical stores are read only.

Google News RSS is collected every day. XLM-RoBERTa scoring runs only with AIPHEED_CB6_NEWS_SCORING=1: a Render starter
instance cannot hold the model. Without scores N1R stays missing and the forecast records news as stale; nothing is imputed.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.cb6_auto.config import news_dir, news_scoring_enabled
from app.cb6_auto.features import qs

MIN_SCORED = 5
# A new quarter's N1R must rest on the whole quarter: every historical quarter has all its province articles scored, and since
# 2024 its newest article within 12 days of the issue date. Scores from the first weeks alone would look valid and are not.
MIN_PROVINCE_COVERAGE = 0.95
MAX_DAYS_NEWEST_ARTICLE = 30
DAILY_REQUEST_BUDGET = 150


def _store():
    from app.news.store import NewsStore

    news_dir().mkdir(parents=True, exist_ok=True)
    return NewsStore(str(news_dir()))


def collect(now: datetime | None = None, max_requests: int = DAILY_REQUEST_BUDGET, sources: list | None = None) -> dict:
    """The current quarter, plus the just-closed one for 45 days (search indexes add articles late)."""
    from app.news.collector import Collector
    from app.news.policy import credible_fn
    from app.news.sources import GoogleNewsRSS
    from app.news.timeutil import PH, quarter_of_date, quarter_start

    now = now or datetime.now(timezone.utc)
    today = now.astimezone(PH).date()
    cur = quarter_of_date(today)
    quarters = [cur]
    if (today - quarter_start(cur)).days < 45:
        y, n = int(cur[:4]), int(cur[-1])
        quarters.insert(0, f"{y - 1}-Q4" if n == 1 else f"{y}-Q{n - 1}")
    col = Collector(_store(), sources or [GoogleNewsRSS()], authorized_until=cur, now=now, credible=credible_fn(None))
    return col.run("incremental", quarters, max_requests=max_requests)


def _auto_articles(store) -> list[dict]:
    """The new store's articles in pipeline_v3's corpus shape (same classifier)."""
    from app.ml.corpus.geocoder import geocode_to_province
    from app.news.classifier_v2 import classify
    from app.news.pipeline_v3 import PROVINCE_CODES

    out = []
    for a in store.articles.values():
        c = classify(a.get("title") or "", geocode_to_province)
        out.append({"article_key": a["article_key"], "title": (a.get("title") or "").strip(),
                    "outlet": a.get("source_domain") or "", "published_ph": a["published_ph"], "ph_date": a["ph_date"][:10],
                    "quarter": a["quarter"],
                    "province_code": a.get("geo_province_code") if a.get("geo_province_code") in PROVINCE_CODES else None,
                    "link": a.get("link") or "", "store": "news_auto", "first_seen_at": a.get("first_seen_at"),
                    "relevant": c["relevant"], "trigger": c["trigger"], "rule": c["rule"]})
    return out


def _admitted(store) -> list[dict]:
    from app.news import pipeline_v3 as P

    seen, rows = set(), []
    for a in list(P.corpus()) + _auto_articles(store):      # first store wins on a duplicate key, as pipeline_v3
        if a["article_key"] not in seen:
            seen.add(a["article_key"])
            rows.append(a)
    kept, _ = P.dedupe([a for a in rows if a["relevant"] == 1])
    return kept


def score_new(store=None) -> dict:
    """Score admitted province-attributed articles of the new store (same scorer and key as the historical scores)."""
    from app.news import pipeline_v3 as P
    from app.news.fssi_v2 import score_admitted

    store = store or _store()
    have = P.intensities()
    keys = [a["article_key"] for a in _admitted(store)
            if a["store"] == "news_auto" and a["province_code"] and a["article_key"] not in have]
    return score_admitted(store, keys)


def _scores(store) -> dict:
    from app.news import pipeline_v3 as P

    out = dict(P.intensities())
    keys = P.intensity_keys()
    for r in store.read("scores"):
        if r.get("model_key") in keys and r.get("status") == "OK":
            out[r["article_key"]] = float(r["score"])
    return out


def n1r_asof(t: int, store=None, require_complete: bool = True) -> dict:
    """N1R(t) with its evidence: admitted articles of quarter t published before O(t) that have a score. With
    require_complete, a quarter whose collection or scoring is unfinished gives a missing value and says why."""
    from app.news import pipeline_v3 as P

    store = store or _store()
    q, O = qs(t), P.origin(t)
    arts = [a for a in _admitted(store) if a["quarter"] == q and P._ph(a) < O]
    sc = _scores(store)
    vals = [sc[a["article_key"]] for a in arts if a["article_key"] in sc]
    prov = [a for a in arts if a["province_code"]]
    coverage = sum(a["article_key"] in sc for a in prov) / len(prov) if prov else 0.0
    newest = max((P._ph(a) for a in arts), default=None)
    gap = (O - newest).days if newest else None
    value = float(sum(vals) / len(vals)) if len(vals) >= MIN_SCORED else math.nan
    why = None
    if require_complete and not math.isnan(value):
        if coverage < MIN_PROVINCE_COVERAGE:
            why = f"only {coverage:.0%} of the province articles are scored"
        elif gap is None or gap > MAX_DAYS_NEWEST_ARTICLE:
            why = f"the newest article is {gap} days before the issue date"
        if why:
            value = math.nan
    return {"quarter": q, "admitted": len(arts), "scored": len(vals), "province_coverage": round(coverage, 3),
            "days_newest_before_issue": gap, "n1r": value, "incomplete": why, "scoring_enabled": news_scoring_enabled()}
