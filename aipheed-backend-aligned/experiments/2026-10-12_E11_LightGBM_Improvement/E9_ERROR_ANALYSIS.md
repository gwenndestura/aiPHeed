# E9 Error Analysis (from E9's permitted outputs; reproduced in the E10 audit)

**E9 core LightGBM (M1)** compared with the baselines. Stress MAE by quarter:

| | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q4 | All |
|---|---|---|---|---|---|---|---|---|
| M1 | 2.41 | 3.55 | 4.05 | 3.91 | **6.09** | 4.72 | **7.01** | 4.54 |
| Carry-forward | 3.00 | 5.00 | 5.30 | 4.34 | 5.70 | 5.90 | 7.30 | 5.22 |
| Regional | 3.71 | 5.00 | 5.30 | 3.36 | 5.70 | 5.90 | 2.30 | 4.47 |
| S1 rule | 3.00 | 5.00 | 5.30 | 4.34 | 5.70 | 5.90 | 2.60 | 4.55 |

**M1 bias** (mean predicted − true): −2.3, −3.5, −4.1, −3.6, −6.1, −4.7, **+7.0**.

## Confirmed findings (computed from outputs)

1. **Largest errors are in 2024-Q4 and 2025-Q4, and in Quezon.** Quezon's MAE is 8.3–11.8 across arms, against 2.0–5.0 for the other provinces. Quezon's provincial component swung from the lowest in 2023 to the highest in 2024–25.
2. **Direction:** under-prediction while stress rose (2023-Q4 to 2025-Q1), then over-prediction at the 2025-Q4 fall. Inputs are 2 quarters old, so all arms lag a moving series.
3. **Predictions too similar across provinces:** M1's provincial spread was 0.0–2.1 from 2024-Q2, against a true 6.5–14.7.
4. **M1 vs carry-forward:** better in 6 of 7 quarters (mean −0.68; bootstrap [−1.11, −0.20]).
5. **M1 vs regional hunger alone (+0.07) and vs the S1 rule (−0.01):** no improvement. The S1 rule equals carry-forward in 6 of 7 quarters and differs only in 2025-Q4, when a newer SWS round existed.
6. **Expanded features overfit:** training MAE 1.3–1.5 vs test MAE 4.9–5.2; more features did not lower test error.
7. **The LOW-class results rest on 2 rows (Quezon 2023-Q4, 2024-Q1).** Balanced accuracy differences between arms come only from those 2 rows and from HIGH recall. Stress-error comparisons do not depend on the class split.
8. **Reuse:** the 7 test quarters were used in E1–E8. The E9 evidence is exploratory.

## Hypotheses tested in E11

| Hypothesis | E11 test | Outcome |
|---|---|---|
| H-a: the shared regional SWS dominates the model, so provinces collapse | Gain share; within-quarter variance | **Supported.** Direct models put 61–100% of gain on regional features or last stress. SWS, regional CPI and unemployment have 0% within-quarter variance. |
| H-b: provincial inputs carry enough variation to learn local differences | Within-quarter share; correlation with the realized deviation d | **Partly.** `cpi_rel` and `anchor_dev` vary only across provinces (100%) and correlate 0.60 / 0.55 with realized d (in-sample, descriptive). But observed province rankings are unstable between consecutive quarters (Kendall τ 0.0–1.0). |
| H-c: over-regularization flattens provinces | Fixed grid C2→C3 | **Not the main cause.** Direct models collapse under every configuration, while the decomposed model keeps a 3–7 point spread. |
| H-d: the S1 formula itself generates the provincial variation | Compare structures | **Supported.** Structures that keep the S1 provincial term (S1 rule, decomposed, residual) preserve spread and ranking. Direct regressors do not. |
| H-e: ML adds value as a correction to the S1 rule | Residual structure | **Not established.** Mean −0.81 vs the S1 rule, but only 4 of 7 quarters better and the interval crosses 0 (see `RESULTS_SUMMARY.md`). |
