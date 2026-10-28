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

---

## 11. Improvement round (LEAD2_IMPROVE; protocol committed in a7455aa before scoring)

### Experiments

**B0** is the reference: P0H4-U. B1-B4 are each the same unified LightGBM with all 12 indicator families, plus the change listed.

| ID | Defect addressed | Code / feature change | Rationale |
|---|---|---|---|
| B1 | 3 of 7 misses are price rises after the issue; the flat projection's bias depends on the regime | `features_v2.py`: `A1_food_anc` and `A1_gap_anc`, projections with the index grown at the BSP 3% target midpoint (monotone) | This projection cut the Lead-2 food-inflation RMSE from 2.37 to 1.93 in FR-II |
| B2 | Training spans different inflation regimes | `improve.py`: recency weights 0.5^(age/HL), with HL ∈ {none, 8, 4} chosen on inner folds | Follow the current regime |
| B3 | B1 + B2 | both | — |
| B4 | The four non-market triggers enter as levels only | `dC3`, `dC4`, `dE1`, `dE2`, `C2_2q`, `C1_run` (changes, 2-quarter typhoons, El Niño duration) | Delayed or changing effects of climate, employment, fish production and remittances |

### Before and after

Same 65 Lead-2 / 70 Lead-1 rows, the same target and the same S-AB hunger term. "+hits / +FA" counts the extra HIGH cases caught and the extra false alarms compared with B0. **CONF** = targets 2025-Q2 to 2026-Q3, held out from this selection.

| Model | Lead-1 accuracy | Lead-1 Brier (Δ vs B0, 90% CI) | Lead-2 accuracy | Lead-2 HIGH precision / recall | Lead-2 TP FP FN TN | Lead-2 Brier (Δ vs B0) | +hits / +FA | Lead-2 CONF accuracy | Lead-2 fails |
|---|---|---|---|---|---|---|---|---|---|
| **B0 = P0H4-U** | 0.843 | 0.132 | **0.800** | 0.62 / **0.59** | 10 6 7 42 | **0.167** | — | 0.833 | R6 |
| **B1 anchored projections** | **0.886** | **0.122 (−0.011 [−0.021, −0.001])** | 0.785 | 0.60 / 0.53 | 9 6 8 42 | 0.168 (+0.000, n.s.) | 0 / +1 | 0.833 | R6 |
| B2 recency weighting | 0.786 | 0.141 | 0.723 | 0.47 / 0.53 | 9 10 8 38 | 0.193 (**+0.026**, worse) | 0 / +4 | 0.700 | R2-R6 |
| B3 = B1 + B2 | 0.871 | 0.132 | 0.754 | 0.53 / 0.53 | 9 8 8 40 | 0.187 (+0.020) | 0 / +2 | 0.767 | R3, R5, R6 |
| B4 trigger dynamics | 0.843 | 0.133 | 0.785 | 0.59 / 0.59 | 10 7 7 41 | 0.169 (+0.002) | 0 / +1 | 0.833 | R6 |

**Selection (frozen rule: Lead-2 DEV Brier ≥ 0.005 better):** none qualifies, so **B0 stays**. None of B1-B4 caught any of the 7 earlier misses.

**B1 is a genuine Lead-1 improvement.**
- The Brier gain is significant, and accuracy improves in both blocks: DEV 0.825 → 0.875, CONF 0.867 → 0.900.
- At Lead 2 it is not significantly different from B0 (one fewer hit).
- It was not adopted, because the pre-set rule targeted Lead 2. Adopting it is the researchers' decision: it is one unified model, so adopting it changes all leads.

### All Lead-2 errors of B0 (13), by pattern (`out/error_patterns.csv`)

| Pattern | Misses (FN) | False alarms (FP) |
|---|---|---|
| Hunger part ≤ 0.5 (SWS reading tied at 11.3) | 3 | — |
| Price rose after the issue date | 3 | — |
| Price fell after the issue date | — | 5 |
| Model behaviour | 1 | 1 |

- **Price surprises in both directions** account for 8 of the 13 errors.
- **6 of the 13 errors are borderline labels** (|realised margin| < 0.5 point).
- The same pattern runs through every quarter with errors, so it is not specific to the seven misses.

### Early-warning check for the 7 misses

Each check lists the indicators beyond the 75th percentile, at the cut-off, in the direction training HIGH rows took.
- **World prices:** cereal, crude oil and urea were high before 6 of the 7 misses.
- **The same indicators were also high before many LOW quarters in 2022-23**, when hunger stayed below 11.3. They are in the model, but they do not separate HIGH from LOW. That is why the LightGBM does not lean on them.
- For Quezon 2024-Q3, both projections were already above threshold (A1_gap 76th percentile, anchored projection 87th), yet the model gave 0.43. This is the one case of model under-use. The poverty input (a static province profile) pulled it down.

### Pass/fail of the final model (B0 = P0H4-U) against every frozen criterion

| Criterion | Lead 1 | Lead 2 |
|---|---|---|
| R1 ≥ 10 quarters, ≥ 40 rows | pass (14, 70) | pass (13, 65) |
| R2 accuracy ≥ 0.75 | pass (0.843) | pass (0.800) |
| R3 balanced accuracy ≥ 0.70 | pass (0.776) | pass (0.732) |
| R4 > always-LOW and > persistence | pass (vs 0.757 / 0.743) | pass (vs 0.738 / 0.723) |
| R5 Brier better than persistence and climatology (p < .10) | pass (.021 / .030) | pass (.029 / .078) |
| R6 HIGH precision and recall ≥ 0.60 | pass (0.69 / 0.65) | **FAIL (0.62 / 0.59)** |
| R7 thirds ≥ 0.60, leave-one-quarter-out ≥ 0.70 | pass | pass (0.65 lowest third; 0.783) |
| **Decision** | **Reliable (development evidence)** | **Not reliable: fails R6 by one HIGH case** |

**All 12 indicators reach the unified LightGBM** (input audit: 21/21 columns, exact reproduction).

**Five-trigger contribution:** see §6.
- Adding change and duration features (B4) did not help climate, employment, fish production or remittances. Their limit is the data (national, coincident, sparse), not the representation.
- Market's dominance is real. It carries the only signal that separates HIGH from LOW at Leads 1-2.

---

## 12. Round 3: target timing, borderline labels, poverty input (protocol v3, committed in bfa6b9b before scoring)

### 12.1 Is the target temporally consistent? (`out/target_timing.csv`)

For every Lead-2 target, the table records:
- the SWS fieldwork end and its 3-month recall window;
- the SWS publication date;
- the price months and their approximate release;
- the Lead-1 and Lead-2 issue dates;
- when the label became complete.

| Finding | Evidence | Decision |
|---|---|---|
| The SWS recall window overlaps the price quarter by **90% on average** (lowest: 2025-Q2 64%, 2025-Q4 66%, 2023-Q4 78%) | fieldwork-end dates | Hunger and price refer to largely the same period |
| A recall-aligned price label (the price months set to the SWS recall months) | — | It would flip 4 of 65 Lead-2 labels and fix 1 of 13 errors. **No target correction is justified.** |
| Every training label is used only after both its SWS round and its last CPI month were published | label-complete dates vs origins (input audit) | No leakage |

### 12.2 Borderline errors

- 6 of the 13 Lead-2 errors had a realised price margin within 0.5 point. Two are within CPI rounding (≤ 0.1 point), so they are effectively coin-flip labels: Cavite 2025-Q2 (−0.07) and Cavite 2026-Q2 (+0.02).
- No error label is in doubt on the hunger side: every error quarter's hunger reading is more than 1.5 standard errors from 11.3.
- The threshold is frozen and was not changed.

### 12.3 How informative is the Lead-2 evaluation?

| Metric | Point estimate | 95% Clopper-Pearson | 90% quarter-block bootstrap |
|---|---|---|---|
| HIGH recall | 10/17 = 0.59 | 0.33 - 0.82 | 0.25 - 0.86 |
| HIGH precision | 10/16 = 0.63 | 0.35 - 0.85 | 0.42 - 0.75 |

- The chance that the true recall is at least 0.60 is **0.49**: the R6 failure is statistically a coin flip.
- 17 HIGH cases fall in only 7 of 13 quarters. The provinces share one regional hunger reading, so the independent evidence is about 7 quarters.
- **No longer valid evaluation exists.** Origins before 2022-Q4 lack the training history the frozen rule requires, and pre-2021 data are outside the study window.

### 12.4 Poverty input (V1)

| Check | Finding |
|---|---|
| Source and year | PSA small-area poverty estimates 2021 (142 LGUs), POPCEN 2024 population, land area |
| Construction | 0.6 × min-max(**unweighted** mean of LGU poverty rates) + 0.4 × min-max(density) |
| Problem 1 | **Two opposite gradients mixed:** Cavite (densest) V1 0.590 ≈ Quezon (poorest) 0.600 |
| Problem 2 | Unweighted LGU mean, not a provincial rate. Population-weighted: Quezon 19.7, Cavite 9.9, Batangas 8.8, Rizal 7.1, Laguna 6.0 |
| Availability | Static profile; POPCEN 2024 published 2025 (disclosed FIRI Amendment 1 deviation) |
| Municipal substitutes | LGU ranking only; one Quezon LGU (Lucena) has no own estimate |
| Quezon 2024-Q3 | V1 pushed the price probability down (SHAP −0.72) |

**Correction tested** (pre-registered). D1 replaces V1 with population-weighted poverty (monotone increasing) plus density. D2 is the same without the constraint.

| | B0 (P0H4-U) | D1 | D2 |
|---|---|---|---|
| Lead 1: accuracy, recall, Brier | 0.843, 0.65, 0.132 | 0.814, **0.53**, 0.133 | 0.814, 0.53, 0.131 |
| Lead 2: accuracy, precision / recall, Brier | 0.800, 0.62 / 0.59, 0.167 | 0.769, 0.56 / 0.59, **0.181** (+0.014, CI excludes 0) | 0.785, 0.59 / 0.59, 0.176 |
| Quezon 2024-Q3, Lead-2 probability | 0.355 | 0.330 | 0.328 |
| Criteria lost vs B0 | — | Lead-1 R6, Lead-2 R5 | Lead-1 R6, Lead-2 R5 |

