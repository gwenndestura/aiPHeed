"""
Official data sources of the served forecast: what each one is, how often it is really published, and the automatic update.

Each source keeps its own publication rhythm (monthly CPI, quarterly production, annual GRDP, poverty rounds every 2-3 years,
censuses every 5 years). A run fetches the sources that are due, validates the download, keeps the previous file when a fetch
fails (never a substitute value) and records every attempt in data/final/sources/log.jsonl. The newest period of each live series
and the day it was first seen online (app.e168.live_data first_seen) decide, together with the release rules, what a forecast may use.

    python -m app.final.sources update     fetch what is due now
    python -m app.final.sources status
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.paths import BACKEND_DIR
from app.quarterly.target import now_ph

DIR = BACKEND_DIR / "data" / "final" / "sources"
LOG = DIR / "log.jsonl"
STATUS = DIR / "status.json"

# id: (name, publisher, frequency, release delay / rule, role, check every N days)
SOURCES = {
    "psa_cpi": ("Consumer Price Index, food and rice, by province", "PSA OpenSTAT", "monthly",
                "about 5 days after the month; usable from the 1st of the second following month", "FINAL input", 7),
    "psa_production": ("Palay and corn production by province", "PSA OpenSTAT", "quarterly",
                       "about 45 days after the quarter", "FINAL input", 7),
    "psa_lfs": ("Labor Force Survey unemployment rate", "PSA OpenSTAT", "monthly/quarterly", "about 6 weeks after the survey month",
                "FINAL input", 7),
    "nasa_power": ("Rainfall and soil moisture at province centroids", "NASA POWER", "monthly", "about 2 months", "FINAL input", 7),
    "noaa_oni": ("Oceanic Nino Index", "NOAA CPC", "monthly (3-month seasons)", "about 10 days after the season ends",
                 "candidate input; shown as climate context", 7),
    "ibtracs": ("Tropical cyclone best tracks", "NOAA NCEI IBTrACS", "continuous", "days", "FINAL input", 7),
    "worldbank_remittances": ("Personal remittances received", "World Bank WDI", "annual", "mid-year", "not a FINAL input (monitored)", 30),
    "news": ("Food-stress news (DA-checked publishers)", "Rappler, Vera Files, Newsbytes, PCIJ and archives", "daily",
             "scored at each refresh; a forecast uses stories published before its cut-off", "FINAL input", 1),
    "psa_grdp_aff": ("Regional accounts: agriculture, forestry and fishing", "PSA OpenSTAT", "annual (April)",
                     "year Y usable from Q3 of Y+1", "evaluated, not a FINAL input (worsened forecasts)", 30),
    "psa_poverty": ("Official poverty statistics by province (4 bases)", "PSA OpenSTAT", "full-year rounds every 2-3 years",
                    "round R usable from 1 January of R+2", "FINAL input (latest released round)", 30),
    "psa_census": ("Census of population", "PSA", "every 5 years", "census year C usable from 1 January of C+2", "FINAL input (density)", 90),
}
LIVE_DATA = ["psa_production", "psa_cpi", "psa_lfs", "nasa_power", "noaa_oni", "ibtracs", "worldbank_remittances"]


def _status() -> dict:
    return json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}


def _save(st: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(st, indent=1, default=str), encoding="utf-8", newline="\n")


def _log(rec: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")


def due(source: str, now=None, st: dict | None = None) -> bool:
    st = st if st is not None else _status()
    last_ok = (st.get(source) or {}).get("last_success_utc")
    if not last_ok:
        return True
    every = SOURCES[source][5]
    return now_ph(now).astimezone(timezone.utc) - datetime.fromisoformat(last_ok) >= timedelta(days=every)


def _fetchers():
    """Name -> callable(today) -> dict. Imported lazily (network code)."""
    from app.e168 import live_data as LD
    from app.hcw import grdp_industry as GI
    from app.hcw import poverty_official as PO
    f = {k: (lambda today, k=k: LD.fetch(today, only=[k])[k]) for k in LIVE_DATA}

    def grdp(today):
        d = GI.fetch()
        if d.empty or d.year.max() < 2023:
            raise ValueError("GRDP download empty or older than the stored series")
        return {"status": "ok", "newest_year": int(d.year.max()), "rows": len(d)}

    def poverty(today):
        d = PO.fetch()
        p = d[d.level == "province_or_district"]
        if p.empty or p.groupby(["indicator", "year"]).size().min() < 70:
            raise ValueError("poverty download incomplete")
        return {"status": "ok", "newest_round": int(p.year.max()), "rows": len(p)}

    f["psa_grdp_aff"], f["psa_poverty"] = grdp, poverty
    return f


def update(now=None, only: list[str] | None = None, fetchers: dict | None = None) -> dict:
    """Fetch the sources that are due. A failed source keeps its previous file; its failure count rises and it is retried on the
    next run. News is collected by the forecast run's data stage (app.final.cycle), not here."""
    st = _status()
    t = now_ph(now)
    today = t.date().isoformat()
    fetchers = fetchers if fetchers is not None else _fetchers()
    res = {}
    for s in SOURCES:
        if s not in fetchers or (only and s not in only) or not due(s, t, st):
            continue
        rec = {"source": s, "attempt_utc": t.astimezone(timezone.utc).isoformat(timespec="seconds")}
        try:
            out = fetchers[s](today)
            if not isinstance(out, dict) or out.get("status") == "failed":
                raise RuntimeError((out or {}).get("error", "fetch reported failure"))
            rec.update(status="ok", detail=out)
            st[s] = {**st.get(s, {}), "last_success_utc": rec["attempt_utc"], "failures": 0, "last_detail": out, "last_error": None}
        except Exception as e:                                   # noqa: BLE001 - recorded; previous data stays
            rec.update(status="failed", error=f"{type(e).__name__}: {e}"[:500])
            prev = st.get(s, {})
            st[s] = {**prev, "last_failure_utc": rec["attempt_utc"], "failures": int(prev.get("failures", 0)) + 1, "last_error": rec["error"]}
        _log(rec)
        res[s] = rec
    _save(st)
    return res


def status(now=None) -> list[dict]:
    st = _status()
    out = []
    for s, (name, pub, freq, rule, role, every) in SOURCES.items():
        x = st.get(s, {})
        out.append({"id": s, "name": name, "publisher": pub, "frequency": freq, "release_rule": rule, "role": role,
                    "check_every_days": every, "last_success_utc": x.get("last_success_utc"), "last_failure_utc": x.get("last_failure_utc"),
                    "consecutive_failures": x.get("failures", 0), "last_error": x.get("last_error"), "due_now": due(s, now, st)})
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    print(json.dumps(update() if cmd == "update" else status(), indent=1, default=str))
