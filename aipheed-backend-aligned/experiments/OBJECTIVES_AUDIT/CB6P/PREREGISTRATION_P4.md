# C-B6P4 pre-registration (owner directive): C-B6P3 with the linear-base strength chosen on inner folds (fixed 2026-11-04, before any fit)

**Owner directive:** keep every risk driver in every forecast (market, climate, fish kill, employment, OFW remittances)
and improve on C-B6P3.

**Development evidence.** The same 100 province-quarters, already examined; this variant is disclosed as
owner-directed.

## Why

- C-B6P3 used a fixed L2 strength (C = 1) for its linear driver base.
- That strength was too weak: the 15 driver inputs dominated and overfitted (accuracy 0.690 / 0.620).

## Definition

- **Exactly C-B6P3** (the hybrid: logistic driver base as LightGBM `init_score`; the same 28 inputs, 15 driver inputs,
  rows, label, folds, seed, origins and leads), except for one change.
- **The change:** the logistic C is selected jointly with the tree setting on the **same inner chronological folds**,
  by log loss.
  - C ∈ {0.001, 0.01, 0.1, 1.0}.
  - Tree settings: `hr_lib.GRID` (8).
  - 32 combinations in all.
  - Ties go to the smaller C, then the lower GRID id.
- **No test-period information enters the selection.**

## Acceptance (as C-B6P3)

1. **Every driver group contributes:** |SHAP| > 0 in at least 99% of scored forecasts, for each of the five groups.
2. **Accuracy:** at least 0.75 at Leads 1 and 2.
3. **Brier:** not worse than C-B6P2 by more than 0.01 at either lead.

**Also reported:** the chosen C per origin and the driver SHAP shares. **Reported whatever the result.**
PLAN-SHA256: 9658210ff1e69d01ee61a15a35faaf37e4296ff5389e76e9223f7cf912961983
