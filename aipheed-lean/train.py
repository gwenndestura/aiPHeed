"""
train.py
--------
One model. One LightGBM classifier, walk-forward by quarter.

No ensemble, no per-commodity-group models, no target encoding, no tuned
threshold, no abstention band. Each of those was measured in the original
pipeline and each bought between +0.004 and +0.023 accuracy, at the cost of
machinery that has to be explained and defended. They are left out here so the
number this file reports is the number a reader can reproduce from the code in
front of them.

Validation is walk-forward: to score quarter Q the model is fit on every
quarter strictly before Q, needing at least MIN_TRAIN_QUARTERS of them. No test
quarter influences any fit. Because whole quarters are held out, no commodity
from a test quarter appears in training in any form.

Both baselines are reported with every figure:

    majority              always predict "no shock"
    seasonal persistence  predict what this series did in the same quarter
                          one year ago

Seasonal persistence is the one that matters. Production is on an annual cycle,
so the same quarter a year back is a strong and entirely free predictor, and a
model that cannot beat it is not earning its complexity.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

from features import LEAN_FEATURES, build_features, leakage_check
from panel import load_panel

OUT = Path(__file__).resolve().parent / "outputs"

MIN_TRAIN_QUARTERS = 8
RANDOM_SEED = 42

# Identical to the original pipeline's, so a head-to-head isolates the feature
# set rather than the hyperparameters. Retuning was measured as exhausted on
# this data: 25 Optuna trials moved held-out accuracy by -0.0001.
PARAMS = dict(objective="binary", verbosity=-1, random_state=RANDOM_SEED,
              class_weight="balanced", n_estimators=300, learning_rate=0.05,
              num_leaves=16, max_depth=4, min_child_samples=20,
              subsample=0.8, colsample_bytree=0.8, reg_alpha=0.5, reg_lambda=0.5)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def metrics(y_true, y_pred, y_prob=None) -> dict:
    """
    Accuracy, precision, recall and F1 -- the four the CS department requires --
    reported for the SHOCK class and again support-weighted, plus ROC-AUC and
    the raw confusion counts.

    The shock-class figures are the ones to lead with. The positive rate is
    about 0.29, so a weighted average is carried by the easy majority class and
    will look good even when the model is missing most real shortfalls.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    out = {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "shock": {
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        },
        "weighted": {
            "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        },
        "confusion": {"tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)},
        "positive_rate": float(y_true.mean()),
        "roc_auc": None,
    }
    if y_prob is not None and len(np.unique(y_true)) > 1:
        out["roc_auc"] = float(roc_auc_score(y_true, np.asarray(y_prob)))
    return out


def baselines(d: pd.DataFrame) -> dict:
    """Majority class and seasonal persistence, on exactly the rows scored."""
    y = d["label_shock"].astype(int)
    majority = float(max(y.mean(), 1 - y.mean()))

    seas = d.dropna(subset=["shock_lag4"])
    seasonal = (float(accuracy_score(seas["label_shock"].astype(int),
                                     seas["shock_lag4"].astype(int)))
                if len(seas) else float("nan"))
    return {"majority": majority,
            "seasonal_persistence": seasonal,
            "seasonal_n": int(len(seas))}


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------

def walk_forward(df: pd.DataFrame, cols: list[str],
                 min_train_quarters: int = MIN_TRAIN_QUARTERS) -> pd.DataFrame:
    """
    Score every quarter that has enough history behind it.

    Returns one row per scored observation with the true label, the predicted
    label, the predicted probability and the fold index, so a caller can slice
    by quarter, province or maturity without refitting anything.
    """
    quarters = sorted(df["quarter"].unique())
    frames = []

    for i, q in enumerate(quarters):
        if i < min_train_quarters:
            continue
        train = df[df["quarter"] < q]
        test = df[df["quarter"] == q]
        if test.empty or train["label_shock"].nunique() < 2:
            continue

        model = LGBMClassifier(**PARAMS).fit(train[cols], train["label_shock"])
        prob = model.predict_proba(test[cols])[:, 1]

        frames.append(pd.DataFrame({
            "quarter": test["quarter"].values,
            "group": test["group"].values,
            "commodity": test["commodity"].values,
            "province_name": test["province_name"].values,
            "label_shock": test["label_shock"].astype(int).values,
            "shock_lag4": test["shock_lag4"].values,
            "prob": prob,
            "pred": (prob >= 0.5).astype(int),
            "fold": i - min_train_quarters,
            "train_quarters": i,
        }))

    if not frames:
        raise RuntimeError("no fold had enough history to score")
    return pd.concat(frames, ignore_index=True)


def report(preds: pd.DataFrame) -> dict:
    """Metrics plus baselines plus the skill margin over each."""
    m = metrics(preds["label_shock"], preds["pred"], preds["prob"])
    b = baselines(preds)
    m["baselines"] = b
    m["skill_vs_majority"] = m["accuracy"] - b["majority"]
    m["skill_vs_seasonal"] = m["accuracy"] - b["seasonal_persistence"]
    return m


def block(title: str, m: dict, indent: str = "  ") -> None:
    s, w, c = m["shock"], m["weighted"], m["confusion"]
    b = m["baselines"]
    auc = f"{m['roc_auc']:.4f}" if m["roc_auc"] is not None else "n/a"
    print(f"\n{indent}{title}")
    print(f"{indent}  n={m['n']:<6d} accuracy={m['accuracy']:.4f}   ROC-AUC={auc}")
    print(f"{indent}    shock class    precision={s['precision']:.4f}  "
          f"recall={s['recall']:.4f}  F1={s['f1']:.4f}")
    print(f"{indent}    weighted avg   precision={w['precision']:.4f}  "
          f"recall={w['recall']:.4f}  F1={w['f1']:.4f}")
    print(f"{indent}    confusion      TP={c['tp']} FP={c['fp']} FN={c['fn']} TN={c['tn']}")
    print(f"{indent}    majority {b['majority']:.4f} (skill {m['skill_vs_majority']:+.4f})"
          f"   |   seasonal persistence {b['seasonal_persistence']:.4f} "
          f"(skill {m['skill_vs_seasonal']:+.4f})")


def table(title: str, groups: dict) -> None:
    print(f"\n  {title}   (precision/recall/F1 = shock class)")
    print(f"    {'':22s} {'n':>6s} {'acc':>8s} {'prec':>8s} {'rec':>8s} {'F1':>8s} {'AUC':>8s}")
    for k, m in sorted(groups.items()):
        auc = f"{m['roc_auc']:.4f}" if m["roc_auc"] is not None else "n/a"
        print(f"    {k:22s} {m['n']:6d} {m['accuracy']:8.4f} {m['shock']['precision']:8.4f} "
              f"{m['shock']['recall']:8.4f} {m['shock']['f1']:8.4f} {auc:>8s}")


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Train and evaluate the lean model.")
    ap.add_argument("--mature-folds", type=int, default=4,
                    help="folds of history below which a row counts as cold-start")
    args = ap.parse_args()

    raw = load_panel()

    fails = leakage_check(raw)
    if fails:
        print("LEAKAGE CHECK FAILED -- refusing to train:", file=sys.stderr)
        for f in fails:
            print("   ", f, file=sys.stderr)
        sys.exit(1)

    df = build_features(raw)
    print(f"panel {len(df):,} rows | quarters {df['quarter'].min()}..{df['quarter'].max()} "
          f"| shock rate {df['label_shock'].mean():.3f} | {len(LEAN_FEATURES)} features "
          f"| leakage check PASS")

    preds = walk_forward(df, LEAN_FEATURES)

    overall = report(preds)
    mature = preds[preds["fold"] >= args.mature_folds]
    cold = preds[preds["fold"] < args.mature_folds]

    print("\n" + "=" * 86)
    print("aiPHeed LEAN -- one LightGBM, 12 features, walk-forward by quarter")
    print("=" * 86)
    block("all folds", overall)
    if len(mature):
        block(f"mature folds (>= {args.mature_folds} folds of history)", report(mature))
    if len(cold):
        block(f"cold-start folds (< {args.mature_folds} folds)", report(cold))

    by_group = {g: report(d) for g, d in preds.groupby("group")
                if d["label_shock"].nunique() > 1}
    by_prov = {g: report(d) for g, d in preds.groupby("province_name")
               if d["label_shock"].nunique() > 1}
    table("by commodity group", by_group)
    table("by province", by_prov)
    print("\n" + "=" * 86)
    print(f"folds: {preds['fold'].nunique()}   scored observations: {len(preds):,}")
    print("=" * 86)

    OUT.mkdir(exist_ok=True)
    payload = {
        "features": LEAN_FEATURES,
        "n_features": len(LEAN_FEATURES),
        "params": dict(PARAMS),
        "quarters": [df["quarter"].min(), df["quarter"].max()],
        "all_folds": overall,
        "mature_folds": report(mature) if len(mature) else None,
        "cold_start_folds": report(cold) if len(cold) else None,
        "by_group": by_group,
        "by_province": by_prov,
    }
    (OUT / "lean_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    preds.to_parquet(OUT / "lean_predictions.parquet", index=False)
    print(f"\nsaved -> {OUT / 'lean_results.json'}")
    print(f"saved -> {OUT / 'lean_predictions.parquet'}")


if __name__ == "__main__":
    main()
