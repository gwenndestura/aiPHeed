"""
v10 Stage 2: re-derives the news corpus facts from the raw article stores (no stored FSSI is trusted). Read-only on all
inputs; writes docs/aipheed/v10/results/news_audit.json. No model is scored against any target here.

BERTopic stability (--topics) refits on titles with the local embedding cache only (never downloads): HF_HUB_OFFLINE=1.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "docs" / "aipheed" / "v10" / "results"
DEV_END = "2026-09-30"
TAGALOG = r"\b(ang|ng|mga|sa|na|ay|si|nang|para|hindi|presyo|bigas|gutom|magsasaka|sapat|pagkain)\b"
THRESH = 0.30   # app.ml.nlp.classifier.RELEVANCE_THRESHOLD


def jl(p: Path) -> pd.DataFrame:
    return pd.DataFrame([json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()])


def norm_title(s: pd.Series) -> pd.Series:
    # Google News appends " - Outlet"; syndicated copies differ only there.
    t = s.str.replace(r"\s+[-|]\s+[^-|]{2,40}$", "", regex=True).str.lower()
    return t.str.replace(r"[^a-z0-9 ]", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()


def corpus() -> pd.DataFrame:
    a, b = jl(ROOT / "data/news_e31/articles.jsonl"), jl(ROOT / "data/news_e60/articles.jsonl")
    return pd.concat([a, b], ignore_index=True).drop_duplicates("article_key").reset_index(drop=True)


def audit() -> dict:
    d = corpus()
    r: dict = {"articles_unique": len(d), "columns": sorted(d.columns)}
    r["sources"] = d.source.value_counts().to_dict()
    r["date_kind"] = d.date_kind.value_counts().to_dict()
    r["n_domains"] = int(d.source_domain.nunique())
    r["top_domains_share"] = (d.source_domain.value_counts(normalize=True).head(5).round(3)).to_dict()
    r["ph_date_range"] = [d.ph_date.min(), d.ph_date.max()]
    r["after_dev_end"] = int((d.ph_date > DEV_END).sum())
    r["usable_publication_timestamp_share"] = float(pd.to_datetime(d.published_ph, errors="coerce", utc=True).notna().mean())
    r["first_seen_range"] = [d.first_seen_at.min(), d.first_seen_at.max()]
    seen = pd.to_datetime(d.first_seen_at, utc=True)
    pub = pd.to_datetime(d.published_ph, utc=True)
    r["median_days_published_to_crawl"] = float(((seen - pub).dt.total_seconds() / 86400).median())
    r["crawl_before_publication"] = int((seen < pub).sum())
    r["has_body_text"] = any(c in d.columns for c in ("body", "text", "content"))
    n = norm_title(d.title)
    r["exact_dup_titles_after_outlet_strip"] = int(n.duplicated().sum())
    r["share_ge2_tagalog_tokens"] = float((n.str.count(TAGALOG) >= 2).mean())
    r["share_ge1_tagalog_tokens"] = float((n.str.count(TAGALOG) >= 1).mean())
    r["geo_assigned_share"] = float(d.geo_province_code.notna().mean())
    r["geo_rows_per_province"] = d.geo_province_code.value_counts().to_dict()

    dev = d[(d.ph_date >= "2021-01-01") & (d.ph_date <= DEV_END)].copy()
    dev["month"] = dev.ph_date.str[:7]
    months = pd.period_range("2021-01", "2026-09", freq="M").astype(str)
    r["articles_per_month"] = dev.groupby("month").size().reindex(months, fill_value=0).describe().round(1).to_dict()

    # Scores: latest record per article across the stores; share scored
    s = pd.concat([jl(ROOT / "data/news_e31/scores.jsonl"), jl(ROOT / "data/news_v3/scores.jsonl")], ignore_index=True)
    r["score_rows"] = len(s)
    r["score_status"] = s.status.value_counts().to_dict()
    r["model_keys"] = s.model_key.value_counts().to_dict()
    ok = s[s.status == "OK"].drop_duplicates("article_key", keep="last")
    r["articles_scored"] = int(ok.article_key.isin(d.article_key).sum())
    g = dev[dev.geo_province_code.notna()].merge(ok[["article_key", "score"]], on="article_key", how="left")
    r["geo_articles_dev"] = len(g)
    r["geo_articles_dev_scored_share"] = float(g.score.notna().mean())
    g["relevant"] = g.score >= THRESH
    quarters = [f"{y}-Q{q}" for y in range(2021, 2027) for q in range(1, 5) if f"{y}-Q{q}" <= "2026-Q3"]
    idx = pd.MultiIndex.from_product([sorted(d.geo_province_code.dropna().unique()), quarters])
    tot = g.groupby(["geo_province_code", "quarter"]).size().reindex(idx, fill_value=0)
    rel = g[g.relevant].groupby(["geo_province_code", "quarter"]).size().reindex(idx, fill_value=0)
    r["province_quarter_cells"] = len(idx)
    r["cells_any_article"] = int((tot > 0).sum())
    r["cells_zero_relevant"] = int((rel == 0).sum())
    r["cells_1_or_2_relevant"] = int(rel.between(1, 2).sum())
    r["cells_ge5_relevant"] = int((rel >= 5).sum())
    r["relevant_median_per_cell"] = float(rel.median())
    r["relevant_per_province"] = rel.groupby(level=0).sum().to_dict()
    r["relevant_max_cell"] = {"value": int(rel.max()), "where": "/".join(rel.idxmax())}
    r["relevant_share_top_quarter_cells"] = float(rel.sort_values(ascending=False).head(5).sum() / max(rel.sum(), 1))
    pq = rel.unstack(0)
    r["relevant_quarter_totals"] = pq.sum(axis=1).astype(int).to_dict()

    # Near-duplicates inside the geo-relevant set: same normalised first 8 tokens within one quarter
    h = g[g.relevant].assign(k=lambda x: norm_title(x.title).str.split().str[:8].str.join(" "))
    r["relevant_near_dup_same_quarter"] = int(h.duplicated(["k", "quarter"]).sum())
    r["relevant_near_dup_share"] = float(h.duplicated(["k", "quarter"]).mean()) if len(h) else float("nan")

    # Bias weight formula: w = log(1 + median) / log(1 + count), per quarter cross-province
    b = pd.read_parquet(ROOT / "data/processed/bias_weights.parquet")
    chk = np.log1p(b.median_articles) / np.log1p(b.article_count)
    r["bias_formula_matches_rows"] = int(np.isclose(chk, b.bias_weight, atol=1e-4).sum())
    r["bias_rows"] = len(b)
    r["bias_median_is_within_quarter"] = bool(np.allclose(
        b.groupby("quarter").article_count.transform("median"), b.median_articles))
    r["bias_weight_at_count_1"] = float(b[b.article_count == 1].bias_weight.max()) if (b.article_count == 1).any() else None
    f = pd.read_parquet(ROOT / "data/processed/fssi_quarterly.parquet")
    r["fssi_rows_2021_on"] = int((f.quarter >= "2021-Q1").sum())
    r["fssi_equals_raw_times_weight_share"] = float(np.isclose(f.fssi_raw * f.bias_weight, f.FSSI, atol=1e-3).mean())
    r["fssi_weight_gt1_rows_in_table"] = int((f.bias_weight > 1).sum())
    r["fssi_manifest"] = json.loads((ROOT / "data/news_e31/fssi_manifest.json").read_text())["evidence_status_counts"]
    r["topics_manifest"] = json.loads((ROOT / "data/news_v3/topics_manifest.json").read_text())
    ann = ROOT.parent / "aipheed-backend-aligned/experiments/FINAL_SYSTEM_SELECTION/annotation"
    ds = ROOT.parent / "aipheed-backend-aligned/experiments/DASHBOARD_SELECTION"
    found = sorted(str(p.relative_to(ROOT.parent)) for base in (ann, ds) for p in base.rglob("news_review_human*.csv"))
    r["human_label_files"] = found
    return r


def topic_stability(seeds=(42, 7, 2026)) -> dict:
    """BERTopic on titles through 2026-Q3 (development), several seeds; plus a past-only refit compared on past rows."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics import adjusted_rand_score
    from umap import UMAP

    d = corpus()
    d = d[d.ph_date <= DEV_END].sort_values("article_key").reset_index(drop=True)
    enc = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", local_files_only=True)
    emb = enc.encode(d.title.tolist(), batch_size=64, show_progress_bar=False, normalize_embeddings=True)

    def fit(idx, seed):
        m = BERTopic(umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=seed),
                     hdbscan_model=HDBSCAN(min_cluster_size=10, prediction_data=False), calculate_probabilities=False,
                     verbose=False)
        t, _ = m.fit_transform(d.title.iloc[idx].tolist(), emb[idx])
        return np.asarray(t)

    full = np.arange(len(d))
    by_seed = {s: fit(full, s) for s in seeds}
    out = {"n": len(d), "seeds": list(seeds), "topics": {s: int(len(set(t) - {-1})) for s, t in by_seed.items()},
           "outlier_share": {s: float((t == -1).mean()) for s, t in by_seed.items()}}
    ss = list(seeds)
    out["ari_between_seeds"] = {f"{a}-{b}": float(adjusted_rand_score(by_seed[a], by_seed[b]))
                                for i, a in enumerate(ss) for b in ss[i + 1:]}
    past = np.where(d.ph_date.values < "2024-01-01")[0]
    tp = fit(past, seeds[0])
    out["past_only_n"] = len(past)
    out["past_only_topics"] = int(len(set(tp) - {-1}))
    out["ari_past_only_vs_full_on_past_rows"] = float(adjusted_rand_score(tp, by_seed[seeds[0]][past]))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    r = audit()
    if "--topics" in sys.argv:
        try:
            r["topic_stability"] = topic_stability()
        except Exception as e:  # missing local model is NEEDS-DATA, not a silent pass
            r["topic_stability"] = {"status": "NOT_RUN", "error": f"{type(e).__name__}: {e}"[:300]}
    (OUT / "news_audit.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
    print(json.dumps(r, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
