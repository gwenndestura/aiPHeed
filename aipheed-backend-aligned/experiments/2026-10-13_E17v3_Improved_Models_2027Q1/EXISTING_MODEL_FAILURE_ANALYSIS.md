# Existing-Model Failure Analysis (from earlier reports; no new results)

**The values below are historical evidence from E13 and E17.** They are not E17 v3 results.

## 1. Regional hunger (E13 Task A; 9 test quarters 2023-Q4..2025-Q4; one quarter ahead in E13's convention)

| Model | Reported MAE (points) |
|---|---|
| Carry-forward | 4.77 |
| Drift | 4.89 |
| Historical mean | 6.74 |
| Ridge AR(1) | 6.57 |
| Ridge AR(1) + regional food inflation | 6.58 |

**Failure modes identified in those reports:**

| Failure mode | Evidence |
|---|---|
| **Structural change** | Hunger moved from 8.7–15.4% (2021–2023) to 14.3–25.3% (2023-Q4..2025-Q4). Training on the calm period teaches mean reversion toward about 10–11%. |
| **Unstable trend and AR sign** | AR slopes ranged from −0.39 to +3.97 (standardized) across folds. Once the rise entered the training data, the model over-reacted: 2025-Q2 forecast 28.0 against 16.15. |
| **Small sample** | 6–14 training points per fold |
| **Weak predictors** | Regional food inflation is **negatively** correlated with hunger in 2021–2025 (r ≈ −0.48). Adding it changed nothing. |
| **Underestimated uncertainty** | 80% intervals from training errors covered 2 of 9 quarters |
| **Possible unforecastability** | Quarter-to-quarter swings of 7–8 points (2025-Q1 → Q2 → Q3) are larger than any signal in the history |

## 2. Provincial F and D (E13 Task B; E17 supporting)

| Target | Finding |
|---|---|
| **F** | No model beats carry-forward at k = 1–4. The best baseline changes with the timing rule. |
| **D** | Shrinking toward 0 beats carry-forward at 2–4 quarters ahead, but it is no better than predicting "no difference" (D = 0) from 2023-Q4 onward |

## 3. Thesis classifier (E17)

| Lead time | Accuracy | Naive persistence | Notes |
|---|---|---|---|
| k = 1 | 0.629 | 0.686 | Below persistence |
| k = 2 | 0.680 | 0.720 | Below persistence |
| k ≥ 3 | — | — | Too few test quarters |

**The failure modes:** a training/test class shift (2021–2023 mostly LOW, 2024–2025 mostly HIGH), a label dominated by regional hunger, and zero-filled features.

## 4. What this implies for E17 v3

- **Any new H model must handle level shifts** (drift, damped or robust trends, a second lag), or it will not beat carry-forward.
- **At h = 5, fewer origins exist than at h = 1.** It must be checked whether the horizon can be evaluated at all.
