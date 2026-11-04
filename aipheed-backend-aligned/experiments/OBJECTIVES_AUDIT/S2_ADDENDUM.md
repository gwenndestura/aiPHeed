# S2 addendum (fixed before any S2 computation; 2026-11-03)

**Change from `S1_PREREGISTRATION.md` §4:** S2 is now evaluated descriptively, at your request. Its adoption remains
impossible by construction: a threshold changes classes, not probabilities, so S2's Brier equals K1's and G2 cannot
pass.

## Definition

- **K1 probability:** 0.5 C-b + 0.5 LOGIT (`NEW_MODEL/ALLBASE/out/blends.csv`).
- **Threshold τ(t, k):** chosen from the grid {0.30, 0.35, …, 0.70}. It maximizes balanced accuracy over past K1
  forecasts (origins t′ < t) whose target label was published before O(t).
- **Fallback and ties:** τ = 0.5 with fewer than 20 such forecasts; ties go to the value closest to 0.5, then the
  lower one.
- **Class:** HIGH if p ≥ τ.

## Reported

- **Metrics:** accuracy, balanced accuracy, precision, recall, F1, the confusion matrix, R1–R7 and Algorithm 3, for
  Leads 1 and 2.
- **Unchanged from K1:** AUC and Brier.
- **Comparison:** against C-b and K1.
- **Leakage check:** τ unchanged when labels unknown at O(t) and forecasts from origins ≥ t are randomized (5 reps).

**Gates as before; adoption: no** (G2 impossible).
ADDENDUM-SHA256: b18787f4a031dce3520538f719e5e44855337ef83a6fa8e70bfee3d02388f480
