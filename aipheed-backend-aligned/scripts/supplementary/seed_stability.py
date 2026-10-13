"""
scripts/seed_stability.py
--------------------------
How much of the reported performance is the random seed?

Algorithm 4 fixes a seed so the run is reproducible. That is correct, but it
means a single reported figure carries whatever luck that seed had, and on a
20-row holdout one flipped prediction moves accuracy by 0.05. A reader is
entitled to know the spread.

This script re-runs Algorithm 4 unchanged across several seeds and reports the
distribution of each metric. It alters no part of the methodology: the feature
vector, the walk-forward structure, the 100-trial budget, the objective and the
holdout are all as approved. Only the seed varies, and the production model
remains the one trained at the approved seed.

    python -m scripts.seed_stability
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = Path("data/supplementary/seed_stability.json")
SEEDS = [42, 1, 7, 13, 23, 99, 2024, 31337]


def run_one(seed: int) -> dict:
    """Algorithm 4 at one seed. Same structure, same budget, same holdout."""
    import optuna
    from lightgbm import LGBMClassifier
    from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                                 precision_score, recall_score, roc_auc_score)

    from app.ml.features.feature_selector import model_features
    from app.ml.training import trainer as T
    from app.ml.training.cross_validation import WalkForwardSplitter

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    feats = pd.read_parquet(T.FEATURES_PATH)
    labels = pd.read_parquet(T.LABELS_PATH)
    df = (feats.merge(labels[["province_code", "quarter", "label_stress"]],
                      on=["province_code", "quarter"], how="inner")
          .sort_values(["quarter", "province_code"]).reset_index(drop=True))
    cols = model_features()
    X, y, q = df[cols], df["label_stress"].astype(int), df["quarter"]

    quarters = sorted(q.unique())
    hold = set(quarters[-T.HOLDOUT_QUARTERS:])
    cv_mask, ho_mask = ~q.isin(hold), q.isin(hold)
    X_cv, y_cv = X[cv_mask], y[cv_mask]
    df_cv = pd.DataFrame({"quarter": q[cv_mask].values}, index=X_cv.index)

    def objective(trial):
        params = {
            "objective": "binary", "verbosity": -1, "boosting_type": "gbdt",
            "random_state": seed, "class_weight": "balanced",
            "num_leaves": trial.suggest_int("num_leaves", 2, 64),
            "max_depth": trial.suggest_int("max_depth", 2, 10),
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }
        sp = WalkForwardSplitter(min_train_quarters=T.MIN_TRAIN_QUARTERS, forecast_gap=0)
        scores = []
        for tr, te in sp.split(df_cv):
            if len(tr) < 5 or len(te) < 1:
                continue
            m = LGBMClassifier(**params)
            m.fit(X_cv.loc[tr], y_cv.loc[tr])
            scores.append(f1_score(y_cv.loc[te], m.predict(X_cv.loc[te]),
                                   average="weighted", zero_division=0))
        return float(np.mean(scores)) if scores else 0.0

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=T.N_TRIALS, show_progress_bar=False)

    best = {**study.best_params, "objective": "binary", "verbosity": -1,
            "boosting_type": "gbdt", "random_state": seed, "class_weight": "balanced"}
    m = LGBMClassifier(**best)
    m.fit(X_cv, y_cv)
    yh, ph = m.predict(X[ho_mask]), m.predict_proba(X[ho_mask])[:, 1]
    yt = y[ho_mask]
    try:
        auc = float(roc_auc_score(yt, ph))
    except ValueError:
        auc = float("nan")

    used = int(sum(1 for s in m.booster_.feature_importance("split") if s > 0))
    nlp_used = int(sum(1 for c, s in zip(cols, m.booster_.feature_importance("split"))
                       if s > 0 and (c.startswith("FSSI") or c.startswith("trigger_"))))
    return {
        "seed": seed,
        "accuracy": round(float(accuracy_score(yt, yh)), 4),
        "precision": round(float(precision_score(yt, yh, average="weighted", zero_division=0)), 4),
        "recall": round(float(recall_score(yt, yh, average="weighted", zero_division=0)), 4),
        "f1": round(float(f1_score(yt, yh, average="weighted", zero_division=0)), 4),
        "roc_auc": round(auc, 4),
        "confusion": confusion_matrix(yt, yh, labels=[0, 1]).tolist(),
        "features_used": used,
        "nlp_features_used": nlp_used,
    }


def main() -> None:
    runs = [run_one(s) for s in SEEDS]
    keys = ("accuracy", "precision", "recall", "f1", "roc_auc")
    summary = {
        k: {"mean": round(float(np.nanmean([r[k] for r in runs])), 4),
            "sd": round(float(np.nanstd([r[k] for r in runs], ddof=1)), 4),
            "min": round(float(np.nanmin([r[k] for r in runs])), 4),
            "max": round(float(np.nanmax([r[k] for r in runs])), 4)}
        for k in keys
    }
    OUT.write_text(json.dumps({"seeds": SEEDS, "runs": runs, "summary": summary}, indent=2))

    print(f"\nALGORITHM 4 ACROSS {len(SEEDS)} SEEDS  (holdout n=20, methodology unchanged)")
    print("=" * 78)
    print(f"  {'seed':>6s} {'acc':>7s} {'prec':>7s} {'rec':>7s} {'f1':>7s} {'auc':>7s} "
          f"{'feats':>6s} {'NLP':>4s}")
    for r in runs:
        print(f"  {r['seed']:6d} {r['accuracy']:7.4f} {r['precision']:7.4f} {r['recall']:7.4f} "
              f"{r['f1']:7.4f} {r['roc_auc']:7.4f} {r['features_used']:6d} {r['nlp_features_used']:4d}")
    print("-" * 78)
    for k in keys:
        s = summary[k]
        print(f"  {k:10s} mean {s['mean']:.4f}  sd {s['sd']:.4f}  range {s['min']:.4f}–{s['max']:.4f}")
    print("=" * 78)
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
