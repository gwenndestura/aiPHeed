"""
app/news/lead_extractor.py
--------------------------
E83: recover the publisher's own lead text for already-collected news records.

The corpus links are Google News redirects (news.google.com/rss/articles/...), which robots.txt disallows and which do
not reveal the publisher URL offline. The publisher URL is therefore resolved from the publisher's own, robots-listed
structures, in this order:

  1. WordPress REST search (`/wp-json/wp/v2/posts?search=`), when the site exposes it publicly; it returns the
     publisher's excerpt directly.
  2. Yoast / WordPress post sitemaps (`/sitemap_index.xml` -> `post-sitemapN.xml`), matched to the headline by slug
     tokens and date.

The resolved page is fetched only when robots.txt allows it for this crawler AND for the AI-crawler tokens a site may
block (ClaudeBot, anthropic-ai), at no more than one request per `MIN_INTERVAL` seconds per host. Stored per article:
the og/meta description, the opening paragraphs (at most `MAX_LEAD_CHARS`), body word count, the publisher's own
publication time, and every attempt with its outcome. Full article bodies are never stored (E31 authorization: lead
text only, no full text); body-derived counts are computed in memory.

Extraction status (one per article):
  lead_ok            opening paragraphs extracted (meta description may also be present)
  meta_only          only the publisher's og/meta description was available
  robots_disallowed  the publisher's robots.txt disallows the article path for this crawler (headline-only by policy)
  blocked            HTTP 401/403/429 or a bot challenge page (headline-only, extraction failed)
  unresolved         no publisher URL could be matched to the headline (headline-only, extraction failed)
  fetch_error        network or parse failure after retries
  no_method          no permitted resolution method exists for this domain (headline-only by policy)
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlparse

import requests

UA = "Mozilla/5.0 (compatible; aiPHeed-thesis-research/1.0; lead-text only)"
ROBOT_TOKENS = ("aiPHeed-thesis-research", "ClaudeBot", "anthropic-ai", "*")
MIN_INTERVAL = 2.5
MAX_LEAD_CHARS = 1200
TIMEOUT = 25

# Resolution method per publisher domain (from the corpus' source_domain). Domains absent here get `no_method`.
# Checked 2026-10-21 with this crawler: the Inquirer family, BusinessMirror and UPLB answer with a bot challenge (403),
# which is never bypassed -> `blocked`; GMA disallows /news/story; Rappler disallows ClaudeBot; Manila Times asks a
# 600-second crawl delay; MB, ABS-CBN and PIA answer 403 or a challenge; Philstar and PNA list no article sitemaps.
YOAST = {
    "newsinfo.inquirer.net", "business.inquirer.net", "globalnation.inquirer.net", "opinion.inquirer.net",
    "cebudailynews.inquirer.net", "entertainment.inquirer.net", "lifestyle.inquirer.net", "sports.inquirer.net",
    "usa.inquirer.net", "pop.inquirer.net", "www.da.gov.ph", "fo4a.dswd.gov.ph", "businessmirror.com.ph",
    "uplb.edu.ph",
}
WPAPI = {"www.bworldonline.com"}
DAILY = {"www.sunstar.com.ph": "https://www.sunstar.com.ph/sitemap/sitemap-daily-{d}.xml"}
POLICY_SKIP = {"www.gmanetwork.com": "robots_disallowed", "gmanetwork.com": "robots_disallowed",
               "rappler.com": "robots_disallowed", "www.rappler.com": "robots_disallowed",
               "www.manilatimes.net": "no_method"}
HOST = {"da.gov.ph": "www.da.gov.ph", "bworldonline.com": "www.bworldonline.com", "dswd.gov.ph": "www.dswd.gov.ph",
        "manilatimes.net": "www.manilatimes.net", "inquirer.net": "newsinfo.inquirer.net",
        "sunstar.com.ph": "www.sunstar.com.ph", "gmanetwork.com": "www.gmanetwork.com", "rappler.com": "www.rappler.com"}

BLOCKED_HOSTS: set[str] = set()       # filled at run time when a host's sitemap index answers with a challenge
STOP = set("a an the of to in on for and or at by with from as is are was were be its it this that new over into".split())


def host_of(domain: str) -> str:
    return HOST.get(domain, domain)


def tokens(s: str) -> list[str]:
    s = html.unescape(s or "").lower()
    s = re.sub(r"[‘’']", "", s)
    return [w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP]


def slug_tokens(url: str) -> list[str]:
    path = urlparse(url).path.rstrip("/")
    return tokens(path.rsplit("/", 1)[-1].replace("-", " "))


def match_score(title: str, url: str) -> float:
    """Share of headline tokens found in the URL slug, penalised when the slug has many extra tokens."""
    a, b = set(tokens(title)), set(slug_tokens(url))
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / max(len(a), 1) * (inter / max(len(b), 1)) ** 0.25


# ------------------------------------------------------------------------------------------------ HTML parsing
class _LeadParser(HTMLParser):
    """Collects meta tags and paragraph text inside the main article container (stdlib only)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.paras: list[str] = []
        self._in_p = 0
        self._buf: list[str] = []
        self._skip = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = (a.get("property") or a.get("name") or "").lower()
            if k and a.get("content") and k not in self.meta:
                self.meta[k] = a["content"]
        elif tag in ("script", "style", "noscript", "figcaption", "aside", "nav", "footer"):
            self._skip += 1
        elif tag == "p" and not self._skip:
            self._in_p += 1
            self._buf = []
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "figcaption", "aside", "nav", "footer") and self._skip:
            self._skip -= 1
        elif tag == "p" and self._in_p:
            self._in_p -= 1
            t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if t:
                self.paras.append(t)
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_p and not self._skip:
            self._buf.append(data)
        if self._in_title:
            self.title += data


