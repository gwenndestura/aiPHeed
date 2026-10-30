# E114: can aiPHeed genuinely forecast food insecurity? (PROTOCOL_E114, frozen c3e5624 before scoring)

**Branch.** `aiPHeed/e114-genuine-forecast` (local only).
**Runner.** `runner/run_e114.py`, seed 114. **Outputs.** `out/e114_results.json`, `out/e114_rows.csv`.
**Data hashes.** In `e114_results.json` → `data_sha256`.

**Unchanged.** The served model, the dashboard, the T43c benchmark, R1-R7 and the seals.

## 1. Answer

**Decision under the frozen protocol: the success criteria (§5) fail at both leads.** In plain terms:

1. **Persistence can be beaten as a level forecast.**
   - On the untouched test quarters (2013-2020, 30 quarters × 4 areas, never scored before), the unified LightGBM forecasts the *change* in hunger with lower squared error than carrying the latest reading forward:
     - Lead 1: MSE 34.9 vs 40.0, Diebold-Mariano p = 0.006;
     - Lead 2: MSE 34.0 vs 37.8, p = 0.038.
   - The gain holds in Balance Luzon and in both halves of the test period.
   - So aiPHeed *can* make a genuine two-quarter-ahead hunger forecast that is not the carried-forward reading.
2. **The gain does not come from the five trigger groups.**
   - It comes from hunger's own history: removing the hunger-history inputs raises Lead-2 test MSE by +6.3 (90% CI +1.2 to +12.1). Hunger tends to return toward its long-run level.
   - The market, climate, employment and news inputs add nothing measurable on the untouched quarters. News makes the forecast slightly worse.
   - A plain damped mean-reversion rule, one of the pre-declared comparators, beats the LightGBM: Lead-2 test MSE 27.0 vs 34.0.
3. **The probability of HIGH has no skill.**
   - For "above the usual level" at Lead 2, the LightGBM's Brier score (0.254) is no better than persistence (0.243) or climatology (0.250).
   - Its balanced accuracy is 0.594, against persistence's 0.614.
   - The model is over-confident (calibration slope 0.48) and over-predicts HIGH (predicted rate 0.54 vs observed 0.41).
   - **Criterion 3 fails at both leads; criterion 4 fails at Lead 2.**
4. **Everything is regional.** No provincial hunger or food-insecurity outcome exists. The data support a forecast for Balance Luzon (the SWS area that contains CALABARZON), not for the five provinces separately.

## 2. Target audit

| Question | Finding |
|---|---|
| What is SWS hunger? | % of families who experienced involuntary hunger at least once in the past 3 months. This is **experienced hunger, the severe end of food insecurity**, not the broader concept (moderate-or-severe food insecurity, e.g. FIES). |
| Is 11.3% defensible? | **No, as a threshold.** It is the 60th percentile of only 6 Balance Luzon quarters (2021-22), the lowest-hunger stretch on record. The 1998-2026 median is 13.8%, and 66% of all quarters exceed 11.3%. SWS publishes no such threshold. It is kept only for continuity with T43c. The primary event here is "above usual", meaning above the area's median of readings published before the issue date. |
| Regional or provincial? | **Regional only.** One Balance Luzon value per quarter is currently copied to all five provinces in T43c. That is one observation, not five, and it is never treated as five here. |
| What the current T43c measures | Regional hunger *and* provincial food-price pressure (a proxy). Not provincial food insecurity. |

## 3. Design (point-in-time)

**Training data.**
- Four SWS areas (NCR, Balance Luzon, Visayas, Mindanao), 1998-2026, 106 quarters.
- One LightGBM regressor, pooled over areas and leads, predicts y − latest reading.
- Its configuration is chosen at each origin by inner chronological folds.

**Inputs, all available before each issue date:**
- **SWS readings:** only rounds already published. The pre-2021 publication date is a rule (month end + 60 days); a +100-day sensitivity is reported.
- **Market:** national food CPI, its change, rice CPI.
- **Climate:** ONI, typhoon count change, palay.
- **Employment:** unemployment change, 2005+.
- **News:** GDELT supply and assistance, 2018+.

**Leakage checks.** These are asserted in the run; it stops if any fails:
- every training target was published before the issue;
- every latest reading equals the mean of the rounds published before the issue (it has to be checked this way, because some quarters have two rounds);
- σ is estimated from each model's own earlier errors only;
- "usual" is computed from known readings only.

**Splits.**

| Split | Targets | Status |
|---|---|---|
| DEV | 2003-12 | — |
| TEST | 2013-20 | untouched, scored once |
| SECONDARY | 2021-26 | inspected before (E109-E113) |

## 4. Results

**Lead 2, test period (2013-2020), 120 rows, 30 quarters; 49 "above usual" rows.**

