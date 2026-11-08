# E107 Addendum 1: eligibility. Frozen before any affected row was scored

**Date:** 2026-10-25.

**What had been seen.** The first development run printed row counts only. No metric, probability or class was viewed. `out/dev/metrics.json` was written but not opened. The counts were:

| | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| T43 (dev quarters) | 4 | 1 | 0 | 0 |
| R (dev quarters) | 2 | 0 | 0 | 0 |

**Why.**

1. **R: a unit defect.** Protocol §3 requires "≥ 5 HIGH rows and ≥ 5 LOW rows".
   - T43 has five rows per quarter, so 5 HIGH rows can come from one quarter.
   - R has one row per quarter (§4), so the same words demand 5 HIGH **quarters**. That is five times stricter.
   - The rule was meant to guarantee examples of both classes, not to treat the two targets differently.
2. **T43: a data limitation, not a defect.**
   - Before 2024 the only HIGH quarter is 2021-Q2. Its features would need an origin before 2021 when *k* ≥ 2.
   - So for Leads 2–4 the first eligible origin is 2024-Q3 (2023-Q4 and 2024-Q2 known). This leaves fewer than 6 evaluable quarters.
   - The frozen rule therefore stays as the primary T43 rule. Leads 2–4 are "not assessable" under it.

**Changes.**

- **A1-1 (R, primary).** An R origin is eligible iff its training rows cover ≥ 6 distinct target quarters, with ≥ 2 HIGH quarters and ≥ 2 LOW quarters. This replaces the row counts for R. T43 keeps §3 unchanged.
- **A1-2 (T43, secondary "extended" analysis).**
  - The same nested procedure is also run with eligibility ≥ 6 quarters, ≥ 3 HIGH rows, ≥ 3 LOW rows. This allows forecasts from the first origin at which any HIGH example after 2021 is known.
  - It is reported next to the primary decision with the same §8 criteria. It does **not** replace the primary §8 decision.
  - Every primary row is also an extended row with an identical prediction: a prediction depends only on its training set and the grid, not on the eligibility rule. The extra rows are development-block rows only.

**Unchanged.** Targets, features, model, grid, selection, threshold, arms, metrics, the §8 criteria, and the final block (all final-block origins are eligible under every rule).