BOILER = re.compile(r"(subscribe|newsletter|all rights reserved|copyright|read next|follow us|advertisement|"
                    r"cookies|sign up|click here|download the|for more news|related stories|^ad$)", re.I)


def parse_page(text: str) -> dict:
    p = _LeadParser()
    try:
        p.feed(text)
    except Exception:
        pass
    desc = p.meta.get("og:description") or p.meta.get("description") or p.meta.get("twitter:description") or ""
    body = [x for x in p.paras if len(x) >= 60 and not BOILER.search(x)]
    lead, n = [], 0
    for x in body:
        if n + len(x) > MAX_LEAD_CHARS and lead:
            break
        lead.append(x[:MAX_LEAD_CHARS])
        n += len(x)
        if len(lead) >= 3:
            break
    return {
        "meta_description": html.unescape(desc).strip(),
        "lead": "\n".join(lead),
        "body_words": int(sum(len(x.split()) for x in body)),
        "body_paragraphs": len(body),
        "published_meta": p.meta.get("article:published_time") or p.meta.get("datepublished") or "",
        "og_title": html.unescape(p.meta.get("og:title") or p.title or "").strip(),
        "_body_text": "\n".join(body),          # transient: used for in-memory features, never written
    }


def is_challenge(text: str) -> bool:
    t = text[:4000].lower()
    return "just a moment..." in t or "cf-chl" in t or "attention required" in t or "captcha" in t


# ------------------------------------------------------------------------------------------------ fetching
@dataclass
class Fetcher:
    get: Callable = field(default=None)
    sleep: Callable[[float], None] = time.sleep
    _last: dict = field(default_factory=dict)
    _robots: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.get is None:
            s = requests.Session()
            s.headers.update({"User-Agent": UA, "Accept-Language": "en,fil;q=0.8"})
            self.get = lambda url: s.get(url, timeout=TIMEOUT, allow_redirects=True)

    def robots(self, host: str) -> urllib.robotparser.RobotFileParser | None:
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self._get(f"https://{host}/robots.txt")
                if r is not None and r.status_code == 200 and not is_challenge(r.text):
                    rp.parse(r.text.splitlines())
                elif r is not None and r.status_code in (404, 410):
                    rp.parse([])              # no robots file: everything allowed
                else:
                    rp = None                 # unknown policy: do not fetch
            except Exception:
                rp = None
            self._robots[host] = rp
        return self._robots[host]

    def allowed(self, url: str) -> bool:
        rp = self.robots(urlparse(url).netloc)
        return rp is not None and all(rp.can_fetch(t, url) for t in ROBOT_TOKENS)

    def _get(self, url: str):
        host = urlparse(url).netloc
        wait = MIN_INTERVAL - (time.monotonic() - self._last.get(host, -1e9))
        if wait > 0:
            self.sleep(wait)
        self._last[host] = time.monotonic()
        return self.get(url)

    def fetch(self, url: str, tries: int = 3):
        """(response | None, outcome) with retries on transient errors; robots checked by the caller."""
        last = "fetch_error"
        for i in range(tries):
            try:
                r = self._get(url)
            except Exception as e:  # network
                last = f"fetch_error:{type(e).__name__}"
                self.sleep(2 * (i + 1))
                continue
            if "charset" not in (r.headers.get("content-type") or "").lower():
                r.encoding = "utf-8"              # requests defaults to ISO-8859-1 without a charset header
            if r.status_code in (401, 403) or (r.status_code == 200 and is_challenge(r.text)):
                return r, "blocked"
            if r.status_code == 429 or r.status_code >= 500:
                last = f"http_{r.status_code}"
                self.sleep(10 * (i + 1))
                continue
            return r, ("ok" if r.status_code == 200 else f"http_{r.status_code}")
        return None, last


