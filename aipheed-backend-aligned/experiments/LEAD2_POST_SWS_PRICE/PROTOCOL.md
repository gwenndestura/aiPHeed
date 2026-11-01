# LEAD2_POST_SWS_PRICE: protocol (frozen before any scoring)

**Status.** Frozen before any result in this folder was computed. The SHA-256 is in `PROTOCOL_SHA256.txt` and the UTC time in `PROTOCOL_FROZEN_AT.txt`. Every runner checks the hash.

**This is the final pre-registered Lead-2 test on the 2023–2026 rows.** Whatever the result, no further variant will be tested on these quarters.

## 1. What changes, and nothing else

**M2 = H4(O'(t)) × P0_price'(t).** Lead 2, target quarter t+2.

| Component | Definition |
|---|---|
| O'(t) | Exactly as in `LEAD2_POST_SWS_ISSUE` (protocol `1328f059…`): O'(t) = max(O(t), min(P(t) + 1 day, quarter end + 67 days)), where P(t) is the publication date of the last BL round of quarter t (`rlib.rounds`) |
| H4(O'(t)) | The served hunger term recomputed at O'(t) (`LEAD2_POST_SWS_ISSUE/runner/score.h4_at`, imported read-only) |
| **P0_price'(t)** | The served **P0 arm** (`l2_lib.price_prob("P0")`: `uni_lib.select` + `UniPrice`, monotone, columns `uni_lib.cols("U2")`) refitted walk-forward, expanding window, on the stacked CH1 rows of every lead (`uni_lib.stack(K)`, K and eligible origins from `FINAL_UNIFIED_LGBM/out/testability_unified.json`), with **one change**, described below |

**The one change.** The CPI cutoff of every origin t, both test and training origins, is m0'(t) = the newest month available at O'(t) (month M is available from the first day of M+2). It replaces `e41_lib.m0_of(t)` (month 2 of quarter t).

**How it is implemented:**

- An in-memory, parameterised replacement for `e41_lib.m0_of` is installed by the new runner (`runner/price_refit.py`). **No file is edited.**
- Every CPI use goes through that single function (verified: `Data.cut`, the CH1 CPI features, `known_ps` training labels, `persist_si`, rice CPI).
- **Kept as served (as of O(t)), by pinning:** the World Bank columns (`uni_lib.world_features`, which also call `m0_of`) are recomputed with the original `m0_of(t)`.
- **Unchanged:** news, SWS-based features, climate, production, LFS, poverty. `Data.cut` uses O(t) and t for those, and `origin()` is not replaced.
- **Same as served:** features, grid, selection procedure, seeds (uni_lib SEED 2027), training window (`uni_lib.train_rows`).

**Execution.** The served-cutoff run and the post-SWS-cutoff run are separate processes, so no cache crosses between them.

**Everything else is as in `LEAD2_POST_SWS_ISSUE`:**

- target T43c;
- the 65 official Lead-2 rows (13 quarters, 2023-Q2 .. 2026-Q3);
- R1–R7 as frozen (`P0H4_LEAD12_REVIEW/runner/reproduce.rules`), with PERSIST-SI and CLIM replaced by their values recomputed at O'(t) (persistence with the newest SWS and the newest CPI at O'(t); climatology; always-LOW);
- threshold 0.50.

## 2. Checks before scoring (the run stops on any failure)

1. **Reproduction:**
   - stored P0H4 Lead 2 = **6/4/11/44**, Lead 1 = **11/5/6/48**;
   - M0 from `LEAD2_POST_SWS_ISSUE` = **10/6/7/42** (recomputed with its functions).
2. **Parity.** The copied pipeline with the **served** cutoff (m0_of unchanged) must reproduce the stored `P0_price` (`FINAL_ARCHITECTURE/out/predictions.csv`) for every Lead-2 row, with max abs. difference ≤ **1e-9** (LightGBM is deterministic with fixed seeds). On failure, M2 is not scored.
3. **Leakage audit (every origin, training origins included):**
   - m0'(t) is available at O'(t), i.e. the first day of month m0'(t)+2 ≤ O'(t);
   - the newest CPI month in `Data.cut(t)` equals m0'(t) and is never later;
   - every SWS round used by H4 was published before O'(t);
   - training rows come only from origins t' < t, whose O'(t') ≤ O'(t), with targets ≤ t−1.

   Additionally, a **perturbation test** at the origin of the 2024-Q2 target (2023-Q4): CPI values for months > m0'(t) are replaced by random numbers, and P0_price'(t) must be unchanged (to 1e-12).

## 3. Independent check of the price half

The served P0 features **cannot be built before 2021**:

- the E41 input loader raises `WindowViolation` on any CPI value before 2021-01;
- the news composites, PSA LGU vulnerability and Pink Sheet columns used by `cols("U2")` exist in the project only from 2021.

Y12's 2012-based provincial CPI (1995–2021) covers **only the CPI family**, not the other feature families, so the served P0 arm cannot be run on independent years.

**The independent gate is therefore NOT EVALUABLE.** As instructed, the decision is then capped at a development pass. No substitute model is run.

## 4. Robustness (reported, and part of the label)

Exactly as `LEAD2_POST_SWS_ISSUE` §8:

- flip each BL quarter within 1.0 point of 11.3, one at a time and all together;
- 2000-draw SWS sampling-error Monte Carlo of R2, R3, R4, R6, R7.

## 5. Reporting

**For M2, M0 and every baseline:**

- accuracy, balanced accuracy, precision, recall, specificity, AUC, Brier with 95% quarter-cluster CIs (B = 2000, seed 2036);
- R1–R7 with their values;
- onsets anticipated;
- results by third.

**Comparison with M0:**

- which of M0's 7 missed HIGH rows M2 catches;
- which new false alarms M2 adds.

**Every run is reported, including failures.** Nothing is changed after scoring.

## 6. Decision

| Decision | Condition | How it is reported |
|---|---|---|
| **(A-dev)** | R1–R7 all pass for M2 on the official rows | "Lead 2 issued after the SWS release, with its CPI cutoff moved to that date, passes on development data; **no independent price check was possible**; needs sealed prospective confirmation." Append "**fragile**" if the Monte Carlo all-rules pass rate is < 0.50. |
| **(C)** | otherwise | – |

**Never reported as the original Lead 2 passing.** It is a disclosed change of issue timing plus CPI cutoff, and the original Lead 2 (issued O(t)) still fails R3, R5 and R6.
