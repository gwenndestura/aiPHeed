"""
FSSI-v2 (E31): the Food Stress Sentiment Index with a validated relevance gate. FSSI-v1 (E28) is kept unchanged.

  admitted  = title-geocoded to a province  AND  relevance rule R1 says DIRECT/INDIRECT  AND  first copy of its
              syndication cluster (same normalised title within 3 days, any outlet);
  intensity = XLM-RoBERTa-large-XNLI max entailment over the ten bilingual FSSI hypotheses (Objective 1), scored on
              the admitted articles WITHOUT the food-nexus guard (R1 now decides relevance; the guard existed to stop
              the model scoring irrelevant text). Stored as its own score version (model_key suffix '|v2-noguard').
  FSSI_v2   = Equation 2 unchanged (bias weight log(1+median)/log(1+n) times the mean intensity), on admitted
              articles; no 0.30 threshold (relevance is decided by the validated rule, not by the intensity score).
  status    = SUFFICIENT (>= 5 admitted), LIMITED_SIGNAL (1-4), NO_USABLE_EVIDENCE (0); never zero-filled.

Validation (E31 validation/): on a fresh blind holdout R1 has precision 0.85 (95% CI 0.77-0.92) and corpus-weighted
recall 0.40 (0.26-0.69) for food-insecurity-related province-attributed titles; the E28 gate had 0.62 / 0.13.
An evidence window (app.news.alignment) restricts the articles to those a forecast or nowcast may use.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta

import pandas as pd

from app.news.collector import PROVINCES
from app.news.relevance import VERSION_DEPLOYED as RULE_VERSION, classify_deployed as classify
from app.news.store import NewsStore

MIN_ARTICLES = 5
SYNDICATION_DAYS = 3
SCORE_SUFFIX = "|v2-noguard"


def norm_title(t: str) -> str:
    t = t.rsplit(" - ", 1)[0] if " - " in t else t
    t = unicodedata.normalize("NFKD", t).lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())


def dedupe(arts: list[dict]) -> tuple[list[dict], dict]:
    """Keep the earliest copy of each syndication cluster (same normalised title within SYNDICATION_DAYS)."""
    out, dropped, seen = [], {}, {}
    for a in sorted(arts, key=lambda a: (a["published_ph"], a["article_key"])):
        n = norm_title(a["title"])
        p = datetime.fromisoformat(a["published_ph"])
        prev = seen.get(n)
        if prev is not None and (p - prev[0]) <= timedelta(days=SYNDICATION_DAYS):
            dropped[a["article_key"]] = prev[1]
            continue
        seen[n] = (p, a["article_key"])
        out.append(a)
    return out, dropped


def v2_model_key() -> str:
    from app.news.scoring import current_model_key

    return current_model_key() + SCORE_SUFFIX


def score_admitted(store: NewsStore, keys: list[str], scorer=None) -> dict:
    """Append v2 intensity scores for admitted articles that do not have one yet."""
    mk = v2_model_key()
    done = {r["article_key"] for r in store.read("scores") if r.get("model_key") == mk and r["status"] == "OK"}
    todo = [k for k in keys if k not in done]
    if not todo:
        return {"model_key": mk, "scored": 0, "already": len(done)}
    if scorer is None:
        import app.ml.nlp.classifier as C

        clf = C.load_classifier()
        if not isinstance(clf, C._XLMRobertaClassifier):
            raise RuntimeError("XLM-RoBERTa unavailable; FSSI-v2 refuses the keyword fallback")

        def scorer(title):
            raw = clf.classify(C.clean_text(title, "", limit=C.PREMISE_CHARS))
            s = {r["topic_id"]: r["score"] for r in raw}
            top = max(s, key=lambda k: s[k])
            return {"status": "OK", "score": round(s[top], 4), "top_hypothesis": top,
                    "all_scores": {k: round(v, 4) for k, v in s.items()}}
    n = 0
    for k in todo:
        rec = {"article_key": k, "model_key": mk, "scored_at": datetime.now().astimezone().isoformat()}
        rec.update(scorer(store.articles[k]["title"]))
        store._append("scores", rec)
        n += 1
    return {"model_key": mk, "scored": n, "already": len(done)}


def admitted_articles(store: NewsStore, window=None) -> tuple[list[dict], dict]:
    from app.news.alignment import is_eligible

    geo = [a for a in store.articles.values() if a.get("geo_province_code") in PROVINCES.values()]
    if window is not None:
        geo = [a for a in geo if is_eligible(a, window)]
    rel = [a for a in geo if classify(a["title"]) != "NONE"]
    kept, dropped = dedupe(rel)
    return kept, {"province_attributed": len(geo), "relevant_R1": len(rel), "syndicated_copies_removed": len(dropped)}


def build_fssi_v2(store: NewsStore, quarters: list[str], write: bool = True, out_name: str = "fssi_v2_panel.csv") -> dict:
    from app.ml.corpus.bias_weighter import compute_bias_weights
    from app.ml.features.fssi_builder import compute_fssi

    mk = v2_model_key()
    sc = {r["article_key"]: r for r in store.read("scores") if r.get("model_key") == mk and r["status"] == "OK"}
    kept, _ = admitted_articles(store)
    kept = [a for a in kept if a["quarter"] in quarters]
    missing = [a["article_key"] for a in kept if a["article_key"] not in sc]
    if missing:
        raise RuntimeError(f"{len(missing)} admitted articles lack a v2 intensity score: run score_admitted first")
    art = pd.DataFrame([{"article_key": a["article_key"], "province_code": a["geo_province_code"], "quarter": a["quarter"],
                         "published": a["published_ph"], "food_insecurity_score": sc[a["article_key"]]["score"],
                         "relevance": classify(a["title"])} for a in kept],
                       columns=["article_key", "province_code", "quarter", "published", "food_insecurity_score", "relevance"])
    if len(art):
        w = compute_bias_weights(art[["province_code", "published"]], save_path=None)
        f = compute_fssi(art, w, save_path=None)
    else:
        f = pd.DataFrame(columns=["province_code", "quarter", "article_count", "fssi_raw", "bias_weight", "FSSI"])
    allgeo = [a for a in store.articles.values() if a.get("geo_province_code")]
    rows = []
    for p, code in PROVINCES.items():
        for q in quarters:
            g = art[(art.province_code == code) & (art.quarter == q)]
            fr = f[(f.province_code == code) & (f.quarter == q)]
            n = int(len(g))
            ev = "SUFFICIENT" if n >= MIN_ARTICLES else "LIMITED_SIGNAL" if n else "NO_USABLE_EVIDENCE"
            rows.append({"province": p, "province_code": code, "quarter": q,
                         "n_province_attributed": sum(1 for a in allgeo if a["geo_province_code"] == code and a["quarter"] == q),
                         "n_admitted": n, "n_direct": int((g.relevance == "DIRECT").sum()),
                         "n_indirect": int((g.relevance == "INDIRECT").sum()),
                         "mean_intensity": round(float(g.food_insecurity_score.mean()), 6) if n else None,
                         "bias_weight": round(float(fr.bias_weight.iloc[0]), 6) if len(fr) else None,
                         "FSSI_v2": round(float(fr.FSSI.iloc[0]), 6) if len(fr) else None, "evidence_status": ev})
    panel = pd.DataFrame(rows)
    csv = panel.to_csv(index=False, lineterminator="\n")
    manifest = {"version": "FSSI-v2", "relevance_rule": RULE_VERSION, "intensity_model_key": mk,
                "quarters": [quarters[0], quarters[-1]], "panel_sha256": hashlib.sha256(csv.encode()).hexdigest(),
                "articles_jsonl_sha256": hashlib.sha256(store.path("articles").read_bytes()).hexdigest(),
                "evidence_status_counts": panel.evidence_status.value_counts().to_dict(),
                "n_admitted_total": int(len(art))}
    if write:
        (store.root / out_name).write_bytes(csv.encode("utf-8"))
        (store.root / out_name.replace(".csv", "_manifest.json")).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return {"panel": panel, "manifest": manifest, "articles": art}
