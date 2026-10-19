"""
app/news/pipeline_v3.py
-----------------------
Improved news pipeline (E64, Objective 1): the E31 + E60 corpora, E60 classifier v2 (relevance and the five triggers),
province attribution, syndication de-duplication, FSSI-v3 and the as-of N3 forecast features. The same functions build
the experiment's training features and the served record's inference features (training/serving parity).

Timing: an origin t (predictor quarter) is issued at O(t) = 00:00 PHT on day 1 of quarter t+1; only articles of quarter
t published before O(t) are used. Missing news is never zero-filled where zero would mean "no stress": counts are
counts of admitted articles (0 = none admitted), coverage is carried separately, and FSSI is None without evidence.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
import re
import statistics
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

from app.news.classifier_v2 import classify

DATA = Path(__file__).resolve().parents[2] / "data"
STORES = (DATA / "news_e31" / "articles.jsonl", DATA / "news_e60" / "articles.jsonl")
SCORES = (DATA / "news_e31" / "scores.jsonl", DATA / "news_v3" / "scores.jsonl")
PROVINCE_CODES = ("PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000")
FIRST_DATE, LAST_DATE = "2021-01-01", "2026-10-14"          # study window (user authorization of 2026-10-14)
TRIGGERS = ("market", "climate", "fish_kill", "employment", "ofw_remittance")
PROVINCE_TRIGGERS = ("market", "climate", "fish_kill", "employment")
NATIONAL_TRIGGERS = ("market", "employment", "ofw_remittance")
HALF_LIFE_DAYS = 30.0
SYNDICATION_DAYS = 3
MIN_ARTICLES = 5
INTENSITY_SUFFIX = "|v2-noguard"
N3_COLS = (["n3_cov"] + [f"n3_{k}_rw" for k in PROVINCE_TRIGGERS] + [f"n3_nat_{k}_rw" for k in NATIONAL_TRIGGERS]
           + ["n3_src", "n3_fssi"])
CLASSIFIER_V2_SHA256 = "327f9431f29f69a96b9208b38cb9010ab85b5254413e09092c62b41d7ebff89a"   # E60 freeze (LF-normalised)


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def origin(t: int) -> datetime:
    """O(t): 00:00 PHT, day 1 of quarter t+1 (naive PH time, as the stores' published_ph without offset)."""
    n = t + 1
    return datetime(n // 4, (n % 4) * 3 + 1, 1)


def classifier_sha() -> str:
    return hashlib.sha256((Path(__file__).parent / "classifier_v2.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def norm_title(t: str) -> str:
    t = t.rsplit(" - ", 1)[0] if " - " in t else t
    t = unicodedata.normalize("NFKD", t).lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())


def _ph(a: dict) -> datetime:
    return datetime.fromisoformat(a["published_ph"]).replace(tzinfo=None)


@functools.lru_cache(maxsize=1)
def corpus() -> tuple[dict, ...]:
    """Every article of both stores once (first store wins on a duplicate key), inside the study window, classified."""
    if classifier_sha() != CLASSIFIER_V2_SHA256:
        raise RuntimeError("classifier v2 differs from its E60 freeze")
    from app.ml.corpus.geocoder import geocode_to_province

    seen, out = set(), []
    for path in STORES:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            a = json.loads(line)
            k = a["article_key"]
            if k in seen or not (FIRST_DATE <= (a.get("ph_date") or "")[:10] <= LAST_DATE):
                continue
            seen.add(k)
            c = classify(a.get("title") or "", geocode_to_province)
            out.append({"article_key": k, "title": (a.get("title") or "").strip(), "outlet": a.get("source_domain") or "",
                        "published_ph": a["published_ph"], "ph_date": a["ph_date"][:10], "quarter": a["quarter"],
                        "province_code": a.get("geo_province_code") if a.get("geo_province_code") in PROVINCE_CODES else None,
                        "link": a.get("link") or "", "store": path.parent.name,
                        "first_seen_at": a.get("first_seen_at"), "relevant": c["relevant"], "trigger": c["trigger"],
                        "rule": c["rule"]})
    out.sort(key=lambda a: (a["published_ph"], a["article_key"]))
    return tuple(out)


def dedupe(arts: list[dict]) -> tuple[list[dict], dict]:
    """Earliest copy of each syndication cluster (same normalised title within SYNDICATION_DAYS, any outlet)."""
    out, dropped, seen = [], {}, {}
    for a in sorted(arts, key=lambda a: (a["published_ph"], a["article_key"])):
        n = norm_title(a["title"])
        p = _ph(a)
        prev = seen.get(n)
        if prev is not None and (p - prev[0]) <= timedelta(days=SYNDICATION_DAYS):
            dropped[a["article_key"]] = prev[1]
            continue
        seen[n] = (p, a["article_key"])
        out.append(a)
    return out, dropped


@functools.lru_cache(maxsize=1)
def admitted() -> tuple[dict, ...]:
    """Relevant (classifier v2) articles, de-syndicated; province-attributed or national (province_code None)."""
    kept, _ = dedupe([a for a in corpus() if a["relevant"] == 1])
    return tuple(kept)


def asof(t: int) -> list[dict]:
    """Admitted articles of predictor quarter t published before the issue date O(t)."""
    q, O = qs(t), origin(t)
    return [a for a in admitted() if a["quarter"] == q and _ph(a) < O]


def intensity_keys() -> set[str]:
    """Model keys of the CURRENT classifier source: the LF-normalised key (app.news.scoring) and the key the same source
    received when hashed with CRLF line endings before D-E64-1 was fixed. Scores of any other classifier are excluded."""
    import app.ml.nlp.classifier as C
    from app.news.scoring import _snapshot_revision

    src = Path(C.__file__).read_bytes().replace(b"\r\n", b"\n")
    rev = _snapshot_revision(C.MODEL_NAME)[:12]
    return {f"{C.MODEL_NAME}@{rev}|clf:{hashlib.sha256(b).hexdigest()[:16]}{INTENSITY_SUFFIX}"
            for b in (src, src.replace(b"\n", b"\r\n"))}


@functools.lru_cache(maxsize=1)
def intensities() -> dict[str, float]:
    """XLM-RoBERTa intensity per article (FSSI-v2 scorer, '|v2-noguard'), from the stored score files, for the current
    classifier source only."""
    keys, out = intensity_keys(), {}
    for path in SCORES:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("model_key") in keys and r.get("status") == "OK":
                out[r["article_key"]] = float(r["score"])
    return out


def fssi_v3(province_code: str, t: int, arts: list[dict] | None = None) -> dict:
    """FSSI-v3 (Equation 2 unchanged) of a province's admitted articles in quarter t, published before O(t).
    Bias weight log(1 + median n) / log(1 + n), median over the counts of the provinces with at least one admitted
    article that quarter (as app.ml.corpus.bias_weighter). No 0.30 intensity threshold: relevance is decided by
    classifier v2, and the status, n and FSSI all describe the same articles (unlike FSSI-v2, D-E64-2)."""
    arts = asof(t) if arts is None else arts
    mine = [a for a in arts if a["province_code"] == province_code]
    n = len(mine)
    status = "SUFFICIENT" if n >= MIN_ARTICLES else "LIMITED_SIGNAL" if n else "NO_USABLE_EVIDENCE"
    if not n:
        return {"n": 0, "status": status, "fssi": None, "mean_intensity": None, "bias_weight": None, "unscored": 0}
    sc = intensities()
    vals = [sc[a["article_key"]] for a in mine if a["article_key"] in sc]
    unscored = n - len(vals)
    if unscored:
        raise RuntimeError(f"{unscored} admitted articles lack an XLM-RoBERTa intensity (run scripts/score_news_v3.py)")
    counts = [c for c in (sum(1 for a in arts if a["province_code"] == p) for p in PROVINCE_CODES) if c > 0]
    med = statistics.median(counts)
    bw = math.log1p(med) / math.log1p(n)
    mi = sum(vals) / n
    return {"n": n, "status": status, "fssi": round(bw * mi, 6), "mean_intensity": round(mi, 6), "bias_weight": round(bw, 6),
            "unscored": 0}


def n3_features(t: int) -> list[dict]:
    """The 12 N3 columns per province at origin t (PROTOCOL section 4), plus the article keys behind them."""
    arts, O = asof(t), origin(t)

    def rw(a):
        age = (O - _ph(a)).total_seconds() / 86400.0
        return math.exp(-math.log(2) * age / HALF_LIFE_DAYS)

    nat = [a for a in arts if a["province_code"] is None]
    rows = []
    for p in PROVINCE_CODES:
        mine = [a for a in arts if a["province_code"] == p]
        f = fssi_v3(p, t, arts)
        r = {"t": t, "province_code": p, "n3_cov": math.log1p(len(mine))}
        for k in PROVINCE_TRIGGERS:
            r[f"n3_{k}_rw"] = sum(rw(a) for a in mine if a["trigger"] == k)
        for k in NATIONAL_TRIGGERS:
            r[f"n3_nat_{k}_rw"] = sum(rw(a) for a in nat if a["trigger"] == k)
        r["n3_src"] = float(len({a["outlet"] for a in mine}))
        r["n3_fssi"] = f["fssi"] if f["fssi"] is not None else float("nan")
        r["fssi_status"] = f["status"]
        r["n_admitted"] = len(mine)
        r["article_keys"] = [a["article_key"] for a in mine]
        r["national_keys"] = [a["article_key"] for a in nat]
        rows.append(r)
    return rows


def feed(province_code: str | None, quarter: str, cutoff: datetime | None = None) -> list[dict]:
    """Dashboard feed rows: admitted articles of a quarter (one province, or all attributed for the region), optionally
    only those published before a cutoff, newest first."""
    rows = [a for a in admitted() if a["quarter"] == quarter and a["province_code"] is not None
            and (province_code is None or a["province_code"] == province_code)
            and (cutoff is None or _ph(a) < cutoff)]
    return sorted(rows, key=lambda a: a["published_ph"], reverse=True)
