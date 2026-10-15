"""E29 D8 shadow test: what would source policy v2 add to the E28 corpus and FSSI?

1. Windows: every (province, query, month) window in which the E28 backfill refused an item from a domain that v2
   would admit (E28 rejected.jsonl stores the domain, query, province and window, never the text).
2. Those windows are re-queried live (Google News RSS) with a credible function that admits ONLY the v2 additions, into
   a separate shadow store (backend_dev/data/news_e29_policy_v2_shadow). The E28 store is not touched.
3. The new items are scored with the unchanged XLM-RoBERTa scorer.
4. A merged copy (E28 + shadow) is built in backend_dev/data/news_e29_policy_v2_merged and its FSSI compared with
   E28's. Note: today's index may differ slightly from E28's run for the same windows; the comparison counts only the
   v2-admitted items, so v1 items are identical by construction.
python -B runner/e29_allowlist_shadow.py [collect|score|compare|all]  ->  runs/e29_allowlist_v2_effect.json
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard29  # noqa: E402

guard29.install()
EXP = guard29.EXP
BD = EXP / "backend_dev"
sys.path.insert(0, str(BD))
from app.news.collector import PROVINCE_QUERIES, REGION_QUERIES, Collector, all_quarters  # noqa: E402
from app.news.policy import additions_only_fn  # noqa: E402
from app.news.sources import GoogleNewsRSS  # noqa: E402
from app.news.store import NewsStore  # noqa: E402
from app.news.timeutil import quarter_of_date  # noqa: E402

E28S = BD / "data" / "news_e28"
SHADOW = BD / "data" / "news_e29_policy_v2_shadow"
MERGED = BD / "data" / "news_e29_policy_v2_merged"


def windows():
    add = additions_only_fn("v2")
    rej = [json.loads(l) for l in (E28S / "rejected.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    w = sorted({(r["province"], r["query_id"], r["window_start"]) for r in rej
                if r["reason"] == "NON_CREDIBLE_SOURCE" and add(r.get("source_domain", ""))})
    return w


def collect():
    store = NewsStore(SHADOW)
    col = Collector(store, [GoogleNewsRSS()], authorized_until="2026-Q2", credible=additions_only_fn("v2"))
    col.run_id = "e29_policy_v2_shadow"
    specs = {s.query_id: s for s in PROVINCE_QUERIES + REGION_QUERIES}
    store.log_run({"event": "start", "run_id": col.run_id, "mode": "policy_v2_shadow", "windows": len(windows())})
    n = 0
    for prov, qid, ws in windows():
        a = date.fromisoformat(ws)
        b = date(a.year + 1, 1, 1) if a.month == 12 else date(a.year, a.month + 1, 1)
        col._window(col.sources[0], specs[qid], prov, quarter_of_date(a), a, b)
        n += 1
    store.log_run({"event": "end", "run_id": col.run_id, "status": "COMPLETED", "requests": col.requests_made,
                   "windows": n, "ended_at": __import__("datetime").datetime.now().isoformat()})
    return {"windows": n, "requests": col.requests_made, "articles": len(store.articles)}


def score():
    from app.news.scoring import score_pending

    return score_pending(NewsStore(SHADOW))


def compare():
    from app.news.fssi import build_fssi

    if MERGED.exists():
        shutil.rmtree(MERGED)
    MERGED.mkdir(parents=True)
    for name in ("articles", "scores"):
        a = (E28S / f"{name}.jsonl").read_text(encoding="utf-8")
        b = (SHADOW / f"{name}.jsonl").read_text(encoding="utf-8") if (SHADOW / f"{name}.jsonl").exists() else ""
        (MERGED / f"{name}.jsonl").write_bytes((a + b).encode("utf-8"))
    qs = all_quarters("2026-Q2")
    base = build_fssi(NewsStore(E28S), qs, write=False)
    v2 = build_fssi(NewsStore(MERGED), qs, write=False)
    pb, pv = base["panel"].set_index(["province", "quarter"]), v2["panel"].set_index(["province", "quarter"])
    changes = []
    for k in pb.index:
        x, y = pb.loc[k], pv.loc[k]
        if x["n_in_fssi"] != y["n_in_fssi"] or x["evidence_status"] != y["evidence_status"]:
            changes.append({"province": k[0], "quarter": k[1], "n_in_fssi_v1": int(x["n_in_fssi"]),
                            "n_in_fssi_v2": int(y["n_in_fssi"]), "status_v1": x["evidence_status"],
                            "status_v2": y["evidence_status"], "FSSI_v1": x["FSSI"], "FSSI_v2": y["FSSI"]})
    sh = NewsStore(SHADOW)
    import collections

    out = {"shadow_articles": len(sh.articles),
           "shadow_by_domain": dict(collections.Counter(a["source_domain"] for a in sh.articles.values()).most_common()),
           "shadow_title_geocoded": sum(1 for a in sh.articles.values() if a["geo_province_code"]),
           "evidence_status_v1": base["summary"]["evidence_status_counts"],
           "evidence_status_v2": v2["summary"]["evidence_status_counts"],
           "articles_in_fssi_v1": int(base["panel"]["n_in_fssi"].sum()),
           "articles_in_fssi_v2": int(v2["panel"]["n_in_fssi"].sum()),
           "province_quarters_changed": changes,
           "v1_panel_sha256": base["summary"]["panel_sha256"], "v2_panel_sha256": v2["summary"]["panel_sha256"],
           "status": "SHADOW ONLY: policy v2 is not active (D8 pending); the E28 FSSI is unchanged"}
    (EXP / "runs" / "e29_allowlist_v2_effect.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = {}
    if step in ("collect", "all"):
        res["collect"] = collect()
    if step in ("score", "all"):
        res["score"] = score()
    if step in ("compare", "all"):
        res["compare"] = compare()
    print(json.dumps(res, indent=1, default=str))
