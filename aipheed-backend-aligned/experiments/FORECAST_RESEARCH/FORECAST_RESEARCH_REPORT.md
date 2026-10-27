# FORECAST_RESEARCH: what limits aiPHeed's forecasts, what was tried, and what was implemented

**Branch:** `aiPHeed/forecast-research`, cut from `aiPHeed/system-fixes` at 2fb7c8b. Local only: not pushed, not deployed.
**Date:** 2026-10-27.
**Protocol:** `PROTOCOL_FORECAST_RESEARCH.md`, SHA-256 `1974fae6`, committed in c8e9a18 before any arm was scored. Addendum 1 (`b83e2d5b`) and Addendum 2 were each hashed before scoring.
**Sources:** `SOURCES.md` (S1-S18). Every citation below points to it.

**Served model is unchanged.** P0H4 is still served, with seal a498b5ef. The candidate built here, P0H4-U, is served only when the backend is started with `AIPHEED_CH1_ENGINE=fr`.

---

## 1. Summary

1. **What limits each lead (verified).** The served label (T43c) is HIGH only when two things hold together:
   - regional SWS hunger is above 11.3;
   - the province's food price condition is met.

   Since 2023-Q4, hunger has been above 11.3 in every quarter. So for three years the label has been decided by the price condition. Two separate defects limit the forecasts:
   - **SWS publication lag (hunger part).** At the quarter-start issue date the newest SWS reading is two quarters old in 13 of 14 quarters, because SWS publishes 13-83 days after the quarter ends. This alone caps Lead-2 HIGH recall at 0.41.
   - **No usable signal for future price movement (price part).** The flat base-effect projection of food CPI already carries most of the price signal: AUC 0.93 / 0.82 / 0.88 at Leads 1-3. Learned corrections from the 12 indicator families make it **worse** at every lead (§5). The projection's error grows with the lead (RMSE 1.9 → 3.5 points) and its bias reverses between inflation regimes.
2. **What helped.** Issuing the Lead-2 forecast the day after SWS publishes (schedule B, a median 59 days before the target quarter) raised Lead-2 results under every price part tested. With the served price part (P0H4 → P0H4-U):

   | | Quarter-start issue | Schedule B |
   |---|---|---|
   | Accuracy | 0.769 | 0.800 |
   | Balanced accuracy | 0.635 | 0.732 |
   | HIGH recall | 0.35 | 0.59 |
   | Brier | 0.194 | 0.167 |

   The Brier gain is −0.027, two-sided p = .09.
3. **What did not help.** None of these improved the forecasts on held-out rows:
   - a bias-corrected projection at longer leads;
   - ridge corrections;
   - a unified LightGBM regressor on the projection error;
   - any single input family added to or removed from it.
4. **Reliability verdict (unchanged).** The maximum reliable lead is still **1**.
   - Lead 2 under schedule B fails one criterion for each price part:
     - P0H4-U fails R6, with recall 10/17 = 0.59 (one row short);
     - the structural Z0 and the LightGBM P4 fail R5 (not significantly better than climatology, p = .20).
   - Lead 2 under the quarter-start issue fails 3 criteria. Leads 3-4 fail 5-6.
5. **Implemented.** Candidate P0H4-U is integrated behind a flag, with tests and a new prospective seal `bd6572e1`. It is the served LightGBM forecast with the Lead-2+ hunger part re-issued after each SWS release.
   - Backend: 890 passed, 18 skipped. Frontend: 83/83.
   - Verified in the dashboard: the Quezon 2027-Q1 panel shows 0.12, which equals the export.
6. **Not validated.** No result here is a clean test (§3.3). The forecasts sealed today are the only clean evidence, and they can be scored only after SWS publishes 2026-Q4 (expected January 2027).

---

## 2. Verified diagnosis (Mission 1)

### 2.1 Raw data to dashboard (traced)

1. **Data.** PSA CPI (monthly, by province), SWS rounds, and the other 10 families are read through `E41 Data.cut(t)`, which keeps only data published before the issue date O(t) = day 1 of quarter t+1.
2. **Features.** `E107.feature_table` builds the inputs. In particular, A1 is the projected food YoY of the target quarter with the latest index held flat. The CH1, UNI and LEAD2 layers add SWS dynamics, world prices and news.
3. **Price part.** The price part π_P is one LightGBM across leads (UNI-FINAL, `P0_price`). The hunger part π_H is `a3.h4`: the newest BL reading, with σ pooled over four SWS areas.
4. **Output.** The forecast is P = π_H × π_P. `export_l2.py` writes it to `backend/data/ch1_engine/rows.csv`, which `ch1_system.py` serves to the API and dashboard.
5. **Reproduced.** π_H and the structural price part are reproduced here to within rounding: max |Δ| = 5e-7 (`out/audit.json`).

