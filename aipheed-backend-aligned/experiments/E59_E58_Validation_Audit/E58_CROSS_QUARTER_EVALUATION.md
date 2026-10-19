# E58 cross-quarter evaluation (frozen protocol; no retuning)

**Source:** `runner/a3_evaluate.py` → `out/evaluation.json`, `out/per_quarter_EW.csv`, `out/per_province_EW.csv`, `E58_QUARTERLY_PREDICTIONS.csv`.

**Rows:** 50 province-quarters, 10 target quarters (2024-Q2..2026-Q3), two quarters ahead.
- 18 HIGH, 32 LOW, 10 onsets.
- E58-EW "predicts HIGH" when it issues any warning (ALERT or EMERGING). Its probability is P_price.

**Independence:** the 5 provinces of a quarter share the regional hunger value and most national inputs. The effective sample is closer to **10 quarters** than to 50 rows, and the onsets form **4 episodes**.

## 1. Pooled

| Model | Acc [quarter-bootstrap 95% CI] | Bal | HIGH prec / rec | LOW prec / rec | F1 | Brier | AUC | TP/TN/FP/FN |
|---|---|---|---|---|---|---|---|---|
| **E58-EW** | **0.78** [0.70, 0.86] | **0.78** | 0.667 / 0.778 | 0.862 / 0.781 | 0.718 | 0.182 | 0.786 | 14/25/7/4 |
| E56 | 0.72 [0.58, 0.86] | 0.684 | 0.625 / 0.556 | 0.765 / 0.812 | 0.588 | 0.214 | 0.649 | 10/26/6/8 |
| Price projection rule | 0.74 [0.68, 0.80] | 0.748 | 0.609 / 0.778 | 0.852 / 0.719 | 0.683 | 0.188 | 0.788 | 14/23/9/4 |
| Persistence | 0.56 [0.40, 0.74] | 0.535 | 0.400 / 0.444 | 0.667 / 0.625 | 0.421 | – | – | 8/20/12/10 |
| Majority class (LOW) | 0.64 [0.44, 0.82] | 0.500 | – / 0 | 0.640 / 1 | 0 | 0.360 | – | 0/32/0/18 |

**Calibration of E58-EW's probability (P_price):**
- CITL −0.10: forecasts about 10 points too high on average.
- Slope 0.75: over-confident.
- Reliability by bin:

| Forecast bin | Observed HIGH share |
|---|---|
| 0.0–0.2 | 0.27 |
| 0.2–0.4 | 0.00 |
| 0.4–0.6 | 0.40 |
| 0.6–0.8 | 0.40 |
| 0.8–1.0 | 0.82 |

## 2. Per quarter (E58-EW)

| Target (issued) | n | HIGH | TP/TN/FP/FN | Acc | Bal | HIGH prec / rec | LOW prec / rec | Brier | AUC | E56 acc | Projection acc | Persistence acc | Majority acc | Stress | Onsets warned |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-Q2 (2024-01-01) | 5 | 4 | 4/0/1/0 | 0.8 | 0.50 | 0.80 / 1.00 | – / 0.00 | 0.19 | 0.25 | **0.2** | 0.8 | 0.2 | 0.2 | rising | 4 of 4 |
| 2024-Q3 | 5 | 1 | 1/2/2/0 | 0.6 | 0.75 | 0.33 / 1.00 | 1.00 / 0.50 | 0.17 | 1.00 | 0.6 | 0.8 | 0.6 | 0.8 | falling | – |
| 2024-Q4 | 5 | 3 | 1/2/0/2 | 0.6 | 0.67 | 1.00 / 0.33 | 0.50 / 1.00 | 0.32 | 0.67 | 0.6 | 0.6 | 0.4 | 0.4 | rising | 1 of 3 |
| 2025-Q1 | 5 | 4 | 3/1/0/1 | 0.8 | 0.88 | 1.00 / 0.75 | 0.50 / 1.00 | 0.16 | 1.00 | 0.8 | 0.8 | 1.0 | 0.2 | stable | – |
| 2025-Q2 | 5 | 3 | 3/1/1/0 | 0.8 | 0.75 | 0.75 / 1.00 | 1.00 / 0.50 | 0.19 | 0.83 | 0.8 | 0.8 | 0.6 | 0.4 | rising | 2 of 2 |
| 2025-Q3 | 5 | 2 | 2/1/2/0 | 0.6 | 0.67 | 0.50 / 1.00 | 1.00 / 0.33 | 0.22 | 0.83 | 0.6 | 0.6 | 0.8 | 0.6 | falling | – |
| 2025-Q4 | 5 | 0 | 0/5/0/0 | 1.0 | – | – | 1.00 / 1.00 | 0.08 | – | 1.0 | 0.6 | 0.2 | 1.0 | falling | – |
| 2026-Q1 | 5 | 0 | 0/5/0/0 | 1.0 | – | – | 1.00 / 1.00 | 0.09 | – | 1.0 | 0.8 | 0.4 | 1.0 | falling | – |
| 2026-Q2 | 5 | 1 | 0/4/0/1 | 0.8 | 0.50 | – / 0.00 | 0.80 / 1.00 | 0.19 | 0.25 | 0.8 | 0.8 | 0.4 | 0.8 | falling | 0 of 1 |
| 2026-Q3 | 5 | 0 | 0/4/1/0 | 0.8 | – | 0.00 / – | 1.00 / 0.80 | 0.20 | – | 0.8 | 0.8 | 1.0 | 1.0 | stable | – |

