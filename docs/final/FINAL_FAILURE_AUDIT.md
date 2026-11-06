# Final failure audit

2026-11-06.
- **Sources:** saved out-of-sample forecasts only, recomputed by `backend/app/final_audit/run.py` into `data/final_audit/out/audit.json`.
- **Tests:** `backend/tests/unit/test_final_audit.py`, 12 passed.
- **Evaluation sample:** 72 provincial forecasts at each lead (ENNS2018 22, ENNS2019 25, ENNS2021 25), 25 HIGH and 47 LOW. **Effective n ≈ 46**, because 73 % of error variance is shared within region and round.

## 1. Reproduced results (Lead 1)
| Model | Accuracy | Balanced | HIGH P / R | LOW P / R | Macro F1 | AUC | Brier | Bias (points) | TP / FP / FN / TN |
|---|---|---|---|---|---|---|---|---|---|
| Always-LOW | 65.3 % | 0.500 | n/a / 0 | 0.65 / 1 | 0.395 | n/a | 0.335 | n/a | 0 / 0 / 25 / 47 |
| Persistence | 62.5 % | 0.703 | 0.48 / 0.96 | 0.96 / 0.45 | 0.624 | 0.827 | 0.213 | +9.5 | 24 / 26 / 1 / 21 |
| PSA-only logistic | 55.6 % | 0.650 | 0.44 / 0.96 | 0.94 / 0.34 | 0.550 | 0.762 | 0.228 | n/a | 24 / 31 / 1 / 16 |
| Logistic regression | 61.1 % | 0.665 | 0.47 / 0.84 | 0.85 / 0.49 | 0.611 | 0.803 | 0.307 | n/a | 21 / 24 / 4 / 23 |
| **E158** | **73.6 %** | 0.760 | 0.58 / 0.84 | 0.89 / 0.68 | 0.730 | 0.860 | 0.1344 | +2.9 | 21 / 15 / 4 / 32 |
| E164 AUTO (withdrawn) | 79.2 % | 0.812 | 0.65 / 0.88 | 0.92 / 0.75 | 0.785 | 0.901 | 0.1223 | +2.8 | 22 / 12 / 3 / 35 |
| E165 AUTO-FINAL | 73.6 % | 0.770 | 0.58 / 0.88 | 0.91 / 0.66 | 0.732 | 0.894 | 0.1213 | +2.6 | 22 / 16 / 3 / 31 |
| **E166** | **76.4 %** | **0.800** | 0.61 / **0.92** | **0.94** / 0.68 | 0.760 | **0.904** | 0.1247 | +3.25 | 23 / 15 / 2 / 32 |
| E167 | 66.7 % | 0.726 | 0.51 / 0.92 | 0.93 / 0.53 | 0.666 | 0.893 | 0.1562 | +6.3 | 23 / 22 / 2 / 25 |

Every figure matches the earlier reports.

## 2. Failures and verified root causes
| Failure | Verified cause | Category |
|---|---|---|
| **Bias toward LOW provinces (+5 to +11 points in 2018/2019)** | National HFIAS fell from 56.2 % (2015) to 46.5 % (2018). The 2018 and 2019 forecasts had only the 2013 and 2015 rounds, so the fall was invisible to them. In 2021 the bias is −2.0 | **Distribution shift**, plus too few rounds |
| **C1 at Lead 1** | 55/72 correct; 56 are needed at effective n 45.5 | **Insufficient observations** |
| **C4, every model and lead** | The level error changes sign between rounds (+6.8, +5.4, −2.0), and 2021 is over-dispersed within the round (slope 0.62). A correction learned from 2018/2019 made 2021 worse (`docs/e166/C1_C4_ANALYSIS.md`) | **Distribution shift, insufficient rounds** |
| **E164's 79.2 %** | Consumption inputs selected in E157 by ranking sources on the test rows | **Evaluation contamination**, corrected in E165 |
| **2021 round, E166 below E158** | Two near-threshold provinces flipped. The source choice switched from consumption to palay | Temporal instability |
| **E167 worse than E166** | Changing the calibration choice and fold rule switched the selected learners (ridge, LightGBM). Real inputs then did worse than shuffled ones | **Selection instability:** the signal is weak |
| **Employment and remittances contribute nothing** | Official inputs are national only (identical for every province in a quarter) | **Geographic limitation** |
| **News: high importance, no value** | Many high-variance columns attract tree splits that do not generalise. Removing or shuffling news never improved results out of sample | Data quality / relevance |
| **Province order within regions (E158 0.60)** | E158's structural level overrides each province's survey position | Architecture, improved in E166 (0.75) |
| **No HIGH test case in CALABARZON** | No CALABARZON reading has ever been at or above 50 | **Target coverage** |

**Not found:**
- **temporal leakage:** corruption tests gave 0.0 change for E160–E167;
- invalid labels (see TARGET_VALIDITY_AUDIT);
- preprocessing errors;
- class-imbalance artefacts: models are not dominated by LOW, and HIGH recall is 0.84–0.92;
- implementation errors in C1–C6, which reproduce exactly.

## 3. The C4 inconsistency: resolved
Earlier reports quoted two different "calibration slopes":

| Name in reports | Exact calculation (code) | E158 Lead 1 | E166 Lead 1 |
|---|---|---|---|
| **C4 (E156, pre-registered)** | Slope of observed logit prevalence `y_true` on predicted logit `mu`. 95 % CI by region-cluster bootstrap (`Pv.scale_test`, used in `e156/leads.py` line 44) | 0.72 [0.47, 0.91]: **fail** | 0.74 [0.51, 0.87]: **fail** |
| "Probability calibration slope" (E165 F6; the "1.53" in E166/E167 reports) | Logistic regression of observed HIGH (0/1) on logit(P(HIGH)) (`e165/final.py` `prob_cal`) | 1.53 [0.96, 2.73] | 1.53 [0.93, 3.40] |

- **They measure different things.**
  - The C4 slope below 1 means the **predicted prevalence levels vary more than the outcomes do**.
  - The probability slope above 1 means **P(HIGH) is compressed toward 0.5** (under-confident).
  - Both come from the same cause: round-level drift inflates the error sd, which spreads the levels and flattens the probabilities.
- **The E156 document's wording** ("probabilities not systematically over- or under-confident") describes the purpose, but **the implemented and pre-registered test is the logit-level slope.**
- **The implemented definition stays authoritative.** Switching to the probability slope now, after the results, would change a criterion post hoc.
- **It does not change the answer.** Under the probability-slope reading, E166 would pass C4 at Leads 1 and 2, but Lead 1 still fails C1. **The maximum reliable lead is 0 under either reading.**
- **Recommendation:** ask the adviser to confirm which definition C4 is meant to have, **for future rounds only**.
