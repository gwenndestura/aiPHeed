"""E31 news relevance validation, step A: draw the review sample and write a BLIND annotation sheet.

Population: the E31 news store (Google News RSS titles, 2021-Q1..2026-10-14), after XLM-R scoring.
Strata (by what the current pipeline did with the article):
  S1_IN_FSSI     province-attributed, XLM-R max-entailment >= 0.30          -> all
  S2_BELOW_THR   province-attributed, scored, < 0.30                         -> 80 sampled
  S3_NO_NEXUS    province-attributed, rejected by the food-nexus guard       -> 140 sampled
  S4_NOT_GEO     not attributed to a province by the title geocoder          -> 80 sampled
Seeded (31). Each sampled item is assigned to the DEV or TEST half by a hash of its key: thresholds and rules may be
chosen on DEV only; TEST is scored once.
The annotation sheet shows only title, outlet, date and the attributed province, in shuffled order (no score, no
stratum), so the labels are not influenced by the classifier. The key file links sheet ids back to strata.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
import guard31  # noqa: E402

guard31.install()

STORE = EXP / "backend_dev" / "data" / "news_e31"
OUT = EXP / "validation"
SIZES = {"S2_BELOW_THR": 80, "S3_NO_NEXUS": 140, "S4_NOT_GEO": 80}
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    arts = {a["article_key"]: a for a in jl(STORE / "articles.jsonl")}
    scores = {}
    for s in jl(STORE / "scores.jsonl"):
        scores[s["article_key"]] = s            # latest wins (append-only store)
    strata = {"S1_IN_FSSI": [], "S2_BELOW_THR": [], "S3_NO_NEXUS": [], "S4_NOT_GEO": []}
    for k, a in sorted(arts.items()):
        g = a.get("geo_province_code")
        if not g:
            strata["S4_NOT_GEO"].append(k)
            continue
        s = scores.get(k)
        if s is None:
            raise SystemExit(f"unscored province-attributed article {k}: run news_cli score first")
        if s["status"] == "NO_FOOD_NEXUS":
            strata["S3_NO_NEXUS"].append(k)
        elif s["status"] == "OK" and s["score"] >= 0.30:
            strata["S1_IN_FSSI"].append(k)
        elif s["status"] == "OK":
            strata["S2_BELOW_THR"].append(k)
    rng = random.Random(31)
    picked = []
    for st, keys in strata.items():
        take = keys if st == "S1_IN_FSSI" else rng.sample(keys, min(SIZES[st], len(keys)))
        picked += [(st, k) for k in take]
    rng.shuffle(picked)
    sheet, key = [], []
    for i, (st, k) in enumerate(picked, 1):
        a = arts[k]
        sid = f"R{i:03d}"
        split = "DEV" if int(hashlib.sha256(k.encode()).hexdigest(), 16) % 2 == 0 else "TEST"
        sheet.append({"id": sid, "title": a["title"], "outlet": a["source_domain"], "date": a["ph_date"],
                      "attributed_province": NAMES.get(a.get("geo_province_code"), "(none)")})
        s = scores.get(k, {})
        key.append({"id": sid, "article_key": k, "stratum": st, "split": split, "quarter": a["quarter"],
                    "geo_province_code": a.get("geo_province_code"), "score": s.get("score"),
                    "score_status": s.get("status"), "top_hypothesis": s.get("top_hypothesis"),
                    "first_query_id": a.get("first_query_id"), "first_query_province": a.get("first_query_province")})
    OUT.mkdir(exist_ok=True)
    (OUT / "annotation_sheet_blind.json").write_bytes(json.dumps(sheet, indent=1, ensure_ascii=False).encode("utf-8"))
    (OUT / "sample_key.json").write_bytes(json.dumps(key, indent=1).encode("utf-8"))
    pop = {k: len(v) for k, v in strata.items()}
    meta = {"population_by_stratum": pop, "sample_by_stratum": {st: sum(1 for s, _ in picked if s == st) for st in strata},
            "seed": 31, "articles_jsonl_sha256": hashlib.sha256((STORE / "articles.jsonl").read_bytes()).hexdigest(),
            "scores_jsonl_sha256": hashlib.sha256((STORE / "scores.jsonl").read_bytes()).hexdigest()}
    (OUT / "sample_meta.json").write_bytes(json.dumps(meta, indent=1).encode())
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
