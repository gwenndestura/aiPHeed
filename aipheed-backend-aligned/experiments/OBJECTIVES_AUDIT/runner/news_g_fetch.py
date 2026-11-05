"""Fetch CALABARZON food headlines from the GDELT DOC 2.0 API, 2017-01-01..2026-09-30, one source for both eras.

Same query as OLD_NEWS/FEASIBILITY.md section 2. Weekly windows (<= 250 records each; a window that hits 250 is
split into days). One request every 6 s (GDELT asks for >= 5 s). Every raw response is saved as received
(../news_g/raw/<start>_<end>.json, git-ignored) and the run is resumable. Titles, URLs, domains and GDELT seen-dates
only; no article page is downloaded.

    python news_g_fetch.py          # -> ../news_g/raw/*.json, ../news_g/headlines.csv, ../news_g/fetch_log.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "news_g"
RAW = HERE / "raw"
API = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERY = "(Batangas OR Cavite OR Laguna OR Rizal OR Calabarzon) (rice OR food OR hunger OR prices) sourcecountry:philippines"
START, END = datetime(2017, 1, 1), datetime(2026, 10, 1)
PAUSE = 15.0


def get(a: datetime, b: datetime) -> dict:
    f = RAW / f"{a:%Y%m%d%H}_{b:%Y%m%d%H}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except ValueError:                                    # a file cut off by a shutdown: fetch it again
            f.unlink()
    q = {"query": QUERY, "mode": "artlist", "maxrecords": "250", "format": "json", "sort": "datedesc",
         "startdatetime": f"{a:%Y%m%d%H%M%S}", "enddatetime": f"{b:%Y%m%d%H%M%S}"}
    url = API + "?" + urllib.parse.urlencode(q)
    for attempt in range(8):
        time.sleep(PAUSE if attempt == 0 else min(600, 30 * 2 ** attempt))   # back off on 429
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (aiPHeed thesis research; contact via repository)"}), timeout=90) as r:
                txt = r.read().decode("utf-8", "replace")
            d = json.loads(txt) if txt.strip().startswith("{") else None
            if d is None:
                if "limit requests" in txt:
                    continue
                d = {"articles": [], "_note": txt[:200]}
            d["_request"] = {"url": url, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            tmp = f.with_suffix(".tmp")                          # write, then rename: never a half-written file
            tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            tmp.replace(f)
            return d
        except Exception as e:  # noqa: BLE001
            err = str(e)
    raise RuntimeError(f"failed {a}..{b}: {err}")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows, log, a = [], [], START
    while a < END:
        b = min(a + timedelta(days=7), END)
        parts = [(a, b)]
        d = get(a, b)
        if len(d.get("articles", [])) >= 250:                    # saturated: split the week into days
            parts = [(a + timedelta(days=i), min(a + timedelta(days=i + 1), b)) for i in range((b - a).days)]
        for x, y in parts:
            dd = d if (x, y) == (a, b) else get(x, y)
            n = len(dd.get("articles", []))
            log.append({"start": f"{x:%Y-%m-%d}", "end": f"{y:%Y-%m-%d}", "n": n, "saturated": n >= 250})
            for r in dd.get("articles", []):
                rows.append({"seendate": r.get("seendate"), "title": r.get("title"), "url": r.get("url"),
                             "domain": r.get("domain"), "language": r.get("language"), "sourcecountry": r.get("sourcecountry")})
        if len(log) % 25 == 0:
            print(f"{a:%Y-%m-%d}: {len(rows)} records so far", flush=True)
        a = b
    H = pd.DataFrame(rows).drop_duplicates("url")
    H["published_utc"] = pd.to_datetime(H["seendate"], format="%Y%m%dT%H%M%SZ", utc=True)
    H.sort_values("published_utc").to_csv(HERE / "headlines.csv", index=False)
    (HERE / "fetch_log.json").write_text(json.dumps({"query": QUERY, "windows": log, "records_unique_url": len(H),
                                                     "saturated_windows": sum(w["saturated"] for w in log)}, indent=1),
                                         encoding="utf-8")
    print(f"done: {len(H)} unique headlines, {sum(w['saturated'] for w in log)} saturated windows")


if __name__ == "__main__":
    main()
