# LEAD2_FIVE_TRIGGER: why Lead 2 falls short, what was tried, and what the five triggers contribute

**Branch:** `aiPHeed/forecast-research` (local; not pushed, not deployed). **Date:** 2026-10-28.
**Protocol:** `PROTOCOL_LEAD2_FIVE_TRIGGER.md` (SHA-256 a80e927f, committed in 1036655 before scoring), plus `ADDENDUM_1_TRIGGER_GROUPS.md` (the user's five trigger groups; hashed before the ablation).
**Served model unchanged:** P0H4, seal a498b5ef. Every figure is development evidence: all 2021-26 quarters had been examined before.

## 1. Answer in brief

- **Lead 2 does not meet the existing criteria.** The best defensible Lead-2 forecast is still P0H4-U, the served unified LightGBM with Lead 2 re-issued after each SWS release. It scores 0.800 accuracy at Lead 2 and fails one criterion, R6: HIGH recall is 10 of 17 = 0.59, and 0.60 is needed.
- **None of the pre-registered improvements beat it:**
  - a regional XLM-R news index;
  - risk-history and transition features;
  - forced class balancing;
  - validation-fitted calibration.

  Under the frozen rule the served model is therefore kept.
- **All 7 missed HIGH cases at Lead 2 are price-part misses.** The hunger part was already at or above 0.5 in each. The model's price probability was below 0.5 because none of the available indicators anticipated those price moves 2 quarters ahead.
- **The five triggers are real model inputs, but Market / Prices carries almost all of the measured value.**
  - Removing all five trigger groups worsens the Lead-2 Brier score by +0.046 (90% CI +0.012 to +0.081).
  - Removing Market alone worsens it by +0.037.
  - Climate, Employment, Fish production and OFW remittances each have small, mixed or negligible effects. The dashboard now states this per group.
- **No leakage, no pipeline defect, and no dashboard mismatch.**
  - The served model was reproduced exactly from code (max |Δ| 5e-7).
  - Every dated input precedes its issue date.
  - The dashboard shows exactly the evaluated forecasts.

## 2. Root causes, ranked by demonstrated impact

| # | Cause | Test | Result |
|---|---|---|---|
| 1 | **Too little information about prices two quarters ahead** | CT1 (missed HIGH cases); CT6; FR-II oracle | **Confirmed.** 7/7 Lead-2 misses are price-part misses. The Lead-2 price-term AUC is 0.67. With the true price, Lead 2 would reach 0.938 (FR-II). |
| 2 | **Target construction** | FR-II T1/T3 | **Confirmed** (earlier phase). Since 2023-Q4 the label equals the price condition, and price pressure moved against measured hunger. Lead 2 forecasts a price-pressure proxy, not measured food insecurity. |
| 3 | **Small sample** | n_eff; FR-II power analysis | **Confirmed.** 13 target quarters at Lead 2, 7 of them with any HIGH case, n_eff ≈ 29. Detecting a Brier difference of 0.02 needs about 100 quarters. One more HIGH hit would flip R6. |
| 4 | Class imbalance | CT4: class_weight forced to balanced | **Rejected.** Recall stays 10/17; Lead-2 DEV Brier is 0.012 worse. |
| 5 | Poor representation of change and risk history | CT3 (C2: current price state, share of the last 4 known quarters with the price condition met, quarter-on-quarter change) | **Rejected.** Lead-2 DEV Brier is 0.0085 worse; recall unchanged. |
| 6 | News/NLP coverage defect | CT2 (C1: regional pooled XLM-R index, coverage 21% → 53%) | **Defect confirmed, but no effect.** The LightGBM never split on the new column, so predictions are identical. Headline-level news exists for only 9 of 22 quarters. |
| 7 | Miscalibration | CT5 (Platt scaling on inner-fold predictions) | **Rejected.** Lead 2 falls to 0.677 accuracy; Brier is 0.022 worse. |
| 8 | Defective features, training or evaluation | Exact reproduction; input audit | **Rejected.** Model and metrics reproduce exactly. 21/21 columns reach the model. No duplicate rows, no misaligned dates. |
| 9 | Dashboard shows other numbers | Served rows vs refit | **Rejected.** Max \|Δ\| 5e-7; probability = hunger × price. |
| 10 | Z0-U fails to beat climatology | FR-II §8 | **Power, not a defect.** The MDE is 0.05-0.07 Brier. |

## 3. Before and after (Lead 2, S-AB schedule, 65 province-quarters, 13 quarters)

| Model | Accuracy [90% CI] | Balanced | HIGH P / R / F1 | LOW P / R / F1 | Missed HIGH | Brier | Fails |
|---|---|---|---|---|---|---|---|
| Served P0H4 (quarter-start issue) | 0.769 [0.65, 0.88] | 0.635 | 0.60 / 0.35 / — | — | 11 | 0.194 | R3, R5, R6 |
| **P0H4-U = C0 (final)** | **0.800 [0.71, 0.89]** | 0.732 | 0.62 / 0.59 / 0.61 | 0.86 / 0.88 / 0.87 | **7** | **0.167** | **R6 only** |
| C1 news index | 0.800 | 0.732 | identical to C0 | | 7 | 0.167 | R6 |
| C2 history/transition | 0.800 | 0.73 | 0.62 / 0.59 | | 7 | 0.178 | R5, R6 |
| C4 balanced weights | 0.800 | 0.73 | 0.62 / 0.59 | | 7 | 0.169 | R6 |
| C5 Platt calibration | 0.677 | 0.57 | 0.38 / 0.35 | | 11 | 0.201 | 6 criteria |

**Baselines at Lead 2 (C0).**
- Always-LOW: 0.738.
- Same-information persistence: C0's Brier is better, one-sided p = .029.
- Climatology: C0's Brier is better, p = .078.

**Calibration (C0, Lead 2).** Slope 1.04; calibration-in-the-large −0.07.

**Lead 1 (C0).** 0.843 [0.76, 0.91]; HIGH P / R / F1 0.69 / 0.65 / 0.67; Brier 0.132. Passes R1-R7.

**Leads 3-4.** 0.633 and 0.673; each fails six criteria.

**By target quarter (Lead 2, correct of 5).** Every quarter is 5/5 except:
- 2023-Q4: 2/5, the hunger-surge onset;
- 2024-Q3: 3/5;
- 2024-Q4: 3/5;
- 2025-Q2: 3/5;
- 2024-Q2, 2025-Q3, 2026-Q2 and 2026-Q3: 4/5 each.

The misses cluster at onsets and policy-driven price turns.

**Improvement achieved.** The SWS-update re-issue (from FORECAST_RESEARCH) moves Lead 2:

| | Before | After |
|---|---|---|
| Accuracy | 0.769 | 0.800 |
| HIGH recall | 0.35 | 0.59 |
| Brier | 0.194 | 0.167 |
| Failed criteria | 3 | 1 |

No change in this phase added to that.

## 4. Final configuration and why it is kept

**C0 = P0H4-U:**
- one unified LightGBM, trained on the rows of all 15 leads at once;
- monotone on the food-price projection;
- inner chronological selection among 8 small configurations, including class weighting;
- the 21 columns of the 12 indicator families plus world prices;
- times the hunger condition from the newest SWS reading, re-issued after each SWS release for Leads ≥ 2.

It is kept because, under the frozen rule, no candidate lowered the Lead-2 DEV Brier by at least 0.005 without harming Lead 1. It is served only with `AIPHEED_CH1_ENGINE=fr`. Making it the default needs your approval.

## 5. Five trigger groups: measured contribution (`out/ablation.json`)

**Method.** Leave-one-group-out walk-forward refits.
- **Δ** = change in risk-probability Brier when the group is removed, with a 90% quarter-block CI. **Positive means the group helped.**
- **SHAP** = relative model influence, not a contribution.

| Group (indicators) | Δ Lead 1 | Δ Lead 2 | SHAP share | Verdict |
|---|---|---|---|---|
| **Market / Prices** (food CPI projection, headline inflation, rice, world prices) | **+0.052** [+0.022, +0.088] | **+0.037** [+0.009, +0.063] | 0.62 | Measurable at Leads 1-3. The forecast depends on it. |
| **Climate** (El Niño status, typhoons, harvest change, fertilizer price) | −0.007 [−0.017, 0.000] | **−0.005** [−0.010, −0.001] | 0.04 | Not established. At Lead 2 it adds slightly more noise than information. |
| **Employment** (LFS unemployment change, national) | **+0.005** [+0.001, +0.013] | +0.003 [−0.001, +0.009] | 0.07 | Small effect at Lead 1 only. It mostly tracks the calendar (ρ +0.96 with time), so it is not read as job conditions. |
| **Fish production** (PSA fisheries production) | +0.003 [−0.000, +0.008] | −0.001 [−0.008, +0.007] | 0.05 | Small effect at Lead 3 only (+0.006). Not established at Leads 1-2. |
| **OFW remittances** (BSP, national) | +0.0001 | 0.0000 | 0.00 | The model almost never uses it. Negligible. |
| *All five removed* | **+0.067** [+0.033, +0.104] | **+0.046** [+0.012, +0.081] | — | The triggers collectively help, almost entirely through Market |

**Other required inputs (not triggers).**

| Input | Effect when removed |
|---|---|
| News / NLP | Helps at Lead 1 (+0.011); slightly better *without* it at Lead 2 (−0.007) |
| Poverty | Not established |
| Hunger outlook inside the price model | Not established |

**Why the smaller groups contribute little:**
- Employment, OFW remittances, El Niño status and GDELT news are **national series**. They have no difference between provinces, so they can only shift whole quarters (about 20 observations).
- The realised typhoon and harvest information arrives **in the target quarter itself**.
- Employment **follows the calendar**.
- The **sample is small**: minimum detectable effects are 0.004-0.04 Brier.

No defect was found that kept a group out of the model. Each group's columns change the predictions when removed.

> Correlated indicators share importance (for example, world rice and the CPI projection). A single importance number does not establish a group's full contribution, which is why the held-out removal test is the primary evidence and SHAP is shown only as influence.

## 6. Leakage check

- Each origin uses PSA CPI through month 2 of the origin quarter, SWS rounds published before the issue date, and news published before the issue date. All are verified for every row (`input_audit.json`).
- Training rows have targets that were known before the origin.
- Selection, class weighting and calibration use only inner folds made of earlier origins.
- The schedule-B re-issue uses only SWS rounds published before its issue date (FR `checks.json`).

## 7. Dashboard (backend only; no design change)

- **The five trigger cards are the approved ones:** Market / Prices, Climate, Employment, Fish production, OFW remittances.
- **Each card's text now adds:**
  - the group's inputs;
  - a sentence generated from the held-out test, for example "leaving this group out made the forecasts worse one quarter ahead and made the forecasts worse two quarters ahead. Its contribution is measurable."
- **No direction is stated where the evidence does not support one.**
- Lead-2 rows keep "experimental: failed the reliability test".
- **Files:** `backend/data/ch1_trigger_evidence.json` (from `runner/export_evidence.py`); `ch1_system.trigger_evidence()` and `plain_evidence()`.
- **Tests:** `test_five_trigger_evidence.py` (3 new); `test_system_fixes.py` updated for the appended sentence.

## 8. Remaining failures and limits

- **Lead 2 fails R6 by one HIGH case.** Do not call it reliable.
- **No validated food-insecurity outcome exists** (OUTCOME_GAP_RESOLUTION: NOT EVALUABLE). Lead 2 predicts the Chapter I proxy class.
- **The sealed forecasts** (a498b5ef, bd6572e1, b7162a63) are the only clean test, from January 2027.

## 9. Thesis-ready summaries

**Methodology.**
- aiPHeed forecasts the Chapter I risk class of each CALABARZON province: HIGH when Balance Luzon SWS hunger exceeds 11.3% and the province's food inflation, or food minus headline inflation, exceeds its 2021-22 60th percentile.
- **Price part:** one LightGBM trained on all forecast horizons together. It uses 12 indicator families grouped into the five proposal triggers (Market/Prices, Climate, Employment, Fish production, OFW remittances), plus news, poverty and the regional hunger outlook. It is refitted at every quarterly issue date on data published before that date.
- **Hunger part:** the probability that hunger stays above 11.3%, from the newest SWS reading and its past movements. Forecasts two or more quarters ahead are re-issued the day after each SWS release.
- **Risk probability:** the product of the two parts.

**Evaluation.**
- **Method:** rolling-origin evaluation over 2023-2026. Seven pre-set criteria (R1-R7), compared with persistence, climatology and always-LOW.
- **Lead 1** passed every criterion: accuracy 0.843, HIGH recall 0.65, Brier 0.132.
- **Lead 2** reached accuracy 0.800 and Brier 0.167, better than persistence (p = .03). It did not pass R6, because HIGH recall was 0.59 against the required 0.60.
- **Five-trigger ablation:** the triggers together improve the forecasts (Lead-2 Brier +0.046 when all are removed), mainly through Market / Prices. The other four groups' individual effects were small or not established with the data available.
- All results are development evidence. The sealed prospective forecasts will provide the first independent test.
