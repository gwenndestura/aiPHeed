# E6 Protocol: Revised Scoring and Probability Pipeline (final evaluation)

| Item | Value |
|---|---|
| Date | 2026-10-12 |
| Status | Frozen before any revised forecast was generated or evaluated |
| Code | `app/ml/features/risk_score_v2.py`, `app/ml/training/revised_trainer.py`, `scripts/build_revised_forecasts.py` |
| Scope | Isolated development backend only. No 2026 label or outcome. |

**This is the sixth analysis on the 7 reused quarters. It is run once.** Its design was informed by E1–E5, so it is exploratory and not an independent validation.

## 1. Selected methodology and why

### Equation 3: evaluated, not replaced

The composite stress formula is kept as the target definition, with corrections:

- a frozen point-in-time threshold;
- missing values stay NaN;
- the regional mean requires all five provinces;
- regional and provincial parts are reported separately.

**Why it is not replaced:**

1. **Over-HIGH is not caused by the formula.** On 2021–2025 data, with the approved 14.345:
   - setting the coefficient to 0 (regional hunger only) labels **30/30** rows in 2024–2025 HIGH;
   - α = 1 gives 29, α = 2 gives 27, α = 2.74 (equal variance) gives 27, α = 4 gives 24.
   - The concentration of HIGH comes from Balance-Luzon hunger (15.3–25.3% in 2024–2025), not from the coefficient.
2. **No outcome exists to estimate a better coefficient,** and equal-variance weighting is unstable: α_eff is 1.13 against the 2021–2023 reference but 2.74 against 2021–2025.
3. **The alternatives already evaluated were not more defensible or not predictable:**

   | Alternative | Result |
   |---|---|
   | S2 (standardized, equal weights) | 35/35 HIGH |
   | P1 (inflation rate) | Price stress only; slowing inflation reads as LOW |
   | D-D (two-condition rule) | LightGBM balanced accuracy 0.535 |
   | E2 (relative price) | Not predictable beyond carry-forward |

**The coefficient α = 2 is kept as a documented, unvalidated parameter.** It is not assumed valid.

### Separated supporting indicators (not probabilities)

| Indicator | Definition | Scope |
|---|---|---|
| Regional hunger signal | SWS Balance-Luzon %, with round, publication date and age | Regional; shared by all five provinces |
| Provincial food-price evidence | Inflation rate (YoY %), relative pressure (pp vs the five-province mean), inflation change (pp), and food CPI index level (context only: a level, not current pressure) | Provincial; as published before the forecast origin |
| Supporting stress | Last published Equation 3 stress, decomposed into regional and provincial components | — |

### Forecast and classification

**Primary forecast:** a LightGBM probability that the province's stress exceeds τ_ref in the target quarter.

**Model (fixed a priori; no search):**

| Setting | Value |
|---|---|
| Inputs | `last_published_stress`, `sws_hunger`, `sws_change`, `cpi_rel`, `food_cpi_yoy`, `rice_price_regular_accel`, `unemployment_rate` |
| Monotone constraints | +1 on the first two; 0 on the rest |
| Hyperparameters | `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42 |
| Class weighting | **None** |
| Timing | Rule L training labels, development-frame inputs; NaN kept |

**Calibration:** Platt scaling only if a training-only inner walk-forward provides at least 8 out-of-fold quarters and at least 10 rows per class. Otherwise the raw probability is used. The decision is recorded per fold.

**Final classification:**

| Class | Rule |
|---|---|
| HIGH | Final probability ≥ 0.50 |
| LOW | Final probability < 0.50 |
| **INSUFFICIENT_DATA** | Any required input is missing (`last_published_stress`, `sws_hunger`, `cpi_rel`, `food_cpi_yoy`), **or** the SWS input is older than 3 quarters, **or** there are fewer than 8 eligible training quarters, **or** the training labels contain one class |

**Threshold τ_ref:**

| Use | τ_ref | Status |
|---|---|---|
| Served retrospective artifact | **10.843**: median stress of labels published before 2023-10-01, frozen | Primary |
| Evaluation-only artifact | **14.345**: the approved value | Leakage-affected on 2021–2025; never served |

## 2. Final evaluation (once)

**Units:**

- Outer test quarters: 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4 (35 rows), as in E1, E3, E4 and E5.
- 2025-Q2 and 2025-Q3 are forecast but have no label, so they are reported as unevaluable.

**What is evaluated:**

- The predictions **evaluated are the served artifact itself.** Labels are computed afterwards from `labels.parquet` at the same τ.

**Comparisons:**

| Comparison | Basis |
|---|---|
| Carry-forward | Last published stress > τ (score: margin) |
| Existing Equation 3 rule | SWS input + 2·`cpi_rel` > τ (score: margin) |
| Regional-only rule | SWS input > τ (score: margin). Shows whether the provincial term adds anything. |
| Always-HIGH and always-LOW | References |
| E3 (class-weighted), reference | From E4 D-C and D-A, not re-run |
| Old served model | Its in-sample probabilities for the same rows. **Descriptive only:** it was trained on these quarters. |

**Metrics:**

- counts: observations, quarters, HIGH/LOW reference labels, and HIGH/LOW/INSUFFICIENT predictions;
- accuracy and balanced accuracy;
- HIGH precision, HIGH recall and LOW recall;
- false HIGH and false LOW counts;
- ROC-AUC and PR-AUC (where both classes exist);
- Brier score and log loss;
- reliability (mean predicted vs observed in probability bins);
- per-quarter results;
- quarter-cluster bootstrap balanced-accuracy differences against each baseline (10,000 draws, seed 42).

**Decision labels (exploratory):**

| Label | Meaning |
|---|---|
| Improvement | Balanced-accuracy gain ≥ 0.10 with a CI excluding 0 |
| Non-inferiority | Within 0.05 of the better baseline |
| Better calibration | Lower Brier and log loss than the class-weighted E3 reference |

Better class balance is reported separately and **is not counted as improvement.**

**What happens after the evaluation:** no settings are changed.