### 2.2 Answers to the Mission-1 questions

| Question | Finding | Evidence |
|---|---|---|
| Why are the forecasts not consistently strong? | The label has two parts. The hunger part is regional and noisy near 11.3 (8.7-11.8 in 2022-23). The price part depends on future price movements that no input predicts (§5). | Label table in `out/baseline_record.json`; oracle table §4.3 |
| Why does performance fall at longer leads? | (a) The known share of the target-quarter YoY window shrinks: 2-4 unknown months at Lead 1, 5-7 at Lead 2, 8-10 at Lead 3. Projection RMSE rises from 1.9 to 3.5 points. (b) At Lead 2 the hunger reading is three quarters old. (c) Every learned correction overfits the 2022-23 inflation regime. | `results.json` continuous; FR1 |
| Are the labels genuine food-insecurity risk? | Partly. The hunger term is an experienced-hunger (access) measure, but regional. The price term is an affordability pressure, not observed food insecurity (S1, S2). T43c is a composite proxy. No provincial food-insecurity outcome exists for 2021-26. | §7 |
| Shortcuts? | The served P0 price part has AUC 0.67 against the projection's 0.93. Its LightGBM leans on E1 (calendar-time confound, ρ +0.95 with time; LEAD2_OPTIMIZATION) and on V1 (a province identifier, BIAS_AUDIT). Its skill comes almost entirely from π_H. | `baseline_record.json` price component |
| Missing or poorly represented indicators? | FSSI-v3 news (N1) is missing in 80% of rows. E2 stops at 2025-Q4. A3 is missing in 9%. No provincial hunger outcome. | `contributions.json` coverage |
| Enough independent observations? | No. About 70 rows per lead, but the province rows within a quarter are correlated (ICC ≈ 0.3). Effective n ≈ 30. Only 7 quarters contain any HIGH row. Per S9, that supports only a few free parameters. | `results.json` n_eff |
| Are the low probabilities justified? | Mostly. Since 2025-Q4 the price condition has been met in only one province-quarter (Cavite 2026-Q2), and the projections of current food inflation are below the thresholds. The served P0H4 is under-confident at Lead 1 (calibration slope 1.98: its probabilities are compressed towards the mean). | calibration in `results.json` |
| Are earlier high accuracies reproducible and better than baselines? | Lead-1 values reproduce: P0H4 0.843, S3 0.857, structural 0.886-0.900. All beat persistence (p < .05). None beats any other candidate significantly. CH1-LGBM's 0.914 is per-lead and was not re-run here. Every quarter was examined repeatedly, so these figures are development figures. | §4 |

### 2.3 Earlier experiments: what helped and what did not

| Helped | Did not help |
|---|---|
| The structural projection (E108 STRUCT, LEAD2 P4/P5) | Pre-2021 data (out of scope) |
| Pooled-area σ for π_H (H4) | FSSI news (F1 gain, no forecast gain) |
| Product-rule framing (CH1) | Climate representations (failed placebo) |
| | Calibration fitted in-fold |
| | Seasonal drift (U6) |
| | Hunger LightGBMs (E109-E113, HG): no model beats the latest SWS reading |

---

## 3. Research basis (Mission 2)

### 3.1 Principles adopted

| Decision | Principle | Source |
|---|---|---|
| Rolling-origin evaluation, scored by lead | Forecasts are tested only on later data; error grows with horizon | S4, S5 |
| Brier and log loss primary, accuracy secondary | Strictly proper scores reward honest probabilities | S6 |
| No calibrator fitted on outcomes; reliability reported separately | Calibration must use data disjoint from training; isotonic regression overfits small samples | S7, S8 |
| Model the continuous price error, threshold only at the end | Dichotomising loses information and power | S3 |
| Persistence and the no-change projection are mandatory baselines | Naive inflation forecasts are hard to beat | S10, S12 |
| Shallow, regularised trees; few free parameters | Small samples need limited complexity | S9, S14 |
| Shared multi-horizon model compared with per-lead fits | Multi-step strategies differ | S11 |
| Family value by refit ablation, permutation and SHAP, read as model influence | Importance is model-specific; correlated features share it | S15, S16 |
| Price shocks from policy treated as unforecastable | EO 62 (rice tariff cut, June 2024) | S17 |

