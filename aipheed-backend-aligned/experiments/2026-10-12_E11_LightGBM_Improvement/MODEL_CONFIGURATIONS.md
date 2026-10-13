# E11 Model Configurations (every run recorded)

## 1. LightGBM settings

All configurations share: seed 42, `deterministic=True`, `force_row_wise=True`, `n_jobs=1`, **no class weights**, NaN kept.

| Config | max_depth | num_leaves | min_child_samples | n_estimators | learning_rate | L1 | L2 |
|---|---|---|---|---|---|---|---|
| C2 stumps | 1 | 2 | 10 | 100 | 0.03 | 0 | 10 |
| C1 shallow, regularized | 2 | 3 | 10 | 50 | 0.05 | 0 | 5 |
| C0 E9 default | — | 4 | 5 | 100 | 0.05 | 0 | 0 |
| C3 moderate | 3 | 4 | 8 | 200 | 0.02 | 1 | 5 |

**Monotone +1** on `sws_hunger` and `last_published_stress` applies in the direct structure only.

**No class weights:** training folds were at most 68% HIGH (51/24); E11 judged that imbalance too mild to justify weighting.

## 2. Runs

| Group | Combinations | Windows | Count |
|---|---|---|---|
| Baselines B1 (carry-forward), B2 (regional), B3 (S1 rule), B4 (majority) | — | expanding, rolling 8 | 8 |
| Fixed grid (exploratory): direct × {core, core_plus, compact, expanded}; decomposed × provincial; residual × residual | 6 × 4 configs | expanding | 24 |
| Nested regressors: the same 6 combinations, config chosen per fold by inner MAE | 6 | expanding, rolling 8 | 12 |
| Nested classifiers: direct × {core, compact}, config chosen by inner Brier | 2 | expanding, rolling 8 | 4 |
| **Total arm/window outputs** | | | **48** |

**Every output is in `runs/20261012T145620Z/predictions.csv`, `scored_rows.csv` and `metrics.json`.** None was discarded.

## 3. Nested selection (what the inner folds chose)

**Inner quarters available per outer fold:**

- expanding window: 1, 2, 3, 4, 5, 6, 8;
- rolling 8 window: **1 in every fold.**

**Consequence:** configuration selection rests on very little inner evidence, and in the rolling window it is effectively a single-quarter choice.

**Choices across the 7 expanding folds:**

| Arm | Choices |
|---|---|
| direct core | C3 × 4, C0 × 3 |
| direct core_plus | C0 × 5, C3 × 2 |
| direct compact | C3 × 6, C0 × 1 |
| direct expanded | C0 × 3, C1 × 2, C3 × 2 |
| decomposed | C3 × 7 |
| residual | C0 × 3, C2 × 2, C3 × 2 |
| classifier core | C0 × 6, C3 × 1 |
| classifier compact | C1 × 3, C0 × 2, C3 × 2 |

**The choices change between folds.** There is no stable "best" configuration, which is consistent with the small sample.

## 4. Calibration

The E6 rule (≥ 8 inner out-of-fold quarters and ≥ 10 rows per class) was **never met**: at most 8 inner quarters and 6 LOW rows. **All classifier probabilities are uncalibrated.**
