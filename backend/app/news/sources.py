"""
News source adapters (E28). Each search returns a FetchResult with an explicit status, so that an empty answer, a
failed request, a rate-limit refusal and an unreadable reply are never confused.

Supported sources (the project's existing integrations; nothing new is invented):

  google_news_rss   https://news.google.com/rss/search with after:/before: date operators. Verified live on
                    2026-10-14 for in-window dates (runs/news_live_probe*.json): HTTP 200, the date filter is honoured,
                    dates have day precision, and a window returns at most 100 items (cap; a 100-item window is
                    split by the collector).
  gdelt_doc         GDELT DOC 2.0 ArtList. GDELT allows one request per 5 s and answers excess requests with HTTP 429
                    or with HTTP 200 and a plain-text "Please limit requests..." body; the old fetcher parsed that as
                    JSON, failed, and silently returned []. From this host every E28 request got 429 (probe files), so
                    GDELT is implemented but recorded as UNAVAILABLE for the backfill.

HTTP is injected (http_get) and so is sleep, so every retry, timeout and rate-limit path is testable offline.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Callable
from urllib.parse import quote, urlparse

OK, EMPTY, FAILED, RATE_LIMITED, MALFORMED = "OK", "EMPTY", "FAILED", "RATE_LIMITED", "MALFORMED_RESPONSE"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/126.0.0.0 Safari/537.36")


@dataclass
class FetchResult:
    source: str
    status: str
    items: list[dict] = field(default_factory=list)
    n_raw: int = 0
    at_cap: bool = False
    http_status: int | None = None
    attempts: int = 0
    error: str | None = None
    requested_at: str = ""
    completed_at: str = ""


class HttpResponse:  # minimal shape the adapters use; requests.Response satisfies it
    status_code: int
    content: bytes
    text: str


def _default_get(url: str, timeout: float, headers: dict):
    import requests

    return requests.get(url, timeout=timeout, headers=headers)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bare_domain(href: str) -> str:
    d = urlparse(href or "").netloc.lower()
    return d[4:] if d.startswith("www.") else d


class _Base:
    name = "base"
    cap = 0
    transient_4xx: frozenset[int] = frozenset({408})

    def __init__(self, http_get: Callable | None = None, sleep: Callable[[float], None] = time.sleep,
                 delay: float = 3.0, max_attempts: int = 4, timeout: float = 30.0,
                 backoff: tuple[float, ...] = (5.0, 15.0, 45.0), rate_limit_backoff: tuple[float, ...] = (60.0, 180.0, 600.0)):
        self.http_get = http_get or _default_get
        self.sleep = sleep
        self.delay = delay
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.backoff = backoff
        self.rate_limit_backoff = rate_limit_backoff

    def _request(self, url: str) -> tuple[object | None, str | None, int, str]:
        """GET with retries. Returns (response, error, attempts, kind) where kind is 'ok' | 'rate' | 'fail'."""
        last_err, kind = None, "fail"
        for attempt in range(1, self.max_attempts + 1):
            try:
                r = self.http_get(url, self.timeout, {"User-Agent": _UA, "Accept-Language": "en-PH,en;q=0.9"})
            except Exception as exc:  # timeout, connection reset, DNS ...
                last_err, kind = f"{type(exc).__name__}: {str(exc)[:120]}", "fail"
                if attempt < self.max_attempts:
                    self.sleep(self.backoff[min(attempt - 1, len(self.backoff) - 1)])
                continue
            if r.status_code in (429, 503) or self._is_rate_text(r):
                last_err, kind = f"HTTP {r.status_code} rate limited", "rate"
                if attempt < self.max_attempts:
                    self.sleep(self.rate_limit_backoff[min(attempt - 1, len(self.rate_limit_backoff) - 1)])
                continue
            if 500 <= r.status_code < 600 or r.status_code in self.transient_4xx:
                last_err, kind = f"HTTP {r.status_code}", "fail"
                if attempt < self.max_attempts:
                    self.sleep(self.backoff[min(attempt - 1, len(self.backoff) - 1)])
                continue
            if r.status_code != 200:
                return r, f"HTTP {r.status_code}", attempt, "fail"     # 4xx other than 429: not retried
            self.sleep(self.delay)                                     # politeness between successful requests
            return r, None, attempt, "ok"
        return None, last_err, self.max_attempts, kind

    def _is_rate_text(self, r) -> bool:
        return False

    def search(self, query: str, start: date, end_excl: date) -> FetchResult:  # pragma: no cover - abstract
        raise NotImplementedError


class GoogleNewsRSS(_Base):
    name = "google_news_rss"
    cap = 100
    # Observed 2026-10-14 during the backfill: Google News intermittently answers a valid search with HTTP 404 under
    # load, and the identical URL returns 200 seconds later (runs/news_backfill_run1.log). A search URL cannot
    # genuinely be "not found", so 404 is retried like a server error instead of being recorded as a final failure.
    transient_4xx = frozenset({404, 408})

    @staticmethod
    def url(query: str, start: date, end_excl: date) -> str:
        return (f"https://news.google.com/rss/search?q={quote(query)}+after:{start.isoformat()}"
                f"+before:{end_excl.isoformat()}&hl=en-PH&gl=PH&ceid=PH:en")

    def search(self, query: str, start: date, end_excl: date) -> FetchResult:
        import feedparser

        t0 = _now()
        r, err, attempts, kind = self._request(self.url(query, start, end_excl))
        res = FetchResult(self.name, FAILED, requested_at=t0, attempts=attempts, error=err,
                          http_status=getattr(r, "status_code", None))
        if kind == "rate":
            res.status = RATE_LIMITED
        if r is None or kind != "ok":
            res.completed_at = _now()
            return res
        body = r.content or b""
        feed = feedparser.parse(body)
        if not feed.entries and (getattr(feed, "bozo", False) or b"<rss" not in body[:2000].lower()):
            res.status, res.error, res.completed_at = MALFORMED, "reply is not a readable RSS feed", _now()
            return res
        for e in feed.entries:
            src = (e.get("source") or {}).get("href", "") if isinstance(e.get("source"), dict) else ""
            title = (e.get("title") or "").strip()
            if " - " in title:                       # Google appends " - Publisher"
                title = title.rsplit(" - ", 1)[0].strip()
            res.items.append({"source_item_id": e.get("id") or e.get("link") or "", "title": title,
                              "link": e.get("link") or "", "source_domain": bare_domain(src),
                              "published_raw": e.get("published") or ""})
        res.n_raw = len(res.items)
        res.at_cap = res.n_raw >= self.cap
        res.status = OK if res.items else EMPTY
        res.completed_at = _now()
        return res


class GDELTDoc(_Base):
    name = "gdelt_doc"
    cap = 250

    def __init__(self, *a, **k):
        k.setdefault("delay", 6.0)        # GDELT: one request per 5 seconds
        super().__init__(*a, **k)

    @staticmethod
    def url(query: str, start: date, end_excl: date) -> str:
        return (f"https://api.gdeltproject.org/api/v2/doc/doc?query={quote(query)}&mode=ArtList&maxrecords=250"
                f"&startdatetime={start.strftime('%Y%m%d')}000000&enddatetime={end_excl.strftime('%Y%m%d')}000000"
                f"&format=json&sort=DateDesc")

    def _is_rate_text(self, r) -> bool:
        try:
            return r.status_code == 200 and (r.text or "").lstrip().lower().startswith("please limit requests")
        except Exception:
            return False

    def search(self, query: str, start: date, end_excl: date) -> FetchResult:
        import json

        t0 = _now()
        r, err, attempts, kind = self._request(self.url(query, start, end_excl))
        res = FetchResult(self.name, FAILED, requested_at=t0, attempts=attempts, error=err,
                          http_status=getattr(r, "status_code", None))
        if kind == "rate":
            res.status = RATE_LIMITED
        if r is None or kind != "ok":
            res.completed_at = _now()
            return res
        txt = (r.text or "").strip()
        if not txt:
            res.status, res.completed_at = EMPTY, _now()      # GDELT answers an empty search with an empty body
            return res
        try:
            data = json.loads(txt)
        except Exception:
            res.status, res.error, res.completed_at = MALFORMED, "reply is not JSON", _now()
            return res
        for a in data.get("articles") or []:
            sd = a.get("seendate", "")
            iso = ""
            try:
                iso = datetime.strptime(sd[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                iso = sd
            res.items.append({"source_item_id": a.get("url", ""), "title": (a.get("title") or "").strip(),
                              "link": a.get("url", ""), "source_domain": bare_domain(a.get("url", "")),
                              "published_raw": iso, "date_kind": "gdelt_seendate"})
        res.n_raw = len(res.items)
        res.at_cap = res.n_raw >= self.cap
        res.status = OK if res.items else EMPTY
        res.completed_at = _now()
        return res