### 3.2 How the claims are classified

| Class | What it covers |
|---|---|
| Published research | S1-S16, as listed in SOURCES.md, only for the principle stated there. |
| Philippine context | S17 (EO 62). PSA and SWS timing from repository records (S18). |
| aiPHeed experiments | Everything in §4-§6. |
| My own hypotheses | Marked as such where they appear (e.g. the ENSO signal in §6.3). |

### 3.3 Honesty note on test data

Every 2021-26 quarter has been inspected by more than 100 earlier experiments. So no 2021-26 result is clean, and that includes this one. The DEV/CONF split was used only for selection discipline. The prospective seals in §9 are the only clean test.

---

## 4. Experiment log (Mission 3, 4)

| ID | Question | What changed | Result | Decision |
|---|---|---|---|---|
| FR0-a (diagnostic) | Is the flat projection biased? | — | Mean error +1.1 / +2.2 / +3.2 / +4.3 points at Leads 1-4. It is negatively related to the current inflation level (mean reversion). | Motivated Z1-Z3 |
| FR0-b (diagnostic) | Does SWS timing matter? | Lead-1 π_H recombined with Lead-2 price | Lead 2: 0.754 → 0.800 | Motivated schedule B |
| FR1 | Which part limits each lead? | 2×2 oracle (§4.3) | Schedule A Lead 2: both parts limit. Schedule B Lead 2: price only (0.938 with the true price). Leads 3-4: price. | — |
| FR2 Z0 | Flat projection | No learning | L1 0.900 / Brier 0.116; L2 0.754 | Structural benchmark |
| FR2 Z1 | Bias correction by lead | Training-mean error | L1 0.900 / 0.124. **Overshoots in 2025** (bias −0.8 to −2.4). L4 0.418. | Selected under A by the dev rule (dev Brier 0.169). Lead 1 only. |
| FR2 Z2 | Ridge on all 12 families | Corrections | Continuous RMSE worse than Z0 at every lead (3.5 vs 1.9 at L1) | Rejected |
| FR2 Z3 | Unified LightGBM regressor, 12 families | Corrections | Worse than Z0: price Brier +0.07 to +0.12 at every lead (p > .99); L1 0.786 | Rejected. LightGBM adds no development value. |
| FR3 | Schedule B | Hunger part only | Lead 2 improves for every price part (Z0 0.754 → 0.800; P0 0.769 → 0.800). Lead 1 worsens, because the reading published just before the issue near the 11.3 line is noisy. | B used for Leads ≥ 2 only: a B Lead-1 forecast is issued after its quarter has started, so it gives no warning. |
| Add. 1 P4 | LightGBM boosted from the projection | init_score = Z0 | All rows: L1 0.871 / Brier 0.115; L2 (B) 0.800 / 0.183. Dev Brier 0.010 worse than the selected arms. | Not adopted by the rule. Reported as the best LightGBM form. |
| Add. 2 | Family contributions | Add-one, leave-one-out, permutation, SHAP | §6 | No family adds value |

### 4.1 Results by lead (evaluation rows: Lead 1 = 70, Lead 2 = 65, Lead 3 = 60, Lead 4 = 55)

Accuracy has a 90% quarter-block CI. **Bold** = passes R1-R7.

| Model | Lead 1 | Lead 2 | Lead 3 | Lead 4 | Max reliable lead |
|---|---|---|---|---|---|
| Always LOW | 0.757 | 0.738 | 0.717 | 0.691 | – |
| Persistence (same information) | 0.743 | 0.677 | 0.567 | 0.545 | – |
| P0H4 (served) | **0.843** [0.76, 0.91] | 0.769 | 0.717 | 0.673 | 1 |
| Z0 structural (A) | **0.900** [0.83, 0.97] | 0.754 | 0.683 | 0.673 | 1 |
| Z1 bias-corrected (A, selected) | **0.900** [0.83, 0.96] | 0.708 | 0.617 | 0.418 | 1 |
| Z3 unified LightGBM (A) | 0.786 | 0.646 | 0.550 | 0.400 | 0 |
| P4 LightGBM from projection (A) | **0.871** [0.79, 0.94] | 0.769 | 0.700 | 0.618 | 1 |
| Z0 (B, selected) | **0.871** | 0.800 [0.71, 0.89], fails R5 | 0.633 | 0.564 | 1 |
| P4 (B) | **0.871** | 0.800, fails R5 | 0.633 | 0.600 | 1 |
| **P0H4-U** (Lead 1 from A, Lead 2+ from B) | **0.843** | 0.800 [0.71, 0.89], fails R6 | 0.633 | 0.673 | 1 |

