# Does Lead-1 accuracy generalize across quarters?

**Companion to** `LEAD1_OBJECTIVES_1_4_ASSESSMENT.md`.

**Inputs.**
- Criteria: `GENERALIZATION_CRITERIA.md`, committed at fbd29b7 **before** any quarter-level number was computed.
- Analysis: `runner/quarter_generalization.py`, with outputs `quarter_metrics.csv` (every model × quarter) and
  `generalization_results.json`.
- Rows: the walk-forward Lead-1 forecasts of the E84 run (65 forecasts, 13 target quarters 2023-Q1..2026-Q3, target
  T43).

**Model judged.** S-SIM, the pre-registered model behind the reported **84.6%** (55/65). The proposed LightGBM
(30 issued rows), the post-hoc hybrid and E88 ENS-ROLL are reported alongside it.

## 1. Quarter by quarter (S-SIM, 5 provinces per quarter)

"Label = price condition" is the share of the quarter's 5 labels that equal the provincial food-price condition alone.

| Target quarter | Regional hunger (%) | Label = price condition | Actual HIGH | Predicted HIGH | Correct | Accuracy | TP / FP / FN | S-SIM vs persistence |
|---|---|---|---|---|---|---|---|---|
| 2023-Q1 | 8.7 | 0.0 | 0 | 0 | 5 | 1.00 | 0/0/0 | tie (1.00) |
| 2023-Q2 | 11.3 | 0.2 | 0 | 0 | 5 | 1.00 | 0/0/0 | tie (1.00) |
| 2023-Q3 | 10.3 | 0.0 | 0 | 0 | 5 | 1.00 | 0/0/0 | tie (1.00) |
| 2023-Q4 | 14.3 | 1.0 | 3 | 0 | **2** | **0.40** | 0/0/3 | tie (0.40) |
| 2024-Q1 | 15.3 | 1.0 | 0 | 0 | 5 | 1.00 | 0/0/0 | tie (1.00) |
| 2024-Q2 | 19.6 | 1.0 | 4 | 3 | 4 | 0.80 | 3/0/1 | tie (0.80) |
| 2024-Q3 | 18.1 | 1.0 | 1 | 1 | 5 | 1.00 | 1/0/0 | win (0.80) |
| 2024-Q4 | 25.3 | 1.0 | 3 | 1 | 3 | 0.60 | 1/0/2 | loss (0.80) |
| 2025-Q1 | 24.0 | 1.0 | 4 | 4 | 5 | 1.00 | 4/0/0 | win (0.40) |
| 2025-Q4 | 16.7 | 1.0 | 0 | 1 | 4 | 0.80 | 0/1/0 | win (0.20) |
| 2026-Q1 | 22.4 | 1.0 | 0 | 0 | 5 | 1.00 | 0/0/0 | win (0.20) |
| 2026-Q2 | 17.3 | 1.0 | 1 | 1 | 3 | 0.60 | 0/1/1 | loss (0.80) |
| 2026-Q3 | 23.6 | 1.0 | 0 | 1 | 4 | 0.80 | 0/1/0 | loss (1.00) |

**Small-sample disclosure.** Each quarter has only 5 rows, which share one regional hunger reading. Seven quarters
contain **no HIGH row**: 2023-Q1, Q2 and Q3, 2024-Q1, 2025-Q4, 2026-Q1 and 2026-Q3. In those quarters, always-LOW is
also 100% correct.

## 2. Is each quarter genuinely unseen? (leakage and design audit)

| Check | Result |
|---|---|
| Lead-1 alignment: every row targets origin + 1 | Verified for all 65 rows (origins 2022-Q4..2026-Q2) |
| Training labels in the expanding window | 0 violations. Each label quarter is ≤ t−1 and every SWS round behind it was published before O(t) (example: origin 2026-Q2 trains up to 2026-Q1, published 2026-05-12) |
| Input cut-off at each origin | 0 violations across all origins: CPI months ≤ month 2 of quarter t, SWS published before O(t), production ≤ t−1 |
| Learned preprocessing | Medians, means and scales are fitted inside each origin's `fit()` on its training rows only (`e43_lib.LRModel.fit`). LightGBM uses no scaling. S-SIM fits no outcome parameters. |
| Thresholds and selection | S-SIM uses 0.5. Threshold and ensemble choices in the post-hoc and E88 arms use only labels published before each origin. No calibration step exists. |
| Correlated rows | The 5 rows of a quarter share regional hunger, so uncertainty is computed by **quarter-block bootstrap** and tests are run **per quarter**. Effective n = 13, not 65. |
| **Weakness 1: target design** | The T43 thresholds use 2021–22 data only. But E40 chose the **percentile (P60)** with prevalence gates computed on development quarters 2023-Q1..2025-Q1, which overlap this evaluation. The label definition is therefore not fully independent of the evaluation period. Not corrected: redefining the approved target is outside scope. Disclosed. |
| **Weakness 2: re-use of quarters** | The same 13 quarters were examined in E83–E88. S-SIM was pre-registered in E83, so its 84.6% is not selection-inflated. The hybrid and ENS-ROLL were chosen later and are optimistic. None of these quarters is truly unseen; only the sealed 2026-Q4..2027-Q2 forecasts are. |

