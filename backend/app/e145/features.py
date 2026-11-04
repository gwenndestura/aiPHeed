"""
E145 province-window news features, as of each issue date (PROTOCOL.md section 4). No survey outcome is used.

    python -m app.e145.features embed     # embeddings of gated text, cached by hash
    python -m app.e145.features build     # data/e145/out/news_features.parquet, one row per origin x lead x key x survey

BERTopic is fitted once per (test origin, lead) on gated articles published before that origin's issue date, so training
rows and the test row share one topic space and the topic space never sees the future. For speed the fit uses a fixed
seeded sample of at most FIT_N documents; the other documents published before the issue date are assigned with transform.
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

from app.e137 import features as F
from app.e145 import OUT, RAW

K = 10.0
W_MONTHS = 12
LEADS = list(range(1, 9))
FIT_N = 8000
N_TOPICS = 6
SEED = 145
ORIGIN_SURVEYS = {"O1": ["NNS2013", "FNRI2015"], "O2": ["NNS2013", "FNRI2015", "ENNS2018"],
                  "O3": ["NNS2013", "FNRI2015", "ENNS2018", "ENNS2019"]}
SURVEY_YEAR = {"NNS2013": 2013, "FNRI2015": 2015, "ENNS2018": 2018, "ENNS2019": 2019}
PREV = {"FNRI2015": "NNS2013", "ENNS2018": "FNRI2015", "ENNS2019": "FNRI2015"}
RAW_COLS = ["nr_volume", "nr_count", "nr_mean"]
TOPIC_COLS = [f"nb_topic_{i}" for i in range(N_TOPICS)]
BC_COLS = ["nb_fssi", "nb_attention", "nb_fssi_delta"] + TOPIC_COLS


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def articles() -> pd.DataFrame:
    a = pd.read_parquet(RAW / "articles_clean.parquet")
    s = pd.read_parquet(RAW / "xlmr_scores.parquet")
    a = a.merge(s, on="hash", how="left")
    a["stress_score"] = a[["p_harder", "p_hardship"]].max(axis=1)
    a["stress"] = (a["stress_score"] >= 0.5) & (a["p_response"].fillna(0) < 0.5)
    return a


def window_stats(a: pd.DataFrame, keys: list[str], issue: pd.Timestamp) -> pd.DataFrame:
    w = a[(a["published"] < issue) & (a["published"] >= issue - pd.DateOffset(months=W_MONTHS))]
    g = w.groupby("key")
    t = pd.DataFrame({"n": g["id"].nunique(), "r": g["stress"].sum(), "mean_score": g["stress_score"].mean()}).reindex(keys)
    t[["n", "r"]] = t[["n", "r"]].fillna(0)
    rho = t["r"].sum() / t["n"].sum() if t["n"].sum() > 0 else np.nan
    t["nr_volume"], t["nr_count"], t["nr_mean"] = np.log1p(t["n"]), np.log1p(t["r"]), t["mean_score"]
    t["nb_fssi"] = _logit((t["r"] + K * rho) / (t["n"] + K)) - _logit(rho) if rho == rho and rho > 0 else np.nan
    lv = np.log1p(t["n"])
    t["nb_attention"] = lv - lv.mean()
    return t.drop(columns=["mean_score"]).reset_index()


def _mask_places(text: str, rx) -> str:
    return rx.sub(" ", text)


def embed() -> None:
    from sentence_transformers import SentenceTransformer
    t = pd.read_parquet(RAW / "to_score.parquet")
    keys = sorted(pd.read_parquet(RAW / "articles_clean.parquet")["key"].unique())
    rx = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys + ["philippines", "manila", "province", "city"]) + r")\b", re.I)
    m = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
    t["masked"] = t["text"].map(lambda s: _mask_places(s, rx))
    v = m.encode(t["masked"].tolist(), batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    np.save(RAW / "embeddings.npy", np.asarray(v, dtype=np.float32))
    t[["hash", "masked"]].to_parquet(RAW / "embeddings_index.parquet", index=False)
    print(v.shape)


def topic_assign(cutoff: pd.Timestamp, a: pd.DataFrame, idx: pd.DataFrame, emb: np.ndarray) -> pd.Series:
    """hash -> topic (0..N_TOPICS-1, or -1), from a BERTopic fitted only on documents published before `cutoff`."""
    import hdbscan
    import umap
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer
    first = a[a["gated"]].groupby("hash")["published"].min()
    pos = pd.Series(np.arange(len(idx)), index=idx["hash"])
    h = first[first < cutoff].index.intersection(pos.index)
    h = np.array(sorted(h))
    if len(h) < 200:
        return pd.Series(dtype=int)
    rng = np.random.default_rng(SEED)
    fit = rng.choice(h, min(FIT_N, len(h)), replace=False)
    docs = idx.set_index("hash")["masked"]
    stop = ["ang", "ng", "sa", "na", "at", "mga", "para", "ay", "si", "ni", "the", "of", "and", "to", "in", "on", "for", "a", "is",
            "that", "with", "by", "as", "from", "it", "was", "are", "at", "be", "has", "have", "an", "this", "will", "said"]
    tm = BERTopic(umap_model=umap.UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=SEED),
                  hdbscan_model=hdbscan.HDBSCAN(min_cluster_size=30, metric="euclidean", prediction_data=True),
                  vectorizer_model=CountVectorizer(stop_words=stop, ngram_range=(1, 2), min_df=3), nr_topics=N_TOPICS + 1,
                  calculate_probabilities=False, verbose=False)
    tm.fit_transform(docs.loc[fit].tolist(), emb[pos.loc[fit].values])
    pred, _ = tm.transform(docs.loc[h].tolist(), emb[pos.loc[h].values])
    return pd.Series(pred, index=h)


def build() -> pd.DataFrame:
    from joblib import Parallel, delayed
    from app.e141 import panel as P
    a = articles()
    out_rows = P.outcomes()[["key", "survey"]]
    keys = sorted(out_rows["key"].unique())
    # non-topic features, one table per survey x lead
    base = []
    for s, y in SURVEY_YEAR.items():
        for h in LEADS:
            t = window_stats(a, keys, F.issue_date(y, h))
            t["survey"], t["lead"] = s, h
            base.append(t)
    base = pd.concat(base, ignore_index=True)
    prev = base[["key", "survey", "lead", "nb_fssi"]].rename(columns={"survey": "prev_s", "nb_fssi": "prev_fssi"})
    base["prev_s"] = base["survey"].map(PREV)
    base = base.merge(prev, on=["key", "prev_s", "lead"], how="left")
    base["nb_fssi_delta"] = base["nb_fssi"] - base["prev_fssi"]
    base = base.drop(columns=["prev_s", "prev_fssi"])

    idx = pd.read_parquet(RAW / "embeddings_index.parquet")
    emb = np.load(RAW / "embeddings.npy")

    def one(o, h):
        target = ORIGIN_SURVEYS[o][-1]
        tp = topic_assign(F.issue_date(SURVEY_YEAR[target], h), a, idx, emb)
        rows = []
        for s in ORIGIN_SURVEYS[o]:
            d = F.issue_date(SURVEY_YEAR[s], h)
            w = a[a["gated"] & (a["published"] < d) & (a["published"] >= d - pd.DateOffset(months=W_MONTHS))].copy()
            w["topic"] = w["hash"].map(tp)
            w = w[w["topic"].notna()]
            nat = w["topic"].value_counts(normalize=True)
            n = w.groupby("key").size().reindex(keys).fillna(0)
            for i in range(N_TOPICS):
                c = w[w["topic"] == i].groupby("key").size().reindex(keys).fillna(0)
                rho = float(nat.get(i, 0.0))
                rows.append(pd.DataFrame({"key": keys, "survey": s, "t": f"nb_topic_{i}", "v": (c + K * rho).values / (n + K).values - rho}))
        r = pd.concat(rows).pivot_table(index=["key", "survey"], columns="t", values="v").reset_index()
        r["origin"], r["lead"] = o, h
        return r

    tops = Parallel(n_jobs=8)(delayed(one)(o, h) for o in ORIGIN_SURVEYS for h in LEADS)
    T = pd.concat(tops, ignore_index=True)
    res = T.merge(base, on=["key", "survey", "lead"], how="left")
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_parquet(OUT / "news_features.parquet", index=False)
    print(res.shape, res.isna().mean().round(3).to_dict())
    return res


if __name__ == "__main__":
    {"embed": embed, "build": build}[sys.argv[1]]()
