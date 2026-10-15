"""E31 relevance validation, step C: a FRESH holdout drawn after rule R1 was frozen (git 752d587).

Population: province-attributed articles NOT in the development sample. Strata by the frozen rule's decision:
  H_R1_POS (R1 says DIRECT/INDIRECT) -> 100 sampled;  H_R1_NEG (R1 says NONE) -> 150 sampled.
Seed 3131. Blind sheet (title, outlet, date, attributed province; shuffled). Scored once by e31_relevance_eval.py
holdout. The E28 gate is evaluated on the same items (its decision is known for every article).
"""
import hashlib, json, random, sys
from pathlib import Path
sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner")); sys.path.insert(0, str(EXP / "backend_dev"))
import guard31  # noqa: E402
guard31.install()
from app.news.relevance import classify  # noqa: E402
STORE = EXP / "backend_dev" / "data" / "news_e31"
OUT = EXP / "validation" / "holdout"
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal", "PH040500000": "Batangas"}
assert hashlib.sha256((EXP / "backend_dev" / "app" / "news" / "relevance.py").read_bytes()).hexdigest().startswith("3eecde30")
jl = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
arts = {a["article_key"]: a for a in jl(STORE / "articles.jsonl")}
scores = {s["article_key"]: s for s in jl(STORE / "scores.jsonl")}
dev = {k["article_key"] for k in json.loads((EXP / "validation" / "sample_key.json").read_text())}
pos, neg = [], []
for k, a in sorted(arts.items()):
    if a.get("geo_province_code") and k not in dev:
        (pos if classify(a["title"]) != "NONE" else neg).append(k)
rng = random.Random(3131)
print("pos", len(pos), "neg", len(neg)); NPOS = min(100, len(pos))
picked = [("H_R1_POS", k) for k in rng.sample(pos, NPOS)] + [("H_R1_NEG", k) for k in rng.sample(neg, 150)]
rng.shuffle(picked)
sheet, key = [], []
for i, (st, k) in enumerate(picked, 1):
    a, s = arts[k], scores.get(k, {})
    sid = f"H{i:03d}"
    sheet.append({"id": sid, "title": a["title"], "outlet": a["source_domain"], "date": a["ph_date"],
                  "attributed_province": NAMES[a["geo_province_code"]]})
    key.append({"id": sid, "article_key": k, "stratum": st, "split": "HOLDOUT", "quarter": a["quarter"],
                "geo_province_code": a["geo_province_code"], "score": s.get("score"), "score_status": s.get("status"),
                "e28_in_fssi": bool(s.get("status") == "OK" and s.get("score", 0) >= 0.30)})
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "annotation_sheet_blind.json").write_bytes(json.dumps(sheet, indent=1, ensure_ascii=False).encode("utf-8"))
(OUT / "sample_key.json").write_bytes(json.dumps(key, indent=1).encode())
meta = {"population_by_stratum": {"H_R1_POS": len(pos), "H_R1_NEG": len(neg)},
        "sample_by_stratum": {"H_R1_POS": NPOS, "H_R1_NEG": 150}, "seed": 3131, "rule_sha256_prefix": "3eecde30",
        "excluded_dev_items": len(dev)}
(OUT / "sample_meta.json").write_bytes(json.dumps(meta, indent=1).encode())
print(json.dumps(meta))
