# E11 Results Summary (run `20261012T145620Z`)

**Basis:** 7 test quarters (2023-Q4 to 2025-Q4), 35 province rows, about 7 independent regional observations. Outcomes at τ0: **33 HIGH, 2 LOW** (both LOW are Quezon).

**All 7 quarters were used in E1–E9. These results are exploratory.** No row was INSUFFICIENT_DATA.

## 1. Stress forecasts: main candidates (expanding window)

| Candidate | MAE | RMSE | Bias | MAE, 2023-Q4 to 2024-Q4 | MAE, 2025 | Concordant share |
|---|---|---|---|---|---|---|
| B1 carry-forward | 5.219 | 6.755 | −2.91 | 4.667 | 6.600 | 0.614 |
| B2 regional hunger | 4.467 | 5.870 | −4.16 | 4.615 | 4.098 | 0.500 |
| **B3 S1 rule** | **4.548** | **5.917** | −4.16 | 4.667 | 4.250 | **0.614** |
| Nested direct core | 4.790 | 6.237 | −2.77 | 4.359 | 5.867 | 0.529 |
| Nested direct core_plus | 5.294 | 6.918 | −3.28 | — | — | 0.436 |
| Nested direct compact | 5.659 | 7.690 | −3.69 | — | — | 0.457 |
| Nested direct expanded | 5.192 | 6.959 | −3.05 | — | — | 0.521 |
| Nested decomposed (provincial d) | 4.598 | 6.323 | −4.28 | 4.718 | 4.298 | **0.707** |
| **Nested residual (S1 rule + LightGBM correction)** | **3.743** | **5.420** | −2.53 | 3.787 | 3.634 | 0.629 |

**Rolling 8-quarter window (nested):**

| Candidate | MAE |
|---|---|
| core | 4.496 |
| core_plus | 5.105 |
| compact | 5.076 |
| expanded | 4.786 |
| decomposed | 4.435 |
| residual | 4.018 |

Baselines are unchanged under the rolling window, except B4.

## 2. Comparison with each baseline

Mean per-quarter MAE difference (candidate − baseline), with the quarter-cluster bootstrap 95% interval and the number of quarters better, out of 7. **Negative = better.**

| Candidate (window) | vs carry-forward | vs regional | vs S1 rule |
|---|---|---|---|
| Direct core (expanding) | **−0.43 [−0.78, −0.08], 6/7** | +0.32 [−0.83, +1.89], 4/7 | +0.24 [−0.72, +1.71], 5/7 |
| Direct core (rolling) | −0.72 [−1.33, −0.16], 5/7 | +0.03 [−0.85, +1.04], 3/7 | −0.05 [−0.75, +0.84], 4/7 |
| Direct core_plus | +0.07 [−0.47, +0.65], 3/7 | +0.83 [−0.49, +2.27], 2/7 | +0.75 [−0.28, +1.99], 2/7 |
| Direct compact | +0.44 [−0.46, +1.59], 3/7 | +1.19 [−0.30, +2.75], 2/7 | +1.11 [−0.17, +2.56], 2/7 |
| Direct expanded | −0.03 [−0.42, +0.38], 4/7 | +0.72 [−0.48, +2.33], 3/7 | +0.64 [−0.38, +2.16], 4/7 |
| Decomposed (expanding) | −0.62 [−2.21, +0.63], 5/7 | +0.13 [−0.57, +0.89], 4/7 | +0.05 [−0.45, +0.72], 5/7 |
| **Residual (expanding)** | **−1.48 [−2.79, −0.17], 5/7** | −0.72 [−2.18, +0.48], 3/7 | **−0.80 [−2.20, +0.29], 4/7** |
| Residual (rolling) | −1.20 [−2.55, +0.14], 5/7 | −0.45 [−1.78, +0.72], 3/7 | −0.53 [−1.79, +0.55], 4/7 |
| S1 rule (B3) | −0.67 [−2.01, 0.00], 1/7 (6 ties) | +0.08 [−0.26, +0.46], 3/7 | — |

