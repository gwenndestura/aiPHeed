# E71 tables (runner/e71_score.py)

## FIR71 labels

Threshold (P60 of the 2022 reference composite): 0.3807. Labelled rows 90 (2022-Q1 … 2026-Q2); HIGH share 0.54.

| Quarter | HIGH of 5 | mean FIR71 | ACCESS | AVAILABILITY | STABILITY |
|---|---|---|---|---|---|
| 2022-Q1 | 0 | 0.299 | 0.375 | 0.435 | 0.087 |
| 2022-Q2 | 1 | 0.314 | 0.321 | 0.535 | 0.087 |
| 2022-Q3 | 4 | 0.475 | 0.564 | 0.515 | 0.345 |
| 2022-Q4 | 3 | 0.388 | 0.333 | 0.515 | 0.316 |
| 2023-Q1 | 1 | 0.359 | 0.640 | 0.350 | 0.087 |
| 2023-Q2 | 4 | 0.425 | 0.552 | 0.435 | 0.287 |
| 2023-Q3 | 5 | 0.643 | 0.568 | 0.515 | 0.845 |
| 2023-Q4 | 4 | 0.417 | 0.285 | 0.380 | 0.588 |
| 2024-Q1 | 5 | 0.537 | 0.403 | 0.620 | 0.588 |
| 2024-Q2 | 5 | 0.444 | 0.493 | 0.550 | 0.287 |
| 2024-Q3 | 4 | 0.448 | 0.438 | 0.475 | 0.431 |
| 2024-Q4 | 5 | 0.535 | 0.463 | 0.720 | 0.422 |
| 2025-Q1 | 0 | 0.255 | 0.482 | 0.195 | 0.087 |
| 2025-Q2 | 1 | 0.257 | 0.404 | 0.280 | 0.087 |
| 2025-Q3 | 4 | 0.408 | 0.397 | 0.335 | 0.492 |
| 2025-Q4 | 3 | 0.365 | 0.383 | 0.230 | 0.481 |
| 2026-Q1 | 0 | 0.256 | 0.055 | 0.585 | 0.128 |
| 2026-Q2 | 0 | 0.217 | 0.177 | 0.385 | 0.087 |

## V1: regional outcome (SWS hunger; validation only, never an input)

Quarters with all five provinces labelled and an SWS round: 17. Spearman ρ(mean FIR71, hunger) = -0.21 [-0.68, +0.35] → **NOT SUPPORTED**. By dimension: ACCESS -0.34, AVAILABILITY +0.01, STABILITY -0.04; share HIGH -0.06. Consecutive-quarter change direction agreement 8/16. Exploratory in-sample OLS of hunger on the dimensions: const +22.2, ACCESS -13.1, AVAILABILITY -1.3, STABILITY -0.2.

| Quarter | mean FIR71 | HIGH share | SWS hunger |
|---|---|---|---|
| 2022-Q2 | 0.314 | 0.2 | 11.8 |
| 2022-Q3 | 0.475 | 0.8 | 9.6 |
| 2022-Q4 | 0.388 | 0.6 | 11.3 |
| 2023-Q1 | 0.359 | 0.2 | 8.7 |
| 2023-Q2 | 0.425 | 0.8 | 11.3 |
| 2023-Q3 | 0.643 | 1.0 | 10.3 |
| 2023-Q4 | 0.417 | 0.8 | 14.3 |
| 2024-Q1 | 0.537 | 1.0 | 15.3 |
| 2024-Q2 | 0.444 | 1.0 | 19.6 |
| 2024-Q3 | 0.448 | 0.8 | 18.1 |
| 2024-Q4 | 0.535 | 1.0 | 25.3 |
| 2025-Q1 | 0.255 | 0.0 | 24.0 |
| 2025-Q2 | 0.257 | 0.2 | 16.1 |
| 2025-Q3 | 0.408 | 0.8 | 23.8 |
| 2025-Q4 | 0.365 | 0.6 | 16.7 |
| 2026-Q1 | 0.256 | 0.0 | 22.4 |
| 2026-Q2 | 0.217 | 0.0 | 17.3 |

## V2: provincial cross-section vs PSA subsistence incidence (face validity only, 5 units)

- FIR71_2023_vs_subsistence_2023: Spearman -0.40 (n 5); Cavite 0.481 vs 0.8%; Laguna 0.48 vs 1.3%; Quezon 0.439 vs 0.9%; Rizal 0.443 vs 2.6%; Batangas 0.462 vs 1.4%
- FIR71_2022_vs_subsistence_2021: Spearman -0.87 (n 5); Cavite 0.37 vs 2.4%; Laguna 0.373 vs 2.4%; Quezon 0.323 vs 6.6%; Rizal 0.388 vs 0.9%; Batangas 0.392 vs 1.0%

