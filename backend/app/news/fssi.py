"""
Province-quarter FSSI from the E28 news store (E28), with the methodology unchanged:

    FSSI_p,t = w_p,t * (1/N) * sum_i max_h score(x_i, h)        (fssi_builder.compute_fssi, Equation 2)
    w_p,t    = log(1 + median_p' n_p',t) / log(1 + n_p,t)        (bias_weighter.compute_bias_weights)
    N        = title-geocoded, XLM-RoBERTa-scored articles at or above the 0.30 relevance threshold

Two E28 corrections around the formula, neither of which changes it:
  * Calendar-aligned lags. compute_fssi takes FSSI_lag1/lag2 with groupby().shift() over the rows that EXIST, so when
    a province has no row for a quarter the "lag 1" is the value from two or more quarters back. Lags here are taken
    on the full quarter grid; a missing quarter gives a missing lag.
  * Missing is missing. A province-quarter without usable articles gets FSSI = null with evidence_status
    NO_USABLE_EVIDENCE (never 0, never LOW), and an incompletely scored cell is SCORING_INCOMPLETE.

The output is deterministic: rows are sorted and the panel's SHA-256 is recorded with the hashes of its inputs, so a
rerun on the same store and model version must reproduce it exactly.
"""
from __future__ import annotations

import hashlib
import json
import math

import pandas as pd

from app.news.audit import MIN_ARTICLES, _latest_scores
from app.news.collector import PROVINCES
from app.news.store import NewsStore
from app.news.timeutil import parse_quarter


def _qi(q: str) -> int:
    y, n = parse_quarter(q)
    return y * 4 + n - 1


def build_fssi(store: NewsStore, quarters: list[str], model_key: str | None = None, write: bool = True) -> dict:
    from app.ml.corpus.bias_weighter import compute_bias_weights
    from app.ml.features.fssi_builder import compute_fssi
    from app.news.scoring import current_model_key

    model_key = model_key or current_model_key()
    scores = _latest_scores(store, model_key)
    code_to_name = {v: k for k, v in PROVINCES.items()}
    recs = []
    for a in store.articles.values():
        if a.get("geo_province_code") in code_to_name and a["quarter"] in quarters:
            s = scores.get(a["article_key"])
            recs.append({"article_key": a["article_key"], "province_code": a["geo_province_code"],
                         "quarter": a["quarter"], "published": a["published_ph"], "source_domain": a["source_domain"],
                         "score_status": s["status"] if s else "UNSCORED",
                         "food_insecurity_score": (s["score"] if s and s["status"] in ("OK", "NO_FOOD_NEXUS")
                                                   else None)})
    art = pd.DataFrame(recs, columns=["article_key", "province_code", "quarter", "published", "source_domain",
                                      "score_status", "food_insecurity_score"])
    scored = art[art["score_status"].isin(["OK", "NO_FOOD_NEXUS"])].copy()
    if len(scored):
        w = compute_bias_weights(scored[["province_code", "published"]].assign(), save_path=None)
        f = compute_fssi(scored, w, save_path=None)
    else:
        w = pd.DataFrame(columns=["quarter", "province_code", "article_count", "median_articles", "bias_weight"])
        f = pd.DataFrame(columns=["province_code", "quarter", "article_count", "fssi_raw", "bias_weight", "FSSI"])
    rows = []
    for p, code in PROVINCES.items():
        for q in quarters:
            g = art[(art["province_code"] == code) & (art["quarter"] == q)]
            fr = f[(f["province_code"] == code) & (f["quarter"] == q)]
            wr = w[(w["province_code"] == code) & (w["quarter"] == q)]
            n_unsc = int((g["score_status"].isin(["UNSCORED", "FAILED"])).sum())
            n_in = int(fr["article_count"].iloc[0]) if len(fr) else 0
            if n_unsc:
                ev = "SCORING_INCOMPLETE"
            elif n_in >= MIN_ARTICLES:
                ev = "SUFFICIENT"
            elif n_in > 0:
                ev = "LIMITED_SIGNAL"
            else:
                ev = "NO_USABLE_EVIDENCE"
            fssi = float(fr["FSSI"].iloc[0]) if len(fr) and ev != "SCORING_INCOMPLETE" else None
            rows.append({"province": p, "province_code": code, "quarter": q,
                         "n_geocoded": int(len(g)), "n_scored": int(len(g) - n_unsc), "n_unscored_or_failed": n_unsc,
                         "n_in_fssi": n_in,
                         "fssi_raw": round(float(fr["fssi_raw"].iloc[0]), 6) if len(fr) else None,
                         "bias_weight": round(float(wr["bias_weight"].iloc[0]), 6) if len(wr) else None,
                         "median_articles_quarter": float(wr["median_articles"].iloc[0]) if len(wr) else None,
                         "FSSI": round(fssi, 6) if fssi is not None else None,
                         "evidence_status": ev,
                         "n_sources": int(g["source_domain"].nunique())})
    panel = pd.DataFrame(rows)
    panel["qidx"] = panel["quarter"].map(_qi)
    panel = panel.sort_values(["province_code", "qidx"]).reset_index(drop=True)
    lag1, lag2 = [], []
    idx = {(r.province_code, r.qidx): r.FSSI for r in panel.itertuples()}
    for r in panel.itertuples():
        lag1.append(idx.get((r.province_code, r.qidx - 1)))
        lag2.append(idx.get((r.province_code, r.qidx - 2)))
    panel["FSSI_lag1"], panel["FSSI_lag2"] = lag1, lag2
    panel["FSSI_accel"] = [None if (a is None or b is None or (isinstance(a, float) and math.isnan(a))) else round(a - b, 6)
                           for a, b in zip(panel["FSSI"], panel["FSSI_lag1"])]
    panel = panel.drop(columns="qidx")
    csv = panel.to_csv(index=False, lineterminator="\n")
    panel_sha = hashlib.sha256(csv.encode()).hexdigest()

    def fsha(name):
        p = store.path(name)
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

    manifest = {"model_key": model_key, "quarters": [quarters[0], quarters[-1]], "rows": len(panel),
                "panel_sha256": panel_sha, "articles_jsonl_sha256": fsha("articles"),
                "scores_jsonl_sha256": fsha("scores"), "relevance_threshold": 0.30,
                "min_articles_sufficient": MIN_ARTICLES,
                "source_policy_counts": {k: v for k, v in sorted(
                    pd.Series([a.get("source_policy", "v1 (E28, before versioning)") for a in store.articles.values()])
                    .value_counts().to_dict().items())},
                "evidence_status_counts": panel["evidence_status"].value_counts().to_dict()}
    if write:
        (store.root / "fssi_panel.csv").write_bytes(csv.encode("utf-8"))   # exact bytes: write_text would add CR on Windows and break the manifest hash
        (store.root / "fssi_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return {"panel": panel, "summary": manifest, "articles": art}