# ------------------------------------------------------------------------------------------------ resolvers
def _ts(s: str) -> date | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


class SitemapIndex:
    """Yoast post sitemaps of one host, loaded lazily for the date range that is needed."""

    def __init__(self, f: Fetcher, host: str, log: Callable[[dict], None]):
        self.f, self.host, self.log = f, host, log
        self.files: list[tuple[str, date | None]] | None = None
        self.urls: dict[str, list[tuple[str, date | None]]] = {}

    def index(self) -> list[tuple[str, date | None]]:
        if self.files is None:
            self.files = []
            for name in ("sitemap_index.xml", "wp-sitemap.xml"):
                u = f"https://{self.host}/{name}"
                if not self.f.allowed(u):
                    continue
                r, out = self.f.fetch(u)
                self.log({"step": "sitemap_index", "url": u, "outcome": out})
                if out == "blocked":
                    BLOCKED_HOSTS.add(self.host)
                if r is None or out != "ok":
                    continue
                locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>(?:\s*<lastmod>\s*([^<\s]+))?", r.text)
                self.files = [(l, _ts(m) if m else None) for l, m in locs if re.search(r"posts?-(post-)?sitemap|sitemap-posts-post", l)]
                if self.files:
                    break
        return self.files

    def load(self, u: str) -> list[tuple[str, date | None]]:
        if u not in self.urls:
            r, out = (self.f.fetch(u) if self.f.allowed(u) else (None, "robots_disallowed"))
            self.log({"step": "sitemap", "url": u, "outcome": out})
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>(?:\s*<lastmod>\s*([^<\s]+))?", r.text) if r is not None and out == "ok" else []
            self.urls[u] = [(l, _ts(m) if m else None) for l, m in locs
                            if not re.search(r"\.(jpe?g|png|gif|webp)$", l, re.I)]
        return self.urls[u]

    def candidates(self, d: date) -> list[str]:
        """Sitemap files that can hold a post published on d: chronological files whose span covers d."""
        files = self.index()
        if len(files) <= 30 or any(lm is None for _, lm in files):
            return [u for u, _ in files]          # small sites: every post file (lastmods are edit times, not order)
        out = []
        prev_end: date | None = None
        for u, lm in files:
            # a post file's lastmod is its newest modification: the file can hold d when lastmod >= d and the
            # previous file ended (roughly) before d + 45 days.
            if lm is not None and lm >= d and (prev_end is None or prev_end <= date.fromordinal(d.toordinal() + 45)):
                out.append(u)
            prev_end = lm or prev_end
        return out


def resolve_wpapi(f: Fetcher, host: str, title: str, d: date, log) -> tuple[str | None, str, dict]:
    q = " ".join(tokens(title)[:8])
    a = date.fromordinal(d.toordinal() - 3).isoformat()
    b = date.fromordinal(d.toordinal() + 3).isoformat()
    u = (f"https://{host}/wp-json/wp/v2/posts?search={quote(q)}&after={a}T00:00:00&before={b}T23:59:59"
         f"&per_page=10&_fields=date,link,title,excerpt")
    if not f.allowed(u):
        return None, "robots_disallowed", {}
    r, out = f.fetch(u)
    log({"step": "wpapi_search", "url": u, "outcome": out})
    if r is None or out != "ok":
        return None, ("blocked" if out == "blocked" else "unresolved"), {}
    try:
        items = json.loads(r.text.lstrip("\ufeff"))      # some WordPress sites prefix a byte-order mark
    except Exception:
        return None, "unresolved", {}
    best, bs = None, 0.0
    for it in items if isinstance(items, list) else []:
        s = match_score(title, it.get("link", "")) if it.get("link") else 0.0
        t2 = html.unescape(re.sub("<[^>]+>", "", (it.get("title") or {}).get("rendered", "")))
        s = max(s, len(set(tokens(title)) & set(tokens(t2))) / max(len(set(tokens(title))), 1))
        if s > bs:
            best, bs = it, s
    if best is None or bs < 0.6:
        return None, "unresolved", {}
    ex = html.unescape(re.sub("<[^>]+>", " ", (best.get("excerpt") or {}).get("rendered", ""))).strip()
    return best["link"], "ok", {"wp_excerpt": re.sub(r"\s+", " ", ex), "match_score": round(bs, 3)}


