# Objective 4: independent baseline verification and the complete comparison record

Script `runner/obj4_baselines.py` → `out/obj4_baselines.json`.

## 1. Implementations verified

| Baseline | Method of verification | Rows | Max \|Δp\| vs stored | Calls differing |
|---|---|---|---|---|
| Combined logistic (LOGIT) | Independent sklearn Pipeline (median imputer, scaler, L2 C = 1) | 138 | 1e-16 | 0 |
| NLP-only logistic | Same | 46 | 1e-16 | 0 |
| **PSA-only logistic** | Same | 138 | **0.49** | 0 |
| Naive persistence | Recomputed from raw SWS rounds published before O(t) | 138 | 0 | 0 |
| Government-only LightGBM | Refit with the h3 specification | 136 | 1e-16 | — |
| NLP-only LightGBM | Refit with the h3 specification | 44 | 6e-17 | — |
| Always-HIGH | p = 1 | — | — | — |

**Additional checks:**
- **Information cut-off:** every training label used at every origin was published before the issue date (`true`).
- **Target identity:** every comparator is scored on the same Balance Luzon labels (H > 11.3), quarter by quarter, by
  `run_iv2.frame`.
- **Evaluation window:** 2010-Q1 to 2026-Q3 (62 quarters). The news-only comparators are scored on the news era only
  (20 / 19 quarters), as stated in every table.

## 2. A defect found in the stored PSA-only baseline

**What happens in `hr_lib.logit`:**
- At origin 2011-Q4 (Lead 1) and 2012-Q1 (Lead 2), the input `R_A3` has a single non-missing training value.
- After median filling, its standard deviation is 2.2e-16 instead of 0, so the `sd > 0` filter keeps it.
- The test value is standardized to 1.6e16, and the forecast saturates at p = 1.0. The correct value is 0.70 / 0.51.

**Impact** (`out/obj4_psa_only_bug_impact.json`): both affected quarters were HIGH, so the defect made PSA-only
slightly *better*.

| | Lead 1: stored → corrected | Lead 2: stored → corrected |
|---|---|---|
| PSA-only Brier | 0.2082 → 0.2097 | 0.2389 → 0.2428 |
| C-b − PSA-only diff | −0.021 → −0.022 | −0.055 → −0.059 |
| Raw one-sided p | 0.255 → 0.241 | 0.040 → 0.028 |

**No conclusion changes:** C-b is still not significantly better than PSA-only after Holm.

**Not fixed in place:** `hr_lib.py` is shared by sealed and stored evidence. Recommended fix, for approval: treat
sd < 1e-12 as zero, then re-export the PSA-only forecasts in a new, labelled file.

## 3. Comparison record (all historical families; development evidence)

| Candidate | Family | Significant / tests | Never beaten significantly |
|---|---|---|---|
| C-b | Objective 4 (5), H3 (6) | Persistence, NLP-only logistic, always-HIGH, government-only LightGBM, NLP-only LightGBM (Lead 1) | PSA-only and combined logistic at both leads |
| K1, K2, K3 | One 42-test family | 6, 2, 3 of 14 | Same two logistic regressions |
| S1 | 14-test family | 4 of 14 | Same |
| S2 | Not tested (Brier = K1's) | — | — |

**Why every candidate fails against the logistic regressions** (Phase A §3C):
- The logistic regressions use the same hunger history, which carries most of the signal.
- The remaining Brier differences (0.005–0.06) need hundreds to thousands of quarters to be significant.

**Conclusion (H3 not rejected):** no candidate is statistically superior to all baselines. The sealed prospective
comparison is the remaining route; it is built but needs a commit to activate.