**Where the residual model's advantage over the S1 rule comes from.** Per-quarter differences: −0.24, +0.43, +0.06, −0.49, **−4.15**, **−2.36**, +1.13. The gain is concentrated in **two peak quarters (2024-Q4, 2025-Q1)**, and the model is worse at the 2025-Q4 downturn. It learned to push the S1 rule upward. That helped while stress was rising and hurt when it fell.

**Overfitting** (mean training MAE vs test MAE):

| Model | Training MAE | Test MAE |
|---|---|---|
| Direct models | 1.3–2.5 | 4.5–5.7 |
| Residual | 1.2–2.4 | 3.6–3.9 |

## 3. Classification at τ0 (all 7 quarters, 35 rows)

| Arm | Output | Accuracy | Balanced acc. | HIGH P / R / F1 | LOW P / R / F1 | Confusion (TH-PH, TH-PL, TL-PH, TL-PL) | Brier |
|---|---|---|---|---|---|---|---|
| B4 always majority | Class | **0.943** | 0.500 | 0.943 / 1.000 / 0.971 | – / 0.000 / – | 33, 0, 2, 0 | — |
| B1 carry-forward | Stress → class | 0.886 | 0.939 | 1.000 / 0.879 / 0.935 | 0.333 / 1.000 / 0.500 | 29, 4, 0, 2 | — |
| B2 regional | Stress → class | 0.857 | 0.689 | 0.967 / 0.879 / 0.921 | 0.200 / 0.500 / 0.286 | 29, 4, 1, 1 | — |
| B3 S1 rule | Stress → class | 0.886 | 0.939 | 1.000 / 0.879 / 0.935 | 0.333 / 1.000 / 0.500 | 29, 4, 0, 2 | — |
| Nested residual | Stress → class | 0.914 | 0.955 | 1.000 / 0.909 / 0.952 | 0.400 / 1.000 / 0.571 | 30, 3, 0, 2 | — |
| Nested decomposed | Stress → class | 0.886 | 0.939 | 1.000 / 0.879 / 0.935 | 0.333 / 1.000 / 0.500 | 29, 4, 0, 2 | — |
| Nested direct core | Stress → class | 0.971 | 0.985 | 1.000 / 0.970 / 0.985 | 0.667 / 1.000 / 0.800 | 32, 1, 0, 2 | — |
| Nested classifier, core | Uncalibrated probability | 0.971 | 0.985 | 1.000 / 0.970 / 0.985 | 0.667 / 1.000 / 0.800 | 32, 1, 0, 2 | 0.030 |
| Nested classifier, compact | Uncalibrated probability | 0.971 | 0.985 | 1.000 / 0.970 / 0.985 | 0.667 / 1.000 / 0.800 | 32, 1, 0, 2 | 0.058 |

TH = true HIGH, TL = true LOW, PH = predicted HIGH, PL = predicted LOW.

**Not meaningful here:**

- **ROC-AUC and PR-AUC:** withheld for every arm (2 LOW < 5).
- **Calibration:** never supportable.

**Reading the classification table:**

- **Every arm except the regional rule finds both LOW rows.** The arms differ only in how many of the 33 HIGH rows they call LOW (1 to 4).
- **Balanced accuracy differences (0.939 vs 0.985) therefore come from 1–3 HIGH rows plus the same 2 LOW rows.**
- **"Always HIGH" reaches 94.3% accuracy with no ability to detect LOW.** Accuracy cannot rank these models.

## 4. Prespecified recommendation rule (nested candidates vs the S1 rule)

| Candidate | ≥ 5/7 better | Mean < 0 and upper < 0 | Ranking ≥ S1 | Rolling same sign | Decision |
|---|---|---|---|---|---|
| Direct core | ✔ | ✘ | ✘ | ✔ | not met |
| Direct core_plus | ✘ | ✘ | ✘ | ✘ | not met |
| Direct compact | ✘ | ✘ | ✘ | ✘ | not met |
| Direct expanded | ✘ | ✘ | ✘ | ✘ | not met |
| Decomposed | ✔ | ✘ | ✔ | ✔ | not met |
| Residual | ✘ (4/7) | ✘ (upper +0.29) | ✔ | ✔ | not met |

**Decision: no LightGBM candidate meets the rule. The S1 rule stays primary; LightGBM stays experimental.**
