# E5 Protocol: Candidate Risk-Scoring Formulas

**Status:** fixed before any E5 code was written or run. It documents each candidate's rationale before evaluation.

**Scope:** isolated experiment. No production, dashboard, scheduler or thesis change. No protected 2026 data.

**This is the fifth analysis on the 7 reused quarters.** To limit repeated testing:

- Candidates already evaluated in E4 are **not re-run**; their E4 results are reused.
- Only the **two new** candidates below are evaluated, **once**.

## 1. Diagnosed causes (read-only, 2021–2025 data only)

### Aligned path (Equation 3)

| Item | Detail |
|---|---|
| Formula | stress = 1·SWS_t + 2·d_p,t |
| SWS_t | Balance-Luzon hunger, % (sd 5.0 across rows) |
| d_p,t | Provincial food CPI YoY − five-province mean, pp; sd of 2d = 3.7 |
| Normalization | None; raw units are added |
| Cutoff | Median of all labelled rows (14.345) |
| Dashboard | Model probability ≥ 0.50 → "high" |

**HIGH share by year (approved label):**

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| Approved label | 0.27 | 0.27 | 0.25 | 0.90 | 0.90 |
| Dashboard (in-sample) | — | — | — | 0.90 | 0.90 |

Over 2021–2025 the label is 50% HIGH, and the dashboard (in-sample) 51%.

**Concentration of HIGH in 2024–2025 follows SWS:** 8.7–15.4% before 2023-Q4, 14.3–25.3% after. **No inflation of HIGH beyond the hunger data was found on this path.**

### Thesis `backend/` path (`label_cpi`, Equation 4)

| Item | Detail |
|---|---|
| Rule | HIGH if the food CPI **index level** > its trailing 24-quarter mean + 1σ in 2 consecutive quarters |
| Dashboard | Blend probability ≥ 0.712 |

**HIGH share by year:**

| | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| Label | 0.25 | 0.65 | 0.90 | **1.00** | 0.90 |
| Dashboard | 0.00 | 0.25 | 0.85 | **1.00** | 0.85 |
| Mean food inflation | — | — | 7.3% | 3.6% | 2.7% |

Over 2021–2025 the label is 74% HIGH, and the dashboard 59%.

**Diagnosis: confirmed artifact.**

- The index rose in 77% of quarter-to-quarter steps.
- 34 HIGH rows had **decelerating** food inflation, 12 had inflation **below 2%**, and 2 had inflation **≤ 0**.
- **A rising price index is read as high risk merely because it exceeds its trailing average.**

## 2. Candidates and rationale (written before evaluation)

### Reference parameters

All reference parameters come from data **published before 2023-10-01**, the first evaluation origin. They are computed once and **frozen**:

- the reference stress set is the 40 labels of the 8 quarters eligible at that origin;
- the reference food-inflation set is the provincial YoY values of quarters whose CPI was published by then.

Prospectively, the same rule uses all data published before the forecast origin.

### Hunger-anchored family (thesis target)

| ID | Formula | Cutoff | Rationale | Status |
|---|---|---|---|---|
| S0 | 1·SWS + 2·d (approved) | Median of all 80 labelled rows (14.345) | Approved definition | Evaluated in E4 (D-A). **Leaky** on these quarters. |
| S1 | 1·SWS + 2·d (approved). Stress is **NaN when any input is missing; no zero-fill.** | Median of reference stress = **τ0 = 10.843**, frozen; prospectively 14.345 | Keeps the approved weights (no evidence supports others). Fixes three defects: the leaky full-sample cutoff, the drifting fold median, and zero-fill of missing CPI. | Evaluated in E4 (D-C); not re-run |
| **S2** (new) | z = (SWS_t − μ_R)/σ_R + d_p,t/σ_d. μ_R, σ_R = mean and sd of SWS over the reference quarters; σ_d = sd of d over the reference rows. | Median of z over the reference rows, frozen | **Equal weighting of standardized components**, the standard default for composite indicators when no empirical weights exist. It replaces the undocumented "×2 in raw units" weight. It gives provincial food-price pressure the same influence as regional hunger. | **Evaluated in E5** |

