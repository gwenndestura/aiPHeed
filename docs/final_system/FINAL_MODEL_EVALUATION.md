# Final model evaluation

**Evidence**
- Protocol: `aipheed-backend-aligned/experiments/FINAL_OBJECTIVE_ACHIEVEMENT/FINAL_FORECASTING_PROTOCOL.md` (sha `d94f0c2c…`), frozen before scoring.
- Outputs: `out/results_primary.json`, `results_verify.json`, `results_placebo.json`, `predictions_primary.csv`.
- Served copy: `backend/data/final_engine/` via `/api/v1/final/evaluation`.

**Status:** **development evidence.** Every 2021–2026 quarter had already been examined in E107–FINAL. The only untouched test is prospective: the seals listed in §8.

## 1. What the model forecasts

| Item | Value |
|---|---|
| Outcome | SWS involuntary ("Total") hunger: the % of families who experienced hunger at least once in the past 3 months |
| Geography | The four SWS areas: NCR, Balance Luzon, Visayas, Mindanao. Balance Luzon contains CALABARZON. |
| Not forecast | Any province, city or municipality: none is measured |
| Classification target (Chapter I Objective 2) | ELEVATED = the area's hunger is above its average over the previous four quarters. Defined and frozen before scoring in FINAL; base rate 0.57; a researcher-defined class, not an SWS or PSA category. |
| Continuous target | Hunger level in percentage points, scored by MAE and RMSE |
| Leads | Lead 0 = the quarter that just ended, whose survey is not yet published (true horizon 1). Leads 1–4 = the next 1–4 quarters. |
| Issue date | The first day of each quarter |

## 2. The model (FIL-OA)

