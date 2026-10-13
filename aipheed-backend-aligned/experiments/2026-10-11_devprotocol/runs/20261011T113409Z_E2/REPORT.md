# E2 Report: Relative Food-Price Stress (run 20261011T113409Z_E2)

**Research alternative. Not a food-insecurity forecast, and not a thesis-target result.**

- E2 has **no bearing on the > 75% accuracy requirement**.
- The test quarters are 7 reused plus 2 less-exposed. **The result is exploratory.**

This report was added after the run. It is not listed in `manifest.json`, whose hashes cover the runner outputs.

## Configuration

| Item | Value |
|---|---|
| Protocol | `../../E2_PROTOCOL.md`, fixed before execution, including the improvement rule |
| Runner | `../../runner/run_e2_relative_cpi.py` |
| Hashes | Recorded in `config.json` |
| Target | d = provincial food CPI YoY − five-province mean, same quarter, in percentage points. Built from `data/processed/psa_indicators.parquet`; no SWS. |
| Target checks | 100 rows (2021-Q1 to 2025-Q4); no missing values; exactly 5 provinces per quarter; sums to 0 within each quarter. Equals the Equation 3 provincial component for all 80 labelled rows (within 2×10⁻⁵). Full construction with publication dates: `target_table_construction.csv`. |
| Eligibility | Provincial CPI publication date, using the WD1 proxy (national + 14 days, verified for 2024-Q4 only; not before 2022-02-04) |
| Folds | All 9 eligible, with 10–18 training quarters (≥ 8 required). Per-fold quarters and dates are in `config.json`. |
| MODEL-B2-reg | `LGBMRegressor`, defaults, seed 42, 44 MODEL-B2 inputs. Determinism check passed. |
| Baselines | Carry-forward (latest eligible d, i.e. d two quarters back); Province-mean (mean over training quarters); Zero |

## Results (all 9 quarters; the decision set)

| Predictor | MAE (pp) | Mean within-quarter Spearman ρ | Top-province hits | Sign balanced accuracy (secondary) | Sign confusion matrix [[TN,FP],[FN,TP]] |
|---|---:|---:|---|---:|---|
| **MODEL-B2-reg** | 1.421 | **0.201** | 2/7 (2 quarters undefined: tied predictions) | 0.583 | [[18, 9], [9, 9]] |
| Carry-forward | 1.536 | **0.378** | 4/9 | 0.611 | [[18, 9], [8, 10]] |
| Province-mean | 1.635 | −0.333 | 1/9 | 0.352 | [[13, 14], [14, 4]] |
| Zero | **1.287** | undefined (constant) | undefined | undefined | [[27, 0], [18, 0]] |

**Sign classes:** 18 provinces above the mean and 27 below or equal, across 45 rows.

**Chance level:** guessing the top province by chance would succeed in 1 of 5 quarters (0.20).

**Paired quarter bootstrap, MODEL-B2-reg − Carry-forward** (10,000 draws, seed 42):

| Measure | Mean difference | 95% CI |
|---|---:|---|
| Spearman ρ | −0.177 | **−0.551 to +0.139** |
| MAE | −0.115 | −0.460 to +0.268 |

## Improvement rule, fixed before execution

| Rule | Result |
|---|---|
| 1. ρ gain ≥ 0.20 over carry-forward | **Fail**: −0.177 |
| 2. 95% CI of the ρ difference excludes 0 (positive) | **Fail**: −0.551 to +0.139 |
| 3. MAE no worse than carry-forward | Pass: 1.421 vs 1.536 |

**Verdict: no demonstrated value beyond carry-forward.**

## Subsets

| Subset | Measure | MODEL-B2-reg | Carry-forward | Province-mean | Zero |
|---|---|---:|---:|---:|---:|
| Reused 7 (2023-Q4 to 2025-Q1, 2025-Q4) | ρ | 0.358 | 0.286 | −0.186 | undefined |
| | MAE | 1.533 | 1.455 | 1.743 | **1.423** |
| | Top hits | 2/5 | 4/7 | 1/7 | undefined |
| Less-exposed 2 (2025-Q2, 2025-Q3) | ρ | −0.35 | 0.70 | −0.85 | undefined |
| | MAE | 1.029 | 1.820 | 1.255 | **0.815** |
| | Top hits | 0/2 | 0/2 | 0/2 | undefined |