def resolve_sitemap(idx: SitemapIndex, title: str, d: date, files: list[str] | None = None) -> tuple[str | None, str, dict]:
    best, bs = None, 0.0
    for u in (files if files is not None else idx.candidates(d)):
        for loc, lm in idx.load(u):
            if lm is not None and (lm.toordinal() < d.toordinal() - 2):
                continue
            s = match_score(title, loc)
            if s > bs:
                best, bs = loc, s
        if bs >= 0.85:
            break
    if best is None or bs < 0.6:
        return None, "unresolved", {"match_score": round(bs, 3)}
    return best, "ok", {"match_score": round(bs, 3)}


# ------------------------------------------------------------------------------------------------ driver
def extract(articles: list[dict], out_path: Path, f: Fetcher | None = None, limit: int | None = None,
            progress: Callable[[int, int], None] | None = None) -> dict:
    """Process articles (dicts with article_key, title, source_domain, ph_date); append one JSON line per article to
    out_path, skipping article_keys already present (idempotent, resumable)."""
    f = f or Fetcher()
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["article_key"])
            except Exception:
                pass
    todo = [a for a in articles if a["article_key"] not in done]
    if limit:
        todo = todo[:limit]
    idxs: dict[str, SitemapIndex] = {}
    counts: dict[str, int] = {}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fh:
        for i, a in enumerate(todo):
            attempts: list[dict] = []
            log = lambda r: attempts.append({**r, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            host = host_of(a["source_domain"])
            d = date.fromisoformat(a["ph_date"])
            rec = {"article_key": a["article_key"], "source_domain": a["source_domain"], "title": a["title"],
                   "ph_date": a["ph_date"], "publisher_url": None, "meta_description": "", "lead": "",
                   "body_words": 0, "body_paragraphs": 0, "published_meta": "", "match_score": None}
            try:
                if host in WPAPI:
                    url, st, extra = resolve_wpapi(f, host, a["title"], d, log)
                elif host in YOAST:
                    idx = idxs.setdefault(host, SitemapIndex(f, host, log))
                    idx.log = log
                    url, st, extra = resolve_sitemap(idx, a["title"], d)
                    if st == "unresolved" and idx.files == []:
                        st = "blocked" if any(x.get("outcome") == "blocked" for x in attempts) or host in BLOCKED_HOSTS else "unresolved"
                elif host in DAILY:
                    idx = idxs.setdefault(host, SitemapIndex(f, host, log))
                    idx.log = log
                    days = [date.fromordinal(d.toordinal() + k).isoformat() for k in (0, -1, 1)]
                    url, st, extra = resolve_sitemap(idx, a["title"], d, [DAILY[host].format(d=x) for x in days])
                elif host in POLICY_SKIP:
                    url, st, extra = None, POLICY_SKIP[host], {}
                else:
                    url, st, extra = None, "no_method", {}
                rec.update({k: v for k, v in extra.items() if k in ("match_score",)})
                if extra.get("wp_excerpt"):
                    rec["meta_description"] = extra["wp_excerpt"]
                if url:
                    rec["publisher_url"] = url
                    if not f.allowed(url):
                        st = "robots_disallowed"
                        log({"step": "page", "url": url, "outcome": st})
                    else:
                        r, out = f.fetch(url)
                        log({"step": "page", "url": url, "outcome": out})
                        if r is not None and out == "ok":
                            pg = parse_page(r.text)
                            pg.pop("_body_text", None)
                            rec.update({k: v for k, v in pg.items() if k != "meta_description"})
                            rec["meta_description"] = pg["meta_description"] or rec["meta_description"]
                            st = "lead_ok" if pg["lead"] else ("meta_only" if rec["meta_description"] else "fetch_error")
                        else:
                            st = "blocked" if out == "blocked" else ("meta_only" if rec["meta_description"] else "fetch_error")
            except Exception as e:  # never stop the batch
                st = f"fetch_error"
                log({"step": "exception", "outcome": f"{type(e).__name__}: {e}"[:200]})
            rec["extraction_status"] = st
            rec["attempts"] = attempts
            rec["extracted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            counts[st] = counts.get(st, 0) + 1
            if progress:
                progress(i + 1, len(todo))
    return counts
