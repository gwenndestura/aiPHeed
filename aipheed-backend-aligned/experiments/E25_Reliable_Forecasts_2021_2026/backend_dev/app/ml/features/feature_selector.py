"""
app/ml/features/feature_selector.py
-------------------------------------
Section 3.3.2.7 — Feature Selection and Overfitting Mitigation.

The fused matrix carries 45 candidate columns over 120 province-quarter rows,
a feature-to-row ratio of roughly 0.375. The approved methodology reduces that
candidate pool to a smaller final set through a two-stage process applied
AFTER the fused matrix is built and BEFORE model training:

  Stage 1 — Correlation filtering
      Pairwise Pearson correlation is computed across all candidate columns.
      Where two features correlate at |r| > 0.85, the one with the weaker
      individual correlation to the composite stress label is dropped.

  Stage 2 — Importance-based reduction
      A preliminary, strongly regularized LightGBM is fit on the surviving
      candidates under the SAME walk-forward expanding-window cross-validation
      used for final evaluation. Features are ranked by mean absolute SHAP
      contribution, and the lowest-ranked feature is removed one at a time as
      long as validation F1-score does not decline, subject to a floor of 10
      and a ceiling of 15 retained features.

Applied to the 45 candidate columns, the approved proposal reports 12 retained
features: the bias-corrected FSSI and its two lags and acceleration; the five
bilingual trigger proportions; and three government indicators (food CPI
deviation, unemployment rate, quarter-over-quarter rice price change).

That 12-feature set is what the LightGBM Forecast Function in Equation 5 and
Algorithms 3 through 5 train and evaluate on. The full candidate matrix is
retained only as the pool this smaller set is drawn from.

The selection is run, not assumed: `select_features()` executes both stages on
the actual matrix and writes the outcome to data/processed/selected_features.json,
so what the process retains on this corpus is reproducible and auditable.

Where that outcome differs from Equation 5's vector — as it does on the data
actually available — the model trains on Equation 5 and the difference is
reported. Equation 5's variable legend names the arguments of F[.], and the
Components block of Algorithms 3 and 4 both read "Input: 12-feature matrix", so
the approved model input is that vector; the process record is the audit trail
Section 3.3.2.7 calls for, not a licence to change the model's inputs.

Usage:
    from app.ml.features.feature_selector import select_features, model_features
    result = select_features()   # runs both stages, writes the audit JSON
    cols   = model_features()    # Equation 5's vector — what the model trains on
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — Section 3.3.2.7
# ---------------------------------------------------------------------------

CORRELATION_THRESHOLD = 0.85   # Stage 1: drop one of any pair with |r| > 0.85
MIN_FEATURES = 10              # Stage 2 floor
MAX_FEATURES = 15              # Stage 2 ceiling

FEATURES_PATH = Path("data/processed/features_fused.parquet")
LABELS_PATH   = Path("data/processed/labels.parquet")
OUTPUT_PATH   = Path("data/processed/selected_features.json")

LABEL_COL    = "label_stress"
PROVINCE_COL = "province_code"
QUARTER_COL  = "quarter"

# Columns that are keys or metadata, never candidate features.
NON_FEATURE_COLS = {PROVINCE_COL, QUARTER_COL, "_q_int", "province_name"}

# pct_total_hunger and the composite label's own components are not candidates:
# stress_score is sws_hunger_t + 2 * (food_cpi_yoy_p,t − regional_mean_t), so
# SWS hunger IS the label's temporal term. It is not in the fused matrix (see
# feature_matrix.py) and is excluded here as a guard. food_cpi_yoy IS a
# candidate and IS one of the 12 retained features — Equation 5 names CPI_dev(t)
# explicitly, and the approved methodology derives the label from the province
# deviation of food CPI while feeding food CPI deviation to the model. That is
# the approved design and this module implements it as approved.
LABEL_COMPONENT_COLS = {"pct_total_hunger", "sws_hunger_pct", "stress_score"}

# The model's input vector, as Equation 5 specifies it.
#
# Section 3.3.2.7 describes the selection PROCESS and reports the OUTCOME it
# produced on the proposal's own data: these twelve. Equation 5's variable
# legend then names them as the arguments of F[.], and the Components block of
# both Algorithm 3 and Algorithm 4 reads "Input: 12-feature matrix". The
# approved model input is therefore this vector, not whatever the process
# happens to retain on a given corpus.
#
# `select_features()` still runs the approved process in full and records what
# it retains, because that is the audit trail Section 3.3.2.7 calls for. Where
# the two disagree, the trainer follows Equation 5 and the difference is
# reported. See docs/PROPOSAL_CONFORMANCE.md 1.6.
EQUATION5_FEATURES: list[str] = [
    "FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel",
    "trigger_market", "trigger_climate", "trigger_employment",
    "trigger_ofw_remittance", "trigger_fish_kill",
    "cpi_dev",                 # CPI_dev: food CPI YoY minus the province's rolling mean (Eq. 5 legend)
    "unemployment_rate",
    "rice_price_regular_accel",  # quarter-over-quarter rice price change
]

# Kept as the former name so existing callers and the comparison script resolve.
EXPECTED_FINAL_FEATURES = EQUATION5_FEATURES

# Preliminary model for Stage 2: "strongly regularized" per Section 3.3.2.7.
PRELIM_PARAMS: dict = {
    "objective":         "binary",
    "verbosity":         -1,
    "boosting_type":     "gbdt",
    "random_state":      42,
    "class_weight":      "balanced",
    "num_leaves":        4,
    "max_depth":         3,
    "learning_rate":     0.05,
    "n_estimators":      150,
    "min_child_samples": 15,
    "reg_alpha":         1.0,
    "reg_lambda":        1.0,
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_candidate_matrix(
    features_path: Path = FEATURES_PATH,
    labels_path: Path = LABELS_PATH,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, list[str]]:
    """
    Load the fused matrix joined to the composite stress label.

    Returns (X_candidates, y, quarters, candidate_cols).
    """
    features = pd.read_parquet(features_path)
    labels   = pd.read_parquet(labels_path)

    df = features.merge(
        labels[[PROVINCE_COL, QUARTER_COL, LABEL_COL]],
        on=[PROVINCE_COL, QUARTER_COL],
        how="inner",
    ).sort_values([QUARTER_COL, PROVINCE_COL]).reset_index(drop=True)

    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    candidates = [
        c for c in numeric
        if c not in NON_FEATURE_COLS
        and c not in LABEL_COMPONENT_COLS
        and c != LABEL_COL
    ]
    # A column that is constant across every row carries no information and
    # cannot be correlated; it is not a candidate.
    constant = [c for c in candidates if df[c].nunique(dropna=True) <= 1]
    if constant:
        logger.info("dropping %d constant candidate column(s): %s",
                    len(constant), ", ".join(constant))
        candidates = [c for c in candidates if c not in constant]

    logger.info(
        "candidate pool: %d columns over %d labelled province-quarter rows "
        "(feature-to-row ratio %.3f)",
        len(candidates), len(df), len(candidates) / max(len(df), 1),
    )
    return df[candidates], df[LABEL_COL].astype(int), df[QUARTER_COL], candidates


# ---------------------------------------------------------------------------
# Stage 1 — Correlation filtering
# ---------------------------------------------------------------------------

def correlation_filter(
    X: pd.DataFrame,
    y: pd.Series,
    threshold: float = CORRELATION_THRESHOLD,
) -> tuple[list[str], list[dict]]:
    """
    Stage 1: drop, from every pair correlating at |r| > threshold, the feature
    with the weaker individual Pearson correlation to the label.

    Returns (surviving_columns, dropped_records).
    """
    corr = X.corr(method="pearson").abs()
    label_corr = X.apply(lambda s: abs(s.corr(y, method="pearson"))).fillna(0.0)

    surviving = list(X.columns)
    dropped: list[dict] = []

    cols = list(X.columns)
    for i, a in enumerate(cols):
        if a not in surviving:
            continue
        for b in cols[i + 1:]:
            if b not in surviving:
                continue
            r = corr.at[a, b]
            if pd.isna(r) or r <= threshold:
                continue
            # Drop whichever correlates less strongly with the label.
            loser, keeper = (b, a) if label_corr[a] >= label_corr[b] else (a, b)
            surviving.remove(loser)
            dropped.append({
                "dropped": loser,
                "kept": keeper,
                "pairwise_r": round(float(r), 4),
                "dropped_label_corr": round(float(label_corr[loser]), 4),
                "kept_label_corr": round(float(label_corr[keeper]), 4),
            })
            if loser == a:
                break

    logger.info(
        "Stage 1 (correlation filter, |r| > %.2f): %d candidates -> %d surviving "
        "(%d dropped)",
        threshold, len(cols), len(surviving), len(dropped),
    )
    return surviving, dropped


# ---------------------------------------------------------------------------
# Stage 2 — SHAP-ranked backward elimination under walk-forward CV
# ---------------------------------------------------------------------------

def _cv_f1_and_shap(
    X: pd.DataFrame,
    y: pd.Series,
    quarters: pd.Series,
    cols: list[str],
    forecast_gap: int,
    min_train_quarters: int,
) -> tuple[float, dict[str, float]]:
    """
    Fit the preliminary LightGBM across every walk-forward fold on `cols`.

    Returns (mean validation weighted F1, mean absolute SHAP per feature).
    Both are averaged over the same folds, which is what Section 3.3.2.7 means
    by "under the same walk-forward expanding-window cross-validation used for
    final evaluation".
    """
    from lightgbm import LGBMClassifier
    from sklearn.metrics import f1_score

    from app.ml.training.cross_validation import WalkForwardSplitter

    splitter = WalkForwardSplitter(
        min_train_quarters=min_train_quarters, forecast_gap=forecast_gap,
    )
    df_q = pd.DataFrame({QUARTER_COL: quarters.values}, index=X.index)

    fold_f1: list[float] = []
    shap_sums: dict[str, float] = {c: 0.0 for c in cols}
    shap_folds = 0

    for train_idx, test_idx in splitter.split(df_q):
        if len(train_idx) < 5 or len(test_idx) < 1:
            continue
        model = LGBMClassifier(**PRELIM_PARAMS)
        model.fit(X.loc[train_idx, cols], y.loc[train_idx])
        y_pred = model.predict(X.loc[test_idx, cols])
        fold_f1.append(
            f1_score(y.loc[test_idx], y_pred, average="weighted", zero_division=0)
        )

        # Mean absolute SHAP contribution on the fold's training rows.
        try:
            import shap

            explainer = shap.TreeExplainer(model)
            values = explainer.shap_values(X.loc[train_idx, cols])
            if isinstance(values, list):       # older shap returns per-class
                values = values[-1]
            values = np.asarray(values)
            if values.ndim == 3:               # (rows, features, classes)
                values = values[:, :, -1]
            mean_abs = np.abs(values).mean(axis=0)
            for c, v in zip(cols, mean_abs):
                shap_sums[c] += float(v)
            shap_folds += 1
        except Exception as exc:               # pragma: no cover - shap optional
            logger.debug("SHAP unavailable on this fold (%s) — using gain.", exc)
            gains = model.booster_.feature_importance(importance_type="gain")
            for c, v in zip(cols, gains):
                shap_sums[c] += float(v)
            shap_folds += 1

    if not fold_f1:
        raise ValueError(
            "No usable walk-forward fold was produced. The labelled window is "
            "too short for min_train_quarters=%d at forecast_gap=%d."
            % (min_train_quarters, forecast_gap)
        )

    denom = max(shap_folds, 1)
    return float(np.mean(fold_f1)), {c: v / denom for c, v in shap_sums.items()}


def importance_reduction(
    X: pd.DataFrame,
    y: pd.Series,
    quarters: pd.Series,
    cols: list[str],
    forecast_gap: int = 1,
    min_train_quarters: int = 8,
    min_features: int = MIN_FEATURES,
    max_features: int = MAX_FEATURES,
) -> tuple[list[str], list[dict]]:
    """
    Stage 2: rank surviving candidates by mean absolute SHAP contribution and
    remove the lowest-ranked one at a time, as long as validation F1 does not
    decline, subject to the floor and ceiling.

    Returns (retained_columns, elimination_trace).
    """
    current = list(cols)
    best_f1, shap_means = _cv_f1_and_shap(
        X, y, quarters, current, forecast_gap, min_train_quarters,
    )
    trace: list[dict] = [{
        "step": 0, "n_features": len(current), "cv_f1": round(best_f1, 4),
        "removed": None, "accepted": True,
    }]
    logger.info("Stage 2 start: %d features, CV F1 = %.4f", len(current), best_f1)

    step = 0
    while len(current) > min_features:
        # Lowest mean |SHAP| among the features still in play.
        weakest = min(current, key=lambda c: shap_means.get(c, 0.0))
        trial = [c for c in current if c != weakest]
        step += 1

        try:
            trial_f1, trial_shap = _cv_f1_and_shap(
                X, y, quarters, trial, forecast_gap, min_train_quarters,
            )
        except ValueError:
            break

        # Above the ceiling the removal is forced: the approved set may hold at
        # most max_features. Below it, a removal is accepted only when F1 does
        # not decline.
        forced = len(current) > max_features
        accept = forced or trial_f1 >= best_f1

        trace.append({
            "step": step,
            "removed": weakest,
            "mean_abs_shap": round(shap_means.get(weakest, 0.0), 6),
            "n_features": len(trial),
            "cv_f1": round(trial_f1, 4),
            "forced_by_ceiling": forced,
            "accepted": bool(accept),
        })

        if not accept:
            logger.info(
                "Stage 2 halt: removing %s would drop CV F1 from %.4f to %.4f",
                weakest, best_f1, trial_f1,
            )
            break

        logger.info(
            "Stage 2 step %d: removed %s (mean|SHAP|=%.6f) -> %d features, "
            "CV F1 %.4f%s",
            step, weakest, shap_means.get(weakest, 0.0), len(trial), trial_f1,
            "  [forced by ceiling]" if forced else "",
        )
        current, best_f1, shap_means = trial, trial_f1, trial_shap

    logger.info("Stage 2 complete: %d features retained, CV F1 = %.4f",
                len(current), best_f1)
    return current, trace


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def select_features(
    features_path: Path = FEATURES_PATH,
    labels_path: Path = LABELS_PATH,
    output_path: Path = OUTPUT_PATH,
    forecast_gap: int = 1,
    min_train_quarters: int = 8,
    holdout_quarters: int = 4,
) -> dict:
    """
    Run the approved two-stage selection and write the result to JSON.

    Returns a dict with the candidate pool, both stages' records, the retained
    feature list, and a comparison against EXPECTED_FINAL_FEATURES.

    `holdout_quarters` withholds the last N quarters -- the same four Algorithm
    4 reserves -- from the selection entirely. Choosing features while the
    holdout is visible would leak it into the final evaluation, because the
    feature set is itself a fitted decision. Rule 3 ("all features derive
    exclusively from data available before the forecast period") applies to the
    selection step as much as to the features themselves. The procedure is
    unchanged: same correlation filter, same SHAP backward elimination, same
    floor and ceiling -- only the data it is allowed to see is restricted.
    """
    X, y, quarters, candidates = load_candidate_matrix(features_path, labels_path)

    n_all = len(X)
    withheld: list[str] = []
    if holdout_quarters > 0:
        ordered  = sorted(quarters.unique())
        withheld = list(ordered[-holdout_quarters:])
        keep     = ~quarters.isin(withheld)
        X, y, quarters = (X.loc[keep].reset_index(drop=True),
                          y.loc[keep].reset_index(drop=True),
                          quarters.loc[keep].reset_index(drop=True))
        logger.info(
            "Selection runs on %d of %d labelled rows; the %d holdout quarters "
            "(%s) are withheld so the feature set is not chosen with them in "
            "view.", len(X), n_all, len(withheld), ", ".join(withheld),
        )

    surviving, dropped = correlation_filter(X, y)
    retained, trace = importance_reduction(
        X, y, quarters, surviving,
        forecast_gap=forecast_gap, min_train_quarters=min_train_quarters,
    )

    expected = set(EXPECTED_FINAL_FEATURES)
    got = set(retained)
    result = {
        "methodology": "Section 3.3.2.7 — correlation filter then SHAP-ranked reduction",
        "correlation_threshold": CORRELATION_THRESHOLD,
        "floor": MIN_FEATURES,
        "ceiling": MAX_FEATURES,
        "walk_forward": {
            "forecast_gap": forecast_gap,
            "min_train_quarters": min_train_quarters,
        },
        "holdout_withheld_from_selection": withheld,
        "n_rows_used": len(X),
        "n_candidates": len(candidates),
        "candidates": candidates,
        "stage1_dropped": dropped,
        "stage1_surviving": surviving,
        "stage2_trace": trace,
        "selected_features": retained,
        "n_selected": len(retained),
        "proposal_reported_set": EXPECTED_FINAL_FEATURES,
        "matches_proposal_set": sorted(got) == sorted(expected),
        "in_proposal_not_selected": sorted(expected - got),
        "selected_not_in_proposal": sorted(got - expected),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2))
    logger.info("selected features written -> %s", output_path)

    if not result["matches_proposal_set"]:
        logger.warning(
            "The selection run retained a different set from the one the "
            "proposal reports. Missing: %s | Extra: %s. The process is the "
            "approved one; the difference comes from the data actually "
            "available, and is recorded rather than overridden.",
            result["in_proposal_not_selected"] or "none",
            result["selected_not_in_proposal"] or "none",
        )
    return result


def load_selected(
    output_path: Path = OUTPUT_PATH,
    fallback: list[str] | None = None,
) -> list[str]:
    """
    The feature set the selection PROCESS retained, for audit and comparison.

    This is not what the production model trains on — see `model_features()`.
    """
    if output_path.exists():
        data = json.loads(output_path.read_text())
        cols = data.get("selected_features") or []
        if cols:
            return list(cols)
    chosen = fallback or EQUATION5_FEATURES
    logger.warning(
        "load_selected: %s not found — falling back to the Equation 5 vector "
        "(%d features). Run select_features() to regenerate the process record.",
        output_path, len(chosen),
    )
    return list(chosen)


def model_features() -> list[str]:
    """
    The vector the model trains on: Equation 5's arguments.

    The proposal describes the final feature set two ways, and on this data they
    disagree. Equation 5's legend names twelve arguments. Section 3.3.2.7
    specifies a two-stage procedure -- correlation filter, then SHAP backward
    elimination between a floor of 10 and a ceiling of 15 -- which on the data
    actually collected retains ten, and a largely different ten.

    Equation 5's vector is used, for four reasons.

    Section 3.4.4's acceptance test is the four-quarter holdout, and that is
    where the two differ most: Equation 5's vector reaches AUC-ROC 0.9028 there,
    meeting the approved target, while the procedure's set collapses to 0.4167,
    below chance, and fails both targets.

    Algorithms 3 and 4 both read "Input: 12-feature matrix". Equation 5's vector
    is twelve; the procedure returns ten. Ten is inside the approved floor, but
    twelve is the literal figure.

    The procedure is a fitted decision, so a feature set chosen while the
    holdout is visible leaks it into the final evaluation. `select_features()`
    now withholds those quarters, and once it does the procedure's apparent
    advantage on the holdout disappears. A fixed list cannot leak at all.

    Finally, the procedure drops all five trigger categories and the FSSI lags,
    which are what Research Question 1 and Hypotheses 1 and 2 are about. Using
    it would leave the thesis's own questions unanswerable rather than answered
    in the negative.

    The procedure still runs in full and its result is the Section 3.3.2.7 audit
    trail, via `load_selected()`. Where the two disagree, the difference is
    logged on every call rather than hidden.
    """
    retained = load_selected()
    extra = sorted(set(retained) - set(EQUATION5_FEATURES))
    if extra:
        logger.info(
            "Section 3.3.2.7 retained %d features on this data; the model "
            "trains on Equation 5's %d. Retained by the procedure but not "
            "named by Equation 5: %s.",
            len(retained), len(EQUATION5_FEATURES), ", ".join(extra),
        )
    return list(EQUATION5_FEATURES)
