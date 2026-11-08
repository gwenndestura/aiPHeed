# Provincial Food-Price Forecast Report (Task B)

**Targets.** Two separate targets, both forecast at the start of quarter T:

- **F[p,T]:** provincial food inflation, year on year.
- **D[p,T]:** F minus the unweighted five-province mean.

**They are food-price targets, not food-insecurity labels.**

**Evaluation setup:**

| Item | Value |
|---|---|
| Test quarters | **11** (2023-Q2..2025-Q4), × 5 provinces = 55 rows |
| Evaluation unit | The **quarter**, with all five provinces kept together |
| Folds | Expanding window |
| Comparisons | Every arm compared on the same rows |

**Status:** **exploratory (timing).** Provincial CPI release dates are proxies (`TARGET_AND_TIMING_AUDIT.md`). All quarters were examined before.

**Sources:**

- v1: `runs/20261013T022702Z/`
- Amendment 1: `runs/a1_20261013T030455Z/`

## 1. Provincial food inflation (F)

| Arm | Type | MAE | RMSE | Bias | MAE relative to carry-forward | Mean within-quarter Kendall τ |
|---|---|---|---|---|---|---|
| **B1_cf**: F at T−2 | Baseline | **2.44** | 3.19 | +1.50 | 1.00 | 0.40 |
| B1_drift: + province trend (A1) | Baseline | 2.47 | 3.36 | +0.98 | 1.01 | 0.45 |
| B1_regional: five-province mean at T−2 | Baseline | 2.48 | 3.15 | +1.50 | 1.01 | — |
| B1_mean: training mean | Baseline | 2.73 | 3.01 | +1.38 | 1.12 | — |
| B1_pmean: province mean | Baseline | 2.97 | 3.30 | +1.69 | 1.21 | −0.11 |
| B1_ridge_F | Model | 2.52 | 2.81 | +1.21 | 1.03 | 0.40 |
| B1_ridge_FR | Model | 2.64 | 2.92 | +1.21 | 1.08 | 0.40 |
| B1_tree | Model | 2.75 | 3.10 | +1.66 | 1.13 | 0.50 |
| B1_lgbm (A1, exploratory) | Model | 2.54 | 3.05 | +1.00 | 1.04 | 0.28 |

**No model beats carry-forward.**

| Comparison with carry-forward | MAE difference (95% interval) | Quarters better |
|---|---|---|
| B1_ridge_F | +0.08 (−0.42 to +0.58) | 4/11 |
| B1_lgbm | +0.10 (−1.08 to +1.16) | 6/11 |

**Feature increments:**

| Step | MAE change (95% interval) |
|---|---|
| Fitting the lag (ridge_F) | +0.08 (−0.42 to +0.58) |
| Adding regional inflation | +0.12 (−0.10 to +0.34) |
| LightGBM in place of ridge_FR | −0.10 (−0.92 to +0.70) |

**No feature adds measurable value.**

**Stability:** the arm order changes between the two halves of the test period. The trees and means do well in 2023-Q2..2024-Q2, when inflation fell from its highs. Carry-forward and drift do well in 2024-Q3..2025-Q4. **No arm beats carry-forward in both halves.**

**Conservative timing (S-T3: inputs and training ≤ T−3; 9 quarters):**

- Every arm gets worse. Carry-forward MAE is 3.27.
- The **training mean** becomes the best baseline (2.67).
- No model beats it.

**Absolute provincial food inflation cannot be forecast better than the simplest baselines**, and the best baseline depends on the timing rule.

## 2. Relative food-price pressure (D)

| Arm | Type | MAE | RMSE | MAE relative to carry-forward | Kendall τ | Sign right, D > 0 (BA) |
|---|---|---|---|---|---|---|
| B2_zero: no difference (= pooled training mean) | Baseline | 1.37 | 1.78 | 1.01 | — | 0.50 |
| **B2_cf**: D at T−2 | Baseline | **1.355** | 1.85 | 1.00 | 0.40 | 0.69 |
| B2_pmean: province mean | Baseline | 1.55 | 2.09 | 1.14 | −0.11 | 0.44 |
| B2_ridge_D: shrunk D at T−2 | Model | 1.19 | 1.62 | 0.88 | 0.40 | 0.69 |
| **B2_ridge_DP**: + province mean | Model | **1.18** | 1.63 | **0.87** | 0.45 | 0.70 |
| B2_tree | Model | 1.42 | 1.92 | 1.04 | 0.47 | 0.69 |
| B2_lgbm (A1, exploratory) | Model | 1.27 | 1.78 | 0.94 | 0.36 | 0.73 |

