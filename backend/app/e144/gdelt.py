"""
E144 area news from the GDELT DOC 2.0 API (public; coverage from 2017-01-01). Daily article counts (timelinevolraw,
with GDELT's daily total as the denominator) for each SWS area x FAO theme, and the daily average tone (timelinetone)
of each area's coverage,
Philippine sources only (sourcecountry:RP). Articles restating SWS results are excluded from every query so the label
cannot enter the inputs.

    python -m app.e144.gdelt     -> data/e144/raw/gdelt/<area>__<theme>__<mode>.json + fetch_log.json
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from app.e144 import RAW

API = "https://api.gdeltproject.org/api/v2/doc/doc"
START, END = "20170101000000", "20261001000000"          # end = the current issue date (exclusive)
AREAS = {
    "metro_manila": '("Metro Manila" OR NCR OR "Quezon City" OR Caloocan OR Taguig OR Pasig OR Makati OR Navotas OR Tondo)',
    "balance_luzon": '(CALABARZON OR "Central Luzon" OR Bicol OR Ilocos OR "Cagayan Valley" OR MIMAROPA OR Cordillera OR '
                     'Pangasinan OR Bulacan OR Pampanga OR Batangas OR Laguna OR Cavite OR Albay OR Isabela OR Tarlac)',
    "visayas": '(Visayas OR Cebu OR Iloilo OR Leyte OR Samar OR Negros OR Bohol OR Tacloban OR Bacolod OR Capiz)',
    "mindanao": '(Mindanao OR Davao OR Zamboanga OR Cotabato OR Bukidnon OR Lanao OR Sulu OR BARMM OR "General Santos" '
                'OR "Cagayan de Oro")',
}
THEMES = {
    "base": "",
    "market": '("rice price" OR "food prices" OR inflation OR "price hike" OR "price increase")',
    "climate": '(typhoon OR flood OR drought OR "El Nino" OR "crop damage")',
    "hunger": '(hunger OR malnutrition OR "food aid" OR "food packs" OR "relief goods")',
    "jobs": '(unemployment OR layoffs OR "lost jobs" OR "job loss" OR livelihood)',
}
EXCLUDE = '-"Social Weather" -SWS'
MODES = ("timelinevolraw", "timelinetone")


def query(area: str, theme: str) -> str:
    return " ".join(x for x in (AREAS[area], THEMES[theme], EXCLUDE, "sourcecountry:RP") if x)


def fetch(q: str, mode: str, max_hours: float = 5.0) -> dict:
    """Patient fetch: 60 s between requests; on HTTP 429 (GDELT throttling this connection) wait 10 minutes and try
    again, for up to `max_hours`."""
    import urllib.error
    url = API + "?" + urllib.parse.urlencode({"query": q, "mode": mode, "startdatetime": START, "enddatetime": END,
                                              "format": "json"})
    t0 = time.time()
    while time.time() - t0 < max_hours * 3600:
        time.sleep(60)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "aipheed-research"})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read().decode("utf-8", "replace")
            if body.lstrip().startswith("{"):
                return json.loads(body)
            time.sleep(120)
        except urllib.error.HTTPError as e:
            time.sleep(600 if e.code == 429 else 120)
        except Exception:
            time.sleep(120)
    raise RuntimeError(f"GDELT failed: {mode} {q[:60]}")


def run() -> dict:
    out_dir = RAW / "gdelt"
    out_dir.mkdir(parents=True, exist_ok=True)
    log = {"api": API, "start": START, "end_exclusive": END, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
           "files": {}}
    for area in AREAS:
        for theme in THEMES:
            for mode in (MODES if theme == "base" else MODES[:1]):
                p = out_dir / f"{area}__{theme}__{mode}.json"
                if not p.exists():
                    p.write_text(json.dumps(fetch(query(area, theme), mode)), encoding="utf-8")
                log["files"][p.name] = {"query": query(area, theme), "mode": mode,
                                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                print(p.name, flush=True)
    (out_dir / "fetch_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    return log


if __name__ == "__main__":
    run()
