# Chapter 3 amendment: aiPHeed as a food-insecurity forecasting system

**Status:** proposed amendment for the adviser's review (2026-11-03). Results are development evidence unless stated
otherwise. Sources: `E99_REPRODUCTION.md`, `../IMPROVE_V2/RESULTS.md`, `../OBJECTIVES_COMPLETION/OBJ4_H3_COMPARISON.md`,
`DECISIONS.md`, `../P0H4_LEAD12_REVIEW/out/price_warning.json` (province food-price pressure),
`../IMPROVE_V2/out/lgu_rankings.csv` (vulnerability inputs).

## Team decision: P0H4 as the main model (pending adviser confirmation)

**Decision (2026-11-03), made by the team and pending adviser confirmation.** The main model is the served **P0H4**
forecast (the Chapter I model), not the IMPROVE_V2 hunger-only model. The IMPROVE_V2 design in sections 2–9 below is
kept unchanged as the **documented alternative**.

**What P0H4 is** (`backend/data/ch1_engine/`, `../LEAD2_OPTIMIZATION/`; unchanged, not retrained):
- **Target.** A province-quarter is HIGH when SWS Balance Luzon hunger is above 11.3% **and** the province's food-price
  condition holds: food CPI year-on-year above the province's 2021–22 60th percentile, or food minus headline inflation
  above its 2021–22 60th-percentile gap.
- **Model.**
  - The price part is one LightGBM trained on the rows of every lead (12 indicator families and world prices).
  - The hunger part is computed from the latest SWS Balance Luzon reading.
  - P(HIGH) = P(hunger) × P(price), and HIGH when P(HIGH) ≥ 0.50.
- **Evidence** (walk-forward 2023-Q1..2026-Q3, development evidence):

  | Lead | Accuracy | Recall (HIGH caught) | R1–R7 |
  |---|---|---|---|
  | 1 | 0.843 on 70 province-quarters | 0.647 (11 of 17) | all pass |
  | 2 | 0.769 on 65 | 0.353 (6 of 17) | fails R3, R5, R6 |

- **Maximum Reliable Lead Time:**
  - **2 quarters** under the paper's Algorithm 3 (75% mean fold accuracy). Lead 3 is the first failure, at 0.717.
  - **1 quarter** under R1–R7.

  Details are in `P0H4_EVIDENCE.md`. Objective status is in `P0H4_OBJECTIVES_STATUS.md`.

**Where P0H4 differs from the paper:**
- The target is not Equation 3. It uses fixed 2021–22 thresholds, not the global median.
- There is no Optuna search.
- Reliability is reported under both Algorithm 3 and R1–R7.
- Provinces differ only through the food-price part, because SWS hunger is regional.

The section 9.1 "Option A" decision below concerns the IMPROVE_V2 alternative. It does not apply while P0H4 is the
main model.

## 1. Why the Chapter III pipeline is replaced

Chapter III defines the forecast target by Equation 3: a composite stress score equal to SWS hunger plus twice the
provincial deviation of food CPI inflation from the regional mean. A province-quarter is labelled HIGH when its score
exceeds the median of all 120 province-quarter scores. Algorithm 3 then finds the furthest lead with at least 75% mean
walk-forward accuracy. Algorithm 4 tunes LightGBM with Optuna and accepts the model only if, on a blind four-quarter
holdout, weighted F1 ≥ 0.75 and AUC-ROC ≥ 0.80.

**This pipeline was implemented as written (experiment E99) and reproduced exactly** (identical metrics, labels and
sealed file). It does not meet its own criteria:

| Criterion | Result | Required |
|---|---|---|
| Algorithm 3, one quarter ahead | Mean fold accuracy **0.30** (naive persistence **0.70**) | ≥ 0.75 |
| Maximum Reliable Lead Time | **0** quarters | ≥ 1 |
| Algorithm 4, blind holdout 2025-Q4..2026-Q3 | Accuracy 0.45, weighted F1 **0.53**, AUC-ROC **0.61** | F1 ≥ 0.75, AUC ≥ 0.80 |
| Against persistence | Significantly worse (McNemar exact p = 0.0003) | Better |

Three reasons explain the failure.

1. **Too little history.** The study window holds about 19 labelled quarters.
2. **A single regime switch.** The Equation 3 label is LOW in almost every quarter of 2021–2023 and HIGH in almost every
   quarter of 2024–2026. A model trained on the earlier years keeps predicting LOW after the switch. Hyperparameter
   tuning (100 Optuna trials) cannot correct this.
