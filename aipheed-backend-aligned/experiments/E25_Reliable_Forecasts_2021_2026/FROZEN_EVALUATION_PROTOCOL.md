# E25 Frozen Evaluation Protocol (written and hashed before any E25 model was fitted on the real quarters)

**Freeze.**

- `runner/PROTOCOL_SHA256.txt` holds the SHA-256 of this file and of the two frozen libraries it relies on (`runner/e23_lib.py`, identical to E23's; `runner/pcf.py`, identical to E24v2's). The hashes are computed by script.
- Every E25 runner refuses to start if any of them changed.
- The SHA-256 of each runner script is recorded in every run manifest. Any later code change that alters a result is logged in `BUG_FIXES.md` with its correctness reason.

**Already done before this freeze** (baselines only, or synthetic):

- `docs/REACHABILITY.md`: naive persistence, calibrated persistence and always-HIGH on the real quarters. This is the "before modeling" computation the task asks for.
- `docs/POWER_SIMULATION.md`: synthetic only.
- `IDEA_LOG.md` Part 1.

**Not blind.** Every 2021-Q1…2026-Q2 outcome was examined in E9–E24v2. **Every E25 result on those quarters is development evidence.** The only untouched evidence is:

- the prospective seals (§9), scored after the researcher authorizes the outcomes by hash;
- quarters authorized in future.

**Supersedes** the earlier E25 draft protocol (`2026-10-14_E25_Window_2021_2026`, SHA-256 253c535c57fb…, verified by script in `runs/readonly_verification.json`).

- That draft was never run on outer rows; only an equivalence check of its runner against E24 was run.
- Its rules are kept: window, masking, targets, timing, the 12 models, its 4 candidates and its FINAL choices (PCF21 for T1, M4_21 for T2).
- This protocol adds ideas, row sets and supporting analyses. **No rule of the draft is relaxed.**

## 1. Window, data and timing

### 1.1 Window

- Quarterly rows run from 2021-Q1 to **2026-Q2**; monthly values from 2021-01 to **2026-06**.
- Every loaded table is asserted at runtime to lie inside the window. A violation stops the run.
- No pre-2021 value is used: no CPI back-cast, no early SWS.

### 1.2 Inputs

Every input is hash-verified on every read by `runner/guard.py`. The pins come from the E17/E18 guards, read programmatically into `inputs/PINS.json`; nothing is typed.

| Input | Coverage | Basis |
|---|---|---|
| E12 `realized_components_2021_2025.csv` (F, D, H, S1) and `details.json` (SWS rounds, verified publication dates) | 2021–2025 | E17/E18 allowlist. Byte-identical copies in `inputs/e12/`, restored from commit 5113ae5. |
| `features_fused.parquet`, read-time filter 2021-Q1…2025-Q4 | 2021–2025 | E17/E18 allowlist. The file also holds 2020 rows; the filter keeps them out of the analysis. |
| `config/governing_model.json` (feature list) | — | E17/E18 allowlist |
| Provincial food CPI YoY, January–June 2026 | 2026 H1 | Authorized 2026-10-13 (E18) |
| Production SWS parquet, read-time filter 2026-Q1…2026-Q2 (March and June 2026 Balance Luzon rounds) | 2026 H1 | Authorized 2026-10-13 (E18) |
| E24v2 `cpi_index_2021_2025_ACP22.csv` (provincial CPI indices, food, 2021-01…2025-12) | 2021–2025 | Public PSA; pinned by E24v2's acquisition manifest. Used only for monthly YoY from 2022-01 (Dnow and the monthly evaluation). **Owner confirmation pending (A6).** |
| `lgu_census.parquet`, `lgu_poverty.parquet` (year filter 2021–2025), `data/reference/*.csv` | Static | E17 allowlist |
| `nns_fies.parquet` (year filter 2021–2025) | 2021, 2023 | E17 allowlist (FNRI face-validity anchor) |

### 1.3 Publication timing (strict)

