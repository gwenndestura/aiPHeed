# E46 addendum: iteration I10, trigger groups admitted by inner validation (frozen before any I10 score)

**Written:** 2026-10-17, after the I8 run (`runs/i8_20261017T001227Z`) and the I9 run (`runs/i9_20261017T005904Z`).
**Freeze:** SHA-256 of this file (LF) in `runner/ADDENDUM_I10_SHA256.txt`, committed with code and tests before I10 is fitted. Run once, then a byte-identical repeat.

## 0. Evidence status

| Candidate | Accuracy | Balanced | HIGH recall | LOW recall | Brier | AUC | Result |
|---|---|---|---|---|---|---|---|
| I8 | 0.771 | 0.665 | 0.44 | | 0.132 | 0.902 | fails A2 |
| I9 | 0.571 | 0.712 | 1.00 | 0.42 | | | fails A1 and A2 |
| I8-MKT (diagnostic) | 0.800 | 0.756 | 0.67 | | | | |

- I8 and I8-BASE are identical on S44. Inner validation rejected the full five-trigger residual (about 30 inputs on about 80 training rows) at nearly every origin, while the smaller market-only residual was sometimes accepted.
- I10 is designed from those S44 aggregates, so **I10 is hindsight-informed** (the twelfth look at S44). Its scores are development evidence, and acceptance is prospective only.

## 1. Diagnosis: D6, all-or-nothing trigger inputs

- **The defect:** I7 and I8 offer the residual either all groups at once or nothing. Each weak or national group (employment and OFW are national, so the same for all five provinces; news is sparse) adds variance on a small sample. One weak group can therefore make inner validation reject the groups that do carry signal.
- **The remedy:** group-wise inclusion decided by inner validation. Every group stays connected to training and inference at every origin, but enters the fitted model only when it reduces the embargoed forward-chaining error.

## 2. I10 (everything not listed is I8 exactly: O'(t) timing, F/G components, no intercept, embargo, hunger component, p ≥ 0.5)

For each price component (F, G) at each origin:
1. Start with the market group + policy block.
2. Evaluate adding each of climate, fish_kill, employment, ofw_remittance and news. Each candidate set is scored by the best of the 15 configurations (drift × {no residual, ridge α 1…1000}), by embargoed forward-chaining RMSE.
3. Add the group with the lowest RMSE if it is strictly lower than the current set's. Ties go to the listed order.
4. Repeat until no group lowers it.

The selected groups are recorded for every origin. The `no residual` configuration remains available.

## 3. Final-candidate rule

The ADDENDUM_I8 rule, with I10 in place of I8:
1. A0–A4 on S44;
2. EXT accuracy ≥ 0.75;
3. minimum leave-one-quarter-out S44 accuracy ≥ 0.70;
4. Brier no worse than B-persist-O'.

**If I10 passes:** it is served behind `AIPHEED_LEAD2_MODEL=e46`, production stays E38, and `forecasting_acceptance_met` stays false (acceptance is prospective).

**Prospective freeze:** `frozen/E46_I10_PROSPECTIVE_2027Q1.json` (O' = 2026-10-15).