| Model | MSE | MAE | BL MSE | Δ MSE vs persistence (90% CI) | DM p | "Above usual" Brier | Accuracy | Balanced accuracy | Precision | Recall | F1 | Calibration slope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Unified LightGBM** | 34.0 | 4.50 | 22.1 | −3.8 [−7.5, −0.2] | 0.038 | 0.254 | 0.583 | 0.594 | 0.49 | 0.65 | 0.56 | 0.48 |
| Persistence (latest reading) | 37.8 | 4.56 | 31.2 | – | – | 0.243 | 0.625 | 0.614 | 0.54 | 0.55 | 0.55 | 0.38 |
| Damped mean reversion | **27.0** | **3.97** | 20.9 | −10.8 [−19.2, −3.2] | 0.038 | **0.233** | 0.600 | 0.592 | 0.51 | 0.55 | 0.53 | 1.62 |
| AR(1) | 28.5 | 4.11 | 22.2 | −9.3 | 0.086 | 0.246 | – | 0.565 | – | 0.69 | – | – |
| Climatology (known mean) | 29.9 | 4.27 | 22.6 | −7.9 | 0.163 | 0.250 | 0.542 | 0.540 | 0.45 | 0.53 | 0.49 | 0.01 |
| Ridge (same inputs) | 33.5 | 4.58 | 25.6 | −4.4 | 0.141 | 0.251 | – | 0.606 | – | 0.78 | – | – |

**Lead 1, test period.**
- LightGBM MSE 34.9 vs persistence 40.0 (p 0.006); damped 28.1; ridge 26.4.
- "Above usual" Brier 0.247 vs persistence 0.244.

**Secondary period, 2021-26 (inspected before), Lead 2.**
- LightGBM MSE 43.8 vs persistence 47.5 (p 0.19, not significant); damped 34.4.
- Persistence classifies best: balanced accuracy 0.736, Brier 0.194.

**At 11.3%.** At Lead 2 on the test period, every model's call is close to always-HIGH (balanced accuracy 0.50-0.61), because 68% of test quarters are above 11.3%.

**Robustness.**
- **+100-day release rule.** LightGBM still beats persistence: Lead 2 MSE 38.6 vs 41.4.
- **Training frozen at pre-2013 targets.** LightGBM loses to persistence (Lead 2: 42.4 vs 37.8). The skill depends on retraining as new readings arrive.

## 5. Trigger-group contributions (test period; refit without each group; Holm over 5)

**Δ MSE when the group is removed** (positive means the group helps):

| Group | Lead 1 Δ MSE [90% CI] | Lead 2 Δ MSE [90% CI] | Lead 2 Holm p | Reading |
|---|---|---|---|---|
| Hunger history | +7.8 [+3.4, +12.4] | +6.3 [+1.2, +12.1] | 0.16 (L1: 0.036) | the only source of skill |
| Market / food prices | −1.3 [−3.0, +0.2] | +0.2 [−1.3, +1.7] | 1.0 | not established |
| Climate | +0.0 | +0.5 [−0.8, +1.9] | 1.0 | not established |
| Employment | −0.9 | +0.1 [−1.2, +1.4] | 1.0 | not established |
| News / NLP | −1.6 [−3.1, −0.3] | −1.4 [−3.4, 0.0] | 1.0 | possible noise |
| Poverty / vulnerability and remittances | – | – | – | **not representable:** no point-in-time regional series in the repository |

**Why the trigger groups add nothing here:**
- **Market, climate and employment** are national series: one value per quarter, shared by all four areas.
- **News** exists only from 2018, so it covers only the last third of the test period.
- **Poverty and remittances** have no dated history at all.

These are data limits. Nothing was fabricated or inflated to make the groups look important.

## 6. What the data support

| Claim | Supported? |
|---|---|
| aiPHeed can forecast the *level* of regional hunger 1-2 quarters ahead better than carrying the latest reading forward | **Yes**, on untouched quarters. But a simple damped mean-reversion rule does it better than the LightGBM. |
| The five trigger groups drive that forecast | **No.** Only hunger history does. |
| aiPHeed can forecast whether hunger will be HIGH ("above usual" or > 11.3%) two quarters ahead | **No.** No skill over persistence or climatology. |
| Provincial food-insecurity forecasts | **No.** There is no provincial outcome. Provinces can only get a vulnerability and price-pressure profile, clearly labelled as such. |
| Lead 2 reliable for the thesis T43c target | **No** (as established in LEAD2_FINAL_SIGNAL). |

## 7. Integration

**Nothing was integrated into the dashboard,** because the frozen criteria failed.

**A defensible next step needs your approval:**
- Show the regional hunger outlook as a *level forecast with a band*. The best evidenced method is damped mean reversion. With LightGBM, damped mean reversion would have to be supplied as an input or baseline.
- Score that outlook prospectively on SWS rounds after the freeze.
- Show provincial vulnerability separately, without a forecast probability.

Any such change keeps the approved UI design and colours.
