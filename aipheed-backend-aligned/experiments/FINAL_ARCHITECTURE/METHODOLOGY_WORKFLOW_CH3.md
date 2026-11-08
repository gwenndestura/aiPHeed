# aiPHeed methodology workflow (for Chapter 3 and the defense)

**Status.** This describes the **recommended** single-model architecture (candidate C of FINAL_ARCHITECTURE; it equals S3 of LEAD2_ONE_MODEL). The dashboard still serves P0H4 (§9) until you approve a change. All numbers come from walk-forward evaluation on 2023–2026 quarters that also informed the design (development evidence).

## 1. What is forecast

**Target (Chapter I).** A province is HIGH food-insecurity risk in a quarter when both hold:
1. **SWS Balance Luzon involuntary hunger is above 11.3%** (the 2021–22 60th percentile). This is measured hunger, but **regional**: one value for all five provinces.
2. **The province's food prices rose unusually fast.** PSA food inflation, or food minus headline inflation, is above the province's 2021–22 60th percentile.

**This is a combined proxy, not observed provincial hunger.** Provinces differ only through prices. LGU values are a priority ranking, not forecasts.

## 2. Data (12 FIRI v2 indicator families), as of each issue date

| Family | Indicator | Source, level |
|---|---|---|
| A1 | Food-price pressure: projected food inflation vs threshold | PSA CPI, province |
| A2 | Headline inflation above usual | PSA CPI, province |
| A3 | Wholesale rice price change | PSA, province |
| V1 | Poverty and population density | PSA SAE 2021, POPCEN 2024, province (static) |
| C1 | El Niño | PAGASA alerts, national; NOAA ONI |
| C2 | Typhoons within 300 km | IBTrACS, province |
| C3 | Palay/corn production drop | PSA, province |
| C4 | Fisheries production drop | PSA, province |
| E1 | Unemployment change | PSA LFS, national |
| E2 | Remittance decline | BSP, national |
| N1 | News food-stress signals | RSS headlines (XLM-RoBERTa), GDELT, province |
| H1 | Regional hunger outlook and recent SWS readings | SWS, region |

**Also used:** the forecast lead (1–15 quarters) and World Bank world rice, cereal, oil and fertiliser prices.

**Issue-date rule.** A forecast issued on the first day of quarter t+1 uses only:
- SWS rounds **published** before that day;
- CPI up to month 2 of quarter t;
- other series at their publication lag.

Tested by perturbing all later data (6 origins, identical forecasts).

## 3. The model: ONE LightGBM for all leads

1. **Stack.** For every past issue date and every lead k = 1…15, one row per province: the indicator values known at that issue date, plus k. The label is the T43c class of the target quarter, used only once that quarter's SWS rounds and CPI were published.
2. **Structural starting point.** LightGBM starts each row from a documented baseline: the A1 food-price projection converted into a probability that the price condition holds. Its spread σ is estimated from the training window's past projection errors. This is a fixed formula used as LightGBM's `init_score`, **not a second trained model**. The trees then learn from all 12 families how the actual risk differs from that baseline, including the hunger condition, which enters only as inputs (H1 outlook, latest SWS reading, recent change, run above or below 11.3, other SWS areas).
3. **Training.** Balanced class weights; monotone constraints (more projected food inflation or more hunger cannot lower risk); depth 1–2, few trees, strong regularisation. Settings are chosen at each issue date by chronological validation on earlier issue dates only.
4. **Output.** P(HIGH) for each province and lead. HIGH at 0.50.

**There is no separate hunger model and no multiplication.** That is the difference from the served P0H4 (§9).

## 4. How reliability and the maximum horizon are decided

**Walk-forward.** At each past issue date: refit, forecast, compare with the outcome once published. Evaluated on 70 rows (14 quarters) at Lead 1 and 65 rows (13 quarters) at Lead 2.

