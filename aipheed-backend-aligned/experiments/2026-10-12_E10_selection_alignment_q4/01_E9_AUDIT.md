# E10: Audit of E9 (no rerun, no retraining)

**Method.** `runner/audit_e9.py` recomputed E9's reported values from E9's own outputs: `scored_rows.csv`, `metrics.json`, `post_analysis.json`, `selection.json`, `folds.json`, `input_frame.csv` and `manifest.json`. It used E9's own metric functions, under the E10 guard. Results: `audit_e9_results.json`.

**Scope.** No protected data, no carrier file, no model fit. E9's code and synthetic tests were reviewed by reading; they were not rerun.

## 1. Findings

| # | Item | Result | Evidence |
|---|---|---|---|
| A1 | S1 formula and mechanics | **Correct and unchanged.** stress = SWS_t + 2 × (food CPI YoY − five-province mean); NaN never zero; complete quarters only; frozen point-in-time median τ; strict ">" | `risk_score_v2.py` hash `5b6c83d6…` in the E9 manifest equals the served-artifact record |
| A2 | Same quarters, rows and targets for every comparison | **Yes.** All 10 arm/output combinations use the same 35 province-quarters. One true stress value per row. | Audit: `same_rows_all_arms: True`, `rows_per_arm: 35` |
| A3 | Features available at each forecast date | **Yes, under development-protocol dates.** 0 violations in 95 frame rows: every non-null input dated strictly before its origin. | Date types in test rows: SWS verified / verified-single; last label **proxy**; provincial CPI **proxy**; regional CPI verified; unemployment **schedule** |
| A4 | Leakage in target generation, preprocessing or selection | **None found.** τ0's 8 quarters were all published before 2023-10-01. Every fold's training labels were published before its origin. The feature filter and calibration are in-fold. Selection used the 5 selection quarters only, and its MAE values reproduce exactly. | Audit flags all True |
| A5 | Independent evidence | **7 test quarters; 33 HIGH / 2 LOW.** Both LOW rows are Quezon (2023-Q4, 2024-Q1). Training folds have 8 to 15 quarters. | — |
| A6 | Reuse of E1–E7 quarters | **Disclosed in E9 and confirmed.** The same 7 quarters were evaluated in E1–E7, so the results are exploratory. | E9 `02`, `07` |
| A7 | Post-run bootstrap (deviation D2) | **Reproducible.** All 23 bootstrap entries recompute exactly (same function, seed 42, quarter order). The M1 − B1 interval is stable across other seeds: [−1.11, −0.21], [−1.10, −0.22], [−1.11, −0.22], [−1.09, −0.20]. | Audit |
| A8 | Reported metrics | **All reproduce exactly** (accuracy, MAE, Brier, per arm and period) | `metrics_reproduced: True` |

## 2. Corrections and clarifications to the E9 record

1. **"Non-inferior" must not be used.** My E9 chat summary called LightGBM "non-inferior". **No non-inferiority margin or test was prespecified,** so that wording is unsupported; the E9 documents themselves do not use it.

   Correct statement: the comparison of M1 with B2 and B3 is **inconclusive**. Mean differences are +0.07 and −0.01, intervals include large differences in both directions, and the exact two-sided sign-flip p is 0.98 for both (post hoc, descriptive).
2. **The E9 selection rule is not proof that LightGBM is better.** It is a pre-set rule for moving away from carry-forward. M1 passed it against carry-forward only. Its margin over carry-forward is consistent across quarters (6/7; exact sign-flip p = 0.047, post hoc and not prespecified).
3. **Newly identified: the S1 formula rule (B3) equalled carry-forward (B1) in 6 of 7 quarters.** Per-quarter difference B3 − B1 is 0.0 for 2023-Q4 to 2025-Q1, and −4.7 in 2025-Q4.
   - **Why:** historically the newest SWS round and CPI quarter at an origin are the same ones that complete the last published label, so "S1 on the newest inputs" is the last published stress.
   - **When they differ:** only when a newer SWS round is published before its label is complete. In E9 that happened once, in 2025-Q4, through the supplementary June 2025 round.
   - **Consequence:** any B3-versus-B1 comparison rests on **one quarter**.
4. **M1's average tie with B3 hides a pattern.**
   - **M1 − B3 per quarter:** −0.59, −1.45, −1.25, −0.42, +0.39, −1.18, **+4.41**. M1 is more accurate in 5 of 7 quarters by about 0.4–1.5 points, but loses badly at the 2025-Q4 turning point.
   - **Why it loses there:** M1 relies on the older last published label, while B3 used the newer SWS round.
5. **The three performance concepts stay separate:**
   - **stress prediction error:** MAE and regional-level error, the most informative;
   - **classification:** accuracy, balanced accuracy and per-class recall, dominated by the 33/2 imbalance;
   - **probability calibration:** never supportable, so M1 probabilities are uncalibrated. Brier was computed only for probability outputs.

## 3. Review of the E9 code and synthetic tests (read, not rerun)

**What the 35 synthetic tests cover:**

- guard decisions and enforcement;
- the read-time row filter;
- quarter arithmetic;
- `cpi_rel` and `cpi_dev` rules (no zero-fill);
- publication-aware training quarters and last published label;
- the poverty vintage;
- the label vault (no early reveal);
- the metric functions.

**What they do not cover:**

- an end-to-end `build_frame` with the timing helpers, though its dates are verified above by the availability audit;
- `predict_all` and `score`;
- an explicit test that B3 equals the S1 formula on inputs.

None of these gaps changes a reported number, because A2–A8 recompute the outputs directly.
