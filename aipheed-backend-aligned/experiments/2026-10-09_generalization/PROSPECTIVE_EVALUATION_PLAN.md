# Prospective Evaluation Plan (frozen 2026-10-09)

**Purpose:** measure performance on quarters whose labels did not exist when the model was chosen. This is criterion C5 of `PREREGISTRATION.json` (SHA-256 `3183c423…c453`).

## Frozen elements

| Element | Value |
|---|---|
| Configuration | `FROZEN_PROSPECTIVE_CONFIG.json`: gov47, LightGBM defaults, `scale_pos_weight = (1−p)/p` from training rows. This is the pre-registered nested procedure's unique choice using data through 2025-Q4, and it is identical to MODEL-B2 / `config/governing_model.json`. |
| Training data | Every labelled row through 2025-Q4, using the strict-timing frame |
| Target | Eq. 3, global threshold **14.6, fixed** (not recomputed with new quarters) |
| Cut-off | 0.50 |
| References, scored on the same quarters | Timing-valid persistence; clock-only (LightGBM on the quarter index, trained through 2025-Q4) |
| Hypotheses compared but **not** substituted | 42-feature logistic (C = 0.1, balanced, no commodity); LightGBM without price features |

## Procedure for each new quarter Q (2026-Q1 onward)

1. **Before Q begins:**
   - Archive every input as released (CPI and rice values, SWS latest round, FSSI from news published through the end of Q−1, and so on), with download timestamps.
   - Compute the forecast from those archived values only.
   - Store forecast, probability and input hashes in `experiments/prospective/<Q>/`.
2. **After SWS publishes round Q and PSA publishes CPI for Q:** compute the Eq. 3 label with the fixed threshold 14.6.
3. **Record every quarter, whatever the result.** No re-fitting, re-thresholding or substitution of the configuration during the evaluation.

## Analysis

- Report cumulative mean quarter accuracy, correct and incorrect counts, ROC-AUC, within-quarter AUC, and paired differences against both references.
- Apply criteria C1–C4 once at least 8 prospective quarters exist. Report the C2 lower bound at every update; it will stay wide until then.
- Expected yield: SWS publishes about 4 rounds a year, so 8 quarters means roughly 2 years.

## Requires authorization

The approved data window is 2020–2025, so extending the pipeline past 2025-Q4 is a methodology change (decision A5). No production component is changed by this plan.
