# E107: one LightGBM on the 12 aiPHeed indicators. Pre-registered protocol

**Date:** 2026-10-25. **Branch:** `aipheed/e107-twelve-indicator-lightgbm` (from `aipheed/simple-methodology` @ `9433f9e`).
**Freezing:** this file is hashed (`runner/PROTOCOL_SHA256.txt`) before any model in it is scored. A change after freezing must be made as a dated addendum, frozen before the rows it affects are scored.
**Requirement basis:** Chapter I §1.5.2 (Objectives 2 and 4) and §1.7. Chapter I sets no accuracy threshold. The 75% accuracy requirement comes from the user's brief and old Chapter III Algorithm 3. It is criterion R2 below, never relaxed.

**Already examined (disclosed):** every outcome quarter through 2026-Q3 was scored by earlier experiments (E38–E106). The audit (`AUDIT.md`) and the label and feature-coverage counts were read before freezing. No E107 model output was seen before freezing.

## 1. Data

- **Window:** 2021-Q1..2026-Q3 only. Loaders refuse earlier rows.
- **Sources:** the tracked E41/E40 monthly CPI index and YoY files, PSA production, LFS, and the E40 news composition. The three extra files in `data_inputs/` are hash-checked. The backend's as-of functions are used for C1, N1, H1 and V1.
- **SWS:** production rounds only (`definition_A = True`, the served rule), for both inputs and labels. The three supplementary 2025 rounds are used only in sensitivity S1.

## 2. Targets

