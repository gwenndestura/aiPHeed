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
from pathlib import Path

import pandas as pd

from app.news.audit import _latest_scores
from app.news.collector import PROVINCES
from app.news.store import NewsStore


TOPICS_DIR = "topics"
SEED = 42
STABILITY_SEEDS = (43, 44)
# Publication gate, fixed before the first run (E59 item 2): enough articles for the pipeline's own minimum
# (3 x min_topic_size), at least 2 topics, at most half the articles left as outliers, and a mean adjusted Rand
# index >= 0.5 between the seed-42 assignment and refits with seeds 43 and 44. Otherwise only the numbers are written.
MIN_TOPICS, MAX_OUTLIER_SHARE, MIN_STABILITY_ARI = 2, 0.5, 0.5
USE_STATEMENT = ("Descriptive only: what the news talked about, per province-quarter. Not a forecast feature: the "
                 "topic model is fitted once on all authorized quarters, so later articles shape the topics of "
                 "earlier quarters.")


def build_topic_files(store: NewsStore, quarters: list[str], model_key: str, threshold: float = 0.30,
                      min_topic_size: int = 10, out_dir: Path | None = None, now: str | None = None) -> dict:
    """build_topics plus a stability check and the published files: <store>/topics/ (or out_dir) gets
    manifest.json always, and topic_proportions.csv + topics.json only when the publication gate passes."""
    from datetime import datetime, timezone

    from sklearn.metrics import adjusted_rand_score

    from app.ml.nlp.topic_model import EMBEDDING_MODEL_NAME, TopicModelPipeline

    out_dir = Path(out_dir) if out_dir else store.root / TOPICS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    df = _topic_articles(store, quarters, model_key, threshold)
    manifest = {"created_utc": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "embedding_model": EMBEDDING_MODEL_NAME, "algorithm": "BERTopic (UMAP 5d cosine, HDBSCAN eom, "
                "KeyBERT-inspired representation, CountVectorizer 1-2 grams, English stop words)",
                "seed": SEED, "stability_seeds": list(STABILITY_SEEDS), "min_topic_size": min_topic_size,
                "articles": f"authorized, title-geocoded to a CALABARZON province, XLM-R score >= {threshold}",
                "scoring_model_key": model_key, "quarters": [quarters[0], quarters[-1]] if quarters else [],
                "n_articles": int(len(df)), "use": USE_STATEMENT,
                "gate": {"min_articles": 3 * min_topic_size, "min_topics": MIN_TOPICS,
                         "max_outlier_share": MAX_OUTLIER_SHARE, "min_stability_ari": MIN_STABILITY_ARI}}
    if len(df) < 3 * min_topic_size:
        manifest.update(status="INSUFFICIENT_ARTICLES", reason=f"{len(df)} articles < {3 * min_topic_size}")
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        return manifest
    texts = df["title"].tolist()
    model = TopicModelPipeline().fit(texts, min_topic_size=min_topic_size, seed=SEED)
    df["topic"] = model.topics_
    aris = []
    for s in STABILITY_SEEDS:
        alt = TopicModelPipeline().fit(texts, min_topic_size=min_topic_size, seed=s)
        aris.append(float(adjusted_rand_score(df["topic"], alt.topics_)))
    info = model.get_topic_info()
    n_topics = int((info["Topic"] != -1).sum())
    outlier = float((df["topic"] == -1).mean())
    manifest.update(n_topics=n_topics, outlier_share=outlier, stability_ari=aris,
                    stability_ari_mean=float(sum(aris) / len(aris)), topic_sizes={
                        str(int(r.Topic)): int(r.Count) for r in info.itertuples()})
    failed = [c for c, ok in (("n_topics", n_topics >= MIN_TOPICS), ("outlier_share", outlier <= MAX_OUTLIER_SHARE),
                              ("stability", manifest["stability_ari_mean"] >= MIN_STABILITY_ARI)) if not ok]
    if failed:
        manifest.update(status="UNSTABLE", reason="publication gate failed: " + ", ".join(failed))
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        return manifest
    keywords = {str(int(r.Topic)): [{"word": w, "weight": round(float(v), 4)}
                                    for w, v in (model.get_topic(int(r.Topic)) or [])[:10]]
                for r in info.itertuples() if int(r.Topic) != -1}
    label = {int(k): ", ".join(x["word"] for x in v[:5]) for k, v in keywords.items()}
    cell_n = df.groupby(["province", "quarter"]).size().rename("n_articles")
    prop = (df.groupby(["province", "quarter"])["topic"].value_counts(normalize=True).rename("share").reset_index()
            .join(cell_n, on=["province", "quarter"]))
    prop["topic_label"] = prop["topic"].map(lambda t: label.get(int(t), "outliers (no topic)"))
    csv = prop.sort_values(["province", "quarter", "topic"]).to_csv(index=False, lineterminator="\n")
    (out_dir / "topic_proportions.csv").write_bytes(csv.encode("utf-8"))
    (out_dir / "topics.json").write_text(json.dumps({"topics": keywords}, indent=1), encoding="utf-8")
    manifest.update(status="OK", proportions_sha256=hashlib.sha256(csv.encode()).hexdigest(),
                    n_province_quarters=int(len(cell_n)))
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def _topic_articles(store: NewsStore, quarters: list[str], model_key: str, threshold: float) -> pd.DataFrame:
    scores = _latest_scores(store, model_key)
    code2name = {v: k for k, v in PROVINCES.items()}
    recs = [{"article_key": a["article_key"], "title": a["title"], "province": code2name[a["geo_province_code"]],
             "quarter": a["quarter"]}
            for a in store.articles.values()
            if a.get("geo_province_code") in code2name and a["quarter"] in quarters
            and (s := scores.get(a["article_key"])) and s["status"] == "OK" and s["score"] >= threshold]
    if not recs:
        return pd.DataFrame(columns=["article_key", "title", "province", "quarter"])
    return pd.DataFrame(recs).sort_values("article_key").reset_index(drop=True)


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
