"""
Extend the E145 province news panel for E147: Rappler from April 2019 to the 2021 issue date, and three further public archives for
the whole window, using the E145 exact phrases. No survey outcome is read. robots.txt is checked per site; 1.5 s between requests.

    python -m app.e147.collect_news     -> data/e147/raw/articles_more.jsonl, news_collect_log.txt
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import quote

from app.e145.collect import keys, queries_for
from app.e147 import RAW

UA = "Mozilla/5.0 (aiPHeed thesis research; food security forecasting; DA Region IV-A)"
DELAY = 1.5
BEFORE = "2021-07-02T00:00:00"         # the latest evaluated issue date for 2021-Q3 is lead 1, 2021-04-01; lead 0 is never used
SITES = {"rappler": ("www.rappler.com", "2019-04-02T00:00:00"), "newsbytes": ("newsbytes.ph", "2012-01-01T00:00:00"),
         "verafiles": ("verafiles.org", "2012-01-01T00:00:00"), "pcij": ("pcij.org", "2012-01-01T00:00:00")}
FIELDS = "id,date,link,title,excerpt"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b""
    except Exception:
        return 0, {}, b""


def allowed(host):
    code, _, body = _get(f"https://{host}/robots.txt")
    if code != 200:
        return True
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(body.decode("utf-8", "ignore").splitlines())
    return rp.can_fetch("*", f"https://{host}/wp-json/wp/v2/posts?search=x")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    done_p = RAW / "news_done.txt"
    done = set(done_p.read_text().splitlines()) if done_p.exists() else set()
    with open(RAW / "articles_more.jsonl", "a", encoding="utf-8", newline="\n") as out, open(done_p, "a", newline="\n") as dn:
        for site, (host, after) in SITES.items():
            if not allowed(host):
                print(site, "ROBOTS_DISALLOWED", flush=True)
                continue
            for key in keys():
                for q in queries_for(key):
                    tag = f"{site}|{key}|{q}"
                    if tag in done:
                        continue
                    page, status = 1, "ok"
                    while True:
                        code, h, body = _get(f"https://{host}/wp-json/wp/v2/posts?search={quote(q)}&after={after}&before={BEFORE}&per_page=100&page={page}&orderby=date&order=asc&_fields={FIELDS}")
                        if code == 400:
                            break
                        if code != 200:
                            status = f"HTTP{code}"
                            break
                        rows = json.loads(body)
                        for r in rows:
                            out.write(json.dumps({"site": site, "key": key, "query": q, "id": f"{site}:{r['id']}", "date": r["date"], "link": r["link"],
                                                  "title": r["title"]["rendered"], "excerpt": r["excerpt"]["rendered"]}, ensure_ascii=False) + "\n")
                        time.sleep(DELAY)
                        if page >= int(h.get("X-WP-TotalPages", h.get("x-wp-totalpages", 1))) or not rows:
                            break
                        page += 1
                    out.flush()
                    if status == "ok":
                        dn.write(tag + "\n")
                        dn.flush()
                    print(tag, status, page, h.get("x-wp-total", h.get("X-WP-Total")), flush=True)
                    time.sleep(0.2)


if __name__ == "__main__":
    main()
