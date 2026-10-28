# aiPHeed Lead 2: audit, corrections, evaluation and thesis sections

**Date:** 2026-10-28. **Branch:** `aiPHeed/forecast-research` (local; not pushed; production model not replaced).

**Evidence base:** LEAD2_FIVE_TRIGGER (protocol a80e927f; Addendum 1 for the trigger groups; Addendum 2 for the validation threshold, frozen before scoring), FORECAST_RESEARCH, FORECAST_RESEARCH_II and OUTCOME_GAP_RESOLUTION. Every 2021-2026 figure is **development evidence**: these quarters had already been examined.

---

## 1. Most consequential findings of the audit

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| 1 | **The target is a price-and-hunger proxy, not measured food insecurity.** Since 2023-Q4 it equals the food-price condition in 55/55 rows. | FR-II §2 | Lead 2 forecasts the Chapter I risk class, and must be described that way |
| 2 | **No provincial or quarterly food-insecurity outcome exists** to validate against | OUTCOME_GAP_RESOLUTION: NOT EVALUABLE | No claim of validated food-insecurity prediction is possible |
| 3 | **Lead-2 misses come from information that did not exist at the cut-off:** a hunger reading tied at 11.3, and price rises after the issue date | §3 (7/7 misses analysed) | No valid model change recovers them (§4) |
| 4 | **The sample is small:** 13 Lead-2 quarters, 7 with any HIGH case, n_eff ≈ 29 | power analysis (FR-II §8) | One HIGH case decides R6. Differences of 0.02 Brier need about 100 quarters to detect. |
| 5 | **No pipeline defect.** The served model reproduces exactly from code (5e-7). 21/21 inputs reach the model; there are no duplicates and no misaligned dates. Training and evaluation labels agree (95/95). The dashboard and Landing figures equal the evaluation file. | `out/input_audit.json` | The low Lead-2 recall is not a bug |
| 6 | **News defect:** the XLM-R index (N1) is missing in 79% of rows | input audit | Fixing coverage (C1) changed nothing: the model never used the added column, because headline-level news exists for only 9 of 22 quarters |
| 7 | **Dashboard defect (fixed):** the map opened on Q1 2027 instead of the Lead-1 quarter | `MapDashboard.tsx` | It now opens on the backend default, Q4 2026 |

## 2. Target decision

- **Kept: T43c**, the Chapter I definition (§1.4 dependent variable; §1.7 "SWS hunger and PSA food prices determine the risk"). The thesis defines this proxy explicitly, so it is the target the objectives are evaluated against.
- **Every report states its limits.**
  - The hunger part is a regional (Balance Luzon) experience-based measure, consistent with FNRI FIES in direction.
  - The price part is an affordability pressure. It moved *against* measured hunger in 2021-26 (ρ = −0.38).
  - It cannot support provincial or municipal food-insecurity levels.
- **Alternative examined: regional SWS hunger alone.** It is a direct measure, but it gives one row per quarter for all provinces. At Lead 2 it scores 0.846 on 13 quarters, cannot meet R1 (≥ 40 rows), and does not beat the newest reading.
- **Not mixed:** no result from one target is compared with another as if equivalent.

## 3. The seven missed HIGH cases at Lead 2 (final model P0H4-U; `out/missed_high_lead2.csv`)

**Column guide**
- π_H = hunger-part probability; π_P = price-part probability; P = π_H × π_P.
- Projected / realised = the price margin in points: projected at the issue date, and as it actually turned out.
- N1 is the only missing input in every case.
- None of the seven was caught by the validation threshold (C0-T) or by C1, C2 or C4.

