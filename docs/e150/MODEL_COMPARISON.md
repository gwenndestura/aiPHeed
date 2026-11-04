# Model comparison

All at HIGH ≥ 50 %, Lead 1, on identical rows. Source: `backend/data/e150/out/comparison.json`, `retro_results.json`, `holdout_results.json`.

**Evidence status:** 2018 and 2019 were seen before E150 and chose the arm. 2021 provinces were opened by E148 and E149, so they are **retrospective, never untouched**. E147's values are its stored forecasts re-thresholded at 50 %, on 2021 only.

## Development, 2018 and 2019 (n = 47, always-HIGH 0.809)

| Model | Accuracy | Balanced | HIGH recall | LOW recall | AUC | Brier | MAE (points) | Slope |
|---|---|---|---|---|---|---|---|---|
| **A-H (selected)** | 0.851 | 0.654 | 0.974 | 0.333 | 0.848 | **0.107** | **7.48** | 1.10 |
| A-Hh | 0.830 | 0.598 | 0.974 | 0.222 | 0.836 | 0.109 | 7.55 | 1.08 |
| A-G | 0.851 | 0.696 | 0.947 | 0.444 | 0.792 | 0.122 | 8.81 | 0.96 |
| E149 / E148 model | 0.809 | 0.500 | 1.000 | 0.000 | 0.658 | 0.131 | 8.79 | 0.90 |
| Persistence | 0.787 | 0.487 | 0.974 | 0.000 | 0.601 | 0.139 | 10.26 | 0.51 |
| Drift | 0.745 | 0.588 | 0.842 | 0.333 | 0.583 | 0.171 | 10.92 | 0.45 |

A-H − E149: −0.024 [−0.071, +0.011].

## Retrospective, 2021 (n = 25, always-HIGH 0.80)

| Model | Accuracy | Balanced | HIGH recall | LOW recall | AUC | Brier | MAE | Slope |
|---|---|---|---|---|---|---|---|---|
| A-H (selected) | 0.84 | 0.60 | 1.00 | 0.20 | 0.66 | 0.143 | **6.37** | 0.85 |
| A-G | 0.88 | 0.70 | 1.00 | 0.40 | 0.74 | 0.129 | 7.13 | 0.65 |
| E149 / E148 model | 0.80 | 0.65 | 0.90 | 0.40 | 0.77 | **0.107** | 7.56 | 0.60 |
| E147 | 0.88 | 0.70 | 1.00 | 0.40 | 0.76 | **0.106** | 7.91 | 0.64 |
| Persistence | 0.88 | 0.70 | 1.00 | 0.40 | 0.74 | 0.120 | 9.61 | 0.62 |
| Drift | 0.80 | 0.65 | 0.90 | 0.40 | 0.74 | 0.132 | 7.09 | 0.62 |

**On 2021 alone, E150 is not better on class probabilities.** A-H − persistence +0.023 [+0.003, +0.045], and A-H − E149 +0.037 [−0.008, +0.093]. It does have the lowest prevalence error.

## Pool, 2018 + 2019 + 2021 (n = 72, 58 HIGH; always-HIGH 0.806)

| Model | Accuracy | Balanced | HIGH recall | LOW recall | F1 | AUC | Brier | ECE | MAE | Slope |
|---|---|---|---|---|---|---|---|---|---|---|
| **A-H** | 0.847 | 0.634 | 0.983 | 0.286 | 0.912 | **0.786** | **0.119** | 0.034 | **7.09** | **1.05** |
| A-Hh | 0.833 | 0.599 | 0.983 | 0.214 | 0.905 | 0.778 | 0.121 | 0.040 | 7.19 | 1.03 |
| **A-G** | **0.861** | **0.697** | 0.966 | **0.429** | 0.918 | 0.777 | 0.124 | 0.096 | 8.23 | 0.71 |
| A-GN (news) | 0.861 | 0.697 | 0.966 | 0.429 | 0.918 | 0.757 | 0.131 | 0.056 | n/a | n/a |
| E149 | 0.806 | 0.554 | 0.966 | 0.143 | n/a | 0.686 | 0.123 | 0.068 | 8.36 | 0.79 |
| A-frozen | 0.792 | 0.627 | 0.897 | 0.357 | 0.874 | 0.741 | 0.134 | 0.054 | n/a | n/a |
| B risk score | 0.806 | 0.500 | 1.000 | 0.000 | 0.892 | 0.621 | 0.153 | 0.100 | n/a | n/a |
| Persistence | 0.819 | 0.563 | 0.983 | 0.143 | 0.898 | 0.651 | 0.133 | 0.095 | 10.03 | 0.57 |
| Drift | 0.764 | 0.610 | 0.862 | 0.357 | 0.855 | 0.637 | 0.158 | 0.127 | 9.59 | 0.53 |
| PSA-only logistic | 0.778 | 0.483 | 0.966 | 0.000 | 0.875 | 0.749 | 0.140 | 0.101 | n/a | n/a |
| NLP-only logistic | 0.806 | 0.500 | 1.000 | 0.000 | 0.892 | 0.634 | 0.158 | 0.111 | n/a | n/a |
| All-inputs logistic | 0.681 | 0.558 | 0.759 | 0.357 | 0.793 | 0.709 | 0.210 | 0.198 | n/a | n/a |