- **Model:** one LightGBM regressor, re-fitted every quarter on everything published before that quarter's issue date.
- **Pooling:** 4 areas × 5 leads.
- **Inputs:** all 12 indicator families (27 columns; `data/feature_map.csv`).
- **What it learns:** the **change from the latest SWS reading**. A model that learned the level itself (FINAL's FIL) absorbed the 2021–23 decline as a rule and failed in the 2024 surge. Anchoring on the latest reading is the change that fixed it.

**Other settings**

| Setting | Value |
|---|---|
| News source | GDELT GKG CALABARZON documents, timestamped in real time by GDELT, measured since the last survey and de-duplicated |
| Survey method change | A flag for the 2025 switch from household-head to adult respondents |
| Missing values | Handled natively by LightGBM; never set to zero |
| Tuning | 4 settings, chosen on each origin's own most recent training quarters |

## 3. Results by lead (2021+ walk-forward; 4-area panel)

| Lead | Rows / quarters | Accuracy | Balanced accuracy | Precision | Recall | F1 | AUC | Confusion (TP/FP/TN/FN) | MAE (pp) | Latest-reading MAE | p (MAE better) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 44 / 11 | **0.614** | 0.621 | 0.783 | 0.600 | 0.679 | 0.710 | 18/5/9/12 | **3.47** | 4.19 | **.025** |
| 1 | 44 / 11 | 0.523 | 0.558 | 0.706 | 0.429 | 0.533 | 0.547 | 12/5/11/16 | 4.95 | 5.05 | .32 |
| 2 | 40 / 10 | 0.500 | 0.516 | 0.667 | 0.462 | 0.545 | 0.489 | 12/6/8/14 | 6.51 | 5.98 | .86 |
| 3 | 36 / 9 | 0.361 | 0.333 | 0.500 | 0.435 | 0.465 | 0.261 | 10/10/3/13 | 7.71 | 6.46 | 1.0 |
| 4 | 32 / 8 | 0.562 | 0.559 | 0.647 | 0.579 | 0.611 | 0.437 | 11/6/7/8 | 7.99 | 6.51 | 1.0 |

The p-value is a one-sided paired cluster bootstrap over target quarters.

**Baselines on the same rows (accuracy)**

| Lead | Latest reading | MA2 | Climatology | Always ELEVATED | Logistic regression | PSA-only | NLP-only |
|---|---|---|---|---|---|---|---|
| 0 | 0.659 | 0.636 | 0.545 | 0.682 | 0.568 | 0.682 | 0.682 |
| 1 | 0.614 | 0.500 | 0.409 | 0.636 | 0.636 | 0.591 | 0.455 |
| 2 | 0.550 | 0.450 | 0.300 | 0.650 | 0.475 | 0.650 | 0.450 |
| 3 | 0.361 | 0.528 | 0.306 | 0.639 | 0.444 | 0.528 | 0.306 |
| 4 | 0.406 | 0.562 | 0.469 | 0.594 | 0.562 | 0.531 | 0.406 |

**Verdict**

| Question | Answer |
|---|---|
| 75% accuracy target | **Not reached.** The best result is 0.614 at Lead 0. |
| Beats the latest-reading baseline in accuracy? | No, at Leads 0–3 |
| Lower level error? | **Yes at Lead 0** (3.47 vs 4.19 points; p = .025). The difference is about even at Lead 1 and worse beyond. |
| Accuracy at Lead 4 | 0.56 vs the latest reading's 0.41, but always-ELEVATED scores 0.59 on the same rows, so this is not skill |

**Compared with FINAL's FIL** (level-learning, same data): Lead-1 accuracy rose from 0.32 to 0.52 and MAE fell from 5.72 to 4.95.

## 4. Reliability rule and maximum lead

**The rule** (frozen, the same at every lead):

| # | Criterion |
|---|---|
| R1 | At least 10 quarters and 30 rows |
| R2 | Accuracy ≥ 0.75 |
| R3 | Balanced accuracy ≥ 0.70 and above every baseline |
| R4 | Brier score significantly better than the latest reading and climatology |
| R5 | Precision and recall ≥ 0.60 |
| R6 | Accuracy ≥ 0.60 in each third of the period |
| R7 | Balance Luzon accuracy ≥ 0.70 |
| R8 | MAE ≤ the latest reading's |

**Passed:** Lead 0 passes R1, R5 and R8; Lead 1 passes R1 and R8; Leads 2–4 pass nothing or only R1.

**Maximum reliable lead: none established.**

## 5. Why 75% was not reached (verified, not assumed)

| Check | Finding |
|---|---|
| **Test–retest (empirical, no model)** | Two SWS rounds taken in the *same* quarter (2021-Q2, 2022-Q2, 2025-Q2) give the same ELEVATED label only 3 times in 8, and differ by 3.7 points on average. A single survey reading often disagrees with itself on this label. |
| **Validated ceiling** | The data were simulated as a true level plus survey noise, using 2021+ parameters only. The simulation reproduced the real accuracy of the latest-reading and MA2 rules in **10 of 10** checks. In that simulation, a forecaster that knows the true process reaches **0.64** at true horizon 1 (Lead 0), 0.58 at 2, 0.54 at 3, 0.53 at 4 and 0.50 at 5. |
| **Untouched history (secondary arm, pre-2021, flagged)** | FINAL's long-history model scored 0.50–0.55 on 70 untouched quarters (2003–2020). Even without survey noise, the ceiling at Lead 1 is about 0.63. |

**Conclusion.** With SWS regional hunger as the outcome, 75% accuracy is above what any model can reach. Better tuning cannot get there. A different outcome with predictable local variation is needed (`THESIS_OBJECTIVE_ASSESSMENT.md`).

## 6. News

| Test | Result |
|---|---|
| With vs without news, same rows | Accuracy 0.61/0.61 (Lead 0), 0.52/0.55 (Lead 1); Brier differences ≤ 0.005; Holm p = 1 at every lead |
| Placebo (100 refits with news shuffled across quarters) | Real news no better than shuffled; p = 0.39 at Leads 0 and 1 |
| GDELT vs the project RSS corpus as the news source | The corpus gives 0.66 / 0.55 at Leads 0–1, within noise of the GDELT version (FIL-OA-CORPUS) |
| News share of SHAP attribution | 3–4% |
| Earlier result (FINAL) | One corpus association (agri-supply news, ρ 0.74) did not replicate in two GDELT sources |

**Conclusion:** news is **context only**. The dashboard marks each headline as a reported event or a possible future risk, and says news is not evidence that hunger will rise.

## 7. Generalization and surges

**By period (Lead 0, FIL-OA vs the latest reading)**

| Period | FIL-OA | Latest reading |
|---|---|---|
| ≤ 2023 | 0.38 | 0.62 |
| 2024 | 0.81 | 0.88 |
| 2025+ | 0.55 | 0.50 |

The MAE is lower in 2025+ (3.14 vs 4.61 points).

**By direction (Lead 0)**

| Direction | FIL-OA | Latest reading |
|---|---|---|
| Falling hunger | 0.71 | 0.65 |
| Rising hunger | 0.56 | 0.67 |

**Leave one quarter out:** the accuracy difference against the latest reading at Lead 0 ranges from −0.07 to +0.03. No single quarter drives the result.

**Sharp increases** (a rise larger than the survey margin; 10 events at Lead 0)

| Model | Flagged ELEVATED | Mean under-prediction | False alarms |
|---|---|---|---|
| FIL-OA | 6 | −6.9 points | 5 of 14 |
| Latest reading | 6 | −8.1 points | — |
| Cost-sensitive variant (ASYM) | 8 | −5.9 points | 11 of 14 |

**Conclusion:** sharp increases are **not anticipated reliably**. The cost-sensitive variant catches more surges only by raising many false alarms.

## 8. Prospective confirmation (sealed, never overwritten)

| Seal | SHA-256 | Targets |
|---|---|---|
| FIL-OA + ASYM | `03534689…` | Issued 2026-10-01; 2026-Q4 … 2027-Q3 |
| FINAL | `c73a0709…` | |
| E107–E113 | Hashes verified by `tests/integration/test_api_final_system.py` | |

**How to score:** run `runner/score_prospective.py` once SWS publishes 2026-Q4, around January 2027.