3. **The label uses future data.** Equation 3 sets the HIGH/LOW threshold at the median over all 120 province-quarters.
   Every training label therefore depends on outcomes from the test period, which contradicts Rule 3 (no look-ahead
   bias). A threshold computed from training quarters only removes the leak, but not the first two problems.

## 2. The amended target

**aiPHeed forecasts food insecurity directly:** whether **SWS involuntary hunger in Balance Luzon** will exceed
**11.3%** in a future quarter.
- SWS hunger is a direct measure of experienced food insecurity: the share of families that went hungry at least once in
  the past three months with nothing to eat.
- 11.3% is the 60th percentile of Balance Luzon hunger in 2021–2022, fixed before evaluation.
- The quarter's value is the mean of its non-commissioned survey rounds.
- A quarter without a round has no label, and no value is imputed.

**Food prices are inputs to the model, not part of the target.** Balance Luzon (Luzon outside Metro Manila) contains
CALABARZON, but is not identical to it. SWS publishes no provincial figure, so the forecast is **regional**.

### 2.1 What each province is shown (proposed design)

**The food-insecurity classification is regional. Province differences come from food prices and vulnerability.**

| Element | What it is | Same for every province? | Role |
|---|---|---|---|
| **Headline** | The regional food-insecurity forecast: P(Balance Luzon hunger > 11.3%), from the reference model of §4. **HIGH when P ≥ 0.50.** | Yes | The risk classification |
| (a) Province food-price pressure | The price part of the served P0H4 forecast (π_price): the probability that the province's food CPI year-on-year exceeds its 2021–22 60th percentile, or food minus headline inflation exceeds its 2021–22 60th-percentile gap. Shown as **Low** (< 0.33), **Medium** (0.33–0.67) or **High** (≥ 0.67). | No | Context, ranking |
| (b) Province vulnerability rank | Rank 1–5 by 0.6 × PSA 2021 poverty incidence + 0.4 × PSA 2024 population density, both min-max normalized across the five provinces | No | Context, ranking |

**Rules.**
- (a) and (b) rank provinces **within** the regional forecast. They never lower or raise the headline, and a province is
  never shown as LOW while the region is HIGH.
- Hunger and prices are **not multiplied**. The headline is the hunger forecast alone.
- (a) is labelled "food-price pressure, not food insecurity". On development evidence π_price does **not** meet R1–R7
  on its own: accuracy 0.61 at Lead 1 and 0.60 at Lead 2, below price persistence at Lead 1
  (`P0H4_LEAD12_REVIEW/out/price_warning.json`). It is therefore shown as a band, not as a validated HIGH/LOW call.
- The band cut-offs 0.33 and 0.67 are fixed thirds of the probability scale. They were not chosen from outcomes, and
  the adviser may set others.

**Vulnerability rank, current inputs.** Province poverty is the population-weighted mean of the PSA 2021 municipal
estimates. Density is total 2024 population over total land area.

| Rank | Province | Poverty (%) | Density (per km²) | Index |
|---|---|---|---|---|
| 1 | Quezon | 19.3 | 256 | 0.600 |
| 2 | Cavite | 9.9 | 2,997 | 0.575 |
| 3 | Rizal | 7.1 | 2,889 | 0.431 |
| 4 | Laguna | 6.0 | 1,912 | 0.242 |
| 5 | Batangas | 8.8 | 961 | 0.227 |

Quezon and Cavite are close (0.600 and 0.575), and the min-max weights over five provinces are sensitive to either
extreme. The rank is a priority order, not a measured rate.

**Cities and municipalities.** Each LGU shows the regional headline. Its position within its province follows the same
vulnerability index at LGU level (§7.2).

## 3. Data

All inputs are publicly available. At each forecast, only values published before the issue date are used: the first
day of the quarter after the forecast origin.

