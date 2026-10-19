# E58 reproducibility audit

**Audit date:** 2026-10-18.
**Repository:** branch `e46-lead2-policy`, HEAD 88d5266. Nothing was modified in E38–E58, and nothing was committed.

## 1. What E58 is (as implemented)

| Component | What it is | Where |
|---|---|---|
| **E38** | Production default. A LightGBM model of the thesis Eq. 3 composite label (SWS hunger + 2 × provincial food-CPI deviation above a trailing median), Lead 2. | served when `AIPHEED_LEAD2_MODEL` is unset (`e41_lead2.mode()` returns `e38`; checked in this audit) |
| **E56** (E56-TUNED) | P(T43 HIGH) = P_hunger × P_price. P_hunger: the I7 regional ridge on SWS hunger. P_price: LightGBM with a base-effect CPI projection offset and intercept-free boosting. The configuration is chosen per origin from 72 (nested chronological validation). | `E56_LightGBM_Optimization/`, artifacts `backend/data/e56/model/` |
| **E57** | Frozen rolling-origin test of E56. 10 origins (2023-Q4..2026-Q1), targets 2024-Q2..2026-Q3, 50 rows, forecasts sealed before scoring. | `E57_E56_Rolling_Origin_Test/` |
| **E58-EW** | A decision rule on E56's outputs; nothing is retrained. ALERT if P(HIGH) ≥ 0.5; EMERGING if P_price ≥ 0.5 and P(HIGH) < 0.5; NONE otherwise. Direction is measured against the latest label known at issue. | `E58_Rising_Stress_Early_Warning/`, `backend/data/e58/e58_record.json` |

**Serving and deployment status:**

| Item | Status |
|---|---|
| Dashboard default | **E38**. E58 is served **only** with `AIPHEED_LEAD2_MODEL=e58`. No `.env` file sets it. |
| Remote branch | `origin/e46-lead2-policy` is at 6fc1a4f (E51). E52–E58 (27 commits) exist **only locally**. |
| Live deployment | **E58 is not deployed** on Render or Vercel. The live deployments were not inspected (no access from this audit). |
| Local preview | `aipheed-e58-api` on port 8003 with the approved frontend on 8083 (a local preview, not production). |

**E58 configuration as served (2027-Q1 forecast):**

| Item | Value |
|---|---|
| Issue date | 2026-10-01 |
| Predictor quarter | 2026-Q3 |
| Target | 2027-Q1 |
| Latest label known at issue | 2026-Q2 |
| E56 configuration | id 23: 2 leaves, 40 trees, learning rate 0.05, all groups, recency 6, no poverty |
| E58-EW thresholds | 0.5 / 0.5 |
| Training | targets ≤ t−1 from 2021-Q3 onward |
| Evaluation | 2024-Q2..2026-Q3 |

## 2. Reproduction (`runner/a1_reproduce.py` → `out/reproduction.json`)

**Method:** every figure was recomputed from the sealed prediction files and the T43 labels rebuilt from the source data, with metric code written for this audit. The E56 procedure was re-executed at all 10 origins.

| Check | Result |
|---|---|
| E57 sealed file sha256 `4d52b1f3…` matches its seal | yes |
| E58 sealed file sha256 `8e8e417a…` matches its seal | yes |
| E56 probabilities in the E57 and E58 seals | identical (max diff 0.0) |
| E56 re-executed at all 10 origins vs sealed | same selected configuration at every origin; max probability diff 5.0e-13 |
| Onset labels rebuilt vs E58 `data/events.csv` | identical |
| T43 = price-pressure label (PS) on every evaluated row | **true, 50/50** |

**Reported vs recomputed (50 rows, 10 quarters):**

| Figure | Reported | Recomputed | Confusion TP/TN/FP/FN |
|---|---|---|---|
| E56 accuracy | 0.72 | 0.720 | 10/26/6/8 |
| E56 onsets detected | 3 / 10 | 3 / 10 | |
| E58-EW accuracy | 0.78 | 0.780 | 14/25/7/4 |
| E58-EW onsets detected | 7 / 10 | 7 / 10 | |
| Price projection rule onsets | 7 / 10 | 7 / 10 | accuracy 0.740 (14/23/9/4) |
| Quarters where EW differs from E56 | "mostly 2024-Q2" | **only 2024-Q2** | |

**Discrepancies: none.**

## 3. Tests re-run (this audit)

| Suite | Result |
|---|---|
| E55 + E58 experiment tests | 13 passed |
| E55 / E56 / E58 serving integration tests | 15 passed |
| Backend full | 402 passed, 18 skipped |
| Frontend | tsc clean; vitest 45 passed |
| Record reproduction (a4: each origin's selected configuration refitted vs the served E58 record) | max diff 5e-5, the 4-decimal rounding of stored past values |

## 4. Verdict

**Reproducibility: Supported.**
- Every reported E57 and E58 figure is reproduced exactly from the sealed artifacts.
- The model is deterministic.

This establishes that the numbers are what the code produces. It does not establish that they generalize (see the other audit files).

## Correction (2026-10-18, added during E60)

**What changed:** `git ls-remote origin` now shows `refs/heads/e46-lead2-policy` at **88d5266**. The E52–E58 commits **are pushed**.
- The "6fc1a4f / only locally" statement above came from the local remote-tracking ref when this audit was written, and it no longer holds.
- Project memory records a push on 2026-10-18, made at the user's request in another session.

**What did not change:**
- The code default is still `e38`.
- This audit cannot see whether the Render service has `AIPHEED_LEAD2_MODEL=e58` set, so the live serving status is **unverified**. It is not "not deployed".