| | Definition | Level | Role |
|---|---|---|---|
| **T43** | Province *p*, quarter *q* is HIGH iff (a) Balance Luzon SWS involuntary hunger H_q (mean of the quarter's production rounds) > 11.3, **and** (b) food CPI YoY_pq > P60_p **or** (food − headline YoY)_pq > gapP60_p. The thresholds are the frozen 2021–22 E40 values. | province-quarter | **Primary.** The Chapter I §1.7 food-insecurity **risk** definition. A composite proxy, not a measured prevalence. |
| **R** | Quarter *q* is HIGH iff H_q > 11.3 | region (Balance Luzon) | **Observed-outcome check.** The only independently observed food-insecurity measure in the project. |

- A row is unlabelled when any part of its label is missing. It is never LOW by default.
- A label of quarter *q* is **known at origin t** iff *q* ≤ *t* − 1, every production round of *q* was posted before O(*t*), and its CPI quarter is complete.

## 3. Time definitions (identical for every lead k = 1, 2, 3, 4)

| Item | Rule |
|---|---|
| Origin | quarter *t* |
| Issue date O(*t*) | 00:00, day 1 of quarter *t* + 1 |
| Latest data at issue | CPI through month 2 of *t*; SWS rounds posted before O(*t*); production, LFS, remittances and rice through *t* − 1; typhoons through *t*; ENSO through *t* − 1; PAGASA items issued before O(*t*); headlines of *t* published before O(*t*) |
| Target quarter | *t* + *k* |
| Label | T43 or R of quarter *t* + *k*, as observed now |
| Features | the 13 columns of section 4, computed from data available at O(*t*). A1 and H1 depend on *k*; the others do not. |
| Training rows at origin *t* | (features of *t*′, label of *t*′ + *k*) for *t*′ ≥ 2021-Q1, *t*′ + *k* ≤ *t* − 1, label known at O(*t*) |
| Eligible origin | training rows from ≥ 6 distinct target quarters, with ≥ 5 HIGH rows and ≥ 5 LOW rows |
| Evaluation rows of lead *k* | every labelled target quarter *q* ≤ 2026-Q3 whose origin *q* − *k* is eligible |
| Development block | evaluation targets before 2025-Q4 |
| Final block | targets 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3. Untouched within E107. Scored once, after the development results are recorded and the code commit is fixed (the commit is written into the results). |

## 4. Features: the 12 indicator families as 13 columns

The 12 families are the FIRI v2 indicators (`firi.LABELS`). Each enters LightGBM as follows (full inventory in `runner/e107_lib.py: INVENTORY` and `INDICATOR_AUDIT.md`):

- **A1** food-price-pressure forecast. Two columns:
  - `A1_food`: the projected food YoY of quarter *t* + *k*, with the latest published index held flat, minus the province's food P60.
  - `A1_gap`: the projected food − headline YoY minus the province's gap P60.

  A1 is a non-learned structural projection, the input the served A1 forecast is built from. LightGBM is itself the price-pressure forecaster, so it cannot take another LightGBM's output as an input. The served-A1 variant is sensitivity S3.
- **A2, A3, V1, C1, C2, C3, C4, E1, E2, N1, H1:** one column each, with the raw value defined in `firi.raw_indicators()`, except **H1**, whose horizon is *k* (`thesis_system.regional_hunger(t, k)`).
- **Missing values:** left as NaN (LightGBM native). Never zero-filled.
- No feature selection. No other columns.
- **R model rows:** one row per origin, holding the mean of the five provinces' values for each column. V1 is then constant, so it carries no information for R by construction.

## 5. The model (E107-LGBM, primary, fixed now)

- **Classifier:** LightGBM `LGBMClassifier`.
- **Fixed settings:** objective binary, learning_rate 0.05, reg_lambda 5, colsample 1, subsample 1, `deterministic`, `force_row_wise`, `feature_pre_filter=False`, seed 107, n_jobs 1.
- **min_child_samples:** 5 for T43, 3 for R.
- **Grid of 8 configurations,** in this order of simplicity:
  - depth ∈ {1, 2}, with num_leaves = 2^depth;
  - then trees ∈ {50, 150};
  - then class_weight ∈ {None, "balanced"}.
- **Nested selection at every origin, training rows only:**
  - Inner folds: the last (up to) 4 distinct training target quarters *q_v*. Each is fitted on training rows whose target is ≤ *q_v* − *k* − 1 and scored on the rows of *q_v*.
  - A fold with fewer than 3 fit quarters, or with one class, is skipped.
  - Score: pooled log loss (p clipped to [1e-6, 1 − 1e-6]). The lowest score wins; ties go to the simpler configuration. With no valid fold, configuration 0 is used.
  - The selected configuration is refitted on all training rows.
- **Class:** HIGH iff P ≥ 0.5 (fixed).
- **Calibration:** none (too few rows). Calibration is reported as a diagnostic.
- **Explanation:** TreeSHAP (`pred_contrib`, log-odds) per column, summed per family and domain.

## 6. Comparison arms (identical rows)

| Arm | Target(s) | Definition |
|---|---|---|
| Persistence (Obj. 4-I) | both | the province's (or region's) latest label known at O(*t*); P = that label |
| Climatology / Majority | both | training HIGH share; class = majority |
| Always-HIGH, Always-LOW | both | accuracy only |
| PSA-only LR (Obj. 4-II) | T43 | L2 logistic, C = 1, standardised, training-median imputation, on A1_food, A1_gap, A2, A3, V1, C3, C4, E1 |
| NLP-only LR (Obj. 4-III) | T43 | the same, on N1 and an N1-missing flag |
| LR-12 (Obj. 4-IV) | T43 | the same, on all 13 columns plus missing flags |
| RULE | T43 | no learning: P = H1 × 1[A1_food > 0 or A1_gap > 0] |
| H1-alone | R | P = H1 (the served hunger outlook) |
| E56 (existing LightGBM) | T43, R | the sealed rolling-origin E56 outputs (`E63_Lead_Time_Study/sealed/predictions.csv`, hash-checked): `E56_p` for T43; `E56_p_hunger` for R. Leads 1–3, intersecting rows. |
| FIRI v2 (served headline) | T43, R | Lead 2: class and score from `backend/data/thesis/firi2_history.csv` (for R, the five-province mean). FIRI is not a probability; its Brier score is shown but flagged. |

## 7. Metrics and inference

**Per lead and target:**
- n rows and n quarters;
- accuracy with Wilson 95% CI, and a quarter-cluster bootstrap CI;
- balanced accuracy;
- precision, recall and F1 for each class;
- confusion matrix;
- AUC-ROC (pooled);
- Brier score and log loss;
- share predicted HIGH;
- per-quarter accuracy and Brier;
- calibration-in-the-large and a 5-bin reliability table.

