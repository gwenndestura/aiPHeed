# E25 Frozen Evaluation Protocol: study window 2021-Q1 to 2026-Q2

**Written and hashed before any E25 model run.** `runner/PROTOCOL_SHA256.txt` holds the hash. Every E25 runner refuses to start if this file changed.

**Not blind.** All 2021–2026 outcomes were examined in E9–E24v2. **Every E25 result is development evidence.** The only unseen test is the prospective seals (Section 8).

## 1. Window and data

**Window.**

- Rows from 2021-Q1 to **2026-Q2** (`AUTHORIZED_LAST_QUARTER`).
- Monthly values from 2021-01 to **2026-06**.
- Every loaded table is asserted at runtime to contain no row outside this window. **A violation stops the run.**

**Allowed inputs** (hash-verified on every read):

| Input | Coverage | Basis |
|---|---|---|
| E12 `realized_components_2021_2025.csv` (S1, H, D) and `details.json` (SWS rounds with verified publication dates) | 2021–2025 | E17/E18 allowlist |
| `features_fused.parquet` | Read-time filter 2021-Q1…2025-Q4 | E17/E18 allowlist |
| `config/governing_model.json` | — | E17/E18 allowlist |
| Provincial food CPI YoY, January–June 2026, and the March/June 2026 SWS rounds (used as **labels only**) | 2026 H1 | E18 authorization |
| E24v2 `acquisition/cpi_index_2021_2025_ACP22.csv` | 2021–2025 rows only | Public PSA, pinned by the SHA-256 in E24v2's manifest. **Pending your confirmation (A6).** Used only to build Dnow. |
| LGU inputs (E24 identity-verified table: 2020 census population released 2021, 2021 SAE) | Static | E17 allowlist via E24. **The 2020 census reference date is flagged in the report.** |

**Not loaded:** any E24v2 file containing a pre-2021 row; the E24v2 poverty/subsistence tables (they contain 2018 rows); anything protected.

## 2. Pre-2021 information removed from in-window rows (applied to every model)

For a `features_fused` row of quarter q:

| Feature | Rule |
|---|---|
| `*_lag1` and `*_accel` (accel = x(q) − x(q−1)) | Set missing if q = 2021-Q1 |
| `FSSI_lag2` | Set missing if q ≤ 2021-Q2 |
| `cpi_dev` | Recomputed as food_cpi_yoy(q) − mean of food_cpi_yoy over quarters q−4…q−1 **that are ≥ 2021-Q1** (at least 2), else missing |

**Year-on-year rates** (food_cpi_yoy, ofw_remit_yoy_pct, D) are kept. They are the published rate of an in-window month or quarter, and they are the approved label's own definition.

**Missing values** are handled as in E23/E24: median imputation (LR), native handling (LightGBM).

**Dnow** (months 1–2 of quarter t, provincial YoY minus the five-province mean):

- from in-window indices, so the first YoY is 2022-01 and the first Dnow is 2022-Q1;
- 2026-Q1/Q2 come from the authorized published YoY.

**In-window comparability check:** the quarterly D derived from these indices for 2022–2025 vs E12's approved D (reported; no pass/fail use).

## 3. Targets, origins, leads (unchanged rules)

**Targets.**

- **T1 (approved, required):** S1 = H + 2D > τ, with τ = median S1 over labels published before O(t) (E23 rule).
- **T2 (exploratory):** D > 0.

**Origins, leads and labels.**

- Origin O(t) = 00:00 PHT on the first day of quarter t+1, for t = 2021-Q1…2026-Q1.
- Leads k = 1…8.
- Target t+k ≤ 2026-Q2, and the label must exist.
- **Label publication (T1):** quarter ≤ t−1 and every definition-A SWS round of that quarter published before O(t).
- **Label publication (T2):** quarter ≤ t−1.

**Independent unit:** the origin quarter. Province rows are never treated as independent.

## 4. Models: 12 per target, fixed now

**No model is added after any result is seen.**

