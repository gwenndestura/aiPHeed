# E26 Protocol Amendment A1: ledger claim test

**Hashed before any unseen outcome exists. Requires adviser approval because it governs C9.**

## Why

- **Date:** written 2026-10-14, after the section D horizon simulation and **before any unseen (sealed-forecast) outcome exists or has been authorized**. No real outcome informed it.
- **What the simulation showed** (synthetic paths; parameters from authorized 2021–2026 data): the frozen claim test, a bounded-bet e-process with λ ≤ 0.5 and threshold 40 against both baselines, has **essentially zero power before 2031**, even for a forecaster that knows the true parameters.
  - The per-date score advantage of such a forecaster is small (Brier about 0.08–0.10 vs persistence; accuracy about 0.01).
  - The bet size cannot exceed 0.5, because a date's score difference can be as bad as −1.
  - With a constant advantage of 0.1 per date, the e-value grows by only about 5% per date, so about 75 dates are needed to reach 40.
- **Conclusion:** the frozen rule would make C9 unreachable for any realistic model. This is a design defect of the test, not evidence about aiPHeed.

## Change (pending adviser approval)

**1. Primary test: a pre-registered single look.**

- The look takes place at the **first year end** at which the unseen ledger record holds **≥ 12 scored dates** and is evaluable (≥ 5 HIGH, ≥ 5 LOW).
- At that look and **only** then, run a one-sided exact sign-flip test of the per-date score differences against **each** baseline: persistence and calibrated persistence.
- A claim needs **p < 0.025 against each baseline** (α = 0.05, Bonferroni).
- The metric is accuracy (approved C2). Brier counts only if the adviser approves P2.
- **No earlier look may be used for a claim.** If the look fails, the claim is "not established". A new pre-registration (new look time, new α) is needed for any later test.

**2. Secondary monitor (no claim): the e-process from section E**, reported every quarter.

**3. Unchanged:** everything else in the protocol (A–D, F, G); the target; C1–C8.

## Effect on reporting

`runs/horizon.json` reports both the frozen e-process rule and the A1 single-look rule.
