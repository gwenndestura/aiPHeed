# Forecast verification report (CH1-LGBM, Lead 1 = 0.914)

**Branch:** `aiPHeed/firi-data-audit`. **Rules kept:** frozen protocol (sha `dd9ab815…`) and Addenda 1–2 unchanged;
Addendum 3 (sha `b264b76b…`, frozen 2026-10-26T13:22:01Z) added the horizon extension and the analyses below
**before** any lead above 4 was scored. Sealed forecasts untouched. Study period 2021+.

Scripts: `runner/testability.py`, `horizon.py`, `verify.py`, `quarter_tests.py`, `export_horizon.py`.
Outputs: `out/`. Tests: `backend/tests/unit/test_horizon_selection.py`.

## 1. What the target is

**Target T43c(p, q)** = HIGH if **[Balance Luzon hunger(q) > 11.3%]** AND **[province food YoY(q) > its 2021–22 P60
OR food YoY − headline YoY > its 2021–22 P60]**, else LOW.

- **Hunger term:** SWS involuntary hunger, Balance Luzon (all of Luzon outside Metro Manila), quarter mean of the
  regular (non-commissioned) rounds. One value per quarter, shared by all five provinces. This is a **direct
  measurement of food insecurity, at regional level**.
- **Price term:** PSA provincial CPI, published YoY, quarter mean of three months. A **proxy** (affordability stress),
  not a food-insecurity measurement.
- **Thresholds:** E40 `label_spec.json`, frozen 2026-10-15 (hunger 11.3 = P60 of 2021–22; province P60s of 2021–22).
- **Evaluated against:** the T43c label of the target quarter, built from the SWS round(s) fielded in that quarter and
  the province's CPI for its three months.

**So T43c is a combined proxy**, Chapter I's §1.7 definition of food-insecurity *risk*: regional measured hunger above
a line, coinciding with unusual provincial price pressure. A HIGH call is **not** a measured provincial food-insecurity
rate, and "accuracy 0.914" is accuracy on this risk class, not on provincial hunger.

## 2. Reproduction

| Check | Result |
|---|---|
| Fresh re-run (horizon.py) vs saved audited predictions, Leads 0–4 | identical (max difference in P(HIGH) = 0) |
| Metrics recomputed with independent numpy code | match the reported results at every lead |
| Labels rebuilt from raw files only (SWS file, fresh PSA index pull, thresholds) | 100 province-quarters, 20 quarters; 99/100 agree |

**The one disagreement:** Batangas 2025-Q2. The food-minus-headline gap is 0.65 from the recomputed index and just
above the 0.66 threshold from PSA's published (rounded) YoY. The protocol specifies published YoY, so the evaluated
label is the protocol's. The model called it HIGH (0.74); under the index-based label Lead 1 would be **63/70 = 0.900**.

| Lead | Correct / cases | Accuracy | HIGH / LOW | TP FP TN FN | Always-LOW | PERSIST-SI | LGBM-GOV | STRUCT |
|---|---|---|---|---|---|---|---|---|
| 0 (nowcast) | 68 / 80 | 0.850 | 17 / 63 | 10 5 58 7 | 0.787 | 0.850 | 0.850 | 0.725 |
| **1** | **64 / 70** | **0.914** | 17 / 53 | 14 3 50 3 | 0.757 | 0.743 | 0.914 | 0.886 |
| 2 | 35 / 60 | 0.583 | 17 / 43 | 5 13 30 12 | 0.717 | 0.650 | 0.700 | 0.700 |
| 3 | 26 / 50 | 0.520 | 14 / 36 | 3 13 23 11 | 0.720 | 0.540 | 0.640 | 0.660 |
| 4 | 23 / 40 | 0.575 | 10 / 30 | 0 7 23 10 | 0.750 | 0.550 | 0.675 | 0.700 |

## 3. Temporal leakage