**Confusion, A-H:** TP 57, FP 10, TN 4, FN 1. **Persistence:** TP 57, FP 12, TN 2, FN 1.

| Brier difference | Value |
|---|---|
| A-H − persistence | −0.013 [−0.046, +0.012], not significant |
| A-H − drift | −0.038 [−0.083, +0.004] |
| A-H − E149 | −0.003 [−0.039, +0.026] |
| A-H − frozen | −0.015 [−0.036, +0.005] |

**Coverage of 90 % intervals, pool:** 0.89.

## By period and island, A-H, Lead 1

| Period | n | Accuracy | Always-HIGH | Persistence accuracy | Brier | Persistence Brier |
|---|---|---|---|---|---|---|
| 2018 | 22 | 0.77 | 0.68 | 0.64 | 0.146 | 0.211 |
| 2019 | 25 | 0.92 | 0.92 | 0.92 | 0.072 | 0.076 |
| 2021 | 25 | 0.84 | 0.80 | 0.88 | 0.143 | 0.120 |

**Luzon** 0.71 (n = 35, always-HIGH 0.63). **Mindanao** 0.95 (n = 22, always-HIGH 0.95). **Visayas** 1.00 (n = 15, always-HIGH 1.00). Skill exists only where classes vary, and the model adds nothing to always-HIGH in Mindanao and Visayas.

## Unopened holdout (12 areas, mostly cities; sealed before reading)

| Rule | Accuracy | Balanced | HIGH recall | LOW recall | AUC | Brier |
|---|---|---|---|---|---|---|
| **E150 placement rule** | **0.75** | **0.81** | 1.00 | 0.63 | 0.84 | 0.262 |
| Shared level alone | 0.33 | 0.50 | 1.00 | 0.00 | n/a | 0.596 |
| Latest national level | 0.33 | 0.50 | 1.00 | 0.00 | n/a | 0.615 |
| Always-LOW (not knowable in advance) | 0.67 | 0.50 | 0.00 | 1.00 | n/a | n/a |

MAE 10.2 points against 18.1 for shared level alone. Correct 9 of 12; approximate 95 % interval 0.47 to 0.91. Largest miss: Batanes, measured 13.6 %, predicted High. The holdout tests placement of city types, not provinces or quarterly movement.

**Seal history:** the first seal (`bfeff610`) had σ missing, and at least one forecast value blank from a city row with no value. My note D2 in the protocol understated this by saying forecast values were unaffected. No label had been read when it was re-sealed (`1c19aca2`).

## Maximum reliable lead

**0 quarters on the pool under the locked gates.**

| Lead | Accuracy | Balanced | LOW recall | AUC | Brier | Coverage | Failed gates |
|---|---|---|---|---|---|---|---|
| 1 | 0.847 | 0.634 | 0.286 | 0.786 | 0.119 | 0.889 | R4, R8 |
| 2 | 0.847 | 0.634 | 0.286 | 0.786 | 0.119 | 0.889 | R4, R8 |
| 3 to 6 | 0.722 | 0.638 | 0.500 | 0.709 | 0.170 | 0.847 | R1, R4, R5, R7 |
| 7, 8 (n = 50) | 0.880 | 0.751 | 0.571 | 0.787 | 0.113 | 0.880 | R2, R4 |

Leads 1 and 2 fail only two gates. Leads 3 to 6 fall largely because the model has lost later survey rounds and because of the poverty defect in `METHODOLOGY_REDESIGN.md`. Leads 7 and 8 lack the 2018 test rows, so they aren't comparable, and do not imply better long-range skill.

## What improved, honestly

| Dimension | E149 | E150 | Verdict |
|---|---|---|---|
| Prevalence error, pool | 8.36 | 7.09 | **Better** |
| Calibration slope, pool | 0.79 | 1.05 | **Better** |
| AUC, pool | 0.686 | 0.786 | **Better** |
| Accuracy, pool | 0.806 | 0.847 | Better, modest |
| LOW recall, pool | 0.143 | 0.286 (A-G 0.429) | Better, still low |
| Brier, pool | 0.123 | 0.119 | No real change |
| Brier, 2021 | 0.107 | 0.143 | **Worse** |
| Provinces separated | 1 clearly | 0 of 10 pairs | **Worse** |
| Quarterly movement used | Almost none | None in A-H; 2.4 to 2.8 points in A-G | Depends on the arm |
| Independent quarterly evidence | Failed | Response beats history on a held-out area | **Better, at area level** |
| News value | None | None | No change |
