"""Objective 1: two-tier NLP pipeline -> domain-distributed, bias-corrected Food Stress Sentiment Index (FSSI).

Tier 1 (XLM-RoBERTa, zero-shot). Every unique headline is scored against fixed natural-language hypotheses with
joeddav/xlm-roberta-large-xnli (multilingual NLI; Filipino and English premises, English hypotheses; Yin et al.
2019 zero-shot-by-entailment). The hypotheses say *what the article is about* (one per explanatory domain, so an
article can carry several domains), *what kind of evidence it is* (an actual hunger report vs a government response)
and its *direction* (conditions getting worse vs improving). Scores are cached per (article, model, hypothesis set).

Tier 2 (BERTopic). Relevant headlines are embedded with paraphrase-multilingual-MiniLM-L12-v2, clustered with
UMAP + HDBSCAN (number of topics not fixed), and each topic is mapped to the domain most of its members carry. The
topic model is fitted on 2021-2022 headlines only and then frozen, so topic features for later quarters are
out-of-sample with respect to the topic model.

FSSI (per province-quarter and per domain). Counting events, not articles; correcting for coverage volume, source
concentration and thin cells:

    1. duplicate headlines and repeated reports of one event (same domain, cosine >= 0.90 within 7 days) collapse to
       one event;
    2. each event gets stress s = P(worse) - P(better) in [-1, 1] and domain relevance r_d = P(domain);
    3. within a cell, an outlet's events are down-weighted by 1/sqrt(events from that outlet in the cell);
    4. raw FSSI_d = sum(w * r_d * max(s, 0)) / sum(w) over ALL events collected for the cell, so a cell with more
       coverage does not automatically score higher (a share, not a count);
    5. corrected FSSI_d = (n * raw + k * regional_value) / (n + k), k = 10 (empirical-Bayes shrinkage of thin
       province cells toward the region for the same quarter); the region value itself is not shrunk;
    6. the model never sees the level directly: features.py standardises it against the cell's own earlier quarters
       (as-of), which removes the long upward drift in collected volume.

Raw counts, raw and corrected values and n are all kept in the output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from app.fi5.paths import NEWS_ARTICLES, NLP

XLMR_MODEL = "joeddav/xlm-roberta-large-xnli"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

DOMAINS = ["market", "climate", "employment", "remittance", "poverty"]
TEMPLATE = "This news is about {}."
LABELS = {   # short label phrases; checked on hand-written English/Filipino sanity headlines before scoring
    "market": "food prices or food supply",
    "climate": "typhoons, floods or drought damaging crops",
    "employment": "jobs or job losses",
    "remittance": "overseas Filipino workers or remittances",
    "poverty": "poverty, hunger or food aid for families",
    "hunger_report": "people going hungry",
    "gov_response": "government aid or relief",
    "worse": "a worsening situation",
    "better": "an improving situation",
}
HYPOTHESES = {k: TEMPLATE.format(v) for k, v in LABELS.items()}
STAGE1 = DOMAINS                                   # every headline that passes the relevance gate
STAGE2 = ["hunger_report", "gov_response", "worse", "better"]   # only headlines with at least one domain
# Recall-oriented relevance gate (English + Filipino terms). Headlines that fail it are labelled irrelevant without
# being scored; this keeps CPU scoring of XLM-R large tractable and removes off-topic false positives.
GATE = re.compile(r"\b(food|rice|bigas|palay|presyo|prices?|inflation|implasyon|supply|shortages?|kakulangan|farmers?|"
                  r"magsasaka|fisher\w*|mangingisda|isda|fish\w*|vegetables?|gulay|onions?|sibuyas|sugar|asukal|pork|"
                  r"baboy|chicken|manok|eggs?|itlog|harvests?|ani|crops?|pananim|agri\w*|nfa|typhoons?|tropical|bagyo|floods?|"
                  r"flooding|flooded|farms?|baha|drought|tagtuyot|el ni[nñ]o|la ni[nñ]a|storms?|landslides?|damage\w*|pinsala|jobs?|"
                  r"trabaho|unemploy\w*|layoffs?|laid off|retrench\w*|workers?|manggagawa|livelihoods?|kabuhayan|wages?|"
                  r"sahod|ofws?|overseas|remittances?|padala|migrant\w*|deploy\w*|repatriat\w*|poor|mahirap|"
                  r"poverty|kahirapan|hunger|hungry|gutom|nagugutom|malnutrition|malnourished|stunting|food packs?|"
                  r"relief|ayuda|aid|tulong|4ps|pantawid|dswd|subsid\w*|cash assistance|feeding|kitchen|ration\w*)\b",
                  re.IGNORECASE)
HYP_HASH = hashlib.sha256(json.dumps(HYPOTHESES, sort_keys=True).encode()).hexdigest()[:12]
RELEVANCE_THRESHOLD = 0.30     # P(domain) >= 0.30; set by reading sampled headlines in the 0.15-0.5 band (most
                               # on-domain at >= 0.3), before any forecasting result was seen
HUNGER_REPORT_THRESHOLD = 0.90  # "actual food insecurity" evidence type: only the >= 0.9 band was mostly real
                                # deprivation reports when sampled (0.5-0.9 were mostly programme/policy news)
TOPIC_DOMAIN_MIN_SHARE = 0.30  # a topic maps to a domain only if >= 30 % of its relevant members carry it
DEDUP_COSINE = 0.90
DEDUP_DAYS = 7
SHRINK_K = 10.0
PROVINCES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Batangas",
             "PH040400000": "Rizal", "PH040500000": "Quezon"}

SCORES = NLP / "xlmr_scores.parquet"
ARTICLES = NLP / "articles.parquet"
TOPICS = NLP / "bertopic_topics.csv"
ARTICLE_TOPICS = NLP / "article_topics.parquet"
FSSI = NLP / "fssi_province_quarter.csv"
EMBEDDINGS = NLP / "embeddings.npy"


def norm_title(t: str) -> str:
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", str(t))          # strip a trailing " - Outlet" suffix
    return re.sub(r"[^0-9a-zÀ-ɏ]+", " ", t.lower()).strip()


def load_corpus() -> pd.DataFrame:
    """Union of the collected Filipino-English news corpora (2021-01 .. 2026-10), one row per article."""
    frames = [pd.read_json(p, lines=True, dtype=False) for p in NEWS_ARTICLES if p.exists()]
    df = pd.concat(frames, ignore_index=True).drop_duplicates("article_key")
    df = df[["article_key", "ph_date", "quarter", "source_domain", "geo_province_code", "first_query_id", "title"]]
    df["geo_province_code"] = df["geo_province_code"].where(df["geo_province_code"].isin(PROVINCES), None)
    df["ph_date"] = pd.to_datetime(df["ph_date"], errors="coerce")
    df = df.dropna(subset=["ph_date", "title"])
    df["title_norm"] = df["title"].map(norm_title)
    df = df[df["title_norm"].str.len() >= 12]
    df["lang_hint"] = np.where(df["first_query_id"].astype(str).str.startswith(("fil", "reg_fil", "trg_fil")), "fil", "en")
    return df.sort_values(["ph_date", "article_key"]).reset_index(drop=True)


def _model_revision() -> str:
    from huggingface_hub import scan_cache_dir
    try:
        for repo in scan_cache_dir().repos:
            if repo.repo_id == XLMR_MODEL:
                return sorted(r.commit_hash for r in repo.revisions)[0][:12]
    except Exception:
        pass
    return "unknown"


def _nli(tok, model, prem: list[str], hyp: list[str], batch: int = 32, device: str = "cpu") -> np.ndarray:
    import torch
    ent, con = model.config.label2id.get("entailment", 2), model.config.label2id.get("contradiction", 0)
    out = np.empty(len(prem))
    order = np.argsort([len(x) for x in prem], kind="stable")      # length-sorted batches: less padding
    with torch.inference_mode():
        for j in range(0, len(order), batch):
            idx = order[j:j + batch]
            enc = tok([prem[i] for i in idx], [hyp[i] for i in idx], return_tensors="pt", padding=True,
                      truncation=True, max_length=96).to(device)
            lg = model(**enc).logits[:, [con, ent]].float()
            out[idx] = torch.softmax(lg, dim=1)[:, 1].cpu().numpy()
    return out


def load_scores() -> pd.DataFrame:
    """The main cache plus any shard files written by parallel workers (same model revision and hypotheses)."""
    files = [f for f in [SCORES, *sorted(NLP.glob("xlmr_scores_part_*.parquet"))] if f.exists()]
    if not files:
        return pd.DataFrame()
    d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    d = d[(d["hyp_hash"] == HYP_HASH)]
    return d.drop_duplicates("title_norm", keep="first").reset_index(drop=True)


def score_xlmr(df: pd.DataFrame, checkpoint_every: int = 300, part: tuple[float, float] = (0.0, 1.0),
               device: str = "cpu", threads: int | None = None) -> pd.DataFrame:
    """Gate, then zero-shot entailment probabilities (stage 1: domains; stage 2: evidence type and direction for
    headlines with a domain). One row per unique normalised headline; cached and resumable. `part` gives a worker a
    fixed slice (fractions of the not-yet-scored headlines, sorted) so a GPU and CPU workers can run side by side;
    each worker writes its own shard file and load_scores() merges them."""
    import os

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(threads or max(1, (os.cpu_count() or 4) - 2))
    rev = _model_revision()
    u = df.drop_duplicates("title_norm")[["title_norm", "title"]].sort_values("title_norm").reset_index(drop=True)
    u["gate"] = u["title"].map(lambda t: bool(GATE.search(str(t))))
    done = load_scores()
    if len(done) and done["model_rev"].iloc[0] != rev:
        done = pd.DataFrame()
    have = set(done["title_norm"]) if len(done) else set()
    todo = u[~u["title_norm"].isin(have)].reset_index(drop=True)
    a, b = int(round(part[0] * len(todo))), int(round(part[1] * len(todo)))
    todo = todo.iloc[a:b]
    target = SCORES if part == (0.0, 1.0) else NLP / f"xlmr_scores_part_{part[0]:.3f}_{part[1]:.3f}.parquet"
    own = pd.read_parquet(target) if target.exists() else pd.DataFrame()
    parts = [own] if len(own) else []
    if len(todo):
        tok = AutoTokenizer.from_pretrained(XLMR_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(XLMR_MODEL).eval().to(device)
        for i in range(0, len(todo), checkpoint_every):
            c = todo.iloc[i:i + checkpoint_every].reset_index(drop=True)
            res = pd.DataFrame({"title_norm": c["title_norm"], "gate": c["gate"]})
            for h in HYPOTHESES:
                res[f"p_{h}"] = 0.0 if h in STAGE1 else np.nan
            g = c.index[c["gate"]].to_numpy()
            if len(g):
                prem = [c.at[k, "title"] for k in g for _ in STAGE1]
                hyp = [HYPOTHESES[h] for _ in g for h in STAGE1]
                p1 = _nli(tok, model, prem, hyp, device=device).reshape(len(g), len(STAGE1))
                for j, h in enumerate(STAGE1):
                    res.loc[g, f"p_{h}"] = p1[:, j]
                g2 = g[(p1 >= RELEVANCE_THRESHOLD).any(axis=1)]
                if len(g2):
                    prem = [c.at[k, "title"] for k in g2 for _ in STAGE2]
                    hyp = [HYPOTHESES[h] for _ in g2 for h in STAGE2]
                    p2 = _nli(tok, model, prem, hyp, device=device).reshape(len(g2), len(STAGE2))
                    for j, h in enumerate(STAGE2):
                        res.loc[g2, f"p_{h}"] = p2[:, j]
            res["model"], res["model_rev"], res["hyp_hash"] = XLMR_MODEL, rev, HYP_HASH
            parts.append(res)
            pd.concat(parts, ignore_index=True).to_parquet(target, index=False)
            print(f"[{device} {part}] scored {min(i + checkpoint_every, len(todo))}/{len(todo)}", flush=True)
    return load_scores()


def backfill_stage2(df: pd.DataFrame) -> pd.DataFrame:
    """Ask the stage-2 questions of every relevant headline that lacks them (e.g. after the relevance threshold was
    lowered from 0.5 to 0.3); results are written into the main cache."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    sc = load_scores()
    rel = sc[[f"p_{d}" for d in STAGE1]].max(axis=1) >= RELEVANCE_THRESHOLD
    need = sc.index[rel & sc["p_worse"].isna()]
    if len(need):
        titles = df.drop_duplicates("title_norm").set_index("title_norm")["title"]
        tok = AutoTokenizer.from_pretrained(XLMR_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(XLMR_MODEL).eval()
        prem = [titles[sc.at[k, "title_norm"]] for k in need for _ in STAGE2]
        hyp = [HYPOTHESES[h] for _ in need for h in STAGE2]
        p2 = _nli(tok, model, prem, hyp).reshape(len(need), len(STAGE2))
        for j, h in enumerate(STAGE2):
            sc.loc[need, f"p_{h}"] = p2[:, j]
        sc.to_parquet(SCORES, index=False)
        for f in NLP.glob("xlmr_scores_part_*.parquet"):
            f.unlink()
    print(f"stage-2 backfilled for {len(need)} headlines")
    return sc


def label_articles(df: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    """Attach scores and derive multi-label domains, evidence type and stress."""
    a = df.merge(scores.drop(columns=["model", "model_rev", "hyp_hash"]), on="title_norm", how="left")
    a[[f"p_{h}" for h in STAGE2]] = a[[f"p_{h}" for h in STAGE2]].fillna(0.0)
    for d in DOMAINS:
        a[f"is_{d}"] = a[f"p_{d}"] >= RELEVANCE_THRESHOLD
    a["n_domains"] = a[[f"is_{d}" for d in DOMAINS]].sum(axis=1)
    a["relevant"] = a["n_domains"] > 0
    a["stress"] = (a["p_worse"] - a["p_better"]).fillna(0.0)
    # Evidence type: an actual hunger report is kept apart from risk factors, responses and background.
    a["evidence_type"] = np.select(
        [~a["relevant"],
         a["p_hunger_report"] >= HUNGER_REPORT_THRESHOLD,
         (a["p_gov_response"] >= RELEVANCE_THRESHOLD) & (a["stress"] <= 0),
         a["stress"] > 0],
        ["irrelevant", "actual_food_insecurity", "government_response", "risk_factor"], default="background")
    return a


def dedupe_events(a: pd.DataFrame, emb: np.ndarray) -> pd.DataFrame:
    """event_id: exact duplicate headlines, and near-duplicates (cosine >= 0.90 within 7 days) sharing a domain."""
    a = a.copy()
    a["event_id"] = -1
    first_by_title: dict[str, int] = {}
    order = np.argsort(a["ph_date"].values, kind="stable")
    dates = a["ph_date"].values.astype("datetime64[D]").astype(np.int64)
    dom = a[[f"is_{d}" for d in DOMAINS]].values
    ev = np.full(len(a), -1)
    for i in order:
        t = a.at[i, "title_norm"]
        if t in first_by_title:
            ev[i] = ev[first_by_title[t]]
            continue
        first_by_title[t] = i
        win = np.where((dates >= dates[i] - DEDUP_DAYS) & (dates <= dates[i]) & (ev >= 0))[0]
        if len(win) and dom[i].any():
            sims = emb[win] @ emb[i]
            ok = win[(sims >= DEDUP_COSINE) & (dom[win] & dom[i]).any(axis=1)]
            if len(ok):
                ev[i] = ev[ok[np.argmax(emb[ok] @ emb[i])]]
                continue
        ev[i] = i
    a["event_id"] = ev
    return a


def embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(EMBED_MODEL, device="cpu")
    return m.encode(texts, batch_size=128, normalize_embeddings=True, show_progress_bar=False)


def fit_topics(a: pd.DataFrame, emb: np.ndarray, fit_end: str = "2022-12-31", seed: int = 42):
    """BERTopic on gate-passing headlines; fitted on <= fit_end, frozen, then applied to every gated headline."""
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP

    rel = a.index[a["gate"].fillna(False).astype(bool)].to_numpy()
    fit_idx = rel[a.loc[rel, "ph_date"] <= pd.Timestamp(fit_end)]
    stop = ["the", "and", "of", "to", "in", "for", "on", "at", "with", "by", "from", "as", "is", "are", "be", "its",
            "ng", "sa", "na", "ang", "mga", "at", "para", "ni", "si", "kay", "rin", "din", "ay", "may", "pa", "nang",
            "inquirer", "net", "news", "gma", "philstar", "abs", "cbn", "rappler", "pna", "manila", "bulletin"]
    model = BERTopic(
        embedding_model=None,
        umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=seed),
        hdbscan_model=HDBSCAN(min_cluster_size=15, min_samples=5, metric="euclidean", prediction_data=True),
        vectorizer_model=CountVectorizer(stop_words=stop, ngram_range=(1, 2), min_df=2),
        calculate_probabilities=False, verbose=False)
    docs_fit = a.loc[fit_idx, "title"].tolist()
    model.fit(docs_fit, emb[fit_idx])
    topics, _ = model.transform(a.loc[rel, "title"].tolist(), emb[rel])
    a = a.copy()
    a["topic"] = -1
    a.loc[rel, "topic"] = topics
    info = model.get_topic_info()
    rows = []
    for _, r in info.iterrows():
        t = int(r["Topic"])
        allmem = a[a["topic"] == t]
        mem = allmem[allmem["relevant"]]
        words = [w for w, _ in (model.get_topic(t) or [])][:8]
        dom_share = {d: float(mem[f"is_{d}"].mean()) if len(mem) else 0.0 for d in DOMAINS}
        main = max(dom_share, key=dom_share.get) if t >= 0 else "outlier"
        if t >= 0 and (len(mem) < 3 or dom_share[main] < TOPIC_DOMAIN_MIN_SHARE):
            main = "none"
        reps = (mem.sort_values(f"p_{main}", ascending=False) if main in DOMAINS else allmem)["title"].head(3).tolist()
        rows.append({"topic": t, "label": " / ".join(words[:4]) if t >= 0 else "(outliers)", "top_words": ", ".join(words),
                     "n_fit": int((a.loc[fit_idx, "topic"] == t).sum()) if "topic" in a else 0,
                     "n_all": int(len(allmem)), "n_relevant": int(len(mem)), "domain": main,
                     **{f"share_{d}": round(v, 3) for d, v in dom_share.items()},
                     "mean_stress": round(float(mem["stress"].mean()), 3) if len(mem) else np.nan,
                     "representative_1": reps[0] if len(reps) > 0 else "",
                     "representative_2": reps[1] if len(reps) > 1 else "",
                     "representative_3": reps[2] if len(reps) > 2 else ""})
    return a, pd.DataFrame(rows)


def _cell_fssi(g: pd.DataFrame) -> dict:
    ev = g.sort_values("ph_date").drop_duplicates("event_id")      # one row per event
    n_src = ev.groupby("source_domain")["event_id"].transform("count")
    w = 1.0 / np.sqrt(n_src.to_numpy(float))
    out = {"n_articles": int(len(g)), "n_events": int(len(ev)), "n_relevant_events": int(ev["relevant"].sum()),
           "n_hunger_reports": int((ev["evidence_type"] == "actual_food_insecurity").sum()),
           "n_sources": int(ev["source_domain"].nunique()),
           "top_source_share": float(ev["source_domain"].value_counts(normalize=True).iloc[0]) if len(ev) else np.nan}
    s = np.clip(ev["stress"].to_numpy(float), 0, None)
    for d in DOMAINS:
        r = ev[f"p_{d}"].to_numpy(float) * ev[f"is_{d}"].to_numpy(float)
        out[f"n_{d}"] = int(ev[f"is_{d}"].sum())
        out[f"fssi_raw_{d}"] = float((w * r * s).sum() / w.sum()) if len(ev) else np.nan
        out[f"topic_share_{d}"] = float((w * (ev["topic_domain"] == d)).sum() / w.sum()) if len(ev) else np.nan
    out["fssi_raw_all"] = float((w * ev["relevant"].to_numpy(float) * s).sum() / w.sum()) if len(ev) else np.nan
    out["hunger_report_share"] = out["n_hunger_reports"] / max(out["n_events"], 1)
    return out


def build_fssi(a: pd.DataFrame) -> pd.DataFrame:
    """Province-quarter and region-quarter FSSI (raw, corrected), counts and coverage diagnostics."""
    rows = []
    for q, g in a.groupby("quarter"):
        reg = _cell_fssi(g)
        rows.append({"quarter": q, "geo": "CALABARZON", **reg, "shrink_weight": 1.0,
                     **{f"fssi_{d}": reg[f"fssi_raw_{d}"] for d in DOMAINS + ["all"]}})
        for code, name in PROVINCES.items():
            gp = g[g["geo_province_code"] == code]
            c = _cell_fssi(gp) if len(gp) else {"n_articles": 0, "n_events": 0}
            n = c.get("n_events", 0)
            lam = n / (n + SHRINK_K)
            corr = {f"fssi_{d}": lam * c.get(f"fssi_raw_{d}", 0.0) + (1 - lam) * reg[f"fssi_raw_{d}"]
                    if n else reg[f"fssi_raw_{d}"] for d in DOMAINS + ["all"]}
            rows.append({"quarter": q, "geo": name, **c, "shrink_weight": lam, **corr})
    f = pd.DataFrame(rows)
    f["coverage_flag"] = np.where(f["n_events"].fillna(0) < 5, "thin (<5 events): mostly regional value",
                                  "adequate")
    return f


def run(skip_scoring: bool = False) -> dict:
    df = load_corpus()
    if not skip_scoring:
        score_xlmr(df)
    scores = backfill_stage2(df)
    a = label_articles(df, scores)
    if EMBEDDINGS.exists() and len(np.load(EMBEDDINGS)) == len(a):
        emb = np.load(EMBEDDINGS)
    else:
        emb = embed(a["title"].tolist())
        np.save(EMBEDDINGS, emb)
    a = dedupe_events(a, emb)
    a, topics = fit_topics(a, emb)
    tmap = dict(zip(topics["topic"], topics["domain"]))
    a["topic_domain"] = a["topic"].map(tmap).where(a["topic"] >= 0, "none")
    topics.to_csv(TOPICS, index=False, lineterminator="\n")
    keep = ["article_key", "ph_date", "quarter", "source_domain", "geo_province_code", "title", "event_id",
            "relevant", "n_domains", "evidence_type", "stress", "topic", "topic_domain"] + \
        [f"p_{n}" for n in HYPOTHESES] + [f"is_{d}" for d in DOMAINS]
    a[keep].to_parquet(ARTICLES, index=False)
    fssi = build_fssi(a)
    fssi.to_csv(FSSI, index=False, lineterminator="\n")
    summary = {
        "corpus_articles": int(len(a)), "unique_headlines": int(a["title_norm"].nunique()),
        "events": int(a["event_id"].nunique()), "relevant_articles": int(a["relevant"].sum()),
        "multi_domain_articles": int((a["n_domains"] > 1).sum()),
        "evidence_type_counts": a["evidence_type"].value_counts().to_dict(),
        "domain_counts": {d: int(a[f"is_{d}"].sum()) for d in DOMAINS},
        "topics": int((topics["topic"] >= 0).sum()), "topic_fit_window": "2021-01-01..2022-12-31",
        "first_date": str(a["ph_date"].min().date()), "last_date": str(a["ph_date"].max().date()),
        "model": XLMR_MODEL, "hypothesis_hash": HYP_HASH, "embedding_model": EMBED_MODEL,
        "fssi_rows": int(len(fssi)),
    }
    (NLP / "nlp_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score", "all"])
    ap.add_argument("--skip-scoring", action="store_true")
    ap.add_argument("--part", default="0:1", help="fraction slice of unscored headlines, e.g. 0:0.6")
    ap.add_argument("--device", default="cpu", help="torch device; the Intel Arc iGPU (xpu) failed on XLM-R large here")
    ap.add_argument("--threads", type=int, default=None)
    args = ap.parse_args()
    if args.cmd == "score":
        lo, hi = (float(x) for x in args.part.split(":"))
        score_xlmr(load_corpus(), part=(lo, hi), device=args.device, threads=args.threads)
    else:
        print(json.dumps(run(skip_scoring=args.skip_scoring), indent=1, default=str))
