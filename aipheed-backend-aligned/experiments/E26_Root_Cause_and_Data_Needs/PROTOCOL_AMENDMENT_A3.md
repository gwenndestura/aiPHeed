# E26 Protocol Amendment A3: success must beat the strongest applicable baseline

**Hashed before any unseen outcome exists. Pending adviser approval, like A1.**

## Why

- **Date:** written 2026-10-14, while preparing the final report and **before any unseen (sealed-forecast) outcome exists or has been authorized**. No real outcome informed it.
- **The brief** defines success as "beating the strongest applicable baseline and demonstrating reliable performance on valid unseen observations".
- **The gap:** A1 tests the candidate only against persistence and calibrated persistence. In E25, **always-HIGH** had the best Brier score at lead 1 (0.075) on development quarters. Which baseline is strongest on unseen quarters cannot be known in advance.

## Change (pending adviser approval)

**1. The A1 look also tests these references** (same dates, same one-sided exact sign-flip):

- **always-HIGH**: the constant probability 1 for every province. It is computed at scoring time, because a constant forecast cannot leak.
- **climatology**: the E25 arm `CLIM_training_rate`, sealed as role `reference_climatology`. It is included where it is sealed for the same origin.

**2. Success condition.** "Success" (`claim_vs_all_references`) requires p < 0.05 / K against **every** baseline and reference present, where K is their number (Bonferroni; K = 4 when all are present). The mean score difference must also be positive against each.

**3. Unchanged:**

- The A1 claim (`claim`: persistence and calibrated persistence, p < 0.025 each) is still reported, with exactly its A1 meaning.
- The look time, the single-look rule, the e-process monitor, the target and C1–C8 are unchanged.

## Effect

`a1_look()` reports `tests` for every role and both `claim` (A1) and `claim_vs_all_references` (A3). The final report calls the result a success only under A3.
