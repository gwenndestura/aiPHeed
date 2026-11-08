# v4 Model report

**Status:**
- **Every number below is DEVELOPMENT.** The rows were all seen before v4 (EVALUATION_DESIGN §2).
- **The sealed tier has 0 scorable rows,** so every confirmatory claim is NOT_YET_TESTABLE (§6).

**Source of all numbers:**
- **Command:** `python -I backend/scripts/v4_validate.py` (seed 2026; moving-block bootstrap with block 3 and 10 000 draws; inner 2 000 draws). All VERIFIED.
- **Outputs:** `v4/results/v4_metrics.csv`, `v4_reliability.csv`, `v4_selection_log.csv`, `v4_selected_by_issue.csv`, `v4_deltax_feature_entries.csv`, `v4_loao_lead2.csv`, `v4_overfitting.csv`, `v4_verdict.json`, `v4_validate_run.txt`.
- **Rerun:** byte-identical results files after the rerun (`git status` clean).

**Rows:** DEVELOPMENT-TEST = the frozen S-U rows (44 / 40 / 36 / 32; Lead 2 = 10 target quarters, 2024-Q1 … 2026-Q3).

## 1. Selection and the exogenous route

**The pre-registered rule kept PERSIST at all 22 issues** (`v4_selected_by_issue.csv`). No challenger's paired inner CI lay above 0. At the served issue (2026-10-01; 14 inner quarters):

| Challenger | Δ within | Inner 95 % CI |
|---|---|---|
| LL-K | +0.054 | [−0.054, +0.179] |
| DELTA-X | −0.036 | [−0.143, +0.054] |
| DELTA-X-LLK | −0.054 | [−0.232, +0.107] |

**The stability rule admitted features at 34 of 84 issue × lead fits** (`v4_deltax_feature_entries.csv`):
- ONI is the most frequent;
- rice CPI YoY, unemployment change, shortage news and typhoons enter intermittently;
- **the admitted set changes from issue to issue,** which is itself evidence of instability.

**DELTA-X lowered the within share at every lead.** At Lead 2 it scored 0.375 vs 0.40, with MAE 6.49 vs 5.98. **The exogenous route failed under the pre-registered rule** (PREREGISTRATION §8).

## 2. Results (DEVELOPMENT-TEST)

**Columns:**
- **Frozen:** within the frozen tolerance, with the block-bootstrap 95 % CI.
- **Amended*:** within the published-margin tolerance. *PROPOSED_NOT_ADOPTED: needs adviser sign-off; development values were already known in v3.

| Lead | Model | n | Frozen % [CI] | Amended* % | MAE | RMSE | Bias | High-tercile bias | Sharp increases within | Variance ratio | Correlation | 80 % coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **V4 (= PERSIST)** | 44 | 47.7 [22.7, 68.2] | 61.4 | 5.05 | 6.76 | −2.38 | −6.75 | 0/15 | 1.37 | 0.35 | 0.64 |
| 1 | LL-K | 44 | 40.9 | 56.8 | 5.25 | 7.10 | −3.02 | −7.79 | 1/15 | 1.25 | 0.29 | 0.61 |
| 1 | DELTA-X | 44 | 34.1 | 50.0 | 5.74 | 7.05 | −2.28 | −7.05 | 1/15 | 1.61 | 0.35 | 0.61 |
| 1 | DELTA-X-LLK | 44 | 25.0 | 43.2 | 6.54 | 7.95 | −4.87 | −9.83 | 1/15 | 1.15 | 0.29 | 0.52 |
| **2** | **V4 (= PERSIST)** | **40** | **40.0 [22.5, 62.5]** | **50.0** | 5.98 | 7.71 | −3.07 | −7.66 | 0/16 | 1.94 | 0.20 | 0.725 |
| 2 | LL-K | 40 | 37.5 | 55.0 | 5.60 | 7.63 | −3.84 | −8.27 | 0/16 | 1.54 | 0.18 | 0.675 |
| 2 | DELTA-X | 40 | 37.5 | 42.5 | 6.49 | 7.93 | −3.06 | −7.30 | 2/16 | 2.32 | 0.25 | 0.65 |
| 2 | DELTA-X-LLK | 40 | 22.5 | 45.0 | 6.73 | 8.05 | −4.67 | −8.97 | 0/16 | 1.65 | 0.23 | 0.55 |
| 3 | V4 | 36 | 36.1 [11.1, 55.6] | 52.8 | 6.46 | 8.49 | −3.83 | −9.45 | 0/15 | 2.48 | −0.01 | 0.75 |
| 4 | V4 | 32 | 37.5 [21.9, 65.6] | 59.4 | 6.51 | 8.99 | −4.56 | −10.06 | 0/15 | 2.80 | −0.09 | 0.81 |

