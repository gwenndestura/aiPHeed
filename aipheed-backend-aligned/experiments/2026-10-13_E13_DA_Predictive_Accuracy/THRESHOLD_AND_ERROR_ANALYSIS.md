# Threshold and Error Analysis (E13)

**Source.** `runs/20261013T022702Z/metrics.json`, `scored_rows.csv` and `quarter_event_tables.csv`.

**Status of these results.** They are retrospective, on quarters examined before.

## 1. Thresholds used

**No threshold was tuned.** All were fixed in the protocol before the run.

| Target | Event | Threshold | Basis | Positives / n |
|---|---|---|---|---|
| A | Hunger rises against the latest published value | forecast > H_last | Direction call; SWS hunger has no official level threshold | **8 / 9** |
| B1 | Provincial food inflation above 4% | 4.0% | Upper bound of the 2–4% inflation target (headline, used as an external reference) | 20 / 55 |
| B2 | Province above the five-province mean | D > 0 | Sign of relative pressure | 24 / 55 |

**S1 τ0 (10.84335)** is diagnosed in `CURRENT_MODEL_DIAGNOSIS.md` and was not re-estimated.

**INSUFFICIENT_DATA:** 0 test rows. All five provinces had T−2 data in every test quarter, and H_age was 1 or 2.

**Calibration** is not applicable, because no arm outputs probabilities.

## 2. Target A: regional hunger (9 quarters, 2023-Q4..2025-Q4)

| Arm | MAE | RMSE | Bias | Increase events: TP/FP/FN/TN | Balanced accuracy | ROC-AUC |
|---|---|---|---|---|---|---|
| **A_cf (carry-forward)** | **4.77** | 5.22 | −3.02 | 0/0/8/1 | 0.50 | 0.50 |
| A_mean | 6.74 | 7.75 | −6.74 | 1/0/7/1 | 0.56 | 1.00 |
| A_ridge_H | 6.57 | 7.39 | −3.95 | 3/1/5/0 | 0.19 | 0.00 |
| A_ridge_HF | 6.58 | 7.42 | −3.90 | 3/1/5/0 | 0.19 | 0.00 |

**Errors by quarter** (absolute error, A_cf):

| Quarter | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 |
|---|---|---|---|---|---|---|---|---|---|
| Error | 3.0 | 5.0 | 5.3 | 2.8 | 5.7 | 5.9 | 7.85 | 6.8 | 0.55 |

**Reading:**

1. **Every arm under-forecast the 2024–2025 rise.**
   - The carry-forward bias is −3.0 points. Hunger rose against the two-quarter-old value in 8 of 9 quarters.
   - The ridge models learned **negative** slopes from the 2021–2023 training data, which fluctuated around 10–11%. They forecast about 10.4% in 2024-Q2 and 2024-Q3, when the realized values were 19.6% and 18.1%. When the rise entered the training data, their slopes turned strongly positive and they **over-forecast** 2025-Q2 (28.0 against 16.15).
   - This is the behaviour of a regression fitted on too few points across a level shift.
2. **The event results rest on one negative case** (2025-Q2), so ROC-AUC values of 0.00 and 1.00 carry almost no information.
3. **The sensitivity S-A1** (production rounds only, 7 quarters) gives the same order. Carry-forward MAE is 5.00; the ridge models are 7.73.

## 3. Target B1: provincial food inflation (55 rows, 11 quarters, 2023-Q2..2025-Q4)

| Arm | MAE | RMSE | Bias | F > 4%: TP/FP/FN/TN | Balanced accuracy | Precision / recall (above 4%) | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|
| **B1_cf** | **2.44** | 3.19 | +1.50 | 16/14/4/21 | **0.70** | 0.53 / 0.80 | 0.74 | 0.70 |
| B1_regional | 2.48 | 3.15 | +1.50 | 13/22/7/13 | 0.51 | 0.37 / 0.65 | 0.70 | 0.69 |
| B1_mean | 2.73 | 3.01 | +1.38 | 20/35/0/0 | 0.50 | 0.36 / 1.00 | 0.56 | 0.43 |
| B1_pmean | 2.97 | 3.30 | +1.69 | 20/35/0/0 | 0.50 | 0.36 / 1.00 | 0.47 | 0.43 |
| B1_ridge_F | 2.52 | 2.81 | +1.21 | 20/33/0/2 | 0.53 | 0.38 / 1.00 | 0.64 | 0.47 |
| B1_ridge_FR | 2.64 | 2.92 | +1.21 | 15/30/5/5 | 0.45 | 0.33 / 0.75 | 0.55 | 0.43 |
| B1_tree | 2.75 | 3.10 | +1.66 | 17/29/3/6 | 0.51 | 0.37 / 0.85 | 0.71 | 0.62 |