| Item | Rule |
|---|---|
| **Origin** | O(t) = 00:00 PHT on the first day of quarter t+1 |
| **SWS rounds 2021–2025** | Usable at O(t) iff the verified publication date (E12) is before O(t) |
| **SWS rounds 2026** | No verified publication date. A round counts as published only after the time the production file shows it had been fetched (an upper bound, rounded up to the next day: 2026-09-10). **So no backtest origin uses a 2026 round, as an input or as a training label.** Sensitivity: the longest verified 2021–2025 lag (fieldwork to publication) gives the same answer for every backtest origin. |
| **T1 label of quarter q** | Published at O(t) iff q ≤ t−1 **and** every round used for that label (under the reading) is usable at O(t) |
| **T2 label of quarter q** | Published at O(t) iff q ≤ t−1 (all three CPI months of q are released before O(t); the provincial release lag is assumed ≤ the national one + 6 days, as in E9/E17) |
| **Dnow(t)** (months 1–2 of quarter t) | Released before O(t) |
| **Features of quarter t** | News of quarter t; government indicators of quarter t−1; the SWS feature = the latest production round usable at O(t) (E23 rule) |

### 1.4 Pre-2021 information removed from in-window rows

Applied to every model (unchanged from the draft):

- `*_lag1` and `*_accel` are set missing at 2021-Q1, and `FSSI_lag2` at 2021-Q1/Q2.
- `cpi_dev` is recomputed from quarters ≥ 2021-Q1 only (at least 2), else missing.
- **Residual risk (stated):** a 2021 value could be a 2020 value carried forward by the original forward-fill. This cannot be detected from in-window rows.

## 2. Targets