**Not adopted.**
- With poverty forced to raise risk, Quezon 2024-Q3 is still missed. The old V1 was not the sole cause.
- The composite V1 helps the model as a **province profile**: it absorbs province-specific differences in how often the price thresholds are crossed. That is predictive, but it is not a poverty effect.
- The dashboard therefore keeps calling its influence "relative model influence", and no causal reading is given.

### 12.5 Final seven-criteria table: every model tested, before (B0) and after

| Model (reason for change) | Lead | R1 | R2 accuracy | R3 balanced | R4 | R5 | R6 precision / recall | R7 | Passes |
|---|---|---|---|---|---|---|---|---|---|
| Served P0H4 (original) | 2 | ✓ | ✓ 0.769 | ✗ 0.635 | ✓ | ✗ | ✗ 0.60 / 0.35 | ✓ | No |
| **P0H4-U (SWS-update re-issue) = FINAL** | 1 | ✓ | ✓ 0.843 | ✓ 0.776 | ✓ | ✓ | ✓ 0.69 / 0.65 | ✓ | **Yes** |
| **P0H4-U = FINAL** | 2 | ✓ | ✓ 0.800 | ✓ 0.732 | ✓ | ✓ | **✗ 0.62 / 0.59** | ✓ | **No (R6, one case)** |
| B1 anchored projections | 2 | ✓ | ✓ 0.785 | ✓ 0.702 | ✓ | ✓ | ✗ 0.60 / 0.53 | ✓ | No |
| B4 trigger dynamics | 2 | ✓ | ✓ 0.785 | ✓ 0.721 | ✓ | ✓ | ✗ 0.59 / 0.59 | ✓ | No |
| C0-T validation threshold | 2 | ✓ | ✗ 0.615 | ✗ 0.607 | ✗ | ✓ | ✗ 0.36 / 0.59 | ✗ | No |
| D1 poverty correction | 2 | ✓ | ✓ 0.769 | ✓ 0.711 | ✓ | ✗ | ✗ 0.56 / 0.59 | ✓ | No |

**Final decision.**
- **Retain P0H4-U as the research candidate.** P0H4 stays the served default until it is reviewed.
- **Lead 1:** reliable (development evidence).
- **Lead 2:** meets 6 of 7 criteria and the 80% accuracy goal. It fails R6 by one HIGH case, and the evaluation cannot tell whether the true recall is above or below 0.60 (P = 0.49).
- **Lead 2 is reported as promising, not validated.** The sealed forecasts, scored from January 2027, are the next real evidence.

---

## 13. Final round: limits of the data and one new early-warning signal (LEAD2_FINAL; protocol committed in 6febd22 before scoring)

### 13.1 What the available indicators can and cannot anticipate (`runner/limits.py`, `out/limits.json`)

| Check, Lead 2, P0H4-U | Result |
|---|---|
| Perfect price knowledge × model hunger term | accuracy 0.938, recall 1.00 |
| Perfect hunger knowledge × model price term | accuracy 0.677, recall 0.59 |
| Price-term AUC on the 55 rows where hunger is HIGH (price decides the label) | model 0.731; flat projection 0.741 |
| Same at Lead 1 | model 0.743; flat projection **0.949** |

- At Lead 2 the LightGBM already uses the aggregate price information about as well as it can be used. **The limit is the information, not the model.**
- At Lead 1 the model under-uses the projection. This matches B1's Lead-1 gain (§11). Lead 1 already passes, so it is not pursued here.

**The 13 Lead-2 errors, one primary category each** (`out/limits_errors.csv`; the analog vote is the 10 nearest training rows whose outcome was known at the origin):

| Category | Cases | Recoverable? |
|---|---|---|
| Sudden: hunger information absent at the cut-off (SWS tied at 11.3, surge published later) | 3 FN (2023-Q4) | No |
| Uncertain label (realised margin within ±0.10, CPI rounding) | 1 FN, 1 FP (Cavite 2026-Q2, 2025-Q2) | No, not honestly |
| Model behaviour (projection on the realised side) | 1 FN, 1 FP (2024-Q3) | Possibly |
| Price surprise the analogs voted for (indicators could plausibly anticipate it) | 2 FN (2024-Q4), 1 FP | Possibly |
| Price surprise the analogs voted against (sudden) | 3 FP | No |

**The only realistic opportunity is the price part:** 5 errors, all about whether current price pressure persists or reverts. The R6 ceiling is 13/17 = 0.76 even if every recoverable miss were fixed. R6 needs 11/17, i.e. one more hit.

### 13.2 Candidate signal (documented in the protocol before scoring)

| Item | |
|---|---|
| Signal | **Composition and breadth of food inflation at the cut-off.** `K_core`: non-fresh food y/y minus the province threshold. `K_fresh_gap`: fresh minus non-fresh y/y. `K_diff`: weight share of the 8 subgroups accelerating. |
| Theory | Fresh-food shocks (fish, fruits, vegetables) reverse with the next harvest or catch; storable and processed food pressure persists ("core excluding fresh food"). Broad acceleration (a diffusion index) signals pressure that continues. |
| Data | PSA OpenStat 0012M4ACP22 provincial CPI by subgroup, 2021-01..2026-09, complete. Its food index equals the model's food CPI exactly. |
| Availability | The same PSA release as the food CPI. Each row reads only months ≤ its cut-off month; this is asserted in code and tested. |
| Coverage | From origin 2022-Q2; 100% of evaluation origins |
| Why new | Every earlier price feature used the aggregate index. E84 S-COMP used subgroups only to simulate prices forward, outside the LightGBM. |
| Leakage control | One candidate, monotone directions fixed in advance, the same origins, rows, grid, seed and S-AB hunger term; nothing fitted on evaluation outcomes |

### 13.3 Before and after (identical rows; B0 reproduces P0H4-U to 5e-7)

| | B0 = P0H4-U, Lead 1 | K1, Lead 1 | **B0 = P0H4-U, Lead 2** | **K1, Lead 2** |
|---|---|---|---|---|
| Accuracy [90% CI] | 0.843 [0.76, 0.91] | 0.843 [0.74, 0.93] | **0.800** [0.71, 0.89] | **0.800** [0.69, 0.89] |
| Balanced accuracy | 0.776 | 0.756 | 0.732 | 0.732 |
| HIGH precision / recall | 0.69 / 0.65 | 0.71 / **0.59** | 0.63 / 0.59 | 0.63 / 0.59 |
| TP FP FN TN | 11 5 6 48 | 10 4 7 49 | 10 6 7 42 | 10 6 7 42 |
| False alarms / missed HIGH | 5 / 6 | 4 / 7 | 6 / 7 | 6 / 7 |
| Brier (Δ vs B0, 90% CI, p) | 0.132 | 0.130 (−0.002 [−0.013, +0.006], p .41) | 0.167 | **0.160 (−0.007 [−0.014, −0.000], p .049)** |
| DEV Brier / DEV balanced | 0.139 / 0.710 | 0.145 / 0.710 | 0.177 / 0.686 | 0.171 / 0.665 |
| CONF accuracy | 0.867 | 0.867 | 0.833 | 0.867 |
| Accuracy by thirds; LOQO min | 0.88, 0.76, 0.90; 0.831 | 0.88, 0.72, 0.95; 0.831 | 0.84, 0.65, 0.90; 0.783 | 0.84, **0.60**, 0.95; 0.783 |
| Price-term accuracy / Brier | 0.614 / 0.223 | 0.643 / 0.216 | 0.600 / 0.227 | **0.692 / 0.212** |
| Brier vs persistence / climatology (p) | .021 / .030 | .015 / .022 | .029 / .078 | .024 / .045 |
| Failed criteria | none | **R6** | R6 | R6 |

**Lead-2 errors.** K1 fixes 2 false alarms (Laguna 2024-Q3, Quezon 2026-Q3) and makes 2 new ones (Batangas 2024-Q3, 2024-Q4). It catches none of the 7 misses: Quezon 2024-Q3 0.355 → 0.370, Cavite 2024-Q4 0.161 → 0.209, Laguna 2024-Q4 0.167 → 0.250.

**Mechanism (training rows at the final origin).**
- Among the 122 rows whose flat projection was already above threshold, K_core separates pressure that held from pressure that reverted: standardised difference **0.64**, close to A1_food's 0.70; K_diff 0.33.
- Overall, K_core and K_diff are not inflated in both classes (0.10 and 0.15). The signal is real and works as theory predicts.
- Its effect is mostly to sharpen probabilities (Brier) rather than move cases across 0.5. Lead-2 SHAP share: K_diff 0.094, K_core 0.017, K_fresh_gap 0.014.

### 13.4 Frozen adoption rule

| Condition | Result |
|---|---|
| Lead-2 DEV Brier ≥ 0.005 better | pass (0.177 → 0.171) |
| Lead-1 DEV Brier not > +0.005 | **fail** (+0.0057) |
| Lead-2 DEV balanced accuracy not lower | **fail** (0.686 → 0.665) |
| Lead-2 accuracy, balanced accuracy, precision, recall within 0.02 | pass |
| New false alarms ≤ new hits | **fail** (2 vs 0) |
| Lead-2 CONF accuracy not lower | pass |
| Lead 1 still passes R1-R7 | **fail** (R6: recall 0.59) |

**K1 is not adopted. P0H4-U is retained.**
- K1's Lead-2 Brier gain is the first statistically supported Lead-2 probability improvement in this series (p = .049).
- It does not change a single Lead-2 HIGH/LOW call, does not catch a missed HIGH case, and costs Lead 1 one HIGH case.

