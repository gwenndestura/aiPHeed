"""
Quarterly news collector (E28): historical backfill and active-quarter incremental collection.

Query plan. Every province gets four queries per calendar-month window, and the region two. They condense the
project's existing Google News query bank (gnews_rss_fetcher: CALABARZON food/price, climate/agriculture, government
programme and Filipino groups, HungerGist themes) into province-anchored Boolean queries, so that every province is
queried in English and Filipino in every month instead of only where a hand-written query happened to name it.
Province anchors exclude the NCR namesakes the geocoder also masks ("Quezon City", "Jose Rizal", "Rizal Park").

Window handling. A window that returns the source cap (100 for Google News) may be truncated, so it is split in two on
a day boundary and both halves are queried; a one-day window still at the cap is recorded TRUNCATED_AT_MIN_WINDOW.

Intake gates (applied to every returned item, in this order; refused items keep only a SHA-256 of the link):
    UNPARSEABLE_DATE         no readable publication date -> its quarter (and so its eligibility) is unknown
    BEFORE_STUDY_WINDOW      published before 2021-01-01 00:00 PHT (study-window rule)
    AFTER_AUTHORIZED_LIMIT   published at or after the end of the last authorized quarter (config/authorization.json)
    AFTER_CUTOFF             published after the run's forecast cutoff, when one is given
    NON_CREDIBLE_SOURCE      publisher not in the project's CREDIBLE_DOMAINS allowlist
    NO_TITLE                 nothing to score
Publication time is converted to Asia/Manila before any comparison; the retrieval time is never used as a
publication date.

Idempotence. The window ledger records the final status of every (source, query, province, window). A rerun skips
COMPLETE and TRUNCATED_AT_MIN_WINDOW windows, re-descends into SPLIT windows, and retries FAILED, RATE_LIMITED,
MALFORMED_RESPONSE and OPEN (still-running) windows. Known articles are recorded as sightings, never rewritten.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.news import sources as S
from app.news.store import NewsStore, article_key, sha, window_id
from app.news.timeutil import (PH, month_windows, ph_midnight, quarter_end_excl, quarter_of_date, quarters_between,
                               parse_quarter, split_window, to_ph)

STUDY_START_Q = "2021-Q1"
STUDY_START_PH = datetime(2021, 1, 1, tzinfo=PH)

PROVINCES: dict[str, str] = {   # name -> code used by app.ml.corpus.geocoder.PROVINCE_PSGC
    "Batangas": "PH040500000", "Cavite": "PH040100000", "Laguna": "PH040200000",
    "Quezon": "PH040300000", "Rizal": "PH040400000",
}
ANCHOR = {
    "Batangas": '"Batangas"', "Cavite": '"Cavite"', "Laguna": '"Laguna"',
    "Quezon": '"Quezon" -"Quezon City"', "Rizal": '"Rizal" -"Jose Rizal" -"Rizal Park"',
}


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    lang: str
    theme: str
    template: str


PROVINCE_QUERIES = (
    QuerySpec("en_food", "en", "food access and prices",
              "{A} (food OR rice OR prices OR hunger OR malnutrition OR inflation)"),
    QuerySpec("en_shocks", "en", "climate and agricultural shocks",
              '{A} (typhoon OR flood OR drought OR "El Nino" OR "crop damage" OR "fish kill" OR farmers OR harvest)'),
    QuerySpec("en_assist", "en", "assistance and livelihoods",
              '{A} (relief OR ayuda OR DSWD OR "food packs" OR livelihood OR poverty)'),
    QuerySpec("fil_all", "fil", "Filipino: food, prices, hunger, aid, farming, storms",
              "{A} (pagkain OR bigas OR presyo OR gutom OR ayuda OR magsasaka OR bagyo OR baha)"),
)
REGION = "REGION"
REGION_QUERIES = (
    QuerySpec("reg_en", "en", "regional food and shocks",
              "CALABARZON (food OR rice OR prices OR hunger OR typhoon OR relief OR farmers)"),
    QuerySpec("reg_fil", "fil", "regional, Filipino",
              "CALABARZON (pagkain OR bigas OR presyo OR gutom OR ayuda OR bagyo)"),
)


def query_text(spec: QuerySpec, province: str) -> str:
    return spec.template.format(A=ANCHOR.get(province, ""))


def plan_for(province: str):
    return REGION_QUERIES if province == REGION else PROVINCE_QUERIES


def _credible(domain: str) -> bool:
    from app.ml.corpus.rss_fetcher import CREDIBLE_DOMAINS

    d = (domain or "").lower()
    if d in CREDIBLE_DOMAINS:
        return True
    parts = d.split(".")
    return any(".".join(parts[i:]) in CREDIBLE_DOMAINS for i in range(1, len(parts)))


def _geocode(title: str) -> str | None:
    from app.ml.corpus.geocoder import geocode_to_province

    return geocode_to_province(title)


def _file_sha(mod) -> str:
    try:
        return hashlib.sha256(Path(mod.__file__).read_bytes()).hexdigest()[:16]
    except Exception:
        return "unknown"


class SourceUnavailable(RuntimeError):
    pass


class Collector:
    def __init__(self, store: NewsStore, sources: list, authorized_until: str, cutoff_ph: datetime | None = None,
                 now: datetime | None = None, credible=_credible, geocode=_geocode, max_consecutive_failures: int = 8,
                 authorized_through: str | None = None):
        self.store = store
        self.sources = sources
        self.authorized_until = authorized_until
        self.limit_ph = ph_midnight(quarter_end_excl(authorized_until))
        if authorized_through:                 # E31: date-level limit inside the last authorized quarter
            self.limit_ph = min(self.limit_ph, ph_midnight(date.fromisoformat(authorized_through) + timedelta(days=1)))
        self.authorized_through = authorized_through
        self.cutoff_ph = to_ph(cutoff_ph) if cutoff_ph else None
        self.now = (now or datetime.now(timezone.utc)).astimezone(PH)
        self.credible = credible
        self.geocode = geocode
        self.max_consecutive_failures = max_consecutive_failures
        self._consec_fail = 0
        self.requests_made = 0
        self.max_requests: int | None = None
        self.run_id = ""
        import app.ml.corpus.geocoder as G

        self.geocoder_sha = _file_sha(G)

    # ------------------------------------------------------------------ public
    def run(self, mode: str, quarters: list[str], provinces: list[str] | None = None,
            max_requests: int | None = None) -> dict:
        provinces = list(provinces or list(PROVINCES) + [REGION])
        self.max_requests = max_requests
        self.run_id = f"{self.now.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"
        refused = [q for q in quarters if parse_quarter(q) > parse_quarter(self.authorized_until)
                   or parse_quarter(q) < parse_quarter(STUDY_START_Q)]
        todo = [q for q in quarters if q not in refused]
        self.store.log_run({"event": "start", "run_id": self.run_id, "mode": mode, "quarters": quarters,
                            "provinces": provinces, "authorized_until": self.authorized_until,
                            "cutoff_ph": self.cutoff_ph.isoformat() if self.cutoff_ph else None,
                            "refused_quarters": refused, "sources": [s.name for s in self.sources],
                            "started_at": datetime.now(timezone.utc).isoformat(), "clock_ph": self.now.isoformat()})
        status = "COMPLETED"
        try:
            for q in todo:
                for a, b in month_windows(q):
                    if ph_midnight(a) > self.now or ph_midnight(a) >= self.limit_ph:   # future / after the limit
                        continue
                    for p in provinces:
                        for spec in plan_for(p):
                            for src in self.sources:
                                self._window(src, spec, p, q, a, b)
        except _Budget:
            status = "INTERRUPTED_BUDGET"
        except SourceUnavailable as exc:
            status = f"STOPPED_SOURCE_UNAVAILABLE: {exc}"
        except KeyboardInterrupt:
            status = "INTERRUPTED"
        end = {"event": "end", "run_id": self.run_id, "status": status, "requests": self.requests_made,
               "ended_at": datetime.now(timezone.utc).isoformat()}
        self.store.log_run(end)
        return end

    # ------------------------------------------------------------------ windows
    def _window(self, src, spec: QuerySpec, prov: str, q: str, a: date, b: date) -> None:
        wid = window_id(src.name, spec.query_id, prov, a.isoformat(), b.isoformat())
        w = self.store.windows.get(wid)
        if w and w["status"] in ("COMPLETE", "TRUNCATED_AT_MIN_WINDOW"):
            return
        if w and w["status"] == "SPLIT":
            for (x, y) in split_window(a, b):
                self._window(src, spec, prov, q, x, y)
            return
        if self.max_requests is not None and self.requests_made >= self.max_requests:
            raise _Budget()
        today_excl = (self.now + timedelta(days=1)).date()
        b_eff = min(b, today_excl)                        # an active quarter is queried only up to today
        is_open = b_eff < b
        query = query_text(spec, prov)
        res = src.search(query, a, b_eff)
        self.requests_made += 1
        n_new = n_seen = 0
        counts: dict[str, int] = {}
        if res.status in (S.OK, S.EMPTY):
            self._consec_fail = 0
            for it in res.items:
                verdict = self._intake(it, src.name, spec, prov, q, a, b_eff)
                counts[verdict] = counts.get(verdict, 0) + 1
            n_new, n_seen = counts.pop("NEW", 0), counts.pop("SEEN", 0)
        else:
            self._consec_fail += 1
        self.store.log_request({"run_id": self.run_id, "source": src.name, "query_id": spec.query_id,
                                "lang": spec.lang, "province": prov, "quarter": q, "window_start": a.isoformat(),
                                "window_end_excl": b_eff.isoformat(), "query": query, "status": res.status,
                                "http_status": res.http_status, "attempts": res.attempts, "error": res.error,
                                "n_raw": res.n_raw, "at_cap": res.at_cap, "n_new": n_new, "n_known": n_seen,
                                "rejected": counts, "requested_at": res.requested_at,
                                "completed_at": res.completed_at})
        if res.status not in (S.OK, S.EMPTY):
            self.store.set_window({"window_id": wid, "source": src.name, "query_id": spec.query_id, "province": prov,
                                   "quarter": q, "start": a.isoformat(), "end_excl": b.isoformat(),
                                   "status": res.status, "run_id": self.run_id, "error": res.error})
            if self._consec_fail >= self.max_consecutive_failures:
                raise SourceUnavailable(f"{src.name}: {self._consec_fail} consecutive failed requests ({res.error})")
            return
        halves = split_window(a, b) if (res.at_cap and not is_open) else None
        if halves:
            self.store.set_window({"window_id": wid, "source": src.name, "query_id": spec.query_id, "province": prov,
                                   "quarter": q, "start": a.isoformat(), "end_excl": b.isoformat(),
                                   "status": "SPLIT", "run_id": self.run_id, "n_raw": res.n_raw})
            for (x, y) in halves:
                self._window(src, spec, prov, q, x, y)
            return
        status = "OPEN" if is_open else ("TRUNCATED_AT_MIN_WINDOW" if res.at_cap else "COMPLETE")
        self.store.set_window({"window_id": wid, "source": src.name, "query_id": spec.query_id, "province": prov,
                               "quarter": q, "start": a.isoformat(), "end_excl": b.isoformat(),
                               "queried_end_excl": b_eff.isoformat(), "status": status, "run_id": self.run_id,
                               "n_raw": res.n_raw})

    # ------------------------------------------------------------------ intake
    def _intake(self, it: dict, source: str, spec: QuerySpec, prov: str, q: str, a: date, b: date) -> str:
        from app.ml.corpus._dates import published_in_ph

        link_hash = sha(it.get("link") or it.get("source_item_id") or "")
        base = {"run_id": self.run_id, "source": source, "query_id": spec.query_id, "province": prov,
                "window_start": a.isoformat(), "link_sha256": link_hash}
        ts = published_in_ph(it.get("published_raw"))
        if ts is None:
            self.store.reject({**base, "reason": "UNPARSEABLE_DATE"})
            return "UNPARSEABLE_DATE"
        ts = ts.to_pydatetime()
        if ts < STUDY_START_PH:
            self.store.reject({**base, "reason": "BEFORE_STUDY_WINDOW"})
            return "BEFORE_STUDY_WINDOW"
        if ts >= self.limit_ph:
            self.store.reject({**base, "reason": "AFTER_AUTHORIZED_LIMIT"})
            return "AFTER_AUTHORIZED_LIMIT"
        if self.cutoff_ph is not None and ts > self.cutoff_ph:
            self.store.reject({**base, "reason": "AFTER_CUTOFF"})
            return "AFTER_CUTOFF"
        if not self.credible(it.get("source_domain", "")):
            self.store.reject({**base, "reason": "NON_CREDIBLE_SOURCE", "source_domain": it.get("source_domain", "")})
            return "NON_CREDIBLE_SOURCE"
        title = (it.get("title") or "").strip()
        if not title:
            self.store.reject({**base, "reason": "NO_TITLE"})
            return "NO_TITLE"
        ph_date = ts.date().isoformat()
        key = article_key(it.get("source_domain", ""), title, ph_date)
        sighting = {"article_key": key, "run_id": self.run_id, "source": source, "query_id": spec.query_id,
                    "province": prov, "window_start": a.isoformat(), "source_item_id": it.get("source_item_id", ""),
                    "seen_at": datetime.now(timezone.utc).isoformat()}
        if key in self.store.articles:
            self.store.add_sighting(sighting)
            return "SEEN"
        rec = {"article_key": key, "title": title, "link": it.get("link", ""),
               "source_item_id": it.get("source_item_id", ""), "source_domain": it.get("source_domain", ""),
               "source": source, "date_kind": it.get("date_kind", "publisher_pubdate"),
               "published_raw": it.get("published_raw"), "published_ph": ts.isoformat(), "ph_date": ph_date,
               "quarter": quarter_of_date(ts.date()), "outside_requested_window": not (a <= ts.date() < b),
               "geo_province_code": self.geocode(title), "geocoder_sha": self.geocoder_sha,
               "source_policy": getattr(self.credible, "version", "v1"),
               "first_query_id": spec.query_id, "first_query_province": prov, "first_run_id": self.run_id,
               "first_seen_at": sighting["seen_at"]}
        self.store.add_article(rec)
        self.store.add_sighting(sighting)
        return "NEW"


class _Budget(Exception):
    pass


def all_quarters(authorized_until: str) -> list[str]:
    return quarters_between(STUDY_START_Q, authorized_until)