**The four frozen conditions** (against the best baseline, carry-forward), unchanged in A1 because no new D baseline exists:

| Arm | MAE difference (95% interval) | Holm p | Leave-one-quarter-out | All four met? |
|---|---|---|---|---|
| B2_ridge_DP | −0.175 (−0.287 to −0.049) | 0.038 | 11/11 | **Yes** |
| B2_ridge_D | −0.166 (−0.369 to +0.048) | 0.160 | — | No |
| B2_lgbm | −0.084 (−0.285 to +0.122) | — | — | No (and not selectable) |

**Feature increments:**

| Step | MAE change (95% interval) | Quarters better |
|---|---|---|
| Shrinking the lag (ridge_D against carry-forward) | −0.17 (−0.37 to +0.05) | 8/11 |
| Adding the province mean | −0.01 (−0.15 to +0.13) | — |
| A tree in place of ridge | **+0.24 (+0.11 to +0.35)**, worse | — |
| LightGBM in place of ridge | +0.09 (−0.03 to +0.22) | — |

**Almost all of the gain comes from shrinking the latest deviation toward 0. More complex models are worse.**

**The gain is against carry-forward, not against "no difference".** On the 9 quarters 2023-Q4..2025-Q4:

| Arm | MAE |
|---|---|
| B2_zero ("no difference") | **1.287**, best |
| B2_ridge_DP | 1.288 |
| B2_ridge_D | 1.32 |
| B2_cf | 1.54 |

The advantage over carry-forward comes from 2023-Q2 and 2023-Q3, when the provincial ranking was still persistent. Under S-T3 the zero baseline is also best (1.29), and no model beats it.

**Stability:** B2_ridge_D and B2_ridge_DP beat carry-forward in both halves:

| Arm | 2023-Q2..2024-Q2 | 2024-Q3..2025-Q4 |
|---|---|---|
| B2_cf | 1.15 | 1.53 |
| B2_ridge_D | 0.97 | 1.37 |
| B2_ridge_DP | 1.01 | 1.33 |
| B2_zero | 1.38 | 1.36 |

**Ranking stability:**

- Realized D rankings agree with the previous quarter at a mean Kendall τ of 0.54.
- Forecast rankings are steadier (0.64–0.66 for ridge and carry-forward), because they follow lagged data.

**80% prediction intervals** (training errors):

| Arm | Coverage | Width |
|---|---|---|
| B2_cf | 0.80 | 3.6 points |
| B2_ridge_DP | 0.80 | 3.2 points (in-sample residuals; optimistic) |
| B1_cf | 0.89 | 11.5 points |

The intervals are wide compared with the typical D spread (1.4–7.3 points within a quarter).

## 3. Does the model predict absolute inflation, relative pressure, or both?

| Target | Can it beat the simplest baseline? |
|---|---|
| **Absolute (F)** | **No** |
| **Relative (D)** | **Only against carry-forward**, by shrinking it. Not against "no difference" from 2023-Q4 onward, and not under conservative timing. |

**Rising pressure (D above its T−2 value)** happened in 27 of 55 rows:

| Arm | Balanced accuracy |
|---|---|
| Carry-forward | 0.50 (it cannot predict a rise) |
| B2_zero | 0.69 |
| B2_ridge_D | 0.69 |
| B2_ridge_DP | 0.66 |

These calls amount to predicting that an extreme value will move back toward 0.

## 4. Conclusion

| Finding | Assessment |
|---|---|
| Verified improvement in provincial food-inflation forecasting | **None** |
| Improvement in relative-pressure forecasting | **One compact shrinkage model meets the frozen rule against carry-forward** (−0.175 points; 13%). The evidence is weak in three ways (below). |

**Why the D evidence is weak:**

1. It does not beat the "no difference" baseline on 9 of the 11 quarters.
2. It disappears under conservative timing.
3. The quarters had already been examined.

**What it supports:** describing the result as "a shrunk forecast of relative food-price pressure was more accurate than carry-forward on 2023–2025 data (exploratory)". **Nothing about food insecurity.**
