"""
scripts/significance_tests.py
------------------------------
Is the model's margin over the baselines distinguishable from noise?

Research Question 3 asks how the combined model compares against six baselines.
Chapter IV reports the point estimates. A point estimate on 55 observations is
not an answer on its own: a margin of +0.036 accuracy is two flipped
predictions, and a reader is entitled to know whether that survives a test.

Two tests, both on the paired predictions the walk-forward folds produce, so
model and baseline are compared on exactly the same rows:

  * McNemar's exact test on the discordant pairs — the standard test for two
    classifiers on one sample. It asks whether the cases only the model gets
    right outnumber the cases only the baseline gets right by more than chance.
  * A paired bootstrap over the 55 observations, giving a confidence interval
    on the accuracy difference.

This adds no method to the pipeline and changes no result. It measures how much
weight the reported comparison can carry.

    python -m scripts.significance_tests
"""

from __future__ import annotations

import json
import warnings
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = Path("data/supplementary/significance_tests.json")
N_BOOT = 10000
RNG = np.random.default_rng(42)


def mcnemar_exact(a_correct: np.ndarray, b_correct: np.ndarray) -> dict:
    """
    Two-sided exact McNemar on paired correctness vectors.

    b01 = a wrong, b right;  b10 = a right, b wrong.
    Under the null the discordant pairs split 50/50, so the count is Binomial(n, 0.5).
    """
    b01 = int(np.sum(~a_correct & b_correct))
    b10 = int(np.sum(a_correct & ~b_correct))
    n = b01 + b10
    if n == 0:
        return {"b01": 0, "b10": 0, "n_discordant": 0, "p_value": 1.0}
    k = min(b01, b10)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return {"b01": b01, "b10": b10, "n_discordant": n,
            "p_value": round(min(1.0, 2 * tail), 4)}


def boot_diff(a_correct: np.ndarray, b_correct: np.ndarray) -> dict:
    """Paired bootstrap CI on (accuracy_a - accuracy_b)."""
    n = len(a_correct)
    diffs = np.empty(N_BOOT)
    for i in range(N_BOOT):
        idx = RNG.integers(0, n, n)
        diffs[i] = a_correct[idx].mean() - b_correct[idx].mean()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"observed_diff": round(float(a_correct.mean() - b_correct.mean()), 4),
            "ci95_low": round(float(lo), 4), "ci95_high": round(float(hi), 4),
            "share_of_resamples_favouring_model": round(float((diffs > 0).mean()), 4)}


def main() -> dict:
    from lightgbm import LGBMClassifier
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    from app.ml.features.feature_selector import model_features
    from app.ml.training import evaluator as E
    from app.ml.training import trainer as T
    from app.ml.training.cross_validation import WalkForwardSplitter

    res = json.load(open("data/processed/training_results.json"))
    gap = res["max_reliable_lead_time"]
    best = {**res["best_params"], "objective": "binary", "verbosity": -1,
            "boosting_type": "gbdt", "random_state": 42, "class_weight": "balanced"}

    feats = pd.read_parquet("data/processed/features_fused.parquet")
    labels = pd.read_parquet("data/processed/labels.parquet")
    df = (feats.merge(labels[["province_code", "quarter", "label_stress"]],
                      on=["province_code", "quarter"], how="inner")
          .sort_values(["quarter", "province_code"]).reset_index(drop=True))
    cols = model_features()
    y = df["label_stress"].astype(int)
    sp = WalkForwardSplitter(min_train_quarters=T.MIN_TRAIN_QUARTERS, forecast_gap=gap)

    truth, pred = {}, {"model": [], "persistence": [], "gov_only_lgbm": []}
    ys = []
    for tr, te in sp.split(df):
        tr_df, te_df = df.loc[tr], df.loc[te]
        ys += list(y.loc[te])

        m = LGBMClassifier(**best)
        m.fit(df.loc[tr, cols], y.loc[tr])
        pred["model"] += list(m.predict(df.loc[te, cols]))

        last = tr_df.sort_values("quarter").groupby("province_code")["label_stress"].last()
        pred["persistence"] += list(
            te_df["province_code"].map(last).fillna(0).astype(int))

        gov = [c for c in E.PSA_FEATURES if c in df.columns]
        g = LGBMClassifier(**best)
        g.fit(df.loc[tr, gov], y.loc[tr])
        pred["gov_only_lgbm"] += list(g.predict(df.loc[te, gov]))

    ys = np.array(ys)
    correct = {k: (np.array(v) == ys) for k, v in pred.items()}

    out = {"n": int(len(ys)), "accuracy": {k: round(float(c.mean()), 4)
                                           for k, c in correct.items()}, "tests": {}}
    for other in ("persistence", "gov_only_lgbm"):
        out["tests"][f"model_vs_{other}"] = {
            "mcnemar": mcnemar_exact(correct["model"], correct[other]),
            "bootstrap": boot_diff(correct["model"], correct[other]),
        }

    OUT.write_text(json.dumps(out, indent=2))

    print(f"\nPAIRED COMPARISON ON THE WALK-FORWARD FOLDS (n={out['n']}, gap={gap})")
    print("=" * 74)
    for k, v in out["accuracy"].items():
        print(f"  {k:18s} accuracy {v}")
    for name, t in out["tests"].items():
        m, b = t["mcnemar"], t["bootstrap"]
        print(f"\n  {name}")
        print(f"    discordant pairs : model-only-right {m['b10']}, "
              f"baseline-only-right {m['b01']}  (n={m['n_discordant']})")
        print(f"    McNemar exact    : p = {m['p_value']}")
        print(f"    accuracy diff    : {b['observed_diff']:+.4f}  "
              f"95% CI [{b['ci95_low']:+.4f}, {b['ci95_high']:+.4f}]")
        print(f"    resamples favouring the model: {b['share_of_resamples_favouring_model']:.1%}")
    print("=" * 74)
    print(f"written -> {OUT}")
    return out


if __name__ == "__main__":
    main()