## V3: collapse and sensitivity

FIR71 class = T43 price condition on 48/90 labelled rows → price-collapsed: **False**. Largest dimension of HIGH rows: {'AVAILABILITY': 26, 'STABILITY': 17, 'ACCESS': 6}; HIGH rows with ACCESS not stressed (≤ 0.75): 49 of 49; stressed-dimension count of HIGH rows: {0: 42, 1: 6, 2: 1}. Leave-one-dimension-out agreement: {'without_ACCESS': [78, 90], 'without_AVAILABILITY': [69, 90], 'without_STABILITY': [68, 90]}. Thresholds: {'agreement': [86, 90], 'prevalence': 0.5888888888888889}, {'agreement': [79, 90], 'prevalence': 0.4222222222222222}. Gap variant: {'agreement': [85, 90], 'prevalence': 0.5777777777777777}. Correlation food YoY vs gap: reference +0.91, all +0.77.

## Lead 1: 55 rows, 11 quarters (2023-Q4 … 2026-Q2), 31 HIGH; ICC 0.62, effective n ≈ 16

| Arm | Correct/n | Accuracy [Wilson 95%] | TP/FP/FN/TN | Prec H | Rec H | F1 H | Rec L | Bal acc | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LightGBM (Objective 2 model) | 27/55 | 0.491 [0.364, 0.619] | 22/19/9/5 | 0.537 | 0.710 | 0.611 | 0.208 | 0.459 | 0.437 | 0.278 | -0.37 |
| LightGBM without news (ablation) | 27/55 | 0.491 [0.364, 0.619] | 22/19/9/5 | 0.537 | 0.710 | 0.611 | 0.208 | 0.459 | 0.458 | 0.267 | -0.20 |
| IV. Logistic regression | 29/55 | 0.527 [0.398, 0.653] | 18/13/13/11 | 0.581 | 0.581 | 0.581 | 0.458 | 0.519 | 0.546 | 0.303 | 0.08 |
| II. PSA-only LR | 38/55 | 0.691 [0.560, 0.797] | 29/15/2/9 | 0.659 | 0.935 | 0.773 | 0.375 | 0.655 | 0.715 | 0.233 | 0.39 |
| III. NLP-only LR | 25/55 | 0.455 [0.330, 0.585] | 24/23/7/1 | 0.511 | 0.774 | 0.615 | 0.042 | 0.408 | 0.419 | 0.306 | -0.11 |
| DIMFUSE (dimension projection + logistic) | 32/55 | 0.582 [0.450, 0.703] | 31/23/0/1 | 0.574 | 1.000 | 0.729 | 0.042 | 0.521 | 0.633 | 0.251 | 0.82 |
| I. Naive persistence | 30/55 | 0.545 [0.415, 0.670] | 23/17/8/7 | 0.575 | 0.742 | 0.648 | 0.292 | 0.517 | 0.517 | 0.455 | 0.01 |
| Province climatology | 27/55 | 0.491 [0.364, 0.619] | 26/23/5/1 | 0.531 | 0.839 | 0.650 | 0.042 | 0.440 | 0.400 | 0.276 | -0.85 |
| Majority | 28/55 | 0.509 [0.381, 0.636] | 27/23/4/1 | 0.540 | 0.871 | 0.667 | 0.042 | 0.456 | 0.456 | 0.491 | -0.07 |

| a − b | Δ Brier [95% CI] | Quarter wins/losses (sign p; Holm) | McNemar a/b only (p) |
|---|---|---|---|
| LGBM vs PERSIST | -0.176 [-0.349, +0.001] | 8/3 (p 0.227; Holm 0.906) | 11/14 (p 0.690) |
| LGBM vs PSA_LR | +0.045 [-0.114, +0.186] | 3/8 (p 0.227; Holm 0.906) | 6/17 (p 0.035) |
| LGBM vs NLP_LR | -0.028 [-0.129, +0.057] | 7/4 (p 0.549; Holm 1.000) | 7/5 (p 0.774) |
| LGBM vs LR | -0.025 [-0.118, +0.066] | 6/5 (p 1.000; Holm 1.000) | 9/11 (p 0.824) |
| LGBM vs PROVCLIM | +0.002 [-0.052, +0.053] | 5/6 (p 1.000) | 6/6 (p 1.000) |
| LGBM vs MAJ | -0.213 [-0.430, -0.001] | 7/4 (p 0.549) | 4/5 (p 1.000) |
| DIMFUSE vs LGBM | -0.028 [-0.110, +0.059] | 8/3 (p 0.227) | 10/5 (p 0.302) |
| LGBM_NONEWS vs LGBM | -0.011 [-0.029, +0.001] | 5/2 (p 0.453) | 0/0 (p 1.000) |
| DIMFUSE vs PERSIST | -0.204 [-0.326, -0.091] | 9/2 (p 0.065) | 8/6 (p 0.791) |

