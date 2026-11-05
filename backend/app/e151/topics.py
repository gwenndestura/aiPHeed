"""
E151 story clustering and BERTopic. Reads no outcome.

embed    multilingual embeddings of masked text, near-duplicate stories (cosine >= 0.93 within 7 days)
fit      one BERTopic per origin, fitted only on stories published before the origin, every later story only assigned
         each topic is mapped to a trigger group by the mean XLM event scores of its stories, or removed as off-topic, with the reason recorded

    python -m app.e151.topics embed | fit -> data/e151/raw/stories.parquet, topic_assign_*.parquet; data/e151/out/topic_report.csv
"""
from __future__ import annotations

import json
import re
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e147 import features as Fe
from app.e150.news_v2 import name_rx
from app.e151 import OUT, RAW
from app.e151.corpus import CAL, DATA

SEED = 151
EVENTS = ["food_access", "purchasing", "supply", "agri_loss", "income", "climate", "displacement", "ofw", "assistance", "recovery", "none"]
GROUP = {"food_access": "poverty", "displacement": "poverty", "purchasing": "market", "supply": "market", "agri_loss": "climate", "climate": "climate", "income": "employment", "ofw": "remittance", "assistance": "response", "recovery": "response"}
ORIGINS = [f"{y}-01-01" for y in range(2014, 2027)] + ["2026-10-01"]
STOP = ["ang", "ng", "sa", "na", "at", "mga", "para", "ay", "si", "ni", "the", "of", "and", "to", "in", "on", "for", "a", "an", "is", "that", "with", "by", "as", "from", "it", "was", "were", "are", "be", "has", "have", "had", "will", "said", "says", "this", "at", "its", "their", "not", "but", "who", "about", "after", "over", "more", "also", "which", "they", "he", "she", "his", "her", "we", "you", "i", "or", "than", "new", "philippines", "philippine", "rappler"]


def mask_rx():
    base = Fe.base_rows().drop_duplicates("key")
    names = set()
    for k in base["key"]:
        names.add(k.title())
    lg = pd.read_csv(DATA / "reference" / "calabarzon_lgus.csv")
    names |= {re.sub(r"\s+City$", "", n) for n in lg["lgu_name"]} | {"Quezon City", "Metro Manila", "Manila", "Luzon", "Visayas", "Mindanao"}
    return re.compile(r"\b(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")\b")


def eligible() -> pd.DataFrame:
    d = pd.read_parquet(RAW / "corpus.parquet", columns=["id", "site", "origin", "published", "title", "text", "score_text", "hash", "geo_level", "provinces", "areas", "gate", "n_outlets", "n_named_lead"])
    d = d[d["gate"] & (d["geo_level"] != "international")].copy()
    return d.sort_values("published").reset_index(drop=True)