### 13.5 Final status

| Criterion | Lead 1 (P0H4-U) | Lead 2 (P0H4-U) |
|---|---|---|
| R1 | pass | pass |
| R2 | pass 0.843 | pass 0.800 |
| R3 | pass 0.776 | pass 0.732 |
| R4 | pass | pass |
| R5 | pass (.021 / .030) | pass (.029 / .078) |
| R6 | pass 0.69 / 0.65 | **fail 0.63 / 0.59** |
| R7 | pass | pass |
| **Decision** | **reliable (development evidence)** | **not reliable** |

**Maximum reliable horizon: Lead 1.**

**Why Lead 2 cannot be validated from the available data.**
- The approved data now have no untested, theoretically motivated signal left that addresses the recoverable errors. Composition and breadth were the last price-side information not yet used, and they improve probabilities without moving the decisive cases.
- The non-recoverable misses (3 hunger ties, 1 rounding-level label) already cap recall at 13/17.

**What validating Lead 2 would need**
- **More independent quarters.** With about 1.3 HIGH cases per quarter, keeping the lower end of a 90% interval for recall above 0.60 needs about 57 HIGH cases if the true recall is about 0.70 (normal approximation). That is about 44 quarters; the sealed prospective forecasts (from 2027-Q1) are the start.
- **A hunger observation between SWS rounds**, or closer to the target quarter, for Balance Luzon or CALABARZON (DSWD/WFP monitoring, OCTA rounds), to resolve threshold ties such as 2023-Q4.
- **A provincial food-insecurity outcome** (CBMS 2024 FIES, FNRI provincial FIES) to validate the target beyond the regional proxy.
- **Forward-looking price information** issued before the quarter (DA/BSP price outlooks, rice import and tariff schedules) for the price rises that began after the issue date.

**Implementation.** No served artifact changed: P0H4 seal a498b5ef; P0H4-U behind `AIPHEED_CH1_ENGINE=fr`. New files:
- `runner/limits.py`, `runner/features_v4.py`, `runner/final.py`;
- `data/stack_v4.csv`;
- `out/limits.json`, `out/limits_errors.csv`, `out/features_v4_audit.json`, `out/final.json`, `out/final_rows.csv`;
- `backend/tests/integration/test_lead2_final.py` (6 tests).

---

## 14. Subgroup signals and the missed HIGH cases (LEAD2_SUBGROUP; protocol committed in 6bc46e3 before scoring)

### 14.1 Probabilities of every Lead-2 HIGH case and false alarm (`out/subgroup_cases.csv`)

| Group | Cases | B0 → K1 probability | Rank among LOW rows, B0 → K1 |
|---|---|---|---|
| Hits | 10 | 0.52-0.70 → 0.52-0.70 | 0.95 → 0.94 |
| **Missed HIGH** | 7 | 0.16-0.36 → 0.21-0.37 | **0.49 → 0.59** |
| False alarms | 6 (B0) / 6 (K1) | 0.52-0.70 | — |

The 7 misses, B0 → K1:
- Laguna 2023-Q4: 0.247 → 0.237
- Quezon 2023-Q4: 0.247 → 0.309
- Batangas 2023-Q4: 0.247 → 0.309
- Quezon 2024-Q3: 0.355 → 0.370
- Cavite 2024-Q4: 0.161 → 0.209
- Laguna 2024-Q4: 0.167 → 0.250
- Cavite 2026-Q2: 0.278 → 0.262

### 14.2 Findings

| Question | Answer |
|---|---|
| Do the subgroup features improve the ordering even where the calls do not change? | **Yes, modestly.** Lead-2 T43c AUC 0.760 → 0.797; price AUC on hunger-HIGH rows 0.731 → 0.753. Five of the 7 misses rise; Laguna 2023-Q4 and Cavite 2026-Q2 fall slightly. |
| Can the better ordering be turned into hits by a threshold or calibration? | **No.** 15 LOW rows still score above the best miss (0.370). Recall ≥ 0.60 needs a cut ≤ 0.309, where precision is 0.39 (TP 11, FP 17). Any threshold or monotone calibration keeps the order, so none can meet R6, however chronologically it is selected. |
| Independent information, or duplicates? | K_core and K_fresh_gap are **mostly duplicates**: R² 0.79 and 0.74 on the 12 aggregate price columns. **K_diff (breadth) is mostly independent** (R² 0.34). The residual HIGH-LOW separation of all three is small (0.27, −0.23, 0.24). |
| Did a missed case have a strong early warning that the model ignored? | **No.** The subgroup-space analog vote flags all 7 misses (0.7-1.0), but it is almost as high on LOW rows (0.66 vs 0.76) and separates the price condition worse than the model (AUC 0.64 vs 0.75). At the 2023-Q4 origins only 5-30 training rows had subgroup values. |
| Structural cap | 3 of the 7 misses (2023-Q4) have π_H = 0.50, so P < 0.50 whatever the price term |

### 14.3 The one candidate supported by the findings

**K2 = P0H4-U + K_diff only.**

**Hypothesis:** the breadth signal carries K1's gain, and the redundant columns caused its regressions.

| | B0 = P0H4-U | K1 | K2 |
|---|---|---|---|
| Lead-1 accuracy / balanced | 0.843 / 0.776 | 0.843 / 0.756 | 0.829 / 0.747 |
| Lead-1 precision / recall | 0.69 / 0.65 | 0.71 / 0.59 | 0.67 / 0.59 |
| Lead-1 Brier (Δ vs B0) | 0.132 | 0.130 (−0.002, n.s.) | 0.139 (**+0.007**, CI [+0.002, +0.013]) |
| **Lead-2 accuracy [90% CI]** | **0.800** [0.71, 0.89] | 0.800 [0.69, 0.89] | 0.769 [0.66, 0.88] |
| Lead-2 balanced | 0.732 | 0.732 | 0.673 |
| Lead-2 precision / recall | 0.63 / 0.59 | 0.63 / 0.59 | 0.57 / **0.47** |
| Lead-2 TP FP FN TN | 10 6 7 42 | 10 6 7 42 | 8 6 9 42 |
| Lead-2 false alarms / missed HIGH | 6 / 7 | 6 / 7 | 6 / 9 |
| Lead-2 Brier (Δ vs B0, p) | 0.167 | 0.160 (−0.007, p .049) | 0.166 (−0.001, p .41) |
| Lead-2 thirds; LOQO min | 0.84, 0.65, 0.90; 0.783 | 0.84, 0.60, 0.95; 0.783 | 0.76, 0.65, 0.90; 0.750 |
| Failed criteria, Lead 1 / Lead 2 | — / R6 | R6 / R6 | R6 / R3, R6 |

**Hypothesis refuted.**
- Without the redundant columns, K2 loses 2 Lead-2 hits (Cavite and Batangas 2024-Q2), and Lead-1 Brier is significantly worse.
- K1's gain therefore came from the columns acting together, not from breadth alone.

**Frozen adoption rule (unchanged):** 8 of 10 conditions fail (1b, 1c, all four "within 0.02" conditions, new false alarms, Lead-1 R1-R7). **K2 is not adopted.**

### 14.4 Conclusion

- **P0H4-U is retained.** Lead 1 is reliable (development evidence). **Lead 2 is not reliable: it fails R6 (0.63 / 0.59).**
- The PSA food-subgroup data hold a small amount of independent information: better ordering and a Brier gain in K1. It is not enough to lift any missed HIGH case above the LOW cases that outrank it, and no threshold or calibration can change that.
- **The subgroup line of work is closed, as the protocol required.** The requirements in §13.5 (more prospective quarters, inter-round hunger data, a provincial FIES outcome, forward price outlooks) are unchanged.

**Files:**
- `runner/subgroup_diag.py`, `runner/subgroup_k2.py`;
- `out/subgroup_diag.json`, `out/subgroup_cases.csv`, `out/subgroup_k2.json`, `out/subgroup_k2_rows.csv`;
- `runner/final.py`: scoring factored into `lead_eval` / `adoption_rule`; outputs byte-identical;
- tests in `backend/tests/integration/test_lead2_final.py`.

The served model is unchanged.

---

## 15. Why Lead 2 misses HIGH cases, and whether any new information exists (LEAD2_CAUSES; screen protocol committed in 603f5cd before running)

### 15.1 Case audit of all 13 Lead-2 errors at their cut-offs (`runner/case_audit.py`, `out/case_audit.csv`)

Only information published before each Lead-2 issue date is used.

**One primary cause per case, by fixed precedence:**
1. **H**: missing or delayed hunger observation.
2. **L**: uncertain label (realised price margin within ±0.10, or the target SWS reading within 1 SE of 11.3).
3. **R**: incorrect model ranking although the flat projection or the analog vote was on the realised side.
4. **V**: insufficient provincial variation (another province in the same quarter had the opposite label with province-varying inputs within 0.5 SD).
5. **P**: a price change that could not be anticipated.

