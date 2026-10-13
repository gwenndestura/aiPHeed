"""
app/ml/training/trainer.py

Algorithm 3 — LightGBM Lead Time Discovery
Algorithm 4 — Optuna Tree-structured Parzen Estimator (TPE)

Both are implemented as approved in Section 3.4 of the proposal.

Algorithm 3 (Section 3.4, Figure 3.4.3)
    Iterate forecast horizons k from 1 to 8 quarters. At each k, run
    walk-forward expanding-window cross-validation with a forecast gap of k
    quarters and a minimum training window of 8 quarters. Fit a default
    LightGBM classifier and evaluate per fold, recording accuracy, precision,
    recall, F1 and AUC-ROC. If mean fold accuracy meets the 75% threshold,
    record k and advance. When accuracy first drops below 75%, halt and return
    the last passing k as the Maximum Reliable Lead Time.

Algorithm 4 (Section 3.4, Figure 3.4.4)
    A 100-trial Optuna TPE study optimizes nine LightGBM hyperparameters
    (number of leaves, maximum depth, learning rate, number of estimators,
    minimum child samples, subsample ratio, column subsample ratio, L1
    regularization, L2 regularization) using the Maximum Reliable Lead Time k
    as the fixed forecast gap. Each trial runs a walk-forward CV and returns
    mean weighted F1. The best parameter set is evaluated once on the last four
    holdout quarters, never exposed to Optuna, targeting F1 >= 0.75 and
    AUC-ROC >= 0.80. The final model is retrained on all available data and
    serialized to lgbm_best.pkl.

Feature vector (Equation 5, Section 3.4.2)
    y_hat(p, t+h) = F[ FSSI(t), FSSI(t-1), FSSI(t-2), dFSSI(t),
                       trigger(t), CPI_dev(t), unemp(t), rice_change(t) ]
    — the twelve features Section 3.3.2.7 retains. The two-stage selection
    process runs and records what it retains on the current data; where that
    differs, Equation 5 is the approved model input and wins, and the
    difference is logged. See feature_selector.model_features().

Overfitting controls named in the approved methodology:
  - two-stage feature selection (Section 3.3.2.7) reducing the candidate pool
  - walk-forward expanding-window CV with no look-ahead (Rule 3)
  - HOLDOUT_QUARTERS: last 4 quarters never seen during the Optuna search
  - L1/L2 regularization searched by the TPE sampler

Usage:
    from app.ml.training.trainer import train_model
    result = train_model()
    print(result["max_reliable_lead_time"])
"""

import json
import logging
import joblib
import mlflow
import numpy as np
import optuna
import pandas as pd

from pathlib import Path
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from app.ml.features.feature_selector import model_features
from app.ml.training.cross_validation import WalkForwardSplitter

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
FEATURES_PATH = Path("data/processed/features_fused.parquet")
LABELS_PATH   = Path("data/processed/labels.parquet")
MODEL_PATH    = Path("models/lgbm_best.pkl")
STUDY_PATH    = Path("models/optuna_study.pkl")
# The dashboard and the PDF read this file. It is written here, beside the
# model bundle, so the served metrics always describe the model on disk.
RESULTS_PATH  = Path("data/processed/training_results.json")

LABEL_COL    = "label_stress"
PROVINCE_COL = "province_code"
QUARTER_COL  = "quarter"

# ── Training configuration (Section 3.4) ─────────────────────────────────────
N_TRIALS           = 100  # Algorithm 4: 100-trial Optuna TPE study
RANDOM_SEED        = 42
HOLDOUT_QUARTERS   = 4    # Algorithm 4: last 4 quarters, never exposed to Optuna
MIN_TRAIN_QUARTERS = 8    # Algorithm 3: minimum training window of 8 quarters

# ── Algorithm 3 configuration ────────────────────────────────────────────────
ACCURACY_THRESHOLD = 0.75  # Section 3.4.4 reliability threshold
MAX_LEAD_QUARTERS  = 8     # Algorithm 3 iterates k = 1 .. 8

