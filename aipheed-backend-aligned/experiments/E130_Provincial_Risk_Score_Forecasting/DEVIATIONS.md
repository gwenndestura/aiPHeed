# E130 deviations from the frozen protocol

## V1 · Planning-simulation implementation corrected to match protocol §11 (2026-10-31)

**What happened.** The first implementation of `e130_lib.simulate_panel` tested N4 against persistence only. Protocol §11 defines the output as the probability of passing N2 **and N4**, and N4 (§8) requires a squared-error advantage over persistence **and** climatology.

**Fix.**
- The code now also tests against climatology, taken as the true province mean (the strongest climatology).
- The first run's simulation numbers are superseded and were never reported.
- The grid, seeds and every other setting are unchanged.

**Why it matters.** Without the climatology test, a model with **no** predictive information (R² = 0) passed whenever the reference was very noisy, just by smoothing the noisy last observation. That would have overstated what passing the rules means.

## V2 · A replication of D5 on the next round, added after exposures X1 and X2

**What is added.** The D5 statistic (protocol §10: provincial food-price rise between rounds vs the PFDR change) will be recomputed on the 2023→2025 changes when the owner supplies the 2025 provincial subsistence table.

**Rule.** The rule is identical to D5 and mechanical, with no discretionary choice. It was added after the 2025 national and provincial *poverty* values were seen (CONTAMINATION_LOG X1, X2), so it is labelled **exploratory**. It is not a pre-registered test.
