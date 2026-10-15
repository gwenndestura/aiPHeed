"""E29: what would article lead text add to the FSSI? (NEWS_SOURCE_AND_TEXT_ACCESS.md §3)

Source: archived copies of the project's OWN publisher RSS feeds (rss_fetcher.FEED_URLS) in the Internet Archive
(Wayback CDX; the project's existing wayback source), snapshots 2025-07-01..2026-06-30 only (authorized period). The
same items are evaluated twice with the project's unchanged geocoder and XLM-RoBERTa classifier:
    premise A = title only (what Google News RSS gives; the E28 FSSI)
    premise B = title + feed description (the methodology's "title and summary", Section 3.3.2.1)
Output: counts of province-attributed, food-nexus and >= 0.30 items under A and B. This measures the value of lead
text; it does not change the E28 FSSI (mixing premises across quarters would break the series).
python -B runner/e29_lead_text_impact.py  ->  runs/e29_lead_text_impact.json, runs/wayback_leads/items.jsonl
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard29  # noqa: E402

guard29.install()
EXP = guard29.EXP
sys.path.insert(0, str(EXP / "backend_dev"))
import feedparser  # noqa: E402
import requests  # noqa: E402

from app.ml.corpus.geocoder import geocode_to_province  # noqa: E402
from app.ml.nlp.classifier import clean_text, has_food_nexus  # noqa: E402

START = datetime(2025, 6, 30, 16, 0, tzinfo=timezone.utc)   # 2025-07-01 00:00 PHT
LIMIT = datetime(2026, 6, 30, 16, 0, tzinfo=timezone.utc)   # 2026-07-01 00:00 PHT
UA = {"User-Agent": "aiPHeed-thesis-research/1.0 (DLSU-D; non-commercial)"}
FEEDS = ["https://business.inquirer.net/feed", "https://cebudailynews.inquirer.net/feed",
         "https://www.philstar.com/rss/headlines", "https://www.philstar.com/rss/business",
         "https://www.manilatimes.net/news/feed", "https://www.rappler.com/feed/", "https://ptvnews.ph/feed/"]
PER_FEED = 60
OUT = EXP / "runs" / "wayback_leads"


def snapshots(url):
    cdx = (f"http://web.archive.org/cdx/search/cdx?url={url}&from=20250701&to=20260630&output=json"
           "&fl=timestamp&filter=statuscode:200&collapse=timestamp:8")
    r = requests.get(cdx, timeout=90, headers=UA)
    ts = [x[0] for x in r.json()[1:]] if r.status_code == 200 and r.text.strip() else []
    if len(ts) > PER_FEED:                       # evenly spaced sample, deterministic
        step = len(ts) / PER_FEED
        ts = [ts[int(i * step)] for i in range(PER_FEED)]
    return ts


def collect():
    OUT.mkdir(parents=True, exist_ok=True)
    seen, items, log = set(), [], []
    for url in FEEDS:
        try:
            tss = snapshots(url)
        except Exception as exc:
            log.append({"feed": url, "error": type(exc).__name__})
            continue
        for ts in tss:
            time.sleep(2.5)
            try:
                r = requests.get(f"https://web.archive.org/web/{ts}id_/{url}", timeout=90, headers=UA)
                f = feedparser.parse(r.content)
            except Exception as exc:
                log.append({"feed": url, "ts": ts, "error": type(exc).__name__})
                continue
            log.append({"feed": url, "ts": ts, "http": r.status_code, "items": len(f.entries)})
            for e in f.entries:
                try:
                    pub = parsedate_to_datetime(e.get("published")).astimezone(timezone.utc)
                except Exception:
                    continue
                if not (START <= pub < LIMIT):
                    continue                     # outside the probe window or after the authorized limit
                title = (e.get("title") or "").strip()
                key = hashlib.sha256(f"{url}|{title}|{pub.date()}".encode()).hexdigest()
                if not title or key in seen:
                    continue
                seen.add(key)
                items.append({"key": key, "feed": url, "snapshot": ts, "published_utc": pub.isoformat(),
                              "title": title, "description": clean_text("", e.get("summary") or e.get("description") or "")})
    (OUT / "items.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n", encoding="utf-8")
    (OUT / "fetch_log.jsonl").write_text("\n".join(json.dumps(x) for x in log) + "\n", encoding="utf-8")
    return items, log


def main():
    items, log = collect()
    from app.news.scoring import xlmr_scorer

    sc = xlmr_scorer()
    res = {"items": len(items), "snapshots_fetched": sum(1 for x in log if "items" in x),
           "fetch_errors": sum(1 for x in log if "error" in x)}
    A = {"geo": 0, "geo_food": 0, "geo_fssi": 0}
    B = {"geo": 0, "geo_food": 0, "geo_fssi": 0}
    scored = []
    for it in items:
        ga = geocode_to_province(it["title"])
        gb = geocode_to_province(it["title"] + ". " + it["description"])
        A["geo"] += ga is not None
        B["geo"] += gb is not None
        if ga:
            fa = has_food_nexus(clean_text(it["title"], ""))
            A["geo_food"] += fa
            if fa:
                s = sc(it["title"], "")
                A["geo_fssi"] += s["score"] >= 0.30
        if gb:
            fb = has_food_nexus(clean_text(it["title"], it["description"]))
            B["geo_food"] += fb
            if fb:
                s = sc(it["title"], it["description"])
                B["geo_fssi"] += s["score"] >= 0.30
                scored.append({"key": it["key"], "score_title_plus_lead": s["score"], "province": gb})
    res["title_only"] = A
    res["title_plus_lead"] = B
    res["ratio_fssi_eligible_B_over_A"] = (B["geo_fssi"] / A["geo_fssi"]) if A["geo_fssi"] else None
    res["note"] = ("same items, same geocoder and classifier; only the premise differs. Sample: up to 60 evenly "
                   "spaced daily snapshots per feed, 2025-07..2026-06; items outside the window are dropped.")
    (EXP / "runs" / "e29_lead_text_impact.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