| Province, target | Type | Cut-off (CPI to) | SWS used → next → target | Price margin now / projected / realised | π_H, π_P → P | Cause | Improvable then? |
|---|---|---|---|---|---|---|---|
| Batangas 2023-Q4 | missed | 2023-08-03 (May) | 11.3 → 10.3 (pub. 11-20) → 14.3 | +1.28 / −1.53 / +0.11 | 0.50, 0.50 → 0.25 | H | No |
| Laguna 2023-Q4 | missed | 2023-08-03 (May) | same | +2.26 / −0.87 / +0.86 | 0.50, 0.50 → 0.25 | H | No |
| Quezon 2023-Q4 | missed | 2023-08-03 (May) | same | −0.21 / −0.89 / +0.19 | 0.50, 0.50 → 0.25 | H | No |
| Quezon 2024-Q3 | missed | 2024-05-01 (Feb) | 15.3 → 19.6 → 18.1 | −1.54 / +0.58 / +3.36 | 0.82, 0.43 → 0.36 | R | Possibly |
| Cavite 2024-Q4 | missed | 2024-07-24 (May) | 19.6 → 18.1 → 25.3 | +0.46 / −2.12 / +0.69 | 0.97, 0.17 → 0.16 | R (analog 0.6) | Weakly |
| Laguna 2024-Q4 | missed | 2024-07-24 (May) | same | +0.06 / −1.81 / +0.29 | 0.97, 0.17 → 0.17 | R (analog 0.7) | Weakly |
| Cavite 2026-Q2 | missed | 2026-01-15 (Nov) | 16.7 → 22.4 → 17.3 | −1.11 / −1.04 / **+0.02** | 0.81, 0.34 → 0.28 | L | No |
| Rizal 2024-Q2 | false alarm | 2024-01-23 (Nov) | 14.3 → 15.3 → 19.6 | +0.07 / +1.39 / −1.25 | 0.76, 0.79 → 0.60 | P | No |
| Laguna 2024-Q3 | false alarm | 2024-05-01 (Feb) | 15.3 → 19.6 → 18.1 | −0.04 / −0.18 / −0.17 | 0.82, 0.64 → 0.53 | R | Possibly |
| Cavite 2025-Q2 | false alarm | 2025-01-15 (Nov) | 25.3 → 16.1 → 16.2 | −0.54 / +1.32 / **−0.07** | 0.99, 0.68 → 0.67 | L | No |
| Rizal 2025-Q2 | false alarm | 2025-01-15 (Nov) | same | −3.59 / +0.04 / −3.02 | 0.99, 0.53 → 0.52 | R (analog 0.2) | Possibly |
| Cavite 2025-Q3 | false alarm | 2025-06-01 (Feb) | 25.3 (no 2025-Q1 round) → 16.1 → 23.8 | +1.83 / +1.58 / −0.57 | 0.98, 0.71 → 0.70 | P | No |
| Quezon 2026-Q3 | false alarm | 2026-05-13 (Feb) | 22.4 → 17.3 → 23.6 | −0.67 / +1.97 / −1.41 | 0.96, 0.55 → 0.53 | P | No |

| Cause | Missed | False alarms | Realistic improvement at the time |
|---|---|---|---|
| Missing or delayed hunger observation | 3 | 0 | **None.** The reading at the cut-off was exactly 11.3, so P ≤ 0.5 × π_P. **Even the next SWS round (2023-Q3, published 2023-11-20) fell to 10.3.** The rise to 14.3 happened between 2023-Q3 and 2023-Q4, so no timelier hunger reading would have flagged it. |
| Uncertain target label | 1 | 1 | None. The realised margins are +0.02 and −0.07 points, within CPI rounding. |
| Price change that could not be anticipated | 0 | 3 | None in the data. The flat projection was above threshold, the analogs agreed, and prices fell after the cut-off. |
| Incorrect model ranking despite useful inputs | 3 | 2 | Possible in principle, but the supporting evidence is weak: analog votes of 0.6-0.7, an overall analog AUC of 0.64, and a model already about as good as the projection at Lead 2 (§13.1). Every targeted fix (B1, B4, C1-C5, D1/D2, K1, K2, validation threshold) left these cases on the same side. |
| Insufficient provincial variation | 0 | 0 | Not a primary cause in any case: no case had an opposite-label province with near-identical inputs. **Structurally**, though, 11 of the 21 inputs take one value across all five provinces at every origin: Employment (E1), OFW remittances (E2), El Niño (C1), the hunger outlook (H1), the two GDELT columns and the five world prices. Only the Market group, production (A2, C3), fish production (C4) and poverty (V1) vary by province. **7 of the 13 Lead-2 quarters have mixed labels**, and those national inputs cannot separate the provinces within them. |

### 15.2 New information: what exists, its coverage and timing

| Source (location) | Level | Coverage held | Release timing | In the Lead-2 model? | Finding |
|---|---|---|---|---|---|
| **NASA POWER rainfall anomaly** (`backend/data/processed/province_rainfall.parquet`) | Province (6 points each), but r = 0.95 across provinces | 1991-Q1..2026-Q2 (2021+ used) | Monthly, posted after month end; 2026-09 vintage | **Never** | Screened (§15.3): no link to the projection error |
| NASA POWER soil moisture / temperature (`province_agroclimate.parquet`) | Province, r = 0.94 | to **2025-Q4** | Monthly | Never | Not usable: it misses the last 3 evaluation origins. It is the same source and regional pattern as rainfall. |
| Fish-kill events (`E87_Outcome_Gap/data_derived/fishkill_events.csv`) | Province (news-reported; not checked against BFAR) | 132 events, 2021-2026 | First-report date | Tested in E87 | Worse (Brier +0.036 at Lead 2) |
| GDELT DOC news volume: shortage, agri_supply, jobs_income, assistance (`E114_Final_Run/data`) | National | Daily 2017+ | Month m usable from day 1 of m+1 | Tested in FINAL_FOOD_INSECURITY_LIGHTGBM | No gain |
| Rice policy events (`E46_Rice_Policy/data`) | National | 5 events, 2023-2025 | Announcement dates | Tested in E46 | Its direction contradicts the 2024-Q4 misses: the July 2024 tariff cut implies falling prices, but prices rose |
| RTWPB IV-A wage orders 19-23 (`E87_Outcome_Gap/data_acquired/wage_orders`, PDF) | Region | About one order a year | Order dates | Never | Regional step changes, with no province-quarter variation to separate HIGH from LOW. No testable Lead-2 hypothesis. |
| PSA retail prices (`commodity_prices.parquet`) | Province | 2020-Q1..**2025-Q4** | Monthly | No | Ends before the last evaluation origins; the same price information as the CPI subgroups (closed in §14) |
| PSA production volumes (`food_availability_panel.parquet`) | Province | 2021-Q1..2026-Q2 | About 1-2 months after the quarter | Partly (A2, C3, C4) | Already represented |
| Domestic fuel prices (`oil_prices.parquet`) | National (one value per quarter) | 2021-2026-Q3 | Weekly / monthly | Crude is in (W_crude_yoy) | National-only duplicate |
| Outcomes: CBMS 2024 FIES, FNRI ENNS provincial FIES, PSA subsistence 2021/2023, NNS 2025 regional | Province / region | One-off cross-sections | — | — | No repeated provincial outcome (OUTCOME_GAP_RESOLUTION); CBMS/FNRI requests drafted, never sent |
| **Not in the repository:** BSP Monetary Policy Report inflation path, DA price outlooks, PAGASA seasonal climate outlooks, DSWD/WFP monitoring, OCTA rounds after 2025 | National / regional | — | Published before the cut-offs | — | Would need collection and an availability audit. None is provincial. |

### 15.3 Development-only rainfall screen (protocol 22e57d20…, committed before running)

Rows: Lead 2, targets 2023-Q2..2024-Q4 (35 rows, 7 quarters). No evaluation row was read. The outcome is realised minus projected price margin.

| Signal | Spearman ρ | 90% CI |
|---|---|---|
| Rainfall anomaly, origin quarter | −0.07 | [−0.35, +0.33] |
| Provincial deviation from the five-province mean | +0.05 | [−0.13, +0.29] |
| Absolute anomaly | −0.02 | [−0.31, +0.27] |

The rule (|ρ| ≥ 0.30 and the CI excluding 0) fails for all three. **No candidate was built.**

### 15.4 Pass/fail with the unchanged criteria (P0H4-U; no candidate qualified)

| Criterion | Lead 1 | Lead 2 |
|---|---|---|
| R1 ≥ 10 quarters, ≥ 40 rows | pass (14, 70) | pass (13, 65) |
| R2 accuracy ≥ 0.75 | pass (0.843) | pass (0.800) |
| R3 balanced accuracy ≥ 0.70 | pass (0.776) | pass (0.732) |
| R4 > always-LOW and persistence | pass | pass |
| R5 Brier better than persistence and climatology | pass (.021 / .030) | pass (.029 / .078) |
| R6 HIGH precision and recall ≥ 0.60 | pass (0.69 / 0.65) | **fail (0.63 / 0.59)** |
| R7 thirds ≥ 0.60, LOQO ≥ 0.70 | pass | pass (0.65; 0.783) |
| **Decision** | **reliable (development evidence)** | **not reliable** |

**Five trigger groups** (unchanged evidence, §6; no new candidate, so nothing is re-measured):
- **Market/Prices** carries the forecast: removing it worsens Lead-2 Brier by +0.037 [+0.009, +0.063].
- **Climate** adds noise at Lead 2 (−0.005).
- **Employment** +0.003 (n.s.); **Fish production** ≈ 0; **OFW remittances** ≈ 0.
- Employment, OFW remittances and El Niño have no provincial variation (§15.1). This is the structural reason they cannot separate HIGH from LOW provinces.

### 15.5 Thesis-ready explanation

