"""E61: BERTopic on every authorized province-attributed title (SO1), same pipeline and gate as E59/build_topic_files.
Pre-registration: ../E61_results.md (md5-stamped in ../preregistration_md5.txt before this ran).

    python -B backend/experiments/e61/runner/e61_run.py      (run from the repo root)

Writes backend/experiments/e61/E61_results.json and manifest.json always; data/news_e61/topics/ only if the gate passes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
E61 = Path(__file__).resolve().parents[1]
BACKEND = E61.parents[1]
sys.path.insert(0, str(BACKEND))
PROTECTED = {"data/e36/e36_record.json": "921f2130c2ab3380c3cd21c1b25fe31a",
             "data/e48/e48_record.json": "a2223c22f85cb4058c0e7e59229dcb67",
             "data/e49/e49_record.json": "14c818ea990b6959584fbff92afd3ade",
             "data/e49/model/E48-A1-LGBM_O2026-10-01.txt": "2b6be3e9ab5e63191aa03639a5640ab1",
             "data/e49/model/E49_C2_calibration.json": "8f0eae02d81857f1d3c72ca5965409df",
             "data/e53/e53_record.json": "fa3d0a51939fae66d87bf77c3d15d738",
             "data/e53/model/E53_C2_calibration.json": "9986f6cb4b4a36a9e9d676709cb3aeee"}
OUT = BACKEND / "data" / "news_e61" / "topics"


def md5s() -> dict:
    out = {p: hashlib.md5((BACKEND / p).read_bytes()).hexdigest() for p in PROTECTED}
    if out != PROTECTED:
        raise SystemExit(f"protected md5 mismatch: {[p for p in out if out[p] != PROTECTED[p]]}")
    return out


def corpus():
    import pandas as pd

    from app.news.collector import PROVINCES, all_quarters
    from app.news.store import NewsStore

    auth = json.loads((BACKEND / "config" / "authorization.json").read_text(encoding="utf-8"))
    quarters = set(all_quarters(auth["authorized_until"]))
    through = auth.get("authorized_through") or "9999-12-31"
    code2name = {v: k for k, v in PROVINCES.items()}
    store = NewsStore(BACKEND / "data" / "news_e31")
    recs = [{"article_key": a["article_key"], "title": a["title"], "province": code2name[a["geo_province_code"]],
             "quarter": a["quarter"]}
            for a in store.articles.values()
            if a.get("geo_province_code") in code2name and a["quarter"] in quarters and a["ph_date"] <= through]
    df = pd.DataFrame(recs).sort_values("article_key").reset_index(drop=True)
    return df, sorted(quarters), through


def main():
    os.chdir(BACKEND)
    from sklearn.metrics import adjusted_rand_score

    from app.ml.nlp.topic_model import EMBEDDING_MODEL_NAME, TopicModelPipeline
    from app.news import topics as T

    res = {"md5_start": md5s(), "preregistration": (E61 / "preregistration_md5.txt").read_text().split()}
    df, quarters, through = corpus()
    MIN_SIZE = 10
    res["corpus"] = {"n_articles": int(len(df)), "quarters": [quarters[0], quarters[-1]], "authorized_through": through,
                     "repeated_titles": int(len(df) - df["title"].nunique()),
                     "per_quarter": {q: int(n) for q, n in df.groupby("quarter").size().items()},
                     "per_province": {p: int(n) for p, n in df.groupby("province").size().items()},
                     "per_province_quarter": {f"{p}|{q}": int(n) for (p, q), n in
                                              df.groupby(["province", "quarter"]).size().items()}}
    gate = {"min_articles": 3 * MIN_SIZE, "min_topics": T.MIN_TOPICS, "max_outlier_share": T.MAX_OUTLIER_SHARE,
            "min_stability_ari": T.MIN_STABILITY_ARI}
    res["model"] = {"embedding_model": EMBEDDING_MODEL_NAME, "seed": T.SEED, "stability_seeds": list(T.STABILITY_SEEDS),
                    "min_topic_size": MIN_SIZE, "gate": gate}
    if len(df) < gate["min_articles"]:
        res.update(status="INSUFFICIENT_ARTICLES")
    else:
        texts = df["title"].tolist()
        print("fit seed", T.SEED, "on", len(texts), "titles", flush=True)
        model = TopicModelPipeline().fit(texts, min_topic_size=MIN_SIZE, seed=T.SEED)
        df["topic"] = model.topics_
        aris = []
        for s in T.STABILITY_SEEDS:
            print("stability seed", s, flush=True)
            alt = TopicModelPipeline().fit(texts, min_topic_size=MIN_SIZE, seed=s)
            aris.append(float(adjusted_rand_score(df["topic"], alt.topics_)))
        info = model.get_topic_info()
        n_topics = int((info["Topic"] != -1).sum())
        outlier = float((df["topic"] == -1).mean())
        mean_ari = float(sum(aris) / len(aris))
        keywords = {str(int(r.Topic)): [{"word": w, "weight": round(float(v), 4)}
                                        for w, v in (model.get_topic(int(r.Topic)) or [])[:10]]
                    for r in info.itertuples() if int(r.Topic) != -1}
        checks = {"articles": len(df) >= gate["min_articles"], "n_topics": n_topics >= gate["min_topics"],
                  "outlier_share": outlier <= gate["max_outlier_share"],
                  "stability": mean_ari >= gate["min_stability_ari"]}
        res.update(n_topics=n_topics, outlier_share=outlier, stability_ari=aris, stability_ari_mean=mean_ari,
                   topic_sizes={str(int(r.Topic)): int(r.Count) for r in info.itertuples()},
                   top_words=keywords, gate_checks=checks,
                   status="OK" if all(checks.values()) else "UNSTABLE")
        failed = [k for k, ok in checks.items() if not ok]
        res["reason"] = "gate passed" if not failed else "publication gate failed: " + ", ".join(failed)
        manifest = {"created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "embedding_model": EMBEDDING_MODEL_NAME, "seed": T.SEED,
                    "stability_seeds": list(T.STABILITY_SEEDS), "min_topic_size": MIN_SIZE,
                    "articles": "authorized, title-geocoded to a CALABARZON province; no relevance or score filter (E61)",
                    "quarters": [quarters[0], quarters[-1]], "n_articles": int(len(df)), "use": T.USE_STATEMENT,
                    "gate": gate, "n_topics": n_topics, "outlier_share": outlier, "stability_ari": aris,
                    "stability_ari_mean": mean_ari, "topic_sizes": res["topic_sizes"], "status": res["status"],
                    "reason": res["reason"], "served": False}
        if res["status"] == "OK":
            label = {int(k): ", ".join(x["word"] for x in v[:5]) for k, v in keywords.items()}
            cell_n = df.groupby(["province", "quarter"]).size().rename("n_articles")
            prop = (df.groupby(["province", "quarter"])["topic"].value_counts(normalize=True).rename("share")
                    .reset_index().join(cell_n, on=["province", "quarter"]))
            prop["topic_label"] = prop["topic"].map(lambda t: label.get(int(t), "outliers (no topic)"))
            csv = prop.sort_values(["province", "quarter", "topic"]).to_csv(index=False, lineterminator="\n")
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "topic_proportions.csv").write_bytes(csv.encode("utf-8"))
            (OUT / "topics.json").write_text(json.dumps({"topics": keywords}, indent=1), encoding="utf-8")
            manifest.update(proportions_sha256=hashlib.sha256(csv.encode()).hexdigest(),
                            n_province_quarters=int(len(cell_n)))
            (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
            res["written"] = [str(p.relative_to(BACKEND)) for p in sorted(OUT.iterdir())]
        else:
            res["written"] = []
        (E61 / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    res["md5_end"] = md5s()
    (E61 / "E61_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("STATUS", res["status"], res.get("reason"), "| topics", res.get("n_topics"), "| outliers",
          res.get("outlier_share"), "| ARI", res.get("stability_ari"))


if __name__ == "__main__":
    main()
