# E9: Error Analysis, and Why So Many Areas Are HIGH

Sources: `runs/20261012T140816Z`: `diagnostics.json`, `scored_rows.csv`, `post_*.csv`, `folds.json`. All values are from 2021–2025 data.

## 1. Are the forecasts inflated? No. The HIGH share comes from the target.

**Every arm *under*-predicts stress in 2023-Q4 to 2025-Q1.** Mean bias, predicted − true:

| Arm | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q4 |
|---|---|---|---|---|---|---|---|
| B1 carry-forward | −3.00 | −5.00 | −5.30 | −2.80 | −5.70 | −5.90 | **+7.30** |
| B2 regional | −3.00 | −5.00 | −5.30 | −2.80 | −5.70 | −5.90 | −1.40 |
| B3 Eq.3 rule | −3.00 | −5.00 | −5.30 | −2.80 | −5.70 | −5.90 | −1.40 |
| M1 core | −2.29 | −3.47 | −4.05 | −3.58 | −6.09 | −4.72 | **+7.01** |
| M2 compact | −1.18 | −3.42 | −4.85 | −5.97 | −7.51 | −6.20 | +6.82 |
| M3 expanded | −1.08 | −3.94 | −4.11 | −3.27 | −6.58 | −6.43 | +7.50 |

**Mean true stress by quarter:** 14.3, 15.3, 19.6, 18.1, **25.3**, 24.0, 16.7.

**HIGH calls vs truth.** The models predict 30–32 HIGH out of 35, against **33** true HIGH. They call slightly *fewer* HIGH than the target contains.

**Conclusion.** The concentration of HIGH under S1 is a property of the **target**: Balance-Luzon hunger rose in 2024–2025, to quarter means of 15–25 against τ0 = 10.84. It is **not** a forecasting artifact. **No adjustment was made.** Lowering predictions or forcing provinces into LOW would contradict the S1 data.

## 2. Each candidate cause, checked

| Candidate cause | Evidence (E9) | Verdict |
|---|---|---|
| **Scoring formula, α weight** | Test rows HIGH out of 35, with τ recomputed per α as of 2023-10-01: **α = 0 → 35, α = 1 → 35, α = 2 → 33, α = 2.74 → 33, α = 4 → 31** | The provincial weight barely changes the HIGH share. **Not the cause.** |
| **Regional dominance in the formula** | Regional-only call agrees with S1 in **76.2%** of 2021–2025 rows. Variance: total 38.9; SWS 25.4 (**65%**); 2 × deviation 13.5. | The regional SWS level drives HIGH/LOW for all five provinces together. **Main structural cause.** |
| **Training targets** | Labels HIGH at τ0: 2021 8/15, 2022 8/15, 2023 11/20, **2024 19/20, 2025 10/10** | The 2024–25 targets really are nearly all HIGH. **Data, not error.** |
| **Threshold** | τ0 = 10.84 is the 2021–2023 median (a lower-hunger period). The approved 14.345 would label fewer 2024–25 rows HIGH, but it is computed from labels through 2025-Q4, so it is **leaky for 2023–2025 evaluation**. | τ0 is correct for leakage-free evaluation. Using 14.345 prospectively is a separate, already-documented decision. **Not a defect to tune.** |
| **Class imbalance, limited variation** | Training HIGH/LOW grows from 20/20 (first fold) to 51/24 (last). Test: 33/2. The 2 LOW cases are one province (Quezon) in 2 consecutive quarters. | Limits every classification metric. **No rebalancing done** (protocol). |
| **Uncalibrated outputs** | M1 mean probability is 0.98–0.99 for every quarter from 2024-Q2. Calibration was never supportable (< 8 inner quarters). | Probabilities saturate. They are **not** probabilities of food insecurity and must be labelled uncalibrated. |
| **Classification rule (0.50)** | From 2024-Q2 on, every M1 probability is ≥ 0.96, so no cutoff up to 0.95 changes those calls. Only 2023-Q4 and 2024-Q1 have low probabilities (minimum 0.13 and 0.02, both for Quezon). | **Not the cause.** Not changed. |
| **Feature scaling or weights** | LightGBM needs no scaling. Feature weights are learned, not set. | **Not applicable** |
| **Missing or stale evidence** | 0 INSUFFICIENT_DATA rows. No test input missing. SWS age is 2 quarters at every test origin. | **Not the cause** |
| **Earlier production inflation** | The production `label_cpi` (index above its trailing mean) was 100% HIGH in 2024. That is an index-trend artifact found in E5, and it is a separate system. | **Already explained.** Not used in E9. |

## 3. Why the models miss

1. **Lag in a rising, then falling, series.**
   - Inputs are 2 quarters old: SWS age 2, CPI from T−2.
   - Stress climbed through 2024, so every forecast trailed it.
   - In 2025-Q4 stress fell (25.3 → 16.7). Arms anchored on the last published label (B1, M1–M3) **over**-predicted by about 7.
   - B2/B3 used the newer June 2025 SWS round and missed by only 1.4.
2. **Quezon.** Its provincial component swung from the lowest in 2023 to the highest in 2024–2025 (true stress up to 34.5). It carries the largest error for every arm (MAE 8.3–11.8).
3. **Overfitting.** Training MAE 1.3–1.8 vs test MAE 4.5–5.2. Adding features (M2, M3) lowers training error and does **not** lower test error.
4. **Unstable feature use.**
   - M2's top-3 regressor features change across folds (mean pairwise Jaccard 0.54).
   - M3 consistently ranks `unemployment_rate` in its top 2 (Jaccard 0.67). That is plausibly a spurious trend proxy.
   - Poverty was dropped in two folds by the training-only filter.

## 4. Differences between provinces, and why the selected model loses them

- **True within-quarter spread:** 6.5 to 14.7 stress points.
- **B1 and B3 (Eq.3 rule) carry the last published provincial gap forward.** Their ranking agreement is the best (concordant share **0.614**).
- **The selected M1 spreads only 0.0–2.1 points from 2024-Q2 onward.** It forecasts the regional level and drops provincial detail (concordant share 0.536).
- **M2/M3 do not improve the ranking** (0.464 and 0.536).

**What this means:**

- Meaningful provincial differences in E9 come from the **S1 provincial component (relative food-price pressure)**, not from the ML forecast.
- **Cities and municipalities:** no LGU-level SWS or CPI exists, so **no LGU-level S1 target can be computed or validated.** Any municipal map would be an unvalidated allocation. E9 produces none.
