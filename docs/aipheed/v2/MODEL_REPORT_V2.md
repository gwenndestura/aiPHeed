# v2 Model report

**Status of every number here: DEVELOPMENT.**
- All 2021–2026-Q3 SWS quarters had been seen before v2 was designed (`PREREGISTRATION.md` §7).
- No historical quarter could be sealed. The sealed confirmation set is future quarters only, and it has **0 scored quarters today** (§8).

**Source of all numbers:**
- **Command:** `python -I backend/scripts/v2_validate.py` (seed 2026; 10 000 outer and 2 000 inner bootstrap draws). All VERIFIED.
- **Outputs:** `results/v2_metrics.csv`, `v2_reliability.csv`, `v2_selection_log.csv`, `v2_selected_by_issue.csv`, `v2_overfitting.csv`, `v2_by_period.csv`, `v2_window_sensitivity.csv`, `v2_verdict.json`, `v2_validate_run.txt`.

**Rows:** the frozen S-U rows (n_obs ≥ 8), asserted identical to the E136 rows in code:
- 44 / 40 / 36 / 32 rows at Leads 1–4;
- 11 / 10 / 9 / 8 target quarters;
- Lead 2 covers 2024-Q1 … 2026-Q3.

## 1. Selection (mechanical, PREREGISTRATION §3)

**The inner-fold rule kept PERSIST at all 22 issues** (`v2_selected_by_issue.csv`):
- Up to 2024-04-01 there were fewer than 6 inner target quarters, so no replacement was possible.
- From 2024-07-01 there were enough quarters, but no challenger's paired 95 % CI lay above 0.

**At the served issue (2026-10-01), inner rows = 56 over 14 quarters:**

| Challenger vs PERSIST | Δ within | Paired 95 % CI | Replaces? |
|---|---|---|---|
| LL | −0.018 | [−0.089, +0.054] | No |
| LL-K | +0.054 | [−0.054, +0.179] | No |

**So V2 = persistence,** and the served forecast is "last observed value carried forward".

## 2. Results on the outer rows (S-U, P-DASH)

The 95 % CIs are block bootstraps over target quarters. "Δ vs PERSIST" is the paired difference in within share.

| Lead | Model | n within / n | % within [95 % CI] | Δ vs PERSIST [CI] | MAE | RMSE | Bias | High-tercile bias | Sharp increases within | Variance ratio | Correlation | 80 % coverage (width) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **V2 (= PERSIST)** | 21/44 | 47.7 [31.8, 65.9] | 0 | 5.05 | 6.76 | −2.38 | −6.75 | 0/15 | 1.37 | 0.35 | 0.64 (12.1) |
| 1 | LL | 19/44 | 43.2 [25.0, 61.4] | −0.045 [−0.11, 0] | 5.06 | 6.82 | −2.74 | −7.22 | 0/15 | 1.28 | 0.34 | 0.66 |
| 1 | LL-K | 18/44 | 40.9 [20.5, 61.4] | −0.068 [−0.14, 0] | 5.25 | 7.10 | −3.02 | −7.79 | 1/15 | 1.25 | 0.29 | 0.61 |
| **2** | **V2 (= PERSIST)** | **16/40** | **40.0 [25.0, 57.5]** | 0 | 5.98 | 7.71 | −3.07 | −7.66 | 0/16 | 1.94 | 0.20 | **0.725** (15.7) |
| 2 | LL | 15/40 | 37.5 [17.5, 57.5] | −0.025 [−0.125, +0.075] | 5.67 | 7.56 | −3.52 | −7.98 | 0/16 | 1.67 | 0.20 | 0.78 |
| 2 | LL-K | 15/40 | 37.5 [17.5, 57.5] | −0.025 [−0.125, +0.075] | 5.60 | 7.63 | −3.84 | −8.27 | 0/16 | 1.54 | 0.18 | 0.68 |
| 3 | **V2** | 13/36 | 36.1 [13.9, 58.3] | 0 | 6.46 | 8.49 | −3.83 | −9.45 | 0/15 | 2.48 | −0.01 | 0.75 (17.1) |
| 4 | **V2** | 12/32 | 37.5 [12.5, 62.5] | 0 | 6.51 | 8.99 | −4.56 | −10.06 | 0/15 | 2.80 | −0.09 | 0.81 (19.0) |