| Check (every test row, Leads 0–4) | Result |
|---|---|
| Newest SWS survey used was published before the issue date | all rows (smallest margin 4 days) |
| Newest CPI month was released before the issue date (month end + 5 days) | all rows (smallest margin 26 days) |
| Newest news item was published before the issue date | all rows |
| Target quarter = origin + lead | all rows |
| Every training set: origins before t, targets ≤ t−1, target CPI quarter published by the issue date | all origins, all leads |
| Perturbation: future SWS, CPI and news randomised at every Lead-1 and Lead-2 origin; forecast must not change | see `out/verify_leakage.json` |
| Missing values | left NaN (LightGBM routing); no imputation from future or other provinces |
| Model settings | chosen inside each training window by chronological inner validation; no global feature selection |

**One finding: threshold look-ahead at the first origin.** The frozen thresholds are percentiles of 2021-Q1–2022-Q4
data. At the first Lead-1 issue date (2023-01-01) the 2022-Q4 SWS round (published 2023-01-19) and the December 2022
CPI were not yet out. Only the 2023-Q1 target (5 rows, all LOW and all correct) is affected. Without it, Lead 1 is
**59/65 = 0.908**. The thresholds are fixed constants set once, not refitted per origin; the effect is disclosed rather
than corrected, because changing them would change the frozen target.

## 4. Generalisation across time; independence

**Lead 1 by target quarter**

| Quarter | Issue | Newest SWS | BL hunger | Hunger > 11.3 | HIGH | Correct | Persistence | Always-LOW |
|---|---|---|---|---|---|---|---|---|
| 2023-Q1 | 2023-01-01 | 2022-Q3 | 8.7 | no | 0 | 5 | 5 | 5 |
| 2023-Q2 | 2023-04-01 | 2022-Q4 | 11.3 | no (= line) | 0 | 5 | 5 | 5 |
| 2023-Q3 | 2023-07-01 | 2023-Q1 | 10.3 | no | 0 | 5 | 5 | 5 |
| 2023-Q4 | 2023-10-01 | 2023-Q2 | 14.3 | yes | 3 | 2 | 2 | 2 |
| 2024-Q1 | 2024-01-01 | 2023-Q3 | 15.3 | yes | 0 | 5 | 5 | 5 |
| 2024-Q2 | 2024-04-01 | 2023-Q4 | 19.6 | yes | 4 | 5 | 1 | 1 |
| 2024-Q3 | 2024-07-01 | 2024-Q1 | 18.1 | yes | 1 | 5 | 2 | 4 |
| 2024-Q4 | 2024-10-01 | 2024-Q2 | 25.3 | yes | 3 | 5 | 5 | 2 |
| 2025-Q2 | 2025-04-01 | 2024-Q4 | 16.2 | yes | 3 | 4 | 4 | 2 |
| 2025-Q3 | 2025-07-01 | 2025-Q2 | 23.8 | yes | 2 | 5 | 3 | 3 |
| 2025-Q4 | 2025-10-01 | 2025-Q2 | 16.7 | yes | 0 | 4 | 2 | 5 |
| 2026-Q1 | 2026-01-01 | 2025-Q3 | 22.4 | yes | 0 | 5 | 4 | 5 |
| 2026-Q2 | 2026-04-01 | 2025-Q4 | 17.3 | yes | 1 | 4 | 4 | 4 |
| 2026-Q3 | 2026-07-01 | 2026-Q1 | 23.6 | yes | 0 | 5 | 5 | 5 |

- All three missed HIGH cases are in **2023-Q4**, the onset of the 2023–24 hunger rise, when the latest survey was
  still below the line.
- **Hunger surges** (BL up ≥ 5 points on the previous quarter: 2024-Q4, 2025-Q3, 2026-Q1, 2026-Q3): 20/20 correct
  (persistence 17/20).
- **Latest block** (2025-Q4 to 2026-Q3, 20 rows): 18/20 = 0.90, persistence 0.75, **always-LOW 0.95**. Only 1 HIGH
  occurred in the block, so the model was *below* always-LOW on the most recent quarters.
- By thirds of the quarters: 0.88 / 0.96 / 0.90; leave-one-quarter-out 0.908–0.954.