Per quarter (LGBM correct/n, HIGH): 2023-Q4 1/5 (4); 2024-Q1 0/5 (5); 2024-Q2 5/5 (5); 2024-Q3 4/5 (4); 2024-Q4 5/5 (5); 2025-Q1 4/5 (0); 2025-Q2 1/5 (1); 2025-Q3 4/5 (4); 2025-Q4 3/5 (3); 2026-Q1 0/5 (0); 2026-Q2 0/5 (0)

Per province (LGBM correct/n, HIGH, missed HIGH): Batangas 6/11 (7, FN 2); Cavite 6/11 (7, FN 2); Laguna 3/11 (4, FN 2); Quezon 5/11 (5, FN 1); Rizal 7/11 (8, FN 2)

E63-style reliable-horizon criterion (vs persistence and province climatology): {'LGBM': False, 'DIMFUSE': False}

## Lead 2: 45 rows, 9 quarters (2024-Q2 … 2026-Q2), 22 HIGH; ICC 0.63, effective n ≈ 13

| Arm | Correct/n | Accuracy [Wilson 95%] | TP/FP/FN/TN | Prec H | Rec H | F1 H | Rec L | Bal acc | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LightGBM (Objective 2 model) | 22/45 | 0.489 [0.350, 0.630] | 20/21/2/2 | 0.488 | 0.909 | 0.635 | 0.087 | 0.498 | 0.519 | 0.284 | 0.24 |
| LightGBM without news (ablation) | 22/45 | 0.489 [0.350, 0.630] | 20/21/2/2 | 0.488 | 0.909 | 0.635 | 0.087 | 0.498 | 0.521 | 0.286 | 0.20 |
| IV. Logistic regression | 29/45 | 0.644 [0.498, 0.768] | 18/12/4/11 | 0.600 | 0.818 | 0.692 | 0.478 | 0.648 | 0.761 | 0.247 | 0.44 |
| II. PSA-only LR | 29/45 | 0.644 [0.498, 0.768] | 19/13/3/10 | 0.594 | 0.864 | 0.704 | 0.435 | 0.649 | 0.674 | 0.314 | 0.22 |
| III. NLP-only LR | 20/45 | 0.444 [0.309, 0.588] | 20/23/2/0 | 0.465 | 0.909 | 0.615 | 0.000 | 0.455 | 0.512 | 0.337 | -0.18 |
| DIMFUSE (dimension projection + logistic) | 29/45 | 0.644 [0.498, 0.768] | 19/13/3/10 | 0.594 | 0.864 | 0.704 | 0.435 | 0.649 | 0.852 | 0.225 | 1.01 |
| I. Naive persistence | 26/45 | 0.578 [0.433, 0.710] | 18/15/4/8 | 0.545 | 0.818 | 0.655 | 0.348 | 0.583 | 0.583 | 0.422 | 0.05 |
| Province climatology | 18/45 | 0.400 [0.270, 0.545] | 18/23/4/0 | 0.439 | 0.818 | 0.571 | 0.000 | 0.409 | 0.464 | 0.283 | -0.57 |
| Majority | 22/45 | 0.489 [0.350, 0.630] | 22/23/0/0 | 0.489 | 1.000 | 0.657 | 0.000 | 0.500 | 0.500 | 0.511 | -0.55 |

