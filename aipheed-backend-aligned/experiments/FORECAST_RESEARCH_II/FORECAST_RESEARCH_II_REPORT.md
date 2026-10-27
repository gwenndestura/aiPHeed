# FORECAST_RESEARCH_II: the remaining forecasting problems

**Branch:** `aiPHeed/forecast-research` (continues from 32b368a). Local only: not pushed, not deployed.
**Date:** 2026-10-27.
**Protocol:** `PROTOCOL_FORECAST_RESEARCH_II.md`, SHA-256 `9b963b18`, committed in cf1b7f9 before any arm was scored or any test was run.
**Sources:** `SOURCES_II.md` (S19-S24) and `../FORECAST_RESEARCH/SOURCES.md` (S1-S18).

**Served model unchanged.** P0H4 is still served (seal a498b5ef). The FORECAST_RESEARCH candidate P0H4-U is unchanged (`AIPHEED_CH1_ENGINE=fr`, seal bd6572e1). This phase adds the research candidate **Z0-U**, served only with `AIPHEED_CH1_ENGINE=fr2`.

> **How to read every number below.** Every 2021-26 quarter had already been examined by earlier experiments, so all figures here are **development evidence**. The only clean test is the prospective seal in §9, which can be scored from January 2027.

---

## 1. Answer in brief

1. **The target is the first problem, not the model.**
   - T43c rebuilds exactly from PSA and SWS (100/100 labels).
   - Since 2023-Q4 it has been decided entirely by the food-price condition (55/55 rows).
   - In 2021-26, provincial food-price pressure moved *against* regional hunger: Spearman ρ = −0.38 at lag 0 and −0.37 at lag 1. The pre-registered construct test (T3) fails.
   - FNRI's FIES food-insecurity prevalence moved with SWS hunger, not with price pressure.
   - So T43c can support "a province faced unusual food-price pressure while regional hunger was high". It cannot support a claim that the province's food insecurity was high, or that it will be (§2).
2. **No new method beat the existing structural projection under the frozen rule.**
   - Eight pre-registered price arms were tested: random walk with drift, a BSP-target-anchored drift, a glide path, joint food/gap simulation, fat-tailed innovations, a fixed-weight combination, and a LightGBM boosted from the new base.
   - The DEV rule selected **Z0**, the flat projection already known from FORECAST_RESEARCH. LightGBM added no development value (LJ 0.0036 worse on DEV Brier).
   - Two new arms improved the forecast of the underlying price, but neither improvement carried through to the binary label (§5.2):
     - the anchored drift (J2) cut the continuous food-inflation error at Leads 3-4 by about a third (CI excludes 0);
     - the joint food/gap model (J0) lowered the price log loss at every lead.
3. **Best defensible candidate across leads: Z0-U.** It is the flat CPI projection × the served hunger term, with the P0H4-U issue schedule.

   | | Lead 1 | Lead 2 (re-issued after SWS) |
   |---|---|---|
   | Accuracy | 0.900 | 0.800 |
   | HIGH precision / recall | 0.81 / 0.76 | 0.61 / 0.65 |
   | Brier | 0.116 | 0.184 |
   | Result | Passes R1-R7 | Fails R5 only (not significantly better than climatology, p = .20) |

   - Leads 3-4 fail 6 of 7 criteria.
   - Z0-U is **not significantly different** from P0H4 or P0H4-U at any lead (two-sided p .45-.86).
   - **Maximum reliable lead: 1**, unchanged.
4. **Lead 2 is one criterion short under both candidates:**
   - P0H4-U fails R6 (recall 10/17);
   - Z0-U fails R5.
   - The one pre-registered procedure that passed Lead 2, online selection, did so only because of its default period. All six robustness variants fail (§5.3).
   - **Lead 2 is not demonstrated.**
5. **The 12 families.**
   - None adds held-out value in any form tested: as a LightGBM correction, as a one-parameter linear correction, or by removal or permutation.
   - Each failure has an identified cause (§6): national series with no provincial variation, coincident rather than leading information, a calendar-time confound, 79% missing news, and a model that sends every family to the price part even when its plausible channel is hunger.
   - The data are also too thin to detect the gains that remain plausible: the minimum detectable Brier gain is 0.004-0.04.
6. **Hard limits, as far as the evidence goes (§8).**
   - Label noise alone caps accuracy at about 0.95-0.96, so it is not the binding limit.
   - The binding limit is statistical power. Telling apart two candidates that differ by 0.02 in Brier would need **about 100-140 labelled quarters**; 2021-26 has 12-14 per lead.
   - The current data cannot choose among the candidates. Only new quarters and a provincial outcome can.
7. **Readiness:**
   - **Demonstration: ready**, with Lead 1 as the development-validated horizon.
   - **Pilot: not yet.** It needs a scored sealed quarter (from January 2027).
   - **Operational: not ready.** It needs ≥ 4 sealed quarters and a provincial food-insecurity outcome.
   - The most valuable next data step is **CBMS 2024 municipal food-insecurity items** or **FNRI provincial FIES**, to validate the target itself (§10).

