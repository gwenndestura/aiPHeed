"""
scripts/supplementary/algorithm4_candidate.py

Algorithm 4 run as Chapter III writes it, on the candidate configuration found
by reliability_diagnostics.py (experiment only, nothing is served):

  * input: the Section 3.3.2.6 matrix (45 candidates + CPI_dev + SWS hunger at t),
    poverty incidence entering only once PSA has published it;
  * forecast gap = the Maximum Reliable Lead Time found by Algorithm 3 (k = 1),
    implemented as features at t -> label at t+1 within province (Rule 3);
  * 100-trial Optuna TPE over the nine approved hyperparameters, objective =
    mean weighted F1 across walk-forward folds of the CV window;
  * the last four target quarters are held out and never shown to Optuna;
  * the best parameters are scored once on that holdout.

    python -m scripts.supplementary.algorithm4_candidate
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import optuna
from lightgbm import LGBMClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

import scripts.supplementary.reliability_diagnostics as R

OUT = Path("data/supplementary/algorithm4_candidate.json")
SEED = 42
HOLDOUT = 4


def main() -> dict:
    f, labels, cand = R.load()
    cols = cand + ["cpi_dev", "sws_hunger"]
    d = R.pairs(f, labels, k=1)
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    hold_q = tq[-HOLDOUT:]
    cv = d[~d["target_quarter"].isin(hold_q)]
    ho = d[d["target_quarter"].isin(hold_q)]
    cv_q = sorted(cv["target_quarter"].unique(), key=R.qi)

    def objective(trial):
        params = {
            "objective": "binary", "verbosity": -1, "random_state": SEED,
            "num_leaves": trial.suggest_int("num_leaves", 2, 64),
            "max_depth": trial.suggest_int("max_depth", 2, 10),
            "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
            "subsample_freq": 1,
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }
        scores = []
        for i in range(R.MIN_TRAIN, len(cv_q)):
            tr = cv[cv["target_quarter"].map(R.qi) < R.qi(cv_q[i])]
            te = cv[cv["target_quarter"] == cv_q[i]]
            if tr["y"].nunique() < 2:
                continue
            m = LGBMClassifier(**params).fit(tr[cols], tr["y"])
            if int(m.booster_.feature_importance("split").sum()) == 0:
                raise optuna.TrialPruned()
            scores.append(f1_score(te["y"], m.predict(te[cols]), average="weighted", zero_division=0))
        return float(np.mean(scores)) if scores else 0.0

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=100)
    best = {**study.best_params, "objective": "binary", "verbosity": -1,
            "random_state": SEED, "subsample_freq": 1}

    m = LGBMClassifier(**best).fit(cv[cols], cv["y"])
    prob = m.predict_proba(ho[cols])[:, 1]
    pred = (prob >= 0.5).astype(int)
    y = ho["y"].values
    persist = ho["last_label"].fillna(0).astype(int).values
    out = {
        "holdout_quarters": hold_q, "n_holdout": int(len(ho)), "holdout_high_share": round(float(y.mean()), 3),
        "best_cv_weighted_f1": round(float(study.best_value), 4), "best_params": study.best_params,
        "holdout": {
            "accuracy": round(float(accuracy_score(y, pred)), 4),
            "precision_weighted": round(float(precision_score(y, pred, average="weighted", zero_division=0)), 4),
            "recall_weighted": round(float(recall_score(y, pred, average="weighted", zero_division=0)), 4),
            "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y, prob)), 4) if len(set(y)) > 1 else None,
            "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
        },
        "holdout_persistence_accuracy": round(float(accuracy_score(y, persist)), 4),
        "holdout_always_high_accuracy": round(float(y.mean()), 4),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
