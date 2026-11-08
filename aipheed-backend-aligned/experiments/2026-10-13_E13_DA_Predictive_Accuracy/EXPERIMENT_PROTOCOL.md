# E13 Experiment Protocol (frozen before any comparison)

**Status.** Written on 2026-10-13, after the outcome audit (`OUTCOME_DATA_AUDIT.md`) and the input inventory (`runs/inspect_20261013T022045Z/`). No baseline or model had been computed at that point.

**Freeze mechanism:**

- The SHA-256 of this file is stored in `runner/PROTOCOL_SHA256.txt`.
- `run_e13.py` refuses to start if the hash differs.
- Any later change is a deviation and must be reported in `TEST_AND_REPRODUCIBILITY_REPORT.md`.

**Not blind.** The analyst has seen every 2021–2025 value in E1–E12. All test quarters below were examined before. **This is a retrospective walk-forward on reused quarters. It is not a new independent test.** The only independent test available to aiPHeed is prospective: 2026-H2, which is protected and not accessed here.

## 1. Questions

| ID | Question | Kind of outcome |
|---|---|---|
| A | Can **regional hunger** H[T] (SWS Balance Luzon) be forecast at the start of quarter T better than simple baselines? | Independently measured hunger, **regional** |
| B1 | Can **provincial food inflation** F[p,T] be forecast better than simple baselines? | Food-price pressure, provincial. **Not food insecurity.** |
| B2 | Can **relative provincial food-price pressure** D[p,T] = F[p,T] − mean of the five F[·,T] be forecast better than simple baselines? | Relative price pressure, provincial. **Not food insecurity.** |
| C | Do provincial price pressure and provincial subsistence incidence agree (2021, 2023)? How does the regional FIES 2025 value compare with SWS 2025? | Descriptive only |
| Dx | Why does the S1 classification label almost every province-quarter HIGH? | Diagnosis, no model comparison |

**Out of scope:**

- **Provincial food-insecurity accuracy.** No outcome exists (see the audit).
- **S1 prediction.** It is covered by E9–E12 and referenced only. Predicting a constructed indicator with its own inputs is internal consistency, not accuracy.

## 2. Forecast origin and availability

- **Origin** of target quarter T: the first day of T.
- **Regional hunger:**
  - A round is usable at origin(T) only if its publication date is strictly earlier than origin(T).
  - **H_last** is the mean of the published rounds of the most recent fieldwork quarter that has at least one published round.
  - **H_age** = T − (that quarter), in quarters.
- **Provincial F and D:** only quarters ≤ T−2 are usable.
  - **Why T−1 is excluded:** its last month ends the day before origin(T), so it cannot be published before origin(T).
  - **Why T−2 is included:** it was released about 10 weeks before origin(T) in every case E9 documented.
  - The release dates are proxies, so this is a calendar rule, not a verified date check.
- **Training pairs for target T:**
  - **A:** every quarter q < T whose rounds were **all** published before origin(T). The features are computed **as of origin(q)**, and pairs missing any feature are dropped.
  - **B1, B2:** every quarter q from 2021-Q3 to T−2, five provinces each, with features as of origin(q). Quarters before 2021-Q3 have no T−2 value inside the window. **No pre-2021 data are used.**
- **Minimum training:** 6 quarters. A test quarter with fewer is skipped and reported.
- **Expected test quarters** (the rule governs if the run finds otherwise):
  - **A:** 2023-Q4 to 2025-Q4, 9 quarters with an observed H.
  - **B1, B2:** 2023-Q2 to 2025-Q4, 11 quarters × 5 provinces = 55 rows.
- **INSUFFICIENT_DATA** (never converted to LOW, 0 or a carried value):
  - **A:** H_last is missing, or H_age > 4.
  - **B1:** the province has no F at T−2.
  - **B2 and its ranking:** fewer than 5 provinces have F at T−2.
  - Counts are reported.

## 3. Arms

Fixed settings:

- **Ridge:** α = 1.0 on features standardized with **training rows only**, with an unpenalized intercept.
- **Tree:** depth 2, min_samples_leaf = 5, random_state = 0.
- **No other settings are tried.**
- **LightGBM is not fitted.** Training sets have 6–14 regional points (A) or 30–80 province rows from 6–16 quarters (B). That is too small for a boosted ensemble, and E9 and E11 found no reliable gain from it. The earlier 45-feature model is not used.

| Target | Arm | Type | Forecast |
|---|---|---|---|
| A | `A_cf` | Baseline | H_last. This is the regional term of the S1 origin rule (E9 B2/B3). |
| A | `A_mean` | Baseline | Mean of all quarterly H values fully published before origin(T), from 2021-Q2 |
| A | `A_ridge_H` | Model | ridge(H_last) |
| A | `A_ridge_HF` | Model | ridge(H_last, F5_lag2), where F5_lag2 is the five-province mean food inflation of T−2 |
| B1 | `B1_cf` | Baseline | F[p,T−2] |
| B1 | `B1_regional` | Baseline | F5_lag2 (regional only; the same for all provinces) |
| B1 | `B1_mean` | Baseline | Pooled mean of the training targets |
| B1 | `B1_pmean` | Baseline | Province historical mean of F over 2021-Q1..T−2 |
| B1 | `B1_ridge_F` | Model | ridge(F_lag2) |
| B1 | `B1_ridge_FR` | Model | ridge(F_lag2, F5_lag2) |
| B1 | `B1_tree` | Model | tree(F_lag2, F5_lag2) |
| B2 | `B2_zero` | Baseline | 0 (regional only: no provincial difference) |
| B2 | `B2_cf` | Baseline | D[p,T−2]. This is the provincial term of the S1 origin rule. |
| B2 | `B2_pmean` | Baseline | Province historical mean of D over 2021-Q1..T−2 |
| B2 | `B2_ridge_D` | Model | ridge(D_lag2) |
| B2 | `B2_ridge_DP` | Model | ridge(D_lag2, Dbar_p) |
| B2 | `B2_tree` | Model | tree(D_lag2, Dbar_p) |