**Paired comparisons:**
- Per-quarter Brier difference (summed over the quarter's rows).
- Quarter-cluster bootstrap 95% CI (2,000 draws, seed 2026).
- Exact one-sided sign-flip permutation p (H1: E107 is better).
- Results are reported for development, final, and combined. Section 8 is decided on **combined** rows, except G3.

## 8. Reliability rule (fixed now). E107-LGBM is reliable at lead k iff all of these hold

| | Criterion |
|---|---|
| R1 | ≥ 6 evaluated target quarters |
| R2 | accuracy ≥ 0.75 |
| R3 | accuracy > Persistence **and** > Majority |
| R4 | Brier < Persistence and < Climatology (for R also < H1-alone), and one-sided sign-flip p < 0.10 against the lowest-Brier of those baselines |
| R5 | recall HIGH ≥ 0.5 and recall LOW ≥ 0.5. Both classes must be present among the evaluated rows, otherwise R5 fails as "not assessable". |
| R6 | AUC ≥ 0.65 (T43). For R: AUC ≥ 0.65 when both classes are present, otherwise not assessable. |
| R7 | share predicted HIGH in [0.1, 0.9] |
| G1 | (T43) quarter accuracy ≥ 0.6 in at least 2/3 of evaluated quarters |
| G2 | Brier < the lowest-Brier R4 baseline in both chronological halves of the evaluated quarters (first ⌈n/2⌉ quarters, rest) |
| G3 | final block: accuracy ≥ max(Persistence, Majority) and Brier ≤ min(R4 baselines) on the final-block rows |

- **Maximum reliable lead** = the largest *k* such that every lead 1..*k* is reliable. If Lead 1 is not reliable, no reliable horizon is established. A lead that passes while a shorter one fails is reported but not counted.
- Leads with fewer than 6 evaluable quarters are reported as "not assessable" (R1).
- **The 75% requirement** is reported per lead from R2 alone, and also together with R3–R7.

## 9. Diagnostics (no effect on section 8; the primary model is fixed)

- **Ablations,** same nested procedure and rows:
  - drop one domain: −A, −V, −C, −E, −N, −H;
  - single domain: A-only, H-only;
  - A+H.
- **Importance:** mean |SHAP| and split-gain per column, family and domain over the evaluation predictions. Share of the largest family.
- **THR-INNER:** the class threshold chosen on the selected configuration's inner-fold predictions to maximise balanced accuracy (ties → nearest 0.5). Reported only.
- **Common rows:** metrics of every assessable lead on the target quarters shared by all of them.

## 10. Sensitivities (reported only)

- **S1:** labels with all SWS rounds, including the three supplementary 2025 rounds. Inputs unchanged.
- **S2:** V1 strict: missing for issue dates before 2025-07-01.
- **S3:** A1 as served: the E56 sealed `E56_p_price` at the same lead (leads 1–3) replaces A1_food and A1_gap, on the rows where it exists.

## 11. Prospective seal

- At origin 2026-Q3 (issue 2026-10-01), train on all labels known at that date.
- Forecast T43 for 2026-Q4, 2027-Q1, 2027-Q2 and 2027-Q3 (Leads 1–4) and R for the same quarters.
- Write `out/sealed_prospective.csv` and its SHA-256 before any of those outcomes is published.
- These are the only unseen-outcome tests.

## 12. Leakage controls (automated tests, `backend/tests/unit/test_e107.py`)

1. All 12 families are in the feature columns and in the fitted booster's feature names.
2. Future perturbation: changing every value published on or after O(*t*) leaves the features of *t* unchanged.
3. Split integrity: every training target quarter is ≤ *t* − 1 and known at O(*t*), and no evaluated (province, target) pair is in its training set.
4. Target alignment: target = *t* + *k*, and labels match the rule recomputed from the raw series.
5. Horizon arithmetic: issue dates, target months, projection base months (2 months at *k* = 4).
6. Window: nothing before 2021.
7. Reproducibility: a stored prediction is reproduced exactly.
8. The seal hash matches.

## 13. Not done

- No pre-2021 data, no new data collection, no web search for SWS/PSA values.
- No change to the served FIRI or E56 code paths, to the dashboard design, or to the deployed configuration.
- No tuning against evaluation rows.
- No synthetic outcomes.