| Province | Origin → target | Issue date | SWS reading used | π_H | π_P | P | Projected / realised price margin | Cause |
|---|---|---|---|---|---|---|---|---|
| Laguna | 2023-Q2 → 2023-Q4 | 2023-08-03 | 2023-Q2 = 11.3 | 0.50 | 0.49 | 0.25 | −0.9 / +0.9 | **Hunger reading tied at 11.3**, so P ≤ 0.5 × π_P. The surge to 14.3 was published 2024-01-22, after the issue. |
| Quezon | 2023-Q2 → 2023-Q4 | 2023-08-03 | 11.3 | 0.50 | 0.49 | 0.25 | −0.9 / +0.2 | Same cause; borderline label |
| Batangas | 2023-Q2 → 2023-Q4 | 2023-08-03 | 11.3 | 0.50 | 0.49 | 0.25 | −1.5 / +0.1 | Same cause; borderline label |
| Quezon | 2024-Q1 → 2024-Q3 | 2024-05-01 | 2024-Q1 = 15.3 | 0.82 | 0.43 | 0.35 | **+0.6** / +3.4 | **Model behaviour:** the projection was above threshold, but the poverty (V1, a static province profile) and hunger-indicator inputs pulled π_P down. Only Platt calibration (C5, rejected overall) caught it. |
| Cavite | 2024-Q2 → 2024-Q4 | 2024-07-24 | 2024-Q2 = 19.6 | 0.97 | 0.17 | 0.16 | −2.1 / +0.7 | **Price rise after the issue date;** no input anticipated it |
| Laguna | 2024-Q2 → 2024-Q4 | 2024-07-24 | 19.6 | 0.97 | 0.17 | 0.17 | −1.8 / +0.3 | Same; borderline label |
| Cavite | 2025-Q4 → 2026-Q2 | 2026-01-15 | 2025-Q4 = 16.7 | 0.81 | 0.35 | 0.28 | −1.0 / +0.0 | Same; borderline label (realised margin 0.02) |

**Summary of causes**

| Cause | Cases |
|---|---|
| Target construction / SWS timing (hunger tie at 11.3) | 3 |
| Insufficient predictive signal (price rose after the issue) | 3 |
| Model behaviour | 1 |
| Borderline labels (margin < 0.5 point, overlapping the above) | 4 |
| Wrong horizon | 0 |
| Missing data | 0, apart from N1, which the model does not use |

**Preventable without future information?** Not by any change tested:
- The validation-selected threshold caught **none** of the seven and added 12 false alarms.
- The only candidate that caught one case (C5) lowered Lead-2 accuracy to 0.677.

## 4. Experiments: original vs improved methodology

Lead-2 rows are 65 province-quarters over 13 quarters. Each experiment was frozen before scoring.

| Experiment | Rationale | Lead-2 accuracy | HIGH recall | Brier | Result |
|---|---|---|---|---|---|
| **Original served P0H4** (quarter-start issue) | — | 0.769 | 0.35 (6/17) | 0.194 | fails R3, R5, R6 |
| **SWS-update re-issue → P0H4-U** (FORECAST_RESEARCH) | The newest hunger reading is two quarters old at the quarter start | **0.800** | **0.59 (10/17)** | **0.167** | fails **R6 only**. Kept as the best version. |
| Structural price arms J0-J3, CMB, LJ (FR-II) | Model price trend and reversal | 0.754-0.800 | 0.35-0.65 | 0.175-0.190 | no development gain over the flat projection |
| C1: regional XLM-R news index | Fix 79% news missingness | 0.800 | 0.59 | 0.167 | identical (never used) |
| C2: risk history and transitions | Represent changes between quarters | 0.800 | 0.59 | 0.178 | worse |
| C4: forced class balancing | Class imbalance | 0.800 | 0.59 | 0.169 | worse |
| C5: Platt calibration (validation folds) | Calibration | 0.677 | 0.35 | 0.201 | much worse |
| **C0-T: validation-selected threshold** (Addendum 2) | Product rule caps P | 0.615 | 0.59 | 0.167 | worse: false alarms 6 → 18; Lead 1 loses R6. **Not adopted.** |

## 5. Fixed acceptance criteria (verified against the approved protocol) and results

**What the approved rule actually requires (R1-R7):**
- R1: ≥ 10 quarters and ≥ 40 rows;
- R2: accuracy **≥ 0.75**;
- R3: balanced accuracy ≥ 0.70;
- R4: better than always-LOW and persistence;
- R5: Brier significantly better than persistence and climatology (one-sided p < .10);
- R6: HIGH precision **and recall ≥ 0.60**;
- R7: stable across thirds and leave-one-quarter-out.

**80% accuracy is the stated goal, not a pass criterion.**

### Final model P0H4-U by horizon