---

## 2. The target: what each label means and what it can support

### 2.1 Exact definition (rebuilt from raw data)

A province p is **HIGH** in quarter q when both conditions hold:
- **Hunger:** H_q > 11.3, where H_q = the mean of the quarter's non-commissioned SWS Balance Luzon involuntary-hunger rounds.
- **Price:** F − θ_f(p) > 0, OR F − HL − θ_g(p) > 0, where:
  - F and HL are the quarter means of PSA's published monthly food and all-items YoY for the province;
  - θ are the province's P60 over 2021-Q1..2022-Q4.

Rebuilt from `psa_cpi_yoy_headline_food_2021_2026.csv` and the SWS rounds file: **100/100 labels, 0 mismatches** (max |ΔF| 3e-7). See `out/target_audit.json`.

**What a positive means.** Regional hunger was above its own 2021-22 60th percentile, and the province's food inflation (or food minus headline) was above *its own* 2021-22 60th percentile.

**What a negative means.** At least one of the two conditions failed. 63 of the 81 negatives had exactly one condition met: 24 were blocked by hunger, 39 by price.

### 2.2 Anatomy

| Year | Rows | HIGH | HIGH by reason (food / gap / both) | Price met, hunger blocked | Hunger met, price blocked |
|---|---|---|---|---|---|
| 2021 | 15 | 2 | 0 / 1 / 1 | 4 | 3 |
| 2022 | 15 | 0 | — | 6 | 5 |
| 2023 | 20 | 3 | 0 / 3 / 0 | 14 | 2 |
| 2024 | 20 | 8 | 0 / 5 / 3 | 0 | 12 |
| 2025 | 15 | 5 | 0 / 5 / 0 | 0 | 10 |
| 2026 | 15 | 1 | 1 / 0 / 0 | 0 | 14 |

- Since 2023-Q4, hunger has been above 11.3 in every quarter, so the label equals the price condition in 55/55 rows. Over all years it equals the price condition in 76% of rows.
- 14 of the 19 HIGH rows came through the *gap* route (food rising faster than headline), and only 5 through the food-level route (4 with both).
- Quezon's gap threshold is negative (−0.56), so Quezon qualifies more easily.

### 2.3 Measurement reliability (T2, supported)

**Hunger term**
- From the published SWS margins of error, the standard error of a BL quarter reading is 1.3-2.3 points.
- 2022-Q4 and 2023-Q2 read **exactly 11.3**, so the rule ("> 11.3") labelled them LOW by a tie. The probability that the true value is on the other side is 0.50.
- 2021-Q3, 2022-Q2, 2023-Q3 and 2022-Q3 have that probability at 0.17-0.36 (`out/label_noise_by_quarter.csv`).

**Accuracy ceiling** for a forecaster that knew the true hunger level and the true price condition, scored against the observed label:

| Lead | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Ceiling | 0.955 | 0.961 | 0.974 | 0.992 |

Sampling noise therefore matters for the 2023 quarters, but it is **not** the reason Lead 2 stays near 0.80 (S21).

**Price term**
- 21-27% of evaluation rows have their deciding price margin within 0.5 points of the threshold.
- Small CPI moves flip these labels. This is the dichotomisation cost described in S3.

### 2.4 Construct validity: does T43c measure food-insecurity risk?

| Check | Result | Reading |
|---|---|---|
| **T3 (pre-set test)**: regional price-pressure excess vs BL hunger | ρ = −0.38 (lag 0), −0.37 (lag 1), −0.07 (lag 2). Circular-shift p = .87 / .87 / .57. Against the hunger *change*: ρ −0.07 / −0.10 / +0.11. | **Not supported.** In 2021-26 the price shocks (2022-23) and the hunger surge (2024-26) did not coincide. A rise in food-price pressure was not followed by a rise in regional hunger. |
| FNRI FIES, moderate-or-severe (S22) | 2021: Batangas 29.7%, Cavite 31.7%, Lucena 26.2% (provincial). 2023: CALABARZON 19.1%. 2025: CALABARZON 22.6% (population basis). BL SWS means 11.6 / 11.2 / 18.9. Price-condition share 0.55 / **0.85** / 0.45. | FIES fell from 2021 to 2023 and rose by 2025, as SWS did. Price pressure peaked in 2023, the year FIES was lowest. The hunger term agrees with the direct outcome; the price term does not. |
| OCTA vs SWS on the 11.3 side (S24) | Agree in 3 of 7 matched rounds. OCTA was published earlier in 3 rounds, but by 3-48 days, and its level differs (for example 7% vs SWS 18.1% in 2024-Q3). | Two independent Balance Luzon surveys disagree on the HIGH/LOW side in most rounds. OCTA is not a usable earlier signal. |
| PSA FIES 2023 vulnerability (S23; n = 5, descriptive) | Food share of spending: Quezon 46.7%, Laguna 39.7%, Rizal 38.7%, Cavite 38.0%, Batangas 35.5%. Bottom-30% population: Quezon 52%. Spearman with each province's T43c HIGH share: 0.60 (food share), 0.50 (bottom 30%). | Quezon is both the most vulnerable province and the most often HIGH. With 5 provinces and province-relative thresholds, this agreement can be coincidence (Quezon's negative gap threshold). It is not validation. |