> **Why Lead 2 misses HIGH cases.**
> - Of the 13 Lead-2 errors, 8 (3 missed, 5 false alarms) could not have been avoided with the information published at the forecast date:
>   - three missed cases in 2023-Q4, where the latest hunger survey sat exactly at the threshold and the next survey actually fell before hunger surged;
>   - two cases whose price label lay within CPI rounding of the threshold;
>   - three false alarms in which food prices fell after the forecast date, against both the price projection and comparable past cases.
> - The other five errors are cases where the inputs pointed weakly in the right direction, but none of nine targeted model revisions moved them across the decision threshold.
> - Eleven of the twenty-one inputs (employment, remittances, El Niño, the hunger outlook, news counts and world prices) are national or regional, so they cannot distinguish provinces within a quarter, and seven of the thirteen quarters had mixed provincial outcomes.
>
> **New data.** The repository holds no unused, timely, province-level source that predicts the remaining errors:
> - provincial rainfall was screened on development data and showed no relationship (|ρ| ≤ 0.07);
> - other sources were already tested, are national, or end before the evaluation period.
>
> **Result.** The final model (P0H4-U) is reliable at Lead 1 (the current quarter: accuracy 0.84, HIGH recall 0.65) and reaches 0.80 accuracy at Lead 2. It fails the HIGH-recall criterion at Lead 2 by one case (10 of 17), so Lead 2 is reported as experimental.
>
> **Limitations.**
> - Every 2021-2026 quarter has been examined during development.
> - The target is a regional-hunger × provincial-price proxy, not measured provincial food insecurity.
> - The Lead-2 evaluation rests on 17 HIGH cases in 7 quarters.
>
> **Next validation steps.**
> 1. Score the sealed forecasts prospectively from 2027-Q1. At about 1.3 HIGH cases per quarter, roughly 44 quarters are needed to bound recall above 0.60.
> 2. Send the drafted CBMS 2024 and FNRI provincial FIES requests, to validate the target beyond the regional proxy.
> 3. Obtain a hunger or food-access observation between SWS rounds (DSWD/WFP monitoring).
> 4. Add forward-looking price information issued before the quarter (BSP/DA outlooks), after an availability audit.

**Served state (unchanged):**
- P0H4 is the served default (seal a498b5ef).
- P0H4-U, the research baseline used throughout, is served only with `AIPHEED_CH1_ENGINE=fr` (seal bd6572e1).
- K1 and K2 are not adopted.

**Files:**
- `runner/case_audit.py`, `runner/rain_screen.py`;
- `out/case_audit.csv`, `out/case_audit.json`, `out/rain_screen.json`;
- `PROTOCOL_LEAD2_CAUSES_SCREEN.md`;
- tests in `backend/tests/integration/test_lead2_final.py`.

---

## 16. Structured LightGBM tuning campaign (LEAD2_TUNING; branch `aiPHeed/lead2-lgbm-tuning`; protocol committed in e5fdf72 before scoring)

### 16.1 Pipeline audit: what can be tuned and what cannot

| Part | Status |
|---|---|
| Served P0H4 vs research P0H4-U | The same unified LightGBM price model, × π_H. P0H4-U only re-issues Leads ≥ 2 after the SWS release. Lead 2: P0H4 0.769 (TP 6, FP 4), P0H4-U 0.800 (TP 10, FP 6). |
| LightGBM settings before this campaign | 8 configurations: depth 1/2, 50/150 rounds, class weight none/balanced; fixed min_child 15, L2 5, learning rate 0.05; no feature or row sampling, L1 or split-gain penalty; chosen per origin on inner chronological folds |
| **Tunable** | Every LightGBM hyperparameter, class weighting, the round count (early stopping), feature form |
| **Not tunable without changing the task** | π_H (SWS-based, not LightGBM), the product rule, the T43c labels, the S-AB timing, the 0.50 cut and R1-R7 |
| **Ranking headroom** | No cut on P0H4-U's Lead-2 probabilities meets R6. A threshold or calibration rule therefore cannot produce a Lead-2 pass; only a better HIGH-vs-LOW ordering can. |
| Structural cap | 3 of the 7 Lead-2 misses have π_H = 0.50, so recall ≤ 14/17 for any price model |

### 16.2 Target and horizon check (unchanged; reported, not altered)

- **Target.** T43c is the operational Chapter I proxy: Balance Luzon SWS hunger > 11.3% AND the provincial food-price condition. It is **not** a direct measurement of provincial food insecurity (§2, §15).
- **Class balance.** HIGH share by lead: 0.24 / 0.26 / 0.28 / 0.31 (17 HIGH at every lead).
- **Labels near the price threshold.** 5 rows within ±0.10 point (rounding) and 15 within ±0.50 at every lead.
- **Timing.** Every training label is used only after both its SWS round and its last CPI month were published (§12.1). The SWS recall window overlaps the price quarter by 90% on average.
- **Decision.** No label change; horizons and cut-off rules are unchanged.

### 16.3 Search procedure

- **72 structures × 5 round checkpoints = 360 configurations:**
  - (depth, leaves) ∈ {(1, 2), (2, 4), (3, 8)};
  - min_data_in_leaf ∈ {15, 5, 40};
  - (feature_fraction, bagging_fraction) ∈ {(1, 1), (0.7, 0.8)}, bagging_freq 1;
  - (L1, L2, min_split_gain) ∈ {(0, 5, 0), (1, 20, 0.05)};
  - class weight ∈ {none, balanced};
  - learning rate 0.05; rounds read at 25 / 50 / 100 / 150 / 300 (early stopping on chronological validation).
- The seed (2027), deterministic mode and the monotone price constraints are those of P0H4-U.
- **The search contains the P0H4-U grid.** Restricted to it, the code reproduces P0H4-U to 4.9e-7.

| Candidate | Features | How hyperparameters were chosen |
|---|---|---|
| N0 | P0H4-U columns | **Nested:** per origin, on that origin's own inner chronological folds (no evaluation row used) |
| N1 | + A1 × V1 (market pressure × vulnerability) | nested |
| N2 | + deviation of current food / gap inflation from the province's own earlier history | nested |
| G0 | P0H4-U columns | **One configuration chosen on DEV** Lead-2 Brier (targets ≤ 2024-Q4), with the Lead-1 constraint. Chosen: depth 1, min_child 15, feature 0.7 / bagging 0.8, L2 5, no class weight, 25 rounds. |

The CONF block (targets 2025-Q2..2026-Q3) was used by no selection.

### 16.4 Results (identical rows; "Δ vs P0H4-U" is the Brier difference with 90% quarter-block CI; negative = better)

| | P0H4 (served) | **P0H4-U (baseline)** | N0 | N1 | N2 | G0 |
|---|---|---|---|---|---|---|
| **Lead 1** accuracy | 0.843 | 0.843 | 0.857 | 0.800 | 0.829 | 0.886 |
| L1 balanced | 0.776 | 0.776 | 0.826 | 0.748 | 0.787 | 0.825 |
| L1 precision / recall | 0.69 / 0.65 | 0.69 / 0.65 | 0.68 / 0.76 | 0.58 / 0.65 | 0.63 / 0.71 | 0.80 / 0.71 |
| L1 Brier (Δ vs P0H4-U) | 0.132 | 0.132 | 0.131 (−0.002 [−0.014, +0.011]) | 0.141 (+0.008) | 0.129 (−0.004 [−0.016, +0.010]) | 0.158 (+0.026 [+0.004, +0.049]) |
| L1 failed | — | — | — | R6 | — | R5 |
| **Lead 2** accuracy [90% CI] | 0.769 [0.65, 0.88] | **0.800** [0.71, 0.89] | 0.723 [0.63, 0.82] | 0.723 [0.62, 0.83] | 0.754 [0.65, 0.85] | 0.738 [0.65, 0.83] |
| L2 balanced | 0.635 | 0.732 | 0.661 | 0.661 | 0.681 | 0.709 |
| L2 HIGH precision / recall | 0.60 / 0.35 | **0.63 / 0.59** | 0.47 / 0.53 | 0.47 / 0.53 | 0.53 / 0.53 | 0.50 / **0.65** |
| L2 TP FP FN TN | 6 4 11 44 | 10 6 7 42 | 9 10 8 38 | 9 10 8 38 | 9 8 8 40 | 11 11 6 37 |
| L2 Brier (Δ vs P0H4-U) | 0.194 (+0.027) | **0.167** | 0.187 (+0.019 [+0.002, +0.039]) | 0.182 (+0.015 [+0.001, +0.031]) | 0.184 (+0.017 [+0.003, +0.036]) | 0.186 (+0.019 [−0.002, +0.041]) |
| L2 Δ vs served P0H4 | — | −0.027 | −0.008 | −0.012 | −0.010 | −0.008 |
| L2 DEV Brier | 0.235 | 0.177 | 0.193 | 0.190 | 0.199 | **0.167** (selected on it) |
| L2 CONF Brier / accuracy | 0.148 / 0.867 | 0.156 / 0.833 | 0.179 / 0.733 | 0.173 / 0.767 | 0.167 / 0.800 | **0.209 / 0.733** |
| L2 thirds; LOQO min | 0.72, 0.70, 0.90; 0.750 | 0.84, 0.65, 0.90; 0.783 | 0.80, 0.55, 0.80; 0.700 | 0.80, 0.55, 0.80; 0.700 | 0.80, 0.60, 0.85; 0.733 | 0.84, 0.55, 0.80; 0.717 |
| L2 AUC (T43c) | 0.625 | 0.760 | 0.694 | 0.710 | 0.684 | 0.741 |
| L2 failed criteria | R3, R5, R6 | **R6** | R2-R7 | R2-R7 | R3, R5, R6 | R2, R4, R5, R6, R7 |

**Lead 2 by province (P0H4-U → G0, accuracy and TP/FP out of HIGH cases; 13 rows each, descriptive):**
- Cavite: 0.69 (1/2 of 3) → 0.62 (1/3)
- Laguna: 0.77 (3/1 of 5) → 0.69 (3/2)
- Quezon: 0.77 (4/1 of 6) → 0.85 (5/1)
- Rizal: 0.85 (0/2 of 0) → 0.85 (0/2)
- Batangas: 0.92 (2/0 of 3) → 0.69 (2/3)

**Development-only diagnostics.**
- **Class weighting.** In all 180 matched configuration pairs, `balanced` gave a worse Lead-2 DEV Brier (mean 0.191 vs 0.180) and a *lower* recall (0.34 vs 0.53). The price condition is the majority class in most training windows, so balancing down-weights it.
- **No configuration reaches the R6 recall.** Across all 360 configurations, the highest Lead-2 DEV recall at 0.50 is 0.545. DEV Brier ranges from 0.167 to 0.245 (median 0.183; P0H4-U 0.177).

### 16.5 Frozen adoption rule

- Strongest eligible candidate by Lead-2 DEV Brier: **G0** (0.167 vs 0.177).