| ID | Target | Status |
|---|---|---|
| **T1-A** | S1 = H + 2D > τ(t). H = mean of the **production** (definition-A) rounds of the quarter; τ(t) = median S1 over the labels published at O(t) (E23 rule). | **PRIMARY (approved)** |
| T1-B | As T1-A, H from every round with E12's quarter assignment (the supplementary rounds give 2025-Q2 and 2025-Q3 labels) | Sensitivity (disputed rounds) |
| T1-C | As T1-B, but the round named "First Quarter 2025 Social Weather Survey" is assigned to 2025-Q1 by its name | Sensitivity (disputed rounds) |
| T1-F | As T1-A with the fixed threshold 14.6 (E23's pre-existing sensitivity value) | Sensitivity (label stability) |
| **T2** | D > 0 (the province's food inflation is above the five-province mean) | **EXPLORATORY**; never substituted for T1 |
| T1-cont | S1 itself, as a continuous forecast | Supporting |

## 3. Origins, leads, minimum training, row sets

- Origins O(t) for t = 2021-Q1…2026-Q1; leads k = 1…8.
- The target t+k must be ≤ 2026-Q2 and must have a label.
- **Minimum training:** ≥ 8 distinct labelled training target quarters at lead k at O(t), for every model, so all models share the same origins.
- Feature models exist only for t ≤ 2025-Q4 (no 2026 features are authorized).

| Row set | Origins | Models |
|---|---|---|
| **R_A (primary)** | t ≤ 2025-Q4 where **every** model has a prediction | All |
| **R_P** | t ≤ 2026-Q1 where every label-history model has a prediction (adds the 2026-Q2 target) | Label-history models only |
| **Pooled leads** | Union of origins over k = 1…8 within R_A (or R_P). Per date, the mean over leads of each per-lead mean loss, so each date counts once. | As the row set |

**The independent unit is the forecast date (origin).** Province rows are never treated as independent. Readings B/C and T1-F are run for label-history models only.

## 4. Models (fixed now; no model is added after any result is seen)

### 4.1 Required by Chapter I (SOP Q3 / H3; Objective 4 maps I→B1, II→B3, III→B4, IV→B2)

| ID | Specification (E23, unchanged) |
|---|---|
| B1_naive_persistence | Last published label (current τ) |
| B2_lr_combined | Logistic regression (median imputation, standardization, C = 1) on news + government |
| B3_lr_gov_only | The same on government |
| B4_lr_nlp_only | The same on news |
| B5_lgbm_gov_only | LightGBM, E23 16-configuration grid, nested chronological selection (last 3 training target quarters, log loss) |
| B6_lgbm_nlp_only | The same on news |
| PROPOSED_lgbm_combined | The same on news + government; SHAP (TreeSHAP) |

### 4.2 References and diagnostics

| ID | Specification | Use |
|---|---|---|
| B1p_calibrated_persistence | Laplace rate of HIGH among training pairs with the same last label | Reference baseline (calibrated persistence) |
| CLIM_training_rate | Laplace rate of HIGH among training pairs | No-skill reference |
| REF_always_HIGH | Score 1.0 | Diagnostic; uses no data |
| MAJ_training_majority | Training majority class | Diagnostic |
| DIAG_ORACLE_H, DIAG_ORACLE_D | PCF21 with the realized target-quarter H (or D) | **Diagnostic only**; never a forecast; never compared as a candidate |
| ABL_no_FSSI, ABL_no_FSSI_group, ABL_no_cpi_dev | PROPOSED refit without FSSI / without FSSI and its lags and acceleration / without cpi_dev, same selected configuration | H1 ablation |

### 4.3 E25 candidates (16)

**T1 (10).** All PCF members:

- use P(HIGH) = 1 − Φ((τ − μ_H − 2μ_D) / √(V_H + 4σ_D²));
- use H from production rounds unless stated;
- use the D part trained on 2021+ pairs only.

| ID | H part | D part | Note |
|---|---|---|---|
| **PCF21 = FINAL_T1** | Local level (E24v2 engine, n = 600) | OLS without intercept of D(t′+k) on D(t′−1), lead-specific | FINAL (as in the draft) |
| PCF21_NOW | Local level | OLS on [Dnow(t′), D(t′−1)] | Draft candidate |
| PCF21_SUPP | Local level, supplementary rounds also as inputs | As PCF21 | Idea 4 |
| PCF21_HIER | Local level | D_HIER_NOW (below) | Idea 6 |
| PCF21_MR | AR(1) mean reversion toward the mean of usable rounds (φ by least squares on a 0.01 grid, gap-adjusted) | As PCF21 | Idea 5 |
| PCF21_LI | Local level + ridge (λ = 1 per row, standardized) effect of the latest change in five-province mean food inflation | As PCF21 | Idea 11 |
| ENS_PCF21_B1p | Mean of PCF21 and B1p | — | Idea 8 |
| GATE_PCF21_B1p | PCF21, unless its inner Brier (last 3 training target quarters, forecasts from their own earlier origins, outer τ) is not strictly lower than B1p's; then B1p | — | Idea 8 |
| CAL_PCF21 | PCF21 with temperature a (logit(p′) = a·logit(p), a ∈ {0.20, 0.25, …, 2.00}) fitted by inner log loss on the same inner forecasts; a = 1 if there are none | — | Idea 8 |
| E24_LR_P | E24's frozen logistic regression on the label-history block | — | E24 prospective candidate |

**T2 (6):**

| ID | Specification |
|---|---|
| **M4_21 = FINAL_T2** | P(D > 0) from OLS without intercept on [Dnow(t′), D(t′−1)], pairs t′ ≥ 2022-Q1, Gaussian errors (as in the draft) |
| M3_21 | As M4_21 on D(t′−1) only, t′ ≥ 2021-Q2 (draft) |
| D_HIER | Province means shrunk toward 0 (empirical Bayes); AR(1) on deviations pooled over provinces and consecutive quarters ≤ t−1; one model for all leads; Gaussian propagation |
| D_HIER_NOW | D_HIER with Dnow(t) as a noisy measurement of D(t) (error variance from quarters ≤ t−1) |
| E24_LR_P_T2 | E24's logistic regression on the label-history block |
| ENS_M4_B1p | Mean of M4_21 and B1p |

**Lineage counted for multiplicity:**

- the 4 draft candidates are included above;
- E24: E24-F and 15 ablation arms;
- E24v2: 6 in-window-relevant arms.

### 4.4 Monthly provincial component (`runner/monthly_d_eval.py`)

- **Data:** d(p,m) = food YoY − five-province mean, months 2022-01…2026-06.
- **Origin:** after month m is released (O_m = 15th of month m+1).
- **Target:** 1[mean d(p, m+1…m+3) > 0].
- **Training:** origins m′ with m′+3 ≤ m, ≥ 12 of them.
- **Baselines:** SIGN_PERSIST (1[d(m) > 0]), CAL_PERSIST (Laplace rate given the sign of d(m)), CLIM.
- **Candidates:** **AR_M = FINAL_M** (OLS without intercept of the target mean on [d(m), mean d(m−2…m)], Gaussian); HIER_M (province means shrunk toward 0, the same regression on deviations).

## 5. Tuning

- Only inside training windows: nested LightGBM selection, LR C fixed at 1, GATE and CAL inner steps, D and H parameters by least squares or likelihood on published data.
- The threshold is 0.5 for every model.
- No label, threshold, window, rule, feature set or grid is changed in response to results.

## 6. Metrics and statistics

**Per target, row set and lead (and pooled):**

- accuracy, balanced accuracy, precision, recall, F1, ROC-AUC (when both classes are present), Brier, log score;
- the confusion counts, with HIGH and LOW counts beside every metric;
- training size (min–max training target quarters) per model and lead.

**Paired tests** (FINAL, PROPOSED and each candidate vs each of B1–B6, B1p, CLIM, MAJ, REF_always_HIGH, on identical rows):

- exact one-sided sign-flip over dates on per-date accuracy and Brier differences (exact up to 16 dates; Monte Carlo with 50,000 draws, seed 20261013, above);
- the paired AUC permutation (whole-date swaps);
- dates better/worse;
- the leave-one-date-out range (chronological; no refit).

**Holm adjustment:**

- across B1–B6 (accuracy and Brier) for FINAL and PROPOSED;
- across B1–B6 + B1p for the proposed criteria;
- across the candidates of a target for each candidate's Brier p against the strongest baseline.

**Continuous (T1-cont):** CRPS (Gaussian) and MAE of μ_S1 vs a random walk (the last published S1, with σ = training RMSE of the random walk at lead k); sign-flip on per-date CRPS differences.

## 7. Acceptance criteria

### 7.1 Original criteria (E24 definitions, unchanged)

Applied to FINAL_T1 on T1-A, lead 1, R_A:

| # | Criterion |
|---|---|
| C1 | Accuracy > 0.75 |
| C2 | Strongest = highest accuracy among B1–B6 (ties: lower Brier). FINAL accuracy higher **and** one-sided sign-flip p < 0.05 on per-date accuracy **and** mean Brier not higher. |
| C3 | Balanced accuracy ≥ 0.60 and greater than the strongest baseline's |
| C4 | More dates better than worse vs the strongest, and the leave-one-date-out accuracy difference ≥ 0 for every left-out date |
| C5 | Correct on more label-change rows than wrong on unchanged rows |
| C6 | E23 reliability rule: evaluable (≥ 8 dates, ≥ 5 HIGH, ≥ 5 LOW), AUC date-cluster bootstrap lower bound > 0.5, Brier better than persistence with p < 0.05. **Researcher-declared; adviser approval pending.** |
| C7 | No leakage (all assertions pass) |
| C8 | Reproducible (byte-identical second run) |
| C9 | Generalizes to unseen quarters: **NOT ASSESSABLE** until sealed forecasts are scored |

**The forecasting goal is met only if C1–C9 all hold.** Where the reachability analysis shows a criterion cannot be met by any model, the report says so.

### 7.2 Proposed criteria

**Pending adviser approval; reported side by side, NEVER as meeting the goal until approved.**

| # | Criterion |
|---|---|
| P1 (replaces C1) | Pooled-lead Brier of FINAL lower than both no-skill references (REF_always_HIGH and CLIM) |
| P2 (replaces C2) | Pooled leads, each date once. Strongest = lowest pooled Brier among B1–B6 and B1p. Mean per-date Brier difference favors FINAL **and** its exact one-sided sign-flip p < 0.05 (Holm across B1–B6 + B1p reported). |
| P3 | = C3 |
| P4 (replaces C4) | Pooled design: more dates better than worse (Brier) vs the strongest, and the leave-one-date-out mean Brier difference favors FINAL for every left-out date |
| P5 | = C5 |
| P6 (replaces C6) | Lead k is reliable iff ≥ 8 dates, FINAL's Brier is below both B1 and B1p with one-sided sign-flip p < 0.05 for each (Holm across leads with ≥ 8 dates), and \|mean p − mean y\| ≤ 0.10 |
| P7–P9 | = C7–C9 |

### 7.3 Hypotheses (E23 decision rules, unchanged)

| Hypothesis | Rule |
|---|---|
| H1 | Primary lead = 1 if evaluable, else the smallest evaluable lead. **Strongest predictor = top 5 by mean \|SHAP\| pooled over dates.** Rejected iff both FSSI and cpi_dev are top 5 pooled, top 5 in ≥ 50% of dates, and have a permutation-importance ΔBrier date-cluster bootstrap lower bound > 0. Not testable if no lead is evaluable; SHAP and ablation are then reported descriptively. |
| H2 | Rejected iff ≥ 2 leads are reliable (E23 rule). Not testable with fewer than 2 evaluable leads. |
| H3 | Rejected iff, at the primary lead, PROPOSED beats every one of B1–B6 (Holm one-sided AUC p < 0.05 and a lower Brier). Not testable if no lead is evaluable. |
| H4, H5 | `instruments/DECISION_RULES.md` (E24, unchanged). Awaiting genuine DA Region IV-A responses. |

## 8. Supporting analyses (descriptive; none selects a model)

- Reachability (done) and power (done).
- The noise ceiling (E24v2 method, n = 600 and n = 300).
- Threshold stability: τ(t) across origins; labels that differ between origins and under T1-F.
- Readings A/B/C: label counts, τ and evaluability, and every label-history arm's metrics under each.
- Province ranking skill: per-date Spearman of the forecast μ_D vs the realized D, against the persistence of D.
- Risk–coverage for FINAL vs B1 (|p − 0.5| ≥ 0.1, 0.2, 0.3, 0.4).
- Oracle decomposition (diagnostic).
- **Authorized 2026 quarters, scored once without refitting:** the predictions from origin t = 2025-Q4 (models fitted at 2026-01-01) for 2026-Q1 (k = 1) and 2026-Q2 (k = 2). Development evidence (viewed in E18).
- **Leave-one-quarter-out refit, NON-CHRONOLOGICAL** (uses future quarters; never evidence of forecasting skill):
  - lead 1;
  - B1p, E24_LR_P, PROPOSED, and the D part of PCF21 and M4_21;
  - the held-out target quarter and every pair touching it are excluded from training.

## 9. Prospective seal (`runner/seal_e25.py`)

| Item | Rule |
|---|---|
| **Origin** | O(2026-Q3) = 2026-10-01 00:00 PHT. This is later than every existing sealed origin (E24v2: 2026-07-01). Sealed on the run date, before any 2026-Q4 or 2027-Q1 outcome exists. |
| **Information** | Authorized data only: labels through 2026-Q2 (the 2026 rounds' upper-bound dates precede O(2026-Q3)); D through 2026-Q2; rounds through June 2026 |
| **Assumption (stated)** | No September 2026 round was published before 2026-10-01. Every Q3 round in 2021–2025 was published on 17 October or later. This is not verified. |
| **Arms sealed** | Only arms whose every input is authorized: the label-history arms not using Dnow (B1, B1p, CLIM, PCF21 = FINAL_T1, PCF21_SUPP, PCF21_MR, PCF21_LI, ENS, GATE, CAL, E24_LR_P; T2: M3_21, D_HIER, E24_LR_P_T2) |
| **Arms reported as MISSING INPUT** | Arms needing Dnow(2026-Q3) (July–August 2026 CPI): PCF21_NOW, PCF21_HIER, M4_21 = FINAL_T2, D_HIER_NOW, ENS_M4_B1p. Feature models (2026-Q3 news and government data). |
| **Targets** | 2026-Q4 (k = 1) and 2027-Q1 (k = 2) |
| **Re-sealing** | The seal is written once and refused if it exists; `--verify` recomputes and compares without writing |
| **Scoring** | Only by `runner/score_sealed.py`, which refuses unless the researcher supplies the outcome files with their SHA-256 |
| **Generalization claim** | Needs ≥ 8 scored dates and ≥ 5 LOW (and ≥ 5 HIGH) rows |

The **operational 2027-Q1 forecast** is the lead-1 forecast at O(2026-Q4) = 2027-01-01. It is complete only when every input listed in `AUTHORIZATION_REQUEST.md` is authorized and published before that cutoff. Otherwise its record shows exactly which inputs are missing.

## 10. Reproducibility

- Every run seals its predictions (SHA-256 of the CSV bytes).
- A second run must give byte-identical seals.
- Seeds: LightGBM `random_state` 42, `deterministic`, `n_jobs` 1; tests 20261013; simulation 20261014.

## 11. Reporting

- Negative results are results.
- If no model beats the baselines, the report says so.
- No criterion is reported as met unless it is met under the rule written here.
