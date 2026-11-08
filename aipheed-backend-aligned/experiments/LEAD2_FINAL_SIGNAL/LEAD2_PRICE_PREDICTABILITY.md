# Lead 2 price predictability (PROTOCOL_LEAD2_FINAL_SIGNAL §1)

**Sources.** Data: `out/study.json`, `out/method_rows.csv`, `out/folds_methods.csv`. Runner: `runner/final_signal.py study`.

**What is forecast.** The official label's price component, provincial price pressure: HIGH if the food margin mf = F − TH_F > 0 or the gap margin mg = F − HL − TH_G > 0. This is **a food-price-pressure proxy, not observed food insecurity**.

**Information used.** Only what was known at O(t).
- σ and ρ come from each method's own earlier out-of-sample errors with known outcomes. A test checks that no error used has a target at or after the origin.
- The ridge is fitted only on rows with outcomes known before the origin.

**Splits.**

| | Lead-2 rows | HIGH quarters |
|---|---|---|
| DEV (targets ≤ 2024-Q4) | 35 | 4 |
| CONF (targets 2025-Q2 to 2026-Q3) | 30 | 3 |

## 1. The series itself

**Crossing rate.** How often the target-quarter price condition differs from the last condition known at issue (quarter t−1):

| | Lead 1 | Lead 2 |
|---|---|---|
| Crossing rate | 0.39 | **0.48** |
| Rate near threshold (\|max margin\| < 1 pp) | 0.47 | 0.35 |
| Rate when clearly separated | 0.34 | 0.56 |
| Share of crossings that are near the threshold | 0.43 | 0.27 |

**At Lead 2 the condition changes about half the time.** Most of these crossings are *not* borderline: they are real moves of more than 1 pp.

**Crossing rate by year (Lead 2):**

| Year | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| Rate | 0.67 | 0.50 | 0.50 | 0.33 | 0.40 |

**Crossing rate by province (Lead 2):**

| Province | Rate |
|---|---|
| Laguna | 0.65 |
| Cavite | 0.53 |
| Quezon | 0.47 |
| Rizal | 0.41 |
| Batangas | 0.35 |

**Persistence.** Autocorrelation of the quarterly food margin:

| Lag (quarters) | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Autocorrelation | 0.60 | 0.33 | **0.05** | −0.10 |

Lag 3 is the distance from the last complete quarter (t−1) to the Lead-2 target (t+2). At that distance **persistence is gone**.

**Seasonality is weak.** Mean change by quarter of year:

| Quarter of year | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| Mean change (pp) | −0.30 | +0.44 | +0.21 | −0.92 |

These changes are small against an error SD of about 2 pp, and they are not used by any method except the seasonal naive.

**Structural breaks are strong.** By year:

| Year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Mean food margin (pp) | −1.3 | +0.1 | +1.0 | −2.6 | −4.3 | −3.6 |
| Price-HIGH share | 0.40 | 0.40 | 0.85 | 0.40 | 0.33 | 0.07 |

The series has regimes (the 2023 surge, the 2024-26 disinflation). It does not have a stable level, trend or seasonal cycle.

## 2. Methods on chronological folds (Lead 2; every forecast made at its own origin)

| Method | DEV rows | DEV margin RMSE | DEV price Brier | DEV price accuracy | DEV T43c Brier | CONF price Brier | CONF T43c Brier |
|---|---|---|---|---|---|---|---|
| M0 CPI projection (Gaussian, own-error σ) | 35 | 2.55 | **0.188** | 0.743 | 0.195 | 0.175 | 0.160 |
| M1 last observation | 35 | 4.30 | 0.251 | 0.571 | 0.160 | 0.205 (25 rows) | 0.190 |
| M2 last condition (binary) | 35 | – | 0.429 | 0.571 | 0.226 | 0.360 (25) | 0.324 |
| M3 seasonal naive | 35 | 5.21 | 0.387 | 0.371 | 0.201 | 0.244 (25) | 0.198 |
| M4 damped trend | 35 | 5.98 | 0.173 | 0.800 | 0.149 | 0.196 (20) | 0.183 |
| M5 ridge (continuous then classify) | **0** (not enough history: the first fit is 2023-Q3, and σ needs 6 earlier errors) | – | – | – | – | 0.310 (20) | 0.284 |
| M6 LightGBM price part (B0) | 35 | – | 0.273 | 0.457 | 0.177 | 0.173 | 0.156 |
| Price climatology | 35 | – | 0.291 | 0.314 | 0.175 | 0.263 | 0.229 |

**Lead 1 (DEV)** for contrast:
- M0 price Brier 0.120 vs LightGBM 0.283.
- T43c Brier: M0 0.124, B0 0.139.

## 3. Answers to the seven questions

1. **Series versus LightGBM.**
   - **Most of the Lead-2 error is in the series.** The price condition changes in 48% of cases and has no persistence at the Lead-2 distance.
   - **LightGBM adds error of its own in development.**
     - Its price part (DEV Brier 0.273) is worse than the projection it is given, when that projection is turned into a probability with its own historical error (0.188).
     - It is worse still at Lead 1 (0.283 vs 0.120).
     - In CONF the two are equal (0.173 vs 0.175).
2. **Crossing rate.** 48% at Lead 2 and 39% at Lead 1.
3. **Where crossings concentrate.**
   - Not near the threshold at Lead 2: only 27% of crossings are borderline.
   - They concentrate in regime changes (2022 rate 0.67; the 2023 surge and the 2024 reversal) and in Laguna and Cavite.
4. **Patterns.**
   - Strong breaks.
   - Persistence only one to two quarters ahead (0.60, 0.33).
   - Negligible seasonality.
   - No stable trend.
5. **Attainable improvement from issue-time information.** Small.
   - The best issue-time methods (M4, M0) reach DEV price Brier 0.17-0.19 against climatology's 0.29.
   - On the T43c target the best method (M4, 0.149) beats B0 (0.177) in DEV, but it does not hold in CONF (0.183 vs 0.156).
6. **Continuous then classify vs direct binary.**
   - Continuous methods with a proper probability (M0, M4) beat the binary methods (M2 last condition 0.429; LightGBM 0.273) on the price label in DEV.
   - The regularized continuous forecaster (M5) could not be tested in DEV because there was too little history. In CONF it is the worst continuous method (0.310).
   - The advantage does not survive conversion to the official T43c label consistently across periods.
7. **Near-threshold vs clearly separated** (Lead 2, 26 near rows):

   | Method | Accuracy, near | Accuracy, separated |
   |---|---|---|
   | M0 | 0.58 | 0.85 |
   | LightGBM | 0.46 | 0.69 |
   | M4 | 0.69 | 0.64 |

   The near-threshold rows are close to chance for every method.

## 4. Consequence for the gated candidates (pre-declared)

| Candidate | Gate | Outcome |
|---|---|---|
| K-A (recent margins) | M1 or M3 must beat M0 on DEV price Brier | Both are worse (0.251, 0.387 vs 0.188). Not fitted. |
| K-B (ridge forecast as input) | M5 must beat M0 and M6 | M5 has no DEV forecasts. Not fitted. |

**M4 is not a candidate.** The damped trend did best on DEV price, but it was not pre-declared as a candidate input.
- Building one now would select on the same DEV results.
- It also fails CONF on the T43c target.
- It is recorded as a hypothesis for a future protocol with a new, untouched confirmation period.
