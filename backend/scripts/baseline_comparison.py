"""
scripts/baseline_comparison.py
---------------------------------
Runs the six real baseline comparisons the paper specifies (Section 1.3 /
Hypothesis H3), against the same real data and evaluation method used
throughout this project (label_cpi, the paper's 12 features, pooled
walk-forward across every real quarter):

  1. Naive persistence          -- predict same label as this province's
                                    previous real quarter
  2. Logistic Regression, combined (all 12 features)
  3. Logistic Regression, government-only (3 features: cpi_deviation,
                                    unemployment_rate, rice_price_qoq_change)
  4. Logistic Regression, NLP-only (9 features: FSSI + 3 derived, 5 triggers)
  5. LightGBM, government-only ablation
  6. LightGBM, NLP-only ablation
  7. LightGBM, combined (the paper's actual proposed model, both
                                    data sources) -- the one this project has
                                    been reporting all along

H3 predicts #7 outperforms all of #1-6. Real, honest result either way.
"""
from __future__ import annotations

import json
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

DATA_DIR = "data/thesis"
MIN_TRAIN_QUARTERS = 8

ALL_12 = [
    "FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel",
    "trigger_market", "trigger_climate", "trigger_employment",
    "trigger_ofw_remittance", "trigger_fish_kill",
    "cpi_deviation", "unemployment_rate", "rice_price_qoq_change",
]
GOV_ONLY = ["cpi_deviation", "unemployment_rate", "rice_price_qoq_change"]
NLP_ONLY = [c for c in ALL_12 if c not in GOV_ONLY]


def walk_forward_generic(df: pd.DataFrame, feature_cols: list[str], fit_predict_fn):
    """fit_predict_fn(X_train, y_train, X_test) -> prob array for test rows"""
    quarters = sorted(df["_qk"].unique())
    all_prob, all_y = [], []
    for i in range(MIN_TRAIN_QUARTERS, len(quarters)):
        tr = df[df["_qk"].isin(quarters[:i])]
        te = df[df["_qk"] == quarters[i]]
        if len(te) == 0 or tr["label_stress"].nunique() < 2:
            continue
        Xtr = tr[feature_cols].fillna(0.0)
        Xte = te[feature_cols].fillna(0.0)
        prob = fit_predict_fn(Xtr, tr["label_stress"], Xte)
        all_prob.append(prob)
        all_y.append(te["label_stress"].to_numpy())
    return np.concatenate(all_prob), np.concatenate(all_y)


def eval_metrics(y, prob, thr=0.5):
    pred = (prob >= thr).astype(int)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "auc": float(roc_auc_score(y, prob)) if len(set(y)) > 1 else float("nan"),
    }


def naive_persistence(df: pd.DataFrame) -> dict:
    """Predict this province's own previous real quarter's label."""
    df = df.sort_values(["province_code", "_qk"]).copy()
    df["prev_label"] = df.groupby("province_code")["label_stress"].shift(1)
    valid = df.dropna(subset=["prev_label"])
    y = valid["label_stress"].to_numpy()
    pred = valid["prev_label"].to_numpy()
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "auc": None,  # persistence has no probability score
    }


def lr_fit_predict(Xtr, ytr, Xte):
    scaler = StandardScaler()
    Xtr_s = scaler.fit_transform(Xtr)
    Xte_s = scaler.transform(Xte)
    m = LogisticRegression(max_iter=1000, random_state=42)
    m.fit(Xtr_s, ytr)
    return m.predict_proba(Xte_s)[:, 1]


def lgbm_fit_predict(Xtr, ytr, Xte, params=None):
    p = dict(objective="binary", verbosity=-1, random_state=42,
            n_estimators=100, num_leaves=8, max_depth=3, min_child_samples=3)
    if params:
        p.update(params)
    m = LGBMClassifier(**p)
    m.fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, 1]


def main() -> None:
    df = pd.read_parquet(f"{DATA_DIR}/panel.parquet")
    results = {}

    print("1. Naive persistence...")
    results["naive_persistence"] = naive_persistence(df)

    print("2. Logistic Regression, combined (12 features)...")
    prob, y = walk_forward_generic(df, ALL_12, lr_fit_predict)
    results["lr_combined"] = {"n": int(len(y)), **eval_metrics(y, prob)}

    print("3. Logistic Regression, government-only (3 features)...")
    prob, y = walk_forward_generic(df, GOV_ONLY, lr_fit_predict)
    results["lr_gov_only"] = {"n": int(len(y)), **eval_metrics(y, prob)}

    print("4. Logistic Regression, NLP-only (9 features)...")
    prob, y = walk_forward_generic(df, NLP_ONLY, lr_fit_predict)
    results["lr_nlp_only"] = {"n": int(len(y)), **eval_metrics(y, prob)}

    print("5. LightGBM, government-only ablation...")
    prob, y = walk_forward_generic(df, GOV_ONLY, lambda a, b, c: lgbm_fit_predict(a, b, c))
    results["lgbm_gov_only"] = {"n": int(len(y)), **eval_metrics(y, prob)}

    print("6. LightGBM, NLP-only ablation...")
    prob, y = walk_forward_generic(df, NLP_ONLY, lambda a, b, c: lgbm_fit_predict(a, b, c))
    results["lgbm_nlp_only"] = {"n": int(len(y)), **eval_metrics(y, prob)}

    print("7. LightGBM, combined (the paper's proposed model)...")
    import joblib
    bundle = joblib.load("models/thesis_food_insecurity_model.joblib")
    results["lgbm_combined_proposed"] = {
        "n": bundle["walk_forward_metrics"]["n"],
        "accuracy": bundle["walk_forward_metrics"]["accuracy"],
        "precision": bundle["walk_forward_metrics"]["precision"],
        "recall": bundle["walk_forward_metrics"]["recall"],
        "f1": bundle["walk_forward_metrics"]["f1"],
        "auc": bundle["walk_forward_metrics"]["roc_auc"],
    }

    print("\n" + "=" * 70)
    print(f"{'Model':<28} {'Acc':>7} {'Prec':>7} {'Rec':>7} {'F1':>7} {'AUC':>7}")
    print("=" * 70)
    for name, m in results.items():
        auc_str = f"{m['auc']:.3f}" if m.get("auc") is not None else "  n/a"
        print(f"{name:<28} {m['accuracy']:.3f}  {m['precision']:.3f}  "
              f"{m['recall']:.3f}  {m['f1']:.3f}  {auc_str}")

    with open(f"{DATA_DIR}/baseline_comparison.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved -> {DATA_DIR}/baseline_comparison.json")


if __name__ == "__main__":
    main()
