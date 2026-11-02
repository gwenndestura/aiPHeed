# LEAD2_MIDQUARTER_UPDATE: results (EXPLORATORY, not evidence)

**Plan:** `PLAN.md` (sha `6b5bff74…`), fixed before any result.

**Run:** `runner/run_m3.py`, exit 0. Results are in `out/results.json` and `out/rows.csv`.

**Leakage audit:** passed for every origin. Each CPI cutoff was available at its issue date D(t), and the SWS round used was published before D(t).

**What was tested.** M3, the mid-quarter update, is issued on the first day of the second month of the next quarter (for example 1 November), with the newest SWS and CPI available then. Every training origin uses the same rule.

**Data.** The 65 official Lead-2 rows, 2023-Q2..2026-Q3, target T43c, threshold 0.50, scored with the frozen R1–R7.

| Model | TP/FP/FN/TN | Acc | Bal. acc | Precision | Recall | AUC | Brier | Fails |
|---|---|---|---|---|---|---|---|---|
| P0H4 (served, issued 1st day of quarter) | 6/4/11/44 | 0.769 | 0.635 | 0.600 | 0.353 | 0.625 | 0.194 | R3, R5, R6 |
| M0 (after SWS release) | 10/6/7/42 | 0.800 | 0.732 | 0.625 | 0.588 | 0.760 | 0.167 | R6 |
| M2 (after SWS release + CPI) | 9/8/8/40 | 0.754 | 0.681 | 0.529 | 0.529 | 0.827 | 0.153 | R3, R4, R6 |
| **M3 (mid-quarter update)** | **11/8/6/40** | **0.785** | **0.740** | 0.579 | **0.647** | 0.781 | 0.158 | **R6 only** |

**Reading:**

- M3 has the best recall and balanced accuracy of the four, and catches 11 of 17 high-risk cases.
- It fails only R6: its precision is 0.579 against the 0.60 required.
- It is the second variant, after M0, to miss only one rule. Neither passes all seven.

**Not evidence.** This is the fifth variant scored on these quarters, so its numbers are optimistic. It cannot be called reliable. It could only be confirmed by pre-registering it and sealing an update on each D(t) from now on.
