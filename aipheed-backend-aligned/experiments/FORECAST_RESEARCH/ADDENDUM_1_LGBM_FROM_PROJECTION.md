# Addendum 1: the unified LightGBM boosted from the structural projection, under schedules A and B

**Hashed before scoring.** Written 2026-10-27, after the frozen FR run (`out/results.json`).

## Why

The frozen run gave three results:
- **Learned corrections hurt.** Z2 (ridge) and Z3 (unified LightGBM regressor) corrections to the price projection raise the continuous RMSE above zero correction at every lead. LightGBM adds no development value (Z3 dev Brier 0.180 vs Z1 0.169 under A; 0.206 vs Z0 0.179 under B).
- **The selected arms are structural.** Z1 under A and Z0 under B. Neither is a LightGBM model, which the thesis requires as its primary candidate.
- **One LightGBM keeps the structure.** The existing LEAD2_OPTIMIZATION arm **P4** is one LightGBM classifier across leads with all 12 families, started from the structural price probability (init_score = logit(Z0)), so it learns only corrections. It was post-hoc in LEAD2_OPTIMIZATION (Addendum 1 there) and was not adopted, because P0 had the lower Lead-2 development Brier *with the quarter-start hunger term*.

This addendum asks one question: does P4, combined with each schedule's hunger term, keep Z0's skill, and is it reliable at any longer lead?

## Arms

| Arm | Definition |
|---|---|
| **P4A** | P4_price × π_H(A) |
| **P4B** | P4_price × π_H(B) |

- P4_price is taken unchanged from `FINAL_ARCHITECTURE/out/predictions.csv`. Its leakage audit is LEAD2_OPTIMIZATION's.
- π_H(A) and π_H(B) are the hunger terms of `out/predictions.csv`.
- Rows, metrics, R1-R7 and baselines are those of the frozen protocol §6.

## Decision rule (fixed now)

**Thesis candidate.** P4 under schedule s becomes the thesis candidate for s if two conditions hold:
1. its DEV Brier (Leads 1-3 mean) is within 0.002 of the protocol-selected arm for s;
2. at Lead 1 it is not significantly worse than that arm (two-sided bootstrap p ≥ 0.10).

Otherwise the protocol-selected structural arm stays the evidence-preferred model, and P4 is reported as the LightGBM alternative.

**Maximum reliable lead.** Reported for each schedule, using R1-R7 unchanged.

**No further arms.** If no lead beyond 1 is reliable, no further tuning arms are run on these quarters.
