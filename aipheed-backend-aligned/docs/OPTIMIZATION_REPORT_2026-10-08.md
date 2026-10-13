# MODEL-B Optimization Report (2026-10-08)

**Status:** experiment only. Nothing in this report is served. The production model (MODEL-A) and Chapter III are unchanged. Nothing has been committed or deployed.

**Script:** `scripts/supplementary/optimize_model_b.py`
**Evidence:** `evidence/2026-10-08_optimization/`

The 78.2% figure from the earlier reliability review is **invalid**. It used SWS hunger data for quarter t, which was published after the forecast quarter had already begun. It is not used anywhere in this report, either as a target or as a comparison.

---

## 1. Baseline

**MODEL-B** is the timing-valid version of Algorithm 3 (LightGBM, default settings, k = 1).

- **Features:** 47 columns. These are the 45 candidates from Section 3.3.2.6, plus CPI_dev, plus SWS hunger.
- **Timing (strict Rule 3):**
  - Government series are taken from quarter t-1.
  - SWS uses the latest round released before quarter t+1 starts.
  - News comes from quarter t.
  - Poverty incidence uses whichever survey had been published by then.
- **Evaluation:** expanding-window walk-forward. Each fold needs at least 8 target quarters of training data, which gives 11 test quarters (55 province-quarter rows). The cut-off is 0.50.

| Metric | Baseline |
|---|---:|
| Mean fold accuracy | **0.7636** |
| Weighted precision | 0.8081 |
| Weighted recall | 0.7636 |
| Weighted F1 | 0.7650 |
| ROC-AUC | 0.8244 |
| Confusion matrix [[TN, FP], [FN, TP]] | [[20, 2], [11, 22]] |
| Accuracy by year (2022 / 2023 / 2024 / 2025) | 0.80 / 0.85 / **0.60** / 0.90 |

I re-ran the baseline and got the same predicted probabilities as before (largest difference about 1e-16).

## 2. Frozen protocol

These rules were fixed before any experiment ran:

- **Nested selection:** every choice (hyperparameters, threshold, feature subset, class weighting) is made inside each outer fold. It uses an inner walk-forward over that fold's training quarters only, with at least 5 inner target quarters. The outer test quarter never influences any choice.
- **One model and one seed:**
  - LightGBM only.
  - Optuna TPE with seed 42, 50 trials per outer fold.
  - No seed selection.
- **Pre-registered rule for a reliable improvement.** A variant counts as a reliable improvement only if all three conditions hold:
  - mean fold accuracy is at least baseline + 0.018 (one test row);
  - no year is worse than the baseline by more than 0.10;
  - ROC-AUC is no lower than baseline − 0.02.
- **Unchanged:** the label (Eq. 3, global median 14.6), the threshold rule (0.50 unless chosen inside training), the 2024 quarters (none removed) and the target.

## 3. Experiments (successful and failed)

The machine-readable results are in:

- `experiment_log.json`: full log, including every per-fold choice.
- `experiment_summary.csv`: one row per variant.
- `predictions_all_variants.csv`
- `feature_importance_by_variant.csv`

Year columns are accuracy for that year; "Reliable" applies the pre-registered rule from Section 2.

| Variant | Change (decided in-fold) | Acc | F1 | AUC | 2022 | 2023 | 2024 | 2025 | Reliable |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| E0 | Baseline (defaults) | 0.7636 | 0.7650 | 0.8244 | 0.80 | 0.85 | 0.60 | 0.90 | n/a |
| E1 | `class_weight="balanced"` | 0.8000 | 0.8016 | 0.8072 | **0.60** | 0.90 | 0.70 | 0.90 | No (2022 −0.20) |
| **E2** | `scale_pos_weight = (1−p)/p`, p = HIGH share in fold training | **0.8182** | **0.8200** | **0.8278** | 0.80 | 0.90 | 0.70 | 0.90 | **Yes** |
| E3 | Decision threshold chosen by inner walk-forward | 0.7636 | 0.7650 | 0.8244 | 0.80 | 0.85 | 0.60 | 0.90 | No (inner search always returned 0.50) |
| E4 | In-fold top-K feature selection (K ∈ {10, 15, 20, 30, all}) | 0.7455 | 0.7463 | 0.8230 | 0.80 | 0.85 | 0.55 | 0.90 | No (worse) |
| E5 | Optuna TPE, 50 trials, inner accuracy | 0.7636 | 0.7650 | 0.7824 | 0.80 | 0.85 | 0.65 | 0.80 | No (AUC −0.04) |
| E6 | TPE plus a class-weight choice | 0.7636 | 0.7650 | 0.7204 | 0.80 | 0.85 | 0.65 | 0.80 | No (AUC −0.10) |
| E7 | TPE plus an inner threshold | 0.7636 | 0.7650 | 0.7824 | 0.80 | 0.85 | 0.65 | 0.80 | No |

