"""
Quarterly province input panel for E148, as of each issue quarter. Reads no 2021 label.

    python -m app.e148.panel build   -> data/e148/out/{gov_panel,news_panel}.parquet

Quarter index: qi = year*4 + quarter - 1 (app.fi5.target). Issue date = first day of the quarter.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e144 import OUT as O144
from app.e144 import data as D
from app.e145 import features as X
from app.e145.features import BC_COLS, RAW_COLS
from app.e147 import RAW as R147
from app.e147 import features as Fe
from app.e148 import OUT
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

FIRST, LAST = qindex("2013-Q1"), qindex("2026-Q4")
if os.getenv("AIPHEED_LIVE_ASOF"):          # a live issue after 2026-Q4 extends the panels to its quarter (app.e168.live_refresh)
    _t = pd.Timestamp(os.getenv("AIPHEED_LIVE_ASOF"))
    LAST = max(LAST, _t.year * 4 + (_t.month - 1) // 3)
QUARTERLY = ["c_soil_anom_3m", "c_rain_anom_6m", "c_tc_4q", "c_agri_yoy", "c_fish_yoy", "oni", "unemp_rate", "remit_yoy"]
ANCHOR_LAG = 6
TOPIC_CUTOFF = {"O2": "2016-07-01", "O3": "2017-07-01", "F": "2019-07-01"}
NEWS_LAST_ISSUE = qindex("2021-Q3")


def q_start(i: int) -> pd.Timestamp:
    """Information cut-off for issue quarter i: its first day, or, for the live issue only, the later as-of date set by
    the live refresh (AIPHEED_LIVE_ASOF, a day inside quarter i; app.e168.live_refresh). Past quarters never move."""
    d = pd.Timestamp(year=i // 4, month=3 * (i % 4) + 1, day=1)
    a = os.getenv("AIPHEED_LIVE_ASOF")
    if a:
        t = pd.Timestamp(a).normalize()
        if t.year * 4 + (t.month - 1) // 3 == i and t > d:
            return t
    return d


def _one(k_key, i):
    return {"key": k_key, "qi": i, **Fe.gov_row(k_key.replace(" ", ""), q_start(i))}


def _region_unemp() -> dict:
    d = pd.read_csv(BACKEND_DIR / "data" / "pfi" / "raw" / "psa_sdg_unemployment_region.csv")
    d = d[(d["Age Group"] == "15 years and above") & (d["Sex"] == "Both sexes")].copy()
    d["g"] = d["Geolocation"].str.replace(".", "", regex=False).str.strip()
    return {g: {int(y): pd.to_numeric(r[y], errors="coerce") for y in d.columns if y.isdigit()} for g, r in d.set_index("g").iterrows()}


def build_gov() -> pd.DataFrame:
    base = Fe.base_rows().drop_duplicates("key")
    jobs = [(k, i) for k in base["key"] for i in range(FIRST, LAST + 1)]
    G = pd.DataFrame(Parallel(n_jobs=18, batch_size=40)(delayed(_one)(k, i) for k, i in jobs))
    q = pd.read_csv(BACKEND_DIR.parent / "aipheed-backend-aligned" / "experiments" / "CORRECTED_PIPELINE" / "out" / "remittances_quarterly_corrected.csv")
    q["qi"] = q["quarter"].map(qindex)
    s = q.set_index("qi")["remit_usd_bn"]
    yoy = pd.Series({i: 100 * (s[i] / s[i - 4] - 1) for i in s.index if i - 4 in s.index})
    # released about 2 months after the quarter: usable for the issue two quarters later at the latest
    G["remit_q_yoy"] = G["qi"].map(lambda i: yoy.get(i - 2, np.nan))
    ru = _region_unemp()
    reg = base.set_index("key")["region"].to_dict()
    names = {"Ilocos": "Region I", "Cagayan Valley": "Region II", "Central Luzon": "Region III", "CALABARZON": "Region IV-A", "MIMAROPA": "MIMAROPA Region", "Bicol": "Region V", "Western Visayas": "Region VI",
             "Central Visayas": "Region VII", "Eastern Visayas": "Region VIII", "Zamboanga Peninsula": "Region IX", "Northern Mindanao": "Region X", "Davao": "Region XI", "SOCCSKSARGEN": "Region XII", "Caraga": "Region XIII",
             "ARMM": "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)", "CAR": "Cordillera Administrative Region (CAR)"}
    def rate(k, i):
        y = i // 4 - 1 if i % 4 >= 1 else i // 4 - 2              # annual rate usable from the second quarter of the following year
        return ru.get(names.get(reg.get(k, ""), ""), {}).get(y, np.nan)
    G["unemp_region"] = [rate(k, i) for k, i in zip(G["key"], G["qi"])]
    OUT.mkdir(parents=True, exist_ok=True)
    G.to_parquet(OUT / "gov_panel.parquet", index=False)
    print("gov", G.shape, G.drop(columns=["key", "qi"]).notna().mean().round(2).to_dict(), flush=True)
    return G


def _topics(cutoff: pd.Timestamp, a, idx, emb) -> pd.Series:
    """BERTopic fitted on documents before `cutoff`; every later document is only assigned, never fitted."""
    import hdbscan
    import umap
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer
    first = a[a["gated"]].groupby("hash")["published"].min()
    pos = pd.Series(np.arange(len(idx)), index=idx["hash"])
    all_h = np.array(sorted(first.index.intersection(pos.index)))
    h = np.array(sorted(first[first < cutoff].index.intersection(pos.index)))
    rng = np.random.default_rng(X.SEED)
    fit = rng.choice(h, min(X.FIT_N, len(h)), replace=False)
    docs = idx.set_index("hash")["masked"]
    stop = ["ang", "ng", "sa", "na", "at", "mga", "para", "ay", "si", "ni", "the", "of", "and", "to", "in", "on", "for", "a", "is", "that", "with", "by", "as", "from", "it", "was", "are", "be", "has", "have", "an", "this", "will", "said"]
    tm = BERTopic(umap_model=umap.UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=X.SEED),
                  hdbscan_model=hdbscan.HDBSCAN(min_cluster_size=30, metric="euclidean", prediction_data=True),
                  vectorizer_model=CountVectorizer(stop_words=stop, ngram_range=(1, 2), min_df=3), nr_topics=X.N_TOPICS + 1, calculate_probabilities=False, verbose=False)
    tm.fit_transform(docs.loc[fit].tolist(), emb[pos.loc[fit].values])
    pred, _ = tm.transform(docs.loc[all_h].tolist(), emb[pos.loc[all_h].values])
    return pd.Series(pred, index=all_h)


def _news_origin(o, a, idx, emb, keys):
    tp = _topics(pd.Timestamp(TOPIC_CUTOFF[o]), a, idx, emb)
    rows = []
    for i in range(qindex("2013-Q1"), NEWS_LAST_ISSUE + 1):
        d = q_start(i)
        t = X.window_stats(a, keys, d)
        w = a[a["gated"] & (a["published"] < d) & (a["published"] >= d - pd.DateOffset(months=X.W_MONTHS))].copy()
        w["topic"] = w["hash"].map(tp)
        w = w[w["topic"].notna()]
        nat = w["topic"].value_counts(normalize=True)
        n = w.groupby("key").size().reindex(keys).fillna(0)
        for j in range(X.N_TOPICS):
            c = w[w["topic"] == j].groupby("key").size().reindex(keys).fillna(0)
            rho = float(nat.get(j, 0.0))
            t[f"nb_topic_{j}"] = (c + X.K * rho).values / (n + X.K).values - rho
        t["qi"], t["origin"] = i, o
        rows.append(t)
    return pd.concat(rows, ignore_index=True)


def build_news() -> pd.DataFrame:
    X.RAW = R147
    a = X.articles()
    a["published"] = pd.to_datetime(a["published"])
    keys = sorted(Fe.base_rows()["key"].unique())
    idx, emb = pd.read_parquet(R147 / "embeddings_index.parquet"), np.load(R147 / "embeddings.npy")
    N = pd.concat(Parallel(n_jobs=3)(delayed(_news_origin)(o, a, idx, emb, keys) for o in TOPIC_CUTOFF), ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    N.to_parquet(OUT / "news_panel.parquet", index=False)
    print("news", N.shape, flush=True)
    return N


COLS_NEWS = BC_COLS
COLS_RAW = RAW_COLS


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build_gov()
        build_news()
