# E166 report: E164 with nested source selection

- **Protocol:** `PROTOCOL.md` (cb60bbdc), with the E165 gates unchanged.
- **Code:** `backend/app/e166/nested_source.py`.
- **Outputs:** `backend/data/e166/out/`.

## What the training-only selection chose
| Outer round | Lead 1 and Lead 2 choice | Source added |
|---|---|---|
| 2018 | OH anchor + ElasticNet + official inputs | **Regional consumption** |
| 2019 | OH anchor + ElasticNet + official inputs | **Regional consumption** |
| 2021 | RSS anchor + RandomForest + official inputs | Farmgate palay |

**Using training rows only, the procedure chose regional consumption in 2 of 3 rounds,** out of five candidate sources. This removes the test-selection objection to the consumption input: it is chosen without seeing the test rows.

## Lead 1 (72 rows)
| | E158 | **E166** |
|---|---|---|
| Accuracy | 73.6 % | **76.4 %** |
| Balanced accuracy | 0.760 | **0.800** |
| HIGH precision / recall | 0.583 / 0.84 | 0.605 / **0.92** |
| LOW precision / recall | 0.889 / 0.681 | **0.941** / 0.681 |
| Macro F1 / AUC / PR-AUC | 0.730 / 0.860 / 0.810 | **0.760 / 0.904 / 0.864** |
| Brier | 0.1344 | **0.1247** (−0.010 [−0.038, +0.020]) |
| Confusion (TP / FP / FN / TN) | 21 / 15 / 4 / 32 | 23 / 15 / **2** / 32 |
| McNemar | | 7 right only for E166, 5 only for E158; p = 0.77 |
| Real − shuffled inputs | | **−0.035 [−0.063, −0.009]: real inputs help** |
| Within-region concordance | 0.60 | **0.75 [0.61, 0.88]** |

## Lead 2
| | E158 | **E166** |
|---|---|---|
| Accuracy | 73.6 % | **79.2 %** |
| Balanced accuracy | 0.760 | 0.822 |
| HIGH / LOW recall | 0.84 / 0.68 | 0.92 / 0.72 |
| Brier | 0.1371 | 0.1246 (−0.012 [−0.044, +0.023]) |
| McNemar | | 7 vs 3, p = 0.34 |
| E156 C1 | fails | **passes** |
| E156 C4 | fails | fails |

## Gates (E165, unchanged)
| Gate | Result |
|---|---|
| F1 Leakage | ✅ 0.0 |
| F2 Beats shuffled provinces | ✅ −0.035 [−0.063, −0.009] |
| F3 Non-inferior to E158 | ✅ |
| F4 HIGH and LOW | ✅ 0.92 / 0.68, balanced 0.80 |
| F5 No material bias | ❌ overall +3.25 (limit ±3); islands within ±5 |
| F6 Probability calibration | ✅ slope 1.53 [0.89, 3.47] |
| F7 Across rounds | ❌ 2021: 80 % vs 88 % (2 rows; limit −5 points). 2018 and 2019 better |
| F8 Features contribute | ✅ |
| F9 Ranks | Interval passes; not displayed (no seal) |
| F10 Reliable Lead 1 | ❌ C1 and C4 fail |

**Status: NOT ACCEPTED** under the fixed gates. F5 misses by 0.25 points and F7 by 2 rows. **The gates are not relaxed.**

## Meaning
- **The owner's claim that regional consumption is meaningful is supported.** The training-only procedure picks it, and with it the inputs beat shuffled provinces significantly. In E165, without any source, they did not.
- **E166 is the strongest legitimate candidate:**

| Lead | E166 | E158 |
|---|---|---|
| 1 | 76.4 % | 73.6 % |
| 2 | 79.2 % | 73.6 % |

- But **it is not better by a statistically significant margin**, it carries a small upward bias, it loses the 2021 round, and **calibration (C4) still fails at every lead.**
- **The live input gap remains.** Consumption data ends in 2023, so it is missing at the 2026-Q4 issue. The owner must download PSA 2024–2025 before E166 can be used live.
- **E158 stays the production thesis model.**