**Quarter-level summary:**

| Statistic | Value |
|---|---|
| mean | 0.78 |
| median | 0.80 |
| SD | 0.15 |
| range | 0.6–1.0 |
| quarters ≥ 0.75 | **7 of 10** |

**What the per-quarter results show:**
- 0.78 is **not uniform**. Three quarters are at 0.6, and two "perfect" quarters (2025-Q4, 2026-Q1) had no HIGH row; always-LOW matches them.
- Within-quarter AUC is computable in only 6 quarters. It reaches 0.25 in 2024-Q2 and 2026-Q2: in those quarters the model ranked the one LOW (or the one HIGH) province wrongly.

## 3. Per province (10 rows each; descriptive)

| Province | HIGH | Acc | HIGH prec / rec | FP | FN | Onsets warned | E56 acc |
|---|---|---|---|---|---|---|---|
| Quezon | 6 | 0.9 | 0.86 / 1.00 | 1 | 0 | 2 of 2 | 0.8 |
| Laguna | 5 | 0.8 | 0.80 / 0.80 | 1 | 1 | 2 of 3 | 0.7 |
| Batangas | 3 | 0.8 | 0.67 / 0.67 | 1 | 1 | 2 of 2 | 0.7 |
| Rizal | 0 | 0.9 | – / – | 1 | 0 | – | 1.0 |
| **Cavite** | 4 | **0.5** | 0.40 / 0.50 | 3 | 2 | 1 of 3 | 0.4 |

## 4. Stress periods

Direction = number of HIGH provinces at the target vs the latest known quarter.

| Stratum | Rows | Onsets | E58-EW acc | Onsets warned | E56 acc | Projection acc | Majority acc |
|---|---|---|---|---|---|---|---|
| Rising | 15 | 9 | 0.733 | 7 | 0.533 | 0.733 | 0.333 |
| Stable | 10 | 0 | 0.80 | – | 0.80 | 0.80 | 0.60 |
| Falling | 25 | 1 | 0.80 | 0 | 0.80 | 0.72 | **0.84** |
| **2024-Q2 only** | 5 | 4 | 0.80 | 4 | 0.20 | 0.80 | 0.20 |
| **Excluding 2024-Q2** | 45 | 6 | 0.778 | 3 | **0.778** | 0.733 | 0.689 |

## 5. False alarms and missed HIGH cases (`E58_RISING_STRESS_CASE_REVIEW.csv`)

**7 false alarms:**
- 2024-Q2 Rizal (EMERGING);
- 2024-Q3 Cavite, Laguna;
- 2025-Q2 Cavite;
- 2025-Q3 Batangas, Cavite;
- 2026-Q3 Quezon.

All but one are ALERTs the E56 model also issued. They are price pressure that was forecast but did not materialise.

**4 missed HIGH rows:**
- 2024-Q4 Cavite and Laguna (both onsets);
- 2025-Q1 Batangas (not an onset);
- 2026-Q2 Cavite (onset; food YoY 4.73 against a threshold of 4.71).

All four are price-part misses.

## 6. Answer

E58-EW reaches **0.78 pooled accuracy** and 7 of 10 quarters at or above 0.75, with balanced HIGH and LOW detection (0.778 / 0.781).

This **conceals two things:**
- the whole difference from E56 is one quarter (2024-Q2);
- accuracy varies from 0.6 to 1.0 between quarters, with the 1.0 quarters having no HIGH row.

Excluding 2024-Q2, E58-EW and E56 are identical (0.778).