| Lead (meaning) | Rows / quarters | Accuracy [90% CI] | Balanced | HIGH precision / recall / F1 | Confusion (TP FP FN TN) | Brier | Always-LOW | Pass |
|---|---|---|---|---|---|---|---|---|
| 1 (current quarter) | 70 / 14 | **0.843** [0.76, 0.91] | 0.776 | 0.69 / 0.65 / 0.67 | 11 5 6 48 | 0.132 | 0.757 | **Yes** (R1-R7) |
| **2 (next quarter)** | 65 / 13 | **0.800** [0.71, 0.89] | 0.732 | 0.62 / **0.59** / 0.61 | 10 6 7 42 | 0.167 | 0.738 | **No: fails R6** (recall 0.59 < 0.60) |
| 3 | 60 / 12 | 0.633 | 0.549 | 0.35 / 0.35 / 0.35 | 6 11 11 32 | 0.218 | 0.717 | No (6 criteria) |
| 4 | 55 / 11 | 0.673 | 0.584 | 0.46 / 0.35 / 0.40 | 6 7 11 31 | 0.246 | 0.691 | No (6 criteria) |

**Lead-2 baselines (Brier, one-sided p):**
- persistence: P0H4-U better, p = .029;
- climatology: P0H4-U better, p = .078.

**Uncertainty**
- The 90% accuracy interval at Lead 2 (0.71-0.89) spans both the 0.75 bar and the 0.80 goal.
- Recall rests on 17 HIGH cases in 7 quarters: one case moves it by 0.06.

**Maximum reliable horizon: Lead 1 (the current quarter).** Lead 2 meets the 80% goal and every criterion except R6. It is **promising development evidence, not a validated forecast.**

## 6. Five triggers (Market/Prices, Climate, Employment, Fish production, OFW remittances)

All five are in the unified LightGBM: their columns change predictions when removed, and none is constant, duplicated or misaligned. The table shows the change in Lead-2 Brier when a group is removed (90% CI); **positive means the group helped.**

| Trigger | Lead 2 | Other leads | Reading | Data needed to do better |
|---|---|---|---|---|
| Market / Prices | **+0.037** [+0.009, +0.063] | Lead 1 +0.052 | Carries the forecast | Official forward price outlooks (BSP, DA) |
| Climate | −0.005 [−0.010, −0.001] | — | Adds noise at Lead 2; realised typhoons and harvests arrive in the target quarter | Seasonal climate forecasts issued before the quarter; provincial production outlooks |
| Employment | +0.003 (n.s.) | Lead 1 +0.005 | National series that follows the calendar | Provincial or regional LFS estimates |
| Fish production | ≈ 0 | Lead 3 +0.006 | Small, late effect | Monthly provincial fisheries data; BFAR fish-kill records |
| OFW remittances | ≈ 0 | — | National series, barely used | Regional remittance or household-income data |
| **All five removed** | **+0.046** [+0.012, +0.081] | — | The triggers collectively help, mainly through Market | — |

Correlated inputs share importance, so SHAP shares (Market 0.62) are shown as model influence only. The removal test is the evidence. The dashboard cards state each group's tested result, and no direction is stated where none was shown.

## 7. Data coverage and the latest usable quarter

| Item | Status for the 2026-10-01 issue |
|---|---|
| Latest complete observation quarter | **2026-Q3** |
| PSA CPI known at Lead-1 issue (1 Oct) | through **August 2026** |
| SWS reading known at Lead-1 issue | **2026-Q2** (17.3) |
| SWS reading at the Lead-2 re-issue (15 Oct) | **2026-Q3** (23.6, published 14 Oct) |
| 2026-Q4 | Not observed. It is the Lead-1 forecast quarter. |
| SWS completeness | 20 of 23 quarters, 2021-Q1..2026-Q3. No regular Balance Luzon round in 2021-Q1, 2022-Q1 or 2025-Q1. |
| SWS updates | Entered by hand; no automatic fetch |
| News (XLM-R) | Headlines for 9 of 22 quarters; N1 missing in 79% of rows |
| Other indicators | Complete in the evaluation rows. A3 rice is 8% missing. E2 is present to 2026-Q3. |

## 8. Thesis-ready methodology

