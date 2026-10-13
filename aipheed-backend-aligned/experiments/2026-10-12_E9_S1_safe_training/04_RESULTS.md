# E9 Results (primary run `runs/20261012T140816Z`)

**Sample:**

- 7 test quarters × 5 provinces = 35 province-quarters.
- Every arm is evaluated on the same 35 rows; no row was INSUFFICIENT_DATA.
- **Independent information is about 7 quarters,** not 35 rows: the five provinces share one regional SWS value per quarter.

**Truth at τ0 = 10.8433:**

| Period | Quarters | HIGH / LOW |
|---|---|---|
| Selection | 2023-Q4 to 2024-Q4 | 23 / 2 |
| Final | 2025-Q1, 2025-Q4 | 10 / 0 |
| All | 7 quarters | **33 / 2** |

**Both LOW cases are Quezon** (2023-Q4 and 2024-Q1): one province, consecutive quarters.

**Probabilities are uncalibrated.** The calibration rule was never met (fewer than 8 inner quarters in every fold).

## 1. Event classification and probabilities (all 7 quarters)

| Arm (output) | Acc. | Bal. acc. | Recall HIGH | Recall LOW | Pred. H/L | Brier | ROC/PR-AUC |
|---|---|---|---|---|---|---|---|
| B1 carry-forward (stress) | 0.886 | 0.939 | 0.879 | 1.000 | 29/6 | — | not meaningful |
| B2 regional (stress) | 0.857 | 0.689 | 0.879 | 0.500 | 30/5 | — | not meaningful |
| B3 Eq.3 origin rule (stress) | 0.886 | 0.939 | 0.879 | 1.000 | 29/6 | — | not meaningful |
| **B4 always majority (HIGH)** | **0.943** | 0.500 | 1.000 | 0.000 | 35/0 | — | — |
| M1 core (probability) | 0.971 | 0.985 | 0.970 | 1.000 | 32/3 | 0.029 | not meaningful |
| M1 core (stress) | 0.943 | 0.970 | 0.939 | 1.000 | 31/4 | — | not meaningful |
| M2 compact (probability) | 0.914 | 0.955 | 0.909 | 1.000 | 30/5 | 0.054 | not meaningful |
| M2 compact (stress) | 0.943 | 0.970 | 0.939 | 1.000 | 31/4 | — | not meaningful |
| M3 expanded (probability) | 0.943 | 0.970 | 0.939 | 1.000 | 31/4 | 0.051 | not meaningful |
| M3 expanded (stress) | 0.971 | 0.985 | 0.970 | 1.000 | 32/3 | — | not meaningful |

**Notes on the table:**

- **ROC-AUC and PR-AUC** were withheld because only 2 LOW rows exist (fewer than 5 per class).
- **Brier** is computed only for probability outputs.
- **F1 for HIGH:** 0.921 (B2) to 0.985 (M1 probability, M3 stress); always-HIGH B4 scores 0.971.
- **F1 for LOW:** 0.286 (B2), 0.5 (B1, B3), 0.571 to 0.8 (M arms); undefined for B4. These rest on **2 LOW rows**. Per-class precision and recall are in `metrics.json`.
- **Selection period (25 rows):** M1 probability accuracy 0.960, balanced accuracy 0.978; B1 0.840 / 0.913; B4 0.920 / 0.500.
- **Final period (10 rows, all HIGH):** every arm scores 1.000; balanced accuracy is undefined.

**Reading.** Every arm, including the trivial "always HIGH" rule (0.943), exceeds 75% accuracy, because 94% of the outcomes are HIGH. Balanced accuracy separates arms only through the 2 Quezon LOW cases. Carry-forward (B1) also gets both right. Mean M1 probabilities are 0.98–0.99 from 2024-Q2 onward (uncalibrated).

## 2. Continuous stress forecasts (the informative comparison)

| Arm | MAE, selection (5 q) | MAE, final (2 q) | MAE, all | RMSE, all | Regional-level error, all | Within-quarter concordant share (ranking by predicted stress) |
|---|---|---|---|---|---|---|
| B1 carry-forward | 4.667 | 6.600 | 5.219 | 6.755 | 5.000 | **0.614** |
| B2 regional | 4.615 | **4.098** | **4.467** | **5.870** | 4.157 | 0.500 (no ranking) |
| B3 Eq.3 origin rule | 4.667 | 4.250 | 4.548 | 5.917 | 4.157 | **0.614** |
| **M1 core** | **4.004** | 5.867 | 4.537 | 6.114 | 4.460 | 0.536 |
| M2 compact | 4.723 | 6.511 | 5.234 | 7.336 | 5.137 | 0.464 |
| M3 expanded | 4.036 | 6.965 | 4.873 | 6.796 | 4.702 | 0.536 |

