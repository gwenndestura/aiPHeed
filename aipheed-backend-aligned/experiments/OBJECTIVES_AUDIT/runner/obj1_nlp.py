"""Objective 1 (OBJ1_PREREGISTRATION.md, hash checked): corpus coverage audit, the labelled-sample tooling, the
issue-date-safe BERTopic evaluation and the pre-registered early-warning test. No forecasting model is fitted.

    python obj1_nlp.py coverage      # corpus, relevance, geography, outlets, duplicates, sufficiency -> ../out/obj1_coverage.json
    python obj1_nlp.py sample        # stratified 300-headline annotation sample (blind) -> ../annotation/
    python obj1_nlp.py score         # agreement and accuracy, only once two annotators have filled the sheets
    python obj1_nlp.py topics        # leakage-safe BERTopic per origin vs the all-quarter model -> ../out/obj1_topics.json
    python obj1_nlp.py earlywarning  # EW1-EW6 Spearman, permutation p, Holm -> ../out/obj1_earlywarning.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
ROOT = EXP.parents[1]
BACKEND = ROOT / "backend"
PLAN = HERE / "OBJ1_PREREGISTRATION.md"
OUT = HERE / "out"
ANN = HERE / "annotation"
SEED = 2036
sys.path.insert(0, str(BACKEND))


def check() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "OBJ1 pre-registration changed"
    return h


def _pipe():
    import os
    os.chdir(BACKEND)
    from app.news import pipeline_v3 as P
    return P


# ================================================================================================ coverage
def coverage():
    P = _pipe()
    C = pd.DataFrame(P.corpus())
    kept, dropped = P.dedupe([a for a in P.corpus() if a["relevant"] == 1])
    A = pd.DataFrame(kept)
    out = {"corpus_headlines": int(len(C)), "quarters": f"{C['quarter'].min()}..{C['quarter'].max()}",
           "relevant_before_dedupe": int(C["relevant"].sum()), "syndicated_copies_dropped": int(len(dropped)),
           "admitted": int(len(A)), "admitted_with_province": int(A["province_code"].notna().sum())}
    out["admitted_province_share"] = out["admitted_with_province"] / max(out["admitted"], 1)
    out["by_province"] = A["province_code"].fillna("none").value_counts().to_dict()
    oc = C["outlet"].value_counts()
    out["outlets"] = {"n": int(len(oc)), "top5_share_of_corpus": float(oc.head(5).sum() / oc.sum()),
                      "hhi": float(((oc / oc.sum()) ** 2).sum()), "top5": oc.head(5).to_dict()}
    ao = A["outlet"].value_counts()
    out["admitted_outlets_top5_share"] = float(ao.head(5).sum() / ao.sum())
    out["store_by_quarter"] = C.groupby("quarter").size().to_dict()
    pq = A.dropna(subset=["province_code"]).groupby(["province_code", "quarter"]).size()
    quarters = sorted(C["quarter"].unique())
    grid = pd.MultiIndex.from_product([sorted(P.PROVINCE_CODES), quarters])
    pq = pq.reindex(grid, fill_value=0)
    out["province_quarters"] = int(len(pq))
    out["sufficient_ge5"] = int((pq >= 5).sum())
    out["sufficient_share"] = float((pq >= 5).mean())
    out["zero_article_share"] = float((pq == 0).mean())
    out["sufficient_by_province"] = {k: int(v) for k, v in (pq >= 5).groupby(level=0).sum().items()}
    out["sufficient_by_year"] = {y: int(v) for y, v in (pq >= 5).groupby(pq.index.get_level_values(1).str[:4]).sum().items()}
    # where do relevant articles without a province come from (geographic attribution gap)
    noprov = A[A["province_code"].isna()]
    out["no_province_examples"] = noprov["title"].head(8).tolist()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "obj1_coverage.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("store_by_quarter", "no_province_examples")}, indent=1))


# ================================================================================================ annotation sample
def sample():
    P = _pipe()
    C = pd.DataFrame(P.corpus())
    kept, _ = P.dedupe([a for a in P.corpus() if a["relevant"] == 1])
    adm = {a["article_key"] for a in kept}
    inten = P.intensities()
    C["admitted"] = C["article_key"].isin(adm).astype(int)
    C["has_province"] = C["province_code"].notna().astype(int)
    C["xlmr"] = C["article_key"].map(inten)
    rng = np.random.default_rng(SEED)
    # strata: admitted with province (scored), admitted national, relevant-but-syndicated or not relevant
    strata = {"admitted_province": (C["admitted"] == 1) & (C["has_province"] == 1),
              "admitted_national": (C["admitted"] == 1) & (C["has_province"] == 0),
              "not_admitted_with_province": (C["admitted"] == 0) & (C["has_province"] == 1),
              "not_admitted_other": (C["admitted"] == 0) & (C["has_province"] == 0)}
    quota = {"admitted_province": 100, "admitted_national": 60, "not_admitted_with_province": 60, "not_admitted_other": 80}
    parts = []
    for s, m in strata.items():
        g = C[m]
        n = min(quota[s], len(g))
        idx = rng.choice(g.index.to_numpy(), n, replace=False)
        parts.append(C.loc[idx].assign(stratum=s, stratum_size=int(len(g))))
    S = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
    S["item"] = np.arange(1, len(S) + 1)
    ANN.mkdir(parents=True, exist_ok=True)
    blank = S[["item", "article_key", "title", "outlet", "ph_date"]].assign(
        food_insecurity_relevant="", province="", food_stress="", notes="")
    for a in ("annotator_A", "annotator_B"):
        p = ANN / f"labels_{a}.csv"
        if not p.exists():                                  # never overwrite a sheet being filled
            blank.to_csv(p, index=False, encoding="utf-8-sig")
    S[["item", "article_key", "stratum", "stratum_size", "relevant", "admitted", "province_code", "xlmr"]].to_csv(
        ANN / "system_outputs_SEALED.csv", index=False)
    print({"items": int(len(S)), "by_stratum": S["stratum"].value_counts().to_dict(),
           "stratum_sizes": {s: int(m.sum()) for s, m in strata.items()}})


def score():
    from sklearn.metrics import cohen_kappa_score, roc_auc_score
    A, B = (pd.read_csv(ANN / f"labels_annotator_{x}.csv", dtype=str) for x in ("A", "B"))
    filled = lambda d: d["food_insecurity_relevant"].fillna("").str.strip().isin(["0", "1"])  # noqa: E731
    if filled(A).sum() < 0.9 * len(A) or filled(B).sum() < 0.9 * len(B):
        raise SystemExit(f"not scored: annotator A filled {int(filled(A).sum())}, B {int(filled(B).sum())} of {len(A)} "
                         "(both must label at least 90%; no label is ever generated by this script)")
    S = pd.read_csv(ANN / "system_outputs_SEALED.csv", dtype={"province_code": str})
    m = A.merge(B, on="item", suffixes=("_A", "_B")).merge(S, on="item")
    m = m[filled(A.set_index("item")).reindex(m["item"]).to_numpy() & filled(B.set_index("item")).reindex(m["item"]).to_numpy()]
    ra, rb = m["food_insecurity_relevant_A"].astype(int), m["food_insecurity_relevant_B"].astype(int)
    res = {"n": int(len(m)), "kappa_relevance": float(cohen_kappa_score(ra, rb))}
    agree = m[ra == rb]
    y, pred = agree["food_insecurity_relevant_A"].astype(int), agree["admitted"].astype(int)
    tp, fp, fn = int(((pred == 1) & (y == 1)).sum()), int(((pred == 1) & (y == 0)).sum()), int(((pred == 0) & (y == 1)).sum())
    res["relevance"] = {"n_agreed": int(len(agree)), "precision": tp / (tp + fp) if tp + fp else None,
                        "recall": tp / (tp + fn) if tp + fn else None,
                        "note": "recall is per stratum-weighted sample; reweight by stratum_size for corpus-level"}
    pa, pb = m["province_A"].fillna("").str.strip(), m["province_B"].fillna("").str.strip()
    res["kappa_province"] = float(cohen_kappa_score(pa, pb))
    g = m[(pa == pb) & m["province_code"].notna()]
    res["geocoder_accuracy"] = {"n": int(len(g)), "accuracy": float((g["province_A"].str.strip() == g["province_code"]).mean())
                                if len(g) else None}
    fs = m[m["xlmr"].notna() & m["food_stress_A"].isin(["0", "1"]) & (m["food_stress_A"] == m["food_stress_B"])]
    res["xlmr_vs_food_stress_auc"] = (float(roc_auc_score(fs["food_stress_A"].astype(int), fs["xlmr"]))
                                      if fs["food_stress_A"].nunique() == 2 else None)
    (OUT / "obj1_annotation_scores.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


# ================================================================================================ topics
def _names() -> set[str]:
    v = pd.read_csv(BACKEND / "data" / "foodinsecurity_engine" / "lgu_vulnerability.csv")
    words = {"calabarzon", "cavite", "laguna", "batangas", "rizal", "quezon"}
    for n in v["lgu_name"].str.lower():
        words |= {w for w in re.split(r"[^a-zñ]+", n.replace("city of ", "")) if len(w) > 3}
    return words - {"city", "general", "santa", "santo", "jose", "juan", "pedro", "maria", "real", "isidro"}


def _npmi(topic_words: list[list[str]], docs: list[set[str]]) -> float:
    n = len(docs)
    vocab = {w for ws in topic_words for w in ws}
    df = {w: sum(1 for d in docs if w in d) for w in vocab}
    vals = []
    for ws in topic_words:
        s = []
        for i in range(len(ws)):
            for j in range(i + 1, len(ws)):
                a, b = ws[i], ws[j]
                co = sum(1 for d in docs if a in d and b in d)
                if co == 0 or df[a] == 0 or df[b] == 0:
                    s.append(-1.0)
                    continue
                pa, pb, pab = df[a] / n, df[b] / n, co / n
                s.append(-1.0 if pab == 1 else math.log(pab / (pa * pb)) / -math.log(pab))
        if s:
            vals.append(float(np.mean(s)))
    return float(np.mean(vals)) if vals else float("nan")


def _fit(titles: list[str], emb: np.ndarray):
    from bertopic import BERTopic
    from bertopic.representation import KeyBERTInspired
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP
    from app.ml.nlp.topic_model import N_GRAM_RANGE, TOP_N_WORDS
    m = BERTopic(embedding_model=_G["enc"], umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine",
                                                             random_state=42),
                 hdbscan_model=HDBSCAN(min_cluster_size=10, metric="euclidean", cluster_selection_method="eom",
                                       prediction_data=True),
                 vectorizer_model=CountVectorizer(ngram_range=N_GRAM_RANGE, stop_words="english", min_df=2),
                 representation_model=KeyBERTInspired(), top_n_words=TOP_N_WORDS, verbose=False)
    topics, _ = m.fit_transform(titles, emb)
    return m, np.asarray(topics)


_G: dict = {}


def _metrics(m, topics, titles, names) -> dict:
    tok = [set(re.findall(r"[a-zñ]+", t.lower())) for t in titles]
    ids = [t for t in m.get_topic_info()["Topic"] if t != -1]
    tw = [[w for w, _ in (m.get_topic(t) or [])][:10] for t in ids]
    tw1 = [[x for w in ws for x in w.split()] for ws in tw]
    place = [any(x in names for w in ws[:3] for x in w.split()) for ws in tw]
    return {"n_docs": len(titles), "n_topics": len(ids), "outlier_share": float((topics == -1).mean()),
            "npmi_mean": _npmi([ws[:10] for ws in tw1], tok), "place_name_topic_share": float(np.mean(place)) if place else None}


def topics():
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics import adjusted_rand_score
    pre = check()
    P = _pipe()
    C = pd.DataFrame(P.corpus()).sort_values(["published_ph", "article_key"]).reset_index(drop=True)
    _G["enc"] = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    emb = _G["enc"].encode(C["title"].tolist(), batch_size=64, show_progress_bar=False, normalize_embeddings=False)
    names = _names()
    pub = pd.to_datetime(C["published_ph"].str[:19])
    res = {"prereg_sha256": pre, "deviation": "the plan text said English and Filipino stop words; the served setting "
           "(English stop words) was used, as the plan's rule 'served settings, unchanged' requires", "origins": {}}
    m_all, t_all = _fit(C["title"].tolist(), emb)
    res["all_quarter_model"] = _metrics(m_all, t_all, C["title"].tolist(), names)
    prev = None
    qs = [f"{y}-Q{q}" for y in range(2022, 2027) for q in range(1, 5)]
    qs = [q for q in qs if q <= "2026-Q3"]
    for q in qs:
        y, k = int(q[:4]), int(q[-1])
        O = pd.Timestamp(year=y + (k == 4), month=1 if k == 4 else 3 * k + 1, day=1)     # issue date O(t) = next quarter start
        mask = (pub < O).to_numpy()
        tit = C.loc[mask, "title"].tolist()
        m, tp = _fit(tit, emb[mask])
        met = _metrics(m, tp, tit, names)
        keys = C.loc[mask, "article_key"].to_numpy()
        if prev is not None:
            common = np.isin(keys, prev[0])
            pk = dict(zip(prev[0], prev[1]))
            met["ari_vs_previous_fit"] = float(adjusted_rand_score([pk[x] for x in keys[common]], tp[common]))
        prev = (keys, tp)
        res["origins"][q] = met
        print(q, met, flush=True)
    o = list(res["origins"].values())
    res["summary"] = {"npmi_mean": float(np.nanmean([x["npmi_mean"] for x in o])),
                      "place_name_share_mean": float(np.nanmean([x["place_name_topic_share"] for x in o])),
                      "ari_mean": float(np.nanmean([x["ari_vs_previous_fit"] for x in o if "ari_vs_previous_fit" in x]))}
    s = res["summary"]
    res["eligible_as_features"] = bool(s["npmi_mean"] > 0 and s["place_name_share_mean"] < .5 and s["ari_mean"] >= .3)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "obj1_topics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"all_quarter": res["all_quarter_model"], "summary": s, "eligible": res["eligible_as_features"]}, indent=1))


def topic_props():
    """Leakage-safe latent patterns per province-quarter: for each quarter t, the model fitted at O(t) on headlines
    published before O(t) (the topics() fits, served settings) assigns quarter t's province-tagged headlines; shares per
    province and topic, with each topic's top words. Quarters whose fit has fewer than 300 headlines are skipped."""
    from sentence_transformers import SentenceTransformer
    pre = check()
    P = _pipe()
    C = pd.DataFrame(P.corpus()).sort_values(["published_ph", "article_key"]).reset_index(drop=True)
    _G["enc"] = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    emb = _G["enc"].encode(C["title"].tolist(), batch_size=64, show_progress_bar=False)
    pub = pd.to_datetime(C["published_ph"].str[:19])
    rows, meta = [], {}
    for q in sorted(C["quarter"].unique()):
        y, k = int(q[:4]), int(q[-1])
        O = pd.Timestamp(year=y + (k == 4), month=1 if k == 4 else 3 * k + 1, day=1)
        mask = (pub < O).to_numpy()
        if mask.sum() < 300:
            meta[q] = {"status": "skipped", "fit_docs": int(mask.sum())}
            continue
        m, tp = _fit(C.loc[mask, "title"].tolist(), emb[mask])
        sub = C.loc[mask].assign(topic=tp)
        sub = sub[(sub["quarter"] == q) & sub["province_code"].notna()]
        words = {t: ", ".join(w for w, _ in (m.get_topic(t) or [])[:5]) for t in set(sub["topic"]) if t != -1}
        for (pc, t), n in sub.groupby(["province_code", "topic"]).size().items():
            rows.append({"province_code": pc, "quarter": q, "topic": int(t), "n": int(n),
                         "share": n / int((sub["province_code"] == pc).sum()),
                         "topic_words": "outlier" if t == -1 else words.get(t, ""), "fit_origin_issue": str(O.date()),
                         "fit_docs": int(mask.sum())})
        meta[q] = {"status": "ok", "fit_docs": int(mask.sum()), "province_tagged_docs": int(len(sub))}
        print(q, meta[q], flush=True)
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_csv(OUT / "obj1_topic_proportions_timesafe.csv", index=False)
    pq = D.groupby(["province_code", "quarter"]).size()
    res = {"prereg_sha256": pre, "quarters": meta, "province_quarters_with_patterns": int(len(pq)),
           "use": "descriptive latent patterns (pre-registered rule failed coherence and place-name share); "
                  "issue-date safe: each quarter's topics come from a model fitted only on earlier-published headlines"}
    (OUT / "obj1_topic_proportions_timesafe.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "quarters"}, indent=1))


# ================================================================================================ early warning
def earlywarning():
    from scipy.stats import spearmanr
    pre = check()
    sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
    import iv2_lib as V
    H = V.H
    d = H.load()
    lab = V.area_labels(d)
    lab = lab[lab["area"] == "BL"].set_index("q")["H"]
    T = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "table_pooled.csv", dtype={"area": str})
    T = T[(T["area"] == "BL") & (T["lead"] == 1)].set_index("t").sort_index()
    z = pd.read_csv(EXP / "NEW_MODEL" / "NEWS_V2" / "out" / "news_anomalies.csv").set_index("t")["z_N1R"]
    sig = pd.DataFrame({"EW1_z_N1R": z, "EW2_dN1R": T["N1R"] - T["N1R"].reindex(T.index - 1).to_numpy(),
                        "EW3_price_share": T["price_share"], "EW4_shortage_share": T["shortage_share"],
                        "EW5_disaster_share": T["disaster_share"], "EW6_jobs_income_share": T["jobs_income_share"]})
    sig = sig[(sig.index >= V.NEWS_ERA) & (sig.index <= H.qi("2026-Q2"))]
    dlt = pd.Series({t: lab.get(t + 1, np.nan) - T.loc[t, "h_last"] for t in sig.index})
    rng = np.random.default_rng(SEED)
    res = {"prereg_sha256": pre, "tests": {}}
    for c in sig.columns:
        g = pd.DataFrame({"s": sig[c], "d": dlt}).dropna()
        r = float(spearmanr(g["s"], g["d"])[0]) if len(g) >= 5 else float("nan")
        perm = [spearmanr(rng.permutation(g["s"].to_numpy()), g["d"])[0] for _ in range(10000)] if len(g) >= 5 else []
        p = float(np.mean(np.asarray(perm) >= r)) if perm else float("nan")
        hit = float(np.mean(np.sign(g["s"] - g["s"].median()) == np.sign(g["d"]))) if len(g) else float("nan")
        res["tests"][c] = {"n": int(len(g)), "spearman": r, "p_one_sided": p, "direction_hit_rate": hit}
    items = sorted(res["tests"].items(), key=lambda x: x[1]["p_one_sided"])
    run = 0.0
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * v["p_one_sided"]))
        v["p_holm"] = run
        v["significant"] = bool(run < .05 and v["spearman"] > 0)
    res["any_significant"] = any(v["significant"] for v in res["tests"].values())
    (OUT / "obj1_earlywarning.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"coverage": coverage, "sample": sample, "score": score, "topics": topics, "topic_props": topic_props,
     "earlywarning": earlywarning}[sys.argv[1]]()