| a − b | Δ Brier [95% CI] | Quarter wins/losses (sign p; Holm) | McNemar a/b only (p) |
|---|---|---|---|
| LGBM vs PERSIST | -0.139 [-0.289, +0.004] | 6/3 (p 0.508; Holm 1.000) | 2/6 (p 0.289) |
| LGBM vs PSA_LR | -0.030 [-0.150, +0.086] | 6/3 (p 0.508; Holm 1.000) | 4/11 (p 0.118) |
| LGBM vs NLP_LR | -0.054 [-0.128, +0.016] | 5/4 (p 1.000; Holm 1.000) | 4/2 (p 0.688) |
| LGBM vs LR | +0.037 [-0.052, +0.128] | 3/6 (p 0.508; Holm 1.000) | 2/9 (p 0.065) |
| LGBM vs PROVCLIM | +0.000 [-0.058, +0.068] | 6/3 (p 0.508) | 6/2 (p 0.289) |
| LGBM vs MAJ | -0.227 [-0.438, -0.038] | 6/3 (p 0.508) | 2/2 (p 1.000) |
| DIMFUSE vs LGBM | -0.058 [-0.104, -0.007] | 7/2 (p 0.180) | 8/1 (p 0.039) |
| LGBM_NONEWS vs LGBM | +0.002 [-0.000, +0.006] | 1/1 (p 1.000) | 0/0 (p 1.000) |
| DIMFUSE vs PERSIST | -0.197 [-0.337, -0.074] | 7/2 (p 0.180) | 5/2 (p 0.453) |

Per quarter (LGBM correct/n, HIGH): 2024-Q2 5/5 (5); 2024-Q3 4/5 (4); 2024-Q4 5/5 (5); 2025-Q1 0/5 (0); 2025-Q2 1/5 (1); 2025-Q3 4/5 (4); 2025-Q4 2/5 (3); 2026-Q1 1/5 (0); 2026-Q2 0/5 (0)

Per province (LGBM correct/n, HIGH, missed HIGH): Batangas 4/9 (5, FN 1); Cavite 5/9 (5, FN 0); Laguna 3/9 (2, FN 0); Quezon 5/9 (4, FN 0); Rizal 5/9 (6, FN 1)

E63-style reliable-horizon criterion (vs persistence and province climatology): {'LGBM': False, 'DIMFUSE': False}

## Lead 3: 40 rows, 8 quarters (2024-Q3 … 2026-Q2), 17 HIGH; ICC 0.58, effective n ≈ 12

| Arm | Correct/n | Accuracy [Wilson 95%] | TP/FP/FN/TN | Prec H | Rec H | F1 H | Rec L | Bal acc | AUC | Brier | Cal. slope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LightGBM (Objective 2 model) | 14/40 | 0.350 [0.221, 0.505] | 14/23/3/0 | 0.378 | 0.824 | 0.519 | 0.000 | 0.412 | 0.389 | 0.356 | -0.90 |
| LightGBM without news (ablation) | 17/40 | 0.425 [0.285, 0.578] | 17/23/0/0 | 0.425 | 1.000 | 0.596 | 0.000 | 0.500 | 0.373 | 0.340 | -1.00 |
| IV. Logistic regression | 15/40 | 0.375 [0.242, 0.530] | 15/23/2/0 | 0.395 | 0.882 | 0.545 | 0.000 | 0.441 | 0.598 | 0.520 | 0.17 |
| II. PSA-only LR | 18/40 | 0.450 [0.307, 0.602] | 17/22/0/1 | 0.436 | 1.000 | 0.607 | 0.043 | 0.522 | 0.550 | 0.518 | 0.20 |
| III. NLP-only LR | 15/40 | 0.375 [0.242, 0.530] | 15/23/2/0 | 0.395 | 0.882 | 0.545 | 0.000 | 0.441 | 0.596 | 0.406 | 0.09 |
| DIMFUSE (dimension projection + logistic) | 17/40 | 0.425 [0.285, 0.578] | 17/23/0/0 | 0.425 | 1.000 | 0.596 | 0.000 | 0.500 | 0.355 | 0.408 | -0.82 |
| I. Naive persistence | 26/40 | 0.650 [0.495, 0.779] | 16/13/1/10 | 0.552 | 0.941 | 0.696 | 0.435 | 0.688 | 0.688 | 0.350 | 0.14 |
| Province climatology | 15/40 | 0.375 [0.242, 0.530] | 14/22/3/1 | 0.389 | 0.824 | 0.528 | 0.043 | 0.434 | 0.503 | 0.292 | -0.21 |
| Majority | 17/40 | 0.425 [0.285, 0.578] | 17/23/0/0 | 0.425 | 1.000 | 0.596 | 0.000 | 0.500 | 0.500 | 0.575 | 1.24 |

