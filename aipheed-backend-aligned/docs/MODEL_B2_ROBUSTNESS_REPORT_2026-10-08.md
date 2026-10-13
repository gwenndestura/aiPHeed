# MODEL-B2 Robustness Report (2026-10-08)

**Scope:** validation of the frozen MODEL-B2 candidate. This phase ran no new optimization search and did not tune MODEL-B2.

**What was not touched:** production (MODEL-A is still served), Chapter III, the target, and the frozen configuration. Nothing was committed or deployed.

**The 81.8% result is preserved exactly as recorded.**

- **Script:** `scripts/supplementary/model_b2_robustness.py`
- **Evidence:** `evidence/2026-10-08_b2_robustness/`
- **Reproduce with:** `python -m scripts.supplementary.model_b2_robustness`

Each finding in this report is tagged with one of four labels:

- **[DATA]** what the data demonstrate;
- **[LIMITATION]** a known weakness that should be disclosed;
- **[METHOD]** a methodological issue;
- **[ADVISER]** a decision that needs adviser approval.

---

## 1. Executive summary

- **[DATA] Exact reproduction.** MODEL-B2 reproduces exactly: the same 55 rows, the same predictions, and probabilities within 1.1e-16. It gets 45/55 correct, for a mean fold accuracy of 0.8182, F1 0.820 and AUC 0.828.
- **[DATA] The gain over the baseline is small.** MODEL-B2 changes only 3 predictions, and all three go from wrong to right. Those three rows are HIGH observations whose baseline probabilities were just under 0.50 (0.41–0.50). They are in 3 different quarters and 3 different provinces. 3 folds improve, 8 are unchanged and none get worse. The exact McNemar test gives p = 0.25, so the gain is consistent in direction but not statistically established.
- **[DATA] No demonstrated advantage over persistence.** "Persistence" means predicting that next quarter's label equals the most recent label.
  - Against naive persistence (80.0%), MODEL-B2 is ahead by one observation (p = 1.0).
  - Against timing-valid persistence, MODEL-B2 is ahead by 3 rows (p = 0.51). Timing-valid persistence uses only labels whose SWS round had been published before the forecast quarter, and it scores 76.4%, the same as the baseline.
  - Neither difference shows superiority.
- **[DATA] The uncertainty is wide.** The 95% interval for 45/55 is 0.70–0.90. We cannot reject the possibility that true accuracy is 75% or lower (one-sided exact p = 0.155).
- **[DATA] Strong potential temporal-trend dependence.** A model given only a time index, under the same protocol, scores 78.2% (AUC 0.886). MODEL-B2 agrees with that time-only model on 85.5% of rows. Removing the price-level features drops MODEL-B2 to 56–60%. The 81.8% therefore depends heavily on price levels that largely track time.
  - This is **not leakage**: every value was available at forecast time.
- **[METHOD] The post-2021 commodity "prices" are not prices.** From 2022-Q1 onward, each commodity series equals its 2021-Q4 price × (1 + food CPI YoY of the same quarter). Its correlation with food CPI YoY is 1.000 within every province. The construction is timing-valid, but it changes what the feature means.
- **[DATA] 2024 accuracy is 70%.** The 2024 errors are explained by:
  - the target shift (95% of 2024 rows are HIGH, against 31% in training);
  - SWS release timing (the hunger jump was not yet published when the forecasts were made);
  - too few high-hunger training examples.
- **[DATA] Algorithm 4 fails on AUC because of the holdout composition.** There are only 2 LOW rows and both are within 1.6 points of the label threshold. Random scores would give an AUC standard deviation of 0.22 on this holdout. No implementation error was found.
- **[ADVISER] 45 vs 12 features.** The Equation 5 12-feature set scores 74.5% with the same weighting rule (69.1% with LightGBM defaults). Chapter III describes both a 45-feature and a 12-feature setup; that contradiction is still open.

**Classification: B. PROMISING BUT NEEDS METHODOLOGY CLARIFICATION** (see Section 15).

## 2. Frozen configuration

File: `MODEL_B2_FROZEN_CONFIG.json`. Hashes:

- config SHA-256: `92c12807…0050`
- input-frame SHA-256: `118c3297…11c1`
- file SHA-256: `d56891ee…0b2e`

The config also stores the SHA-256 of every script involved. The script checks that the feature list matches `best_candidate_config.json` before it runs.

| Item | Frozen value |
|---|---|
| Algorithm | Algorithm 3: LightGBM `LGBMClassifier`, library defaults (`objective=binary`, `random_state=42`) |
| Class weighting | `scale_pos_weight = (1 − p)/p`, where p is the HIGH share of that fold's training rows |
| Features | 47: the 45 candidates from Section 3.3.2.6, plus `cpi_dev` and `sws_hunger` |
| Target | `label_stress` (Eq. 3; HIGH if stress score > global median 14.6) |
| Horizon | k = 1 (features of quarter t predict the label of t+1) |
| Timing | Strict Rule 3: government series of t−1; news of t; SWS as released before t+1; poverty as published |
| Walk-forward | Expanding window; at least 8 target quarters; 11 test quarters (2022-Q4 to 2025-Q4); 55 rows |
| Cut-off | 0.50 |
| Seed | 42 |

## 3. Reproducibility [DATA]

| Check | Result |
|---|---|
| Identical fold assignment (11 quarters, 55 rows matched) | Yes |
| Identical labels | Yes |
| Identical predictions | Yes |
| Maximum probability difference | 1.1e-16 |
| Correct / total | 45 / 55 |
| Mean fold accuracy / F1 / AUC | 0.8182 / 0.8200 / 0.8278 |
| Predictions SHA-256 | `25f2ea5e…2e817` |
| **Overall** | **PASS** |

## 4. Outer-fold results

