"""
Province-quarter coverage audit, missing-window finder and operational status view (E28).

Collection status (was the news looked for?) and evidence sufficiency (did it find enough to compute an FSSI?) are
kept apart, and neither is a risk statement. Zero retrieved articles never means zero food insecurity.

collection_status
    NOT_ATTEMPTED   no request was made for any planned window of the province-quarter
    FAILED          requests were made but none succeeded
    PARTIAL         some planned window is unattempted, failed, rate-limited, malformed, still open, or was truncated
                    at the one-day minimum
    COMPLETE        every planned window of every query was answered (OK or EMPTY) without truncation
evidence_status (articles title-geocoded to the province, scored, and at/above the 0.30 relevance threshold)
    SUFFICIENT              >= 5 (bias_weighter.DATA_SUFFICIENCY_MIN_ARTICLES)
    LIMITED_SIGNAL          1-4
    NO_USABLE_EVIDENCE      0
    SCORING_INCOMPLETE      some attributable article is unscored or failed scoring
coverage_status (the single label the dashboard shows)
    COMPLETE                        collection COMPLETE and evidence SUFFICIENT
    COMPLETE_LIMITED_EVIDENCE       collection COMPLETE, evidence LIMITED_SIGNAL
    COMPLETE_NO_USABLE_EVIDENCE     collection COMPLETE, nothing usable (a quiet or unattributable period)
    PARTIALLY_COVERED               collection PARTIAL or scoring incomplete
    NO_USABLE_EVIDENCE_COLLECTION_FAILED / NOT_ATTEMPTED
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from app.news.collector import PROVINCES, REGION, plan_for
from app.news.store import NewsStore, window_id
from app.news.timeutil import month_windows, quarter_end_excl, quarter_start, split_window

MIN_ARTICLES = 5
LEAF_OK = ("COMPLETE",)
NOTE_ZERO = ("Zero retrieved or retained articles is a statement about news coverage, never evidence of zero food "
             "insecurity or zero food-related concern.")


def resolve_leaves(store: NewsStore, source: str, qid: str, prov: str, a: date, b: date) -> list[tuple[date, date, str]]:
    w = store.windows.get(window_id(source, qid, prov, a.isoformat(), b.isoformat()))
    if w is None:
        return [(a, b, "NOT_ATTEMPTED")]
    if w["status"] == "SPLIT":
        h = split_window(a, b)
        return resolve_leaves(store, source, qid, prov, *h[0]) + resolve_leaves(store, source, qid, prov, *h[1])
    return [(a, b, w["status"])]


def _sources(store: NewsStore) -> list[str]:
    s = sorted({w["source"] for w in store.windows.values()})
    return s or ["google_news_rss"]


def _days(a: date, b: date) -> int:
    return (b - a).days


def missing_windows(store: NewsStore, quarters: list[str], sources: list[str] | None = None) -> list[dict]:
    out = []
    for src in sources or _sources(store):
        for q in quarters:
            for p in list(PROVINCES) + [REGION]:
                for spec in plan_for(p):
                    for a, b in month_windows(q):
                        for x, y, st in resolve_leaves(store, src, spec.query_id, p, a, b):
                            if st not in LEAF_OK and st != "TRUNCATED_AT_MIN_WINDOW":
                                out.append({"source": src, "province": p, "quarter": q, "query_id": spec.query_id,
                                            "start": x.isoformat(), "end_excl": y.isoformat(), "status": st})
    return out


def _latest_scores(store: NewsStore, model_key: str | None) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for r in store.read("scores"):
        if model_key and r.get("model_key") != model_key:
            continue
        prev = best.get(r["article_key"])
        if prev is None or (prev["status"] == "FAILED" and r["status"] != "FAILED"):
            best[r["article_key"]] = r
    return best


def coverage_audit(store: NewsStore, quarters: list[str], model_key: str | None = None,
                   threshold: float = 0.30) -> list[dict]:
    if model_key is None:
        try:
            from app.news.scoring import current_model_key

            model_key = current_model_key()
        except Exception:
            model_key = None
    scores = _latest_scores(store, model_key)
    reqs = store.read("requests")
    rej = store.read("rejected")
    sight = store.read("sightings")
    arts = store.articles
    srcs = _sources(store)

    req_by = defaultdict(list)
    for r in reqs:
        req_by[(r["province"], r["quarter"])].append(r)
    rej_by = defaultdict(Counter)
    for r in rej:
        try:
            q = f"{r['window_start'][:4]}-Q{(int(r['window_start'][5:7]) - 1) // 3 + 1}"
        except Exception:
            q = "?"
        rej_by[(r["province"], q)][r["reason"]] += 1
    sight_by = defaultdict(list)
    for s in sight:
        a = arts.get(s["article_key"])
        if a is not None:
            sight_by[(s["province"], a["quarter"])].append(s["article_key"])
    code_to_name = {v: k for k, v in PROVINCES.items()}
    geo_by = defaultdict(list)
    for a in arts.values():
        if a.get("geo_province_code") in code_to_name:
            geo_by[(code_to_name[a["geo_province_code"]], a["quarter"])].append(a)

    rows = []
    for q in quarters:
        qa, qb = quarter_start(q), quarter_end_excl(q)
        for p in list(PROVINCES) + [REGION]:
            rq = req_by.get((p, q), [])
            st_counts = Counter(r["status"] for r in rq)
            leaves = []
            per_query_cov = {}
            for src in srcs:
                for spec in plan_for(p):
                    lv = []
                    for a, b in month_windows(q):
                        lv += resolve_leaves(store, src, spec.query_id, p, a, b)
                    leaves += lv
                    per_query_cov[f"{src}:{spec.query_id}"] = round(
                        sum(_days(x, y) for x, y, s in lv if s in LEAF_OK or s == "TRUNCATED_AT_MIN_WINDOW")
                        / _days(qa, qb), 4)
            leaf_st = Counter(s for _, _, s in leaves)
            if not rq:
                coll = "NOT_ATTEMPTED"
            elif not any(r["status"] in ("OK", "EMPTY") for r in rq):
                coll = "FAILED"
            elif all(s in LEAF_OK for s in leaf_st.elements()):
                coll = "COMPLETE"
            else:
                coll = "PARTIAL"
            keys_via = sight_by.get((p, q), [])
            row = {
                "province": p, "province_code": PROVINCES.get(p), "quarter": q,
                "collection_attempted": bool(rq),
                "sources_queried": sorted({r["source"] for r in rq}),
                "queries_planned": [s.query_id for s in plan_for(p)],
                "first_request_utc": min((r["requested_at"] for r in rq), default=None),
                "last_request_utc": max((r["completed_at"] for r in rq), default=None),
                "query_date_range": [qa.isoformat(), (qb - timedelta(days=1)).isoformat()],
                "date_coverage_by_query": per_query_cov,
                "requests": len(rq), "request_status_counts": dict(st_counts),
                "leaf_window_status_counts": dict(leaf_st),
                "failed_requests": st_counts.get("FAILED", 0) + st_counts.get("RATE_LIMITED", 0),
                "empty_results": st_counts.get("EMPTY", 0),
                "malformed_responses": st_counts.get("MALFORMED_RESPONSE", 0),
                "windows_truncated_at_minimum": leaf_st.get("TRUNCATED_AT_MIN_WINDOW", 0),
                "discovered": sum(int(r.get("n_raw") or 0) for r in rq),
                "rejected_at_intake": dict(rej_by.get((p, q), {})),
                "retrieved_unique_via_province_queries": len(set(keys_via)),
                "duplicate_sightings_via_province_queries": len(keys_via) - len(set(keys_via)),
                "collection_status": coll,
                "note": NOTE_ZERO,
            }
            if p != REGION:
                g = geo_by.get((p, q), [])
                sc = [scores.get(a["article_key"]) for a in g]
                n_ok = sum(1 for s in sc if s and s["status"] in ("OK", "NO_FOOD_NEXUS"))
                n_fail = sum(1 for s in sc if s and s["status"] == "FAILED")
                n_uns = sum(1 for s in sc if s is None)
                in_fssi = sum(1 for s in sc if s and s["status"] == "OK" and s["score"] >= threshold)
                dates = sorted({a["ph_date"] for a in g})
                if n_fail or n_uns:
                    ev = "SCORING_INCOMPLETE"
                elif in_fssi >= MIN_ARTICLES:
                    ev = "SUFFICIENT"
                elif in_fssi > 0:
                    ev = "LIMITED_SIGNAL"
                else:
                    ev = "NO_USABLE_EVIDENCE"
                row.update({
                    "retained_title_geocoded": len(g),
                    "query_matched_any_geocode": len(set(keys_via)),
                    "scored": n_ok, "scoring_failed": n_fail, "unscored": n_uns,
                    "included_in_fssi": in_fssi,
                    "publication_days_with_articles": len(dates),
                    "publication_date_min": dates[0] if dates else None,
                    "publication_date_max": dates[-1] if dates else None,
                    "evidence_status": ev,
                })
                if coll == "NOT_ATTEMPTED":
                    cs = "NOT_ATTEMPTED"
                elif coll == "FAILED":
                    cs = "NO_USABLE_EVIDENCE_COLLECTION_FAILED"
                elif coll == "PARTIAL" or ev == "SCORING_INCOMPLETE":
                    cs = "PARTIALLY_COVERED"
                elif ev == "SUFFICIENT":
                    cs = "COMPLETE"
                elif ev == "LIMITED_SIGNAL":
                    cs = "COMPLETE_LIMITED_EVIDENCE"
                else:
                    cs = "COMPLETE_NO_USABLE_EVIDENCE"
                row["coverage_status"] = cs
            rows.append(row)
    return rows


def status_view(store: NewsStore, authorized_until: str, stale_after_days: int = 7,
                now: datetime | None = None) -> dict:
    runs = store.read("runs")
    ends = [r for r in runs if r.get("event") == "end"]
    starts = {r["run_id"]: r for r in runs if r.get("event") == "start"}
    now = now or datetime.now(timezone.utc)
    last_ok = max((r["ended_at"] for r in ends if r["status"] == "COMPLETED"), default=None)
    stale = last_ok is None or (now - datetime.fromisoformat(last_ok)) > timedelta(days=stale_after_days)
    wst = Counter(w["status"] for w in store.windows.values())
    unfinished = [r["run_id"] for r in starts.values() if r["run_id"] not in {e["run_id"] for e in ends}]
    return {
        "authorized_until": authorized_until,
        "runs": [{"run_id": e["run_id"], "mode": starts.get(e["run_id"], {}).get("mode"), "status": e["status"],
                  "requests": e.get("requests"), "ended_at": e["ended_at"]} for e in ends[-10:]],
        "runs_without_end_record": unfinished,
        "last_completed_run_utc": last_ok,
        "stale": stale,
        "window_status_counts": dict(wst),
        "failed_or_open_windows": [w["window_id"] for w in store.windows.values()
                                   if w["status"] in ("FAILED", "RATE_LIMITED", "MALFORMED_RESPONSE", "OPEN")][:200],
        "torn_lines": store.torn_lines,
        "articles": len(store.articles),
    }