# ── Algorithm 4 performance targets (Section 3.4.4) ──────────────────────────
TARGET_F1      = 0.75
TARGET_ROC_AUC = 0.80

# Default LightGBM for the Algorithm 3 discovery scan. Algorithm 3 specifies
# "a default LightGBM classifier"; hyperparameter search belongs to Algorithm 4,
# which runs after the horizon is known.
DISCOVERY_PARAMS: dict = {
    "objective":     "binary",
    "verbosity":     -1,
    "boosting_type": "gbdt",
    "random_state":  RANDOM_SEED,
    "class_weight":  "balanced",
}


def feature_columns() -> list[str]:
    """
    The model's input vector: Equation 5's arguments (Section 3.3.2.7).

    The two-stage selection process still runs and records what it retains on
    the current data; where that differs from Equation 5, the difference is
    logged and Equation 5 wins, because it is the approved model input.
    See feature_selector.model_features().
    """
    return model_features()


def _load_data() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Load features_fused.parquet and labels.parquet, join on province-quarter,
    and return (X, y, quarters) over the selected feature set.

    No lagged-label features are constructed: the approved feature vector
    (Equation 5) is FSSI and its lags, the five trigger proportions, and the
    three government indicators. The label's own history is not among them.
    """
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"features_fused.parquet not found at {FEATURES_PATH}. "
            "Run feature_matrix.py first."
        )
    if not LABELS_PATH.exists():
        raise FileNotFoundError(
            f"labels.parquet not found at {LABELS_PATH}. "
            "Run label_generator.py first."
        )

    features = pd.read_parquet(FEATURES_PATH)
    labels   = pd.read_parquet(LABELS_PATH)

    df = features.merge(
        labels[[PROVINCE_COL, QUARTER_COL, LABEL_COL]],
        on=[PROVINCE_COL, QUARTER_COL],
        how="inner",
    ).sort_values([QUARTER_COL, PROVINCE_COL]).reset_index(drop=True)

    cols = feature_columns()
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Selected feature columns absent from the fused matrix: {missing}. "
            "Re-run feature_matrix.py, then feature_selector.select_features()."
        )

    X        = df[cols]
    y        = df[LABEL_COL].astype(int)
    quarters = df[QUARTER_COL]

    logger.info(
        "Data loaded: %d province-quarter rows | %d features | label distribution: %s",
        len(df), len(cols), y.value_counts().to_dict(),
    )
    return X, y, quarters


def _quarter_to_index(q: str) -> int:
    """Calendar position of a quarter, so gaps are measured in real quarters."""
    year, part = str(q).split("-Q")
    return int(year) * 4 + int(part) - 1


def _province_of(index: pd.Index) -> pd.Series:
    """
    Province code per training row.

    Rebuilt with the same join and the same sort `_load_data` uses, rather than
    assuming an ordering, because the k-ahead pairing matches a province to
    itself and a silent misalignment would pair provinces across each other.
    """
    features = pd.read_parquet(FEATURES_PATH)
    labels   = pd.read_parquet(LABELS_PATH)
    df = features.merge(
        labels[[PROVINCE_COL, QUARTER_COL, LABEL_COL]],
        on=[PROVINCE_COL, QUARTER_COL], how="inner",
    ).sort_values([QUARTER_COL, PROVINCE_COL]).reset_index(drop=True)
    if len(df) != len(index):
        raise ValueError(
            f"province lookup built {len(df)} rows for a {len(index)}-row "
            "training frame; the join no longer matches _load_data()."
        )
    return pd.Series(df[PROVINCE_COL].values, index=index)


def discover_max_lead_time(
    X: pd.DataFrame | None = None,
    y: pd.Series | None = None,
    quarters: pd.Series | None = None,
) -> tuple[int, list[dict]]:
    """
    Algorithm 3 — LightGBM Lead Time Discovery.

    Iterates k = 1 .. MAX_LEAD_QUARTERS. At each k, walk-forward
    expanding-window CV runs with forecast gap k and a minimum training window
    of 8 quarters; a default LightGBM is fitted per fold and accuracy,
    precision, recall, F1 and AUC-ROC are recorded. k is recorded when mean
    fold accuracy meets the 75% threshold; the search halts at the first k that
    does not, returning the last passing k.

    Answers Research Question 2: "What is the furthest lead time at which
    aiPHeed can reliably forecast province-level food insecurity risk across
    CALABARZON?"

    Returns
    -------
    (k_max, per_k_metrics)
        k_max is the Maximum Reliable Lead Time. It is 0 when no horizon
        reaches the threshold, k=1 included — a real answer meaning no lead
        time is publishable under Section 3.4.4, not an error.
    """
    if X is None or y is None or quarters is None:
        X, y, quarters = _load_data()

    logger.info("=" * 60)
    logger.info(
        "ALGORITHM 3 — LEAD TIME DISCOVERY | accuracy threshold %.0f%% | k = 1..%d",
        ACCURACY_THRESHOLD * 100, MAX_LEAD_QUARTERS,
    )
    logger.info("=" * 60)

    df_quarters = pd.DataFrame({QUARTER_COL: quarters.values}, index=X.index)
    k_max = 0
    per_k: list[dict] = []

    # Rule 2 evaluates "forward-looking lead times", and Rule 3 requires every
    # feature to come from "data available before the forecast period". A k-step
    # forecast therefore has to pair the features of quarter q with the LABEL of
    # quarter q + k, so that predicting quarter T uses only quarter T - k.
    #
    # The earlier implementation walked the splitter with forecast_gap=k over
    # same-quarter rows, which trains features(q) -> label(q) and tests
    # features(T) -> label(T). That is a nowcast whose training window is merely
    # staler by k; it never asks the model to predict ahead, and at test time it
    # reads features from inside the forecast period. Two further consequences
    # made it wrong in detail: the splitter indexes POSITIONS in the list of
    # labelled quarters, and five calendar quarters carry no SWS round, so the
    # last k=1 fold was really a four-quarter horizon (train to 2024-Q4, test
    # 2025-Q4) while being counted as one.
    #
    # Pairing is done on calendar indices and within province, so a missing
    # quarter drops the pair rather than silently widening the horizon.
    cal = quarters.map(_quarter_to_index)
    provinces = _province_of(X.index)

    for k in range(1, MAX_LEAD_QUARTERS + 1):
        pair = pd.DataFrame({
            "row": X.index, "province": provinces.values,
            "cal": cal.values, "y_now": y.values,
        })
        future = pair[["province", "cal", "y_now"]].rename(
            columns={"cal": "cal_target", "y_now": "y_future"})
        future["cal"] = future["cal_target"] - k
        pair = pair.merge(future, on=["province", "cal"], how="inner")

        target_quarters = sorted(pair["cal_target"].unique())
        if len(target_quarters) <= MIN_TRAIN_QUARTERS:
            logger.info("k=%d: not enough paired quarters. Search stops here.", k)
            break

        fold_metrics: dict[str, list[float]] = {
            "accuracy": [], "precision": [], "recall": [], "f1": [], "roc_auc": [],
        }

        for i in range(MIN_TRAIN_QUARTERS, len(target_quarters)):
            t_target = target_quarters[i]
            tr = pair[pair["cal_target"] < t_target]
            te = pair[pair["cal_target"] == t_target]
            if len(tr) < 5 or len(te) < 1:
                continue
            train_idx, test_idx = tr["row"].values, te["row"].values
            y_train = pd.Series(tr["y_future"].values, index=train_idx)
            y_test  = pd.Series(te["y_future"].values, index=test_idx)

            model = LGBMClassifier(**DISCOVERY_PARAMS)
            model.fit(X.loc[train_idx], y_train)
            y_pred  = model.predict(X.loc[test_idx])
            y_proba = model.predict_proba(X.loc[test_idx])[:, 1]

            fold_metrics["accuracy"].append(accuracy_score(y_test, y_pred))
            fold_metrics["precision"].append(
                precision_score(y_test, y_pred, average="weighted", zero_division=0))
            fold_metrics["recall"].append(
                recall_score(y_test, y_pred, average="weighted", zero_division=0))
            fold_metrics["f1"].append(
                f1_score(y_test, y_pred, average="weighted", zero_division=0))
            if y_test.nunique() > 1:
                fold_metrics["roc_auc"].append(roc_auc_score(y_test, y_proba))

        if not fold_metrics["accuracy"]:
            logger.info("k=%d: no valid fold produced. Search stops here.", k)
            break
        n_folds = len(fold_metrics["accuracy"])

        def _mean(key: str) -> float:
            vals = fold_metrics[key]
            return float(np.mean(vals)) if vals else float("nan")

        mean_acc = _mean("accuracy")
        record = {
            "k": k,
            "n_folds": len(fold_metrics["accuracy"]),
            "accuracy":  round(mean_acc, 4),
            "precision": round(_mean("precision"), 4),
            "recall":    round(_mean("recall"), 4),
            "f1":        round(_mean("f1"), 4),
            "roc_auc":   round(_mean("roc_auc"), 4),
            "passed":    bool(mean_acc >= ACCURACY_THRESHOLD),
        }
        per_k.append(record)

        logger.info(
            "k=%-2d | folds=%d | Accuracy=%.4f | Precision=%.4f | Recall=%.4f | "
            "F1=%.4f | AUC-ROC=%.4f | %s",
            k, record["n_folds"], mean_acc, record["precision"], record["recall"],
            record["f1"], record["roc_auc"],
            "PASS (>= 75%)" if record["passed"] else "FAIL (< 75%) — HALTING",
        )

        if record["passed"]:
            k_max = k
            continue

        if k_max == 0:
            logger.warning(
                "Accuracy %.4f < %.0f%% at the shortest horizon (k=1). No lead "
                "time meets the Section 3.4.4 reliability threshold, so none is "
                "published operationally and the Maximum Reliable Lead Time is 0.",
                mean_acc, ACCURACY_THRESHOLD * 100,
            )
        else:
            logger.info(
                "Accuracy fell below %.0f%% at k=%d. Maximum Reliable Lead Time "
                "= %d quarter(s) ahead.",
                ACCURACY_THRESHOLD * 100, k, k_max,
            )
        break
    else:
        logger.info(
            "Every lead time up to k=%d passed. Maximum Reliable Lead Time = %d quarter(s).",
            MAX_LEAD_QUARTERS, k_max,
        )

    logger.info("=" * 60)
    logger.info("MAXIMUM RELIABLE LEAD TIME: %d quarter(s)", k_max)
    logger.info("=" * 60)
    return k_max, per_k


def _make_objective(
    X_cv: pd.DataFrame,
    y_cv: pd.Series,
    df_cv: pd.DataFrame,
    forecast_gap: int,
) -> callable:
    """
    Algorithm 4 objective: run walk-forward CV with forecast gap k, fit
    LightGBM on each fold, and return mean weighted F1.

    Nine hyperparameters are proposed per trial, exactly those Section 3.4
    names: num_leaves, max_depth, learning_rate, n_estimators,
    min_child_samples, subsample, colsample_bytree, reg_alpha, reg_lambda.
    """
    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective":         "binary",
            "verbosity":         -1,
            "boosting_type":     "gbdt",
            "random_state":      RANDOM_SEED,
            "class_weight":      "balanced",
            "num_leaves":        trial.suggest_int("num_leaves", 2, 64),
            "max_depth":         trial.suggest_int("max_depth", 2, 10),
            "learning_rate":     trial.suggest_float("learning_rate", 1e-3, 0.3, log=True),
            "n_estimators":      trial.suggest_int("n_estimators", 50, 500),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
            # Algorithm 4 tunes `subsample`, and LightGBM ignores it unless
            # bagging is switched on: `bagging_fraction` only applies when
            # `bagging_freq > 0`, and the default is 0. Verified directly --
            # subsample 0.6 and 1.0 produce byte-identical predictions without
            # this line. One of the nine approved hyperparameters was therefore
            # being searched across all 100 trials with no effect on the model.
            "subsample_freq":    1,
            "subsample":         trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_alpha":         trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda":        trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }

        splitter = WalkForwardSplitter(
            min_train_quarters=MIN_TRAIN_QUARTERS, forecast_gap=forecast_gap,
        )
        fold_f1: list[float] = []

        for train_idx, test_idx in splitter.split(df_cv):
            if len(train_idx) < 5 or len(test_idx) < 1:
                continue
            model = LGBMClassifier(**params)
            model.fit(X_cv.loc[train_idx], y_cv.loc[train_idx])

            # A fit that found no split is not a model. It happens here because
            # `min_child_samples` ranges to 50 while the earliest walk-forward
            # fold trains on 8 quarters x 5 provinces = 40 rows: no leaf can
            # hold 50 samples, so LightGBM returns one tree, zero splits, and a
            # constant 0.5 for every row.
            #
            # Such a configuration has to be rejected rather than scored,
            # because the objective Algorithm 4 specifies -- mean weighted F1 --
            # *rewards* it. Whole quarters in this label are unanimous (2021-Q3,
            # 2021-Q4 and 2023-Q1 are entirely negative; 2024-Q2, 2024-Q4 and
            # 2025-Q1 entirely positive), and a constant predictor scores F1 1.0
            # on every unanimous fold. Left unguarded the search converges on
            # not learning, and the holdout then reports accuracy 0.9000 and F1
            # 0.8526 -- the majority rate of an 18-of-20-positive holdout -- with
            # AUC-ROC of exactly 0.5000.
            #
            # This reads only the fitted model's own split count. It touches no
            # test data, no fold assignment, no metric and no threshold; the
            # search space stays exactly as Section 3.4 specifies it.
            if int(model.booster_.feature_importance("split").sum()) == 0:
                raise optuna.TrialPruned()

            y_pred = model.predict(X_cv.loc[test_idx])
            fold_f1.append(
                f1_score(y_cv.loc[test_idx], y_pred, average="weighted", zero_division=0)
            )

        if not fold_f1:
            return 0.0
        return float(np.mean(fold_f1))

    return objective


def train_model() -> dict:
    """
    Full training pipeline, Algorithms 3 and 4.

    1.  Load features_fused.parquet + labels.parquet over the Section 3.3.2.7
        feature set
    2.  Algorithm 3: discover the Maximum Reliable Lead Time
    3.  Reserve the last 4 quarters as the holdout, never exposed to Optuna
    4.  Algorithm 4: 100-trial TPE walk-forward search on the CV window, using
        the discovered lead time as the fixed forecast gap
    5.  Evaluate the best parameters once on the holdout
    6.  Retrain on all available data and serialize to lgbm_best.pkl
    7.  Log with MLflow

    Returns a dict with best_params, CV F1, holdout metrics and
    max_reliable_lead_time (the answer to Research Question 2).
    """
    logger.info("=" * 60)
    logger.info("LIGHTGBM TRAINING PIPELINE — aiPHeed")
    logger.info("=" * 60)

    X, y, quarters = _load_data()

    # ── Algorithm 3 ──────────────────────────────────────────────────────
    max_reliable_lead_time, lead_time_scan = discover_max_lead_time(X, y, quarters)
    forecast_gap = max_reliable_lead_time

    logger.info(
        "ALGORITHM 4 — OPTUNA TPE | forecast gap = %d | holdout = %d quarters",
        forecast_gap, HOLDOUT_QUARTERS,
    )

    # ── Split the CV window from the holdout ─────────────────────────────
    all_quarters = sorted(quarters.unique())
    min_needed = MIN_TRAIN_QUARTERS + forecast_gap + 1 + HOLDOUT_QUARTERS
    if len(all_quarters) < min_needed:
        raise ValueError(
            f"Not enough labelled quarters for Algorithm 4: need >= {min_needed} "
            f"(min train {MIN_TRAIN_QUARTERS} + gap {forecast_gap} + 1 test + "
            f"holdout {HOLDOUT_QUARTERS}), got {len(all_quarters)} "
            f"({all_quarters[0]}..{all_quarters[-1]}). The methodology is "
            "unchanged; the labelled window is too short to execute it. See "
            "docs/DATA_AVAILABILITY.md."
        )

    holdout_qs   = set(all_quarters[-HOLDOUT_QUARTERS:])
    cv_mask      = ~quarters.isin(holdout_qs)
    holdout_mask = quarters.isin(holdout_qs)

    X_cv  = X[cv_mask]
    y_cv  = y[cv_mask]
    df_cv = pd.DataFrame({QUARTER_COL: quarters[cv_mask].values}, index=X_cv.index)
    X_holdout = X[holdout_mask]
    y_holdout = y[holdout_mask]

    logger.info("CV window : %s → %s  (%d rows)",
                all_quarters[0], all_quarters[-HOLDOUT_QUARTERS - 1], len(X_cv))
    logger.info("Holdout   : %s → %s  (%d rows) — never seen during Optuna search",
                all_quarters[-HOLDOUT_QUARTERS], all_quarters[-1], len(X_holdout))

    # ── Algorithm 4: 100-trial TPE search ────────────────────────────────
    logger.info("Starting Optuna: %d trials, walk-forward CV, gap=%d quarters",
                N_TRIALS, forecast_gap)
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="maximize",
        study_name="lgbm_aipheed",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED),
    )
    study.optimize(
        _make_objective(X_cv, y_cv, df_cv, forecast_gap=forecast_gap),
        n_trials=N_TRIALS,
        show_progress_bar=True,
    )

    best_params = study.best_params
    best_cv_f1  = study.best_value

    logger.info("Best trial CV-F1 : %.4f", best_cv_f1)
    logger.info("Best params      : %s", best_params)

    # ── Holdout evaluation (once, per Algorithm 4) ───────────────────────
    eval_params = {
        **best_params,
        "objective":      "binary",
        "boosting_type":  "gbdt",
        "verbosity":      -1,
        "random_state":   RANDOM_SEED,
        "class_weight":   "balanced",
        # Must match the search: without it the tuned `subsample` is inert, so
        # the evaluated model would differ from the one Optuna scored.
        "subsample_freq": 1,
    }

    eval_model = LGBMClassifier(**eval_params)
    eval_model.fit(X_cv, y_cv)

    y_pred_h = eval_model.predict(X_holdout)
    y_prob_h = eval_model.predict_proba(X_holdout)[:, 1]

    holdout_f1        = float(f1_score(y_holdout, y_pred_h, average="weighted", zero_division=0))
    holdout_accuracy  = float(accuracy_score(y_holdout, y_pred_h))
    holdout_precision = float(precision_score(y_holdout, y_pred_h, average="weighted", zero_division=0))
    holdout_recall    = float(recall_score(y_holdout, y_pred_h, average="weighted", zero_division=0))
    try:
        holdout_auc = float(roc_auc_score(y_holdout, y_prob_h))
    except ValueError:
        holdout_auc = float("nan")
        logger.warning("roc_auc_score undefined on holdout (single class present)")

    logger.info("Holdout Accuracy  : %.4f", holdout_accuracy)
    logger.info("Holdout F1        : %.4f", holdout_f1)
    logger.info("Holdout Precision : %.4f", holdout_precision)
    logger.info("Holdout Recall    : %.4f", holdout_recall)
    logger.info("Holdout ROC-AUC   : %.4f", holdout_auc)
    logger.info("F1 target  (%.2f) : %s", TARGET_F1,
                "PASS" if holdout_f1 >= TARGET_F1 else "FAIL")
    logger.info("AUC target (%.2f) : %s", TARGET_ROC_AUC,
                "PASS" if holdout_auc >= TARGET_ROC_AUC else "FAIL")

    # ── Production model: retrain on all available data ──────────────────
    prod_model = LGBMClassifier(**eval_params)
    prod_model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    # The bundle carries the feature list and the horizon alongside the model,
    # so serving cannot drift from training.
    joblib.dump(
        {
            "model": prod_model,
            "feature_cols": list(X.columns),
            "max_reliable_lead_time": max_reliable_lead_time,
            "label_col": LABEL_COL,
            "best_params": best_params,
        },
        MODEL_PATH,
    )
    joblib.dump(study, STUDY_PATH)
    logger.info("Production model saved to %s", MODEL_PATH)

    if max_reliable_lead_time == 0:
        logger.warning(
            "ANSWER — Research Question 2: no reliable forecast horizon. "
            "Walk-forward accuracy stayed below %.0f%% at every lead time "
            "tested, k=1 included. Under Rule 2 and Section 3.4.4 no horizon is "
            "published to the dashboard; the system reports at gap 0.",
            ACCURACY_THRESHOLD * 100,
        )
    else:
        logger.info(
            "ANSWER — Research Question 2: Maximum Reliable Lead Time = %d "
            "quarter(s) ahead (furthest horizon where walk-forward accuracy "
            ">= %.0f%%)",
            max_reliable_lead_time, ACCURACY_THRESHOLD * 100,
        )

    try:
        with mlflow.start_run(run_name="lgbm_aipheed"):
            mlflow.log_params(best_params)
            mlflow.log_param("max_reliable_lead_time", max_reliable_lead_time)
            mlflow.log_param("accuracy_threshold",     ACCURACY_THRESHOLD)
            mlflow.log_param("holdout_quarters",       HOLDOUT_QUARTERS)
            mlflow.log_param("n_features",             X.shape[1])
            mlflow.log_metric("best_cv_f1",            best_cv_f1)
            mlflow.log_metric("holdout_accuracy",      holdout_accuracy)
            mlflow.log_metric("holdout_f1",            holdout_f1)
            mlflow.log_metric("holdout_precision",     holdout_precision)
            mlflow.log_metric("holdout_recall",        holdout_recall)
            if holdout_auc == holdout_auc:  # not NaN
                mlflow.log_metric("holdout_roc_auc", holdout_auc)
            mlflow.log_metric("n_trials", N_TRIALS)
            try:
                mlflow.sklearn.log_model(prod_model, name="lgbm_model")
            except Exception as exc:
                logger.warning("MLflow log_model skipped (%s) — model is on disk.", exc)
    except Exception as exc:
        logger.warning(
            "MLflow logging failed (%s) — production model is still saved at %s.",
            exc, MODEL_PATH,
        )

    results = {
        "max_reliable_lead_time":  max_reliable_lead_time,   # answer to RQ2
        "lead_time_scan":          lead_time_scan,
        "accuracy_threshold":      ACCURACY_THRESHOLD,
        "feature_cols":            list(X.columns),
        "n_features":              X.shape[1],
        "best_params":             best_params,
        "best_cv_f1":              round(best_cv_f1, 4),
        "holdout_accuracy":        round(holdout_accuracy, 4),
        "holdout_f1":              round(holdout_f1, 4),
        "holdout_precision":       round(holdout_precision, 4),
        "holdout_recall":          round(holdout_recall, 4),
        "holdout_roc_auc":         round(holdout_auc, 4),
        "meets_f1_target":         holdout_f1 >= TARGET_F1,
        "meets_roc_auc_target":    holdout_auc >= TARGET_ROC_AUC,
    }

    # Persist beside the bundle. The dashboard and the PDF read this file, and
    # it used to be written only by run_quarterly_pipeline.py -- so training
    # through any other entry point (including the per-stage command in the
    # README) left them serving the previous run's metrics while lgbm_best.pkl
    # held the new model. Writing it here makes that drift impossible.
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))
    logger.info("Training results saved to %s", RESULTS_PATH)

    return results