**What the target can legitimately support**
- "In quarter q the province was HIGH under the Chapter I proxy: unusual provincial food-price pressure together with high regional hunger."
- A province ranking of *price pressure relative to the province's own 2021-22 normal*.

**What it cannot support**
- A provincial or municipal food-insecurity level.
- A comparison of vulnerability between provinces (the thresholds are province-relative).
- A claim that price pressure leads to hunger: in this window it did not.

**Strongest justified interim approach**
- Keep T43c as the Chapter I classification (the label was not changed).
- Report its two measured parts separately, each with its own reliability (§5.4):
  - the **regional hunger condition** (a direct experience-based access measure that agrees with FNRI);
  - the **provincial price-pressure outlook** (an affordability pressure, with significant skill over baselines to Lead 3).
- Keep vulnerability in the LGU priority layer, where it belongs, rather than in the hazard forecast.

---

## 3. Root causes of the remaining limits (ranked by the evidence)

| # | Root cause | Evidence |
|---|---|---|
| 1 | **The label measures two weakly or negatively related signals joined by AND.** From 2023-Q4 it reduces to a relative price threshold. | §2.2 (55/55 rows); T3 ρ = −0.38; FNRI follows hunger, not price |
| 2 | **Too few independent outcomes to tell candidates apart.** 7 quarters contain any HIGH row; n_eff ≈ 27-31 per lead. | MDE 0.05-0.07 Brier for FINAL vs P0H4-U; detecting 0.02 needs ~100-140 quarters (§8) |
| 3 | **Future food-price movement beyond the flat projection is mostly unpredictable** with 2021-26 indicators. | Every learned correction is worse (FR Z1-Z3; LJ; add-one). Only the zero-parameter anchored drift improves the continuous error, and only from Lead 3 (§5.2). |
| 4 | **The hunger term lags (SWS publication) and is noisy near 11.3.** | FR schedule B (Lead 2 0.754 → 0.800); 2022-Q4 and 2023-Q2 sit exactly on 11.3 (§2.3) |
| 5 | **Dichotomisation discards forecast gains.** | J2 cuts food-inflation RMSE 3.12 → 2.14 at Lead 3 (CI excludes 0) yet does not lower the label Brier on DEV. 21-27% of rows lie within 0.5 points of the threshold. |
| 6 | **Families are routed to the wrong channel or carry no provincial variation** | §6 |

---

## 4. Hypotheses tested and decisions

