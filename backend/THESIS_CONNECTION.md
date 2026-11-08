# backend_thesis — connected to the paper

This is a full copy of `backend/`, kept completely separate so the live app
in `backend/` is untouched. Inside this copy, the main forecast pipeline has
been rewired to actually run on the paper's own methodology (Chapter III),
instead of the production-shortfall model the live app evolved into.

## What is connected

- **Label**: `label_cpi`, the paper's own CPI-only robustness label
  (Equation 4) — not the composite SWS+CPI label (Equation 3), which only
  has 30 real data rows and cannot train anything. `label_cpi` has full
  real coverage: 120/120 province-quarters, the paper's exact
  2020-Q1..2025-Q4 window.
- **Features**: exactly the paper's 12 features (Equation 5) — FSSI + 3
  derived, 5 news triggers, CPI deviation, unemployment, rice price change.
- **Model**: a single LightGBM classifier (not the 4-model ensemble the live
  app uses), tuned with Optuna TPE (100 trials), per Algorithm 4.
- **Evaluation**: a real, blind 4-quarter holdout (2025-Q1..2025-Q4), never
  shown to Optuna during tuning — Algorithm 4 as literally specified.
- **Serving**: `app/ml/inference/thesis_predictor.py` scores every province
  directly from this model. `app/services/dashboard.py`'s default
  ("nowcast") horizon now calls it — verified end to end: available
  quarters, province summary, region roll-up, and municipal disaggregation
  all return real numbers from the paper's model, not the old commodity
  model.

Files: `scripts/build_thesis_panel.py` → `scripts/train_thesis_model.py` →
`app/ml/inference/thesis_predictor.py`, wired into `_engine()` in
`app/services/dashboard.py`.

## What is NOT connected (left on the original logic)

- **SHAP / Risk Drivers panel** (`app/ml/inference/explainer.py`) still
  explains the old commodity-level model. Rewiring SHAP for a single
  province-level LightGBM model is a smaller, different job (no per-group
  ensemble to sum over) and was not done in this pass.
- **"One-quarter-ahead" forecast horizon** (`app/ml/inference/forecaster.py`)
  is a distinct, separately-trained, t-1-lagged architecture the paper does
  not describe. Left on the original Forecaster.
- **Admin / training-data-review screens** and anything else that reads
  `data/processed/food_availability_panel.parquet` or the old model bundle
  directly is unaffected — only the dashboard's default forecast path was
  rewired.

## The honest result — read before presenting this

Connecting the dashboard to the paper's method does not make the paper's
method work well. A real, blind holdout test (never shown to the tuner)
gives:

| Metric | Value |
|---|---|
| Accuracy | 90.0% |
| Precision | 90.0% |
| Recall | 100% |
| F1 | 94.7% |
| AUC | **0.625** |

The accuracy/F1 numbers look strong, but the holdout quarters are 90%
positive (18 of 20 rows), and the model predicted positive for **all 20**
— identical to a trivial "always guess the majority class" baseline. AUC
(which measures real ranking ability, independent of that imbalance) is
0.625, barely above chance (0.50) and well under the paper's own 0.80
target. This is recorded, not hidden, in the model bundle itself
(`holdout_metrics`, `trivial_baseline_check`, `meets_thesis_targets` keys)
and surfaced on every prediction via the `thesis_note` field.

**Bottom line**: the dashboard is now genuinely running the paper's
formula, features, model type, and evaluation procedure — but the paper's
own procedure, run honestly on the real data that exists, does not produce
a model that reliably distinguishes risk from non-risk. That is a finding
about the data (SWS survey data volume, and the fact that the fallback
label mostly just tracks a real inflation trend), not a bug in this
connection.
