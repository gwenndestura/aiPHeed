# E128 temporal generalization

**Source.** `out/temporal_conditions.csv` and `E128_LEAD_1_TO_4_COMPARISON.csv` (DEV / LATER blocks).

**About the condition tags.** They describe the target quarter after the fact. They are used for analysis only, not as inputs.

## By block (T1, accuracy / Brier)

| Model | Lead 1 DEV (n = 7) | Lead 1 LATER (n = 6) | Lead 2 DEV (2) | Lead 2 LATER (6) | Lead 4 LATER (6) |
|---|---|---|---|---|---|
| LightGBM | 0.57 / 0.31 | 0.67 / 0.36 | 0.50 / 0.30 | 1.00 / 0.01 | **0.00 / 0.70** |
| Persistence | 0.71 / 0.29 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 |
| PSA-only | 0.71 / 0.32 | 0.67 / 0.29 | 0.50 / 0.29 | 1.00 / 0.01 | 0.33 / 0.57 |
| NLP-only | 0.43 / 0.38 | 1.00 / 0.07 | 0.50 / 0.20 | 1.00 / 0.06 | 0.67 / 0.25 |
| Log. Regression | 0.71 / 0.31 | 0.67 / 0.32 | 1.00 / 0.01 | 0.83 / 0.05 | 0.00 / 0.90 |

## By condition (LightGBM vs persistence accuracy, T1; n in brackets)

| Condition of the target quarter | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| Before 2023-Q4 (lower-hunger regime) | 1.00 vs 1.00 [2] | — | — | — |
| From 2023-Q4 (high-hunger regime) | 0.55 vs 0.82 [11] | 0.88 vs 1.00 [8] | 0.86 vs 1.00 [7] | 0.00 vs 1.00 [6] |
| Hunger ≥ 15 % | 0.60 vs 0.90 [10] | 0.88 vs 1.00 [8] | 0.86 vs 1.00 [7] | 0.00 vs 1.00 [6] |
| Food CPI YoY ≥ 5 % | 1.00 vs 1.00 [2] | — | — | — |
| ≥ 8 storms entering PAR | 0.67 vs 1.00 [3] | 0.50 vs 1.00 [2] | 1.00 vs 1.00 [1] | 0.00 vs 1.00 [1] |
| Unemployment rising (YoY) | 0.60 vs 1.00 [5] | 1.00 vs 1.00 [5] | 1.00 vs 1.00 [5] | 0.00 vs 1.00 [5] |

## Findings

**1. No stable generalization.**
- LightGBM is worse than persistence in the high-hunger regime at every lead.
- All five of its Lead-1 errors are high-hunger quarters: 2023-Q4, 2024-Q1, 2024-Q2, 2025-Q2 and 2025-Q3. In each, it predicted LOW (p 0.06–0.29) because the training years had low hunger.

**2. Results depend on a few easy quarters.**
- The T1 Lead 2–3 accuracies (0.86–0.88) come from 7–8 consecutive HIGH quarters.
- Any model that predicts HIGH gets them.

**3. The condition subsets are tiny** (1–5 quarters for food inflation, typhoons and employment). No condition-specific claim is supportable.

**4. T4 (above recent usual)**
- Lead 1 LATER: LightGBM 0.67, persistence 0.67 (n = 6). PSA-only 0.83.
- Leads 2–4: every model is 0.17–0.67, around or below chance.