| ID | Hypothesis | Result | Decision |
|---|---|---|---|
| T1 | T43c rebuilds from raw data and is price-decided since 2023-Q4 | 100/100; 55/55 | Supported |
| T2 | The hunger term is often within sampling error of 11.3 | 2023-Q2 and 2023-Q3 in the evaluation set (plus four training quarters) | Supported; ceiling 0.95-0.99, not binding |
| T3 | Price pressure goes with higher or rising hunger | ρ < 0; p ≥ .57 | **Not supported** |
| H1 | Trend/reversal modelling (drift, anchor, glide path) beats flat at Leads ≥ 2 | Price DEV Brier: J1/J2/J3 worse than the better of Z0/J0 at Lead 2 or 3. Continuous RMSE: J2 better at Leads 3-4 | Not supported for the label; supported for the continuous price forecast (reported, not adopted) |
| H2 | Joint food/gap simulation improves price calibration | Price log loss J0 < Z0 at Leads 1-3 (0.402 vs 0.432; 0.533 vs 0.560; 0.510 vs 0.534) | Supported. It does not change the selection (J0's DEV T43c Brier is 0.0035 worse). |
| H3 | Fat-tailed innovations improve rare-event log loss | JB3 < J3 at Lead 1 only | Not supported |
| H4 | Each family's failure has an identifiable cause | A cause was assigned to all 12 (§6) | Supported |
| H5 | The schedule-B Lead-1 loss is sampling noise | Only 19% (P0 price part) / 54% (Z0) of the loss comes from readings within 1 SE of 11.3 | **Not supported.** The loss comes from *compensating errors* (§7). |
| H6 | The price component is reliable to a longer lead than T43c | Both reach max lead 1. The price component at Lead 2 misses R2 by one row (0.743, J0/J2) and beats persistence and climatology significantly to Lead 3 | Not supported by the rule; it is the strongest component signal |
| H7 | Online selection is as good as DEV selection | Not worse at Leads 1-3 (better at Lead 2, p = .014) | Supported, but its Lead-2 pass is fragile (§5.3) |

---

## 5. Forecasting approaches and the best candidate

### 5.1 All price parts × the hunger term (S-AB schedule), evaluation rows L1 70 / L2 65 / L3 60 / L4 55

| Model | Lead 1 acc / Brier | Lead 2 acc / Brier | Lead 3 | Lead 4 | DEV Brier (L1-3) | Max reliable lead |
|---|---|---|---|---|---|---|
| Always LOW | 0.757 | 0.738 | 0.717 | 0.691 | — | — |
| **Z0-U (FINAL)** | **0.900 / 0.116** | 0.800 / 0.184, fails R5 | 0.633 | 0.564 | **0.1767** | **1** |
| P0H4 (served, quarter-start) | 0.843 / 0.132 | 0.769 / 0.194, fails R3, R5, R6 | 0.717 | 0.673 | 0.1917 | 1 |
| P0H4-U | 0.843 / 0.132 | 0.800 / **0.167**, fails R6 | 0.633 | 0.673 | 0.1919 | 1 |
| J0 joint, zero drift | 0.871 / 0.116 | 0.769 / 0.175 | 0.683 | 0.673 | 0.1802 | 0 (L1 recall 0.59) |
| J1 drift = trailing 12 m | 0.857 / 0.128 | 0.769 / 0.182 | 0.633 | 0.527 | 0.1878 | 0 |
| J2 anchored 3% | 0.871 / 0.119 | 0.769 / 0.176 | 0.667 | 0.673 | 0.1815 | 1 |
| J3 glide path | 0.857 / 0.123 | 0.785 / 0.179 | 0.650 | 0.582 | 0.1838 | 0 |
| J3T (σ track check) | 0.857 / 0.124 | 0.769 / 0.180 | 0.650 | 0.582 | 0.1849 | 0 |
| JB3 bootstrap tails | 0.857 / 0.122 | 0.785 / 0.181 | 0.633 | 0.545 | 0.1836 | 0 |
| CMB (Z0 + J3T)/2 | 0.871 / 0.120 | 0.800 / 0.181, fails R5, R6 | 0.650 | 0.545 | 0.1802 | 1 |
| LJ LightGBM from J3T | 0.871 / 0.123 | 0.754 / 0.190 | 0.633 | 0.455 | 0.1803 | 1 |

**Selection (frozen rule).**
- The best DEV arm is Z0 (0.1767).
- The best LightGBM arm is LJ (0.1803), 0.0036 worse. That is outside the 0.002 tolerance, so **LightGBM adds no development value**.
- FINAL = Z0. It replaces P0H4-U as the *research* candidate, because its DEV Brier is lower and it is not significantly worse at any lead.

### 5.2 HIGH detection, calibration and comparisons of FINAL

| Lead | TP | FP | FN | TN | Precision | Recall | Balanced acc. | Log loss | AUC | Calibration slope / CITL | n_eff |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 13 | 3 | 4 | 50 | 0.81 | 0.76 | 0.854 | 0.390 | 0.92 | 1.34 / −0.09 | 30.5 |
| 2 | 11 | 7 | 6 | 41 | 0.61 | 0.65 | 0.751 | 0.549 | 0.72 | 0.76 / −0.13 | 29.1 |
| 3 | 6 | 11 | 11 | 32 | 0.35 | 0.35 | 0.549 | 0.628 | 0.63 | 0.48 / −0.11 | 27.9 |
| 4 | 3 | 10 | 14 | 28 | 0.23 | 0.18 | 0.457 | 0.670 | 0.48 | 0.13 / −0.07 | 26.8 |

**FINAL vs each comparator** (ΔBrier = FINAL − comparator; one-sided bootstrap p; Holm across the 5 comparisons):

| Comparator | Lead 1 | Lead 2 | Lead 3 |
|---|---|---|---|
| P0H4 | −0.016 (Holm .45) | −0.011 (.71) | +0.039 (1.0) |
| P0H4-U | −0.016 (.45) | +0.017 (.77) | +0.004 (1.0) |
| Persistence | −0.141 (raw .028, Holm .14) | −0.093 (.50) | −0.262 (**.006**) |
| Climatology | −0.085 (raw .046, Holm .14) | −0.044 (.61) | −0.025 (1.0) |

**Two more points**
- **No candidate is shown to be better than another at any lead.** The Lead-1 superiority over persistence passes R5's unadjusted p < .10, but not Holm at .05.
- **Continuous price forecast** (`out/continuous.json`), food-inflation RMSE over all evaluation origins:

  | | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
  |---|---|---|---|---|
  | Z0 (flat) | 1.92 | 2.37 | 3.12 | 3.50 |
  | J2 (anchored drift) | 1.79 | 1.93 | 2.14 | 2.03 |

  - The paired gain is significant at Lead 3 (ΔMSE 5.2 [1.8, 8.5]) and Lead 4 (8.1 [4.5, 11.5]). It holds in DEV and, at Lead 4, in CONF.
  - J2 has **no fitted parameter**; it is anchored at the BSP 2-4% target midpoint (S19).
  - This is the one clear methodological improvement found. It improves the *price outlook*, not the T43c class.

### 5.3 Honest-selection check (online selection, H7)

- **The procedure.** ONL picks, at each origin, the arm with the best price-term Brier on earlier outcomes.
- **Its result.**
  - It passed R1-R7 at Leads 1 and 2: Lead 2 0.815, Brier 0.160, precision and recall 0.65.
  - Maximum reliable lead: 2.
- **Why that pass is not robust** (`out/posthoc_onl.json`, post hoc, not used for selection):
  - The gain over Z0 comes mostly from the first five origins, where ONL used its default arm (P0) because fewer than 4 quarters were known.
  - Changing the default to Z0 or J0, the minimum to 3, 5 or 6 quarters, or the score to T43c Brier makes Lead 2 fail in every case (max reliable lead 1, or 0).
- **Conclusion.** It is not evidence that Lead 2 is reliable. ONL's current pick (J0) is in the exploratory seal.

### 5.4 The two components separately (H6)

| Component | Lead 1 | Lead 2 | Lead 3 | Note |
|---|---|---|---|---|
| Provincial price condition, J0 (75 / 70 / 65 rows) | 0.840, passes all | **0.743** (one row short of 0.75), bal 0.74, P 0.69, R 0.73; vs persistence p .01, vs climatology p < .001 | 0.723, fails R2, R7 | The forecast has real skill over the baselines to Lead 3. Accuracy is just under the bar. |
| Provincial price condition, Z0 | 0.920 (R 1.00) | 0.671 | 0.708 | |
| Regional hunger condition (one row per quarter, S-AB) | 0.857 (n 14) | 0.846 (n 13) | 0.750 | Cannot pass R1 (≥ 40 rows) with one regional series, and never beats the newest reading (R4/R5). This is a structural evaluation limit, not a model failure. |

---

## 6. The 12 indicator families: measured contribution and why the ten fail

**Tests**
- **D-tests:** `out/families.json`.
- **LightGBM tests:** `out/contrib_ii.json`. Add-one = LJ with only that family plus lead, vs the J3T base; ΔBrier > 0 means it helps.
- No percentages are normalised across families, and nothing here is causal (S15, S16).

**Column guide**
- **Prov. variation:** within-quarter share of the family's variance (0 = national series).
- **ρ time:** Spearman with calendar time.
- **Predictive / explanatory association:** Spearman with the flat-projection error at L1/L2/L3. Predictive uses the issue-time value; explanatory uses the target-quarter value. * marks a CI that excludes 0.
- **Add-one ΔBrier:** helpful if > 0. * marks a CI that excludes 0.

| Family | Missing | Prov. variation | ρ time | Predictive association | Explanatory association | 1-parameter linear vs zero (ΔMSE, L2/L3) | LightGBM add-one ΔBrier (L1/L2/L3) | Leave-one-out / permutation | MDE | Verdict and cause |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 food CPI | 0% | — | — | — | — | — | Extra columns −0.001 / **−0.009\*** / −0.009 | ≈ 0 | 0.012-0.016 | **Predictive as the projection base** (removing it: +0.074 Brier at L1, CI [0.018, 0.126]; +0.067 at L3). Its extra columns add nothing. |
| H1 SWS hunger | 0% | 0 | +0.80 | −0.22 / −0.21 / **−0.43\*** | −0.21 / −0.29 / **−0.44\*** | +0.69 / +2.52 (n.s.) | −0.003 / **−0.022\*** / **−0.033\*** | ≈ 0 | 0.009-0.040 | **Carries the label's hunger part** (removing π_H: +0.041 at L1, CI includes 0). Inside the price part it is harmful. Its negative link to the price error is T3 again. |
| A2 headline / oil | 0% | 0.23 | −0.30 | +0.11 / +0.05 / −0.01 | **+0.51\* / +0.40\* / +0.59\*** | −1.48 / −2.40 | −0.004 / −0.011 / **−0.015\*** | +0.001 / ≈ 0 | 0.010-0.020 | No predictive value. **Coincident, not leading:** the realised headline explains the realised food error, but the value known at issue does not. |
| A3 rice | 8% | 0.16 | −0.20 | ≈ 0 | n.s. | −1.65 / −2.47 | −0.002 / **−0.014\* / −0.018\*** | **−0.005\* / −0.009\*** (removing it helps) | 0.010-0.019 | **No demonstrated value; harmful.** No association with the target. |
| V1 poverty | 0% | **1.00 (static)** | 0 | ≈ 0 | ≈ 0 | +0.42 / −0.02 | **−0.004\*** / −0.010 / **−0.014\*** | ≈ 0 | 0.008-0.028 | No value. A static province identifier, and the label's thresholds are province-relative, so it cannot carry information. It belongs in the LGU vulnerability layer. |
| C1 ENSO | 0% | **0 (national)** | +0.19 | ≈ 0 | ≈ 0 | −0.43 / −1.23 | ≈ 0 | ≈ 0 | 0.004-0.008 | No price value. **It is associated with the hunger change** (+0.44\* / +0.45\* / +0.74\* at L1-3): a possible channel mismatch, seen in one El Niño episode (§6.1). |
| C2 typhoons | 0% | 0.06 | +0.22 | +0.21 / −0.10 / −0.28 | −0.25 / **−0.39\*** / −0.29 | +0.06 / +0.63 | ≈ 0 | ≈ 0 | 0.001-0.003 | No value. Coincident: the typhoon in the target quarter cannot be known at issue. |
| C3 harvest / fertilizer | 0% | 0.57 | +0.07 | n.s. | n.s. | +0.21 / −0.13 | **−0.012\* / −0.028\* / −0.032\*** | ≈ 0 | 0.023-0.042 | **Harmful** as a LightGBM correction. No association. The linear form is significantly less harmful (architecture). |
| C4 fisheries | 0% | 0.68 | −0.18 | n.s. | n.s. | +0.62 / +0.35 | **−0.004\* / −0.011\* / −0.010\*** | +0.001\* / ≈ 0 | 0.007-0.021 | Harmful as LightGBM; no association; architecture (linear less harmful). |
| E1 unemployment | 0% | **0** | **+0.96** | −0.22 / −0.18 / −0.25 | −0.23 / −0.31 / **−0.47\*** | **−13.7\* / −17.1\*** | +0.003 / **−0.011\*** / −0.011 | ≈ 0 | 0.005-0.020 | **No value. Calendar-time confound** (R² 0.92 on A1 + time); a strongly harmful linear correction. |
| E2 remittances | 0% | **0** | +0.16 | +0.20 / +0.16 / +0.23 (n.s.) | n.s. | −4.4 / −6.0 | −0.001 / **−0.018\* / −0.027\*** | ≈ 0 | 0.004-0.034 | No value. National, no association, and the series stops at 2025-Q4. |
| N1 FSSI-v3 news | **79%** | 0.15 | +0.17 | −0.27 / +0.37 / −0.12 | n.s. | +0.55 / +0.64 | −0.002 / **−0.014\* / −0.018\*** | +0.001\* / ≈ 0 | 0.005-0.020 | No value. **Coverage** is the first problem. |
| N1 GDELT price-news share | 0% | **0** | −0.29 | +0.19 / +0.30 / +0.37 (n.s.) | ≈ 0 | **+1.70 / +2.38** (vs lead mean: CI excludes 0 at L2 and L3; vs zero n.s.) | (in N1 above) | — | — | **The only weak signal**, and only in a one-parameter linear form: the LightGBM cannot use it (architecture). Not Holm-significant across 12 families × 3 leads. A hypothesis for prospective testing, not a contribution. |

**Summary**
- **No family is "predictive"** under the pre-registered classification. Holm-adjusted p for "helps" is 1.00 for every family at every lead.
- **Many families are significantly harmful** when added to the structural base as a LightGBM correction: A1 extra columns, A3, V1, C3, C4, E1, E2, N1, H1.
- **The data rule out large gains.** The best-case improvement in the CI is below 0.01 Brier for every family. Gains of the size the MDE could detect (0.004-0.04) are therefore either absent or not established.
- **Distinguishing the kinds of value.**
  - *Predictive* value (held out): only A1 as the base and H1 as the hunger term.
  - *Explanatory* value (contemporaneous): A2, C2 and E1/H1 at Lead 3.
  - *Contextual* value: climate (C1) and fish-kill events are useful for monitoring and narrative, not as forecast inputs.
- **SHAP of LJ** (model influence only) was unstable. The first third of origins had no fitted correction; the Spearman between the second and third thirds is 0.31. A1 and A3 dominate the second third, and A2 the third.

### 6.1 Why the families fail (H4, all supported)

1. **National series (C1, E1, E2, GDELT; H1 is regional).** They have no between-province variation, so they can only shift whole quarters. That leaves about 14-20 effective observations for each family.
2. **Coincident, not leading (A2, C2).** The information arrives in the target quarter itself.
3. **Time confound (E1).** It tracks the calendar, not labour conditions.
4. **Coverage (N1, 79% missing).**
5. **Channel mismatch.** Every family enters only the *price* part, but climate, income and remittances plausibly act on *hunger*.
   - C1's association with the hunger change is the clearest sign.
   - The hunger part cannot be learned from 14 regional quarters (E87, E109-E113).
6. **Architecture.** For V1, C3, C4, GDELT and H1, a one-parameter linear correction is significantly better than the LightGBM add-one. But even the linear form does not beat the no-correction projection.
7. **Power.** MDEs of 0.004-0.04 Brier mean a real but modest effect cannot be confirmed in 2021-26.

---

## 7. Lead 1, Lead 2 and the issue schedule

**Why schedule B (the SWS-update issue) hurts Lead 1** (`out/schedule_limits.json`)
- With the P0 price part, the B-minus-A Lead-1 Brier loss is +0.026 per row.
- 19% of it comes from readings within 1 SE of 11.3. Most of it (1.33 of the positive sum) comes from one origin, 2023-Q4 (target 2024-Q1):
  - B saw the newly published 14.3 surge reading, so π_H was high;
  - the price part's false alarms then became HIGH calls;
  - under A the stale 10.3 reading had suppressed them.
- **So the quarter-start Lead 1 looked better partly for the wrong reason:** a stale hunger reading cancelled price-part errors.
- This is not a defect of B. B's Lead-1 forecast is a nowcast, issued after its quarter starts, and is never shown as a warning.

**Products ordered by warning time** (P0 / Z0 price parts)

| Product | Median warning | Accuracy | Brier | HIGH recall |
|---|---|---|---|---|
| L1-A (quarter start) | 0 days | 0.843 / **0.900** | 0.132 / 0.116 | 0.65 / 0.76 |
| L2-B (after the SWS release) | 59 days | 0.800 / 0.800 | **0.167** / 0.184 | 0.59 / 0.65 |
| L2-A | 91 days | 0.769 / 0.754 | 0.194 / 0.203 | 0.35 / 0.41 |
| L3-B | 152 days | 0.633 / 0.633 | 0.218 / 0.222 | 0.35 / 0.35 |
| L3-A | 182 days | 0.717 / 0.683 | 0.183 / 0.182 | 0.24 / 0.41 |
| L4-B / L4-A | 242 / 274 days | 0.56-0.67 | 0.24-0.26 | ≤ 0.35 |

**The defensible calendar** (implemented in P0H4-U and Z0-U)
- A quarter-start issue for Lead 1.
- An SWS-update re-issue for Leads 2-4.
- This keeps the timely Lead-1 warning and uses the newest hunger reading for every longer lead, with no future information (checked in FR `checks.json`).
- Past about 60 days of warning, no product is reliable. Lead 3 and beyond are no better than always-LOW.

---

## 8. Hard limits (as far as the evidence permits)

| Limit | Evidence | Consequence |
|---|---|---|
| Label noise (L1) | Accuracy ceiling 0.955 / 0.961 / 0.974 / 0.992 at Leads 1-4 | Not binding: the models sit at 0.80 (Lead 2), far below the ceiling |
| Oracle (L2, FR1) | With the true price, schedule-B Lead 2 would reach 0.938; with the true hunger level, the forecast price gives 0.677 | The Lead-2 limit is the price condition two quarters ahead |
| Power (L3) | FINAL vs P0H4-U: bootstrap SD of ΔBrier gives MDE 0.053 / 0.056 / 0.068 at Leads 1-3. Detecting ΔBrier 0.02 needs ≈ 99 / 103 / 140 labelled quarters; 0.01 needs ≈ 400+ | **The 2021-26 data cannot distinguish the candidates.** Each new quarter adds about 2 effective observations per lead, so prospective scoring alone needs many years. A provincial outcome series would add cross-sectional power. |
| Price predictability (L4) | The random-walk innovation variance exceeds the flat projection's realised MSE at every lead (share −0.57 to −1.23). The bias share of the MSE is 0.15 / 0.37 / 0.54 / 0.66. | Food CPI mean-reverts month to month. The only systematic, reducible part of the error is the bias (drift), which the anchored drift addresses (§5.2). Nothing else in the 12 families predicts the rest. |

---

## 9. Implementation and tests

| File | Change |
|---|---|
| `backend/app/ml/inference/ch1_system.py` | `DATA_FR2` and an `ENGINES` map (`fr`, `fr2`). New `structural()`, `indicator()` and `text()`. When the served price part is structural, the model line, definition, report cover, evidence note, driver text and protocol name describe the CPI projection. The default output is unchanged. |
| `backend/app/services/{dashboard, report, report_data_e31}.py`, `backend/app/api/v1/final.py` | Read the definition and report text through `indicator()` and `text()`. The P0H4 and P0H4-U wording is byte-identical. |
| `backend/data/ch1_engine_fr2/{rows.csv, evaluation.json}` | New: the Z0-U export. Same rows, hunger part and issue dates as P0H4-U; the price part is Z0. Attribution: Market / Prices only (the price part uses only CPI). |
| `backend/tests/integration/test_forecast_research_ii.py` | New: 6 tests. Default and fr unchanged; only the price part changes; seals; verdict; API = rows; structural wording. |
| `.claude/launch.json` | New `api-fr2` configuration |
| `aipheed-backend-aligned/experiments/FORECAST_RESEARCH_II/` | Protocol, sources, runners, outputs, this report |

**Checks**
- `price_audit.json`: index-based YoY vs PSA published YoY, max |Δ| 0.05 (rounding). J0 reproduces the Z0 projection to within 0.13 points.
- LJ reproduced in `contrib_ii.py` (max |Δ| < 2e-5).

**Tests**
- Backend: **896 passed, 18 skipped**: 890 before, plus the 6 new tests (§9.1).
- Frontend: **83/83** (no frontend file changed).

**Dashboard check** (API on `AIPHEED_CH1_ENGINE=fr2`)
- Quezon 2026-Q4 riskScore 0.2115, equal to `rows.csv`.
- Map, Q1 2027 regional average 0.13, equal to the mean of the export.
- The influence panel shows Market / Prices 100% and every other group 0%, which is correct for a CPI-only price part.

**Prospective seal** (`out/PROSPECTIVE_SEAL.json`; score only after SWS publishes 2026-Q4 and later)

| Seal | Content |
|---|---|
| `b7162a63` | FINAL Z0-U, 20 rows: Lead 1 issued 2026-10-01; Leads 2-4 issued 2026-10-15 |
| `39c808a8` | Exploratory: ONL (pick J0) and the **post-hoc** J2S anchored-drift arm |
| `a498b5ef` (served), `bd6572e1` (P0H4-U) | Unchanged |

Z0-U's 2027-Q2 and 2027-Q3 rows are HIGH for Quezon (and Cavite in 2027-Q2). They are Lead 3-4 forecasts, which fail the reliability rule. The cause is the projection's positive bias and wide σ at long leads, so they must be shown as experimental.

### 9.1 Test results

- **Full backend suite** (backend venv, `python -m pytest -q`): 896 passed, 18 skipped, 3 warnings, in 161 s.
- **The 32 tests of the three engine files** (`test_forecast_research_ii.py`, `test_forecast_research.py`, `test_system_fixes.py`): all pass.
- **Frontend** (`vitest run`): 17 files, 83 tests, all pass.

---

## 10. Data needed to validate provincial food-insecurity forecasting

Ranked by value per effort. Draft requests are in `E87_Outcome_Gap/DATA_REQUESTS.md`.

| Rank | Data | Why it is decisive | Route |
|---|---|---|---|
| 1 | **PSA CBMS 2024 food-insecurity items** for the 142 CALABARZON LGUs, with enumeration months | The first provincial *and* municipal direct outcome. It validates the province class, the LGU ranking and the target itself (does the price condition coincide with measured food insecurity?) | PSA CPCD (`cbms@psa.gov.ph`), CBMS Data Request Form, or eFOI |
| 2 | **FNRI FIES for Laguna, Quezon and Rizal** (ENNS rolling round), plus 2023/2025 provincial domains, ideally by quarter of interview | Completes the 2021 provincial cross-section (only Batangas, Cavite and Lucena are public). Quarter-of-interview tables would give the first time-varying FIES series. | DOST-FNRI Director or eFOI (precedent: "Raw data of ENNS 2021" was answered) |
| 3 | **SWS hunger microdata for CALABARZON respondents**, 2021-26 | A regional (CALABARZON rather than Balance Luzon) hunger series with its own standard error. It removes part of the regional-to-provincial mismatch. | SWS Survey Data Library (cost-based) |
| 4 | Official forward-looking price information (BSP inflation outlook, DA rice supply outlook) as dated vintages | The only plausible source of information about future food prices beyond the projection (FR §4.4) | Published reports, archived by date |
| 5 | Prospective quarters | Every sealed quarter adds clean evidence; scoring starts January 2027 | Already sealed |

Until rank 1 or 2 exists, **no provincial food-insecurity forecast can be validated**. Only the Chapter I proxy class can be.

---

## 11. Readiness decision (rules fixed in protocol §12)

| Use | Decision | Reason |
|---|---|---|
| **Demonstration** | **Ready** (P0H4 as served; Z0-U and P0H4-U as research candidates) | Lead 1 is reliable on development evidence, and the served text matches each model. Present Lead 2 as experimental, the label as a proxy class, and LGU numbers as priority rankings. |
| **Pilot** | **Not ready** | It needs ≥ 1 scored sealed quarter at Lead 1 (accuracy ≥ 0.75, recall ≥ 0.60). The first is possible after SWS publishes 2026-Q4 (expected January 2027). No lead beyond 1 qualifies. |
| **Operational deployment** | **Not ready** | It needs ≥ 4 consecutive sealed quarters passing R2 and R6, plus validation against CBMS or FNRI provincial outcomes. T3 also shows the price term does not track hunger, so the target needs that validation before any operational food-insecurity claim. |

**Decisions left to the researcher and adviser**
1. Whether to keep LightGBM in the price part (P0H4 / P0H4-U) or adopt the structural projection (Z0-U). The evidence does not separate them, and the thesis wording requires LightGBM.
2. Whether to add the continuous price outlook (J2) as a reported product at Leads 2-4.
3. Whether to send requests A and B of §10.

The validator-only rule of 2026-10-27 remains unresolved. Every candidate here uses SWS and food CPI as inputs.

---

## Reproduce

Run from `FORECAST_RESEARCH_II/runner` with the backend venv. FORECAST_RESEARCH outputs must exist.

```
python target_audit.py
python price_arms.py
python score_ii.py
python posthoc_onl.py
python contrib_ii.py
python families.py
python schedule_limits.py
python continuous.py
python export_ii.py
```