**Baselines at Lead 2, same rows (frozen):**
- TREND-D 30.0 %;
- CLIM 15.0 %;
- RIDGE-ALL 39.3 % (28 rows);
- SEAS-LLM 45.0 %;
- HFM-X 50.0 %;
- V2 40.0 % (`v4_metrics.csv`).

## 3. "Beats every other model" (PREREGISTRATION §5; one-sided moving-block p, Holm, α = 0.05)

**Lead 2, frozen tolerance.** Δ within (V4 − baseline) and Holm-adjusted p:

| Baseline | PERSIST | TREND-D | CLIM | RIDGE-ALL | HFM-X | SEAS-LLM | V2 |
|---|---|---|---|---|---|---|---|
| Δ | 0 | +0.10 | +0.25 | +0.07 | −0.10 | −0.05 | 0 |
| Holm p | 1.0 | 0.68 | 0.00 | 0.38 | 1.0 | 1.0 | 1.0 |

**Verdict:**
- **NO** under the frozen tolerance at every lead.
- **NO** under the amended tolerance at every lead (`v4_verdict.json` → `beats_all_development`).
- V4 beats only CLIM. It cannot beat itself (PERSIST, V2), and HFM-X and SEAS-LLM are higher on these rows.

## 4. The 75 % claim on DEVELOPMENT data

| Tolerance | Share | Block 95 % CI | Verdict |
|---|---|---|---|
| Frozen | 0.40 | [0.225, 0.625] | `DEVELOPMENT_ONLY` |
| Amended (proposed) | 0.50 | [0.325, 0.675] | `DEVELOPMENT_ONLY` |

**Both upper bounds are below 0.75.** Had these been sealed rows, both would read REJECTED. They are not sealed rows, so this is not a confirmatory verdict.

## 5. Reliability, generalisation and controls

- **Frozen N1–N7** (`v4_reliability.csv`): V4 and all candidates are NOT_RELIABLE at Leads 1–4. N2, N4 and N5 fail; N1 fails at Leads 3–4.
- **Leave-one-area-out, Lead 2** (`v4_loao_lead2.csv`; parameters estimated without the held-out area):

  | Model | Held out | Pooled |
  |---|---|---|
  | LL-K | 0.35 | 0.375 |
  | DELTA-X | 0.35 | 0.375 |
  | PERSIST | — | 0.40 |

  **Within share by area:**

  | Area | PERSIST | LL-K (held out) | DELTA-X (held out) |
  |---|---|---|---|
  | Metro Manila | 0.7 | 0.5 | 0.6 |
  | Balance Luzon | 0.3 | 0.3 | 0.2 |
  | Visayas | 0.1 | 0.3 | 0.2 |
  | Mindanao | 0.5 | 0.3 | 0.4 |

  **No spatial generalisation gain.** Balance Luzon, the area that contains CALABARZON, scores 0.2–0.3.
- **Overfitting** (`v4_overfitting.csv`), inner vs outer Lead-2 MAE:

  | Model | Inner MAE | Outer MAE |
  |---|---|---|
  | PERSIST | 4.56 | 5.98 |
  | LL-K | 4.10 | 5.60 |
  | DELTA-X | 4.43 | 6.49 |
  | DELTA-X-LLK | **3.82** | **6.73** |

  The exogenous models gain on their inner folds and lose outside them: the signature of fitting noise.
- **Leakage controls:**
  - shuffle-target: V4 and PERSIST 0.275, and PERSIST was selected at all issues;
  - future-shift positive control: PERSIST 1.00;
  - injected rounds and cross-issue snapshots are refused (tests);
  - the v2 mutation checks still apply to the shared `as_of` and lead code.

## 6. Sealed tier

**Seal:** `v4/sealed/V4_PROSPECTIVE_SEAL.csv`, SHA-256 `7ac72fec…ad0e`.
- **Contents:** 224 rows. V4, the 4 candidates, TREND-D, CLIM and SEAS-LLM at the P-DASH issues 2026-07-01 and 2026-10-01, for targets 2026-Q4 … 2027-Q3.
- **Baselines added at scoring:** V2 from the v2 seal; HFM-X from the E134 seal, which saw more information, so the comparison is conservative. RIDGE-ALL is not available (DEVIATIONS #3).

**Scorer:** `v4_score_sealed.py` ran on 2026-11-01. **0 of 280 rows were scorable,** so every claim at every lead is `NOT_YET_TESTABLE` (`v4/results/v4_sealed_verdict.json`, `v4/sealed/ACCESS_LOG.md`).
