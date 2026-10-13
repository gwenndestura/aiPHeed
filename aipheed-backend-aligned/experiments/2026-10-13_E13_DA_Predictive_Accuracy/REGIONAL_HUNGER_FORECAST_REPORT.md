# Regional Hunger Forecast Report (Task A)

**Target.** SWS Balance-Luzon involuntary hunger, H[T] (% of families), forecast at the start of quarter T.

| Item | Value |
|---|---|
| Test quarters | **9** (2023-Q4..2025-Q4). Each is **one** observation; there are no provincial rows. |
| Training | 6 to 14 earlier quarters, all fully published before the origin |
| Timing | **Established** (verified publication dates) |
| Status | **Small sample; previously explored quarters.** This is not a fresh validation. |

**Sources:**

- v1: `runs/20261013T022702Z/`
- Amendment 1: `runs/a1_20261013T030455Z/` (`metrics_a1.json` → `results.A`)

## 1. Results

| Arm | Type | MAE | RMSE | Bias | MAE relative to carry-forward |
|---|---|---|---|---|---|
| **A_cf**: latest published value | Baseline | **4.77** | 5.22 | −3.02 | 1.00 |
| A_drift: latest value + average quarterly change (A1) | Baseline | 4.89 | 5.34 | −3.02 | 1.03 |
| A_mean: historical mean | Baseline | 6.74 | 7.75 | −6.74 | 1.41 |
| A_ridge_H: regularized AR(1) on the latest value | Model | 6.57 | 7.39 | −3.95 | 1.38 |
| A_ridge_HF: + regional food inflation (T−2) | Model | 6.58 | 7.42 | −3.90 | 1.38 |

**Against carry-forward:** A_ridge_H is worse by **+1.81** points (bootstrap interval +0.20 to +3.33). It is better in only 3 of 9 quarters, and better in 0 of 9 leave-one-quarter-out subsets.

**Adding regional food inflation** to the AR(1) changes MAE by +0.006 (−0.10 to +0.12). **It adds nothing.**

**Absolute error by quarter:**

| Quarter | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 |
|---|---|---|---|---|---|---|---|---|---|
| Realized H | 14.3 | 15.3 | 19.6 | 18.1 | 25.3 | 24.0 | 16.15 | 23.8 | 16.7 |
| A_cf error | 3.0 | 5.0 | 5.3 | 2.8 | 5.7 | 5.9 | 7.85 | 6.8 | 0.55 |
| A_ridge_H error | 3.95 | 4.88 | 9.15 | 7.67 | 10.0 | 7.21 | 11.81 | 4.24 | 0.22 |

**Stability:**

| Period | A_cf | A_drift | A_ridge_H |
|---|---|---|---|
| First 4 quarters | 4.03 | 4.61 | 6.41 |
| Last 5 quarters | 5.36 | 5.11 | 6.70 |

**No arm beats carry-forward in both halves.** A_drift is better only in the second half.

**80% prediction intervals for carry-forward** (training errors, 2021–2023) covered the realized value in only **2 of 9** quarters, against a nominal 80%. The errors learned in a calm period were far too small for the 2024–2025 level shift. **No defensible uncertainty band can be built from this history.**

## 2. Can the model detect changes earlier than a baseline?

**Event:** hunger rises above the latest published value. It happened in **8 of 9** quarters, so only one quarter had no rise.

| Arm | TP / FP / FN / TN | Balanced accuracy |
|---|---|---|
| Carry-forward | 0 / 0 / 8 / 1 | 0.50 (it cannot predict a rise) |
| A_drift | 4 / 1 / 4 / 0 | 0.25 |
| A_ridge_H | 3 / 1 / 5 / 0 | 0.19 |

**With one negative case, these figures cannot show that any method detects changes earlier.**

## 3. Assumptions

**The AR(1) assumes a stable mean.** The series moved from 8.7–15.4% (2021–2023) to 14.3–25.3% (2023-Q4..2025-Q4), so that assumption fails here.

- **The fitted slopes changed sign across folds:** −0.39 to −0.22 (standardized) in the first four folds, and up to +3.97 in later folds.
- **Effect on forecasts:** at first the model pulled them toward the old mean. Later it over-reacted (2025-Q2 forecast 28.0 against 16.15).

**Regional food inflation is negatively correlated with hunger** (Pearson −0.48 at lag 0, −0.46 at lag 1, −0.25 at lag 2; n = 17–18 quarters). Hunger rose while food inflation fell in 2024–2025. This is not a usable leading signal in this period.

## 4. Conclusion

- **No verified improvement in regional hunger forecasting.**
  - The simplest method, the latest published value, has the lowest error (4.8 points).
  - It still misses the direction of change in most quarters.
- **Uncertainty is larger than the training history suggests.** Its 80% intervals covered 2 of 9 quarters.
- **This is regional information only.** It says nothing about differences between provinces.
