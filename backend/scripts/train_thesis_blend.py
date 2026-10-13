"""
scripts/train_thesis_blend.py
------------------------------
Train the three-way blend that ThesisPredictor serves, so the quarterly
scheduler can retrain it unattended.

Why this script exists: the served bundle (models/thesis_food_insecurity_model
.joblib, model_type "three_way_blend") had no builder in the repository.
scripts/train_thesis_model.py writes a LightGBM-only bundle under the key
"model", which ThesisPredictor cannot load (it reads "lgbm_model",
"lr_model", ...). Pointing the scheduler at that script would have taken the
dashboard down on the first quarterly run.

The recipe below is reconstructed from what the served bundle records about
itself, not from the lost script:
    lgbm_model   LightGBM on Equation 5's 12 features, Optuna TPE (Algorithm 4),
                 search space and objective from train_thesis_model.tune()
    lr_model     LogisticRegression (L2, max_iter 1000) on the 3 government
                 features, StandardScaler, missing values filled with 0.0
    weak_model   LogisticRegression (L2, class_weight balanced) on the climate,
                 fish-kill and OFW-remittance triggers, StandardScaler, 0.0 fill
    weights      0.4 / 0.4 / 0.2
    threshold    F1-maximising cutoff on the BLENDED walk-forward out-of-fold
                 scores of the most recent half of the tuning quarters, the
                 same holdout-blind rule train_thesis_model.py uses
The 0.0 fill matches ThesisPredictor._score(), so the models are trained on
the same inputs they are served.

Because the lost script's exact cutoff search is unknown, a retrain will not
reproduce the current 0.712 cutoff or metrics to the decimal. Every retrain
records its own walk-forward and blind-holdout metrics in the bundle.

Usage:
    cd backend
    python scripts/train_thesis_blend.py --out models/candidates/blend.joblib
    python scripts/train_thesis_blend.py --trials 20 --out ...   # quick check
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_thesis_model as base  # noqa: E402  (tune, pick_threshold, constants)

ROOT = Path(__file__).resolve().parents[1]

LGBM_COLS = base.FEATURE_COLS
LR_COLS = ["cpi_deviation", "unemployment_rate", "rice_price_qoq_change"]
WEAK_COLS = ["trigger_climate", "trigger_fish_kill", "trigger_ofw_remittance"]
W_LGBM, W_LR, W_WEAK = 0.4, 0.4, 0.2
LABEL = "label_stress"


def _fit_components(train: pd.DataFrame, params: dict) -> dict:
    lgbm = LGBMClassifier(**params).fit(train[LGBM_COLS], train[LABEL])

    lr_scaler = StandardScaler().fit(train[LR_COLS].fillna(0.0))
    lr = LogisticRegression(max_iter=1000, random_state=base.SEED).fit(
        lr_scaler.transform(train[LR_COLS].fillna(0.0)), train[LABEL])

    weak_scaler = StandardScaler().fit(train[WEAK_COLS].fillna(0.0))
    weak = LogisticRegression(max_iter=1000, class_weight="balanced",
                              random_state=base.SEED).fit(
        weak_scaler.transform(train[WEAK_COLS].fillna(0.0)), train[LABEL])

    return {"lgbm_model": lgbm, "lr_model": lr, "lr_scaler": lr_scaler,
            "weak_model": weak, "weak_scaler": weak_scaler}


def blend_proba(c: dict, rows: pd.DataFrame) -> np.ndarray:
    """Identical arithmetic to ThesisPredictor._score()."""
    p = W_LGBM * c["lgbm_model"].predict_proba(rows[LGBM_COLS])[:, 1]
    p += W_LR * c["lr_model"].predict_proba(
        c["lr_scaler"].transform(rows[LR_COLS].fillna(0.0)))[:, 1]
    p += W_WEAK * c["weak_model"].predict_proba(
        c["weak_scaler"].transform(rows[WEAK_COLS].fillna(0.0)))[:, 1]
    return p


def blended_walk_forward(df: pd.DataFrame, params: dict):
    """Expanding window, one quarter per fold, >= MIN_TRAIN_QUARTERS of history."""
    quarters = sorted(df["_qk"].unique())
    probs, ys, qks = [], [], []
    for i in range(base.MIN_TRAIN_QUARTERS, len(quarters)):
        tr = df[df["_qk"].isin(quarters[:i])]
        te = df[df["_qk"] == quarters[i]]
        if len(te) == 0 or tr[LABEL].nunique() < 2:
            continue
        probs.append(blend_proba(_fit_components(tr, params), te))
        ys.append(te[LABEL].to_numpy())
        qks.append(np.full(len(te), quarters[i]))
    if not probs:
        return np.array([]), np.array([]), np.array([])
    return np.concatenate(probs), np.concatenate(ys), np.concatenate(qks)


def _metrics(y: np.ndarray, prob: np.ndarray, threshold: float) -> dict:
    pred = (prob >= threshold).astype(int)
    out = {
        "n": int(len(y)),
        "n_positive": int(y.sum()),
        "n_negative": int(len(y) - y.sum()),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
    }
    out["roc_auc"] = float(roc_auc_score(y, prob)) if len(set(y)) > 1 else None
    return out


def train(panel_path: Path, n_trials: int) -> dict:
    df = pd.read_parquet(panel_path)
    quarters = sorted(df["_qk"].unique())
    holdout_qk = quarters[-base.HOLDOUT_QUARTERS:]
    tune_df = df[~df["_qk"].isin(holdout_qk)]
    holdout_df = df[df["_qk"].isin(holdout_qk)]

    base.N_TRIALS = n_trials
    print(f"Tuning LightGBM on {len(tune_df)} rows, {n_trials} Optuna trials...")
    best_params = base.tune(tune_df)
    params = dict(objective="binary", verbosity=-1, random_state=base.SEED, **best_params)

    # Cutoff: blended out-of-fold scores, most recent half of the tuning folds.
    tune_prob, tune_y, tune_qk = blended_walk_forward(tune_df, params)
    recent = tune_qk >= np.median(np.unique(tune_qk))
    threshold = base.pick_threshold(tune_prob[recent], tune_y[recent])
    print(f"Cutoff from blended walk-forward scores: {threshold:.3f}")

    # Blind holdout: components fitted on tuning rows only.
    hold_prob = blend_proba(_fit_components(tune_df, params), holdout_df)
    holdout_metrics = _metrics(holdout_df[LABEL].to_numpy(), hold_prob, threshold)

    # Walk-forward over the whole panel, the figure the dashboard reports.
    wf_prob, wf_y, _ = blended_walk_forward(df, params)
    walk_forward_metrics = _metrics(wf_y, wf_prob, threshold)

    meets = bool(holdout_metrics["f1"] >= 0.75
                 and (holdout_metrics["roc_auc"] or 0.0) >= 0.80)

    production = _fit_components(df, params)
    df_q = df.sort_values("_qk")
    bundle = {
        "model_type": "three_way_blend",
        **production,
        "weak_feature_cols": WEAK_COLS,
        "lgbm_feature_cols": LGBM_COLS,
        "lr_feature_cols": LR_COLS,
        "blend_weight_lgbm": W_LGBM,
        "blend_weight_lr": W_LR,
        "blend_weight_weak": W_WEAK,
        "feature_cols": LGBM_COLS,
        "label": "label_cpi (thesis Eq. 4)",
        "threshold": threshold,
        "trained_through": df_q["quarter"].iloc[-1],
        "n_train_rows": int(len(df)),
        "best_params": params,
        "holdout_metrics": holdout_metrics,
        "walk_forward_metrics": walk_forward_metrics,
        "holdout_quarters": sorted(holdout_df["quarter"].unique().tolist()),
        "trivial_baseline_check": {
            "note": "always-positive baseline on the same holdout",
            "accuracy": float(holdout_df[LABEL].mean()),
        },
        "meets_thesis_targets": meets,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trained_by": "scripts/train_thesis_blend.py",
        "note": (
            "Three-way blend: Optuna-tuned LightGBM (40%) + government-only LR "
            "(40%) + climate/fish-kill/OFW-remittance trigger LR (20%). Cutoff "
            "chosen from blended walk-forward out-of-fold scores, never from the "
            "holdout. Holdout "
            + ("clears" if meets else "does not clear")
            + " the Algorithm 4 targets (F1>=0.75, AUC>=0.80)."
        ),
    }
    return bundle


def main() -> None:
    ap = argparse.ArgumentParser(description="Train the served three-way blend")
    ap.add_argument("--panel", type=Path, default=base.PANEL_PATH)
    ap.add_argument("--out", type=Path, required=True,
                    help="where to write the bundle (a candidate path, not the served file)")
    ap.add_argument("--trials", type=int, default=base.N_TRIALS)
    args = ap.parse_args()

    bundle = train(args.panel, args.trials)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.out)
    summary = {k: bundle[k] for k in ("trained_through", "n_train_rows", "threshold",
                                      "holdout_metrics", "walk_forward_metrics",
                                      "meets_thesis_targets")}
    print(json.dumps(summary, indent=2))
    print(f"Saved -> {args.out}")


if __name__ == "__main__":
    main()
