# Chapter 3 amendment: aiPHeed as a food-insecurity forecasting system

**Status:** proposed amendment for the adviser's review (2026-11-03). Results are development evidence unless stated
otherwise. Sources: `E99_REPRODUCTION.md`, `../IMPROVE_V2/RESULTS.md`, `../OBJECTIVES_COMPLETION/OBJ4_H3_COMPARISON.md`,
`DECISIONS.md`, `../P0H4_LEAD12_REVIEW/out/price_warning.json` (province food-price pressure),
`../IMPROVE_V2/out/lgu_rankings.csv` (vulnerability inputs).

## Team decision (latest): C-b as the main model; REF+news and REF reported beside it

**Decision (2026-11-03, later than the REF+news decision below; it supersedes it), made by the team and pending adviser
confirmation.**

**The model.** C-b is the REF+news LightGBM with its 8 raw news columns replaced by **one NLP input, the bias-corrected
FSSI-v3 as an anomaly against its own past 8 quarters** (`../NEW_MODEL/NEWS_V2/`). The target, inputs, settings, grid,
seed, leads and window are otherwise IMPROVE_V2's.

**This is a recorded decision, not a test result.** C-b did not pass its own fixed improvement rule over REF+news: the
Lead-1 Brier gain is not significant (Holm p 0.348; Lead 2 p 0.060).

**Evidence** (62 quarters 2010–2026; development evidence):

| | Lead 1 | Lead 2 |
|---|---|---|
| Accuracy | 0.790 | 0.790 |
| Balanced accuracy | 0.717 | 0.717 |
| Precision / recall | 0.812 / 0.907 | 0.812 / 0.907 |
| F1 | 0.857 | 0.857 |
| AUC | 0.702 | 0.704 |
| Brier | 0.187 | 0.184 |
| R1–R7 | fails R7 only (2015–2020 third 12/21) | fails R7 only |

- **Algorithm 3:** Maximum Reliable Lead Time **2** (Lead 3 0.726). **R1–R7:** 0.
- **Objective 4 / H3** (Holm):
  - better than persistence, NLP-only, always-HIGH and the government-only LightGBM at both leads, and the NLP-only
    LightGBM at Lead 1;
  - **not** better than the PSA-only or combined logistic regressions;
  - so **H3 is not rejected**.
- **NLP, stated plainly.** The FSSI input is included and **changes no classification**. C-b equals the same model
  without news in 66 of 67 quarters, and its SHAP share is 0.0–0.1%. Objective 1's pipeline is built and evaluated;
  its forecast value is nil with news available only from 2021.
- **Seal and protocol.**
  - C-b's forecasts issued 2026-10-01 are sealed in `../NEW_MODEL/NEWS_V2/sealed_prospective_CB.csv` (SHA-256
    `67baec66…`, P 0.8595, HIGH), after the results were known.
  - The prospective protocol applies to C-b through `PROSPECTIVE_ADDENDUM_CB.md` (SHA-256 `fc110575…`). Its first
    four 2027 quarters are the Algorithm 4 blind holdout.

**Proposed thesis sentences (for the adviser):**
- Ch. I §1.5.2 / Ch. III §3.4: "The proposed model is a LightGBM forecasting regional (Balance Luzon) SWS hunger above
  11.3% from hunger history, food prices, world prices, climate, agricultural supply and an NLP-derived Food Stress
  Sentiment Index."
- Results, NLP: "The FSSI was integrated as a model input and evaluated by ablation; with news available only from
  2021, it did not change any classification. NLP signals are additionally used for explanations and staged early
  warnings."
- Province and LGU wording: Option C (§2.1, §9.1), unchanged.

## Earlier team decision (superseded 2026-11-03 by C-b): REF+news as the main model; P0H4 kept as the documented alternative

**Decision (2026-11-03, later than the P0H4 decision below; it supersedes it), made by the team and pending adviser
confirmation.**