### 4.1 Fold table: baseline vs MODEL-B2 [DATA]

| Fold | Quarter | HIGH rows (of 5) | Baseline | MODEL-B2 | Change |
|---:|---|---:|---:|---:|---:|
| 1 | 2022-Q4 | 1 | 0.8 | 0.8 | 0 |
| 2 | 2023-Q1 | 0 | 1.0 | 1.0 | 0 |
| 3 | 2023-Q2 | 1 | 0.8 | 0.8 | 0 |
| 4 | 2023-Q3 | 1 | 0.8 | 1.0 | **+0.2** |
| 5 | 2023-Q4 | 3 | 0.8 | 0.8 | 0 |
| 6 | 2024-Q1 | 4 | 0.4 | 0.6 | **+0.2** |
| 7 | 2024-Q2 | 5 | 0.4 | 0.4 | 0 |
| 8 | 2024-Q3 | 4 | 0.8 | 0.8 | 0 |
| 9 | 2024-Q4 | 5 | 0.8 | 1.0 | **+0.2** |
| 10 | 2025-Q1 | 5 | 1.0 | 1.0 | 0 |
| 11 | 2025-Q4 | 4 | 0.8 | 0.8 | 0 |

The gain is **3 folds × one row each**. No fold gets worse. The gain is not concentrated in one fold, but it is also not broad: 8 of the 11 folds are unchanged.

### 4.2 The three rows MODEL-B2 changes [DATA]

| Quarter | Province | Actual | Baseline P(HIGH) | MODEL-B2 P(HIGH) | Stress score |
|---|---|---|---:|---:|---:|
| 2023-Q3 | Rizal | HIGH | 0.446 | 0.621 | 14.94 |
| 2024-Q1 | Batangas | HIGH | 0.497 | 0.621 | 16.78 |
| 2024-Q4 | Cavite | HIGH | 0.415 | 0.562 | 21.97 |

These are the **only** predictions that change, and none goes from right to wrong. All three are HIGH rows that the baseline scored just below 0.50, so the class weight moved them across the cut-off.

This is the expected effect of reweighting toward the minority class: it adds no new information. On average, MODEL-B2 raises P(HIGH) by 0.062 across all rows.

Errors by province:

| | Batangas | Cavite | Laguna | Quezon | Rizal | Total |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 2 | 4 | 3 | 1 | 3 | 13 |
| MODEL-B2 | 1 | 3 | 3 | 1 | 2 | 10 |

The full row-by-row table is in Appendix A (`outer_test_rows_55.csv` also carries the feature values).

### 4.3 Year results

| Year | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|
| Baseline | 0.80 | 0.85 | 0.60 | 0.90 |
| MODEL-B2 | 0.80 | 0.90 | **0.70** | 0.90 |

## 5. Baseline comparison [DATA]

All figures are on the same 55 outer-test rows.

| | MODEL-B baseline | MODEL-B2 |
|---|---:|---:|
| Correct / incorrect | 42 / 13 | 45 / 10 |
| Mean fold accuracy | 0.7636 | 0.8182 |
| Weighted precision | 0.8081 | 0.8413 |
| Weighted recall | 0.7636 | 0.8182 |
| Weighted F1 | 0.7650 | 0.8200 |
| ROC-AUC | 0.8244 | 0.8278 |

**Paired comparison:** MODEL-B2 is right and the baseline wrong on 3 rows; the reverse happens on 0 rows.

- Exact McNemar test: p = 0.25.
- Quarter-cluster bootstrap 95% interval for the difference: [0.000, +0.109].

**Interpretation:** the improvement is consistent in direction (it never hurts), but 3 rows are **too few to establish it statistically**.

## 6. Persistence comparison (H3, kept separate from the 75% criterion)

Two persistence references are reported:

- **Naive persistence:** the province's label at quarter t. This is optimistic, because under strict Rule 3 the SWS round for quarter t is usually published only after t+1 has begun.
- **Timing-valid persistence:** the province's latest label whose SWS round was published before t+1 began.

The two references disagree on 10 of the 55 rows.

| | Baseline | MODEL-B2 | Persistence (naive) | Persistence (timing-valid) |
|---|---:|---:|---:|---:|
| Correct / incorrect | 42 / 13 | 45 / 10 | 44 / 11 | 42 / 13 |
| Mean fold accuracy | 0.7636 | 0.8182 | 0.8000 | 0.7636 |
| Weighted precision | 0.8081 | 0.8413 | 0.8080 | 0.7810 |
| Weighted recall | 0.7636 | 0.8182 | 0.8000 | 0.7636 |
| Weighted F1 | 0.7650 | 0.8200 | 0.8016 | 0.7660 |
| By year (2022 / 2023 / 2024 / 2025) | 0.80 / 0.85 / 0.60 / 0.90 | 0.80 / 0.90 / 0.70 / 0.90 | 0.60 / 0.80 / 0.80 / 0.90 | 0.80 / 0.80 / 0.65 / 0.90 |

| Pair | Rows A right, B wrong | Rows B right, A wrong | McNemar p | Bootstrap 95% CI of difference |
|---|---:|---:|---:|---|
| MODEL-B2 vs naive persistence | 4 | 3 | 1.00 | [−0.091, +0.109] |
| MODEL-B2 vs timing-valid persistence | 6 | 3 | 0.51 | [−0.036, +0.145] |
| Baseline vs naive persistence | 3 | 5 | 0.73 | [−0.164, +0.073] |

**Conclusion for H3:**

- **Naive persistence:** MODEL-B2 beats it by **1 observation**. That is neither statistically nor practically meaningful.
- **Timing-valid persistence:** the margin is 3 rows, still not statistically meaningful.