**Bootstrap intervals for the subsets (B2 − CF):**

- **Reused 7:** ρ −0.094 to +0.278; MAE −0.210 to +0.450.
- **Less-exposed 2:** the interval has only 2 points to resample (ρ −1.3 to −0.8). **It is not a meaningful uncertainty estimate.**
- The less-exposed quarters are **not independent**: their d values entered earlier models as inputs (E2 protocol).

## Per quarter

| Quarter | ρ B2 / CF / PM | MAE B2 / CF / PM / Zero | Actual top province | B2 top | CF top |
|---|---|---|---|---|---|
| 2023-Q4 | 0.74 / 0.5 / 0.8 | 0.77 / 1.10 / 0.90 / 1.03 | Batangas | tie (undefined) | Rizal |
| 2024-Q1 | 0.67 / 0.9 / 0.9 | 1.00 / 1.16 / 0.64 / 0.95 | Rizal | tie (undefined) | Rizal |
| 2024-Q2 | −0.1 / −0.2 / 0.0 | 2.26 / 2.39 / 1.99 / 1.43 | Quezon | Batangas | Batangas |
| 2024-Q3 | −0.4 / −0.4 / −0.7 | 2.42 / 2.58 / 2.62 / 1.80 | Quezon | Rizal | Rizal |
| 2024-Q4 | 0.9 / 0.3 / −0.7 | 1.26 / 0.81 / 2.37 / 1.84 | Quezon | Quezon | Quezon |
| 2025-Q1 | 0.6 / 0.7 / −1.0 | 2.01 / 0.95 / 2.48 / 2.09 | Quezon | Cavite | Quezon |
| 2025-Q2 | 0.0 / 0.8 / −0.7 | 0.98 / 1.58 / 1.49 / 1.09 | Laguna | Quezon | Quezon |
| 2025-Q3 | −0.7 / 0.6 / −1.0 | 1.08 / 2.06 / 1.02 / 0.54 | Cavite | Quezon | Quezon |
| 2025-Q4 | 0.1 / 0.2 / −0.6 | 1.01 / 1.19 / 1.21 / 0.81 | Laguna | Laguna | Laguna |

Province-level predictions and errors: `scored_rows.csv`.

## Interpretation

1. **Can the model predict relative food-price stress?**
   - **Not better than simple baselines.** Its MAE (1.42) is below carry-forward's (1.54), but **above Zero's (1.29)**. Predicting "no provincial difference" has the smallest error of all predictors.
   - Its lower MAE comes from shrinking predictions toward 0, not from better ranking.
   - **It ranks provinces worse than carry-forward:** ρ 0.20 against 0.38.
2. **Can it identify the most-stressed province?**
   - **No.** It hit 2 of 7 defined quarters, against carry-forward's 4 of 9 and chance at 1 in 5.
   - In 2 quarters its predictions were tied at the top, consistent with the coarse default trees on 50–90 training rows.
3. **Can it predict absolute food insecurity?** **E2 cannot address this.** The target contains no hunger measure.

**Notable pattern** (observation, not tested):

- Quezon's deviation moved from −2.4 (2023-Q4) to between +3.6 and +5.2 (2024-Q2 to 2025-Q1). Every predictor missed the onset of this shift.
- Carry-forward then tracked it with a two-quarter lag.
- The province-mean baseline ranked backwards (ρ −0.33), because the historical ordering (Rizal highest) broke down.

## Integrity

| Check | Result |
|---|---|
| Runner hash guard: 293 protected files (aligned data, models, frozen forecasts, reports, pre-registration drafts, experimental modules, runners, **E1 run and diagnosis artifacts**) | **Unchanged** |
| Target access | All 9 targets revealed only after their predictions were written (`manifest.json`) |
| No 2026 target | Enforced |
| Production modules | None loaded |
| Production `backend/` | 54 files re-hashed, including the served model `cbab63f8…`; all match. No archive, candidate or pipeline-run folders. |
| Pipeline, admin endpoint, scheduler, promotion, deployment | None |
| Protected 2026 outcome data | Not accessed |
| Other files | Nothing outside this run folder changed during the run |
| Tests before execution | Full suite 208 passed, including 13 new E2 safety tests |
| Deviations from protocol | None |
