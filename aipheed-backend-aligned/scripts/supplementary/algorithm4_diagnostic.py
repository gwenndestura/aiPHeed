"""
scripts/supplementary/algorithm4_diagnostic.py

Algorithm 4 diagnostic after the Algorithm 3 optimization (acceptance rule
unchanged: holdout weighted F1 >= 0.75 and AUC-ROC >= 0.80).

Same timing-valid inputs and k = 1 forward pairing. 100-trial TPE over the nine
approved hyperparameters, mean weighted F1 over the CV window's walk-forward
folds, the last four target quarters held out and scored once. Three
technically valid class-handling settings are compared; none changes the rule.
Writes evidence/2026-10-08_optimization/algorithm4_diagnostic.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import optuna
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.reliability_diagnostics as R

OUT = Path("evidence/2026-10-08_optimization/algorithm4_diagnostic.json")


def run(setting: str) -> dict:
    f, labels, cols = A.frame_t2()
    d = R.pairs(f, labels, 1)
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    hold = tq[-4:]
    cv, ho = d[~d["target_quarter"].isin(hold)], d[d["target_quarter"].isin(hold)]
    cvq = sorted(cv["target_quarter"].unique(), key=R.qi)

    def extra(train):
        if setting == "balanced":
            return {"class_weight": "balanced"}
        if setting == "scale_pos_weight_ratio":
            pos = train["y"].mean()
            return {"scale_pos_weight": float((1 - pos) / pos)}
        return {}

    def obj(trial):
        p = {"objective": "binary", "verbosity": -1, "random_state": 42, "subsample_freq": 1,
             "num_leaves": trial.suggest_int("num_leaves", 2, 64),
             "max_depth": trial.suggest_int("max_depth", 2, 10),
             "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
             "n_estimators": trial.suggest_int("n_estimators", 50, 500),
             "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
             "subsample": trial.suggest_float("subsample", 0.6, 1.0),
             "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
             "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
             "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True)}
        s = []
        for i in range(R.MIN_TRAIN, len(cvq)):
            tr = cv[cv["target_quarter"].map(R.qi) < R.qi(cvq[i])]
            te = cv[cv["target_quarter"] == cvq[i]]
            m = LGBMClassifier(**p, **extra(tr)).fit(tr[cols], tr["y"])
            if int(m.booster_.feature_importance("split").sum()) == 0:
                raise optuna.TrialPruned()
            s.append(f1_score(te["y"], m.predict(te[cols]), average="weighted", zero_division=0))
        return float(np.mean(s)) if s else 0.0

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    st = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    st.optimize(obj, n_trials=100)
    best = {**st.best_params, "objective": "binary", "verbosity": -1, "random_state": 42,
            "subsample_freq": 1, **extra(cv)}
    m = LGBMClassifier(**best).fit(cv[cols], cv["y"])
    prob = m.predict_proba(ho[cols])[:, 1]
    y = ho["y"].values
    pred = (prob >= 0.5).astype(int)
    low = [round(float(p), 3) for p, t in zip(prob, y) if t == 0]
    return {"setting": setting, "cv_weighted_f1": round(st.best_value, 4),
            "holdout_accuracy": round(float(accuracy_score(y, pred)), 4),
            "holdout_f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
            "holdout_auc": round(float(roc_auc_score(y, prob)), 4),
            "low_row_probabilities": low,
            "high_rows_scored_below_lowest_LOW": int((prob[y == 1] < min(prob[y == 0])).sum()),
            "n_holdout": int(len(y)), "n_low": int((y == 0).sum()),
            "meets_f1": bool(f1_score(y, pred, average="weighted", zero_division=0) >= 0.75),
            "meets_auc": bool(roc_auc_score(y, prob) >= 0.80)}


def main():
    res = [run(s) for s in ("default", "balanced", "scale_pos_weight_ratio")]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
