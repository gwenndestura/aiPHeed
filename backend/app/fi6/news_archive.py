"""Source-consistent historical news archive (FI6-N), collected from publishers' public WordPress REST archives.

Why: the 2021+ Google News corpus cannot inform a model evaluated on 2010-2026 (no news before 2021; search-engine
retrospective sampling makes collected volume grow with time). Publisher archives are complete, date-stamped and
the same for every year, so a 2012 quarter and a 2025 quarter are collected the same way.

    python -m app.fi6.news_archive collect [--sites rappler,bulatlat]   # resumable; ledger.csv records every request
    python -m app.fi6.news_archive status

Rules: robots.txt is checked at run time (sites that disallow the API path are skipped); each site's crawl-delay
(or 1.5 s) is respected; only id, date (publication, site local = PHT), modified, link, title and excerpt are
requested. Retrieval time is stored separately and never used as a publication date. Raw responses stay local
(data/fi6/news_archive/raw is gitignored: third-party text); the ledger and derived features are committed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from app.fi6.paths import FI6

ARCHIVE = FI6 / "news_archive"
RAW = ARCHIVE / "raw"
LEDGER = ARCHIVE / "ledger.csv"
UA = "Mozilla/5.0 (aiPHeed thesis research; food security forecasting; DA Region IV-A)"
LAST_DAY = "2026-11-01T00:00:00"          # collect publications up to 2026-10-31

SITES = {   # key: (host, first year, minimum delay s, source type)
    "rappler": ("www.rappler.com", 2012, 1.5, "national news"),
    "bulatlat": ("www.bulatlat.com", 2008, 10.0, "alternative press"),
    "verafiles": ("verafiles.org", 2008, 1.5, "investigative / fact-check"),
    "newsbytes": ("newsbytes.ph", 2012, 1.5, "national news"),
    "pinoyweekly": ("pinoyweekly.org", 2008, 5.0, "alternative press"),
    "pcij": ("pcij.org", 2008, 1.5, "investigative"),
}
# WordPress search ANDs bare words anywhere in the post; quoted phrases match exactly (checked 2026-11-02: Rappler
# 2015 "Quezon province" 6,675 unquoted vs 27 quoted). Quezon and Rizal are anchored through distinctive towns
# because "Quezon"/"Rizal" alone mostly mean Quezon City or Jose Rizal.
ANCHORS = ["Batangas", "Cavite", "Laguna", '"Quezon province"', '"Rizal province"', "CALABARZON", '"Southern Tagalog"',
           "Lucena", "Tayabas", "Sariaya", "Infanta", "Gumaca", "Mauban", "Antipolo", "Cainta", "Calamba",
           '"Los Banos"', "Lipa", "Dasmarinas", "Bacoor", "Imus"]
NATIONAL = ["OFW", "remittances", "repatriation", '"deployment ban"', '"rice price"', '"rice prices"', '"rice shortage"',
            '"food prices"', "layoffs", "retrenchment", '"El Nino"', '"crop damage"', '"agricultural damage"', "hunger",
            "malnutrition", "gutom", "bigas"]
QUERIES = [("anchor", q) for q in ANCHORS] + [("national", q) for q in NATIONAL]
FIELDS = "id,date,modified,link,title,excerpt"
_lock = threading.Lock()


def _curl(url: str) -> tuple[int, dict, bytes]:
    p = subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", UA, "-D", "-", url], capture_output=True)
    raw = p.stdout
    # split the last header block from the body
    head, _, body = raw.partition(b"\r\n\r\n")
    while body.startswith(b"HTTP/"):
        head, _, body = body.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    try:
        code = int(lines[0].split()[1])
    except Exception:
        code = 0
    hdr = {l.split(":", 1)[0].strip().lower(): l.split(":", 1)[1].strip() for l in lines[1:] if ":" in l}
    return code, hdr, body


def allowed(host: str) -> tuple[bool, float]:
    rp = urllib.robotparser.RobotFileParser()
    code, _, body = _curl(f"https://{host}/robots.txt")
    rp.parse(body.decode("utf-8", "replace").splitlines() if code == 200 else [])
    delay = rp.crawl_delay("*") or 0
    return rp.can_fetch("*", f"https://{host}/wp-json/wp/v2/posts?search=x"), float(delay)


def _ledger() -> pd.DataFrame:
    return pd.read_csv(LEDGER) if LEDGER.exists() else pd.DataFrame(columns=["site", "kind", "query", "year", "status"])


def _log(row: dict):
    with _lock:
        new = not LEDGER.exists()
        pd.DataFrame([row]).to_csv(LEDGER, mode="a", header=new, index=False, lineterminator="\n")


def collect_site(key: str, years: range | None = None, window: tuple[str, str] | None = None):
    """Collect `key` by calendar year, or (live refresh) only the publications in `window` = (after, before), ISO
    timestamps. A window is recorded in the ledger as 'YYYY-MM-DD..YYYY-MM-DD' and never repeated."""
    host, first, min_delay, stype = SITES[key]
    ok, cd = allowed(host)
    if not ok:
        _log({"site": key, "kind": "robots", "query": "", "year": "", "status": "ROBOTS_DISALLOWED", "total": 0,
              "pages": 0, "items": 0, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        return
    delay = max(min_delay, cd)
    done = _ledger()
    if window and len(done):                 # a live window is redone unless it completed
        done = done[done["status"] == "COMPLETE"]
    done = set(zip(done["site"], done["query"], done["year"].astype(str))) if len(done) else set()
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"{key}.jsonl"
    spans = [(f"{window[0][:10]}..{window[1][:10]}", window[0], window[1])] if window else         [(year, f"{year}-01-01T00:00:00", f"{year + 1}-01-01T00:00:00" if year < 2026 else LAST_DAY) for year in (years or range(first, 2027))]
    fails = 0
    for year, after, before in spans:
        for kind, q in QUERIES:
            if (key, q, str(year)) in done:
                continue
            if window and fails >= 3:            # live refresh: a site failing 3 queries in a row is skipped until the next run
                _log({"site": key, "kind": kind, "query": q, "year": year, "status": "SKIPPED_SITE_FAILING", "total": 0, "pages": 0,
                      "items": 0, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
                continue
            page, pages, total, items, status = 1, 1, 0, 0, "COMPLETE"
            while page <= pages:
                url = (f"https://{host}/wp-json/wp/v2/posts?search={quote(q)}&after={after}&before={before}"
                       f"&per_page=100&page={page}&orderby=date&order=asc&_fields={FIELDS}")
                for attempt in range(4):
                    code, hdr, body = _curl(url)
                    if code == 200:
                        break
                    if code == 400 and page > 1:        # past the last page
                        break
                    time.sleep(delay * (3 ** attempt))
                if code != 200:
                    status = f"HTTP_{code}" if not (code == 400 and page > 1) else status
                    break
                try:
                    rows = json.loads(body.decode("utf-8-sig"))
                except Exception:
                    status = "MALFORMED"
                    break
                if page == 1:
                    total = int(hdr.get("x-wp-total", len(rows)))
                    pages = int(hdr.get("x-wp-totalpages", 1))
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                with _lock, open(out, "a", encoding="utf-8") as fh:
                    for r in rows:
                        fh.write(json.dumps({"site": key, "source_type": stype, "query_kind": kind, "query": q,
                                             "wp_id": r.get("id"), "date": r.get("date"), "modified": r.get("modified"),
                                             "link": r.get("link"), "title": (r.get("title") or {}).get("rendered", ""),
                                             "excerpt": (r.get("excerpt") or {}).get("rendered", ""),
                                             "retrieved_utc": now}, ensure_ascii=False) + "\n")
                items += len(rows)
                page += 1
                time.sleep(delay)
            fails = 0 if status == "COMPLETE" else fails + 1
            _log({"site": key, "kind": kind, "query": q, "year": year, "status": status, "total": total, "pages": pages,
                  "items": items, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def collect(sites: list[str], window: tuple[str, str] | None = None):
    th = [threading.Thread(target=collect_site, args=(s, None, window), daemon=True) for s in sites]
    for t in th:
        t.start()
    for t in th:
        t.join()


def status() -> pd.DataFrame:
    l = _ledger()
    return l.groupby(["site", "status"]).agg(requests=("query", "count"), items=("items", "sum")).reset_index()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "status"])
    ap.add_argument("--sites", default=",".join(SITES))
    a = ap.parse_args()
    if a.cmd == "collect":
        collect(a.sites.split(","))
    print(status().to_string())
