# E128 maximum reliable forecast lead time

**Rule (frozen).** R1–R7 of the FINAL_THESIS_OBJECTIVES protocol, unchanged. A lead is reliable only if it passes all seven on the outer walk-forward rows. The maximum reliable lead is the largest K with Leads 1..K all passing.

**Sources.** `E128_RELIABLE_HORIZON_COMPARISON.csv`, `E128_LEAD_1_TO_4_COMPARISON.csv`.

## Result

| Model | T1 (primary) | T4 (sensitivity) |
|---|---|---|
| LightGBM (proposed) | **None established** | None |
| Naive persistence | None | None |
| PSA-only | None | None |
| NLP-only | None | None |
| Logistic Regression | None | None |

**Calendar duration: 0 months.**
- No horizon (3, 6, 9 or 12 months) is supported at the regional level with 2021–2026 data.
- **Status: inconclusive, not "shown unreliable".** The rows needed to establish reliability do not exist (R1), and every row was previously inspected.

## Why: the criteria at Lead 1 (the first lead tested)

**LightGBM, T1**

| Criterion | Value | Requirement | Pass |
|---|---|---|---|
| R1 | 13 quarters, 13 rows | ≥ 10 quarters and ≥ 40 rows | ✗ (rows) |
| R2 | Accuracy 0.615 | ≥ 0.75 | ✗ |
| R3 | Balanced accuracy 0.773 (only 2 LOW rows) | ≥ 0.70 | ✓ |
| R4 | 0.615 vs majority 0.615 and persistence 0.846 | Greater than both | ✗ |
| R5 | Brier 0.332 vs persistence 0.154 (p 0.97) and CLIM 0.294 (p 0.66) | Lower than both, p < 0.10 | ✗ |
| R6 | Precision 1.00, recall 0.545 | Both ≥ 0.60 | ✗ |
| R7 | Thirds 0.40 / 0.50 / 1.00; leave-one-quarter-out minimum 0.58 | ≥ 0.60 and ≥ 0.70 | ✗ |

## Even with R1's 40-row part removed (sensitivity, not the verdict)

**No model passes any lead under either target.**

**Closest: PSA-only, T4 Lead 1.** It fails **R5** only:
- accuracy 0.909, balanced accuracy 0.938, precision 1.00, recall 0.875;
- Brier 0.156 vs persistence 0.182, one-sided p 0.42, so not significant;
- n = 11 quarters, 3 LOW.

**Why it is not a finding**
- It is 1 of 40 model × target × lead cells, so a multiple-comparison artefact is likely.
- It does not extend to Lead 2 (accuracy 0.50, balanced accuracy 0.40).

## Answers

| Question | Answer |
|---|---|
| LightGBM maximum reliable lead | **None established** (0 quarters) |
| Each baseline | **None** |
| Does LightGBM extend the horizon beyond the baselines? | **No.** No model has a horizon. LightGBM is not better than any baseline at any lead after Holm correction. Its one "significant" result, vs LR at T1 Lead 4, compares two models that were both 0 % accurate. |
| Independent evaluation observations supporting the result | 13 / 8 / 7 / 6 quarters at Leads 1–4 (T1); 11 / 8 / 7 / 6 (T4) |
| Confirmed, provisional or inconclusive | **Inconclusive** |
| Furthest defensible forecast horizon | **None established** with the regional SWS target in 2021–2026. Earlier Chapter I work reported Lead 1 for the province-quarter T43c (CH1 / LEAD2). That label is not admissible under E128's rules, so E128 cannot confirm it. |