**Context baselines, same rows, Lead 2** (re-scored from E136 predictions; never selectable):

| Model | n within / n | % within [CI] | Δ vs PERSIST [CI] | MAE |
|---|---|---|---|---|
| TREND-D | 12/40 | 30.0 [20.0, 42.5] | −0.10 [−0.20, 0] | 7.17 |
| CLIM (expanding mean) | 6/40 | 15.0 [2.5, 27.5] | −0.25 [−0.40, −0.10] | 7.75 |
| RIDGE-ALL (its 28 rows) | 11/28 | 39.3 [25.0, 53.7] | −0.07 [−0.18, +0.07] | 7.36 |
| SEAS-LLM | 18/40 | 45.0 [22.5, 67.5] | +0.05 [−0.10, +0.20] | 5.72 |
| HFM-X | 20/40 | 50.0 [32.5, 67.5] | +0.10 [−0.125, +0.325] | 4.87 |

Leads 1, 3 and 4 for the context models are in `v2_metrics.csv`.

**Reading:**
- No model, old or new, reaches 75 % at any lead.
- **No model beats persistence with a CI above zero at Lead 2.** HFM-X has the highest point estimate (50 %), but its CI spans −12.5 to +32.5 pp.
- LL and LL-K lower Lead-2 MAE slightly (5.60–5.67 vs 5.98) without raising the within share. This is consistent with Gate 1: denoising the anchor removes part of a 15 % noise share, while 85 % of the error is unpredictable true change.

## 3. Lead reliability: frozen N1–N7 (`v2_reliability.csv`, applied by `e130_lib.numeric_reliability`)

N3/N4 baselines are persistence and climatology, as in the completed backend run. P = pass, F = fail.

| Lead | Model | N1 | N2 | N3 | N4 | N5 | N6 | N7 | Label |
|---|---|---|---|---|---|---|---|---|---|
| 1 | V2 | P | F | P | F | F | P | F (0.64) | NOT_RELIABLE |
| 2 | V2 | P | **F (0.40)** | P | F | F | P | P (0.725) | **NOT_RELIABLE** |
| 3 | V2 | F (9 quarters) | F | P | F | F | P | P | NOT_RELIABLE |
| 4 | V2 | F (8 quarters) | F | P | F | F | P | P | NOT_RELIABLE |
| 1–4 | LL, LL-K | as V2, plus N6 fails | | | | | | | NOT_RELIABLE |

**Maximum reliable lead (development):** none.
**Maximum reliable lead (future rows):** not yet testable: 0 of the 10 needed unseen quarters.

## 4. Overfitting and generalisation (`v2_overfitting.csv`, `v2_window_sensitivity.csv`)

**Train vs inner vs outer error** (averaged over the 10 outer Lead-2 issues):

| Model | Training one-step MAE | Inner Lead-2 MAE | Outer Lead-2 MAE |
|---|---|---|---|
| PERSIST / V2 | 3.38 | 4.56 | 5.98 |
| LL | 3.24 | 4.39 | 5.67 |
| LL-K | 3.18 | 4.10 | 5.60 |

- The training-to-outer gap is similar for all three models (+2.4 to +2.6 pp), and the 1–2 parameter models do not widen it. **There is no sign of overfitting.**
- The gap itself comes from the horizon: one step vs h = 3, and the 2024 surge in the outer rows.

**Window sensitivity** (estimation from 2022-Q1 instead of 2021-Q2; Lead 2 drops to 28 rows because fewer rows reach n_obs ≥ 8):
- PERSIST 0.464, LL 0.500, LL-K 0.500;
- the ranking between denoising and persistence flips with the window, so there is **no stable advantage**.