| Group | Source and series | Rule at the issue date |
|---|---|---|
| Hunger history | SWS, four survey areas, 1998-Q3 onward: latest Balance Luzon reading, its change, 4-quarter mean, the horizon in quarters, and a hunger outlook term (latest reading compared with 11.3% using the historical forecast error) | Rounds published before the issue date |
| Food and headline prices | PSA CPI, Region IV-A, food and all items (2018 basket; pre-2018 values are PSA's back-cast): year-on-year inflation and 3-month food momentum | Up to the second month of the origin quarter |
| Rice | PSA rice CPI, Region IV-A, year-on-year | As above |
| Climate | NOAA Oceanic Niño Index (latest value, 12-month maximum) | Season ending by the second month |
| Typhoons | IBTrACS tracks within 300 km of the five provinces' centroids | Origin quarter |
| Agriculture | PSA palay and corn production; fisheries production (year-on-year decline) | Previous quarter |
| World prices | World Bank Pink Sheet: rice, cereals, crude oil, urea | Up to the second month |

No missing value is filled with zero. An automated perturbation test confirmed that no information published after the
issue date reaches a forecast: randomizing all later data left the forecasts unchanged at six origins.

## 4. Method

1. **Model.** One LightGBM binary classifier, consistent with Chapter III's choice of algorithm. Rows for forecast leads
   1 to 15 quarters are stacked, with the lead as an input.
2. **Walk-forward, expanding window.** At every quarterly origin from 1998-Q3, the model is refitted on all earlier
   rows whose outcome had been published, then forecasts the next quarters.
3. **Configuration.** Chosen at each origin by chronological validation on the four most recent training origins, from
   eight fixed settings: tree depth 1 or 2, 50 or 150 trees, with or without class balancing. Learning rate 0.05,
   L2 regularization 5, minimum 15 rows per leaf.
   - This replaces Algorithm 4's Optuna search.
   - It is a small, fixed grid evaluated only on past data, which suits the short series. No setting was tuned on the
     evaluation quarters.
4. **Decision rule.** HIGH when P ≥ 0.50.
5. **Evaluation.** Forecasts for target quarters 2010-Q1 to 2026-Q3: **62 quarters**, of which 43 HIGH and 19 LOW.
6. **Explanation (SHAP).** TreeSHAP contributions are summed into indicator groups and expressed as each group's share
   of total influence.

## 5. Results (walk-forward, 62 quarters)

| Metric | Lead 1 | Lead 2 |
|---|---|---|
| Accuracy | **0.790** | **0.790** |
| Precision | 0.812 | 0.812 |
| Recall | 0.907 | 0.907 |
| F1 | 0.857 | 0.857 |
| AUC-ROC | 0.702 | 0.704 |
| Brier score | 0.188 | 0.184 |
| Confusion (TP / FP / FN / TN) | 39 / 9 / 4 / 10 | 39 / 9 / 4 / 10 |

**The identical Lead-1 and Lead-2 confusion matrices are real, not a copy error.** They were recomputed from the raw
walk-forward forecasts (`../IMPROVE_V2/out/forecasts.csv`, arm REF, P ≥ 0.50) and the labels:
- The two leads are separate forecasts: every Lead-2 forecast comes from an origin one quarter earlier. Only 1 of 62
  probabilities is equal, and the mean absolute difference is 0.094 (maximum 0.49). The Brier scores differ (0.1875 and
  0.1838).
- The HIGH/LOW calls differ in 8 quarters. Lead 1 alone is wrong in 2016-Q3, 2017-Q4, 2022-Q2 (missed HIGH) and
  2018-Q2 (false HIGH). Lead 2 alone is wrong in 2016-Q4, 2020-Q3, 2023-Q4 (missed HIGH) and 2019-Q1 (false HIGH).
  Each lead therefore has three extra missed HIGH quarters and one extra false HIGH, so the counts match.
- The model depends little on the lead. A Lead-2 forecast is close to the Lead-1 forecast made at the same origin for
  the previous quarter (for example 0.337 for both 2016-Q3 at Lead 1 and 2016-Q4 at Lead 2). The two series are
  roughly one quarter apart, so their errors move to neighbouring quarters.

**Baselines.** Brier differences, one-sided paired cluster bootstrap, Holm correction:

| Comparator | Lead 1 | Lead 2 |
|---|---|---|
| Naive persistence (latest survey reading; accuracy 0.661, Brier 0.339) | **better**, Holm p = 0.001 | **better**, p = 0.001 |
| Always-HIGH | better, p = 0.028 | better, p = 0.023 |
| Logistic regression, news only | better, p = 0.008 | better, p = 0.014 |
| LightGBM, government indicators only | better, p = 0.014 | better, p = 0.010 |
| LightGBM, news only | better, p = 0.014 | p = 0.061 (not significant) |
| Logistic regression, PSA indicators only | lower Brier, not significant (p = 0.51) | not significant (p = 0.08) |
| Logistic regression, all indicators | lower Brier, not significant (p = 0.51) | not significant (p = 0.08) |

**SHAP group shares** (Lead 1):

| Group | Share |
|---|---|
| Past SWS hunger | 64.7% |
| World food and energy prices | 22.4% |
| CALABARZON food and headline prices | 6.3% |
| Rice prices | 2.8% |
| Climate (ONI) | 2.0% |
| Fisheries | 1.0% |
| Crops | 0.9% |
| Typhoons | 0.1% |

## 6. Reliability, stated both ways

**Under the thesis criterion** (Algorithm 3: mean walk-forward accuracy ≥ 75%, advancing from Lead 1 until the first
failing lead):
- The walk-forward was re-run exactly as specified, storing Leads 1–15 (`../IMPROVE_V2_LEADS/RESULTS.md`). There was no
  tuning and no change to the model. It reproduces every stored Lead-1 and Lead-2 forecast bit for bit.
- Each origin is one fold with one forecast per lead, so mean fold accuracy equals accuracy over the 62 target
  quarters.
- **Maximum Reliable Lead Time = 2 quarters** on development evidence. Lead 3 is the first lead below 0.75.

| Lead | Accuracy | Algorithm 3 | Persistence | R7 thirds (2010–15, 2015–20, 2020–26) | R1–R7 failed |
|---|---|---|---|---|---|
| 1 | 0.790 | pass | 0.661 | 0.95, **0.57**, 0.85 | R7 |
| 2 | 0.790 | pass | 0.661 | 0.95, **0.57**, 0.85 | R7 |
| 3 | **0.726** | **fail (stop)** | 0.661 | 0.95, **0.48**, 0.75 | R2, R3, R5, R7 |

- At Lead 3 the model still beats persistence (R4 pass; Brier −0.142, p < 0.001), but balanced accuracy is 0.64 and
  it is not significantly better than climatology (p = 0.14).
- Leads 4–15, beyond the stopping point, are recorded for completeness: accuracy 0.60–0.68, and all fail R2, R3, R5
  and R7.

**Under a stricter, pre-registered stability rule (R7):**
- R7 requires at least 60% accuracy in each third of the evaluation period. The model **fails at every lead**. At
  Leads 1 and 2 it scores 0.95 for 2010 to about 2015, **0.57** for about 2015–2020, and 0.85 for about 2020–2026.
- At Leads 1 and 2 it passes the other six rules: sample size, accuracy, balanced accuracy, beating always-LOW and persistence, Brier
  score below persistence and climatology, and precision and recall ≥ 0.60.
- Without the two 2020 mobile-phone survey quarters it would pass all seven. This is reported as a sensitivity check
  only.

**Stability must therefore be confirmed on forecasts sealed before their outcomes exist.**
- The Lead-2 forecast for 2027-Q1 is sealed: P(HIGH) = 0.86, SHA-256 `94c62596…`. New forecasts are sealed each
  quarter.
- About ten scored quarters (late 2029) give a first independent check.
- The full sample-size rule (40 quarters) is reached in about 2037.

**Evidence status.** These quarters had been examined during development, so the results above are **development
evidence**, not an independent test.

## 7. Limitations

1. **Regional, not provincial.** SWS measures hunger for Balance Luzon only, so all five provinces receive the same
   food-insecurity forecast. Provinces differ only in their food-price pressure and vulnerability rank (§2.1), and
   neither is a measured food-insecurity rate. No provincial food-insecurity outcome exists for 2010–2026. The CBMS
   2024 local results are not public.
2. **LGU rankings reflect vulnerability, not measured food insecurity.**
   - The 142 cities and municipalities are ranked within their province by 0.6 × PSA 2021 poverty incidence + 0.4 ×
     PSA 2024 population density (both min-max normalized).
   - The current export multiplies this index by the regional probability. Because the probability is the same for
     every province, this does not change the order. The product is not shown as a risk level, since it would fall
     below 0.50 in towns of a HIGH region.
   - The outputs are labelled "priority ranking, not a measured rate".
   - **Correction:** the `note` column of `../IMPROVE_V2/out/lgu_rankings.csv` says that "most LGUs carry a
     province-mean poverty substitute". This is wrong. **141 of the 142 LGUs use their own PSA 2021 municipal
     estimate.** Only Lucena (a highly urbanized city, excluded from the PSA no-HUC table) uses the Quezon province
     value. The note appears on all 142 rows. The file is left unchanged, and this correction applies to it.
3. **Province food-price pressure is not a validated forecast.** π_price does not meet R1–R7 at Lead 1 or Lead 2
   (§2.1), so it is shown as a Low/Medium/High band for context only.
4. **News adds no measurable gain.**
   - The NLP pipeline (zero-shot XLM-RoBERTa, the bias-corrected FSSI, event categories, BERTopic) is implemented.
   - Adding its outputs did not improve the forecast: Brier +0.008 at Lead 1 and +0.015 at Lead 2.
   - A news-only model was the weakest.
   - Province-tagged news is sufficient in only 17% of province-quarters.
5. **External reference (face validity only).** The DOST-FNRI 2023 National Nutrition Survey reports that **19.1%** of
   CALABARZON households were moderately or severely food insecure (95% CI 17.0–21.1), against 31.4% nationally.
   This is a different measure from SWS hunger. It is cited as context, never used as a label.
6. **Known survey breaks.**
   - SWS used mobile-phone interviews in 2020-Q2 and 2020-Q3.
   - SWS changed its respondent base from household heads to adults from 2025-Q2.
   - Pre-2018 CPI values are PSA's later back-cast.
7. **Missing source.** BSP remittance data could not be retrieved automatically and is not used.

## 8. Effect on the hypotheses

| Hypothesis | Under the amended model |
|---|---|
| H1 (FSSI and food CPI deviation not among the strongest predictors) | **Not rejected.** Past hunger and world prices dominate; food prices carry about 6% of influence and news about 3%. |
| H2 (not reliable across lead times) | **Rejected under the thesis's 75% criterion up to Lead 2** (Maximum Reliable Lead Time = 2; Lead 3 fails at 0.726). **Not rejected under the stricter stability rule** (R7 fails at every lead). Both are reported; prospective confirmation is pending. |
| H3 (the combined model will not outperform the six comparators) | **Not rejected.** The model beats persistence, the news-only models and the government-only LightGBM, but not the PSA-only or combined logistic regressions significantly. |
| H4, H5 | Data collection in progress |

## 9. Wording changes needed in Chapters I and III

### 9.1 From province-level to regional food insecurity

Two wordings are given for the adviser to choose between.

**Decision (2026-11-03): Option A, chosen by the team, pending adviser confirmation.** Every province shows the regional
food-insecurity forecast as its headline. The province food-price pressure band and the vulnerability rank are shown
beside it and are never multiplied with it. Option B is kept below in case the adviser prefers it. This decision applies
to the IMPROVE_V2 alternative only. The main model is now P0H4 (see "Team decision" at the top).

#### Option A (chosen by the team, pending adviser confirmation): regional food-insecurity forecast, with provincial food-price pressure and vulnerability

This matches the design of §2.1.

| Where | Current | Proposed |
|---|---|---|
| §1.3 RQ2 (p. 10) | "furthest lead time … reliably forecast **province-level** food insecurity risk" | "… reliably forecast **regional (Balance Luzon) food insecurity** for the CALABARZON provinces, reported with each province's food-price pressure and vulnerability rank" |
| §1.3 RQ3 (p. 10), §1.4 H3 (p. 11) | "classifying **provincial** food insecurity risk" | "classifying **regional** food insecurity risk" |
| §1.4 (p. 11), dependent variable | "high or low, **of a CALABARZON province** in a given quarter" | "high or low **Balance Luzon hunger (> 11.3%)** in a given quarter, applied to every CALABARZON province" |
| §1.4 H2 (p. 11) | "classify whether a CALABARZON **province** is at high or low…" | "classify whether **regional hunger**, and hence each CALABARZON province's food-insecurity risk, will be high or low…" |
| Obj 2 I, II, IV (pp. 12–13) | "**province-level** classifications", "high-risk **provinces**" | "**quarterly** food-insecurity classifications for each province (regional forecast)", "high-risk **quarters**, with provinces ordered by food-price pressure and vulnerability" |
| Obj 3 (p. 13), Rule 4 (p. 48), Algorithm 5 (p. 46) | "from **validated province-level** forecasts" | "from the **regional food-insecurity forecast**. Provinces and LGUs are ordered by food-price pressure and PSA vulnerability (priority rankings, not measured rates), which never change the regional classification" |
| §1.7 (p. 15) | "SWS quarterly hunger data and PSA food price data will be used to **determine** food insecurity risk" | "SWS quarterly hunger defines the food-insecurity classification, which is regional. Provincial PSA food prices and PSA poverty and density data show how provinces differ within it; food prices and other indicators are also model **inputs**" |
| New sentence, §1.7 or §3.4.2 | — | "The food-insecurity classification is regional; differences between provinces come from food-price pressure and vulnerability, not from a provincial food-insecurity measurement." |
| §3.4.2 Eq. 3 and Table 3.4.2.3 (pp. 51–52) | Composite stress score, global median | Replaced by y = 1 if Balance Luzon hunger > 11.3% (fixed threshold). The province's price condition is reported beside it, not combined with it. |
| Eq. 5 and Table 3.4.2.4 (pp. 52–53) | Features FSSI, triggers, CPI_dev, unemployment, rice change | The input groups of §3 above |
| Algorithm 4 (pp. 43–45) | Optuna TPE, 100 trials | Chronological selection over a fixed eight-setting grid at each origin |
| Algorithm 3 (pp. 41–43), §3.4.4 (p. 57) | 75% mean fold accuracy only | 75% mean fold accuracy, reported together with a stability check across periods; confirmation on sealed forecasts |

#### Option B (alternative): regional forecast only, with provincial and municipal vulnerability ranking

The province food-price pressure band is left out. Provinces differ only by vulnerability rank.

| Where | Current | Proposed |
|---|---|---|
| §1.3 RQ2 (p. 10) | "furthest lead time … reliably forecast **province-level** food insecurity risk" | "… reliably forecast **regional (Balance Luzon) food insecurity**, with provincial and municipal vulnerability rankings" |
| §1.3 RQ3 (p. 10), §1.4 H3 (p. 11) | "classifying **provincial** food insecurity risk" | "classifying **regional** food insecurity risk" |
| §1.4 (p. 11), dependent variable | "high or low, **of a CALABARZON province** in a given quarter" | "high or low **Balance Luzon hunger (> 11.3%)** in a given quarter" |
| §1.4 H2 (p. 11) | "classify whether a CALABARZON **province** is at high or low…" | "classify whether **regional hunger** will be high or low…" |
| Obj 2 I, II, IV (pp. 12–13) | "**province-level** classifications", "high-risk **provinces**" | "**quarterly regional** classifications", "high-risk **quarters**" |
| Obj 3 (p. 13), Rule 4 (p. 48), Algorithm 5 (p. 46) | "from **validated province-level** forecasts" | "from the **regional food-insecurity forecast**, ranked within each province by PSA vulnerability weights (priority rankings, not measured rates)" |
| §1.7 (p. 15) | "SWS quarterly hunger data and PSA food price data will be used to **determine** food insecurity risk" | "SWS quarterly hunger defines the forecast target; PSA food prices and other indicators are model **inputs**" |
| §3.4.2 Eq. 3 and Table 3.4.2.3 (pp. 51–52) | Composite stress score, global median | Replaced by y = 1 if Balance Luzon hunger > 11.3% (fixed threshold) |
| Eq. 5 and Table 3.4.2.4 (pp. 52–53) | Features FSSI, triggers, CPI_dev, unemployment, rice change | The input groups of §3 above |
| Algorithm 4 (pp. 43–45) | Optuna TPE, 100 trials | Chronological selection over a fixed eight-setting grid at each origin |
| Algorithm 3 (pp. 41–43), §3.4.4 (p. 57) | 75% mean fold accuracy only | 75% mean fold accuracy, reported together with a stability check across periods; confirmation on sealed forecasts |

### 9.2 The fourteen internal consistency fixes (`DECISIONS.md`, W1–W14)

| # | Fix | Under the amendment |
|---|---|---|
| W1 | One study window | **Amend:** the target history is 1998–2026 (evaluation 2010–2026). News remains 2020–2026. |
| W2 | RQ5: DA evaluators assess both functional accuracy and usability (DEPDev optional) | Applies |
| W3 | Population density: PSA 2024 POPCEN, not the 2020 census | Applies |
| W4 | FNRI reference: NNS 2023 only | Applies |
| W5 | Objective 4 lists the six comparators of RQ3 and H3 | Applies |
| W6 | Article text truncated at 512 characters throughout | Applies |
| W7 | Missing values left missing, never zero-filled | Applies |
| W8 | STAGED forecasts are not public until approved | Applies |
| W9 | No global-median threshold (Rule 3) | Superseded: Equation 3 is replaced; the 11.3% threshold is fixed in advance |
| W10 | Distinguish the two "CPI deviation" definitions | Superseded with Equation 3; food CPI inflation enters as an input |
| W11 | Define Equation 4's baseline and Rule 7's rolling threshold | Applies to Rule 7. Equation 4 is optional if Equation 3 is replaced. |
| W12 | One LightGBM as the proposed model; the blend, if kept, as a comparison | Applies |
| W13 | State the corpus size actually used | Applies |
| W14 | DA evaluators do not annotate labels (labels are computed) | Applies |
