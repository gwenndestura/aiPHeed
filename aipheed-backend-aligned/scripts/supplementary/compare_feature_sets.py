"""
scripts/compare_feature_sets.py
--------------------------------
Evaluate the model on both readings of Section 3.3.2.7.

Section 3.3.2.7 specifies a two-stage selection *process* and also reports the
*outcome* that process produced on the proposal's own data: twelve features —
FSSI and its two lags and acceleration, the five bilingual trigger proportions,
and food CPI deviation, unemployment rate and quarter-over-quarter rice price
change.

On the data actually available those two can disagree: running the approved
process may retain a different set. The proposal's twelve are a result, and
results move with the data the task permits to change; the process is the
methodology and does not. So the pipeline trains on the process output.

That leaves a fair question for a reviewer — what would the model score on the
twelve features the proposal names? This script answers it by running the same
Algorithm 3 and Algorithm 4 on each set and printing them side by side. It adds
no method; it evaluates one that is already approved, twice.

    python -m scripts.compare_feature_sets
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PROC = Path("data/processed")
OUT = Path("data/supplementary/feature_set_comparison.json")


def evaluate(cols: list[str], label: str) -> dict:
    """Algorithm 3 then a holdout fit, on one feature set."""
    from lightgbm import LGBMClassifier
    from sklearn.metrics import (
        accuracy_score, f1_score, precision_score, recall_score, roc_auc_score,
    )

    from app.ml.training import trainer as T
    from app.ml.training.cross_validation import WalkForwardSplitter

    feats = pd.read_parquet(PROC / "features_fused.parquet")
    labels = pd.read_parquet(PROC / "labels.parquet")
    df = feats.merge(labels[["province_code", "quarter", "label_stress"]],
                     on=["province_code", "quarter"], how="inner")
    df = df.sort_values(["quarter", "province_code"]).reset_index(drop=True)

    missing = [c for c in cols if c not in df.columns]
    if missing:
        return {"feature_set": label, "error": f"missing columns: {missing}"}

    X, y, q = df[cols], df["label_stress"].astype(int), df["quarter"]
    dfq = pd.DataFrame({"quarter": q.values}, index=X.index)

    # Algorithm 3 on this set.
    k_max, scan = 0, []
    for k in range(1, T.MAX_LEAD_QUARTERS + 1):
        sp = WalkForwardSplitter(min_train_quarters=T.MIN_TRAIN_QUARTERS, forecast_gap=k)
        try:
            if sp.get_n_splits(dfq) < 1:
                break
        except ValueError:
            break
        accs = []
        for tr, te in sp.split(dfq):
            if len(tr) < 5 or len(te) < 1:
                continue
            m = LGBMClassifier(**T.DISCOVERY_PARAMS)
            m.fit(X.loc[tr], y.loc[tr])
            accs.append(accuracy_score(y.loc[te], m.predict(X.loc[te])))
        if not accs:
            break
        mean_acc = float(np.mean(accs))
        scan.append({"k": k, "accuracy": round(mean_acc, 4),
                     "passed": mean_acc >= T.ACCURACY_THRESHOLD})
        if mean_acc >= T.ACCURACY_THRESHOLD:
            k_max = k
        else:
            break

    # Holdout fit at the discovered horizon, with default params so the two
    # sets are compared on the features rather than on a tuning budget.
    quarters = sorted(q.unique())
    need = T.MIN_TRAIN_QUARTERS + k_max + 1 + T.HOLDOUT_QUARTERS
    if len(quarters) < need:
        return {"feature_set": label, "n_features": len(cols),
                "max_reliable_lead_time": k_max, "lead_time_scan": scan,
                "error": f"needs {need} quarters for the holdout, has {len(quarters)}"}

    hold = set(quarters[-T.HOLDOUT_QUARTERS:])
    cv, ho = ~q.isin(hold), q.isin(hold)
    m = LGBMClassifier(**T.DISCOVERY_PARAMS)
    m.fit(X[cv], y[cv])
    pred, prob = m.predict(X[ho]), m.predict_proba(X[ho])[:, 1]
    try:
        auc = float(roc_auc_score(y[ho], prob))
    except ValueError:
        auc = float("nan")

    return {
        "feature_set": label,
        "n_features": len(cols),
        "features": cols,
        "max_reliable_lead_time": k_max,
        "lead_time_scan": scan,
        "holdout_accuracy": round(float(accuracy_score(y[ho], pred)), 4),
        "holdout_precision": round(float(precision_score(
            y[ho], pred, average="weighted", zero_division=0)), 4),
        "holdout_recall": round(float(recall_score(
            y[ho], pred, average="weighted", zero_division=0)), 4),
        "holdout_f1": round(float(f1_score(
            y[ho], pred, average="weighted", zero_division=0)), 4),
        "holdout_roc_auc": round(auc, 4),
    }


def main() -> None:
    from app.ml.features.feature_selector import EXPECTED_FINAL_FEATURES, load_selected

    runs = [
        evaluate(load_selected(), "selection run on the available data"),
        evaluate(list(EXPECTED_FINAL_FEATURES), "the twelve the proposal reports"),
    ]
    OUT.write_text(json.dumps(runs, indent=2))

    print("\nFEATURE SET COMPARISON  (default LightGBM, same folds)")
    print("=" * 78)
    for r in runs:
        print(f"\n{r['feature_set']}  ({r.get('n_features')} features)")
        if "error" in r:
            print(f"  could not evaluate: {r['error']}")
            continue
        print(f"  Maximum Reliable Lead Time : {r['max_reliable_lead_time']}")
        for m in ("holdout_accuracy", "holdout_precision", "holdout_recall",
                  "holdout_f1", "holdout_roc_auc"):
            print(f"  {m:27s}: {r[m]}")
    print("=" * 78)
    print(f"written -> {OUT}")


if __name__ == "__main__":
    main()
