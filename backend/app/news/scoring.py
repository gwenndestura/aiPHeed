"""
XLM-RoBERTa scoring of stored articles (E28), using the project's approved classifier unchanged
(app.ml.nlp.classifier: joeddav/xlm-roberta-large-xnli, ten bilingual HungerGist hypotheses, max entailment,
food-nexus guard, 0.30 relevance threshold).

What changes is how failure is handled. The classifier silently substitutes a KEYWORD score when the model cannot be
loaded or an inference raises; an FSSI built on those scores looks like a model FSSI. Here:
  * if the model cannot be loaded, nothing is scored and ScoringUnavailable is raised;
  * an inference error is stored as status FAILED with no score (retried on the next run);
  * a premise with no food referent is stored as NO_FOOD_NEXUS with score 0.0 (the classifier's own rule).

Scores are append-only in scores.jsonl and keyed by model_key = model name @ snapshot revision | classifier.py hash, so
a re-score under the same model is skipped and a model or hypothesis change creates a new, separate score version.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.news.store import NewsStore


class ScoringUnavailable(RuntimeError):
    pass


def _snapshot_revision(model_name: str) -> str:
    import os

    hub = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    d = hub / ("models--" + model_name.replace("/", "--")) / "snapshots"
    revs = sorted(p.name for p in d.iterdir()) if d.exists() else []
    return revs[-1] if revs else "unknown"


def current_model_key() -> str:
    import app.ml.nlp.classifier as C

    # E64 (D-E64-1): hash the LF-normalised source. Hashing raw bytes made the key depend on the checkout's line endings
    # (git core.autocrlf), so an identical classifier got a new key and every stored score stopped matching.
    code = hashlib.sha256(Path(C.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]
    return f"{C.MODEL_NAME}@{_snapshot_revision(C.MODEL_NAME)[:12]}|clf:{code}"


def xlmr_scorer() -> Callable[[str, str], dict]:
    import app.ml.nlp.classifier as C

    clf = C.load_classifier()
    if not isinstance(clf, C._XLMRobertaClassifier):
        raise ScoringUnavailable("XLM-RoBERTa could not be loaded; the classifier fell back to keywords, which E28 "
                                 "refuses for the FSSI")

    def score(title: str, summary: str) -> dict:
        text = C.clean_text(title, summary, limit=C.PREMISE_CHARS)
        if not C.has_food_nexus(text):
            return {"status": "NO_FOOD_NEXUS", "score": 0.0, "top_hypothesis": None, "all_scores": {}}
        raw = clf.classify(text)                      # exceptions propagate -> FAILED
        s = {r["topic_id"]: r["score"] for r in raw}
        top = max(s, key=lambda k: s[k])
        return {"status": "OK", "score": round(s[top], 4), "top_hypothesis": top,
                "all_scores": {k: round(v, 4) for k, v in s.items()}}

    return score


def score_pending(store: NewsStore, scorer: Callable[[str, str], dict] | None = None, model_key: str | None = None,
                  only_geocoded: bool = True, limit: int | None = None) -> dict:
    model_key = model_key or current_model_key()
    done = {}
    for r in store.read("scores"):
        if r.get("model_key") == model_key and r["status"] != "FAILED":
            done[r["article_key"]] = r
    todo = [a for a in store.articles.values()
            if a["article_key"] not in done and (a.get("geo_province_code") or not only_geocoded)]
    todo.sort(key=lambda a: (a["quarter"], a["article_key"]))
    if limit is not None:
        todo = todo[:limit]
    if not todo:
        return {"model_key": model_key, "scored": 0, "failed": 0, "already_scored": len(done), "pending": 0}
    scorer = scorer or xlmr_scorer()
    n_ok = n_fail = 0
    for a in todo:
        rec = {"article_key": a["article_key"], "model_key": model_key,
               "scored_at": datetime.now(timezone.utc).isoformat()}
        try:
            rec.update(scorer(a["title"], ""))
            n_ok += 1
        except Exception as exc:
            rec.update({"status": "FAILED", "score": None, "error": f"{type(exc).__name__}: {str(exc)[:160]}"})
            n_fail += 1
        store._append("scores", rec)
    return {"model_key": model_key, "scored": n_ok, "failed": n_fail, "already_scored": len(done),
            "pending": len(todo) - n_ok - n_fail}
