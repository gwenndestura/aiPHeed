# E11 Protocol: LightGBM Improvement under the S1 Target (frozen before the first E11 run)

**Naming.** Your request named the folder "E10_LightGBM_Improvement". E10 already exists (`2026-10-12_E10_selection_alignment_q4`), so this experiment is **E11**, and the file names use E11.

**Frozen:** 2026-10-12, before any E11 model was fitted. The runner records this file's SHA-256 and refuses to start without it. Later changes are listed in §10 as deviations.

## 1. Question

Can LightGBM, tuned only inside training folds, predict the S1 stress indicator better than the simple rules? In particular:

- does it beat **the S1 formula rule**, the hardest simple baseline?
- does it keep **provincial differences**?

## 2. Target, data and timing (unchanged from E9)

| Item | Specification |
|---|---|
| Target | **S1** (`risk_score_v2.compute_stress`): SWS_t + 2 × (provincial food CPI YoY − five-province mean); NaN never zero; complete quarters only |
| Event | Stress > **τ0 = 10.8433** (median of labels published before 2023-10-01; checked at run time) |
| Data | Exactly the E9 allowlist, read through the guard (hash-pinned, row filter ≤ 2025-Q4, pre-2021 dropped). The input frame is rebuilt with E9's `safe_frame` and must equal E9's `input_frame.csv` exactly. |
| Timing | E9 development-protocol dates: provincial CPI is proxy-dated (unverified); unemployment is schedule-dated (unverified); SWS and regional CPI dates are verified |
| Excluded | News (carrier files; E7 sufficiency 0/100); rice (forward-filled cells); `food_cpi` index level (no approved 2026 source); fuel, FX, remittances, climate (blocked source tables) |

**New features**, all from labels published before the origin:

- `anchor_dev`: the provincial deviation (d) of the latest published label;
- `lps_change`: change in stress between the two latest published labels;
- `dev_change`: change in d between those two labels.

## 3. Folds

- **Outer folds:** the same 7 test quarters as E9 (2023-Q4 to 2025-Q4), with ≥ 8 eligible training quarters. Training uses only labels published before the origin (label vault).
- **Main evidence:** the expanding window. **Sensitivity:** a rolling window of the last 8 eligible training quarters.
- **Inner folds** (for configuration selection, inside each outer training set only): walk-forward over the training quarters. Each inner target needs ≥ 6 inner training quarters published before its origin.
- **Reuse:** all 7 outer quarters were used in E1–E9, so **every E11 result is exploratory.** Any selection made by looking at outer results is labelled as such.

## 4. Candidates (all prespecified)

**Baselines:**

| Arm | Output | Definition |
|---|---|---|
| B1 carry-forward | Stress | Latest published stress |
| B2 regional | Stress | Latest published SWS |
| B3 S1 formula rule | Stress | SWS input + 2 × `cpi_rel` (T−2) |
| B4 majority | Class only | Majority class of the fold's training labels |

**LightGBM structures:**

| Structure | What the model predicts | How the stress forecast is formed |
|---|---|---|
| Direct | Stress | The model output |
| Decomposed | The provincial deviation d | Stress = SWS input + 2 × predicted d; the regional part stays the latest SWS |
| Residual | The correction (stress − S1 rule) | Stress = S1 rule + predicted correction. This tests whether ML adds anything to the formula. |

**Feature sets:**

| Set | Features |
|---|---|
| core | `last_published_stress`, `sws_hunger`, `sws_change` |
| core_plus | core + `lps_change`, `anchor_dev` |
| compact | core + `cpi_rel`, `cpi_rel_lag1`, `food_cpi_yoy`, `food_cpi_yoy_lag1`, `cpi_dev` |
| expanded | compact + `poverty_incidence`, `headline_cpi`, `food_minus_headline_yoy` (+ lag1), `unemployment_rate` |
| provincial (decomposed only) | `cpi_rel`, `cpi_rel_lag1`, `anchor_dev`, `dev_change`, `cpi_dev`, `food_cpi_yoy`, `food_cpi_yoy_lag1` |
| residual (residual only) | core_plus + `cpi_rel`, `cpi_rel_lag1`, `cpi_dev` |

