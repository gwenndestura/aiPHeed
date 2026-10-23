# E105: food-insecurity (SWS hunger) forecasting model. Pre-registered protocol

**Date:** 2026-10-23. **Branch:** `main` @ `0239273`, isolated directory, nothing committed. Production, E100–E104 and all sealed files are read only and hash-checked before and after. Outputs go to `out/` only.
**Freezing:** this file is hashed (`runner/PROTOCOL_SHA256.txt`) before any model below is scored.

**Already examined (disclosed):** all 2021-Q2..2026-Q3 SWS outcomes; E104's ridge forecasts (R0–R4, worse than persistence); the persistence (RW) error at Lead 2 2025-Q2..2026-Q3. No model below (MA2, MEAN, AR1D, SES, DRIFT, the B residual models, the SWS-ALL input variant) has been scored. All results are **development evidence**; the 2026-Q4 / 2027-Q1 seal is the unseen test.

## Diagnosis that motivates the design (from inspection, before scoring)

1. One regional outcome per quarter: 21 quarters with a posted SWS round in 2021-Q2..2026-Q3 (2022-Q1 has none). Province or LGU copies are not independent observations.
2. Trained models needing ≥ 8 posted label pairs start forecasting in 2024-Q4 / 2025-Q2, when every outcome is HIGH.
3. E104's ridge models were trained mostly on the 2023–24 rise (later hunger ≈ latest + 5 points) and extrapolate it (forecasts ≈ 29.6% when the latest reading is 24.0%).
4. The served as-of hunger input uses production rounds only (`definition_A = True`). The three supplementary 2025 rounds (2025-Q2 ×2, 2025-Q3; published 2025-06-27, 2025-08-15, 2025-11-05) are ignored as inputs but included in the evaluation outcome. The latest reading therefore stayed at 2025-Q1 (24.0%) for the issue dates 2025-07-01, 2025-10-01 and 2026-01-01.
5. Univariate time-series models need only the posted SWS history, so they can forecast from 2021-Q4 onward and be evaluated on quarters with both outcome classes.

## Outcome

y_L(t) = mean of all SWS Balance Luzon rounds of quarter t + L (%); class HIGH if > 11.3. L ∈ {1, 2}.

## Information at origin t (issue = day 1 of quarter t + 1)

- SWS input series, rounds with `published` < issue: **SWS-ALL** (all rounds; primary) and **SWS-A** (`definition_A` only; the served rule, sensitivity). Quarter value = mean of its posted rounds. H_last = value of the latest posted quarter. No pre-2021 round exists in the file or is used.
- External features: E102 as-of regional features (REL, E1raw, A2raw) and the FIRI v2 history indicator raw values (C1 El Niño flag, C3 harvest drop, regional mean) for origin t.
- Training pair (t', y(t' + L)) at origin t only if t' < t and every round of quarter t' + L was posted before issue(t).

## Models

**Tier A (univariate; posted SWS history only):**

| Id | Forecast |
|---|---|
| RW | H_last |
| MA2 | mean of the last two posted quarter values |
| MEAN | mean of all posted quarter values |
| AR1D | μ + φ^g (H_last − μ); μ = MEAN; φ = least-squares slope of (H_q − μ) on (H_{q−1} − μ) over consecutive posted quarters, clipped to [0, 1], ≥ 5 pairs else φ = 1; g = quarters from the latest posted quarter to the target |
| SES | simple exponential smoothing level over posted quarters; α ∈ {0.1, …, 1.0} minimising one-step squared error on the posted history (≥ 5 values, else α = 1) |
| DRIFT | H_last + g × mean of the last up-to-4 quarter-to-quarter changes (0 if none) |

**Tier B (persistence + external adjustment):** ŷ = H_last + f(x), f fitted on training residuals y − H_last (≥ 8 pairs), ridge alpha = 5 on standardised x with intercept: B-REL (REL), B-E1 (E1raw), B-RELE1 (REL, E1raw), B-A2 (A2raw), B-CLIM (C1, C3), B-ALL (REL, E1raw, A2raw, C1, C3); B-GBM: LightGBM regressor on the B-ALL features (20 trees, num_leaves 2, max_depth 1, learning_rate 0.1, min_child_samples 3, reg_lambda 5, deterministic, seed 105). News (N1: 20 of 115 province-quarters) and poverty (constant over time) cannot enter a regional time model (disclosed).

**Probabilities** for every model: p = 1 − Φ((11.3 − ŷ) / σ), σ = RMSE of that model's own earlier forecasts whose outcomes were fully posted before the issue (≥ 4, else 4.0 points).

**Reference (separate evaluations, never pooled):** served FIRI v2 regional index (E103 values) and persistence probability P0 (H1) for classification; production LightGBM is a price-pressure model and is not re-evaluated here.

## Evaluation

- **Tier A set:** per lead, every target with an outcome where all Tier A models forecast (both classes expected). **Tier B set:** where all Tier B models forecast; RW and the Tier A models are re-scored on that same set.
- Level: MAE, RMSE, mean error; paired squared-error difference vs RW (bootstrap 95% CI, 2,000 draws, seed 2026; exact sign-flip permutation p); period split at 2024-Q1; leave-one-quarter-out robustness (RMSE difference vs RW after removing the quarter most favourable to the model).
- Classification (from p ≥ 0.5): accuracy (Wilson CI), balanced accuracy, recall and precision for HIGH and LOW, F1, confusion matrix, Brier, calibration-in-the-large, share predicted HIGH; per quarter with rising-stress flags (y = 1 after y = 0, or +3 points).

## Decision rules (fixed now)

- **Level improvement over persistence:** MAE and RMSE both lower than RW on the common set, permutation p < 0.10, and RMSE still lower than RW after removing the single most favourable quarter.
- **75% classification objective (Lead 2):** accuracy > 0.75 on a set with both classes, above ALWAYS and above RW's class accuracy, HIGH recall ≥ 0.5 and LOW recall ≥ 0.5, share predicted HIGH between 0.1 and 0.9.
- **Best valid model:** the lowest Lead-2 RMSE among models meeting the level-improvement rule at Lead 2 and not worse than RW at Lead 1 (RMSE); if none, persistence remains the best valid model.
- **SWS-ALL vs SWS-A:** reported for RW and the best model; the primary results use SWS-ALL.
- **Prospective:** seal every model's Lead-1 2026-Q4 and Lead-2 2026-Q4 / 2027-Q1 forecasts before those rounds are posted.

## Not done

No pre-2021 data (study-window rule), no new data, no synthetic outcomes, no tuning on any outcome beyond the walk-forward rules above, no change to served or sealed files, no commit.
