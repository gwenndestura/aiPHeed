"""
Nationwide province-level news collection for E145, from Rappler's public WordPress REST archive.

Every surveyed province gets the same queries, so CALABARZON is not favoured. No survey outcome is read here.

    python -m app.e145.collect articles     # province phrases, full archive, paginated (resumable)

robots.txt is checked at start; 1.5 s between requests; only id, date, link, title and excerpt are requested. Raw text
stays local (data/e145/raw is gitignored: third-party text); the ledger and derived features are committed.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import quote

from app.e145 import RAW

HOST = "www.rappler.com"
UA = "Mozilla/5.0 (aiPHeed thesis research; food security forecasting; DA Region IV-A)"
DELAY = 1.5
FIRST = 2012
BEFORE = "2019-04-02T00:00:00"   # the last evaluated issue date is 2019-04-01 (lead 1, ENNS 2019); collect later years only if news passes
FIELDS = "id,date,link,title,excerpt"
# Names that also mean something else are anchored (same rule as FI6-N: "Quezon" alone is mostly Quezon City, "Rizal"
# mostly Jose Rizal). Decided from the names alone, before any outcome was read.
SPECIAL = {"quezon": ['"Quezon province"'], "rizal": ['"Rizal province"'], "mountain": ['"Mountain Province"'],
           "western samar": ['"in Samar"', '"Samar province"'], "north cotabato": ['"North Cotabato"'],
           "compostela valley": ['"Compostela Valley"', '"Davao de Oro"']}


def queries_for(key: str) -> list[str]:
    """Exact phrases. Rappler's search matches bare or single quoted words loosely (checked 2026-11-04: "Aklan" and
    Aklan rice both return the 10,000-hit cap, including articles that never mention Aklan), but multi-word quoted
    phrases exactly ("Quezon province" 619; "Aklan rice" 1). Every province therefore uses the same two phrases."""
    if key in SPECIAL:
        return SPECIAL[key]
    n = "Tawi-Tawi" if key == "tawi tawi" else key.title().replace(" Del ", " del ").replace(" De ", " de ")
    return [f'"in {n}"', f'"{n} province"']


def keys() -> list[str]:
    from app.e141 import panel as P
    return sorted(P.outcomes()["key"].unique())


def _get(url: str) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b""
    except Exception:
        return 0, {}, b""


def _fetch(url: str) -> tuple[int, dict, bytes]:
    for attempt in range(4):
        code, h, body = _get(url)
        if code in (200, 400):
            return code, h, body
        time.sleep(DELAY * 3 ** (attempt + 1))
    return code, h, body


def robots_ok() -> None:
    rp = urllib.robotparser.RobotFileParser()
    code, _, body = _get(f"https://{HOST}/robots.txt")
    if code == 200:
        rp.parse(body.decode("utf-8", "ignore").splitlines())
        if not rp.can_fetch("*", f"https://{HOST}/wp-json/wp/v2/posts?search=x"):
            raise SystemExit("robots.txt disallows the archive path")


def articles() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    done_path = RAW / "articles_done.txt"
    done = set(done_path.read_text().splitlines()) if done_path.exists() else set()
    with open(RAW / "articles.jsonl", "a", encoding="utf-8", newline="\n") as out, open(done_path, "a", newline="\n") as dn:
        for key in keys():
            for q in queries_for(key):
                tag = f"{key}|{q}"
                if tag in done:
                    continue
                page, status = 1, "ok"
                while True:
                    url = (f"https://{HOST}/wp-json/wp/v2/posts?search={quote(q)}&after={FIRST}-01-01T00:00:00"
                           f"&before={BEFORE}&per_page=100&page={page}&orderby=date&order=asc&_fields={FIELDS}")
                    code, h, body = _fetch(url)
                    if code == 400:          # past the last page
                        break
                    if code != 200:
                        status = f"HTTP{code}"
                        break
                    rows = json.loads(body)
                    for r in rows:
                        out.write(json.dumps({"key": key, "query": q, "id": r["id"], "date": r["date"], "link": r["link"],
                                              "title": r["title"]["rendered"], "excerpt": r["excerpt"]["rendered"]},
                                             ensure_ascii=False) + "\n")
                    time.sleep(DELAY)
                    if page >= int(h.get("X-WP-TotalPages", h.get("x-wp-totalpages", 1))) or not rows:
                        break
                    page += 1
                out.flush()
                if status == "ok":
                    dn.write(tag + "\n")
                    dn.flush()
                print(tag, status, page, h.get("x-wp-total", h.get("X-WP-Total")), flush=True)


if __name__ == "__main__":
    robots_ok()
    {"articles": articles}[sys.argv[1]]()
