"""E83 step N1: recover publisher lead text for every collected article (resumable; appends to leads.jsonl).

Run from backend/:  python ../aipheed-backend-aligned/experiments/E83_Deep_Reconstruction/runner/run_leads.py [limit]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / "backend"
sys.path.insert(0, str(BACKEND))
from app.news import lead_extractor as LX  # noqa: E402

OUT = BACKEND / "data" / "news_e83" / "leads.jsonl"
SOURCES = [BACKEND / "data" / "news_e31" / "articles.jsonl", BACKEND / "data" / "news_e60" / "articles.jsonl"]

# accessible publishers first, so usable leads arrive early; challenged/blocked hosts cost one probe each
ORDER = ["da.gov.ph", "bworldonline.com", "fo4a.dswd.gov.ph", "sunstar.com.ph"]


def articles() -> list[dict]:
    seen, out = set(), []
    for p in SOURCES:
        for line in p.read_text(encoding="utf-8").splitlines():
            a = json.loads(line)
            if a["article_key"] in seen:
                continue
            seen.add(a["article_key"])
            out.append({k: a[k] for k in ("article_key", "title", "source_domain", "ph_date")})
    rank = {d: i for i, d in enumerate(ORDER)}
    return sorted(out, key=lambda a: (rank.get(a["source_domain"], 99), a["ph_date"]))


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    arts = articles()
    print(f"{len(arts)} unique articles", flush=True)
    c = LX.extract(arts, OUT, limit=lim,
                   progress=lambda i, n: print(f"{i}/{n}", flush=True) if i % 50 == 0 or i == n else None)
    print(json.dumps(c), flush=True)
    allrec = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines()]
    print(Counter(r["extraction_status"] for r in allrec))