**The data are too few to establish that MODEL-B2 is a better forecaster than persistence.** This is separate from the 75% criterion. Clearing 75% does not imply H3.

## 7. Price-level dependency stress test

Every variant below uses the same folds and seed and the same `scale_pos_weight` rule; only the feature columns differ. Nothing here replaces MODEL-B2.

The feature groups are:

- **Price levels:** `rice_price_regular`, `rice_price_regular_lag1`, `food_cpi`, `headline_cpi`, and the five `commodity_*` series. Fuel and FX levels are added in some variants: `diesel_php_per_l`, its lag 1, `gasoline_php_per_l`, `brent_usd_per_bbl`, `fx_usd_php_avg`.
- **Transformations already in Chapter III:** `food_cpi_yoy` (with its lag and accel), `cpi_dev`, `food_minus_headline_yoy` (with its lag and accel), `rice_price_regular_accel` and `diesel_php_per_l_accel`. No new transformation was constructed.

| Variant | Features | Correct | Mean acc | F1 | AUC | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A.** MODEL-B2, all features | 47 | 45 | **0.818** | 0.820 | 0.828 | 0.80 | 0.90 | 0.70 | 0.90 |
| **B.** Without food price levels (fuel/FX levels and transforms kept) | 38 | 31 | 0.564 | 0.567 | 0.627 | 0.20 | 0.65 | 0.45 | 0.80 |
| **B′ = C.** Without any price level; transformed prices kept | 33 | 33 | 0.600 | 0.604 | 0.618 | 0.20 | 0.75 | 0.45 | 0.80 |
| **B″.** Without any price variable | 24 | 42 | 0.764 | 0.765 | 0.784 | 0.80 | 0.80 | 0.75 | 0.70 |

Removing the levels while keeping their methodology-supported transformations (B′) is the same feature set as "transformed price features only" (C), so the two coincide.

Fold accuracy for each variant:

| Variant | 22-Q4 | 23-Q1 | 23-Q2 | 23-Q3 | 23-Q4 | 24-Q1 | 24-Q2 | 24-Q3 | 24-Q4 | 25-Q1 | 25-Q4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.8 | 1.0 | 0.8 | 1.0 | 0.8 | 0.6 | 0.4 | 0.8 | 1.0 | 1.0 | 0.8 |
| B | 0.2 | 1.0 | 0.4 | 0.8 | 0.4 | 0.2 | 0.4 | 0.8 | 0.4 | 0.8 | 0.8 |
| B′ = C | 0.2 | 1.0 | 0.6 | 0.8 | 0.6 | 0.2 | 0.4 | 0.8 | 0.4 | 0.8 | 0.8 |
| B″ | 0.8 | 0.8 | 0.8 | 1.0 | 0.6 | 0.4 | 0.8 | 1.0 | 0.8 | 0.6 | 0.8 |

With default LightGBM (no class weight), the same feature sets score 0.673 (B), 0.655 (B′ = C) and 0.727 (B″).

**[DATA] What this shows:**

- The 81.8% **depends heavily on price-level features**: removing them costs 12–14 correct rows.
- The result is also **fragile to which price columns are present**. Keeping the price transformations without the levels (B′ = C) does worse than dropping prices altogether (B″).
- With only 55 test rows, accuracy swings between 56% and 82% depending on the feature set. A score this sensitive to feature choice should not be read as a stable property of the method.
- The 2022 collapse to 0.20 in B and B′ comes from the 2022-Q4 fold, which has a single HIGH row: the class weight pushes 4 LOW rows over the cut-off.

## 8. Temporal-trend diagnostic

This is described as **potential temporal-trend dependence**, not leakage: every value was published before the forecast quarter.

**[DATA] Correlation with the time index** (Spearman, on the 95 paired rows):

| Feature (MODEL-B2 gain rank) | Gain share | ρ with time |
|---|---:|---:|
| 1. rice_price_regular | 0.251 | 0.547 |
| 2. commodity_rootcrops | 0.197 | 0.302 |
| 3. commodity_livestock | 0.101 | 0.577 |
| 4. FSSI_lag2 | 0.067 | 0.348 |
| 5. headline_cpi | 0.064 | **0.995** |
| 6. unemployment_rate_lag1 | 0.051 | −0.354 |
| 7. commodity_fruit_veg | 0.036 | 0.270 |
| 8. rice_price_regular_lag1 | 0.034 | 0.656 |
| 9. food_cpi | 0.032 | **0.917** |
| 10. food_cpi_yoy_lag1 | 0.022 | 0.321 |

Weighted by gain, the mean |ρ| across the top 10 is 0.50.

**[DATA] The label itself trends by year.** HIGH share by target year:

| Year | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| HIGH share | 0.53 | 0.20 | 0.20 | 0.45 | 0.95 | 0.80 |

The price levels by year are in `price_levels_by_year.csv`. Rice rose from 34.8 in 2022 to 46.2 in 2024, the same pattern as the label.

**[DATA] A clock-only reference.** LightGBM was given one feature, the quarter index, under the identical protocol and weighting rule:

| Model | Mean acc | F1 | AUC | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Time index only | **0.782** | 0.784 | **0.886** | 0.80 | 0.75 | 0.75 | 0.90 |
| Time index + SWS known | 0.782 | 0.784 | 0.893 | 0.80 | 0.75 | 0.75 | 0.90 |
| MODEL-B2 (47 features) | 0.818 | 0.820 | 0.828 | 0.80 | 0.90 | 0.70 | 0.90 |

A tree cannot extrapolate past the latest quarter it has seen, so the time-only model simply carries forward the most recent training regime. It **clears 75% without any food-security information.** MODEL-B2 agrees with it on 85.5% of the 55 rows and is ahead by only 2 correct rows.

