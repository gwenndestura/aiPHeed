"""
E144-P2 area news from Google News RSS (the project's existing source, app.news.sources.GoogleNewsRSS): for each SWS
area x FAO theme x calendar month (2021-01 .. 2026-09), every item returned for the area-and-theme query; a window at
the 100-item cap is split on a day boundary until it is not. Only credible domains are kept (app.news.collector policy).
Articles restating SWS results are excluded by the query (-"Social Weather" -SWS).

    python -m app.e144.gnews   -> data/e144/raw/gnews/items.jsonl, ledger.json
"""
from __future__ import annotations

import json
import time
from datetime import date

from app.e144 import RAW
from app.news.collector import _credible
from app.news.sources import GoogleNewsRSS
from app.news.timeutil import split_window

AREAS = {
    "metro_manila": '("Metro Manila" OR "Quezon City" OR Caloocan OR Taguig OR Pasig OR Makati OR Navotas)',
    "balance_luzon": '(CALABARZON OR "Central Luzon" OR Bicol OR Ilocos OR "Cagayan Valley" OR Pangasinan OR Batangas '
                     'OR Laguna OR Cavite OR Pampanga OR Bulacan)',
    "visayas": '(Visayas OR Cebu OR Iloilo OR Leyte OR Samar OR Negros OR Bohol)',
    "mindanao": '(Mindanao OR Davao OR Zamboanga OR Cotabato OR Bukidnon OR Lanao OR BARMM)',
}
THEMES = {
    "market": '("rice price" OR "food prices" OR inflation OR "price hike" OR "price increase")',
    "climate": '(typhoon OR flood OR drought OR "El Nino" OR "crop damage")',
    "hunger": '(hunger OR malnutrition OR "food aid" OR "food packs" OR "relief goods")',
    "jobs": '(unemployment OR layoffs OR "lost jobs" OR "job loss" OR livelihood)',
}
EXCLUDE = '-"Social Weather" -SWS'
FIRST, LAST = (2021, 1), (2026, 9)          # months; the last complete month before the 2026-10-01 issue


def months():
    y, m = FIRST
    while (y, m) <= LAST:
        a = date(y, m, 1)
        b = date(y + (m == 12), 1 if m == 12 else m + 1, 1)
        yield a, b
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def query(area: str, theme: str) -> str:
    return f"{AREAS[area]} {THEMES[theme]} {EXCLUDE}"


def _collect(src, q, a, b, out, depth=0):
    r = src.search(q, a, b)
    if r.status not in ("OK", "EMPTY", "ok", "empty") and not r.items:
        return {"status": str(r.status), "error": r.error}
    if r.at_cap:
        halves = split_window(a, b)
        if halves:
            for x, y in halves:
                time.sleep(1.0)
                _collect(src, q, x, y, out, depth + 1)
            return {"status": "SPLIT"}
    out.extend(r.items)
    return {"status": "OK", "n": len(r.items), "at_cap": bool(r.at_cap)}


def run() -> dict:
    d = RAW / "gnews"
    d.mkdir(parents=True, exist_ok=True)
    ledger_p = d / "ledger.json"
    ledger = json.loads(ledger_p.read_text()) if ledger_p.exists() else {}
    src = GoogleNewsRSS()
    with (d / "items.jsonl").open("a", encoding="utf-8", newline="\n") as fh:
        for area in AREAS:
            for theme in THEMES:
                for a, b in months():
                    key = f"{area}|{theme}|{a.isoformat()}"
                    if ledger.get(key, {}).get("status") in ("OK", "SPLIT"):
                        continue
                    items = []
                    st = _collect(src, query(area, theme), a, b, items)
                    for it in items:
                        if _credible(it.get("source_domain", "")):
                            fh.write(json.dumps({"area": area, "theme": theme, "window_start": a.isoformat(),
                                                 "window_end_excl": b.isoformat(), **it}) + "\n")
                    st["n_credible"] = sum(_credible(i.get("source_domain", "")) for i in items)
                    ledger[key] = st
                    ledger_p.write_text(json.dumps(ledger))
                    time.sleep(1.0)
                print(area, theme, flush=True)
    return ledger


if __name__ == "__main__":
    run()