**What failed and why:**

- **Hyperparameter tuning (E5–E7):**
  - Tuning did not raise accuracy, and it lowered AUC.
  - Each inner search has only 3–10 inner test quarters (15–50 rows) to score candidates on. With so little data, the search overfits the inner folds, and the configurations it picks do not carry over to the outer test quarter.
  - The library defaults are the more robust choice at this sample size.
- **Threshold search (E3):** it always settled on 0.50. Moving the threshold therefore adds nothing beyond the default.
- **Feature selection (E4):** choosing a smaller feature set inside each fold lowered accuracy. The top-K choice was unstable from fold to fold.
- **Balanced class weight (E1):** overall accuracy rose to 0.80, but 2022 fell by 0.20. That breaks the year rule, so E1 is rejected.

## 4. Final candidate: MODEL-B2 (E2)

**What changes.** Only one setting differs from MODEL-B: `scale_pos_weight` is set to (1−p)/p, where p is the share of HIGH rows in that fold's training data. It is recomputed from training data alone in every fold; across folds it moved from 1.857 down to 1.093 as the HIGH share grew. Every other LightGBM parameter stays at the library default (`random_state=42`).

Configuration: `best_candidate_config.json`.

**Why this is a correction, not tuning.** The training data are imbalanced: 28–48% HIGH depending on the fold. The weight simply counteracts that imbalance using a fixed formula, so no search over the test data is involved. It is a standard LightGBM setting, and the algorithm is still Algorithm 3.

| Metric | MODEL-B (baseline) | MODEL-B2 (E2) | Change |
|---|---:|---:|---:|
| Mean fold accuracy | 0.7636 | **0.8182** | +0.0545 (+3 rows) |
| Weighted F1 | 0.7650 | 0.8200 | +0.0550 |
| Weighted precision | 0.8081 | 0.8413 | +0.0332 |
| ROC-AUC | 0.8244 | 0.8278 | +0.0034 |
| HIGH precision / recall | n/a | 0.926 / 0.758 | n/a |
| Confusion matrix [[TN, FP], [FN, TP]] | [[20, 2], [11, 22]] | [[20, 2], [8, 25]] | 3 fewer missed HIGH |
| Missed HIGH (FN) | 11 | 8 | −3 |

The gain comes entirely from 3 HIGH rows that the baseline missed and E2 catches. E2 adds no false alarms.

### 4.1 Fold-level results (`best_candidate_fold_results.csv`)

| Test quarter | 22-Q4 | 23-Q1 | 23-Q2 | 23-Q3 | 23-Q4 | 24-Q1 | 24-Q2 | 24-Q3 | 24-Q4 | 25-Q1 | 25-Q4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Accuracy | 0.8 | 1.0 | 0.8 | 1.0 | 0.8 | **0.6** | **0.4** | 0.8 | 1.0 | 1.0 | 0.8 |

### 4.2 Year-level results (`best_candidate_year_results.csv`)

| Year | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|
| Accuracy | 0.80 | 0.90 | **0.70** | 0.90 |
| At least 75%? | Yes | Yes | **No** | Yes |

### 4.3 Robustness (`e2_robustness.json`)

**Sensitivity to the minimum training window.** E2 stays at 0.80 or above for every window tried, and stays above E0 throughout:

| Minimum training quarters | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|
| E2 accuracy | 0.800 | 0.817 | 0.818 | 0.820 | 0.800 |
| E0 accuracy | 0.754 | 0.767 | 0.764 | 0.760 | 0.733 |
| E2 AUC | 0.807 | 0.824 | 0.828 | 0.832 | 0.817 |

**Longer horizons.**

| Horizon | E2 accuracy | E0 accuracy |
|---|---:|---:|
| k = 2 | 0.740 | 0.720 |
| k = 3 | 0.733 | 0.689 |

Both fall below 0.75, so the **maximum reliable lead time is 1 quarter**.

**Reproducibility.** Running E2 twice gives identical probabilities.

### 4.4 Feature importance (`best_candidate_feature_importance.csv`)

Importance is the mean share of gain across folds.