**[DATA] Within-year signal.** Each level was centred on its target-year mean, removing the year-to-year trend, and its AUC for separating HIGH from LOW was recomputed:

| Feature | Raw AUC | Within-year AUC |
|---|---:|---:|
| rice_price_regular | 0.813 | 0.637 |
| headline_cpi | 0.719 | 0.524 |
| food_cpi | 0.732 | 0.640 |
| commodity_rootcrops | 0.621 | 0.626 |
| commodity_livestock | 0.439 | 0.412 |

- **Rice and the CPI levels mostly carry between-year (time) information.** Their AUC falls sharply once the year trend is removed; headline CPI drops to near chance.
- **`commodity_rootcrops` works differently.** It keeps its signal inside each year, because it separates **provinces** (see Section 9).

**[DATA] Conclusion:** there is strong evidence of potential temporal-trend dependence. A substantial part of MODEL-B2's accuracy is achievable from "which period is it" alone. This does not invalidate the evaluation, which is timing-valid, but the 81.8% cannot be read as evidence that the price features causally anticipate food stress.

## 9. CPI-derived feature limitation

**[DATA] Construction of each price variable:**

| Feature | Through 2021 | 2022 onward | Construction | Timing-valid? | Interpretation |
|---|---|---|---|---|---|
| `commodity_fruit_veg`, `_leafy_veg`, `_livestock`, `_poultry`, `_rootcrops` | Observed PSA NRP retail prices (2012-based series, quarterly mean of monthly) | **Derived.** First affected quarter: **2022-Q1** | price(q) = price(2021-Q4, province, item) × (1 + food CPI YoY(q, province)/100), in `backend/fix_primary_data.py` (`fix_commodity_prices`). This is **not cumulative**. | **Yes.** Under strict Rule 3 the model sees quarter t−1, which needs CPI of t−1 (published early in t) and a 2021-Q4 anchor. | **Changes meaning.** Correlation with the province's food CPI YoY is **1.000** for every province and group from 2022 on. Each series is a rescaled food-inflation rate, multiplied by a fixed province anchor, not a price. |
| `rice_price_regular` | 2020: PSA OpenStat retail RMR (psa_indicators) | 2021 onward: observed **PSA wholesale** RMR (table 0052M4AWB01) | Observed series; wholesale replaces retail from 2021 | Yes (t−1) | **Observed, but with a series break.** Wholesale runs about PHP 3–6/kg below retail (the source note says so), so 2020 vs 2021+ levels are not like-for-like. Since the earliest test quarter is 2022-Q4, the break affects only training rows. |
| `food_cpi`, `headline_cpi` | PSA CPI (2018=100) | Same | Observed index levels | Yes (t−1) | Observed. As levels of an index, they rise almost monotonically (ρ with time 0.92–0.995). |
| `diesel_*`, `gasoline_*`, `brent_*`, `fx_usd_php_avg` | DOE / EIA / ECB | Same | Observed | Yes (t−1) | Observed |

What the data show:

1. **[DATA] No commodity variable is temporally invalid.** Each uses only information released before the forecast quarter, so there is **no leakage**.
2. **[LIMITATION] From 2022 on, `commodity_*` carries no price information.** It duplicates food CPI YoY, scaled by a province-specific 2021-Q4 anchor. Across provinces, the anchor makes it a stable **province identifier**. That is why `commodity_rootcrops` separates Rizal and Batangas (high anchor) from Cavite, Laguna and Quezon (Section 10).
3. **[LIMITATION] Construction break at 2021 → 2022.** The series changes from observed prices to derived values.
4. **[LIMITATION] Rice changes from retail to wholesale in 2021.**
5. **[LIMITATION] Zero-filled first quarter.** In the timing-valid diagnostic frame, the first feature quarter for each province (2020-Q1) has its government series shifted to t−1 and filled with 0 instead of left missing. This affects 5 training rows and no test row. It is an implementation detail of the diagnostic frame, not a timing violation, and it is left unchanged here so that MODEL-B2 stays frozen.
6. **[ADVISER]** The variables are **not removed**. Whether they may still be described as "commodity prices" in Chapter IV, or must be described as "CPI-scaled commodity indices after 2021", is a documentation decision for the adviser.

## 10. 2024 error analysis (no tuning, nothing removed)

**[DATA] Class distribution and accuracy:**

| Quarter | Rows | HIGH | MODEL-B2 accuracy |
|---|---:|---:|---:|
| 2024-Q1 | 5 | 4 | 0.6 |
| 2024-Q2 | 5 | 5 | 0.4 |
| 2024-Q3 | 5 | 4 | 0.8 |
| 2024-Q4 | 5 | 5 | 1.0 |

19 of the 20 rows in 2024 are HIGH. Before 2024, 20 of 65 training rows (31%) were HIGH.

**[DATA] 2024-Q1 and 2024-Q2 predictions:**

| Quarter | Province | Actual | MODEL-B2 | P(HIGH) | Baseline P | Top contributions (log-odds) |
|---|---|---|---|---:|---:|---|
| Q1 | Cavite | HIGH | LOW ✗ | 0.145 | 0.078 | rice +0.85, livestock −0.54, rootcrops −0.41, poultry −0.38 |
| Q1 | Laguna | HIGH | LOW ✗ | 0.259 | 0.135 | rice +0.85, livestock −0.54, rootcrops −0.40, poultry −0.38 |
| Q1 | Quezon | LOW | LOW ✓ | 0.221 | 0.131 | rice +0.85, livestock −0.54, rootcrops −0.40 |
| Q1 | Rizal | HIGH | HIGH ✓ | 0.867 | 0.783 | **rootcrops +1.93**, rice +0.85 |
| Q1 | Batangas | HIGH | HIGH ✓ | 0.621 | 0.497 | **rootcrops +1.96**, rice +0.85 |
| Q2 | Cavite | HIGH | LOW ✗ | 0.381 | 0.236 | rice +0.95, rootcrops −0.79, fruit_veg +0.68 |
| Q2 | Laguna | HIGH | LOW ✗ | 0.446 | 0.378 | rice +1.11, rootcrops −0.80 |
| Q2 | Quezon | HIGH | LOW ✗ | 0.248 | 0.209 | rice +1.19, rootcrops −0.57 |
| Q2 | Rizal | HIGH | HIGH ✓ | 0.984 | 0.961 | **rootcrops +1.62**, rice +1.13 |
| Q2 | Batangas | HIGH | HIGH ✓ | 0.949 | 0.898 | **rootcrops +1.41**, rice +1.16 |

