"""E60 step N1 (no forecasting scores): audit of the news corpus behind aiPHeed's news features.

Reports, for the store the E40-E58 features were built from (E31 backend_dev) and the backend store:
size, date range, sources and domains, collection timestamps, province attribution, title-only content, duplicates,
per-trigger keyword hit counts with the deployed TRIGGER_KEYWORDS, and province-quarter coverage.

    backend/venv/Scripts/python.exe -B runner/n1_corpus_audit.py  -> out/corpus_audit.json, out/trigger_hits_by_quarter.csv
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

E60 = Path(__file__).resolve().parents[1]
EXP = E60.parent
ROOT = EXP.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.nlp.trigger_classifier import TRIGGER_KEYWORDS  # noqa: E402  (read-only)

STORES = {"E31_backend_dev (model features)": EXP / "E31_Chapter1_Completion" / "backend_dev" / "data" / "news_e31" / "articles.jsonl",
          "backend/data/news_e31": ROOT / "backend" / "data" / "news_e31" / "articles.jsonl"}
RX = {c: [re.compile(r"\b" + re.escape(k) + r"\b", re.I) for k in kws] for c, kws in TRIGGER_KEYWORDS.items()}


def load(p):
    return pd.DataFrame([json.loads(x) for x in p.open(encoding="utf-8")])


def main():
    out = {"trigger_keyword_counts": {c: len(v) for c, v in TRIGGER_KEYWORDS.items()},
           "trigger_keywords": TRIGGER_KEYWORDS, "stores": {}}
    for name, p in STORES.items():
        if not p.exists():
            out["stores"][name] = {"exists": False}
            continue
        a = load(p)
        a = a[a["ph_date"] >= "2021-01-01"]
        for c, rx in RX.items():
            a[f"hit_{c}"] = a["title"].fillna("").map(lambda t, rx=rx: int(any(r.search(t) for r in rx)))
        geo = a["geo_province_code"].notna()
        dup_title = a["title"].str.lower().str.replace(r"\s+-\s+[^-]+$", "", regex=True).duplicated(keep=False)
        s = {"exists": True, "articles": int(len(a)), "date_min": a["ph_date"].min(), "date_max": a["ph_date"].max(),
             "collected_first": str(a["first_seen_at"].min()) if "first_seen_at" in a else None,
             "collected_last": str(a["first_seen_at"].max()) if "first_seen_at" in a else None,
             "sources": a["source"].value_counts().to_dict() if "source" in a else None,
             "top_domains": a["source_domain"].value_counts().head(15).to_dict() if "source_domain" in a else None,
             "has_body_text": bool(any(k in a.columns for k in ("text", "body", "content", "summary"))),
             "columns": sorted(a.columns.tolist()),
             "province_attributed": int(geo.sum()), "province_attributed_share": float(geo.mean()),
             "attributed_by_province": a.loc[geo, "geo_province_code"].value_counts().to_dict(),
             "near_duplicate_titles": int(dup_title.sum()),
             "trigger_hits_all": {c: int(a[f"hit_{c}"].sum()) for c in RX},
             "trigger_hits_attributed": {c: int(a.loc[geo, f"hit_{c}"].sum()) for c in RX},
             "articles_with_any_hit_attributed": int((a.loc[geo, [f"hit_{c}" for c in RX]].sum(axis=1) > 0).sum()),
             "date_kind": a["date_kind"].value_counts().to_dict() if "date_kind" in a else None}
        g = a[geo].groupby(["quarter", "geo_province_code"]).agg(n=("title", "size"), **{f"hits_{c}": (f"hit_{c}", "sum") for c in RX})
        s["province_quarters_with_articles"] = int(len(g))
        s["province_quarters_with_fewer_than_5"] = int((g["n"] < 5).sum())
        s["median_articles_per_province_quarter"] = float(g["n"].median())
        out["stores"][name] = s
        if name.startswith("E31"):
            g.reset_index().to_csv(E60 / "out" / "trigger_hits_by_quarter.csv", index=False)
            # title samples per trigger for the audit (first 8 hits each, attributed only)
            out["sample_titles"] = {c: a.loc[geo & (a[f"hit_{c}"] == 1), ["ph_date", "geo_province_code", "title"]].head(8).values.tolist()
                                    for c in RX}
            kw = Counter()
            for c, rx in RX.items():
                for k, r in zip(TRIGGER_KEYWORDS[c], rx):
                    kw[(c, k)] = int(a.loc[geo, "title"].fillna("").map(lambda t, r=r: bool(r.search(t))).sum())
            out["keywords_never_matched_attributed"] = {c: [k for k in TRIGGER_KEYWORDS[c] if kw[(c, k)] == 0] for c in RX}
            out["top_matching_keywords"] = {c: sorted(((k, kw[(c, k)]) for k in TRIGGER_KEYWORDS[c]), key=lambda x: -x[1])[:6] for c in RX}
    (E60 / "out").mkdir(exist_ok=True)
    (E60 / "out" / "corpus_audit.json").write_text(json.dumps(out, indent=1, default=str, ensure_ascii=False))
    for n, s in out["stores"].items():
        print(n, {k: v for k, v in s.items() if k not in ("columns", "top_domains", "attributed_by_province")})
    print("never matched", {c: len(v) for c, v in out["keywords_never_matched_attributed"].items()})
    print("top", out["top_matching_keywords"])


if __name__ == "__main__":
    (E60 / "out").mkdir(parents=True, exist_ok=True)
    main()