**The 70 rows are not 70 independent outcomes.** They are 14 quarters × 5 provinces. The hunger term is one value per
quarter, and provincial food inflation co-moves (mean pairwise correlation 0.70).

| Quarter-level view (Lead 1, 14 quarters) | Value |
|---|---|
| Quarters with every province correct | 10 / 14 |
| Quarters where the hunger condition was called correctly (π_H ≥ 0.5) | 12 / 14 |
| Price condition alone, row accuracy | 0.77 |
| CH1 better / worse than **always-LOW**, by quarter (sign test) | 5 / 1, p = 0.11 |
| CH1 better / worse than **persistence** | 5 / 0, p = 0.031 |
| CH1 better / worse than **LGBM-GOV** (no news) | 0 / 0 (identical calls) |

The quarter-clustered bootstrap (90% CI 0.843–0.971) already treats quarters as the unit. At quarter level, the edge
over persistence is significant; the edge over always-LOW rests on 6 differing quarters and is **not** significant
(p = 0.11).

## 5. The 75% requirement against the frozen rule

Lead 1 passes R1–R7 (≥ 10 quarters; accuracy ≥ 0.75; balanced ≥ 0.70; beats always-LOW and persistence; Brier below
persistence and climatology, p < 0.10; precision and recall ≥ 0.60; stable thirds and leave-one-quarter-out). Nothing
was changed to get there. **The result is valid under the frozen rule.**

It demonstrates that, from information published before the quarter starts, the Chapter I risk class of each province
for that quarter is called correctly 91% of the time in 2023–2026 (lower 90% bound 0.84).

Limits:
- It is a combined proxy whose food-insecurity part is regional.
- The evidence is 14 quarters, 17 HIGH rows in 7 of them.
- The advantage over always-LOW is not significant at quarter level.
- The latest block has almost no HIGH cases.
- Sensitivities give 0.900 (index-based label) and 0.908 (without the first origin).

## 6. Reliable horizon (see `MAXIMUM_RELIABLE_LEAD_TIME_VERIFIED.md`)

Every lead with at least one evaluable quarter was scored (1–8). **Maximum reliable lead: 1**. Lead 1 forecasts the
quarter that starts on the issue date, **1–2 quarters after the newest published SWS survey** (13 of 14 quarters: 2).
Leads 2–8 fail.

## 7. The 12 families and news

All 12 families are columns of the price LightGBM (16 columns). Availability ≠ contribution: A1 carries 0.67 of the
Lead-1 SHAP share; C1 carries 0. **News:** CH1 with news and LGBM-GOV without news make identical calls at Lead 1
(Brier difference +0.0004, Holm p = 1.0). Without news, Leads 2–3 are significantly better (Lead 3 Holm p < 0.001).
**News does not improve the forecast.**

## 8. Thesis-ready conclusion (Chapter I objectives)

| Objective | Status | Evidence |
|---|---|---|
| 1 NLP pipeline | **Partially achieved** | Pipeline built and running; no predictive gain at any lead (identical Lead-1 calls without news) |
| 2 I–IV metrics | **Achieved at Lead 1** for the Chapter I risk class | 64/70, 0.914, balanced 0.883, P/R 0.82/0.82, F1 0.82; a combined proxy with a regional hunger term |
| 2 V horizon | **Achieved (determined)** | Maximum reliable lead 1 (1–2 quarters after the newest SWS survey); Leads 2–8 fail; longest credibly testable lead 3 |
| 3 LGU rankings | **Partially achieved** | Rankings built on the validated province forecast × PSA poverty/density; not validated against municipal outcomes; DA evaluator assessment (H4) not yet held |
| 4 Baseline comparison | **Partially achieved** | Beats persistence and the LR comparators; ties LGBM-GOV, so H3 is not rejected under the all-six rule |
| 5 Dashboard / evaluation | **Partially achieved** | Dashboard serves the verified results; FNRI face validity done; ISO 25010 survey not yet run |
