# Prospective Validation Protocol (frozen 2026-10-13; to be evaluated later)

**Status:**

- **When it was written:** before any quarter after 2025-Q4 was seen in this work, and before any E15 prototype output.
- **Hash:** the SHA-256 of this file is in `PROSPECTIVE_VALIDATION_PROTOCOL.sha256`.
- **Changes:** this file must not be edited. An amendment needs a new, versioned file that states its reason and is hashed **before** the quarters it affects are published.
- **Execution:** this experiment (E15) **does not run** the evaluation.

**What the results can mean:**

- **H1** forecasts relative food-price pressure, D. D is derived from official provincial CPI, but it is **not food insecurity.**
- **H2** is **internal consistency of a constructed indicator** (S1).
- **Neither validates food-insecurity prediction.** If an independent provincial outcome becomes available, a new protocol is required.

## 1. Hypotheses (only these two)

| ID | Hypothesis | Candidate forecasts (already defined in E13; no new formula) |
|---|---|---|
| **H1** | D persists only partly, so a shrunk forecast of D beats carry-forward for next-quarter D | **Primary:** `B2_ridge_D` = ridge(D[p,T−2]). **Secondary:** `B2_ridge_DP` = ridge(D[p,T−2], province mean D over 2021-Q1..T−2). |
| **H2** | Shrinkage helps next-quarter S1 forecasting | `S1_shrink_D` = H_last_A + 2 × B2_ridge_D. `S1_shrink_DP` = H_last_A + 2 × B2_ridge_DP. |

## 2. Baselines

| Hypothesis | Baseline | Definition |
|---|---|---|
| H1 | Carry-forward | D[p,T−2] (E13 `B2_cf`) |
| H1 | Training-mean D, pooled | The mean of D over the training rows. This is **0 by construction** for complete quarters (E13 `B2_zero`). |
| H1 | Training-mean D, by province | Mean of D[p, 2021-Q1..T−2] (E13 `B2_pmean`) |
| H2 | Carry-forward components (the S1 origin rule) | H_last_A + 2 × D[p,T−2] |
| H2 | Training-mean D | H_last_A + 2 × 0 |

**H_last_A** is the mean of the production-series (`definition_A`) SWS rounds of the most recent fieldwork quarter that has a round published before the origin. It is the same rule as E13's `h_last`, restricted to production rounds.

## 3. Target, horizon and cutoffs

| Item | Specification |
|---|---|
| **Target** | H1: D[p,T] for the 5 provinces. H2: S1[p,T] = H_A[T] + 2·D[p,T]. |
| **Horizon** | Forecast issued at **origin(T) = the first day of quarter T**. Provincial inputs come from quarter T−2 and earlier. SWS inputs are rounds published before the origin. |
| **Publication cutoff (inputs)** | An input is usable only if officially published **before** origin(T). Where verified release dates exist they are used; otherwise the calendar rule applies (quarter T−1 cannot be published before origin(T)). Each input's release date and status is recorded. |
| **Publication cutoff (outcomes)** | Quarter T is scored only after F[T] has been published for **all five** provinces (and, for H2, a production-series SWS round fielded in T). The value used is the first one obtained at scoring time, and its vintage date is recorded. |
| **Missing data** | Fewer than 5 provinces with F at T or T−2 makes the quarter **INSUFFICIENT_DATA**. It is excluded and counted, never imputed. |
| **Training** | Expanding window from 2021-Q3 through T−2, refitted at each origin. Ridge α = 1.0 on training-standardized features. **No retuning.** |
| **Implementation** | E13 functions `b_training`, `b_features`, `ridge_fit_predict` and `forecast_B`, pinned by hash: `e13_lib.py` `118afbf5…6bf63723`, `run_e13.py` `5c09d6a2…6bed081221`. Any code change is an amendment. |

## 4. Eligible quarters

- **First confirmatory target quarter: 2026-Q3.** Values for 2026-Q1 and 2026-Q2 already appear in project records (exposure documented in earlier experiments). They may serve only as **inputs** and training data once published. They are never confirmatory test quarters.
- **Order:** the quarters are scored in calendar order. Every eligible quarter is included; none may be dropped after it is seen.

## 5. Metrics

| Metric | Role |
|---|---|
| **MAE** | **Primary**, pooled over provinces and quarters |
| RMSE | Secondary |
| Rank correlation: within-quarter **Spearman ρ** between forecast and realized D (or S1) across the 5 provinces, averaged over quarters | Secondary. Kendall τ is also reported, for continuity with E13. |
| Per-quarter and per-province MAE; bias | Descriptive |

## 6. Decision rule and the number of quarters needed

**A candidate counts as supporting a hypothesis only if all of the following hold on the eligible prospective quarters:**

1. Its MAE is lower than every baseline's.
2. The quarter-cluster bootstrap 95% interval of MAE(candidate) − MAE(best baseline) lies entirely below 0 (10,000 draws; seed 20261013).
3. The exact one-sided sign-flip p on per-quarter MAE differences is < 0.05 after a Holm adjustment over that hypothesis's two candidates.
4. Its MAE stays below the best baseline's when each quarter is left out in turn.
5. **The number of eligible quarters is at least the minimum below.**

**Minimum quarters.** Computed in `runs/sizing_20261013T024522Z/sizing.json` from E13's per-quarter differences. Settings: one-sided α = 0.025 (Holm's first step), power 0.80.

| Hypothesis and candidate | E13 effect (MAE difference, quarters) | SD | Quarters for 80% power at the E13 effect | At half the effect |
|---|---|---|---|---|
| H1 `B2_ridge_D` vs carry-forward | −0.166 (8/11 better) | 0.364 | 38 | 152 |
| H1 `B2_ridge_DP` vs carry-forward | −0.175 (9/11 better) | 0.214 | **12** | 48 |
| H2 `S1_shrink_D` vs the S1 origin rule | −0.031 (3/9 better) | 0.245 | 506 | 2,023 |
| H2 `S1_shrink_DP` vs the S1 origin rule | −0.030 (3/9 better) | 0.294 | 773 | 3,090 |

The smallest number of quarters at which the exact sign-flip test can reach p < 0.025 is 6.

**Frozen minimums:**

- **H1: at least 12 eligible quarters** (2026-Q3 through 2029-Q2 at the earliest) before any claim.
  - Results from fewer than 12 quarters are **exploratory** and must be labelled so.
  - The E13 effects were estimated on quarters that had already been examined, so they are probably optimistic. **At half the effect, 48 quarters would be needed.**
- **H2: no confirmatory claim is possible in any foreseeable period** (more than 500 quarters needed). H2 results are always **exploratory**.
  - **The reason:** S1 forecast errors are dominated by the shared regional hunger term, which shrinkage does not affect.
- **No early stopping for success.** Interim looks are exploratory.

## 7. Governance

- **Who may run it:** the evaluation uses quarters after 2025-Q4. It may be run **only** under an explicit, separately approved protected-data procedure. That procedure needs your and your adviser's written approval, a guarded and hash-pinned input allowlist, and a new experiment folder.
- **E15 does not run it** and contains no code that reads 2026 data.
- **What must be reported:** every scored quarter, the INSUFFICIENT_DATA count, input release dates and their status, outcome vintages, and every deviation.
- **What may be claimed afterwards:**
  - At most: "a shrunk forecast of relative provincial food-price pressure was more accurate than carry-forward over N new quarters" (H1).
  - Not: anything about food insecurity, provincial risk, or the validity of S1's weight or threshold.
