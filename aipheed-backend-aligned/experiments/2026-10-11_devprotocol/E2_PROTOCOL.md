# E2 Protocol: Relative Food-Price Stress (research alternative)

**Status:** fixed before execution.

**What E2 is:**

- **A research-alternative experiment.** It does not replace Equation 3 or the thesis target.
- **It is not a food-insecurity forecast,** and must not be used in the dashboard or the thesis methodology.
- **It can answer:**
  1. Can the model predict relative food-price stress?
  2. Can it identify the province with the greatest relative food-price stress?
- **It cannot answer:** whether the model predicts absolute food insecurity.
- **It says nothing about the > 75% accuracy requirement.**

## Target

**Definition:** `d(p, q) = food_cpi_yoy(p, q) − mean over the five provinces of food_cpi_yoy(q)`.

| Item | Detail |
|---|---|
| Source | `data/processed/psa_indicators.parquet` (read-only), the same series `label_generator.py` uses for Equation 3 |
| Units | Percentage points of year-on-year food inflation |
| Coverage | 2021-Q1 to 2025-Q4, 20 quarters × 5 provinces. No missing values; exactly 5 provinces per quarter. |
| Consistency check | It equals (stress − SWS) / 2 from `labels.parquet` for all 80 labelled rows, to within 2×10⁻⁵ |
| SWS | **Not used** |

**Publication eligibility:**

- d(q) is published when the final-month provincial CPI of q is released. This uses `devprotocol_rule_l.cpi_published(q, provincial=True)`:
  - WD1 proxy: national release + 14 days;
  - verified for 2024-Q4 only;
  - never before 2022-02-04 (WD5).
- **Limitation:** the proxy is not a verified provincial release date.

## Folds

| Item | Rule |
|---|---|
| Training data for target T | Quarters q < T with d published before T's origin (00:00 on the first day of T) |
| Minimum | 8 eligible quarters. A target with fewer is marked **ineligible**, not relaxed. |
| Test quarters (fixed) | 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q2, 2025-Q3, 2025-Q4 |

**Exposure of the test quarters:**

- **Reused (7):** the E1 test quarters. Their deviations were further exposed by the E1 diagnosis.
- **Less-exposed (2): 2025-Q2 and 2025-Q3.**
  - They were never evaluation targets.
  - **They are not independent.** Their deviation values entered earlier models as inputs: `cpi_rel` is d two quarters back. 2025-Q2 was an input to E1's 2025-Q4 fold, and 2025-Q3 is printed as `cpi_rel_known` in `experiments/2026-10-09_window2021/FROZEN_2026_FORECASTS.csv`.
  - They did not influence the E2 design: the diagnosis used labelled quarters only.

**Excluded quarters:**

- 2026-Q1 and 2026-Q2: their CPI values were seen during collection.
- 2026-Q3 and 2026-Q4: protected.

## Inputs and models

**Inputs:**

- `development_frame()` rows for target T, with the MODEL-B2 set of 44 inputs, unchanged.
- No feature selection.
- Missing values stay NaN.

**Fixed predictors:**

| Name | Definition |
|---|---|
| MODEL-B2-reg | `LGBMRegressor(objective="regression", random_state=42, verbosity=-1)`, library defaults, no tuning. Fitted twice per fold; the predictions must be identical. |
| Carry-forward | d of the latest eligible quarter, for each province |
| Province-mean | The mean of d over the eligible training quarters, for each province |
| Zero | 0 for every province (no differentiation) |

## Metrics

**Main metrics:**

- **Within-quarter Spearman ρ.** Computed per quarter, then averaged. It is undefined when the predictions are constant, as for Zero.
- **Top-province hit.** Whether the predicted maximum equals the actual maximum. It is undefined when the predicted maximum is tied.
- **MAE.**
- Per-quarter predictions and errors.

**Secondary metric, sign classification:**

- Prediction > 0 vs actual > 0, with the threshold fixed at 0.
- Reported as balanced accuracy, class counts and per-quarter accuracy.

**Uncertainty:**

- A quarter-cluster bootstrap (10,000 draws, seed 42) of the paired per-quarter differences, MODEL-B2-reg − Carry-forward, for ρ and MAE.
- **With only 9 quarters, the intervals are coarse.**

**Subsets:** all 9 quarters (the primary set for the decision rule), reused 7, and less-exposed 2.

## Improvement rule (fixed before execution; applied to the 9-quarter set)

MODEL-B2-reg **demonstrates value** only if all three hold:

1. Mean within-quarter ρ is at least **0.20 higher** than Carry-forward's.
2. The 95% bootstrap interval of the paired ρ difference **excludes 0**.
3. MAE is **no worse** than Carry-forward's.

**Otherwise the result is "no demonstrated value beyond carry-forward."** If the interval is too wide to be informative, the uncertainty is reported rather than any success claimed.

## Safeguards

- The runner never loads production modules.
- Outputs go to a fresh `runs/<UTC>_E2/` folder, with no overwriting.
- Each fold's predictions are written **before** its test-quarter d is revealed.
- No 2026 target can be loaded.
- Protected files are hashed before and after the run: the E1 run and diagnosis folders, the runners, the data, models, frozen forecasts, reports and pre-registration drafts.
