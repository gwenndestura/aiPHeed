# E59: Algorithm 3 lead-time scan for the served E49 model family (k = 1..8)

## Pre-registration (written 2026-10-17T13:33Z, before any E59 result was computed)

**Purpose.** This answers Specific Objective 2-V and RQ2 with the thesis's own Algorithm 3 (pp. 41-42): "iterate
forecast horizons k from 1 to 8 quarters … If mean fold accuracy meets the 75% threshold, k will be recorded …
When accuracy first drops below 75%, the search will halt and returns the last passing k as the Maximum Reliable
Lead Time." It is evaluation only, with no tuning.

**Model (identical at every k).** The served E49 family:
- inputs: E48-A1 (E36's inputs + the five trigger proportions);
- pool: `E48-T5`, i.e. COMPACT_T5 / COMB_T5 x G1/G4/G3/G2;
- nested selection on eligible earlier dates; seed 36; threshold 0.5;
- E49-C2 shrinkage calibration fitted on eligible earlier dates only (raw probability with fewer than 3);
- label: the served trailing-median label.

**Walk-forward at lead k.**
- k = 1 uses the E36 harness (`e36_lib.walk_forward`), the procedure that produced the served E49 numbers. It
  must reproduce E49: accuracy 0.846, balanced accuracy 0.841, AUC 0.855; otherwise the run stops.
- k >= 2 uses E37's generic lead-k procedure (`e37_lib.walk_forward(d, k)`; the one used for E38 and E55).
- Origin O(t) = first day of quarter t+1, target t+k. A date is scored only if all five labels exist and the
  training set at that origin has at least 10 rows with both classes. This is the existing rule; the thesis's
  "minimum training window of 8 quarters" is reported as a deviation, not re-implemented.
- Eligible earlier dates (selection and calibration) are those whose target quarter was posted before O(t).

**Reported per k.**
- n scored dates and rows, LOW rows;
- accuracy, precision, recall, F1, AUC, balanced accuracy, Brier, the 95% date-bootstrap CI of accuracy;
- naive persistence (B1) on the same rows: accuracy, balanced accuracy, Brier.

**Evaluable.** A lead is *evaluable* only if it has at least 4 scored dates (20 rows) and both classes among
them. Otherwise it is reported as "not evaluable" with its counts; it is never skipped silently.

**Algorithm 3, exactly.**
- Start at k = 1. A lead *passes* if it is evaluable and its mean fold accuracy is >= 0.75. A fold is a scored
  date; every date has 5 rows, so the mean fold accuracy equals the pooled accuracy.
- The search halts at the first k that does not pass (accuracy < 0.75, or not evaluable).
- **Maximum Reliable Lead Time (MRLT)** = the last passing k, or "none" if k = 1 fails.
- Leads after the halt are still reported, for information only; they cannot extend the MRLT.

**CI version (reported alongside).** As above, but a lead passes only if the lower bound of its 95%
date-bootstrap accuracy interval is >= 0.75.

**Caveat fixed now.** All scored dates were examined during model development, so this is development evidence,
not a blind test. Different k score different dates, so the leads are not on identical rows.

## Results

Run `20261017T133518Z`. k = 1 reproduces E49 (accuracy 0.846, balanced 0.841, AUC 0.855): **True**. Protected md5s identical at start and end: **True**.

| k | Dates | Rows | LOW rows | Evaluable | Accuracy (95% CI) | Balanced | Precision | Recall | F1 | AUC | Brier | Persistence acc / bal / Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 13 | 65 | 12 | yes | 0.846 (0.769-0.923) | 0.841 | 0.957 | 0.849 | 0.900 | 0.855 | 0.151 | 0.877 / 0.860 / 0.123 |
| 2 | 11 | 55 | 6 | yes | 0.709 (0.582-0.836) | 0.544 | 0.902 | 0.755 | 0.822 | 0.738 | 0.218 | 0.800 / 0.741 / 0.200 |
| 3 | 9 | 45 | 3 | yes | 0.733 (0.622-0.844) | 0.393 | 0.917 | 0.786 | 0.846 | 0.591 | 0.213 | 0.756 / 0.560 / 0.244 |
| 4 | 7 | 35 | 2 | yes | 0.800 (0.629-0.943) | 0.424 | 0.933 | 0.848 | 0.889 | 0.515 | 0.193 | 0.800 / 0.424 / 0.200 |
| 5 | 5 | 25 | 1 | yes | 0.960 (0.880-1.000) | 0.500 | 0.960 | 1.000 | 0.980 | 0.250 | 0.092 | 0.880 / 0.458 / 0.120 |
| 6 | 4 | 20 | 1 | yes | 0.900 (0.800-1.000) | 0.474 | 0.947 | 0.947 | 0.947 | 0.816 | 0.082 | 0.900 / 0.474 / 0.100 |
| 7 | 3 | 15 | 1 | **no** (3 scored dates (< 4)) | 0.933 (0.800-1.000) | 0.964 | 1.000 | 0.929 | 0.963 | 0.964 | 0.052 | 0.867 / 0.464 / 0.133 |
| 8 | 1 | 5 | 0 | **no** (1 scored dates (< 4)) | 1.000 (1.000-1.000) | – | 1.000 | 1.000 | 1.000 | – | 0.008 | 1.000 / – / 0.000 |

Target quarters scored per lead:

- k = 1: 2023-Q1, 2023-Q2, 2023-Q3, 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3
- k = 2: 2023-Q3, 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3
- k = 3: 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3
- k = 4: 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3
- k = 5: 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3
- k = 6: 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3
- k = 7: 2026-Q1, 2026-Q2, 2026-Q3
- k = 8: 2026-Q3

**Algorithm 3 (mean fold accuracy >= 0.75):** k = 1: pass (0.846); k = 2: stop (0.709). **Maximum Reliable Lead Time = 1 quarter(s).**

**CI version (95% lower bound >= 0.75):** k = 1: pass (0.769); k = 2: stop (0.582). **Maximum Reliable Lead Time = 1 quarter(s).**

### Reading

- The search halts at k = 2: accuracy 0.709, below 75% and below persistence (0.800). The **Maximum Reliable Lead Time is one quarter** under both rules. At k = 1 the CI lower bound (0.769) also clears 75%.
- Leads 3-6 are reported only for information: the search has already halted. Their accuracy (0.73-0.96) is not skill. With only 1-3 LOW rows each, balanced accuracy is at or below 0.5 and AUC falls to 0.25-0.82, the pattern of predicting HIGH almost everywhere when nearly every target quarter is HIGH.
- Leads 7 and 8 have 3 and 1 scored dates (fewer than 4): not evaluable.
- Development evidence only (all scored quarters were examined during development); different leads score different quarters.