**Main model.** The food-insecurity model **IMPROVE_V2 "REF+news"**: SWS Balance Luzon involuntary hunger > 11.3%,
forecast by the IMPROVE_V2 reference LightGBM with the news columns inside the forecast, exactly as specified in
IMPROVE_V2 (no tuning, no new settings). It is chosen because the thesis title ("Using NLP and Machine Learning")
requires news inside the forecast.

**Reported beside it.** REF, the same model without news.

| Model | Lead 1 accuracy | Lead 2 accuracy | R1–R7 failed |
|---|---|---|---|
| REF+news | 0.758 | 0.758 | R3, R5, R7 |
| REF | 0.790 | 0.790 | R7 |

On the stored IMPROVE_V2 results, **news does not improve the forecast**: Brier is worse by +0.008 at Lead 1
(p 0.82) and by +0.015 at Lead 2 (p 0.96). This is reported, not hidden.

**Multi-source design around it:**

| Source | Role |
|---|---|
| SWS hunger | **when**: the regional food-insecurity forecast and its class, the same for all five provinces |
| PSA poverty incidence among families (2023, Table 1) | **where**: weights the province score (Option C, §2.1); never changes the class |
| PSA 2021 city and municipal SAE poverty (60%) and 2024 density (40%) | **where**: LGU priority within the province (Objective 3); Lucena uses PSA's own 2021 value (Table 2a) |
| PSA food poverty (subsistence incidence, 2023) | context text only, with its precision; not used for ranking |
| PSA food prices | **province pressure**: the P0H4 price-part band, shown beside the score as context; changes nothing |
| News | **explanation and early warning** (provincial GDELT flags are staged for human confirmation and never public), as well as a model input |
| DOST-FNRI 2023 | **check**: face validity only |

**Province design: Option C** (§2.1 and §9.1), the team's choice, pending adviser confirmation.
- Each province's score is the regional food-insecurity forecast weighted by its PSA poverty incidence.
- The class is always the regional class.
- Options A and B are kept as alternatives.
- It is served by `AIPHEED_MAP_MODEL=foodinsecurity` (`../FOOD_INSECURITY_SYSTEM/PLAN.md`, `STEP4_RESULTS.md`).

**Alternatives kept, not deleted:**
- **P0H4** (next section) is the documented alternative.
- **REF** without news is reported beside the main model.

Evidence for REF+news is in `../OPTION_1/`.

## Earlier team decision (superseded 2026-11-03): P0H4 as the main model (pending adviser confirmation)

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

### 2.1 What each province is shown

#### Option C (the team's choice, 2026-11-03, pending adviser confirmation): regional food-insecurity forecast weighted by provincial poverty; class always regional

**The food-insecurity classification is regional. The province score weights it by provincial poverty and never
changes the class.**

| Element | What it is | Same for every province? | Role |
|---|---|---|---|
| **Class (colour)** | HIGH when the regional REF+news probability P(Balance Luzon hunger > 11.3%) ≥ 0.50 | Yes | The risk classification |
| **Province score** | score_p = P_reg × pov_p / max_k pov_k, where pov is the PSA 2023 poverty incidence among families (Table 1). The poorest province shows P_reg itself | No | Order of the provinces (a priority score, not a probability) |
| Food-price pressure | The P0H4 price-part band (Low < 0.33 ≤ Medium < 0.67 ≤ High) | No | Context only |
| Food poverty | PSA 2023 subsistence incidence among families, with "low precision (CV > 30%)" where true (all but Rizal) | No | Context only, not used for ranking |
| News | Regional sentence (E112 categories) and provincial sentence (E85 GDELT categories). The provincial flag is staged for human confirmation and never shown in public text | No | Explanation, early warning |

**Rules.**
- The weighting never lowers the class. A province with score < 0.50 is still HIGH when the region is HIGH.
- The order is fixed by poverty in every quarter. What changes over time is the regional probability, the price band
  and the news.
- **LGUs:** 0.6 × PSA 2021 poverty + 0.4 × density, min-max within the province, times the province score
  (Objective 3). Lucena uses PSA's own 2021 value (Table 2a, 10%). Colour = the regional class.

