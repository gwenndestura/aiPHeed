# LEAD2_EXPLORATION: results (EXPLORATORY, not evidence)

**Plan:** `EXPLORATION_PLAN.md`, sha `b96368fd…`, fixed before any result.

**Data:** the 65 closed 2023–2026 Lead-2 rows, which were already examined. Nothing was refitted; only HIGH/LOW decision rules on the existing hunger and price parts were explored.

**Run:** `runner/explore.py`, exit 0. Every result is in `out/exploration.json`, and the stdout is in `out_stdout.txt`.

**Finding:** no decision rule passes all seven rules, even in-sample. Every combination fails R6 (precision and recall both ≥ 0.60) after cross-validation. The best combinations pass 5 of 6 of R2–R7, the same as M0 under the served rule. **No improvement survives cross-validation in the number of rules passed** (plan §4).

## Nested leave-one-quarter-out (the honest estimate) and in-sample (optimistic)

| Combination | Nested: R2–R7 passed | Nested: TP/FP/FN/TN | Acc | Bal. acc | Precision | Recall | Nested fails | In-sample best grid point → passed |
|---|---|---|---|---|---|---|---|---|
| **S2×F2** (M2 parts, both parts) | **5/6** | 16/14/1/34 | 0.769 | **0.825** | 0.533 | **0.941** | R6 | (0.5, 0.45) → 5/6 |
| **S3×F1** (mean price, product) | **5/6** | 9/5/8/43 | **0.800** | 0.713 | **0.643** | 0.529 | R6 | 0.50 → 5/6 |
| S1×F1 (M0 parts, product) | 5/6 | 9/6/8/42 | 0.785 | 0.702 | 0.600 | 0.529 | R6 | 0.55 → 5/6 |
| S1×F2 (M0 parts, both parts) | 4/6 | 6/3/11/45 | 0.785 | 0.645 | 0.667 | 0.353 | R3, R6 | (0.5, 0.6) → 5/6 |
| S0×F2 (served parts, both parts) | 3/6 | 6/4/11/44 | 0.769 | 0.635 | 0.600 | 0.353 | R3, R5, R6 | (0.8, 0.6) → 3/6 |
| S2×F1 (M2 parts, product) | 1/6 | 12/16/5/32 | 0.677 | 0.686 | 0.429 | 0.706 | R2, R3, R4, R6, R7 | 0.45 → 5/6 |
| S3×F2 (mean price, both parts) | 1/6 | 11/16/6/32 | 0.662 | 0.657 | 0.407 | 0.647 | R2, R3, R4, R6, R7 | (0.5, 0.45) → 3/6 |
| S0×F1 (served parts, product) | 1/6 | 4/4/13/44 | 0.738 | 0.576 | 0.500 | 0.235 | R2, R3, R4, R5, R6 | 0.50 → 3/6 |
| *Reference: M0 under D0 (registered primary), in-sample* | *5/6* | *10/6/7/42* | *0.800* | *0.732* | *0.625* | *0.588* | *R6* | – |

**Selected for the addendum** (plan §4: top-ranked, plus the next with a different part set passing as many rules):

1. **S2×F2 at (0.5, 0.45):** HIGH when the post-SWS hunger part ≥ 0.50 **and** the M2 price part ≥ 0.45.
2. **S3×F1 at 0.50:** HIGH when the post-SWS hunger part × the mean of the two price parts ≥ 0.50.

## What this means

| Rule | Trade-off on these rows |
|---|---|
| **S2×F2** | Catches almost every high-risk case (16 of 17 out of sample), but about half its alarms are false (precision 0.53) |
| **S3×F1** | Raises fewer false alarms (precision 0.64), but still misses about half (recall 0.53) |
| **M0 under D0** | Sits in between |

On these 13 quarters, no rule gets both precision and recall above 0.60. More rules tried on the same quarters would only fit noise.

The two selected rules are registered in `backend/seals/PREREG_LEAD2_ADDENDUM_1.md`, to be judged only on sealed, on-time 2027+ quarters.
