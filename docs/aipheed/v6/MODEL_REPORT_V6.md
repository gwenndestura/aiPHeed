# v6 Model report

**Status: every table is DEVELOPMENT.** The rows were all seen before v6. The CONFIRMATORY tier has 0 scorable rows (§7).

**Sources:**
- **Command:** `python -I backend/scripts/v6_validate.py` (seed 2026; moving-block bootstrap, block 3, 10 000 draws).
- **Outputs:** `results/v6_metrics.csv`, `v6_reliability.csv`, `v6_selection_log.csv`, `v6_selected_by_issue.csv`, `v6_lgbm_fits.csv`, `v6_dm_hln.csv`, `v6_overfitting.csv`, `v6_by_period.csv`, `v6_window_sensitivity.csv`, `v6_loao_lead2.csv`, `v6_verdict.json`, `v6_validate_run.txt`.
- **Verification:** all VERIFIED. A rerun left the results byte-identical.
- **Rows:** asserted equal to the hashed v4 DEVELOPMENT-TEST tier (44 / 40 / 36 / 32; Lead 2 = 2024-Q1 … 2026-Q3).

**Exploratory results** are only in §6 and `DEVIATIONS.md`.

## 1. Selection and LightGBM verdict

**The pre-registered rule kept PERSIST at all 22 issues,** also under the 2022-Q1 training window. **LightGBM did not beat persistence, so it is not served** (PREREGISTRATION §8).

At the served issue (2026-10-01; 14 inner quarters):

| Challenger vs PERSIST | Δ within | Inner 95 % CI |
|---|---|---|
| LL-K | +0.054 | [−0.054, +0.179] |
| LGBM-D | −0.071 | [−0.179, +0.018] |
| LGBM-D-S | −0.089 | [−0.196, 0.000] |

**How much LightGBM was actually tested:**
- 54 of 84 fits had < 30 training rows, so no model existed and they forecast persistence. All no-model fits are in that class.
- **At Lead 2 a model exists only from issue 2025-01-01, so it never forecast the 2024 surge.** Those 16 rows equal persistence, and its record rests on **24 rows**.
- Exogenous features entered at 34 of 84 fits, ONI most often.
- The learned shrinkage weight was w = 0 at 65 fits (54 of them no-model), 1.0 at 17, and 0.5 and 0.75 at 1 each.
- Best iteration moved widely between neighbouring issues (Lead 2: 198, 123, 150, 195, 3, 14, 169, 20), which is a sign of instability (INFERRED).

## 2. Results

CIs are block bootstrap. **Proposed** = the published-margin tolerance, `PROPOSED_NOT_ADOPTED`.

| Lead | Model | n | Frozen % [CI] | Proposed % [CI] | MAE | RMSE | Bias | High-tercile bias | Sharp increases within | Variance ratio | Correlation | 80 % coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **V6 (= PERSIST)** | 44 | 47.7 [22.7, 68.2] | 61.4 [43.2, 75.0] | 5.05 | 6.76 | −2.38 | −6.75 | 0/15 | 1.37 | 0.35 | 0.64 |
| 1 | LL-K | 44 | 40.9 [9.1, 65.9] | 56.8 | 5.25 | 7.10 | −3.02 | −7.79 | 1/15 | 1.25 | 0.29 | 0.61 |
| 1 | LGBM-D | 44 | 36.4 [20.5, 45.5] | 59.1 | 5.61 | 7.25 | −2.19 | −7.36 | 0/15 | 1.61 | 0.30 | 0.66 |
| 1 | LGBM-D-S | 44 | 38.6 [20.5, 47.7] | 59.1 | 5.78 | 7.48 | −2.28 | −7.58 | 0/15 | 1.65 | 0.27 | 0.64 |
| **2** | **V6 (= PERSIST)** | **40** | **40.0 [22.5, 62.5]** | **50.0 [32.5, 67.5]** | 5.98 | 7.71 | −3.07 | −7.66 | 0/16 | 1.94 | 0.20 | 0.725 |
| 2 | LL-K | 40 | 37.5 [12.5, 65.0] | 55.0 [22.5, 77.5] | 5.60 | 7.63 | −3.84 | −8.27 | 0/16 | 1.54 | 0.18 | 0.675 |
| 2 | **LGBM-D** | 40 | **30.0 [15.0, 42.5]** | 40.0 [22.5, 55.0] | **7.50** | 8.95 | −2.83 | −8.12 | 0/16 | 2.80 | 0.10 | 0.65 |
| 2 | LGBM-D-S | 40 | 27.5 [12.5, 40.0] | 42.5 [22.5, 57.5] | 7.50 | 8.93 | −2.99 | −8.25 | 0/16 | 2.73 | 0.10 | 0.65 |
| 3 | V6 | 36 | 36.1 [11.1, 55.6] | 52.8 | 6.46 | 8.49 | −3.83 | −9.45 | 0/15 | 2.48 | −0.01 | 0.75 |
| 3 | LGBM-D | 36 | 30.6 [8.3, 47.2] | 47.2 | 7.38 | 9.21 | −3.40 | −9.89 | 0/15 | 3.23 | −0.07 | 0.67 |
| 4 | V6 | 32 | 37.5 [21.9, 65.6] | 59.4 | 6.51 | 8.99 | −4.56 | −10.06 | 0/15 | 2.80 | −0.09 | 0.81 |
| 4 | LGBM-D | 32 | 43.8 [21.9, 68.8] | 59.4 | 6.31 | 8.90 | −4.16 | −9.75 | 2/15 | 2.94 | −0.08 | 0.81 |