1. **Data collection and preprocessing.**
   - Sources (2021-2026; a value is used only after its publication date):
     - PSA monthly provincial CPI;
     - PSA rice prices, palay/corn and fisheries production, and Labor Force Survey;
     - PSA 2021 poverty estimates and the 2024 census;
     - BSP OFW remittances;
     - PAGASA ENSO alerts; IBTrACS typhoon tracks;
     - World Bank world food and fertilizer prices;
     - news headlines scored by XLM-RoBERTa, and GDELT news counts;
     - SWS involuntary hunger (Balance Luzon).
   - Missing values stay blank, never zero.
2. **Food-insecurity target (Chapter I).** A province is HIGH in a quarter when SWS Balance Luzon hunger is above 11.3% AND its food inflation, or food minus headline inflation, exceeds its 2021-22 60th percentile.
3. **The 12 indicators.**
   - The food CPI is projected to the target quarter by holding the latest index flat.
   - The other indicators enter as their latest published change or level.
   - They are grouped into the five proposal triggers (Market/Prices, Climate, Employment, Fish production, OFW remittances), plus news, poverty and the regional hunger outlook.
4. **Unified LightGBM.**
   - One LightGBM is trained on the rows of every forecast horizon together.
   - It estimates the chance that the price condition holds.
   - At each quarterly issue date it is refitted on earlier rows whose outcomes were known, with settings chosen on earlier origins only.
5. **Forecasting.**
   - Risk probability = P(hunger condition) × P(price condition). The hunger part comes from the newest SWS reading and its past movements.
   - Lead 1 (the current quarter) is issued on the quarter's first day.
   - Lead 2 (the next quarter) and longer leads are re-issued after each SWS release.
6. **Maximum reliable horizon.** The longest lead that, together with every shorter lead, passes R1-R7 on rolling-origin (walk-forward) forecasts.
7. **Explanations.** SHAP values of the price model are grouped into the five triggers and shown as relative influence. Each trigger's contribution is tested by removing it and refitting.
8. **Evaluation.** Accuracy, balanced accuracy, HIGH precision, recall and F1, confusion matrices, the Brier score and calibration. Comparison with always-LOW, persistence and climatology, using quarter-block bootstrap intervals.

## 9. Thesis-ready results

- **Lead 1 (current quarter):** passed every reliability criterion. Accuracy 0.843 on 70 province-quarters, HIGH recall 0.65, Brier 0.132, better than persistence and climatology.
- **Lead 2 (next quarter):** reached accuracy 0.800 and Brier 0.167, better than persistence (p = .03).
  - It fell short of the HIGH-recall criterion: 10 of 17 HIGH cases, 0.59 against 0.60.
  - The seven misses were:
    - three quarters where the latest hunger survey sat exactly at the threshold before a surge published after the forecast;
    - three price rises that began after the forecast date;
    - one case where the model under-weighted an above-threshold price projection.
  - A validation-selected decision threshold, news-coverage repair, transition features, class balancing and calibration did not reduce these misses.
- **Leads 3-4:** not reliable.
- **Triggers:** the five together improved forecasts, mainly through Market/Prices. Climate, Employment, Fish production and OFW remittances showed small or no measurable contributions with the available national and quarterly data.
- **Status of all results:** development evidence on 2021-2026 data. Forecasts sealed in October 2026 provide the first independent test from January 2027.

## 10. Remaining limitations and data required

- **A province- or municipality-level food-insecurity outcome**, repeated over time: CBMS 2024 FIES aggregates and FNRI provincial FIES (requests drafted, not sent).
- **More quarters.** Prospective scoring of the sealed forecasts, one quarter at a time.
- **Earlier hunger information** than the SWS release, and forward-looking price outlooks.
- **Provincial (rather than national)** employment, remittance and climate-impact data.
- **The validator-only question** (CPI and SWS as inputs) remains for the adviser.

## Implementation changes in this phase

| File | Change |
|---|---|
| `frontend/src/components/MapDashboard.tsx` | The map opens on the backend's default quarter (Lead 1, Q4 2026). This is a logic change only. Frontend 83/83. |
| `backend/data/ch1_trigger_evidence.json`, `ch1_system.plain_evidence` | The trigger cards state each group's tested contribution |
| Production model | **Unchanged** (P0H4, seal a498b5ef). P0H4-U stays behind `AIPHEED_CH1_ENGINE=fr` until you approve it. |
