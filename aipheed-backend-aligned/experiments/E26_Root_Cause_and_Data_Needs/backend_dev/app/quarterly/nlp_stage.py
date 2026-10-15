"""
app/quarterly/nlp_stage.py  (E24)
---------------------------------
News features for ONE forecast period, built only from articles that app.quarterly.eligibility marked ELIGIBLE
(original publication time in PHT, inside the reference quarter, on or before the cutoff).

Uses the project's approved functions unchanged:
    * scoring: an injected scorer returning the Algorithm 1 food_insecurity_score per article (the production
      scorer is app.ml.nlp.classifier, XLM-RoBERTa zero-shot; tests inject a stub so no model is loaded);
    * relevance gate 0.30 (classifier.RELEVANCE_THRESHOLD) inside fssi_builder.compute_fssi;
    * bias weights: bias_weighter.compute_bias_weights (geocoded articles, per-quarter cross-province median);
    * FSSI: fssi_builder.compute_fssi;  triggers: trigger_classifier.classify_triggers.
Lags (FSSI_lag1/2, accel) need earlier quarters' FSSI from the versioned archive and are joined by the caller.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

TRIGGERS = ["market", "climate", "employment", "ofw_remittance", "fish_kill"]


def build_news_features(eligible: pd.DataFrame, period, scorer: Callable[[pd.DataFrame], pd.Series],
                        provinces: list[str]) -> dict:
    from app.ml.corpus.bias_weighter import DATA_SUFFICIENCY_MIN_ARTICLES, compute_bias_weights
    from app.ml.features.fssi_builder import compute_fssi
    from app.ml.nlp.trigger_classifier import classify_triggers

    q = str(period.reference_quarter)
    df = eligible[eligible["province_code"].notna()].copy()
    if df.empty:
        return {"quarter": q, "rows": [{"province_code": p, "FSSI": None, "article_count": 0,
                                        "data_sufficiency": "LIMITED_SIGNAL", **{f"trigger_{t}": None for t in TRIGGERS}}
                                       for p in provinces], "scored_articles": 0}
    df["food_insecurity_score"] = scorer(df).astype(float).to_numpy()
    df["published"] = df["published_ph"].map(lambda t: t.isoformat())
    df["quarter"] = q
    w = compute_bias_weights(df)
    f = compute_fssi(df, w, save_path=None)
    text = (df.get("title", "").fillna("") + ". " + df.get("summary", pd.Series("", index=df.index)).fillna("")).astype(str)
    trig = text.map(classify_triggers)
    rows = []
    for p in provinces:
        g = df[df["province_code"] == p]
        fr = f[(f["province_code"] == p) & (f["quarter"] == q)]
        wr = w[(w["province_code"] == p) & (w["quarter"] == q)]
        n = int(wr["article_count"].iloc[0]) if len(wr) else 0
        row = {"province_code": p, "FSSI": float(fr["FSSI"].iloc[0]) if len(fr) else None, "article_count": n,
               "data_sufficiency": "OK" if n >= DATA_SUFFICIENCY_MIN_ARTICLES else "LIMITED_SIGNAL"}
        for t in TRIGGERS:
            row[f"trigger_{t}"] = float(trig[g.index].map(lambda x: t in x).mean()) if len(g) else None
        rows.append(row)
    return {"quarter": q, "rows": rows, "scored_articles": int(len(df))}
