"""
scripts/supplementary/algorithm4_timing_valid.py

Algorithm 4 diagnostic, separate from Algorithm 3, on timing-valid inputs
(rule T2 of timing_audit.py: SWS as published before the forecast quarter,
government series of t-1, news of t, poverty as published). 100-trial TPE,
nine approved hyperparameters, mean weighted F1, k = 1, last four target
quarters held out and never shown to Optuna. Writes
data/supplementary/algorithm4_timing_valid.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score

import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.timing_audit as T


def frame_t2():
    f, labels, cand = R.load()
    rel = T.sws_release_dates()
    sws = pd.read_parquet("data/processed/sws_hunger.parquet").groupby("quarter")["pct_total_hunger"].first()
    def val(q):
        known = [(rel[s], s) for s in sws.index if s in rel and rel[s] < T.qstart(T.nxt(q))]
        return sws[max(known)[1]] if known else 0.0
    f["sws_hunger"] = f["quarter"].map(val)
    nlp = [c for c in cand if c.startswith(("FSSI", "trigger_"))]
    gov = [c for c in cand + ["cpi_dev"] if c not in nlp and c != "poverty_incidence"]
    f = f.sort_values(["province_code", "t"])
    f[gov] = f.groupby("province_code")[gov].shift(1).fillna(0.0)
    return f, labels, cand + ["cpi_dev", "sws_hunger"]


def main():
    f, labels, cols = frame_t2()
    d = R.pairs(f, labels, 1)
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    hold = tq[-4:]
    cv, ho = d[~d["target_quarter"].isin(hold)], d[d["target_quarter"].isin(hold)]
    cvq = sorted(cv["target_quarter"].unique(), key=R.qi)

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
            tr, te = cv[cv["target_quarter"].map(R.qi) < R.qi(cvq[i])], cv[cv["target_quarter"] == cvq[i]]
            m = LGBMClassifier(**p).fit(tr[cols], tr["y"])
            if int(m.booster_.feature_importance("split").sum()) == 0:
                raise optuna.TrialPruned()
            s.append(f1_score(te["y"], m.predict(te[cols]), average="weighted", zero_division=0))
        return float(np.mean(s)) if s else 0.0

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    st = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    st.optimize(obj, n_trials=100)
    best = {**st.best_params, "objective": "binary", "verbosity": -1, "random_state": 42, "subsample_freq": 1}
    m = LGBMClassifier(**best).fit(cv[cols], cv["y"])
    prob = m.predict_proba(ho[cols])[:, 1]
    pred = (prob >= 0.5).astype(int)
    y = ho["y"].values
    out = {"holdout_quarters": hold, "n": int(len(y)), "n_low": int((y == 0).sum()),
           "best_cv_weighted_f1": round(st.best_value, 4),
           "accuracy": round(float(accuracy_score(y, pred)), 4),
           "f1_weighted": round(float(f1_score(y, pred, average="weighted", zero_division=0)), 4),
           "roc_auc": round(float(roc_auc_score(y, prob)), 4),
           "confusion": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
           "always_high": round(float(y.mean()), 4),
           "persistence": round(float(accuracy_score(y, ho["last_label"].fillna(0).astype(int))), 4)}
    Path("data/supplementary/algorithm4_timing_valid.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
