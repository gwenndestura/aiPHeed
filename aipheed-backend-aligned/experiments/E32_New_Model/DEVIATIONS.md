# E32 implementation details and deviations

## Part A. Fixed BEFORE any candidate was run

These close gaps the frozen protocol left open. No result had been seen when they were written. They are committed in the same commit as the first evaluation code.

1. **Training labels use their own origin's threshold.**
   - A training pair (X(t'), S1(t'+k)) is labelled HIGH if S1(t'+k) > τ(t'), where τ(t') is the threshold in force at O(t').
   - The margin features use the same τ(t').
   - The model therefore learns P(S1 above the threshold in force at the origin | information at the origin), which is the quantity it is scored on.
2. **PCFN news shift is β·(news_reg(t) − mean of news_reg over the training pairs).**
   - This equals least squares with an intercept, using only the slope.
   - Training pairs are consecutive posted H quarters (q−1, q) with news_reg(q−1) known, all posted before the origin.
   - With fewer than 6 pairs, β = 0.
3. **PCFN D-regression needs at least 25 complete pairs.**
   - Complete means D_last, Dnow, rice_rel and news_n all present.
   - Otherwise, at that origin, the PCF21 D-model (D_last only) is used, and the fallback is recorded per origin.
4. **References are publication-aware.**
   - Persistence (B1) and calibrated persistence (B1p) use the latest labelled quarter whose rounds were all posted before the origin. This is the E25 rule.
   - `app.quarterly.cycle.reference_probabilities` (used by the E27–E31 ledger) does **not** check publication: it takes the label of t−1 even when its round was posted after the origin. For 90% of origins, that gives persistence information it could not have had. E32 does not use it. This is reported as a finding.
5. **Missing features in LR/LGBM training.**
   - Missing D_last or Dnow (before 2022-Q1) makes the pair ineligible (dropped).
   - Missing rice_rel is impossible (rice starts 2021-01).
   - fssi_v2 missing → 0 with `fssi_missing = 1`; news counts of 0 are real zeros.
   - When every training label belongs to one class, the prediction is the Laplace rate (n_HIGH+1)/(n+2).
6. **All arms are scored against the E32 labels** (E31 input vintage 2, verified posting dates).
   - P45's stored probabilities came from E25 inputs (vintage 1); only its labels are recomputed.
   - Where the τ in force differs between vintages (targets whose origin falls after a 2026 round's true posting date), this is listed in the results.
7. **Lead 2** uses the same feature vector and the same rules. H_gap carries the extra quarter.
8. **Evaluable dates (added after the first run crashed before producing any score).**
   - A (lead, target) date is evaluated only when every E32 candidate AND PCF21 can be computed at its origin.
   - PCF21's D-model needs 40 published pairs, so the earliest lead-2 dates are not computable for PCF21.
   - Skipped dates are listed in `results.json` (`skipped_dates`).
   - P45 is compared on its own common rows.