## 4. Primary metric and the improvement rule

- **Primary metric:** test MAE for each target, pooled over its test rows. Target A has 1 row per quarter. Targets B1 and B2 have 5 rows per quarter.
- **Reported with it:**
  - RMSE and bias;
  - per-quarter MAE;
  - MAE by province (B1, B2);
  - the within-quarter Kendall τ between forecast and realized values (B1, B2).

**A model counts as improving on the baselines for its target only if all four conditions hold:**

1. **Lower MAE than every baseline** for that target.
2. **Bootstrap interval below 0.** The quarter-cluster bootstrap 95% interval of MAE(model) − MAE(best baseline) lies entirely below 0.
   - The best baseline is the one with the lowest test MAE. Choosing it after the test makes the comparison **stricter**.
   - Settings: B = 10,000; seed 20261013.
3. **Sign-flip test.** The exact one-sided sign-flip test on the per-quarter MAE differences against that baseline gives p < 0.05 after a Holm adjustment across that target's models (2 for A, 3 for B1, 3 for B2).
4. **Leave-one-quarter-out.** The model's MAE stays below the best baseline's when each test quarter is left out in turn (every subset).

**If no model meets all four conditions,** the result is: *no defensible improvement has been established for that target.*

**If a model meets them,** it is still described as **retrospective evidence on previously examined quarters.** For B1 and B2 it is evidence about price pressure, **not about food insecurity.**

The rule does not use the 75% figure, class balance or the number of HIGH labels.

## 5. Secondary event classification

These thresholds are fixed now and never tuned. They do not enter the improvement rule.

| Target | Event | Predicted event | Score for ROC-AUC and PR-AUC | Justification |
|---|---|---|---|---|
| A | H[T] > H_last (hunger rises against the latest published value) | forecast > H_last | forecast − H_last | Natural direction call; no level threshold exists for SWS hunger |
| B1 | F[p,T] > 4.0% | forecast > 4.0 | forecast | Upper bound of the government's 2–4% inflation target band. It is used as an external reference: the band applies to headline inflation, not food. |
| B2 | D[p,T] > 0 (above the five-province mean) | forecast > 0 | forecast | The sign of relative pressure |

**Metrics reported:** n, positives and negatives; TP, FP, FN and TN; balanced accuracy; precision and recall for each class; ROC-AUC and PR-AUC when both classes are present; results by quarter and by province.

**Calibration** is not applicable, because no arm outputs probabilities.

## 6. Sensitivity analyses (descriptive; never used to choose)

- **S-A1:** target A with production (`definition_A`) rounds only, for both the target and the inputs. This removes the three supplementary 2025 rounds.
- **S-B1:** B1 and B2 restricted to the E9–E12 test quarters (2023-Q4, 2024-Q1..Q4, 2025-Q1, 2025-Q4), for comparability.

## 7. Descriptive external comparisons (C)

- **C1:** for 2021 and 2023, each province's mean F and mean D over the four quarters, against its subsistence incidence (with CV) and against the 2021 LGU-poverty median.
  - Spearman ρ with n = 5 for each year. **No p-values. No inference.**
- **C2:** the regional FIES 2025 value (22.6%) beside the mean of the SWS 2025 rounds.
  - Different instruments, recall periods and geographies. **Shown side by side only.**

## 8. Diagnosis (Dx)

Computed from file 1 (realized S1, H and D), with τ0 = 10.84335 (recorded; no S1 value lies between the two τ0 values):

- the HIGH share by year;
- the agreement of S1 HIGH/LOW with the H-only call (H > τ0);
- for each quarter, the D a province would need to be LOW, (τ0 − H)/2, against the observed range of D;
- the share of S1's deviation from τ0 that comes from the regional term;
- for information only, the HIGH count under the documented prospective τ = 14.345. **It is not evaluated or selected.**

## 9. Order of operations and seal

1. Verify the protocol hash and the allowlist hashes.
2. Build every test row's features and every arm's forecast from data available at origin(T) only.
3. Run a **future-perturbation check:** for each test quarter, set every value not available at origin(T) to 999 and confirm that every forecast is unchanged.
4. Write `predictions.csv` (forecasts only, no realized values) and record its SHA-256 in `SEAL.json`.
5. Only then join the realized values and compute the metrics.
6. Run the whole procedure twice and confirm byte-identical outputs.

## 10. What a result would and would not mean for DA

- **Target A** speaks about forecasting regional hunger. It gives **one** value for the region, never five provincial values.
- **Targets B1 and B2** speak about food-price pressure in each province, which DA can monitor. They are **not food insecurity.**
- **No outcome here validates S1 HIGH/LOW, any weight or any threshold** for provincial food insecurity.
- **Before any operational use** (outside this experiment), a result would need:
  1. prospective confirmation on new quarters;
  2. an adviser's decision.