### 4.2 HIGH detection, false alarms and misses

| Model | TP | FP | FN | TN | Precision | Recall | Brier | Log loss | AUC |
|---|---|---|---|---|---|---|---|---|---|
| P0H4, Lead 1 | 11 | 5 | 6 | 48 | 0.69 | 0.65 | 0.132 | 0.418 | 0.87 |
| Z1, Lead 1 | 14 | 4 | 3 | 49 | 0.78 | 0.82 | 0.124 | 0.423 | 0.92 |
| P0H4, Lead 2 (A) | 6 | 4 | 11 | 44 | 0.60 | 0.35 | 0.194 | 0.576 | 0.62 |
| **P0H4-U, Lead 2 (B)** | 10 | 6 | 7 | 42 | 0.62 | 0.59 | 0.167 | 0.502 | 0.76 |
| Z0, Lead 2 (B) | 11 | 7 | 6 | 41 | 0.61 | 0.65 | 0.184 | 0.549 | 0.72 |

**Cost of the trade.** At Lead 2, schedule B turns 4 missed HIGH province-quarters into hits, at a cost of 2 more false alarms (P0H4 → P0H4-U). For an early-warning screen, a missed warning usually costs more than one extra check, but that weighting is DA's call.

**Baselines (Brier, one-sided quarter-block bootstrap).**

| Comparison | Lead 1 | Lead 2 (B) |
|---|---|---|
| P0H4-U vs persistence | p = .02 | p = .03 |
| P0H4-U vs climatology | p = .03 | p = .08 |
| Z0 (B) vs climatology | — | p = .20 (the reason it fails R5) |

No candidate is significantly better than P0H4 at Lead 1: Z0 vs P0H4 Δ = −0.016, p two-sided = .45.

### 4.3 Oracle decomposition (accuracy, with recall in brackets; structural price part)

| Lead | Forecast × forecast (A) | True hunger × forecast price | Forecast hunger (A) × true price | Forecast hunger (B) × true price |
|---|---|---|---|---|
| 1 | 0.900 (0.76) | 0.929 (1.00) | 0.943 (1.00) | 0.814 (0.82) |
| 2 | 0.754 (0.41) | 0.677 (0.65) | 0.815 (0.59) | **0.938 (1.00)** |
| 3 | 0.683 (0.41) | 0.733 (0.94) | 0.983 (0.94) | 0.800 (0.59) |
| 4 | 0.673 (0.18) | 0.545 (0.71) | 0.818 (0.41) | 0.982 (0.94) |

**Reading.**
- Once the SWS lag is removed (B), Lead 2 is limited by the price forecast. With the true price it would reach 0.938.
- Combining the true hunger term with the forecast price makes Lead 2 *worse* (0.677). The Lead-2 price probabilities are over-dispersed (calibration slope 0.43 under A), and the hunger factor shrinks them.

### 4.4 Why Lead 2 still fails, and what would fix it

| Cause | Evidence | What would be needed |
|---|---|---|
| Future food-price movement is not predictable from the 2021-26 indicators | Z2, Z3 and every add-one family are worse than no correction. The 2024-25 turn came from a policy (EO 62, S17) and world rice prices. | Another inflation cycle of data; official price outlooks (BSP inflation forecasts, DA rice supply outlook) as inputs |
| Only 7 HIGH quarters | n_eff ≈ 29 at Lead 2 | Time: each new quarter adds about 1 effective observation |
| R5/R6 are borderline | Z0 vs climatology p = .20; P0H4-U recall 10/17 | Prospective quarters (sealed) |

---

## 5. Final architecture, target and training (Mission 3, 6)