| Rank | Feature | Gain share |
|---:|---|---:|
| 1 | rice_price_regular | 0.251 |
| 2 | commodity_rootcrops | 0.197 |
| 3 | commodity_livestock | 0.101 |
| 4 | FSSI_lag2 | 0.067 |
| 5 | headline_cpi | 0.064 |
| 6 | unemployment_rate_lag1 | 0.051 |
| 7 | commodity_fruit_veg | 0.036 |
| 8 | rice_price_regular_lag1 | 0.034 |
| 9 | food_cpi | 0.032 |
| 10 | food_cpi_yoy_lag1 | 0.022 |

How to read this:

- **Price levels dominate.** These series trend upward over time, so part of what they contribute is probably a time signal ("later quarters are more often HIGH"), not a causal driver.
- **Commodity prices after 2021 are not independent measurements.** They are derived from food CPI, so they do not add separate information.
- **News carries real weight.** The news-based FSSI (lag 2) is the strongest non-price feature.

## 5. Why 2024 is weak (`investigation_2024.json`)

The errors are concentrated in 2024-Q1 and 2024-Q2, where accuracy is 0.4 under the baseline. The investigation found four causes:

1. **Hunger jumped to a new level.** Mean SWS hunger was 19.6 in 2024, against about 11 in 2022–2023. The training folds had 28–34% HIGH rows, but 80–100% of the 2024 test rows were HIGH. Mean predicted probability rose only gradually (0.33 → 0.54 → 0.78), so the model caught up one to two quarters late.
2. **2024 conditions fell outside the training data.** Measured against the training rows before 2024-Q1:
   - `enso_numeric`: standardized mean difference of 2.41, with 75% of 2024 rows outside the training range.
   - `rice_price_regular`: 90% of rows outside the range.
   - `rice_price_regular_accel`: standardized mean difference of 1.65.
   - Drought alerts and rainfall anomalies also shifted.

   A tree model cannot extrapolate beyond values it has seen.
3. **Timing.** Under strict Rule 3, the SWS round that first showed the jump was not yet released when the forecasts for 2024-Q1 and 2024-Q2 were issued.
4. **Not enough history.** There were only about 7 years of quarterly data and no earlier comparable shock to learn from.

The investigation found no implementation error. E2 improves 2024 from 0.60 to 0.70 but does not bring it to 75%. No variant was allowed to drop 2024 quarters or to tune on them.

## 6. Algorithm 4 diagnostic (`algorithm4_diagnostic.json`)

**Setup.** The acceptance rule is unchanged: holdout weighted F1 ≥ 0.75 **and** AUC-ROC ≥ 0.80.

- Optuna TPE with 100 trials searches the nine approved hyperparameters.
- The objective is cross-validated weighted F1 under walk-forward.
- The last 4 target quarters (2024-Q3 to 2025-Q4; 20 rows, only 2 of them LOW) are held out and scored once.

| Class handling | CV F1 | Holdout F1 | Holdout AUC | Probabilities given to the 2 LOW rows | Passes |
|---|---:|---:|---:|---|---|
| Default | 0.784 | 0.80 | 0.50 | 0.980, 0.764 | F1 yes, AUC **no** |
| Balanced | 0.788 | 0.80 | 0.50 | 0.649, 0.754 | F1 yes, AUC **no** |
| scale_pos_weight (E2 rule) | 0.809 | 0.80 | 0.444 | 0.908, 0.922 | F1 yes, AUC **no** |

**Algorithm 4 fails the AUC part of its rule in every setting.**

- **Why.** With only 2 LOW rows in the holdout, AUC depends entirely on how those 2 rows rank against 18 HIGH rows. Both LOW rows come from a period of high hunger, and the model gives them high probabilities. The cause is the composition of the holdout, not a degenerate model: the trees do split, and F1 passes.
- **Consequence.** Section 3.4.4 says a configuration below threshold is not published. By that rule, no Algorithm 4 configuration qualifies.
- **What was not done.** The holdout window was not moved or redefined, because that would amount to choosing the test set after seeing results.

## 7. Leakage and timing audit (`feature_audit.csv`)

Each of the 47 features has a recorded source, frequency, transformation, typical release lag and the quarter used. Under strict Rule 3:

- **Released before the forecast quarter:** every feature is published before quarter t+1 begins.
  - SWS uses release dates taken from the article dates in the source URLs, plus four manually checked dates.
  - Poverty incidence uses the survey vintage that had been published.
  - CPI_dev uses only prior quarters (t-5 to t-2).
- **No target-period information:** no feature contains information from quarter t+1.
- **Label not used as a feature:** labels enter only as y.
- **Training data only:** class weights, thresholds, feature subsets and hyperparameters are all computed from training folds.
- **Consistency check:** `scripts/verify_consistency.py` still passes 39/39 on production.