**[DATA] SWS available when each forecast was issued:**

| Target quarter | Latest SWS round published | SWS value known | SWS of the target quarter |
|---|---|---:|---:|
| 2024-Q1 | 2023-Q3 | 10.3 | 15.3 |
| 2024-Q2 | 2023-Q4 | 14.3 | 19.6 |
| 2024-Q3 | 2024-Q1 | 15.3 | 18.1 |
| 2024-Q4 | 2024-Q2 | 19.6 | 25.3 |

**[DATA] Distribution shift of 2024 test rows against pre-2024 training rows:**

| Feature | SMD | Share of 2024 rows outside training range |
|---|---:|---:|
| enso_numeric | 2.41 | 0.75 |
| rice_price_regular_accel | 1.65 | 0.45 |
| rice_price_regular | 1.24 | 0.90 |
| rainfall_anomaly_pct | −0.99 | 0.25 |
| sws_hunger | 0.83 | 0.25 |
| drought_alert | 0.75 | 0.75 (training never saw an alert) |
| commodity_livestock | 0.48 | 0 |
| commodity_rootcrops | 0.34 | 0 |
| food_cpi_yoy | −0.14 | 0 |

**Attribution of the errors:**

| Candidate cause | Supported? | Evidence |
|---|---|---|
| Target shift | **Yes, primary** | 95% HIGH in 2024 against 31% HIGH in training. MODEL-B2's mean P(HIGH) in Q1 is 0.42 and rises only as more 2024 rows enter training. |
| SWS release timing | **Yes** | The jump (10.3 → 15.3 → 19.6) was published two rounds late. At the Q1 forecast the model saw 10.3, which is a normal value. |
| Insufficient historical examples | **Yes** | Only 10 of 65 training rows had SWS ≥ 15. There was no earlier comparable shock to learn from. |
| Province pattern from CPI-derived `commodity_rootcrops` | **Yes** | Rizal and Batangas are correct because of a +1.4 to +2.0 rootcrops contribution. Every miss is in Cavite, Laguna or Quezon, where rootcrops pulls toward LOW. This reflects the 2021-Q4 anchor (Section 9), not a price signal. |
| Rice-price shift | **Did not cause the misses** | 90% of 2024 rice values lie outside the training range, but the rice contribution is positive (+0.85 to +1.19) for every province. It pushed toward HIGH. |
| ENSO / drought shift | **Not a driver** | These values are outside or never seen in training, so trees cannot use them. Neither appears among the top contributions. |

No 2024 quarter was removed, and nothing was tuned on 2024.

## 11. Uncertainty of 81.8% [DATA]

| Quantity | Value |
|---|---|
| Point estimate | **81.8%** (45/55; pooled and mean fold are equal because every fold has 5 rows) |
| Outer-test observations | **55**, in 11 quarters × 5 provinces |
| Wilson 95% interval | **69.7% – 89.8%** |
| Clopper–Pearson exact 95% interval | 69.1% – 90.9% |
| Quarter-cluster bootstrap 95% (11 quarters resampled) | 70.9% – 90.9% |
| One-sided exact test, H0: accuracy ≤ 75% | p = 0.155 |
| Baseline 76.4% (42/55), Wilson 95% | 63.7% – 85.6% |

**Interpretation:**

- 81.8% is an **imprecise** estimate. One row is worth 1.8 points, and the 95% interval runs roughly from 70% to 90%.
- The lower end is below 75%, and the data do not reject a true accuracy of 75% or less.
- The rows are not independent. The five provinces in a quarter share SWS, ENSO and national series, so the effective sample is closer to 11 than to 55. The cluster bootstrap reflects this.

## 12. Algorithm 4 diagnostic (criterion unchanged; holdout unchanged)

**Saved results:** holdout F1 is 0.80 under all three class settings, and AUC is 0.50 / 0.50 / 0.444.

**[DATA] Holdout composition:**

- 20 rows over 2024-Q3, 2024-Q4, 2025-Q1 and 2025-Q4: 18 HIGH and **2 LOW**.
- AUC is computed over only 2 × 18 = 36 HIGH–LOW pairs, so it moves in steps of 0.028. Each LOW row decides half the score.
- The two LOW rows:

| Row | SWS of the target quarter | Stress score | Below threshold by |
|---|---:|---:|---:|
| Cavite 2024-Q3 | 18.1 | 13.90 | 0.70 |
| Batangas 2025-Q4 | 16.7 | 13.06 | 1.54 |

- Both rows sit in **high-hunger quarters**. They are LOW only because the province's food CPI ran below the regional mean in the target quarter. That information is not observable at forecast time.

**Ruling out alternatives:**