**Target (unchanged).** T43c = [SWS Balance Luzon hunger > 11.3] AND [the province's food YoY > its 2021-22 P60, OR food minus headline YoY > its gap P60].
- It is a **composite proxy**: an experienced-hunger term that is regional, and a provincial affordability pressure.
- No target was changed, because no independent provincial food-insecurity outcome exists to justify a change (S1).

**Candidate P0H4-U (implemented).**
- **Price part π_P.** One LightGBM trained on the rows of all leads together, on all 12 families, the lead, and world prices. It is unchanged from the served P0H4 and refitted at each origin on the rows whose outcomes were known.
- **Hunger part π_H.** Φ((newest BL reading − 11.3)/σ_h), with σ_h = RMSE of the newest-reading errors at that true horizon, pooled over the four SWS areas.
- **Issue.**
  - Lead 1: day 1 of the quarter.
  - Leads ≥ 2: re-issued the day after SWS publishes the previous quarter's BL hunger reading, at the latest on day 1 of the quarter's third month. Only π_H changes; every other input keeps its quarter-start cut-off.
- **Forecast.** P = π_H × π_P. HIGH when P ≥ 0.50.

**Why not the structural Z0/Z1.**
- The thesis requires a LightGBM model.
- The best LightGBM form (P4, boosted from the projection) does not differ significantly from Z0 at any lead.
- The served P0 price part does not differ significantly from Z0 at Lead 1 (p = .45) or Lead 2 (p = .66).
- Switching price parts would cost the thesis's required model for no demonstrated gain. Z0/Z1 are reported as the strongest simple benchmark.
- If the adviser accepts a non-LightGBM price part, Z0 is the evidence-preferred choice: Lead 1 0.900, and its probabilities are the simplest to explain. Z1 is not recommended beyond Lead 1, because its bias correction overshoots at Leads 3-4 (0.42 at Lead 4).

---

## 6. Input-family contributions (Mission 5)

All Δ values are held-out refits on the same rows.
- **Add-one:** the Z3 model on one family + lead, compared with Z0 (no correction).
- **Leave-one-out:** the Z3 model without one family, compared with Z3-full.

| Family | Coverage (missing) | Add-one: price Brier Δ vs Z0, L1 / L2 / L3 | Add-one, food error vs a lead-only model (post-hoc) | Leave-one-out from Z3 | Permutation (Z3 fixed) | Verdict |
|---|---|---|---|---|---|---|
| A1 food CPI (base) | 0% | Removing the base: T43c Brier +0.057 at L1 (A), +0.071 (B) | — | — | — | **Predictive as the projection base, Lead 1** (CI lower bound 0.000 under A, excludes 0 under B). Its extra columns add nothing. |
| H1 SWS hunger (π_H) | 0% | Removing π_H: +0.033 at L1 (A), CI includes 0 | — | — | — | **Carries the label's hunger part.** Not significant alone, because hunger stayed above 11.3 throughout 2024-26. |
| A2 headline / oil | 0% | +0.051 / +0.041 / +0.074 | Lower at L2-4 (p ≤ .04) | +0.003 to +0.008 | ≈ 0 | Weak (food error only; the price term is worse) |
| A3 rice | 9% | +0.016 / +0.019 / +0.108 | Worse | −0.004 to −0.019 (removing it helps) | Negative at L2-4 | No demonstrated value |
| V1 poverty | 0% | +0.028 / +0.045 / +0.095 | Worse | ≈ 0 | 0 | No value (static province identifier) |
| C1 ENSO | 0% | +0.025 / +0.010 / +0.013 | Lower at L3-4 (p ≤ .02) | ≈ 0 | ≈ 0 | Weak. **Hypothesis:** an ENSO-to-food-price link 2-3 quarters ahead, seen in one El Niño episode only. |
| C2 typhoons | 0% | +0.011 / +0.017 / +0.051 | n.s. | ≈ 0 | ≈ 0 | No demonstrated value |
| C3 harvest / fertilizer | 0% | +0.045 / +0.044 / +0.095 | n.s. | Removing it helps | Negative | No demonstrated value |
| C4 fisheries | 0% | +0.037 / +0.040 / +0.093 | Worse | ≈ 0 | ≈ 0 | No demonstrated value |
| E1 unemployment | 0% | +0.048 / +0.058 / +0.110 | Worse (p ≥ .97) | ≈ 0 | Small positive | No value (calendar-time confound) |
| E2 remittances | 0% (stops 2025-Q4) | +0.083 / +0.054 / +0.145 | Worse | ≈ 0 | ≈ 0 | No demonstrated value |
| N1 news (FSSI-v3 + GDELT) | **80% missing** (N1) | +0.030 / +0.042 / +0.062 | n.s. | Removing it helps at L1-2 | Negative | No demonstrated value. Data coverage is the first problem. |

**Stability.**
- SHAP ranks of the Z3 food-error model are unstable across chronological thirds: Spearman 0.69 for thirds 1→2, 0.34 for 2→3, 0.00 for 1→3. A1 dominates the first third; A2 and A3 dominate the last.
- Correlated price families (A1, A2, A3, world prices) share influence, so their individual SHAP shares are not causal (S15, S16).

**For the dashboard.**
- The served bars show relative SHAP influence on the price part of P0H4's own LightGBM. They are labelled "Relative model influence", never causes.
- This study adds one finding: none of the non-price families improves held-out forecasts. Their bars describe what the model used, not what helped.

---

## 7. Calibration (Mission 4, 7)

| Model, lead | Calibration slope | Calibration-in-the-large | ECE |
|---|---|---|---|
| P0H4, Lead 1 | 1.98 (under-confident) | −0.07 | 0.12 |
| Z1, Lead 1 | 1.31 | −0.13 | 0.19 |
| P0H4-U, Lead 2 | 1.04 | −0.07 | 0.11 |
| P0H4, Lead 2 (A) | 0.47 (over-dispersed) | −0.03 | 0.14 |

These are diagnostics on the evaluation rows. Nothing was refitted to them (S7).
- All models under-predict the HIGH share slightly (calibration-in-the-large < 0).
- P0H4-U's Lead-2 probabilities are the best calibrated of the Lead-2 candidates.
- With n_eff ≈ 30, a binned reliability curve has 5-26 rows per bin, so calibration claims are weak (S8).

---

## 8. Methodology in plain words (matches the code)

1. **What it predicts.** Whether a province will be HIGH risk in a coming quarter: SWS hunger in Balance Luzon above 11.3% AND the province's food prices rising faster than their usual 2021-22 level. It is a risk class built from two signals, not a measured hunger rate for the province.
2. **Data.** PSA provincial CPI, rice prices, production, labour force, poverty and population; BSP remittances; PAGASA ENSO status; IBTrACS typhoons; SWS hunger; news (FSSI-v3, GDELT); World Bank world prices. Window: 2021 to 2026-Q3. Each value is used only after its publication date.
3. **How the 12 families are prepared.**
   - Food CPI: projected to the target quarter by holding the latest index flat (base effect).
   - The other families: their latest published change or level at the issue date.
   - Gaps stay blank, never zero.
4. **How it learns.** At every past issue date, a LightGBM model is trained on the earlier rows whose outcomes were already published. The rows of all leads are trained together, with the lead as an input. It estimates the chance that the price condition will hold. The hunger chance comes from the newest SWS reading and how much SWS readings have moved over the same span in the past.
5. **How each lead is made.**
   - Lead 1: issued on the first day of the quarter.
   - Lead 2 and beyond: re-issued the day after SWS publishes its newest hunger reading.
   - The forecast probability = hunger chance × price chance.
6. **How inputs are evaluated.** Each family is removed from, or added alone to, the model. The model is re-run on every past issue date, and the change in error on held-out quarters is measured. Shuffling and SHAP are used only as checks.
7. **How it is tested against baselines.** Always-LOW, persistence (same information), climatology, the structural projection and the earlier models, on identical rows. Brier differences use bootstrap resampling by quarter.
8. **How probabilities are read.** 0.50 or above = HIGH. Probabilities are scored with the Brier score and checked for calibration. They are never adjusted using the evaluation outcomes.
9. **How the maximum reliable horizon is chosen.** A lead is reliable only if it passes all seven pre-set criteria: enough quarters; accuracy ≥ 0.75; balanced accuracy ≥ 0.70; better than always-LOW and persistence; Brier significantly better than persistence and climatology; HIGH precision and recall ≥ 0.60; stable over time. The maximum is the longest lead for which it and every shorter lead pass.
10. **How it supports DA planning.**
    - Lead 1: a reliable (development-evidence) province risk class at the start of each quarter.
    - Lead 2: an earlier, experimental signal about two months before the quarter starts.
    - LGU numbers rank cities and municipalities within a province by poverty and density. They are not measured municipal forecasts.

---

## 9. Implementation and verification (Mission 8, 9)

### 9.1 Files changed or added

| File | Change |
|---|---|
| `backend/app/ml/inference/ch1_system.py` | `data_dir()` selects `ch1_engine_fr` only when `AIPHEED_CH1_ENGINE=fr`; `evaluation()` is cached per path; Lead-2 re-issue sentence (`sws_update_text`); model line and reliability sentences name P0H4-U only in that mode. The default output is unchanged. |
| `backend/data/ch1_engine_fr/rows.csv`, `evaluation.json` | New: the P0H4-U export |
| `backend/tests/integration/test_forecast_research.py` | New: 6 tests (default unchanged; only the Lead-2+ hunger part differs; seals; verdict; API = rows; text) |
| `.claude/launch.json` | New `api-fr` configuration |
| `aipheed-backend-aligned/experiments/FORECAST_RESEARCH/` | Protocol, addenda, sources, runners, outputs, this report |

### 9.2 Checks (`out/checks.json`, all passed)

- The scorer reproduces `predictions.csv` byte for byte.
- Under schedule B, no SWS round is used before its publication, and no issue date falls after the cap.
- The price parts are identical across schedules.
- No training row has a target after t−1.
- The export uses only SWS published before its issue date.

### 9.3 Tests

- Backend: **890 passed, 18 skipped** (884 + 6 new).
- Frontend: **83 passed**. No frontend file was changed.

### 9.4 Dashboard

The API was run with `AIPHEED_CH1_ENGINE=fr`.
- Q1 2027 regional average: 0.08, equal to the mean of the export (the served model shows 0.07).
- Quezon panel: 0.12, equal to `rows.csv`.
- `/forecast` gives verificationDate 2026-10-15, and its horizon label carries the re-issue sentence.
- The province panel's municipality list was empty in the local preview. This is independent of this change: the API returns 41 Quezon LGUs under both engines, and the basemap tiles failed to load locally.

### 9.5 Prospective seals (`out/PROSPECTIVE_SEAL.json`)

| Seal | Content | Issued |
|---|---|---|
| `bd6572e1` | P0H4-U Lead 2-4 rows | 2026-10-15 |
| `8a06a188` | Selected arms Z1 (A) and Z0 (B) | 2026-10-01 / 2026-10-15 |

The served seal `a498b5ef` is unchanged.

---

## 10. What remains unvalidated

- **Every 2021-26 figure is development evidence**, not an independent test.
- **No lead beyond 1 is reliable.** Lead 2 under schedule B is close: one criterion short.
- **No provincial or municipal food-insecurity outcome exists.** The province classes rest on a regional hunger series. The LGU ranking has never been checked against outcomes.
- **No family besides food CPI and SWS has shown held-out value**, and news data coverage is poor.
- **The validator-only rule is not met.** The user's rule of 2026-10-27 (PSA food CPI and SWS as validators, not inputs) is not satisfied by P0H4, P0H4-U, Z0 or Z1. All of them use both as inputs. Under that rule there is no reliable horizon (VALIDATOR_ONLY). This study followed the mission's instruction to keep all 12 families eligible. The choice between the two remains with the researcher and the adviser.

---

## 11. Readiness

| Use | Status | Condition |
|---|---|---|
| DA demonstration | **Ready** | Present Lead 1 as the development-validated horizon and Lead 2 as experimental. Explain the two-part label and that LGU numbers are a priority ranking. |
| Limited pilot | **Conditional** | After the sealed 2026-Q4 forecasts are scored (SWS release, expected January 2027), and only for Lead 1, as one input to DA's own assessment. |
| Operational deployment | **Not ready** | Needs: (1) prospective verification over several quarters; (2) an independent provincial outcome (e.g. CBMS or FNRI FIES) to validate the label; (3) a decision on the validator-only rule; (4) better news coverage. |

---

## Reproduce

Run from `FORECAST_RESEARCH/runner` with the backend venv:

```
python snapshot.py
python snapshot.py extra
python audit.py
python score.py
python addendum1.py
python contrib.py
python export_fr.py
python checks.py
```

`baseline.py` writes the baseline record.