| Condition | G0 |
|---|---|
| Lead-2 DEV Brier ≥ 0.005 better | pass |
| Lead-1 DEV Brier not > +0.005 | pass |
| Lead-2 DEV balanced accuracy not lower | pass |
| Lead-2 accuracy / balanced / precision within 0.02 | **fail / fail / fail** |
| Lead-2 recall within 0.02 | pass (0.65) |
| New false alarms ≤ new hits | **fail** |
| Lead-2 CONF accuracy not lower | **fail** (0.733 vs 0.833) |
| Lead 1 passes R1-R7 | **fail** (R5) |
| G0 extra guard: CONF Brier not worse / CONF accuracy not lower | **fail** (0.209 vs 0.156) / **fail** |

**Not adopted. P0H4-U is retained.**

### 16.6 What the campaign shows

1. **Wider tuning makes Lead 2 worse, not better.**
   - Nested selection over 360 configurations picks deeper, longer models on inner folds of 5-20 rows. Every nested candidate is significantly worse than P0H4-U at Lead 2 (Brier +0.015 to +0.019, CIs exclude 0).
   - The small P0H4-U grid is the better-regularised choice for 13 quarters of data.
2. **Choosing one configuration on the development quarters overfits them.**
   - G0 improves DEV Lead-2 Brier (0.177 → 0.167) and raises recall to 0.65.
   - On the untouched CONF quarters it is the worst candidate (Brier 0.209, accuracy 0.733), with 11 false alarms.
   - G0's ordering would meet R6 at one cut (0.533), but that cut can only be found on the evaluation rows, so it is not admissible.
3. **Feature-form arms add nothing.** Market pressure × vulnerability (N1) and own-history deviation (N2) correlate 0.86-0.94 with the existing price columns, and both are worse than P0H4-U at Lead 2.
4. **Class weighting does not help.** It lowers recall and worsens calibration in every matched pair.
5. **Lead 1.** N0 and N2 are slightly better than P0H4-U at Lead 1 (accuracy 0.857 / 0.829, Brier −0.002 / −0.004), but not significantly, and worse on the CONF quarters (0.800 / 0.767 vs 0.867). No Lead-1 change is warranted.
6. **The Lead-2 limit is the information, not the settings.** No cut on P0H4-U meets R6. The best development-period recall over 360 configurations is 0.545. The remaining misses are hunger ties, rounding-level labels and price changes after the cut-off (§15).

### 16.7 Final outcome

| Criterion | Lead 1 (P0H4-U) | Lead 2 (P0H4-U) | Lead 2, strongest tuned candidate (G0) |
|---|---|---|---|
| R1 | pass | pass | pass |
| R2 accuracy ≥ 0.75 | pass 0.843 | pass 0.800 | **fail** 0.738 |
| R3 balanced ≥ 0.70 | pass 0.776 | pass 0.732 | pass 0.709 |
| R4 > always-LOW, persistence | pass | pass | **fail** |
| R5 Brier vs persistence / climatology | pass | pass | **fail** (p .057 / .224) |
| R6 precision / recall ≥ 0.60 | pass 0.69 / 0.65 | **fail 0.63 / 0.59** | **fail 0.50 / 0.65** |
| R7 stability | pass | pass | **fail** (third 0.55) |

- **The 80% accuracy goal with all seven criteria is not achieved.**
- **The maximum reliable horizon remains Lead 1.**
- P0H4-U stays the research baseline. P0H4 stays the served default (seal a498b5ef).
- The campaign's configuration, every candidate's rows and the 360-configuration DEV table are saved in `out/tune.json`, `out/tune_rows.csv`, `out/tune_configs.csv` and `out/tune_dev_configs.csv`.

**Thesis-ready paragraph.**