## 5. Bias and behaviour by period (`v2_by_period.csv`, Lead 2)

| Period | n | V2 within | V2 MAE | V2 bias | LL-K within | SEAS-LLM within | HFM-X within |
|---|---|---|---|---|---|---|---|
| 2024 surge | 16 | 0.25 | 8.49 | −8.49 | 0.06 | 0.06 | 0.56 |
| 2025–26 | 24 | 0.50 | 4.31 | +0.54 | 0.58 | 0.71 | 0.46 |

**Bias:**
- The overall bias (−3.07) and the high-tercile bias (−7.66) come from the surge, as DIAGNOSIS Q2 showed (lag part −5.78, selection part −1.88).
- They are not stable across periods, so no bias correction was fitted (rejected before fitting).

**Variance ratio:** 1.94 at Lead 2. This is not a collapse to the mean: persistence passes the full variability of the latest reading (including its noise) into the forecast. Correlation with the outcome is 0.20.

**Sharp increases** (y − y_latest > 2·SE): 16 rows at Lead 2; V2 catches 0. By construction no change-free forecaster can; HFM-X caught 8, which was not enough to make it reliable.

## 6. Leakage controls (`v2_verdict.json` → `leakage_controls`; tests in `backend/tests/unit/test_v2_core.py`)

| Control | Expected | Observed |
|---|---|---|
| Shuffle-target: values permuted within area, publication dates kept, full procedure rerun | No advantage over PERSIST | V2 keeps PERSIST at all 22 issues; Lead-2 within falls from 0.40 to 0.275. LL-K reaches 0.35 on the shuffled series: denoising an i.i.d. series towards its mean helps, as expected (DEVIATIONS #2, interpretation only). |
| Future shift (positive control): cutoff moved past the target's publication | Within rises far above the honest run | PERSIST 1.00, LL 0.975 (vs 0.40 honest). The evaluation is sensitive to leakage. |
| Injected round published on or after the issue | Forecast unchanged | Unchanged (test); the same injection one day before the issue **does** change it (positive control) |
| Feature table with a row dated at the issue | `LeakageError` | Raised (test) |
| **Mutation spot-check:** `as_of` `<` → `<=`, lead `D−1+k` → `D+k`, inner truth = all rounds, news `<` → `<=`, FIRI prior `<` → `<=` | Guarding tests fail | `results/mutation_check.txt` (TEST_REPORT) |

**Independent implementation check:** LL equals E131's local level (`f_LLM`) on all 272 P-DASH rows (max diff < 1e-9; test).

## 7. Intervals

- **V2 80 % split-conformal coverage:** 0.64 / 0.725 / 0.75 / 0.81 at Leads 1–4. N7 needs 0.70–0.90, so it passes at Leads 2–4 and fails at Lead 1.
- **Mean width** is 12–19 pp: honest, and too wide for operational use. That width is the uncertainty the data support.

## 8. Sealed / future confirmation

- **Seal:** `sealed/V2_PROSPECTIVE_SEAL.csv`, SHA-256 `e88f7bb2…25d7`.
  - It holds 112 rows: V2 + 3 candidates, issues 2026-07-01 and 2026-10-01, targets 2026-Q4 … 2027-Q3.
  - It was written before any of those targets was published; the targets exclude 2026-Q3, which was already published.
- **Scorer:** `backend/scripts/v2_score_sealed.py` ran once on 2026-11-01 with **0 rows scorable**, so every lead is `NOT_YET_TESTABLE` (`results/v2_future_verdict.json`, `sealed/ACCESS_LOG.md`).
- **Next scorable target:** 2026-Q4, about 2027-02 (+120-day completeness rule).
- **N1 minimum (10 unseen Lead-2 quarters):** about mid-2029 (DIAGNOSIS Q4).
