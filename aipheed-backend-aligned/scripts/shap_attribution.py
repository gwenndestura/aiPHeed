"""
scripts/shap_attribution.py

Global SHAP attribution of the served model (Research Question 1, Objective 1).

Computes Equation 7's per-feature Shapley values for every province-quarter in
the fused matrix with the production model, then reports for each feature its
mean |SHAP| and its share of the total, the NLP versus government split, and
how much of the attribution comes from features that differ between provinces
(provincial) versus features shared by all five in a quarter (regional).

Writes data/processed/shap_attribution.json, which the results documents read.

    python -m scripts.shap_attribution
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.inference.explainer import Explainer
from app.ml.training.evaluator import NLP_FEATURES

OUT = Path("data/processed/shap_attribution.json")


def main() -> dict:
    ex = Explainer()
    ex._load()
    feats = ex._features
    cols = ex._feature_cols
    X = feats[cols].fillna(0.0)
    raw = ex._explainer.shap_values(X)
    arr = np.asarray(raw[-1] if isinstance(raw, list) else raw)
    if arr.ndim == 3:
        arr = arr[:, :, -1]

    mean_abs = np.abs(arr).mean(axis=0)
    total = float(mean_abs.sum()) or 1.0
    order = np.argsort(-mean_abs)
    features = [{
        "rank": int(r + 1),
        "feature": cols[i],
        "mean_abs_shap": round(float(mean_abs[i]), 6),
        "share_of_total": round(float(mean_abs[i] / total), 4),
        "mean_signed_shap": round(float(arr[:, i].mean()), 6),
    } for r, i in enumerate(order)]

    nlp = sum(f["share_of_total"] for f in features if f["feature"] in NLP_FEATURES)

    # Regional vs provincial: a feature counts as regional in a quarter when
    # all five provinces carry the same value for it in that quarter.
    shared = np.zeros_like(arr, dtype=bool)
    for q, idx in feats.groupby("quarter").groups.items():
        rows = feats.loc[idx, cols]
        same = (rows.round(9).nunique() <= 1).values
        shared[feats.index.get_indexer(idx)] = same
    abs_arr = np.abs(arr)
    regional = float(abs_arr[shared].sum() / abs_arr.sum())

    result = {
        "model_features": cols,
        "n_province_quarters": int(len(X)),
        "baseline_phi0": round(float(ex._baseline), 4),
        "features": features,
        "nlp_share": round(nlp, 4),
        "gov_share": round(1 - nlp, 4),
        "regional_share": round(regional, 4),
        "provincial_share": round(1 - regional, 4),
        "n_features_used": int((mean_abs > 0).sum()),
    }
    OUT.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    r = main()
    for f in r["features"]:
        print(f"{f['rank']:>2}. {f['feature']:28s} {f['share_of_total']:.4f}")
    print("NLP share", r["nlp_share"], "| provincial share", r["provincial_share"],
          "| features used", r["n_features_used"])