**Issued forecasts (2026-Q4, 2027-Q1; P_reg 0.869, HIGH):**

| Province | Poverty 2023 | Score |
|---|---|---|
| Quezon | 6.9% | 0.869 |
| Rizal | 5.6% | 0.705 |
| Laguna | 5.4% | 0.680 |
| Batangas | 4.9% | 0.617 |
| Cavite | 4.3% | 0.542 |

All five are HIGH.

#### Option A (earlier team choice, now an alternative): regional headline, with food-price pressure and vulnerability rank beside it

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

**Decision (2026-11-03, latest): Option C, chosen by the team, pending adviser confirmation.** It applies to the main
model, REF+news (see "Team decision" at the top).
- Every province's score is the regional food-insecurity forecast weighted by its PSA 2023 poverty incidence among
  families.
- The class is always the regional class.
- Food-price pressure, food poverty and news are context.

Options A and B are kept below in case the adviser prefers them. The earlier Option A decision is superseded.

#### Option C (chosen by the team, pending adviser confirmation): regional food-insecurity forecast weighted by provincial poverty; class always regional

| Where | Current | Proposed |
|---|---|---|
| §1.3 RQ2 (p. 10) | "furthest lead time … reliably forecast **province-level** food insecurity risk" | "… reliably forecast **regional (Balance Luzon) food insecurity** for the CALABARZON provinces, with each province weighted by its PSA poverty incidence" |
| §1.3 RQ3 (p. 10), §1.4 H3 (p. 11) | "classifying **provincial** food insecurity risk" | "classifying **regional** food insecurity risk" |
| §1.4 (p. 11), dependent variable | "high or low, **of a CALABARZON province** in a given quarter" | "high or low **Balance Luzon hunger (> 11.3%)** in a given quarter, applied to every CALABARZON province" |
| §1.4 H2 (p. 11) | "classify whether a CALABARZON **province** is at high or low…" | "classify whether **regional hunger**, and hence every CALABARZON province's food-insecurity class, will be high or low…" |
| Obj 2 I, II, IV (pp. 12–13) | "**province-level** classifications", "high-risk **provinces**" | "**quarterly regional** classifications applied to each province", "high-risk **quarters**, with provinces ordered by a poverty-weighted priority score" |
| Obj 3 (p. 13), Rule 4 (p. 48), Algorithm 5 (p. 46) | "from **validated province-level** forecasts" | "from the **regional food-insecurity forecast**, which passed Algorithm 3 at Leads 1–2. Provinces are weighted by PSA poverty incidence among families (2023), and LGUs are ranked within each province by PSA 2021 poverty (60%) and density (40%). These are priority rankings, not measured rates, and never change the class" |
| §1.7 (p. 15) | "SWS quarterly hunger data and PSA food price data will be used to **determine** food insecurity risk" | "SWS quarterly hunger defines the food-insecurity classification, which is regional. PSA poverty weights the provinces. PSA food prices are model **inputs** and a context band" |
| New sentence, §1.7 or §3.4.2 | — | "The food-insecurity classification is regional; each province's score weights it by PSA poverty incidence and never changes the class." |
| §1.5.2 Obj 1 | FSSI per province-quarter as a model input | "regional news signals as model inputs; provincial GDELT categories as explanation and early-warning context, with flags staged for human confirmation" |
| §3.4.2 Eq. 3 and Table 3.4.2.3 (pp. 51–52) | Composite stress score, global median | Replaced by y = 1 if Balance Luzon hunger > 11.3% (fixed threshold) |
| Algorithm 3 (pp. 41–43), §3.4.4 (p. 57) | 75% mean fold accuracy only | "75% mean fold accuracy, reported with the stricter rules R1–R7, which REF+news fails (Maximum Reliable Lead Time 2 under the 75% rule, 0 under R1–R7); confirmation on sealed forecasts" |

The Eq. 5 and Algorithm 4 rows are the same as in Option A.

#### Option A (earlier team choice, now an alternative): regional food-insecurity forecast, with provincial food-price pressure and vulnerability

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