| Candidate cause | Finding |
|---|---|
| **Holdout composition** | **Primary.** With 2 LOW rows, random scores give AUC = 0.50 ± 0.22 (SD), and 10.7% of random scorings reach AUC ≥ 0.80. The known-SWS feature scores AUC 0.50 because it is constant within a quarter. |
| Model probabilities | **Contributing.** The model ranks both LOW rows high (0.65–0.98 across settings). It cannot separate them because the deciding information is a cross-sectional CPI deviation in the target quarter, which is not yet known. The walk-forward MODEL-B2 probabilities on the same 20 rows also give a low AUC (0.333; baseline 0.472). |
| Class imbalance | **Not the cause.** Default, balanced and `scale_pos_weight` settings all fail. Training is 39% HIGH; the holdout is 90% HIGH. |
| Training procedure | **Not the cause.** All three settings with 100 TPE trials reach CV F1 0.78–0.81 and holdout F1 0.80, and the trees are non-degenerate. |
| Implementation | **Not the cause.** AUC recomputed by counting pairs by hand matches sklearn exactly. The holdout is the last four target quarters, as specified. |

**[METHOD] / [ADVISER]** The criterion (F1 ≥ 0.75 **and** AUC ≥ 0.80 on the holdout) was not changed, and the holdout was not moved. Under Section 3.4.4, Algorithm 4 currently produces no publishable configuration. Whether an AUC computed on 2 LOW rows is an informative acceptance test is a question for the adviser. It was not altered here.

## 13. 45 vs 12 features

- **[DATA] MODEL-B2 uses the 45-feature reading** (the 45 candidates from Section 3.3.2.6, plus CPI_dev and SWS).
- **[DATA] The Equation 5 set of 12 features, under the same protocol:**

| Feature set | Correct | Mean acc | F1 | AUC | 2022 / 2023 / 2024 / 2025 |
|---|---:|---:|---:|---:|---|
| 12 features, default LightGBM | 38 | 0.691 | 0.688 | 0.758 | 0.80 / 0.75 / 0.55 / 0.80 |
| 12 features, `scale_pos_weight` rule | 41 | 0.745 | 0.748 | 0.789 | 0.80 / 0.80 / 0.65 / 0.80 |
| 12 features + SWS known, `scale_pos_weight` rule | 41 | 0.745 | 0.748 | 0.847 | 0.80 / 0.85 / 0.60 / 0.80 |
| MODEL-B2, 47 features | 45 | 0.818 | 0.820 | 0.828 | 0.80 / 0.90 / 0.70 / 0.90 |

  - The 12-feature version is worse by 4 rows (−7.3 points) under the same weighting, and by 7 rows with defaults. In both cases it falls below 75%.
  - Given Section 7, much of the 47-feature advantage comes from price levels with potential temporal-trend dependence. The 12-feature set contains no levels.
- **[METHOD] The manuscript contradicts itself.** Chapter III describes 45 features at lines 1418, 1462, 1775 and 1930, and 12 features at lines 1164, 1685, 1781–1782, 1817 and 1825. Section 3.3.2.7 is missing.
- **[ADVISER]** This is a documentation and methodology issue, separate from MODEL-B2's statistical robustness. It was **not resolved here**, and Chapter III was not edited.

## 14. Limitations

What the data demonstrate:

- 45/55 correct, exactly reproducible, timing-valid, with no leakage.
- A 3-row improvement over the baseline, none of it at the baseline's expense.
- No demonstrated advantage over persistence.
- A wide uncertainty interval (69.7%–89.8%).

Limitations:

1. A time-index-only model reaches 78.2%. MODEL-B2's lead over a pure clock is 2 rows.
2. The result depends heavily on price levels (56–60% without them) and is fragile to feature-set changes.
3. Commodity series from 2022 are CPI-YoY-derived and act as province identifiers.
4. Rice changes from retail to wholesale in 2021.
5. 2024 accuracy is 70%. Nearly all 2024 rows are HIGH, and the hunger jump reached the model late because of SWS release timing.
6. The effective sample is about 11 quarters, and the label threshold is a global median.
7. Eight variants were compared on the same test folds in the optimization phase. E2 passed a pre-registered rule, but some selection optimism remains.
8. Diagnostic frame: the first quarter's government series are zero-filled (5 training rows only).

Methodological issues:

- The 45-vs-12 contradiction, with Section 3.3.2.7 missing.
- Algorithm 4's AUC test is applied to a holdout with 2 LOW rows.
- The 75% criterion is a point-estimate threshold that a trend-only reference also clears on this sample.

**[ADVISER] Decisions that need adviser approval:**

1. Which feature reading governs: 45 or 12.
2. Whether Algorithm 4's non-publication rule blocks reporting MODEL-B2.
3. Whether to report the 81.8% together with its interval and the time-only and persistence references. Recommended: yes.
4. How to describe the post-2021 commodity variables.
5. Whether H3 is reported as not supported, or as inconclusive.

## 15. Final recommendation

**Classification: B. PROMISING BUT NEEDS METHODOLOGY CLARIFICATION**

Why it is **not A (ROBUST CANDIDATE)**:

- The 95% interval reaches 69.7%.
- The gain over the baseline is 3 rows (p = 0.25).
- There is no demonstrated advantage over persistence.
- A clock-only reference reaches 78.2%.
- Removing price levels drops accuracy to 56–60%.
- Algorithm 4 fails its AUC criterion.

Why it is **not C (NOT DEFENSIBLE) or D (INVALID)**:

- The evaluation is timing-valid, with no leakage found.
- The result reproduces exactly.
- The improvement passed a rule fixed before the run, made no right prediction wrong, and comes from a fixed training-only formula rather than a search.

The 81.8% is a legitimate measured result under Chapter III's stated Algorithm 3 criterion.

What can be defended in the thesis:

- "Under strict-timing walk-forward evaluation, MODEL-B2 classified 45 of 55 province-quarters correctly (81.8%; 95% CI 69.7–89.8%)."
- That statement must be accompanied by:
  - the persistence references (80.0% naive, 76.4% timing-valid);
  - the time-only reference (78.2%);
  - the price-level dependence;
  - the 2024 result (70%);
  - the Algorithm 4 failure.