**Result: PASS.**

Release lags for series other than SWS and poverty follow each agency's usual publication practice. Under the strict rule there is one full quarter of margin, but the dates should still be confirmed against the official release calendars.

## 8. Comparison against the 76.4% baseline

| Model | Mean fold accuracy | vs 76.4% | Meets 75% overall | Weakest year | Beats persistence (0.800) |
|---|---:|---:|---|---|---|
| MODEL-B (baseline) | 0.7636 | n/a | Yes | 2024: 0.60 | No |
| **MODEL-B2 (E2)** | **0.8182** | **+5.5 pp** | Yes | 2024: 0.70 | By one row (+0.018) |
| Best tuned variant (E5/E7) | 0.7636 | +0.0 | Yes | 2024: 0.65 | No |

"Persistence" means predicting that next quarter's label equals this quarter's, scored on the same 55 rows. It reaches 0.800 (by year: 0.60 / 0.80 / 0.80 / 0.90), and it is **optimistic**: under strict Rule 3, this quarter's label depends on an SWS round that is usually not yet published when the forecast is made. Even against that generous comparison, E2's margin is a single row. H3 (the model beats persistence) is therefore at best weakly supported.

## 9. Remaining limitations

1. **Selection optimism.** Eight variants were compared on the same 11 outer test folds. E2 met a rule written before the runs, and its choice of weights is a training-only formula. Even so, choosing the best of eight carries some optimism. The +5.5 pp should be confirmed on quarters not yet observed (2026 onward) before it is treated as settled.
2. **2024 remains below 75%** (0.70). The model lags regime shifts by one to two quarters.
3. **Price levels may act partly as a clock**, and commodity prices after 2021 are derived from CPI.
4. **Algorithm 4 AUC fails (0.44–0.50).** Under Section 3.4.4, this blocks publishing any Algorithm 4 configuration as things stand.
5. **The 45-vs-12 feature-count contradiction in Chapter III is unresolved.**
   - 45 features: lines 1418, 1462, 1775, 1930.
   - 12 features: lines 1164, 1685, 1781–1782, 1817, 1825.
   - Section 3.3.2.7 is missing.

   The adviser must decide which reading governs. MODEL-B and MODEL-B2 follow the 45-feature reading.
6. **Small sample:** 55 test rows, so one row moves accuracy by 1.8 pp. The 95% Wilson interval for 45 of 55 rows correct (81.8%) runs from about 0.70 to 0.90, so the lower end is below 75%.
7. **The strict-timing assumption** (forecast issued before t+1) is the reading of Rule 3 that Chapter III supports. A looser reading changes which SWS round is available.

## 10. Deliverables index

| # | Required output | File |
|---|---|---|
| 1 | Report | `docs/OPTIMIZATION_REPORT_2026-10-08.md` |
| 2 | Machine-readable experiment results | `evidence/2026-10-08_optimization/experiment_log.json`, `experiment_summary.csv`, `predictions_all_variants.csv` |
| 3 | Best-model config | `best_candidate_config.json` |
| 4 | Best-model predictions and probabilities | `best_candidate_predictions.csv` |
| 5 | Fold-level results | `best_candidate_fold_results.csv` |
| 6 | Year-level results | `best_candidate_year_results.csv` |
| 7 | Feature importance | `best_candidate_feature_importance.csv`, `feature_importance_by_variant.csv` |
| 8 | Leakage and timing audit | `feature_audit.csv`, Section 7 |
| 9 | Comparison against 76.4% | Sections 4 and 8 |
| Extra | 2024 investigation, Algorithm 4 diagnostic, robustness | `investigation_2024.json`, `algorithm4_diagnostic.json`, `e2_robustness.json` |

To reproduce (from `aipheed-backend-aligned/`):

```
python -m scripts.supplementary.optimize_model_b
python -m scripts.supplementary.investigate_2024
python -m scripts.supplementary.feature_audit_model_b
python -m scripts.supplementary.algorithm4_diagnostic
```

## 11. Recommendation

**CANDIDATE READY FOR REVIEW.** MODEL-B2 passes the leakage, timing and reproducibility checks and the pre-registered improvement rule. It should **not** be deployed yet, because:

- Algorithm 4 fails its AUC threshold;
- 2024 is below 75%;
- the 45-vs-12 question needs the adviser's decision;
- the gain should be confirmed on quarters not yet observed.

MODEL-A remains in production. A single configuration above 75% does not by itself mean the thesis passes.