**Baselines at Lead 2, same rows (frozen):** TREND-D 30.0 %; CLIM 15.0 %; RIDGE-ALL 39.3 % (28 rows); SEAS-LLM 45.0 %; HFM-X 50.0 %; V2 and V4 40.0 % (`v6_metrics.csv`).

**LGBM-D and LGBM-D-S share the exact Lead-2 MAE by coincidence:** they differ on 8 rows, where the absolute errors cancel exactly. Checked, not a bug.

## 3. "Beats every other model" (8 baselines, Holm, α = 0.05)

**Lead 2, frozen tolerance, V6.** Δ within and Holm-adjusted one-sided moving-block p; DM-HLN on squared error is secondary (negative t favours V6):

| Baseline | PERSIST | TREND-D | CLIM | RIDGE-ALL | HFM-X | SEAS-LLM | V2 | V4 |
|---|---|---|---|---|---|---|---|---|
| Δ within | 0 | +0.10 | +0.25 | +0.07 | −0.10 | −0.05 | 0 | 0 |
| Holm p | 1.0 | 0.81 | 0.00 | 0.45 | 1.0 | 1.0 | 1.0 | 1.0 |
| DM-HLN t (one-sided p) | identical | −1.77 (0.055) | −1.51 (0.083) | −0.66 (0.27) | +0.83 (0.79) | +0.38 (0.64) | identical | identical |

**Verdict: NO** at every lead, under both tolerances.

**LGBM-D at Lead 2: NO.** It is below PERSIST by 10 points, below HFM-X by 20, and above only CLIM. DM-HLN vs PERSIST: t = +1.59 (it has the larger error), one-sided p = 0.93.

## 4. The 75 % claim

| Model, tolerance | Share | Block 95 % CI | Verdict |
|---|---|---|---|
| V6, frozen | 0.40 | [0.225, 0.625] | `DEVELOPMENT_ONLY` |
| V6, proposed | 0.50 | [0.325, 0.675] | `DEVELOPMENT_ONLY` |
| LGBM-D, frozen | 0.30 | [0.15, 0.425] | `DEVELOPMENT_ONLY` |
| LGBM-D-S, frozen | 0.275 | [0.125, 0.40] | `DEVELOPMENT_ONLY` |

## 5. Reliability, generalisation, overfitting (frozen N1–N7)

- **V6, all leads: NOT_RELIABLE.**
  - N2, N4 and N5 fail at every lead.
  - N1 fails at Leads 3–4.
  - N7 fails at Lead 1.
  - LGBM-D and LGBM-D-S also fail N3 at Leads 1–3.
- **Train / inner / outer MAE, Lead 2:**

  | Model | Train (change) | Inner | Outer |
  |---|---|---|---|
  | PERSIST | — | 4.56 | 5.98 |
  | LL-K | — | 4.10 | 5.60 |
  | LGBM-D | **3.34** | 4.86 | **7.50** |
  | LGBM-D-S | 3.63 | 4.86 | 7.50 |

  LightGBM's gap of about 4 points is the largest of any model, despite the heavy regularisation: it overfits.
- **By period, Lead 2:**

  | Period | n | V6 within / MAE | LGBM-D within / MAE | HFM-X within | SEAS-LLM within |
  |---|---|---|---|---|---|
  | 2024 surge | 16 | 0.25 / 8.49 | 0.25 / 8.49 (no model; equals persistence) | 0.56 | 0.06 |
  | 2025–26 | 24 | 0.50 / 4.31 | **0.33 / 6.84** | 0.46 | 0.71 |

  In 2025–26 LightGBM kept predicting rises learned from the surge.
- **Window sensitivity (2022-Q1 start, same 40 rows):** LGBM-D 0.425, MAE 5.86; PERSIST 0.40, MAE 5.98; LL-K 0.375, MAE 5.65. The ranking changes with the window, because fewer rows means more no-model fallback. PERSIST is still selected at all issues.

## 6. Controls

| Control | Pre-registered expectation | Observed | Status |
|---|---|---|---|
| Shuffle-target | LGBM gains nothing over PERSIST | **LGBM-D 0.40 vs PERSIST 0.275;** rule picked LGBM-D at 1 of 22 issues | **EXPECTATION NOT MET** (DEVIATIONS #3) |
| Future shift, cutoff after the target's publication | Within far above the honest run | PERSIST 1.00 vs 0.40 | Met |
| Injected round on the issue day or later | Forecast unchanged | Unchanged; the same round a day earlier changes it | Met (tests) |
| Snapshot used at another issue | `LeakageError` | Raised | Met (test) |

**EXPLORATORY** (`DEVIATIONS.md`): label permutation on the real series gives mean 0.355, range 0.30–0.475, against honest LGBM-D 0.30. So there is no sign of leakage and no sign of skill.

## 7. Confirmatory tier

**Seals:**
- `sealed/V6_PROSPECTIVE_SEAL.csv` (`1309a556…`; V6 + 4 candidates; issues 2026-07-01 and 2026-10-01);
- `sealed/V6_BASELINE_SEAL.csv` (`495e6a93…`; RIDGE-ALL and HFM-X, reproduced exactly on 12 historical rows before sealing);
- the v4 and v2 seals for the other baselines.

**All 8 baselines now have forecasts at the same cutoff.**

**Scorer:** `v6_score_sealed.py` ran once: **0 of 336 rows scorable, so every claim at every lead is `NOT_YET_TESTABLE`** (`sealed/ACCESS_LOG.md`, `results/v6_sealed_verdict.json`).