What cannot be defended on this evidence:

- that MODEL-B2 beats persistence (H3);
- that the price features drive the forecasts causally;
- that 81.8% is a precise estimate;
- that the thesis passes because 81.8% > 75%.

Production stays on MODEL-A. MODEL-B2 is not deployed, and the 81.8% result is preserved as recorded.

---

## Appendix A. The 55 outer-test predictions

Feature values are as the model saw them under strict timing. "SWS known" is the latest round published before the forecast quarter. Full feature columns are in `outer_test_rows_55.csv`.

| Fold | Forecast quarter | Province | Actual | MODEL-B2 | P(HIGH) | Correct | Baseline | Persistence (timing-valid) | rice_price_regular | commodity_rootcrops | SWS known | FSSI_lag2 |
|---:|---|---|---|---|---:|---|---|---|---:|---:|---:|---:|
| 1 | 2022-Q4 | Cavite | LOW | LOW | 0.331 | yes | LOW | LOW | 31.44 | 57.72 | 11.7 | 0.396 |
| 1 | 2022-Q4 | Laguna | LOW | LOW | 0.453 | yes | LOW | LOW | 36.40 | 57.28 | 11.7 | 0.378 |
| 1 | 2022-Q4 | Quezon | LOW | LOW | 0.453 | yes | LOW | LOW | 36.87 | 59.31 | 11.7 | 0.647 |
| 1 | 2022-Q4 | Rizal | HIGH | LOW | 0.453 | **no** | LOW | HIGH | 38.38 | 65.44 | 11.7 | 0.352 |
| 1 | 2022-Q4 | Batangas | LOW | LOW | 0.331 | yes | LOW | HIGH | 32.80 | 70.83 | 11.7 | 0.717 |
| 2 | 2023-Q1 | Cavite | LOW | LOW | 0.102 | yes | LOW | LOW | 32.76 | 58.43 | 9.6 | 0.396 |
| 2 | 2023-Q1 | Laguna | LOW | LOW | 0.082 | yes | LOW | LOW | 39.50 | 57.99 | 9.6 | 0.378 |
| 2 | 2023-Q1 | Quezon | LOW | LOW | 0.473 | yes | LOW | LOW | 37.47 | 60.05 | 9.6 | 0.647 |
| 2 | 2023-Q1 | Rizal | LOW | LOW | 0.414 | yes | LOW | LOW | 34.47 | 66.25 | 9.6 | 0.352 |
| 2 | 2023-Q1 | Batangas | LOW | LOW | 0.431 | yes | LOW | HIGH | 33.23 | 71.70 | 9.6 | 0.717 |
| 3 | 2023-Q2 | Cavite | LOW | LOW | 0.303 | yes | LOW | LOW | 34.80 | 60.67 | 11.3 | 0.396 |
| 3 | 2023-Q2 | Laguna | LOW | LOW | 0.068 | yes | LOW | LOW | 35.22 | 60.21 | 11.3 | 0.378 |
| 3 | 2023-Q2 | Quezon | LOW | LOW | 0.418 | yes | LOW | LOW | 37.41 | 62.35 | 11.3 | 0.647 |
| 3 | 2023-Q2 | Rizal | HIGH | LOW | 0.298 | **no** | LOW | HIGH | 33.90 | 68.79 | 11.3 | 0.352 |
| 3 | 2023-Q2 | Batangas | LOW | LOW | 0.231 | yes | LOW | LOW | 33.52 | 74.45 | 11.3 | 0.717 |
| 4 | 2023-Q3 | Cavite | LOW | LOW | 0.144 | yes | LOW | LOW | 35.94 | 61.34 | 8.7 | 0.396 |
| 4 | 2023-Q3 | Laguna | LOW | LOW | 0.046 | yes | LOW | LOW | 34.92 | 60.88 | 8.7 | 0.362 |
| 4 | 2023-Q3 | Quezon | LOW | LOW | 0.416 | yes | LOW | LOW | 38.34 | 63.04 | 8.7 | 0.648 |
| 4 | 2023-Q3 | Rizal | HIGH | HIGH | 0.621 | yes | LOW (fixed by B2) | LOW | 35.30 | 69.55 | 8.7 | 0.352 |
| 4 | 2023-Q3 | Batangas | LOW | LOW | 0.369 | yes | LOW | LOW | 34.52 | 75.28 | 8.7 | 0.717 |
| 5 | 2023-Q4 | Cavite | LOW | LOW | 0.123 | yes | LOW | LOW | 36.04 | 59.57 | 11.3 | 0.396 |
| 5 | 2023-Q4 | Laguna | HIGH | LOW | 0.075 | **no** | LOW | LOW | 36.15 | 59.11 | 11.3 | 0.362 |
| 5 | 2023-Q4 | Quezon | LOW | LOW | 0.127 | yes | LOW | LOW | 39.12 | 61.21 | 11.3 | 0.648 |
| 5 | 2023-Q4 | Rizal | HIGH | HIGH | 0.885 | yes | HIGH | HIGH | 35.66 | 67.53 | 11.3 | 0.352 |
| 5 | 2023-Q4 | Batangas | HIGH | HIGH | 0.809 | yes | HIGH | LOW | 37.52 | 73.09 | 11.3 | 0.717 |
| 6 | 2024-Q1 | Cavite | HIGH | LOW | 0.145 | **no** | LOW | LOW | 38.88 | 59.77 | 10.3 | 0.863 |
| 6 | 2024-Q1 | Laguna | HIGH | LOW | 0.259 | **no** | LOW | LOW | 44.17 | 59.32 | 10.3 | 0.362 |
| 6 | 2024-Q1 | Quezon | LOW | LOW | 0.221 | yes | LOW | LOW | 40.78 | 61.42 | 10.3 | 0.352 |
| 6 | 2024-Q1 | Rizal | HIGH | HIGH | 0.867 | yes | HIGH | HIGH | 40.17 | 67.77 | 10.3 | 0.352 |
| 6 | 2024-Q1 | Batangas | HIGH | HIGH | 0.621 | yes | LOW (fixed by B2) | LOW | 42.86 | 73.34 | 10.3 | 0.717 |
| 7 | 2024-Q2 | Cavite | HIGH | LOW | 0.381 | **no** | LOW | LOW | 37.29 | 57.66 | 14.3 | 0.786 |
| 7 | 2024-Q2 | Laguna | HIGH | LOW | 0.446 | **no** | LOW | HIGH | 43.12 | 57.22 | 14.3 | 0.362 |
| 7 | 2024-Q2 | Quezon | HIGH | LOW | 0.248 | **no** | LOW | LOW | 40.14 | 59.25 | 14.3 | 0.352 |
| 7 | 2024-Q2 | Rizal | HIGH | HIGH | 0.984 | yes | HIGH | HIGH | 43.92 | 65.37 | 14.3 | 0.352 |
| 7 | 2024-Q2 | Batangas | HIGH | HIGH | 0.949 | yes | HIGH | HIGH | 47.19 | 70.75 | 14.3 | 0.816 |
| 8 | 2024-Q3 | Cavite | LOW | HIGH | 0.831 | **no** | HIGH | HIGH | 42.07 | 56.71 | 15.3 | 0.434 |
| 8 | 2024-Q3 | Laguna | HIGH | HIGH | 0.696 | yes | HIGH | HIGH | 46.99 | 56.28 | 15.3 | 0.362 |
| 8 | 2024-Q3 | Quezon | HIGH | HIGH | 0.670 | yes | HIGH | LOW | 53.50 | 58.27 | 15.3 | 0.352 |
| 8 | 2024-Q3 | Rizal | HIGH | HIGH | 0.916 | yes | HIGH | HIGH | 46.47 | 64.29 | 15.3 | 0.352 |
| 8 | 2024-Q3 | Batangas | HIGH | HIGH | 0.972 | yes | HIGH | HIGH | 49.86 | 69.59 | 15.3 | 0.816 |
| 9 | 2024-Q4 | Cavite | HIGH | HIGH | 0.562 | yes | LOW (fixed by B2) | HIGH | 47.75 | 57.89 | 19.6 | 0.434 |
| 9 | 2024-Q4 | Laguna | HIGH | HIGH | 0.582 | yes | HIGH | HIGH | 46.48 | 57.45 | 19.6 | 0.689 |
| 9 | 2024-Q4 | Quezon | HIGH | HIGH | 0.618 | yes | HIGH | HIGH | 54.80 | 59.48 | 19.6 | 0.352 |
| 9 | 2024-Q4 | Rizal | HIGH | HIGH | 0.834 | yes | HIGH | HIGH | 46.44 | 65.63 | 19.6 | 0.686 |
| 9 | 2024-Q4 | Batangas | HIGH | HIGH | 0.862 | yes | HIGH | HIGH | 47.93 | 71.03 | 19.6 | 0.816 |
| 10 | 2025-Q1 | Cavite | HIGH | HIGH | 0.777 | yes | HIGH | HIGH | 46.16 | 56.99 | 19.6 | 0.434 |
| 10 | 2025-Q1 | Laguna | HIGH | HIGH | 0.729 | yes | HIGH | HIGH | 46.49 | 56.55 | 19.6 | 0.744 |
| 10 | 2025-Q1 | Quezon | HIGH | HIGH | 0.951 | yes | HIGH | HIGH | 43.38 | 58.56 | 19.6 | 0.352 |
| 10 | 2025-Q1 | Rizal | HIGH | HIGH | 0.950 | yes | HIGH | HIGH | 45.25 | 64.61 | 19.6 | 0.686 |
| 10 | 2025-Q1 | Batangas | HIGH | HIGH | 0.952 | yes | HIGH | HIGH | 47.89 | 69.92 | 19.6 | 0.816 |
| 11 | 2025-Q4 | Cavite | HIGH | HIGH | 0.624 | yes | HIGH | HIGH | 35.45 | 56.68 | 24.0 | 0.588 |
| 11 | 2025-Q4 | Laguna | HIGH | HIGH | 0.930 | yes | HIGH | HIGH | 36.42 | 56.25 | 24.0 | 0.770 |
| 11 | 2025-Q4 | Quezon | HIGH | HIGH | 0.968 | yes | HIGH | HIGH | 38.73 | 58.24 | 24.0 | 0.525 |
| 11 | 2025-Q4 | Rizal | HIGH | HIGH | 0.946 | yes | HIGH | HIGH | 34.55 | 64.26 | 24.0 | 1.125 |
| 11 | 2025-Q4 | Batangas | LOW | HIGH | 0.964 | **no** | HIGH | HIGH | 37.54 | 69.55 | 24.0 | 0.378 |

## Appendix B. Evidence files (`evidence/2026-10-08_b2_robustness/`)

| File | Contents |
|---|---|
| `MODEL_B2_FROZEN_CONFIG.json` | Frozen configuration, with hashes of the config, the input frame and the scripts |
| `robustness_results.json` | Every number in this report |
| `outer_test_rows_55.csv` | Row-level predictions for the baseline, MODEL-B2 and both persistence references, with feature values |
| `fold_comparison.csv` | Section 4.1 |
| `price_stress_predictions.csv` | Section 7 predictions |
| `time_trend_correlation.csv`, `price_levels_by_year.csv` | Section 8 |