**Configurations** (simplest first). All share seed 42, `deterministic=True`, one thread, and **no class weights**: training folds are at most about 68% HIGH, which is not severe enough to justify weights.

| Config | Settings |
|---|---|
| C2 stumps | depth 1, 2 leaves, `min_child_samples` 10, 100 trees, lr 0.03, L2 10 |
| C1 shallow, regularized | depth 2, 3 leaves, `min_child_samples` 10, 50 trees, lr 0.05, L2 5 |
| C0 E9 default | 4 leaves, `min_child_samples` 5, 100 trees, lr 0.05 |
| C3 moderate | depth 3, 4 leaves, `min_child_samples` 8, 200 trees, lr 0.02, L1 1, L2 5 |

**Monotone +1** on `sws_hunger` and `last_published_stress` applies only in the direct structure.

**Runs:**

- **Fixed-configuration grid (exploratory):**
  - direct × {core, core_plus, compact, expanded} × 4 configs;
  - decomposed × provincial × 4;
  - residual × residual × 4.
- **Nested (primary):** for each of those 6 structure-and-feature combinations, the inner folds choose a configuration per outer fold by the lowest inner MAE (ties → simpler). With no inner evidence, the simplest config (C2) is used.
- **Classifiers:** direct × {core, compact}, with the configuration nested by inner Brier score. HIGH if p ≥ 0.50. **Calibration** follows the E6 rule (Platt only if ≥ 8 inner out-of-fold quarters and ≥ 10 rows per class); otherwise probabilities are uncalibrated.
- **INSUFFICIENT_DATA:** the E9 rule, identical for all arms.

## 5. Metrics

| Output | Metrics |
|---|---|
| Stress | MAE; RMSE; bias (mean predicted − true); regional-level error; per-quarter and per-province MAE; predicted vs true spread; concordant pairs out of 10; Spearman; ranking persistence |
| Classification | Accuracy; balanced accuracy; per-class precision, recall and F1; confusion matrix; class counts; ROC-AUC and PR-AUC only with ≥ 5 rows per class |
| Probabilities | Brier only |

**Uncertainty:** quarter-cluster bootstrap (2,000 draws, seed 42) of per-quarter MAE differences against B1, B2 and B3, plus the exact sign-flip p over 7 quarters (descriptive). No row-level test: 35 rows ≠ 35 independent observations.

## 6. Recommendation rule (prespecified; applied to the six nested candidates)

LightGBM is recommended over the S1 rule only if a nested candidate meets **all** of:

1. lower MAE than B3 in **≥ 5 of 7** quarters;
2. mean per-quarter MAE difference vs B3 **< 0**, with the bootstrap 95% upper bound **< 0**;
3. concordant share **≥ B3's**;
4. the same direction (mean difference < 0) under the **rolling window**.

**Otherwise the S1 rule stays primary and LightGBM is reported as experimental.** No non-inferiority claim is made, because no margin was set.

## 7. Diagnostics

- Within-quarter variance share of each feature (how much provincial variation it carries).
- Correlation of d_T with `anchor_dev` and `cpi_rel`, descriptive on 2021–2025 labels.
- Gain share of regional vs provincial features.
- Training vs test MAE.
- Inner-selection choices per fold.
- Metrics with and without the 2 LOW rows (classification only).

## 8. Stop rules

The run stops on any of:

- an allowlist hash mismatch;
- a guard denial;
- the rebuilt frame differing from the E9 frame;
- τ0 not equal to 10.8433 ± 0.001;
- a quarter after 2025-Q4 appearing anywhere;
- non-determinism (two identical prediction passes required).

## 9. Not claimed

- That a configuration chosen by looking at the outer quarters generalizes.
- Calibrated probabilities.
- A food-insecurity probability.
- Blind or prospective performance (the Q4 forecast is the separate E10 activity).
- That reaching 75% accuracy means success.

## 10. Deviations (filled in after the run, if any)

None yet.
