"""
scripts/supplementary/optimize_model_b.py

Nested walk-forward optimization of MODEL-B (Algorithm 3, LightGBM, one quarter
ahead, strict Rule 3 timing). Experiment only; nothing is served.

Protocol (frozen)
  * Data: timing-valid frame (algorithm4_timing_valid.frame_t2): 45 Section
    3.3.2.6 candidates + CPI_dev + SWS hunger as released before the forecast
    quarter; government series of t-1; news of t; poverty as published.
  * Outer evaluation: features of t -> label of t+1, expanding window, minimum 8
    target quarters, 11 test quarters (55 rows), cut-off 0.50 unless a variant
    chooses its own threshold inside training.
  * Every choice (hyperparameters, threshold, feature subset, class weighting)
    is made INSIDE each outer fold from that fold's training quarters only, by
    an inner walk-forward (minimum 5 target quarters). The outer test quarter
    never influences a choice.
  * LightGBM only; Optuna TPE with seed 42 for searches; one seed, no seed
    selection.

Pre-registered rule for a reliable improvement over the baseline:
  mean fold accuracy >= baseline + 0.018 (one test row), no year lower by more
  than 0.10, and ROC-AUC no lower than baseline - 0.02.

Writes evidence/2026-10-08_optimization/.

    python -m scripts.supplementary.optimize_model_b
"""

from __future__ import annotations

import hashlib
import json
import time
import warnings
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.reliability_diagnostics as R

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

OUT = Path("evidence/2026-10-08_optimization")
SEED = 42
OUTER_MIN = 8
INNER_MIN = 5
N_TRIALS = 50
THRESHOLDS = np.round(np.arange(0.20, 0.81, 0.05), 2)
K_GRID = [10, 15, 20, 30, None]          # None = all features
BASE = {"objective": "binary", "verbosity": -1, "random_state": SEED}


# ---------------------------------------------------------------- helpers
def quarters(d):
    return sorted(d["target_quarter"].unique(), key=R.qi)


def inner_splits(train, min_train=INNER_MIN):
    tq = quarters(train)
    for i in range(min_train, len(tq)):
        tr = train[train["target_quarter"].map(R.qi) < R.qi(tq[i])]
        te = train[train["target_quarter"] == tq[i]]
        if tr["y"].nunique() == 2:
            yield tr, te


def fit(params, X, y):
    return LGBMClassifier(**{**BASE, **params}).fit(X, y)


def inner_oof(train, cols, params):
    """Out-of-fold probabilities of the inner walk-forward (training data only)."""
    parts = []
    for tr, te in inner_splits(train):
        m = fit(params, tr[cols], tr["y"])
        parts.append(pd.DataFrame({"q": te["target_quarter"].values, "y": te["y"].values,
                                   "p": m.predict_proba(te[cols])[:, 1]}))
    return pd.concat(parts) if parts else pd.DataFrame(columns=["q", "y", "p"])


def mean_fold_acc(oof, thr=0.5):
    if oof.empty:
        return 0.0
    return float(oof.assign(c=((oof["p"] >= thr).astype(int) == oof["y"]).astype(float))
                 .groupby("q")["c"].mean().mean())


def search_space(trial, with_cw=False):
    p = {
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        "num_leaves": trial.suggest_int("num_leaves", 2, 64),
        "max_depth": trial.suggest_int("max_depth", 2, 10),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 30),
        "subsample_freq": 1,
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "min_split_gain": trial.suggest_float("min_split_gain", 0.0, 1.0),
    }
    if with_cw:
        cw = trial.suggest_categorical("class_weight", ["none", "balanced"])
        if cw == "balanced":
            p["class_weight"] = "balanced"
    return p


def tune(train, cols, with_cw=False, fixed=None):
    def objective(trial):
        params = {**search_space(trial, with_cw), **(fixed or {})}
        oof = inner_oof(train, cols, params)
        return mean_fold_acc(oof)
    st = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=SEED))
    st.optimize(objective, n_trials=N_TRIALS)
    best = dict(st.best_params)
    if best.pop("class_weight", "none") == "balanced":
        best["class_weight"] = "balanced"
    best["subsample_freq"] = 1
    return {**best, **(fixed or {})}, st.best_value


def pick_threshold(oof):
    scores = {t: mean_fold_acc(oof, t) for t in THRESHOLDS}
    top = max(scores.values())
    return float(min((t for t, s in scores.items() if s == top), key=lambda t: abs(t - 0.5)))


def topk(train, cols, k):
    if k is None or k >= len(cols):
        return list(cols)
    m = fit({}, train[cols], train["y"])
    imp = pd.Series(m.booster_.feature_importance("gain"), index=cols)
    return list(imp.sort_values(ascending=False).index[:k])


def pick_k(train, cols):
    best_k, best_s = None, -1
    for k in K_GRID:
        parts = []
        for tr, te in inner_splits(train):
            sel = topk(tr, cols, k)
            m = fit({}, tr[sel], tr["y"])
            parts.append(pd.DataFrame({"q": te["target_quarter"].values, "y": te["y"].values,
                                       "p": m.predict_proba(te[sel])[:, 1]}))
        s = mean_fold_acc(pd.concat(parts))
        if s > best_s + 1e-12:
            best_k, best_s = k, s
    return best_k, best_s