| a − b | Δ Brier [95% CI] | Quarter wins/losses (sign p; Holm) | McNemar a/b only (p) |
|---|---|---|---|
| LGBM vs PERSIST | +0.006 [-0.193, +0.208] | 4/4 (p 1.000; Holm 1.000) | 0/12 (p 0.000) |
| LGBM vs PSA_LR | -0.163 [-0.303, -0.012] | 7/1 (p 0.070; Holm 0.281) | 0/4 (p 0.125) |
| LGBM vs NLP_LR | -0.050 [-0.151, +0.047] | 4/4 (p 1.000; Holm 1.000) | 2/3 (p 1.000) |
| LGBM vs LR | -0.165 [-0.307, -0.027] | 7/1 (p 0.070; Holm 0.281) | 1/2 (p 1.000) |
| LGBM vs PROVCLIM | +0.064 [-0.001, +0.125] | 2/6 (p 0.289) | 2/3 (p 1.000) |
| LGBM vs MAJ | -0.219 [-0.388, -0.039] | 7/1 (p 0.070) | 0/3 (p 0.250) |
| DIMFUSE vs LGBM | +0.052 [-0.027, +0.144] | 2/6 (p 0.289) | 3/0 (p 0.250) |
| LGBM_NONEWS vs LGBM | -0.015 [-0.035, +0.003] | 6/2 (p 0.289) | 3/0 (p 0.250) |
| DIMFUSE vs PERSIST | +0.058 [-0.146, +0.302] | 5/3 (p 0.727) | 1/10 (p 0.012) |

Per quarter (LGBM correct/n, HIGH): 2024-Q3 4/5 (4); 2024-Q4 2/5 (5); 2025-Q1 0/5 (0); 2025-Q2 1/5 (1); 2025-Q3 4/5 (4); 2025-Q4 3/5 (3); 2026-Q1 0/5 (0); 2026-Q2 0/5 (0)

Per province (LGBM correct/n, HIGH, missed HIGH): Batangas 3/8 (4, FN 1); Cavite 4/8 (4, FN 0); Laguna 1/8 (1, FN 0); Quezon 2/8 (3, FN 1); Rizal 4/8 (5, FN 1)

E63-style reliable-horizon criterion (vs persistence and province climatology): {'LGBM': False, 'DIMFUSE': False}

## Selection and the 80% statement (PROTOCOL §7)

Selected: **DIMFUSE**. Lead-2 29/45 = 0.644, HIGH recall 0.864, balanced 0.649; vs persistence Δ Brier -0.197 [-0.337, -0.074]. Criteria {'accuracy_ge_0.80': False, 'recall_HIGH_ge_0.50': True, 'balanced_ge_0.70': False, 'beats_persistence_brier_ci': True}. **80% as proxy-prediction accuracy: False. Claimable as food-insecurity accuracy: False.** Evaluation quarters are not unseen.

## Sealed prospective forecasts (no outcome yet)

| Lead | Origin | Target | Province | LGBM | DIMFUSE | PERSIST | LR |
|---|---|---|---|---|---|---|---|
| 1 | 2026-Q3 | 2026-Q4 | Cavite | 0.545 | 0.443 | 0 | 0.991 |
| 1 | 2026-Q3 | 2026-Q4 | Laguna | 0.598 | 0.56 | 0 | 0.997 |
| 1 | 2026-Q3 | 2026-Q4 | Quezon | 0.517 | 0.339 | 0 | 0.953 |
| 1 | 2026-Q3 | 2026-Q4 | Rizal | 0.482 | 0.359 | 0 | 0.99 |
| 1 | 2026-Q3 | 2026-Q4 | Batangas | 0.598 | 0.494 | 0 | 0.996 |
| 2 | 2026-Q2 | 2026-Q4 | Cavite | 0.414 | 0.622 | 0 | 0.355 |
| 2 | 2026-Q2 | 2026-Q4 | Laguna | 0.449 | 0.657 | 0 | 0.554 |
| 2 | 2026-Q2 | 2026-Q4 | Quezon | 0.416 | 0.631 | 0 | 0.246 |
| 2 | 2026-Q2 | 2026-Q4 | Rizal | 0.439 | 0.441 | 0 | 0.001 |
| 2 | 2026-Q2 | 2026-Q4 | Batangas | 0.547 | 0.723 | 0 | 0.104 |
| 2 | 2026-Q3 | 2027-Q1 | Cavite | 0.364 | 0.181 | 0 | 0.025 |
| 2 | 2026-Q3 | 2027-Q1 | Laguna | 0.364 | 0.328 | 0 | 0.019 |
| 2 | 2026-Q3 | 2027-Q1 | Quezon | 0.395 | 0.107 | 0 | 0.067 |
| 2 | 2026-Q3 | 2027-Q1 | Rizal | 0.364 | 0.13 | 0 | 0.016 |
| 2 | 2026-Q3 | 2027-Q1 | Batangas | 0.395 | 0.231 | 0 | 0.019 |
