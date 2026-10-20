"""
scripts/score_news_v3.py
------------------------
E64: XLM-RoBERTa-large-XNLI intensity for every admitted (classifier v2, de-syndicated, province-attributed) article of
the v3 corpus that has no '|v2-noguard' score yet. Same scorer and model key as FSSI-v2 (app.news.fssi_v2.score_admitted);
appends to data/news_v3/scores.jsonl (never rewrites data/news_e31).

    cd backend && venv/Scripts/python.exe -B scripts/score_news_v3.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.ml.nlp.classifier as C  # noqa: E402
from app.news import pipeline_v3 as P  # noqa: E402
from app.news.fssi_v2 import v2_model_key  # noqa: E402


def main():
    mk = v2_model_key()
    have = P.intensities()
    todo = [a for a in P.admitted() if a["province_code"] and a["article_key"] not in have]
    out = P.DATA / "news_v3" / "scores.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"model {mk}; to score {len(todo)}", flush=True)
    if not todo:
        return
    clf = C.load_classifier()
    if not isinstance(clf, C._XLMRobertaClassifier):
        raise SystemExit("XLM-RoBERTa unavailable; refusing the keyword fallback")
    with out.open("a", encoding="utf-8", newline="\n") as fh:
        for i, a in enumerate(todo, 1):
            raw = clf.classify(C.clean_text(a["title"], "", limit=C.PREMISE_CHARS))
            s = {r["topic_id"]: r["score"] for r in raw}
            top = max(s, key=lambda k: s[k])
            rec = {"article_key": a["article_key"], "model_key": mk, "scored_at": datetime.now().astimezone().isoformat(),
                   "status": "OK", "score": round(s[top], 4), "top_hypothesis": top,
                   "all_scores": {k: round(v, 4) for k, v in s.items()}}
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            if i % 25 == 0:
                print(f"{i}/{len(todo)}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