def embed():
    from sentence_transformers import SentenceTransformer
    d = eligible()
    rx = mask_rx()
    txt = d["score_text"].map(lambda s: rx.sub("PLACE", s)[:500])
    m = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
    m.max_seq_length = 128
    E = m.encode(txt.tolist(), batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    np.save(RAW / "embeddings.npy", E.astype("float32"))
    # near-duplicates: a greedy pass through a sliding 7-day window; rewrites of the same story get the same story id
    t = d["published"].values.astype("datetime64[s]").astype("int64")
    story = np.arange(len(d))
    start = 0
    wk = 7 * 86400
    for i in range(len(d)):
        while t[i] - t[start] > wk:
            start += 1
        if i > start:
            s = E[start:i] @ E[i]
            j = int(np.argmax(s))
            if s[j] >= 0.93:
                story[i] = story[start + j]
    d["story"] = story
    d["masked"] = txt.values
    d.to_parquet(RAW / "stories.parquet", index=False)
    a = {"eligible_articles": int(len(d)), "stories": int(pd.Series(story).nunique()), "near_duplicate_share": float(1 - pd.Series(story).nunique() / len(d))}
    (OUT / "story_audit.json").write_text(json.dumps(a, indent=1), newline="\n")
    print(a, flush=True)


def _fit(origin: str, d, E, ev):
    import hdbscan
    import umap
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer
    cut = pd.Timestamp(origin)
    tr = np.where((d["published"] < cut).values & d["first"].values)[0]
    tm = BERTopic(umap_model=umap.UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=SEED, n_jobs=1), hdbscan_model=hdbscan.HDBSCAN(min_cluster_size=max(15, len(tr) // 250), metric="euclidean", prediction_data=True),
                  vectorizer_model=CountVectorizer(stop_words=STOP, ngram_range=(1, 2), min_df=3), nr_topics="auto", calculate_probabilities=False, verbose=False)
    y, _ = tm.fit_transform(d["masked"].iloc[tr].tolist(), E[tr])
    y = np.asarray(y)
    fit_df = pd.DataFrame({"topic": y, "hash": d["hash"].iloc[tr].values}).merge(ev, on="hash", how="left")
    info = tm.get_topic_info()
    rows = []
    cols = [f"pr_{e}" for e in EVENTS]
    for t in info["Topic"]:
        if t < 0:
            continue
        g = fit_df[fit_df["topic"] == t]
        means = g[cols].mean()
        top = means.drop("pr_none")
        ev_top = top.idxmax().replace("pr_", "")
        kw = [w for w, _ in tm.get_topic(t)[:8]]
        off = bool(means["pr_none"] >= 0.5)
        rows.append({"origin": origin, "topic": int(t), "n": int(len(g)), "keywords": ", ".join(kw), "top_event": ev_top, "group": None if off else GROUP[ev_top], "off_topic": off, "mean_none": float(means["pr_none"]), "mean_top_event": float(top.max())})
    R = pd.DataFrame(rows)
    # assignment of every story: fitted stories keep their topic; a story after the origin is assigned, never fitted
    all_y = np.full(len(d), -1)
    all_y[tr] = y
    rest = np.where(~np.isin(np.arange(len(d)), tr))[0]
    if len(rest):
        y2, _ = tm.transform(d["masked"].iloc[rest].tolist(), E[rest])
        all_y[rest] = y2
    out = pd.DataFrame({"id": d["id"].values, "topic": all_y})
    mp = R.set_index("topic")["group"].to_dict()
    out["t_group"] = out["topic"].map(mp)
    out.to_parquet(RAW / f"topic_assign_{origin}.parquet", index=False)
    return R, {"origin": origin, "fit_stories": int(len(tr)), "topics": int(len(R)), "outlier_share": float((y == -1).mean()), "off_topic": int(R["off_topic"].sum())}


def event_probs() -> pd.DataFrame:
    """Deviation D3: each event is the mean of three readers on their own scales (XLM-RoBERTa, embedding similarity, seed phrases), set on stories before 2015.
    A story is off-topic (pr_none = 1) if it names a foreign place and no Philippine one, or its title carries an off-topic phrase."""
    e = pd.read_parquet(RAW / "labels_raw.parquet").drop_duplicates("hash").reset_index(drop=True)
    ev = [k for k in EVENTS if k != "none"]
    Z = np.column_stack([np.nan_to_num(e[[f"{a}_{k}" for a in ("nz", "sz", "lz")]].values).mean(axis=1) for k in ev])
    p = np.exp(Z - Z.max(axis=1, keepdims=True))
    p = p / p.sum(axis=1, keepdims=True)
    off = ((e["for_lex"] > 0) & (e["ph_lex"] == 0)) | (e["off_lex"] > 0)
    o = pd.DataFrame(p, columns=[f"pr_{k}" for k in ev])
    o["pr_none"] = off.astype(float).values
    o["hash"] = e["hash"].values
    o["problem"] = 1 / (1 + np.exp(-e["z_problem"].fillna(0.0).values))
    o["plan"] = 1 / (1 + np.exp(-e["z_plan"].fillna(0.0).values))
    return o


def fit():
    d = pd.read_parquet(RAW / "stories.parquet")
    E = np.load(RAW / "embeddings.npy")
    d["first"] = ~d.duplicated("story")
    ev = event_probs()
    res = Parallel(n_jobs=7)(delayed(_fit)(o, d, E, ev) for o in ORIGINS)
    pd.concat([r for r, _ in res], ignore_index=True).to_csv(OUT / "topic_report.csv", index=False, lineterminator="\n")
    (OUT / "topic_fits.json").write_text(json.dumps([m for _, m in res], indent=1), newline="\n")
    print(json.dumps([m for _, m in res], indent=0), flush=True)


if __name__ == "__main__":
    {"embed": embed, "fit": fit}[sys.argv[1]]()
