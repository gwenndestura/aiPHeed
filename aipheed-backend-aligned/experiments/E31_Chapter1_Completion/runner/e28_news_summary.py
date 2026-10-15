"""Summarise the E28 news store and coverage audit for the report.  -> runs/e28_news_summary.json + .md"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
EXP = guard28.EXP
S = EXP / "backend_dev" / "data" / "news_e28"


def rd(n):
    return [json.loads(l) for l in (S / f"{n}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


arts, reqs, rej, scores = rd("articles"), rd("requests"), rd("rejected"), rd("scores")
cov = json.loads((S / "coverage_audit.json").read_text(encoding="utf-8"))
sc = {s["article_key"]: s for s in scores}
out = {"articles": len(arts), "requests": len(reqs), "request_status": dict(Counter(r["status"] for r in reqs)),
       "requests_retried": sum(r["attempts"] > 1 for r in reqs), "windows_at_cap": sum(r["at_cap"] for r in reqs),
       "rejected": dict(Counter(r["reason"] for r in rej)),
       "title_geocoded": sum(1 for a in arts if a["geo_province_code"]),
       "scored": len(sc), "score_status": dict(Counter(s["status"] for s in sc.values())),
       "ok_at_or_above_0.30": sum(1 for s in sc.values() if s["status"] == "OK" and s["score"] >= 0.30),
       "languages_queried": ["en", "fil"], "sources": sorted({r["source"] for r in reqs}),
       "first_request": min(r["requested_at"] for r in reqs), "last_request": max(r["completed_at"] for r in reqs)}
rows = []
for q in sorted({r["quarter"] for r in cov}):
    c = [r for r in cov if r["quarter"] == q and r["province"] != "REGION"]
    rows.append({"quarter": q, "requests": sum(r["requests"] for r in cov if r["quarter"] == q),
                 "articles_published_in_q": sum(1 for a in arts if a["quarter"] == q),
                 "title_geocoded": sum(r["retained_title_geocoded"] for r in c),
                 "in_fssi": sum(r["included_in_fssi"] for r in c),
                 "status": dict(Counter(r["coverage_status"] for r in c)),
                 "collection": dict(Counter(r["collection_status"] for r in c))})
out["by_quarter"] = rows
prov = {}
for p in ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal"):
    c = [r for r in cov if r["province"] == p]
    prov[p] = {"title_geocoded": sum(r["retained_title_geocoded"] for r in c), "in_fssi": sum(r["included_in_fssi"] for r in c),
               "quarters_limited": sum(r["coverage_status"] == "COMPLETE_LIMITED_EVIDENCE" for r in c),
               "quarters_no_usable": sum(r["coverage_status"] == "COMPLETE_NO_USABLE_EVIDENCE" for r in c)}
out["by_province"] = prov
(EXP / "runs" / "e28_news_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
md = ["| Quarter | Requests | Articles published in quarter | Title-geocoded (5 prov.) | In FSSI (≥ 0.30) | Coverage status (5 provinces) |",
      "|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['quarter']} | {r['requests']} | {r['articles_published_in_q']} | {r['title_geocoded']} | {r['in_fssi']} | "
              + ", ".join(f"{k.replace('COMPLETE_', '').lower()} {v}" for k, v in r["status"].items()) + " |")
(EXP / "runs" / "e28_news_by_quarter.md").write_text("\n".join(md), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "by_quarter"}, indent=1))
print("\n".join(md))