# ------------------------------------------------------------ experiments
def run_variant(name, d, cols):
    tq = quarters(d)
    rows, choices, importances = [], [], []
    for i in range(OUTER_MIN, len(tq)):
        train = d[d["target_quarter"].map(R.qi) < R.qi(tq[i])]
        test = d[d["target_quarter"] == tq[i]]
        params, thr, sel, note = {}, 0.5, list(cols), {}
        if name == "E0_baseline_default":
            pass
        elif name == "E1_class_weight_balanced":
            params = {"class_weight": "balanced"}
        elif name == "E2_scale_pos_weight_ratio":
            pos = train["y"].mean()
            params = {"scale_pos_weight": float((1 - pos) / pos)}
            note["scale_pos_weight"] = round(params["scale_pos_weight"], 3)
        elif name == "E3_threshold_inner":
            thr = pick_threshold(inner_oof(train, cols, {}))
        elif name == "E4_featuresel_inner":
            k, s = pick_k(train, cols)
            sel = topk(train, cols, k)
            note["k"] = k or len(cols)
        elif name == "E5_tpe_tuned":
            params, s = tune(train, cols)
            note["inner_acc"] = round(s, 4)
        elif name == "E6_tpe_tuned_with_classweight_choice":
            params, s = tune(train, cols, with_cw=True)
            note["inner_acc"] = round(s, 4)
        elif name == "E7_tpe_tuned_plus_threshold":
            params, s = tune(train, cols)
            thr = pick_threshold(inner_oof(train, cols, params))
            note["inner_acc"] = round(s, 4)
        m = fit(params, train[sel], train["y"])
        p = m.predict_proba(test[sel])[:, 1]
        rows.append(pd.DataFrame({"variant": name, "target_quarter": tq[i],
                                  "province_code": test["province_code"].values,
                                  "y": test["y"].values, "p": p,
                                  "pred": (p >= thr).astype(int), "threshold": thr,
                                  "last_label": test["last_label"].values}))
        imp = pd.Series(m.booster_.feature_importance("gain"), index=sel)
        importances.append((imp / imp.sum()).rename(tq[i]))
        choices.append({"test_quarter": tq[i], "threshold": thr, "n_features": len(sel),
                        "params": params, **note})
    preds = pd.concat(rows, ignore_index=True)
    imp = pd.concat(importances, axis=1).fillna(0.0).mean(axis=1).sort_values(ascending=False)
    return preds, choices, imp


def summarise(preds):
    m = R.metrics(preds["y"], preds["pred"], preds["p"].values, preds["target_quarter"].values)
    return {k: m[k] for k in ("accuracy_mean_fold", "precision_weighted", "recall_weighted",
                              "f1_weighted", "precision_high", "recall_high", "roc_auc",
                              "confusion_matrix_[[TN,FP],[FN,TP]]", "accuracy_by_year",
                              "accuracy_by_fold")}


def reliable(c, b):
    worse_year = max(b["accuracy_by_year"][y] - c["accuracy_by_year"][y] for y in b["accuracy_by_year"])
    return bool(c["accuracy_mean_fold"] >= b["accuracy_mean_fold"] + 0.018
                and worse_year <= 0.10 + 1e-9
                and (c["roc_auc"] or 0) >= (b["roc_auc"] or 0) - 0.02)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f, labels, cols = A.frame_t2()
    d = R.pairs(f, labels, 1)
    variants = ["E0_baseline_default", "E1_class_weight_balanced", "E2_scale_pos_weight_ratio",
                "E3_threshold_inner", "E4_featuresel_inner", "E5_tpe_tuned",
                "E6_tpe_tuned_with_classweight_choice", "E7_tpe_tuned_plus_threshold"]
    log, all_preds, imps, base = [], [], {}, None
    for v in variants:
        t0 = time.time()
        preds, choices, imp = run_variant(v, d, cols)
        s = summarise(preds)
        if v == "E0_baseline_default":
            base = s
        entry = {"variant": v, "seconds": round(time.time() - t0, 1), "metrics": s,
                 "reliable_improvement": None if base is s else reliable(s, base),
                 "per_fold_choices": choices}
        log.append(entry)
        all_preds.append(preds)
        imps[v] = imp
        print(f"{v:42s} acc={s['accuracy_mean_fold']:.4f} f1={s['f1_weighted']:.4f} "
              f"auc={s['roc_auc']} years={s['accuracy_by_year']} "
              f"reliable={entry['reliable_improvement']} ({entry['seconds']}s)", flush=True)

    pd.concat(all_preds).to_csv(OUT / "predictions_all_variants.csv", index=False)
    pd.DataFrame(imps).to_csv(OUT / "feature_importance_by_variant.csv")
    src = Path(__file__).read_bytes()
    meta = {"script_sha256": hashlib.sha256(src).hexdigest(), "seed": SEED, "outer_min": OUTER_MIN,
            "inner_min": INNER_MIN, "n_trials": N_TRIALS, "features": cols,
            "n_outer_test_rows": int(len(all_preds[0])),
            "rule": "reliable = acc >= base+0.018 AND no year worse by >0.10 AND AUC >= base-0.02"}
    (OUT / "experiment_log.json").write_text(json.dumps({"meta": meta, "experiments": log},
                                                         indent=2, default=str))
    return log


if __name__ == "__main__":
    main()
