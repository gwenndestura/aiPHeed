"""E34: independent audit of the E31 news store (2021-01-01 .. 2026-10-14).

Re-derives every check from the raw JSONL ledger with its own code. Only the frozen RULE DEFINITIONS under audit are
imported from E31 backend_dev (query plan, R1.1 relevance rule, geocoder); no E31 audit/FSSI output is reused as input.

Checks
  C1 collection ledger: every planned (query, province, month) window from 2021-01 to the authorized limit resolved to
     COMPLETE leaves (split windows followed); request errors, rate limits, cap hits, truncation
  C2 publication dates: raw pubDate -> Asia/Manila -> ph_date -> quarter recomputed; range; outside-requested-window
  C3 identity and duplicates: article_key recomputed; same link; same (domain,title) on other dates (date drift);
     syndication (same normalised title, other outlet, <= 3 days); near-duplicates (token Jaccard >= 0.9, <= 3 days)
  C4 geography: geocoder rerun vs stored code; NCR namesake / non-place patterns among attributed titles
  C5 relevance and FSSI-v2 counts: R1.1 + dedup recomputed per province-quarter vs fssi_v2_panel.csv
  C6 information cutoffs: record windows recomputed with alignment rules; every admitted article in a window checked
Writes runs/e34_news_audit.json. Run: PY -B runner/e34_news_audit.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
E31 = HERE.parent / "E31_Chapter1_Completion"
BD = E31 / "backend_dev"
STORE = BD / "data" / "news_e31"
sys.path.insert(0, str(BD))

from app.news.collector import PROVINCES, REGION, plan_for          # noqa: E402  (rule definitions under audit)
from app.news.relevance import classify_deployed                    # noqa: E402
from app.ml.corpus.geocoder import geocode_to_province               # noqa: E402

PH = timezone(timedelta(hours=8))
START = date(2021, 1, 1)
LIMIT = date(2026, 10, 14)            # authorized through (inclusive)
LIMIT_EXCL = LIMIT + timedelta(days=1)
CODE2NAME = {v: k for k, v in PROVINCES.items()}


def jl(name):
    with open(STORE / f"{name}.jsonl", encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(t: str) -> str:                      # own normaliser (publisher suffix removed, ascii, lower)
    import unicodedata
    t = t.rsplit(" - ", 1)[0] if " - " in t else t
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())


def qof(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def months():
    d = START
    while d < LIMIT_EXCL:
        n = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        yield d, n
        d = n


# ---------------------------------------------------------------- C1 ledger
def c1(windows, requests):
    W = {}
    for w in windows:                          # last record per window id wins (ledger is append-only)
        W[(w["source"], w["query_id"], w["province"], w["start"], w["end_excl"])] = w

    def leaves(qid, prov, a: date, b: date):
        w = W.get(("google_news_rss", qid, prov, a.isoformat(), b.isoformat()))
        if w is None:
            return [(a, b, "NOT_ATTEMPTED")]
        if w["status"] == "SPLIT":
            days = (b - a).days
            mid = a + timedelta(days=days // 2)
            return leaves(qid, prov, a, mid) + leaves(qid, prov, mid, b)
        return [(a, b, w["status"])]

    status, bad, planned, n_leaves = Counter(), [], 0, 0
    per_q_status = defaultdict(Counter)
    for prov in list(PROVINCES) + [REGION]:
        for spec in plan_for(prov):
            for a, b in months():
                planned += 1
                # the month window may have been queried clipped to the authorized limit (Oct 2026)
                b_eff = b
                if ("google_news_rss", spec.query_id, prov, a.isoformat(), b.isoformat()) not in W and b > LIMIT_EXCL - timedelta(days=0):
                    b_eff = LIMIT_EXCL
                lv = leaves(spec.query_id, prov, a, b_eff)
                if lv[0][2] == "NOT_ATTEMPTED" and b_eff != b:
                    lv2 = leaves(spec.query_id, prov, a, b)
                    if lv2[0][2] != "NOT_ATTEMPTED":
                        lv = lv2
                for x in lv:
                    n_leaves += 1
                    status[x[2]] += 1
                    per_q_status[qof(a)][x[2]] += 1
                    if x[2] != "COMPLETE":
                        bad.append({"query": spec.query_id, "province": prov, "start": x[0].isoformat(),
                                    "end_excl": x[1].isoformat(), "status": x[2]})
    last_end = max(date.fromisoformat(w["end_excl"]) for w in windows)
    rs = Counter(r["status"] for r in requests)
    http = Counter(str(r.get("http_status")) for r in requests)
    at_cap = sum(1 for r in requests if r.get("at_cap"))
    raw_by_q = defaultdict(int)
    for r in requests:
        if r["status"] in ("OK", "EMPTY"):
            raw_by_q[r["quarter"]] += r.get("n_raw", 0)
    rej = Counter()
    for r in requests:
        for k, v in (r.get("rejected") or {}).items():
            rej[k] += v
    return {"planned_month_windows": planned, "resolved_leaves": n_leaves, "leaf_status": dict(status),
            "non_complete_leaves": bad[:50], "n_non_complete": len(bad), "latest_window_end_excl": last_end.isoformat(),
            "requests": len(requests), "request_status": dict(rs), "http_status": dict(http),
            "requests_at_cap": at_cap, "intake_rejections": dict(rej),
            "per_quarter_leaf_status": {q: dict(c) for q, c in sorted(per_q_status.items())}}


# ---------------------------------------------------------------- C2 dates
def c2(arts):
    issues, kinds, outside, per_q = Counter(), Counter(), 0, Counter()
    examples = defaultdict(list)
    for a in arts:
        kinds[a.get("date_kind")] += 1
        raw = a.get("published_raw") or ""
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ph = dt.astimezone(PH)
        except Exception:
            issues["unparseable_raw"] += 1
            continue
        if ph.isoformat() != datetime.fromisoformat(a["published_ph"]).astimezone(PH).isoformat():
            issues["published_ph_mismatch"] += 1
            examples["published_ph_mismatch"].append(a["article_key"][:12])
        if ph.date().isoformat() != a["ph_date"]:
            issues["ph_date_mismatch"] += 1
        if qof(ph.date()) != a["quarter"]:
            issues["quarter_mismatch"] += 1
        if ph.date() < START:
            issues["before_2021"] += 1
        if ph.date() > LIMIT:
            issues["after_limit"] += 1
            examples["after_limit"].append(a["ph_date"])
        if a.get("outside_requested_window"):
            outside += 1
        per_q[a["quarter"]] += 1
    return {"articles": len(arts), "date_kind": dict(kinds), "issues": dict(issues),
            "examples": {k: v[:5] for k, v in examples.items()},
            "outside_requested_window": outside, "articles_per_quarter": dict(sorted(per_q.items())),
            "min_date": min(a["ph_date"] for a in arts), "max_date": max(a["ph_date"] for a in arts)}


# ---------------------------------------------------------------- C3 identity / duplicates
def c3(arts):
    def akey(a):
        t = a["title"]
        import unicodedata
        n = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().casefold()
        n = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", n)).strip()
        return hashlib.sha256(f"{(a['source_domain'] or '').lower()}|{n}|{a['ph_date']}".encode()).hexdigest()

    key_mismatch = sum(1 for a in arts if akey(a) != a["article_key"])
    keys = Counter(a["article_key"] for a in arts)
    links = Counter(a["link"] for a in arts)
    by_dt = defaultdict(set)
    for a in arts:
        by_dt[(a["source_domain"], norm(a["title"]))].add(a["ph_date"])
    drift = {k: sorted(v) for k, v in by_dt.items() if len(v) > 1}
    drift_close = sum(1 for v in drift.values()
                      if min((date.fromisoformat(y) - date.fromisoformat(x)).days for x, y in zip(v, v[1:])) <= 3)
    # syndication / near duplicates across outlets within 3 days
    srt = sorted(arts, key=lambda a: a["published_ph"])
    by_title = defaultdict(list)
    for a in srt:
        by_title[norm(a["title"])].append(a)
    synd = 0
    synd_ex = []
    for n, g in by_title.items():
        if len(n) < 15:
            continue
        for i in range(1, len(g)):
            d = (datetime.fromisoformat(g[i]["published_ph"]) - datetime.fromisoformat(g[0]["published_ph"])).days
            if g[i]["source_domain"] != g[0]["source_domain"] and d <= 3:
                synd += 1
                if len(synd_ex) < 5:
                    synd_ex.append([g[0]["title"][:90], g[0]["source_domain"], g[i]["source_domain"]])
    tok = [(datetime.fromisoformat(a["published_ph"]), set(norm(a["title"]).split()), a) for a in srt]
    near, near_ex = 0, []
    for i in range(len(tok)):
        ti, si, ai = tok[i]
        if len(si) < 5:
            continue
        for j in range(i + 1, len(tok)):
            tj, sj, aj = tok[j]
            if (tj - ti).days > 3:
                break
            if len(sj) < 5 or norm(ai["title"]) == norm(aj["title"]):
                continue
            jac = len(si & sj) / len(si | sj)
            if jac >= 0.9:
                near += 1
                if len(near_ex) < 8:
                    near_ex.append([ai["title"][:90], aj["title"][:90], round(jac, 3)])
    return {"article_key_recompute_mismatch": key_mismatch, "duplicate_article_keys": sum(v - 1 for v in keys.values() if v > 1),
            "duplicate_links": sum(v - 1 for v in links.values() if v > 1),
            "same_outlet_title_on_several_dates": len(drift), "of_which_within_3_days": drift_close,
            "date_drift_examples": [[k[0], k[1][:80], v] for k, v in list(drift.items())[:6]],
            "cross_outlet_same_title_within_3_days": synd, "syndication_examples": synd_ex,
            "near_duplicate_pairs_jaccard_ge_0.9_within_3_days": near, "near_duplicate_examples": near_ex}


# ---------------------------------------------------------------- C4 geography
RISKY = {
    "quezon_city": r"quezon city|\bq\.?c\.?\b", "jose_rizal": r"jose rizal|rizal memorial|rizal park|rizal day",
    "manuel_quezon": r"manuel (?:l\. )?quezon|president quezon", "laguna_lake": r"laguna (?:lake|de bay)",
    "quezon_film_or_person": r"\"quezon\"|quezon(?:'s)? (?:film|movie)", "rizal_avenue_or_street": r"rizal (?:avenue|ave|st|street)",
}


def c4(arts):
    mism, attributed, by_code = [], 0, Counter()
    risky = Counter()
    risky_ex = defaultdict(list)
    for a in arts:
        g = geocode_to_province(a["title"])
        if g != a.get("geo_province_code"):
            mism.append([a["title"][:90], a.get("geo_province_code"), g])
        if a.get("geo_province_code"):
            attributed += 1
            by_code[CODE2NAME.get(a["geo_province_code"], a["geo_province_code"])] += 1
            tl = a["title"].lower()
            for k, rx in RISKY.items():
                if re.search(rx, tl):
                    risky[k] += 1
                    if len(risky_ex[k]) < 4:
                        risky_ex[k].append([a["title"][:100], CODE2NAME.get(a["geo_province_code"])])
    return {"attributed": attributed, "by_province": dict(by_code), "geocoder_rerun_mismatches": len(mism),
            "mismatch_examples": mism[:8], "risky_pattern_counts_among_attributed": dict(risky),
            "risky_examples": dict(risky_ex)}


# ---------------------------------------------------------------- C5 relevance / FSSI counts
def c5(arts):
    cnt = defaultdict(lambda: Counter())
    admitted = []
    for a in arts:
        c = a.get("geo_province_code")
        if not c:
            continue
        cls = classify_deployed(a["title"])
        cnt[(CODE2NAME[c], a["quarter"])]["attributed"] += 1
        if cls in ("DIRECT", "INDIRECT"):
            admitted.append((a, cls))
    # own syndication dedup: same normalised title within 3 days -> keep earliest
    admitted.sort(key=lambda x: (x[0]["published_ph"], x[0]["article_key"]))
    seen, kept, dropped = {}, [], 0
    for a, cls in admitted:
        n = norm(a["title"])
        p = datetime.fromisoformat(a["published_ph"])
        if n in seen and (p - seen[n]) <= timedelta(days=3):
            dropped += 1
            continue
        seen[n] = p
        kept.append((a, cls))
    for a, cls in kept:
        k = (CODE2NAME[a["geo_province_code"]], a["quarter"])
        cnt[k]["admitted"] += 1
        cnt[k][cls.lower()] += 1
    panel = {}
    with open(STORE / "fssi_v2_panel.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            panel[(r["province"], r["quarter"])] = r
    diffs = []
    for k, r in panel.items():
        c = cnt.get(k, Counter())
        for col, mine in (("n_province_attributed", c["attributed"]), ("n_admitted", c["admitted"]),
                          ("n_direct", c["direct"]), ("n_indirect", c["indirect"])):
            if int(r[col]) != mine:
                diffs.append([k[0], k[1], col, int(r[col]), mine])
    suff = Counter("SUFFICIENT" if c["admitted"] >= 5 else ("LIMITED_SIGNAL" if c["admitted"] else "NO_USABLE_EVIDENCE")
                   for k, c in ((k, cnt.get(k, Counter())) for k in panel))
    per_year = Counter()
    for a, _ in kept:
        per_year[a["quarter"][:4]] += 1
    return {"admitted_recomputed": len(kept), "syndicated_dropped": dropped, "panel_rows": len(panel),
            "panel_count_differences": diffs[:20], "n_panel_count_differences": len(diffs),
            "evidence_status_recomputed": dict(suff), "admitted_per_year": dict(sorted(per_year.items())),
            "kept_keys": sorted(a["article_key"] for a, _ in kept)}


# ---------------------------------------------------------------- C6 cutoffs
def c6(arts, kept_keys):
    rec = json.loads((BD / "data" / "e31" / "e31_record.json").read_text(encoding="utf-8"))
    from app.news.alignment import evidence_window           # rule under audit; windows recomputed from it
    out = {}
    A = {a["article_key"]: a for a in arts}
    for name, w in rec["news"]["windows"].items():
        lead = w["lead"]
        ew = evidence_window(w["target_quarter"], w["mode"], w["information_cutoff_ph"], lead=lead,
                             authorized_limit_excl=datetime(2026, 10, 15, tzinfo=PH))
        same = (ew.evidence_quarter == w["evidence_quarter"] and ew.window_end_excl_ph == w["window_end_excl_ph"]
                and ew.window_start_ph == w["window_start_ph"])
        used = [A[k] for k in kept_keys if A[k]["quarter"] == ew.evidence_quarter]
        late = [a["article_key"][:12] for a in used
                if datetime.fromisoformat(a["published_ph"]) > datetime.fromisoformat(w["information_cutoff_ph"])]
        early = [a["article_key"][:12] for a in used
                 if datetime.fromisoformat(a["published_ph"]) < datetime.fromisoformat(w["window_start_ph"])]
        target_q_in_forecast = (w["mode"] == "forecast" and ew.evidence_quarter == w["target_quarter"])
        out[name] = {"recomputed_window_matches_record": same, "admitted_articles_in_window": len(used),
                     "after_cutoff": late, "before_window": early, "forecast_uses_target_quarter": target_q_in_forecast}
    # the record's article list: every listed article inside the store, date-consistent
    listed = rec["news"]["articles"]
    missing = [x["article_key"][:12] for x in listed if x["article_key"] not in A]
    after = [x["article_key"][:12] for x in listed if x["published_ph"][:10] > LIMIT.isoformat()]
    return {"windows": out, "record_articles": len(listed), "record_articles_not_in_store": missing,
            "record_articles_after_limit": after}


def main():
    arts, req, win = jl("articles"), jl("requests"), jl("windows")
    res = {"experiment": "E34", "generated_at": datetime.now(PH).isoformat(), "store": str(STORE.relative_to(HERE.parent)),
           "input_sha256": {f: sha_file(STORE / f"{f}.jsonl") for f in ("articles", "requests", "windows", "scores")}
           | {"fssi_v2_panel.csv": sha_file(STORE / "fssi_v2_panel.csv")},
           "authorized_through": LIMIT.isoformat()}
    res["C1_ledger"] = c1(win, req)
    res["C2_dates"] = c2(arts)
    res["C3_duplicates"] = c3(arts)
    res["C4_geography"] = c4(arts)
    r5 = c5(arts)
    kept = r5.pop("kept_keys")
    res["C5_relevance_fssi"] = r5
    res["C5_relevance_fssi"]["admitted_keys_sha256"] = hashlib.sha256(json.dumps(kept).encode()).hexdigest()
    res["C6_cutoffs"] = c6(arts, kept)
    out = HERE / "runs" / "e34_news_audit.json"
    out.write_bytes(json.dumps(res, indent=1, ensure_ascii=False).encode("utf-8"))
    print(json.dumps({k: (v if k in ("C2_dates",) else v) for k, v in res.items() if k.startswith("C")}, indent=1,
                     ensure_ascii=False)[:9000])


if __name__ == "__main__":
    main()
