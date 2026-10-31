# E131 numerical forecasting report

## Pre-registered tolerance

**Definition.** tol = 1.645 × SE of the reference quarter. SE comes from the published margin at the observed proportion. Median SE is 1.95 points, so the median tolerance is 3.21 points.

**What 75 % requires.** At least 75 % of predictions inside tolerance needs a forecast error (against the true value) with SD ≤ 1.022 × SE, about **2.0 points**. An oracle would score 90 %.

## Results

These are the shared rows, P-DASH issue. RMSE and R² are in `out/x1_metrics.csv`.

| Lead | Rows / quarters | Best share within | Best MAE | LGBM-ALL within / MAE | PERSIST within / MAE |
|---|---|---|---|---|---|
| 1 | 36 / 9 | 0.44 (PERSIST) | 5.38 (PERSIST) | 0.31 / 6.12 | 0.44 / 5.38 |
| **2** | 28 / 7 | **0.50 (LLM)** | **4.70 (LLM)** | 0.39 / 6.13 | 0.46 / 5.28 |
| 3 | 24 / 6 | 0.67 (NLP-ONLY) | 3.24 (NLP-ONLY) | 0.46 / 5.05 | 0.54 / 4.04 |
| 4 | 20 / 5 | 0.55 (LLM) | 3.52 (LLM) | 0.15 / 6.35 | 0.50 / 3.77 |

**At 75 % within tolerance: not achieved at any lead, by any model, under either issue policy.**

Lead-2 RMSE is 6.5 (LLM) to 7.8 points (LGBM-ALL), roughly 3× the 2-point requirement.

## LLM at Lead 2, by area and by level

| Group | Rows | MAE | Bias | Within |
|---|---|---|---|---|
| Metro Manila | 7 | 2.77 | −1.71 | 0.71 |
| Balance Luzon | 7 | 4.41 | −1.80 | 0.43 |
| Visayas | 7 | 4.93 | −1.51 | 0.43 |
| Mindanao | 7 | 6.68 | −1.48 | 0.43 |
| Low tercile | 10 | 3.77 | +3.77 | — |
| Middle tercile | 9 | 3.16 | −2.19 | — |
| High tercile | 9 | 7.27 | −7.05 | — |

**Sharp increases** (Δ > 2 SE, 7 rows): 0 of 7 inside tolerance. Mean error −9.6, versus −9.7 for persistence.

## Calibration

80 % coverage at Lead 2: LLM 0.86, PERSIST 0.82, LGBM-ALL 0.57.

LLM's intervals are well calibrated at Leads 2–3. On the univariate set they are calibrated at Lead 2 (0.75) and under-cover at Lead 1 (0.61).

## Why the magnitude is not learned to 75 %

The target's **true** quarter-to-quarter changes are several points. The 2024 surge and the 2025–26 oscillation, in particular, are not anticipated by any available predictor.

A model can remove survey noise, which is what LLM does, but it cannot predict an unforeseen shift. The remaining error is about 3× what 75 % agreement requires.