> A structured LightGBM tuning campaign tested 360 configurations of tree structure, minimum leaf size, feature and row sampling, L1/L2 and split-gain regularisation, class weighting and early-stopped boosting rounds. Two cut-off-safe feature forms were also tested (market pressure × vulnerability; deviation from the province's own inflation history). Hyperparameters were chosen either inside each forecast origin on earlier quarters only, or once on the 2023-24 development quarters. Neither improved the two-quarter-ahead forecast:
> - the nested choices were significantly worse than the original eight-configuration model;
> - the configuration chosen on the development quarters improved them but deteriorated on the later, untouched quarters (accuracy 0.73 vs 0.83).
>
> Class weighting reduced HIGH recall and worsened calibration. No configuration reached a development-period HIGH recall of 0.60 at the 0.50 cut. The original model's ranking admits no cut meeting the precision-and-recall criterion, so the remaining Lead-2 shortfall reflects missing information (delayed hunger surveys, price changes after the forecast date, labels at the rounding limit), not untuned settings. The final model is unchanged: reliable at Lead 1 (accuracy 0.84, HIGH recall 0.65), 0.80 accuracy at Lead 2 with HIGH recall 0.59, which is short of the 0.60 criterion.

**Files:**
- `PROTOCOL_LEAD2_TUNING.md`;
- `runner/tune_lib.py`, `runner/tune.py`, `runner/features_v5.py`;
- `data/stack_v5.csv`;
- `out/tune*.{json,csv}`, `out/features_v5_audit.json`;
- `backend/tests/integration/test_lead2_tuning.py` (6 tests).

---

## 17. Architecture verification and final decision (LEAD2_ARCH; `runner/arch_audit.py`, `out/arch_audit.json`)

### 17.1 The verified prediction equation

For province p, origin quarter t and lead k (target quarter t + k):

1. **Issue date.** Lead 1: the first day of quarter t + 1 (schedule A). Leads ≥ 2: the day after SWS publishes quarter t's Balance Luzon reading, at the latest day 1 of month 3 of quarter t + 1 (schedule B). Together these are S-AB.
2. **Hunger part.**
   - π_H = Φ((h_last − 11.3) / max(σ_h, 0.5)).
   - h_last is the newest Balance Luzon reading published before the issue date.
   - σ_h is the RMS of the h-step changes in the four SWS areas (h = target − reading quarter) published before the issue date.
   - When fewer than 8 changes exist, the served H1 is used instead (0 of the 250 evaluation rows).
3. **Price part.**
   - π_P = sigmoid(LightGBM raw score), a single unified LightGBM over leads 1-15.
   - Inputs: all 12 indicator families (21 columns, the five trigger groups among them).
   - Monotone in A1_food, A1_gap and A_mom.
   - Refitted at each origin on rows whose price labels were known; configuration chosen on inner chronological folds.
4. **Forecast.** P = π_H × π_P; **HIGH if P ≥ 0.50.** No clipping or intermediate threshold exists anywhere on the path.

**Reproduction check:**
- π_H recomputes to within 4.7e-7 on all 250 rows;
- P = π_H × π_P to within 7.8e-7;
- π_P ranges from 0.016 to 0.800 over all evaluation rows.

### 17.2 Does the hunger part impose a real upper bound on recall? Yes, for three cases, and only for classification.

| Lead-2 HIGH case | Newest reading at the issue | π_H | π_P needed for P ≥ 0.50 | Model π_P | Hit |
|---|---|---|---|---|---|
| Batangas, Laguna, Quezon 2023-Q4 | 2023-Q2 = **11.3** | **0.500** | **1.000 (impossible)** | 0.495 | no |
| Batangas, Cavite, Laguna, Quezon 2024-Q2 | 2023-Q4 = 14.3 | 0.760 | 0.658 | 0.68-0.80 | yes |
| Quezon 2024-Q3 | 2024-Q1 = 15.3 | 0.821 | 0.609 | 0.432 | no |
| Cavite, Laguna 2024-Q4 | 2024-Q2 = 19.6 | 0.968 | 0.516 | 0.166 / 0.173 | no |
| Quezon 2024-Q4 | 19.6 | 0.968 | 0.516 | 0.651 | yes |
| Batangas, Laguna, Quezon 2025-Q2 | 2024-Q4 = 25.3 | 0.988 | 0.506 | 0.60-0.65 | yes |
| Laguna, Quezon 2025-Q3 | 25.3 | 0.975 | 0.513 | 0.65 / 0.71 | yes |
| Cavite 2026-Q2 | 2025-Q4 = 16.7 | 0.806 | 0.620 | 0.345 | no |

**Controlled test** (`backend/tests/integration/test_lead2_arch.py`):
- For the 2023-Q4 issue (2023-08-03), `fr_lib.pi_h` returns exactly 0.5.
- A LightGBM fitted with the production recipe, given extreme price inputs (10⁶), still returns π_P < 1.
- With π_P = 1 − 10⁻¹², P = 0.4999999999995 < 0.50.
- With the largest π_P the model ever produced (0.80), P = 0.40.

**Conclusions:**
- **The statement in §3 and §15 is correct.** The mathematical recall ceiling at the 0.50 cut is **14/17 = 0.82**. The 13/17 in §13.1 is the *practical* ceiling, which also excludes the rounding-level label Cavite 2026-Q2.
- The cap applies to classification only. The three capped cases can still rank above LOW rows, but never cross 0.50.
- Every other missed case needed π_P between 0.52 and 0.62 and received 0.17-0.43.

### 17.3 The precise reason the model misses HIGH cases

| Misses | Mechanism in the equation |
|---|---|
| 3 (2023-Q4) | **π_H = 0.5 exactly** because the newest reading equals the 11.3 line. The next reading (10.3, published 2023-11-20) was lower still, so no timelier hunger reading would have helped. |
| 3 (Quezon 2024-Q3; Cavite and Laguna 2024-Q4) | **π_P too low.** The flat CPI projection was below threshold (−1.5 to −2.1 points for 2024-Q4; Quezon's was above at +0.58, but the province profile pulled it down). Prices then rose after the issue date. |
| 1 (Cavite 2026-Q2) | **Label at the rounding limit:** realised margin +0.02 point, projection −1.04 |

### 17.4 Target and class learning (`C_target_learning`)

| Question | Finding |
|---|---|
| Is the target defined the same at every lead? | **Yes.** The price label of every (province, quarter) is identical across all leads and origins (nunique = 1). The hunger condition is the same Balance Luzon reading for all provinces. |
| Temporal representation | The unified model stacks leads 1-15, so each label appears 3.5 (2022-Q4) to 9.8 (2026-Q2) times, with different lead-specific inputs. Recent targets have at least as many rows as older ones, so old quarters are not over-weighted. |
| Are the classes learned consistently over time? | The price-condition base rate in training moves from 0.21 (2022-Q4) to 0.64 (2023-Q4) and back to 0.47 (2026-Q2). This is a genuine regime shift (the 2023-24 inflation episode), and it is why above-threshold pressure in 2025-26 often reverted (the false alarms). Recency weighting to follow it was tested (B2/B3) and made Lead 2 worse. |
| Is the loss aligned with the evaluation? | Partly. The price model minimises price-label log loss (a proper score), while the evaluation scores P = π_H × π_P. A decision-weighted loss (rows weighted by π_H) would align them, but before 2024 almost every training row has π_H < 0.5. The weights would only switch on in the 2023-24 inflation regime: in effect recency weighting, which was already rejected. |
| Probability use | Ranking and classification both use P. No cut on P0H4-U's Lead-2 P meets R6 (§16.1), so recalibration cannot help. |
| Could one LightGBM rank T43c directly? | **Not with the development data.** Distinct T43c HIGH labels known in training are **2 at every origin through 2023-Q4**, and 5 at 2024-Q1/Q2. Under the existing eligibility rule (≥ 5 HIGH rows), a direct model is **ineligible at 5 of the 7 development origins**. The earlier direct single-model study (LEAD2_ONE_MODEL S0-S3, quarter-start timing) reached only 0.68-0.75 at Lead 2. The factorisation exists precisely because the price label has 30-100 distinct training labels and the joint label has 2-19. |

### 17.5 Evaluation design and the P0H4 / P0H4-U difference

- **Uncertainty.** Lead 2 has 17 HIGH cases in 7 of 13 quarters, so one case moves recall by 0.059. If the true recall were:
  - 0.65, the observed recall would reach 11/17 only 62% of the time;
  - 0.70, 78% of the time;
  - 0.59, 41% of the time.
- Separating a 0.70 recall from 0.60 with a 90% bound needs about **57 HIGH cases**.
- **Why P0H4 and P0H4-U differ.** They share the price part exactly. P0H4 issues Lead 2 at the quarter start; P0H4-U re-issues it after the SWS release (median 33 days later), with one newer hunger reading. This changes 8 Lead-2 calls (`out/arch_p0h4_vs_u.csv`):
  - **+4 hits:** all of 2024-Q2, using the 2023-Q4 reading of 14.3 published 2024-01-22 instead of 2023-Q3's 10.3;
  - **+3 false alarms:** Rizal 2024-Q2, Rizal 2025-Q2, Quezon 2026-Q3;
  - **−1 false alarm:** Laguna 2026-Q2.
- **Which is the real deployment behaviour?**
  - Today, **P0H4**: the served default issues every lead at quarter start, SWS readings are entered by hand, and the scheduler runs quarterly.
  - P0H4-U reflects deployment only if the operator re-issues Lead 2 after each SWS release. The `AIPHEED_CH1_ENGINE=fr` export does this; its 2027-Q1 forecast was re-issued 2026-10-15 and sealed (bd6572e1).
- No threshold or configuration was selected on the evaluation period in this round.

### 17.6 Candidates considered and why none was scored

| Candidate | Rationale | Development data check | Decision |
|---|---|---|---|
| Direct T43c LightGBM under S-AB timing | Avoid the product cap; learn the joint label | Ineligible at 5 of 7 DEV origins (2 HIGH labels); 10 Lead-2 DEV rows would decide it | **Not run.** It cannot be evaluated fairly, and the closest tested form (S0-S3) failed. |
| Hybrid: direct where eligible, product otherwise | Same | Only 2 DEV origins (5 HIGH targets) would use the direct part | Not run: too little development data |
| Decision-weighted price loss (weights ∝ π_H) | Align the loss with P | Weights are near-uniform before 2024, then equivalent to recency weighting | Not run: an equivalent of rejected B2 |
| Hunger-dependence (copula) correction to the product | The price and hunger conditions are negatively correlated (ρ = −0.38) | Needs joint labels: 2-19 distinct | Not identifiable |
| Recalibration or threshold | — | No cut meets R6 for P0H4-U | Excluded mathematically |

No candidate met the stopping rule set before this round, so **no new experiment was scored**.

### 17.7 Final comparison and decision

| Criterion | P0H4 (served), Lead 1 | P0H4, Lead 2 | P0H4-U, Lead 1 | **P0H4-U, Lead 2** | Strongest tuned (G0, §16), Lead 2 |
|---|---|---|---|---|---|
| Accuracy | 0.843 | 0.769 | 0.843 | **0.800** | 0.738 |
| Balanced accuracy | 0.776 | 0.635 | 0.776 | 0.732 | 0.709 |
| HIGH precision / recall | 0.69 / 0.65 | 0.60 / 0.35 | 0.69 / 0.65 | 0.63 / **0.59** | 0.50 / 0.65 |
| TP FP FN TN | 11 5 6 48 | 6 4 11 44 | 11 5 6 48 | 10 6 7 42 | 11 11 6 37 |
| Brier | 0.132 | 0.194 | 0.132 | 0.167 | 0.186 |
| Later quarters (2025-Q2..2026-Q3), accuracy / Brier | 0.867 / 0.123 | 0.867 / 0.148 | 0.867 / 0.123 | 0.833 / 0.156 | 0.733 / 0.209 |
| R1 | ✓ | ✓ | ✓ | ✓ | ✓ |
| R2 | ✓ | ✓ | ✓ | ✓ | ✗ |
| R3 | ✓ | ✗ | ✓ | ✓ | ✓ |
| R4 | ✓ | ✓ | ✓ | ✓ | ✗ |
| R5 | ✓ | ✗ | ✓ | ✓ | ✗ |
| R6 | ✓ | ✗ | ✓ | **✗** | ✗ |
| R7 | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Decision** | **reliable** | not reliable | **reliable** | **not reliable (R6)** | not reliable |

Lead-1 rows are identical for P0H4 and P0H4-U: they differ only from Lead 2 on.

**Decision**
- Reliability has **not** improved in this round.
- P0H4 stays the served default (seal a498b5ef). P0H4-U stays the research baseline (bd6572e1).
- The maximum reliable horizon is **Lead 1**.
- 80% accuracy with all seven criteria at Lead 2 is not achieved with the available data.

### 17.8 The additional observations required, and how each would enable a better model

1. **A second hunger observation between SWS rounds.** A monthly DSWD/WFP food-access monitor, or SWS microdata for CALABARZON, for Balance Luzon or CALABARZON.
   - It would replace the single reading in π_H with a fresher, less tied estimate. This addresses the 3 capped cases and the timing gap behind P0H4 vs P0H4-U.
2. **More target quarters with HIGH cases.**
   - About 57 HIGH cases (≈ 44 quarters) are needed to bound recall.
   - At least 5 distinct T43c HIGH labels at every development origin would make a direct-ranking LightGBM evaluable.
   - The sealed prospective forecasts from 2027-Q1 accumulate these.
3. **Forward-looking price information published before the issue date** (BSP inflation path, DA price and supply outlooks, rice import schedules).
   - It gives π_P information about post-issue price moves, the cause of 3 misses and 3 false alarms.
4. **A provincial, repeated food-insecurity outcome** (CBMS 2024 FIES; FNRI provincial FIES).
   - It would validate the target itself and allow a province-level hunger part instead of one regional reading for all five provinces.
5. **Operational:** automate the SWS release re-issue (the P0H4-U schedule) if the researchers choose to deploy it. That makes deployment match the better-scoring evaluation design, but it does not by itself pass R6.

**Files:**
- `runner/arch_audit.py`;
- `out/arch_audit.json`, `out/arch_cap_cases.csv`, `out/arch_p0h4_vs_u.csv`;
- `backend/tests/integration/test_lead2_arch.py` (6 tests).

---

## 18. Deployment timing (SWS-release re-issue) and the hunger × price formula

### 18.1 How Lead-2 forecasts reach the dashboard today

| Step | Current behaviour |
|---|---|
| Forecast generation | The dashboard serves a **static export**, `backend/data/ch1_engine/rows.csv` (P0H4, seal a498b5ef), written by the research export scripts. Every lead is issued on the first day of the quarter (latest: 2026-10-01). |
| SWS readings | Entered **by hand** into the research rounds file. No fetcher runs; SWS publishes about 2-7 weeks into each quarter (2026-Q3: 2026-10-14). |
| Scheduler (`app/tasks/scheduler.py`) | The quarterly E27 cycle (15 Jan / Apr / Jul / Oct), daily news collection and a monthly refresh. **None re-issues the CH1 forecasts after an SWS release.** |
| History | The export keeps one row per province-quarter, so an earlier issue is overwritten, not kept |
| Consequence | Deployed Lead-2 forecasts use a hunger reading that is often two quarters old. The better-scoring P0H4-U rows exist only as a second research export (`ch1_engine_fr`, served only with `AIPHEED_CH1_ENGINE=fr`). |

### 18.2 What was built (off by default)

`backend/app/ml/inference/sws_reissue.py`:

- **Manual SWS entry.** `enter_sws_reading()` and `scripts/sws_reissue.py enter`. Each entry is validated: area, 0-100 range, fieldwork end not after publication and not before the quarter. **A publication after today is refused.** An identical re-entry returns `duplicate`; a conflicting value is refused. The store is `backend/data/ch1_reissue/sws_rounds.csv`, seeded from the verified research rounds file.
- **Release-triggered re-issue.** `reissue(now)` re-issues each open origin's Lead-2+ forecasts:
  - **When:** the day after SWS publishes that origin quarter's Balance Luzon reading. If the reading arrives after the window cap (day 1 of month 3), the re-issue happens at the cap instead.
  - **How:** π_H is recomputed with the same formula as P0H4-U, using only rounds published before the issue date. π_P is the quarter-start LightGBM output, unchanged; **the model is not refitted.**
  - **Lead 1** is not re-issued.
- **History.** `forecast_history.csv` is **append-only**. Each row records:
  - `forecast_id`, `issue_date`, `data_cutoff`, `trigger` (`quarter_start` / `sws_release` / `window_cap`);
  - the SWS quarter and publication date used, `h_last`, `sigma_h`, both parts and the probability;
  - `supersedes` (the forecast it replaces) and `recorded_at`.

  `current(now)` returns the forecast in force at any date.
- **No duplicates.** One re-issue per schedule-B date. A second SWS round for the same quarter before the cap (it happened once, in 2025-Q2) moves the date, and the forecasts are re-issued again; the earlier rows are kept.
- **Scheduler.** A daily 05:00 job, `run_sws_reissue`, is registered **only when `AIPHEED_SWS_REISSUE=1`**. Every run is idempotent.
- **Served default unchanged.** `ch1_system` still serves `ch1_engine`. The history is not read by the dashboard until the researchers authorise that switch.

### 18.3 Verification

**Day-by-day replay** (`runner/deploy_replay.py`, `out/deploy_replay.json`):
- 1,343 days, 2022-12 to 2026-12, running the job twice a day.
- Each origin's quarter-start P0H4 forecasts are recorded on their own issue date.

| Check | Result |
|---|---|
| Re-issued Lead-2..4 probabilities vs P0H4-U | **max \|Δ\| 1.0e-6** (180 rows) |
| Issue dates vs the evaluated S-AB schedule | all equal: 13 SWS releases, 1 window cap |
| Repeated runs (second run each day, plus 3 extra runs) | 0 rows added; file byte-identical |
| Duplicate forecast IDs | 0 |
| Quarter-start rows | all 250 kept unchanged; 15 re-issues superseded by the 2025-Q2 second round, all kept |
| Every SWS reading used was published before its issue date | yes |

**Backend tests** (`tests/integration/test_sws_reissue.py`, 8 tests):
- manual-entry validation and duplicates;
- a release-triggered update that reproduces the deployed `ch1_engine_fr` 2026-10-15 rows within 1e-5;
- the window cap without a release;
- repeated runs and append-only history (earlier bytes unchanged);
- an extreme future round in the store leaves earlier forecasts unchanged;
- the replay result;
- the scheduler registers the job only when enabled;
- the served default and seal are unchanged.

### 18.4 The deployment-timing effect, evaluated alone (Lead 2, same model, same 65 rows)

| | Deployed today: P0H4 quarter-start | Deployable: P0H4 + SWS re-issue (= P0H4-U) |
|---|---|---|
| Accuracy | 0.769 | **0.800** |
| Balanced accuracy | 0.635 | 0.732 |
| HIGH precision / recall | 0.60 / 0.35 | 0.63 / **0.59** |
| TP FP FN TN | 6 4 11 44 | 10 6 7 42 |
| Brier | 0.194 | **0.168** (Δ −0.027 [−0.059, −0.000], p = .047) |
| Later quarters (2025-Q2..2026-Q3): accuracy / Brier | 0.867 / 0.148 | 0.833 / 0.158 |
| Thirds; LOQO min | 0.72, 0.70, 0.90; 0.750 | 0.84, 0.65, 0.90; 0.783 |
| Brier vs persistence / climatology (p) | .112 / .157 | .029 / .085 |
| Failed criteria | R3, R5, R6 | **R6 only** |

- **The re-issue fixes the deployed system's R3 and R5 failures and lifts Lead-2 accuracy to the 0.80 goal.**
- **It does not solve R6:** recall stays at 0.59.
- On the later quarters alone it is slightly worse: one more false alarm, accuracy 0.833 vs 0.867.
- It is a deployment change, not a model change: the price model is identical.

### 18.5 Does the hunger × price formula restrict the ranking? No (protocol f3c05aa, development data only)

| Check (targets 2021-Q1..2024-Q4) | Result |
|---|---|
| Dependence between the hunger and price conditions (70 labels, 14 quarters) | **φ = −0.31**, 90% CI [−0.59, −0.03]. Negative: high hunger came with *lower* price pressure in 2021-24. |
| Lead-2 DEV, product (P0H4-U) | AUC 0.775, Brier 0.177, recall 0.45, precision 0.71 |
| Upper bound min(π_H, π_P) (maximal positive dependence) | AUC 0.754, Brier 0.184, recall 0.45, precision 0.56 |
| Lower bound max(0, π_H + π_P − 1) | AUC 0.742, Brier 0.202, recall 0.36, precision 0.80 |

**What this shows**
- With negative dependence, the true joint probability lies **below** the product. So the product does not understate HIGH risk; if anything it overstates it.
- The only alternative that would raise HIGH probabilities (towards min) is contradicted by the data, and it ranks worse on development rows.
- The frozen rule built no candidate.

### 18.6 Why no new model experiment is warranted

Every evidence-supported hypothesis has now been tested or ruled out on development data:
- price-side information: K1/K2 (§13-14), rainfall (§15);
- tuning: 360 configurations, class weights, two feature forms (§16);
- a direct joint-label model: ineligible at 5 of 7 DEV origins (§17);
- the combination formula (§18.5);
- thresholds and calibration: no cut meets R6.

The remaining misses are:
- 3 hunger ties (π_H = 0.5);
- 3 post-issue price moves the inputs did not anticipate;
- 1 rounding-level label.

None has an unused, cut-off-safe signal in the repository. A further model variant would be a search on the same 17 HIGH cases, so no experiment was run.

### 18.7 Comparison

| | Deployed baseline: P0H4 (served) | Research baseline: P0H4-U = P0H4 + re-issue | Candidate |
|---|---|---|---|
| Lead 1: accuracy, precision / recall, Brier | 0.843, 0.69 / 0.65, 0.132 | identical (Lead 1 is not re-issued) | none justified |
| Lead 2: accuracy | 0.769 | 0.800 | — |
| Lead 2: balanced, precision / recall | 0.635, 0.60 / 0.35 | 0.732, 0.63 / 0.59 | — |
| Lead 2: TP FP FN TN, Brier | 6 4 11 44, 0.194 | 10 6 7 42, 0.167 | — |
| Lead 2: later quarters (accuracy) | 0.867 | 0.833 | — |
| Lead 1 R1-R7 | all pass | all pass | — |
| Lead 2 R1-R7 | fails R3, R5, R6 | **fails R6** | — |

### 18.8 Thesis-ready explanation

> **Model performance and deployment timing are separate.**
> - The forecasting model, one LightGBM price model combined with the SWS hunger outlook, is unchanged. It is reliable for the current quarter (Lead 1: accuracy 0.84, HIGH precision 0.69, recall 0.65, all seven criteria met).
> - For the next quarter (Lead 2), the deployed system issued every forecast on the first day of the quarter. The latest published hunger survey was then often two quarters old. Issued that way, Lead 2 scored 0.77 accuracy with HIGH recall 0.35.
> - A re-issue step now updates the Lead-2 forecasts the day after each SWS release, without retraining the model. Its release-triggered updates, repeated runs, append-only history and data cut-off are tested.
> - With it, the same model reaches 0.80 accuracy at Lead 2, a significantly better Brier score (−0.027, p = .047) and HIGH recall 0.59. That clears every criterion except HIGH recall ≥ 0.60, which it misses by one case.
> - The improvement comes from **timelier information, not a better model**.
> - The probability formula (hunger probability × price probability) was checked against the evidence: hunger and price pressure moved in opposite directions in 2021-24 (φ = −0.31), so the formula does not understate risk.
> - Lead 2 remains experimental until more quarters, a between-round hunger observation, forward price information or a provincial food-insecurity outcome (§17.8) allow it to be validated.

### 18.9 Changed files and commits (branch `aiPHeed/lead2-lgbm-tuning`; local, not pushed)

| File | Change |
|---|---|
| `backend/app/ml/inference/sws_reissue.py` | **new**: SWS entry, release-triggered re-issue, append-only history, `current()`, `run_daily()` |
| `backend/app/tasks/scheduler.py` | daily `run_sws_reissue` job, registered only when `AIPHEED_SWS_REISSUE=1` |
| `backend/scripts/sws_reissue.py` | **new** CLI: `enter`, `run`, `status` |
| `backend/data/ch1_reissue/sws_rounds.csv` | **new** SWS store, seeded from `FORECAST_RESEARCH/data/sws_rounds_primary.csv` |
| `backend/tests/integration/test_sws_reissue.py` | **new**, 8 tests |
| `backend/tests/integration/test_lead2_arch.py` | + combination-screen test |
| `experiments/LEAD2_FIVE_TRIGGER/runner/deploy_replay.py`, `out/deploy_replay*.{json,csv}` | **new** replay |
| `PROTOCOL_LEAD2_COMBINATION_SCREEN.md`, `runner/comb_screen.py`, `runner/COMBINATION_SHA256.txt`, `out/comb_screen.json` | formula screen (protocol committed in f3c05aa before running) |
| `ch1_engine/`, `ch1_engine_fr/`, seals, frontend | **unchanged** |

**To activate in deployment (needs your authorisation):**
1. Set `AIPHEED_SWS_REISSUE=1` and `AIPHEED_ENABLE_SCHEDULER=1`.
2. Enter each SWS release with `scripts/sws_reissue.py enter`.
3. Point the dashboard at `sws_reissue.current()`. This last step is not built: the frontend and served export are unchanged.