**Per-quarter MAE:**

| Arm | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q4 |
|---|---|---|---|---|---|---|---|
| B1 | 3.00 | 5.00 | 5.30 | 4.34 | 5.70 | 5.90 | 7.30 |
| B2 | 3.71 | 5.00 | 5.30 | 3.36 | 5.70 | 5.90 | 2.30 |
| B3 | 3.00 | 5.00 | 5.30 | 4.34 | 5.70 | 5.90 | 2.60 |
| M1 | 2.41 | 3.55 | 4.05 | 3.91 | 6.09 | 4.72 | 7.01 |
| M2 | 1.83 | 3.45 | 4.85 | 5.97 | 7.51 | 6.20 | 6.82 |
| M3 | 1.74 | 3.94 | 4.11 | 3.80 | 6.58 | 6.43 | 7.50 |

**Quarter-cluster bootstrap** of the mean per-quarter MAE difference: 2,000 draws, 7 clusters. The interval is unstable at this size. It was computed post hoc with the pre-specified method (deviation D2).

| Comparison | Mean difference | 95% interval | Quarters lower |
|---|---|---|---|
| M1 − B1 | **−0.683** | [−1.110, −0.198] | 6/7 |
| M1 − B2 | +0.069 | [−1.101, 1.781] | 4/7 |
| M1 − B3 | −0.011 | [−1.094, 1.527] | 5/7 |
| M2 − B1 | +0.014 | [−0.817, 0.981] | 4/7 |
| M3 − B1 | −0.346 | [−0.962, 0.277] | 4/7 |
| B2 − B1 | −0.752 | [−2.284, 0.204] | 3/7 |
| B3 − B1 | −0.671 | [−2.014, 0.000] | 1/7 |

## 3. By province (MAE over the 7 quarters)

| Arm | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|
| B1 | 3.64 | 4.94 | **11.15** | 2.68 | 3.70 |
| B2 | 3.01 | 4.30 | 8.33 | 3.12 | 3.58 |
| B3 | 3.49 | 4.59 | 8.76 | 2.95 | 2.96 |
| M1 | 2.00 | 4.67 | 10.25 | 2.44 | 3.32 |
| M2 | 1.96 | 4.96 | 11.84 | 3.41 | 4.00 |
| M3 | 2.38 | 4.20 | 10.84 | 3.31 | 3.63 |

Province codes follow `labels.parquet`: PH040100000 Cavite, PH040200000 Laguna, PH040300000 Quezon, PH040400000 Rizal, PH040500000 Batangas.

**Quezon dominates the error.** Its provincial component moved from the lowest (2023) to the highest (2024–2025).

**Provincial spread** (max − min predicted stress within a quarter vs the true spread):

| | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q4 |
|---|---|---|---|---|---|---|---|
| True | 8.27 | 6.53 | 9.93 | 12.60 | 12.53 | 14.67 | 6.53 |
| B1 / B3 | 10.67 | 10.87 | 8.27 | 6.53 | 9.93 | 12.60 | 14.67 / 6.93 |
| M1 | 8.40 | 9.47 | 0.62 | 1.06 | **0.00** | **0.00** | 2.05 |
| M3 | 8.27 | 8.32 | 3.37 | 3.87 | 0.91 | 3.59 | 4.26 |

**From 2024-Q2 onward the selected M1 predicts nearly the same stress for all five provinces.** It does not produce meaningful provincial differences.

## 4. Selection (rule fixed in the protocol; selection quarters only)

| Step | MAE ratio | Quarters better | Moved? |
|---|---|---|---|
| B2 vs B1 | 0.989 | 2/5 | no |
| B3 vs B1 | 1.000 | 0/5 | no |
| **M1 vs B1** | **0.858** | **4/5** | **yes** |
| M2 vs M1 | 1.179 | 2/5 | no |
| M3 vs M1 | 1.008 | 2/5 | no |

**Selected by the rule: M1 core.** On the final period, M1's MAE (5.87) is lower than B1's (6.60) but **higher than B2 (4.10) and B3 (4.25)**. Interpretation is in `06_MODEL_SELECTION.md`.
