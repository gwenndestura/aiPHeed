# LEAD2_PERSIST_BLEND: results (EXPLORATORY, post-hoc)

**Plan:** `PLAN.md`, sha `98770618…`, commit `865fe08`, written before scoring.

**Runner and outputs:** `runner/run_blend.py`, `out/results.json` and `out/rows.csv`.

**Data:** 65 Lead-2 rows over 13 target quarters (2023-Q2..2026-Q3). The price condition s had a value for every row.

## Result: candidate B fails (R5, R6) and is worse than M3

| | TP/FP/FN/TN | Accuracy | Balanced | Precision | Recall | AUC | Brier | Rules passed | Fails |
|---|---|---|---|---|---|---|---|---|---|
| **B** = h × (0.5 m + 0.5 s) | 10/8/7/40 | 0.769 | 0.711 | 0.556 | 0.588 | 0.721 | 0.1827 | 5/7 | R5, R6 |
| M3 (reference) | 11/8/6/40 | 0.785 | 0.740 | 0.579 | 0.647 | 0.781 | 0.1582 | 6/7 | R6 |

**B's failures:**
- **R5.** Its Brier is below PERSIST-SI by 0.064 (p = 0.061), but below CLIM by only 0.032 (p = 0.253, not < 0.10).
- **R6.** Precision 0.556 and recall 0.588, both below 0.60.

## What happened

**Blending in price persistence did not remove false alarms. It moved them:**
- B adds 2025-Q4 (3 HIGH, 0 actual) and 2026-Q1 (1 HIGH, 0 actual), where prices had been hot but were cooling.
- B removes the model's correct 2026-Q2 call.

**The three 2023-Q4 misses remain.** At that origin the hunger part was 0.22, because the newest SWS reading was still low. No price term can lift h × p to 0.50 there.

**Persistence helps when price conditions last, and hurts when they turn.** Over 2024–2026 they turned often enough to cancel the gain.

## Correction disclosed

In the first run, the frozen `reproduce.rules()` scored R1–R3 and R6 on its default column (`P0H4_p3`), not on the candidate.

**The cause:** its internal `scores(g)` call has its default column bound when the module is imported.

**The fix:** the runner was corrected to point `scores` at the evaluated column, as `LEAD2_FOODINSECURITY/runner/run_fi.py` already did. It now asserts that R2 equals the candidate's accuracy. The fix is confirmed by the M3 reference, which reproduces its published result exactly (11/8/6/40, failing R6 only).

The plan was not changed.

## Conclusion

The one user-authorised extra candidate does not improve Lead 2. M3 remains the best Lead-2 variant on these rows: 6 of 7 rules, failing precision. It stays exploratory, registered in PREREG_LEAD2 addendum 2, and is to be judged on sealed 2027+ quarters.
