# C-B6 pre-registration: C-b + national rice stocks (fixed before any fit, 2026-11-04)

**Development evidence;** the 23rd historical attempt, on the same 62 previously examined quarters. C-b stays the main
model unless C-B6 passes the rule below and the team and adviser approve.

## Why this is not a repeat

| Evidence | Source |
|---|---|
| Rice stocks are the only input added since C-b with a significant out-of-sample gain: C-E6 vs C-E2, Brier −0.0036 (p 0.012) and −0.0023 (p 0.086) | `out/ce6_results.json` |
| C-E6 inherits C-E2's architecture (8-setting average + E1 + E2), which fails R3 (0.690 / 0.679) | same |
| C-b's architecture (grid selection on inner folds, no E1 / E2) passes R3 (0.717) and has the best accuracy (0.790) | `NEW_MODEL/NEWS_V2` |
| **Never tested:** rice stocks inside the C-b architecture | — |

## Hypothesis

H7: adding ST1 and ST2 to C-b improves C-b's Brier score at both leads, while keeping C-b's classification strengths
(accuracy ≥ 0.75, R3).

## Definition

- **Exactly C-b** (`NEW_MODEL/NEWS_V2/runner/run_news_v2._origin`):
  - the same table (IMPROVE_V2 pooled BL rows + `z_N1R`);
  - labels known at O(t);
  - walk-forward from 1998-Q3;
  - `hr_lib.lgbm_select` (inner chronological folds) over `hr_lib.GRID`;
  - seed, fallback and test leads 1–8.
- **Inputs:** C-b's 21 + `ST1`, `ST2` exactly as `ce6_model.py` (stock month ≤ issue month − 4; leakage check in
  `out/ce6_checks.json`): 23 inputs.
- **Unchanged:** target 11.3% and threshold 0.50.
- **No variant** (other lags, features, weights or settings) will be tried after seeing the results.

## Evaluation (as C-E6)

- **Sample:** 62 verdict quarters, Leads 1–2 (Leads 1–8 for Algorithm 3).
- **Metrics and rules:** all metrics, R1–R7.
- **Statistics:** paired Brier vs C-b and vs C-E6; the 14-test Holm family vs the 7 baselines (one-sided cluster
  bootstrap, seed 2036, B 5000).

## Acceptance (all required)

1. **H7:** Brier < C-b at both leads, one-sided p < 0.10.
2. **Rules and lead:** R1–R7 pass at Leads 1 and 2, and MRLT ≥ 2.
3. **Accuracy:** ≥ 0.75 at both leads.
4. **Leakage:** the C-E6 feature leakage check holds.
5. **Plus team and adviser approval.**

"Beats all seven" (all 14 Holm comparisons significant) is reported separately.

**Reported whatever the result.**
PLAN-SHA256: 2efd9677e3785f4b3469b416e34cd824d536e16450ae100ceea537044d20a38b