**A lead is reliable only if it passes all of these (fixed beforehand):**
- ≥ 10 quarters;
- accuracy ≥ 0.75;
- balanced accuracy ≥ 0.70;
- beats always-LOW and persistence;
- Brier better than persistence and climatology;
- precision and recall ≥ 0.60;
- stable across thirds and leave-one-quarter-out;
- also passes in the later 2025–26 block.

**Maximum reliable lead** = the run of consecutive passes from Lead 1. **Result: Lead 1.** Leads 2+ are generated but labelled experimental.

**Uncertainty.** Bootstrap by target quarter, never treating the five provinces as independent hunger observations.

## 5. Explanations

**For the single model.** The structural price baseline (the offset) carries most of the price information, and SHAP of the trees does not include it. So the Market bar must include the row's offset deviation from its average. Otherwise prices would look unimportant (implementation note for adoption).

**What the bars are.** SHAP contributions of the one model, summed into indicator groups and rescaled to 100%: **relative model influence**, not causes.
- Every family has a row; nothing is hidden.
- The horizon (`lead`) is excluded and disclosed.
- Each group's status says whether its inputs were published at the issue date.

**What they are not:** municipal hunger estimates, or proof that a factor caused food insecurity.

## 6. What is and is not established

**Established (development evidence):**
- Lead-1 forecasts of the combined proxy: accuracy 0.857, balanced 0.79, precision 0.73, recall 0.65, Brier 0.112. Better than price-only and hunger-only baselines.
- No leakage found.
- Historical replay reproduces the stored forecasts.

**Not established:**
- reliable forecasts beyond one quarter;
- detection of new hunger onsets (0 of 10 at Lead 2);
- provincial or municipal hunger;
- the utilization dimension of food security;
- performance on untouched data. The first untouched outcome is SWS 2026-Q4; forecasts are sealed before it.

## 7. Indicator findings for the defense

| Group | Finding |
|---|---|
| Market | Strongest evidence. Removing the price columns **and** the structural price baseline worsens Lead-1 Brier by 0.083 [0.044, 0.128] and Lead-2 by 0.045 [0.022, 0.070]. Partly structural, because the target's price leg uses the same CPI. |
| Climate | One El Niño episode in 2021–26. A richer representation (ONI severity and duration, PAGASA level and duration, typhoon and production lags) lowered Lead-2 Brier by 0.003. **The gain failed the placebo:** shuffled climate values did as well (p = .55). So **no demonstrated predictive value**. The model leans on climate inputs mainly in El Niño quarters. |
| Employment, remittances, news, poverty | No demonstrated predictive gain in this sample (national data, 17% news coverage, static poverty). Kept as required families; shown as such. |
| Hunger | Decisive. It separates hunger-LOW quarters from price spikes. |

## 8. Simple flow for the defense slide

Published data (PSA, SWS, PAGASA/NOAA, IBTrACS, BSP, news)
→ issue-date cut-off
→ 12 indicator families + lead
→ ONE LightGBM (structural price baseline + learned adjustments), refitted each quarter
→ P(HIGH) per province and lead
→ walk-forward evaluation → maximum reliable lead (Lead 1)
→ dashboard: forecast, horizon status, relative influence, LGU priority ranking

## 9. Served P0H4 vs recommended single model

| | P0H4 (served) | Single model (C) |
|---|---|---|
| Design | **Hybrid:** one LightGBM for the price condition × a closed-form hunger probability | One LightGBM on the combined target |
| Lead 1 | 0.843; Brier 0.132 | 0.857; Brier 0.112 (difference n.s., p = .43) |
| Lead 2 | Brier 0.194 | Brier 0.232 (n.s., p = .25) |
| Lead 3 | Brier 0.183 | 0.256 (**significantly worse**, p = .003) |
| Rizal calibration (Lead 1 mean p vs observed 0) | 0.19 | 0.05 |

**Maximum reliable lead:** 1 for both.
