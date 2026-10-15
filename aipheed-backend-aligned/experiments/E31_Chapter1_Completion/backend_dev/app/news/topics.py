"""
BERTopic latent patterns per province-quarter (E28, Objective 1).

Uses the project's TopicModelPipeline (paraphrase-multilingual-MiniLM-L12-v2, UMAP random_state 42, HDBSCAN,
KeyBERT-inspired representation). The model is fitted ONCE on the titles of the authorized 2021-Q1..2026-Q2 articles
that are title-geocoded to a CALABARZON province and scored at or above the 0.30 relevance threshold.

Leakage statement. A topic model fitted on every quarter lets later articles shape the topics of earlier quarters,
so these proportions are DESCRIPTIVE (what the news talked about, per province-quarter) and are NOT used as forecast
features. A forecast feature would need a model refitted at each origin on articles published before it.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd

from app.news.audit import _latest_scores
from app.news.collector import PROVINCES
from app.news.store import NewsStore


def build_topics(store: NewsStore, quarters: list[str], model_key: str, threshold: float = 0.30,
                 min_topic_size: int = 10) -> dict:
    from app.ml.nlp.topic_model import TopicModelPipeline

    scores = _latest_scores(store, model_key)
    code2name = {v: k for k, v in PROVINCES.items()}
    recs = [{"article_key": a["article_key"], "title": a["title"], "province": code2name[a["geo_province_code"]],
             "quarter": a["quarter"]}
            for a in store.articles.values()
            if a.get("geo_province_code") in code2name and a["quarter"] in quarters
            and (s := scores.get(a["article_key"])) and s["status"] == "OK" and s["score"] >= threshold]
    df = pd.DataFrame(recs).sort_values("article_key").reset_index(drop=True)
    if len(df) < 3 * min_topic_size:
        return {"status": "INSUFFICIENT_ARTICLES", "n_articles": int(len(df))}
    tm = TopicModelPipeline()
    model = tm.fit(df["title"].tolist(), min_topic_size=min_topic_size)
    df["topic"] = model.topics_
    info = model.get_topic_info()
    labels = {int(r.Topic): ", ".join(w for w, _ in (model.get_topic(int(r.Topic)) or [])[:5]) for r in info.itertuples()}
    prop = (df.groupby(["province", "quarter"])["topic"].value_counts(normalize=True).rename("share").reset_index())
    prop["topic_label"] = prop["topic"].map(labels)
    top = (prop[prop["topic"] != -1].sort_values(["province", "quarter", "share"], ascending=[True, True, False])
           .groupby(["province", "quarter"]).head(3))
    csv = prop.sort_values(["province", "quarter", "topic"]).to_csv(index=False, lineterminator="\n")
    (store.root / "topic_proportions_descriptive.csv").write_bytes(csv.encode("utf-8"))
    out = {"status": "OK", "n_articles": int(len(df)), "n_topics": int((info["Topic"] != -1).sum()),
           "outlier_share": float((df["topic"] == -1).mean()), "topics": {str(k): v for k, v in labels.items()},
           "top_topics_by_province_quarter": top.to_dict("records"),
           "proportions_sha256": hashlib.sha256(csv.encode()).hexdigest(),
           "use": "descriptive only; not a forecast feature (fitted on all authorized quarters)"}
    (store.root / "topics_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out