**Expectation for S2, stated now:** because regional SWS in 2024–2025 lies 2–6 reference standard deviations above μ_R, S2 will still classify most 2024–2025 rows HIGH. Standardization is not expected to reduce HIGH counts materially.

### Price-stress family (correction for the `backend/` path; not a hunger measure)

| ID | Formula | Cutoff | Rationale | Status |
|---|---|---|---|---|
| P0 | `label_cpi` (index level > trailing mean + 1σ, 2 consecutive quarters) | — | Current served label | Diagnosed. Not evaluated: it is the artifact itself. |
| **P1** (new) | HIGH if provincial food **inflation rate** (YoY %) > r_ref in quarter t **and** t−1 | r_ref = median food YoY over the reference rows, frozen | Keeps Equation 4's 2-consecutive-quarter persistence rule, but measures **the rate of price increase** instead of the index level. That removes the trend artifact: a falling inflation rate can now produce LOW. | **Evaluated in E5** |

### Considered and not evaluated (rejected a priori)

| ID | Formula | Why not evaluated |
|---|---|---|
| C1 | Year-over-year change in stress, HIGH if > 0 | Under Rule L only 3 test folds have ≥ 8 eligible change-quarters (2022-Q1 has no label), and it measures **worsening**, not risk level |
| D-D (E4) | Relative provincial priority | Already evaluated: LightGBM balanced accuracy 0.535 |
| Any reweighting chosen to balance HIGH and LOW | — | Prohibited |

## 3. Evaluation (S2 and P1, once each)

**Model and folds:**

| Item | Value |
|---|---|
| Folds | The 7 test quarters (2023-Q4 to 2025-Q4), as in E1/E3/E4. Training labels are those published before each origin: Rule L for S2; provincial CPI publication (WD1 proxy) for P1. At least 8 training quarters. |
| Model | E3 LightGBM configuration: 7 inputs; `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42; `scale_pos_weight` from training labels |
| Monotone constraints for S2 | +1 on `last_published_stress` and `sws_hunger` (S2 increases with SWS, and stress persists) |
| Monotone constraints for P1 | **All 0.** P1 contains no SWS, and no direction is asserted. |

**Baselines:**

| Candidate | Carry-forward | Origin-known rule | References |
|---|---|---|---|
| S2 | Last published S2 label (score: last z − cutoff) | z from the SWS input and `cpi_rel` > cutoff (score: margin) | Always-HIGH and always-LOW |
| P1 | Last published P1 label | Latest available provincial food YoY > r_ref (score: margin) | Always-HIGH and always-LOW |

**Metrics:**

- class proportions (all 2021–2025 rows by year, quarter and province, and the test rows);
- confusion matrices;
- balanced accuracy;
- HIGH precision, HIGH recall (missed HIGH) and LOW recall (false HIGH);
- ROC-AUC where a continuous score exists;
- per-quarter results;
- a quarter-bootstrap paired balanced-accuracy difference against each baseline (10,000 draws, seed 42).

**Decision rule per candidate:** the same as E3 (exploratory).

## 4. Criteria for the recommended candidate (fixed now)

**Required:**

1. It measures a **food-insecurity-relevant** quantity, anchored in hunger, for the thesis target.
2. Its threshold has a fixed meaning and is computed point-in-time, without leakage.
3. It has no mechanical artifact: no index trend, no drifting threshold, no zero-fill.
4. Its weights and normalization are justified a priori, not tuned.
5. Its classification moves with its source indicators. When the measured quantity falls, the HIGH share can fall.

**Tie-break:** when more than one candidate meets 1–5, keep the **approved** weights unless an alternative has a stronger documented justification.

**Predictive results are reported, but are not used to rank candidates** that meet 1–5.

The price-stress candidate (P1) **cannot** meet criterion 1. It is assessed only as a correction for the `backend/` path, pending an adviser decision.