| # | ID | Role | Specification |
|---|---|---|---|
| 1 | B1_naive_persistence | Required (Obj. 4-I, H3) | Last published label |
| 2 | B2_lr_combined | Required | LR on news + government (E23 spec) |
| 3 | B3_lr_gov_only | Required | LR on government |
| 4 | B4_lr_nlp_only | Required | LR on news |
| 5 | B5_lgbm_gov_only | Required | Nested LightGBM on government (E23 16-configuration grid) |
| 6 | B6_lgbm_nlp_only | Required | Nested LightGBM on news |
| 7 | PROPOSED_lgbm_combined | Required (proposed) | Nested LightGBM on news + government |
| 8 | B1p_calibrated_persistence | Reference | Laplace rate of HIGH among training pairs with the same last label |
| 9 | REF_always_HIGH | Reference | Score 1.0. Uses the test class balance; not a forecaster. |
| 10 | MAJ_training_majority | Diagnostic | Training majority class |
| 11 | **T1: PCF21 (FINAL_E25)** / **T2: M4_21 (FINAL_E25)** | Candidate | **PCF21:** E24v2's PCF with the D part trained on 2021+ pairs only (t′ ≥ 2021-Q2). **M4_21:** least squares without intercept of D(t′+k) on [Dnow(t′), D(t′−1)], 2021+ pairs only (t′ ≥ 2022-Q1) |
| 12 | **T1: PCF21_NOW** / **T2: M3_21** | Candidate | **PCF21_NOW:** PCF21 with M4_21 as its D part. **M3_21:** least squares without intercept on D(t′−1) only (t′ ≥ 2021-Q2) |

**Candidates:** 2 per target, 4 in total. All other arms from E24/E24v2 are **not** candidates in E25.

## 5. Minimum training and row sets

**Minimum training (every model, every row):** ≥ 8 distinct labelled training target quarters at that lead.

- PCF candidates also need ≥ 8 distinct fieldwork quarters among the SWS rounds usable at the origin.
- A model below its minimum has no prediction at that origin.

**Row sets.** Every table compares models on **identical rows**.

| Set | Rows | Models |
|---|---|---|
| **R_A** | Origins t ≤ 2025-Q4 where models 1–10 and candidate 11 (T1) / 12 (T2) all have predictions | All 10 + that candidate |
| **R_B** | Same, for the NOW-type candidate (T1: 12; T2: 11) | All 10 + that candidate |
| **P** (secondary) | Origins t ≤ 2026-Q1 where the candidate, B1 and B1p have predictions. Adds the origin whose features E23/E24 lack. | Candidate, B1, B1p, REF_always_HIGH |

FINAL_E25 is judged on R_A (T1) and R_B (T2).

## 6. Statistics, evaluability and criteria (E24 definitions, unchanged)

**Metrics:** accuracy, balanced accuracy, precision, recall, F1, ROC-AUC, Brier, confusion counts.

**Tests:**

- exact one-sided sign-flip on per-origin accuracy and Brier differences (Monte Carlo above 16 origins, seed 20261013);
- Holm across B1–B6 for accuracy;
- origins better/worse;
- leave-one-origin-out range;
- paired AUC permutation when both classes are present.

**Evaluable** = ≥ 8 origins **and** ≥ 5 HIGH **and** ≥ 5 LOW in that row set. Otherwise every result at that lead is labelled **"not evaluable"**.

**Criteria C1–C9 for FINAL_E25** (E24 definitions):

- the strongest applicable baseline = the highest accuracy among B1–B6 and B1p (ties: lower Brier);
- REF_always_HIGH is reported beside it;
- C9 = NOT ASSESSABLE (no in-scope unseen quarters are scored yet).

**The forecasting goal is met only if C1–C9 all hold.**

**Training size reported:** for every model and lead, the number of training target quarters (minimum–maximum over origins).

## 7. Audits (descriptive)

- **Timing assertions in every fold:**
  - every training label published before O(t);
  - no training target ≥ t;
  - features of quarter t (news) and t−1 (government);
  - SWS rounds published before O(t).
- **Masking audit:** the number of cells masked per feature.
- **Constant / province-invariant features:** per feature, the share of quarters where all five provinces share one value; features constant over 2021–2025.
- **Label construction vs Chapter I:** recorded in the report; no change to the label.
- **Noise ceiling:** as E24v2 §7, recomputed.

## 8. Prospective seals

**The E24v2 seals are kept unchanged.** Only their in-scope arms count:

- T1: B1, B1p, M2;
- T2: B1.

**New E25 seals** (`runner/seal_e25.py`):

- only at an origin later than every sealed origin;
- only when every input of that origin is inside the authorized window;
- never twice at the same origin;
- scored only after you authorize the outcomes.

**A generalization claim** needs ≥ 8 scored origins and ≥ 5 LOW (and ≥ 5 HIGH) rows.

## 9. No tuning

- No label, threshold, window, rule, feature set or hyperparameter grid is changed in response to results.
- If no model beats the baselines, the report says so.
