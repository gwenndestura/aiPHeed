"""
scripts/label_reference_points.py
----------------------------------
Reference points any reported accuracy must be read against.

Section 3.4.4 accepts a model only against what comparable work achieves and
what a system feeding real anticipatory decisions should be trusted to deliver.
Research Question 3 makes the comparison explicit. This script computes the
reference points that make a headline number interpretable, and one that is
specific to the approved label's construction.

Equation 3 defines the target as

    stress(p,t)       = sws_hunger(t) + 2 * (food_cpi_yoy(p,t) - regional_mean(t))
    label_stress(p,t) = 1 if stress(p,t) > global_median(stress)

so the label is a deterministic function of two published series. One of them,
SWS hunger, is excluded from the feature matrix as leakage. The other, food CPI
deviation, is an approved model input: Equation 5 names CPI_dev(t) and Section
3.3.2.7 retains it among the final twelve features.

That is worth stating plainly rather than leaving for a reader to discover, so
the script reports how far the label's own inputs get on their own. It does not
change the methodology; it measures it.

    python -m scripts.label_reference_points
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path("data/processed")
OUT = Path("data/supplementary/label_reference_points.json")


def main() -> dict:
    labels = pd.read_parquet(PROC / "labels.parquet")
    feats = pd.read_parquet(PROC / "features_fused.parquet")

    df = feats.merge(
        labels[["province_code", "quarter", "label_stress", "stress_score",
                "sws_hunger_pct", "food_cpi_yoy", "regional_food_cpi_yoy"]],
        on=["province_code", "quarter"], suffixes=("", "_lab"),
    )
    y = df["label_stress"].values
    dev = (df["food_cpi_yoy_lab"] - df["regional_food_cpi_yoy"]).values

    # Reconstruct the label from its own two published inputs. This is 1.0 by
    # construction and is reported so the identity is explicit: a model handed
    # BOTH inputs would be reading its own target.
    recon = (df["sws_hunger_pct"] + 2 * dev > df["stress_score"].median()).astype(int)

    # The model gets only the CPI term. A single-feature median split on it is
    # the ceiling that term alone can reach.
    m = df["food_cpi_yoy"].values
    thr = float(np.median(m))
    cpi_only = max(((m > thr).astype(int) == y).mean(),
                   ((m <= thr).astype(int) == y).mean())

    # Naive persistence, the Research Question 3 baseline that matters most on
    # an autocorrelated label.
    d2 = df.sort_values(["province_code", "quarter"])
    prev = d2.groupby("province_code")["label_stress"].shift(1)
    has = prev.notna()
    persistence = float((prev[has] == d2["label_stress"][has]).mean())

    within = df.groupby("quarter")["label_stress"].nunique()

    out = {
        "n_rows": int(len(df)),
        "n_quarters": int(df["quarter"].nunique()),
        "positive_rate": round(float(y.mean()), 4),
        "majority_class_accuracy": round(float(max(y.mean(), 1 - y.mean())), 4),
        "naive_persistence_accuracy": round(persistence, 4),
        "label_reconstructed_from_its_own_inputs": round(float((recon == y).mean()), 4),
        "food_cpi_yoy_single_feature_accuracy": round(float(cpi_only), 4),
        "corr_cpi_deviation_with_label": round(float(np.corrcoef(dev, y)[0, 1]), 4),
        "corr_sws_hunger_with_label": round(
            float(np.corrcoef(df["sws_hunger_pct"], y)[0, 1]), 4),
        "quarters_with_no_within_quarter_variation": int((within == 1).sum()),
        "note": (
            "SWS hunger is constant across the five provinces within a quarter, "
            "so it carries the label's temporal movement and food CPI deviation "
            "carries its cross-province movement. The model receives the CPI "
            "term (approved, Equation 5) and not the SWS term (excluded as "
            "leakage). A reported accuracy is therefore meaningful above "
            "food_cpi_yoy_single_feature_accuracy and, more demandingly, above "
            "naive_persistence_accuracy."
        ),
    }

    OUT.write_text(json.dumps(out, indent=2))
    width = max(len(k) for k in out if k != "note") + 2
    print("\nLABEL REFERENCE POINTS")
    print("=" * (width + 12))
    for k, v in out.items():
        if k == "note":
            continue
        print(f"  {k:<{width}} {v}")
    print("=" * (width + 12))
    print(f"\n{out['note']}\n")
    print(f"written -> {OUT}")
    return out


if __name__ == "__main__":
    main()
