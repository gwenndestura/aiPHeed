"""E28 live-source probe (Phase B). Asks each supported news source for an IN-WINDOW period and reports only
HTTP status, item counts and the publication-date range of the items returned. It never prints or stores a title,
link or summary, so a source that ignores the date filter cannot expose post-June-2026 text: such items are only
counted as 'after_authorized_limit'.

Run from E28:  python -B runner/news_live_probe.py   ->  runs/news_live_probe.json
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
import feedparser  # noqa: E402
import requests  # noqa: E402

LIMIT = datetime(2026, 7, 1, tzinfo=timezone.utc) - __import__("datetime").timedelta(hours=8)  # 2026-07-01 00:00 PHT
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def summarize(dates, lo, hi):
    ok = [d for d in dates if d is not None]
    after = sum(1 for d in ok if d >= LIMIT)
    inwin = [d for d in ok if lo <= d < hi]
    return {"n_items": len(dates), "n_undated": len(dates) - len(ok), "n_after_authorized_limit": after,
            "n_inside_requested_window": len(inwin), "n_outside_window_but_authorized": len(ok) - after - len(inwin),
            "min_date_inside": min(inwin).isoformat() if inwin else None,
            "max_date_inside": max(inwin).isoformat() if inwin else None}


def gnews(query, after, before):
    url = (f"https://news.google.com/rss/search?q={quote(query)}+after:{after}+before:{before}"
           f"&hl=en-PH&gl=PH&ceid=PH:en")
    t0 = datetime.now(timezone.utc)
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    out = {"source": "google_news_rss", "query": query, "after": after, "before": before,
           "requested_at_utc": t0.isoformat(), "http_status": r.status_code}
    if r.status_code == 200:
        f = feedparser.parse(r.content)
        dates = []
        for e in f.entries:
            try:
                dates.append(parsedate_to_datetime(e.get("published")).astimezone(timezone.utc))
            except Exception:
                dates.append(None)
        lo = datetime.fromisoformat(after).replace(tzinfo=timezone.utc)
        hi = datetime.fromisoformat(before).replace(tzinfo=timezone.utc)
        out.update(summarize(dates, lo, hi))
    return out


def gdelt(query, start, end):
    url = (f"https://api.gdeltproject.org/api/v2/doc/doc?query={quote(query)}&mode=ArtList&maxrecords=250"
           f"&startdatetime={start}&enddatetime={end}&format=json")
    t0 = datetime.now(timezone.utc)
    out = {"source": "gdelt_doc_2", "query": query, "start": start, "end": end, "requested_at_utc": t0.isoformat()}
    try:
        r = requests.get(url, timeout=60)
    except Exception as exc:
        out.update({"http_status": None, "error": type(exc).__name__})
        return out
    out["http_status"] = r.status_code
    body = r.text
    try:
        arts = r.json().get("articles") or []
        dates = []
        for a in arts:
            try:
                dates.append(datetime.strptime(a.get("seendate", "")[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc))
            except Exception:
                dates.append(None)
        lo = datetime.strptime(start, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        hi = datetime.strptime(end, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        out.update(summarize(dates, lo, hi))
    except Exception:
        # Non-JSON reply: GDELT answers out-of-range or malformed requests with a plain-text message. Record only its
        # length and whether it names the time span, never its text (it carries no article content in any case).
        out.update({"non_json_reply_chars": len(body),
                    "reply_mentions_timespan": any(k in body.lower() for k in ("timespan", "date", "months"))})
    return out


def main():
    res = []
    probes = [("gnews", ("Batangas rice prices", "2021-01-01", "2021-02-01")),
              ("gnews", ("Quezon bigas presyo", "2021-04-01", "2021-05-01")),
              ("gnews", ("Laguna food prices", "2026-04-01", "2026-05-01")),
              ("gnews", ("Cavite food OR rice OR hunger", "2023-07-01", "2023-08-01")),
              ("gdelt", ("Batangas rice", "20210101000000", "20210201000000")),
              ("gdelt", ("Laguna food", "20260401000000", "20260501000000"))]
    tag = ""
    if len(sys.argv) > 2:          # python news_live_probe.py <tag> '<json list of [kind, [args]]>' [delay_s]
        tag = "_" + sys.argv[1]
        probes = [(k, tuple(a)) for k, a in json.loads(sys.argv[2])]
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    for kind, args in probes:
        try:
            res.append(gnews(*args) if kind == "gnews" else gdelt(*args))
        except Exception as exc:
            res.append({"source": kind, "args": list(args), "error": type(exc).__name__})
        time.sleep(delay)
    out = HERE.parent / "runs" / f"news_live_probe{tag}.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