**Reading:**

- **All arms over-forecast** (bias +1.2 to +1.7 points), because provincial food inflation fell from the 2023 highs. The falling trend is the largest single component of the error.
- **Carry-forward has the lowest MAE and the best event balance.** It has 14 false alarms (above-4% forecast, not realized) and 4 misses.
- **The trained arms barely use the latest value.** The ridge slope on F(T−2) is only 0.002–0.25 in raw units, so B1_ridge_F is close to the training mean.
- **The largest quarterly error** was 2024-Q1 (carry-forward MAE 5.5 points). The 2023-Q3 values (8.6–13.0%) were carried forward, but the realized values were −0.2 to 3.1%.

## 4. Target B2: relative provincial food-price pressure (55 rows)

| Arm | MAE | RMSE | D > 0: TP/FP/FN/TN | Balanced accuracy | ROC-AUC | PR-AUC | Mean Kendall τ |
|---|---|---|---|---|---|---|---|
| B2_zero | 1.37 | 1.78 | 0/0/24/31 | 0.50 | 0.50 | 0.44 | — |
| **B2_cf** (best baseline) | **1.355** | 1.85 | 16/9/8/22 | 0.69 | 0.76 | 0.77 | 0.40 |
| B2_pmean | 1.55 | 2.09 | 8/14/16/17 | 0.44 | 0.42 | 0.47 | −0.11 |
| B2_ridge_D | 1.19 | 1.62 | 16/9/8/22 | 0.69 | 0.76 | 0.77 | 0.40 |
| **B2_ridge_DP** | **1.18** | 1.63 | 16/8/8/23 | **0.70** | **0.80** | **0.80** | **0.45** |
| B2_tree | 1.42 | 1.92 | 16/9/8/22 | 0.69 | 0.67 | 0.68 | 0.47 |

**Reading:**

- **The largest errors in every arm are 2024-Q2 and 2024-Q3** (about 2.1–2.6 points). Quezon swung from D ≈ −2.3 to +3.6, and Batangas, Cavite and Rizal moved the other way. No input available at T−2 anticipated that reversal.
- **B2_ridge_D gives the same sign calls as carry-forward,** because its forecast is 0.53–0.78 × D(T−2). It differs only in **magnitude**, which lowers MAE. **For a DA user who reads only "above or below the regional average", it adds nothing.**
- **B2_ridge_DP changes 3 of 55 sign calls against carry-forward:**
  - 2 corrected: Rizal 2024-Q2 and Laguna 2025-Q3;
  - 1 lost: Batangas 2023-Q2.

  Two of the three changes are forecasts within 0.05 points of zero. The net effect is one fewer false alarm.

## 5. Practical meaning of the errors

| Target | Typical error (MAE) | Against what scale |
|---|---|---|
| A | 4.8 points of hunger prevalence (carry-forward) | Regional hunger ranged 8.7–25.3% in 2021–2025 |
| B1 | 2.4 percentage points of food inflation (carry-forward) | Provincial food inflation in test quarters averaged 3.7–4.7% by province |
| B2 | 1.2–1.4 points of relative pressure | The within-quarter spread of D was 1.4–7.3 points |

**These forecasts are made at the start of the target quarter.** Official values arrive later:

- provincial CPI about 3 weeks after the quarter ends;
- SWS hunger about 1–15 weeks after the fieldwork.

The forecast therefore gains roughly 3–6 months over the official figure. Its errors are large compared with the quarter-to-quarter changes DA would act on.