No leakage defect was found in the forecasting pipeline.

## 3. Stability and comparison with baselines

**Pooled (S-SIM).**
- 55/65 = 0.846. Quarter-block bootstrap 95% CI **[0.738, 0.938]**.
- Persistence 0.723, CI [0.554, 0.877]; always-LOW 0.754, CI [0.584, 0.923]. The intervals overlap.

**Early vs late period (S-SIM).**

| Period | Rows | Accuracy | Balanced | Recall (HIGH) | Precision (HIGH) |
|---|---|---|---|---|---|
| Early (2023–2024) | 40 | 0.85 | 0.73 | 5/11 = 0.45 | 1.00 |
| Late (2025–2026) | 25 | 0.84 | 0.83 | 4/5 = 0.80 | 0.57 |

**Quarter-level comparison with persistence** (13 quarters): 4 wins, 3 losses, 6 ties. One-sided sign test p = 0.50.

**Quarters that contain a HIGH row** (6 quarters, 30 rows, 16 HIGH):

| Model | Correct | Accuracy |
|---|---|---|
| S-SIM | 22/30 | 0.73 |
| Persistence | 20/30 | 0.67 |
| Always-LOW | 14/30 | 0.47 |

**Changing-risk rows** (label differs from the latest known label; persistence is wrong on all of them):

| Model | Rising (0 → 1), 9 rows | Falling (1 → 0), 9 rows |
|---|---|---|
| S-SIM | 5/9 | 8/9 |
| ENS-ROLL | 4/9 | 9/9 |
| Hybrid | 6/9 | 8/9 |

**Does the model just repeat the previous label?** S-SIM agrees with persistence on 72% of rows, LightGBM on 50%.

**Other models, quarter-block CIs.**

| Model | Accuracy | 95% CI | Note |
|---|---|---|---|
| LightGBM | 0.867 | [0.733, 0.967] | 30 rows; beats persistence in 3 of 6 quarters, loses 1 |
| PSA-only | 0.867 | [0.733, 0.967] | same 30 rows |
| Hybrid | 0.877 | [0.769, 0.969] | |
| ENS-ROLL | 0.862 | [0.723, 0.969] | |

**Pre-set criteria (S-SIM).**

| Criterion | Result | Pass |
|---|---|---|
| (a) Quarters with at least 3/5 correct | 12/13 = 92% (only 2023-Q4 fails) | Yes |
| (b) Early and late accuracy ≥ 0.75 | 0.85 and 0.84 | Yes |
| (c) More quarter wins than losses vs persistence, sign-test p < 0.10 | 4–3, p = 0.50 | **No** |
| (d) Pooled HIGH recall ≥ 0.5 and HIGH caught in each period | 0.56; yes | Yes |
| (e) Changing-risk accuracy ≥ 0.5 and above persistence | 13/18 = 0.72 vs 0 | Yes |

**Verdict: Partially generalized.**

## 4. Food insecurity or proxy?

- **Proxy target (province level).**
  - From 2023-Q4 on, the label equals the provincial food-price condition in every quarter.
  - In 2023-Q1..Q3 the label was LOW because hunger was below 11.3%, even where prices were high.
  - The cross-quarter stability above is stability on **hunger-gated food-price pressure**.
- **Independently measured food insecurity** (SWS Balance Luzon hunger above 11.3%, one regional value per quarter,
  13 quarters):

  | Method | Correct | Accuracy |
  |---|---|---|
  | S-SIM's hunger component | 12/13 | 0.92 |
  | Persistence of the last reading | 11/13 | 0.85 |
  | Always above 11.3% | 10/13 | 0.77 |

  This is regional, a single series, and differs from persistence by one quarter. It cannot establish provincial
  food-insecurity generalization.

## 5. Conclusion

Lead-1 accuracy is **partially generalized**:
- it is stable across the early and late periods (0.85 and 0.84);
- the correct majority holds in 12 of 13 quarters;
- it recovers most falling-risk transitions and about half of rising ones;
- it outperforms persistence where risk changes.

It is **not** demonstrated to be better than naive persistence quarter by quarter (4 wins, 3 losses). Its pooled
interval overlaps persistence and always-LOW. Seven of the 13 quarters contain no HIGH case, which flatters accuracy.

The generalization shown is generalization on the **proxy target** (hunger-gated food-price pressure). It is not
demonstrated generalization in predicting household food insecurity at province level. Only the sealed prospective
quarters can show performance on truly unseen data.
