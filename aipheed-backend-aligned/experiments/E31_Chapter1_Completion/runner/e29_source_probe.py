"""E29 source probe (NEWS_SOURCE_AND_TEXT_ACCESS.md). Records counts, lengths and date ranges only; never prints or
stores a title or text. Everything requested is inside 2021-01-01..2026-06-30.

  A. Google News RSS: E28 query vs `intitle:` variants (province name and/or food term in the title) for fixed
     in-window months; how many returned titles name a province (geocoder) and carry a food word (classifier's
     food-nexus guard), i.e. could enter the FSSI.
  B. Internet Archive (Wayback CDX, the project's existing wayback source): snapshots per year of the project's own
     publisher RSS feeds (FEED_URLS) up to 2026-06-30; one snapshot per probe year opened: items, share with a
     description, median description length, feed depth in days.
python -B runner/e29_source_probe.py  ->  runs/e29_source_probe.json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import date, datetime, timezone
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
from app.news.sources import GoogleNewsRSS  # noqa: E402

LIMIT = datetime(2026, 6, 30, 16, 0, tzinfo=timezone.utc)   # 2026-07-01 00:00 PHT
UA = {"User-Agent": "aiPHeed-thesis-research/1.0 (DLSU-D; non-commercial)"}


def g_probe():
    g = GoogleNewsRSS(delay=3.0)
    cases = {
        "e28_body_match": '"Batangas" (food OR rice OR prices OR hunger OR malnutrition OR inflation)',
        "intitle_province": 'intitle:Batangas (food OR rice OR prices OR hunger OR malnutrition OR inflation)',
        "intitle_both": 'intitle:Batangas intitle:(rice OR food OR prices OR palay OR bigas OR presyo OR fish OR farmers)',
        "intitle_both_fil": 'intitle:Batangas intitle:(bigas OR presyo OR pagkain OR gutom OR magsasaka OR isda)',
    }
    months = [(date(2021, 2, 1), date(2021, 3, 1)), (date(2023, 7, 1), date(2023, 8, 1)), (date(2025, 11, 1), date(2025, 12, 1))]
    out = []
    for name, q in cases.items():
        for a, b in months:
            r = g.search(q, a, b)
            n_after = n_geo = n_food = n_both = 0
            for it in r.items:
                try:
                    ts = parsedate_to_datetime(it["published_raw"])
                except Exception:
                    continue
                if ts >= LIMIT:
                    n_after += 1
                    continue
                geo = geocode_to_province(it["title"]) is not None
                food = has_food_nexus(clean_text(it["title"], ""))
                n_geo += geo
                n_food += food
                n_both += geo and food
            out.append({"query": name, "month": a.isoformat()[:7], "status": r.status, "n": r.n_raw,
                        "after_limit": n_after, "title_geocoded": n_geo, "title_food_word": n_food,
                        "fssi_eligible_titles": n_both})
    return out


def wb_probe():
    from app.ml.corpus.rss_fetcher import FEED_URLS

    res = []
    for url in FEED_URLS:
        cdx = ("http://web.archive.org/cdx/search/cdx?url=" + url + "&from=2021&to=20260630&output=json"
               "&fl=timestamp,statuscode&filter=statuscode:200&collapse=timestamp:8")
        try:
            r = requests.get(cdx, timeout=60, headers=UA)
            rows = r.json()[1:] if r.status_code == 200 and r.text.strip() else []
        except Exception as exc:
            res.append({"feed": url, "error": type(exc).__name__})
            time.sleep(3)
            continue
        per_year = {}
        for ts, _ in rows:
            per_year[ts[:4]] = per_year.get(ts[:4], 0) + 1
        entry = {"feed": url, "daily_snapshots_by_year": per_year, "samples": []}
        for year in ("2021", "2024"):
            ts = next((t for t, _ in rows if t.startswith(year)), None)
            if not ts:
                continue
            time.sleep(3)
            try:
                s = requests.get(f"https://web.archive.org/web/{ts}id_/{url}", timeout=60, headers=UA)
                f = feedparser.parse(s.content)
            except Exception as exc:
                entry["samples"].append({"ts": ts, "error": type(exc).__name__})
                continue
            descs, dates = [], []
            for e in f.entries:
                d = (e.get("summary") or e.get("description") or "")
                descs.append(len(clean_text("", d)))
                try:
                    dates.append(parsedate_to_datetime(e.get("published")))
                except Exception:
                    pass
            dd = [d for d in dates if d and d < LIMIT]
            entry["samples"].append({"ts": ts, "http": s.status_code, "items": len(f.entries),
                                     "with_description": sum(1 for x in descs if x > 40),
                                     "median_description_chars": statistics.median(descs) if descs else None,
                                     "feed_depth_days": (round((max(dd) - min(dd)).total_seconds() / 86400, 2)
                                                         if len(dd) > 1 else None)})
        res.append(entry)
        time.sleep(3)
    return res


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = {"run_at": datetime.now(timezone.utc).isoformat()}
    if which in ("all", "gnews"):
        out["google_news_intitle"] = g_probe()
    if which in ("all", "wayback"):
        out["wayback_feeds"] = wb_probe()
    p = EXP / "runs" / f"e29_source_probe_{which}.json"
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
