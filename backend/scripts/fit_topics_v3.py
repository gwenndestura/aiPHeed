"""
scripts/fit_topics_v3.py
------------------------
E64 (Objective 1, tier 2): BERTopic latent topics on the v3 news corpus (E31 + E60 stores, 2021-01-01..2026-10-14,
titles only; the source gives no body text), with the project pipeline (app.ml.nlp.topic_model: multilingual MiniLM
embeddings, UMAP, HDBSCAN, KeyBERT-inspired representation, fixed seeds).

Outputs (data/news_v3/):
  topic_info.csv               topic id, size, top words
  article_topics.csv           article_key, quarter, province_code, relevant (classifier v2), trigger, topic_id
  topic_proportions.csv        province-quarter shares of the top topics among province-attributed articles
  topics_manifest.json         corpus hash, parameters, counts

Descriptive only: the topics are fitted on the whole window at once, so they are NOT used as forecast features (that would
use later articles to define earlier features). They describe latent food-stress patterns per province-quarter.

    cd backend && venv/Scripts/python.exe -B scripts/fit_topics_v3.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.nlp.topic_model import EMBEDDING_MODEL_NAME, MIN_TOPIC_SIZE, TopicModelPipeline  # noqa: E402
from app.news import pipeline_v3 as P  # noqa: E402

OUT = P.DATA / "news_v3"
MODEL_DIR = Path("models/bertopic_v3")


def main():
    arts = pd.DataFrame(list(P.corpus()))
    arts["summary"] = ""
    tm = TopicModelPipeline()
    tm.fit(arts["title"].tolist())
    topics, _ = tm.transform(arts["title"].tolist())
    arts["topic_id"] = topics
    info = tm.get_topic_info()
    OUT.mkdir(parents=True, exist_ok=True)
    keep = [c for c in ("Topic", "Count", "Name", "Representation") if c in info.columns]
    info[keep].to_csv(OUT / "topic_info.csv", index=False, lineterminator="\n")
    arts[["article_key", "quarter", "province_code", "relevant", "trigger", "topic_id"]].to_csv(
        OUT / "article_topics.csv", index=False, lineterminator="\n")
    props = tm.compute_proportions(arts, save_path=None)
    props.to_csv(OUT / "topic_proportions.csv", index=False, float_format="%.6f", lineterminator="\n")
    try:
        tm.save(MODEL_DIR)
    except Exception as exc:                    # the proportions and assignments above are the deliverable
        print("model save skipped:", exc)
    man = {"corpus_articles": int(len(arts)), "corpus_keys_sha256": hashlib.sha256(
               "\n".join(sorted(arts["article_key"])).encode()).hexdigest(),
           "window": [P.FIRST_DATE, P.LAST_DATE], "text": "titles only", "embedding_model": EMBEDDING_MODEL_NAME,
           "min_topic_size": MIN_TOPIC_SIZE, "umap_random_state": 42, "topics_excluding_outliers": int((info["Topic"] != -1).sum()),
           "outlier_share": round(float((arts["topic_id"] == -1).mean()), 4),
           "province_quarter_rows": int(len(props)), "use": "descriptive latent patterns; not a forecast feature"}
    (OUT / "topics_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
