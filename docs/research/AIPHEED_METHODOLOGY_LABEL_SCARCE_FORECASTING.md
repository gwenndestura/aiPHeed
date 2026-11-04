# AIPHEED Methodology: Forecasting Provincial Food-Insecurity Risk with Scarce Labels

**Basis:** `AIPHEED_RELATED_LITERATURE_REVIEW.md` (26 sources) and AIPHEED experiments E137–E143, FI6-N, and FI9-N.
**Model family:** LightGBM (gradient-boosted decision trees), the same family as the XGBoost models of Westerveld et al. (2021) and Foini et al. (2023).

---

## 1. The principle borrowed from the literature

The reviewed systems predict food insecurity where no measurement exists by **borrowing labels measured at other places, times, or scales**:

| System | Label it learns from | What it predicts without a label |
|---|---|---|
| HungerMap LIVE (Martini et al., 2022) | WFP surveys where they exist | Areas and days without surveys |
| Balashankar et al. (2023) | IPC phases in many districts and countries | Future IPC phases, 3–12 months ahead |
| Foini et al. (2023) | Past food-consumption observations | The next 30 days |
| Lentz et al. (2019) | Malawi surveys, 2010–2011 | Village clusters in 2013 |

AIPHEED applies the same principle to CALABARZON. It learns from the food-insecurity measurements that exist and predicts the province-quarters that have no measurement:

| Label | Scale | Frequency | Role |
|---|---|---|---|
| **SWS involuntary hunger** | Area: NCR, Balance Luzon (contains CALABARZON), Visayas, Mindanao | Quarterly | The **time** signal, analogous to IPC/FCS in the literature |
| **FNRI HFIAS moderate-or-severe** | Province, nationwide | Survey rounds 2013, 2015, 2018/2019 (2021 pending) | The **provincial** signal |
| **FNRI 2023 NNS FIES** (CALABARZON 19.1%) | Region | One round | Agreement benchmark only; never pooled with HFIAS |

## 2. Forecasting task

| Item | Definition |
|---|---|
| Unit | Province *p* (Cavite, Laguna, Batangas, Rizal, Quezon); models are trained on every province and area with data |
| Issue date | First day of the quarter viewed on the dashboard (*t*), using only information released before that date |
| Targets | Quarters *t*+1 to *t*+4, that is 3, 6, 9, and 12 months ahead. *t*+1 is the dashboard target |
| Output | P(HIGH food-insecurity risk) per province and target quarter, with an interval and a HIGH / LOW / UNCERTAIN class |
| HIGH | The province's expected moderate-or-severe food insecurity in the target quarter is above the national level |
| Update | Re-issued automatically every quarter; each issue is sealed before its outcome exists |

## 3. Inputs, organized by the FAO four dimensions

Every value carries its **reference period** and **release date**. A forecast issued on date *d* uses only values released before *d* (the ragged-edge rule of Giannone, Reichlin and Small, 2008). A missing or late value enters as missing, with an availability flag. LightGBM handles missing inputs natively.

| FAO dimension / group | Indicators (provincial unless stated) | Source |
|---|---|---|
| Availability | Palay, corn, and fisheries production, year-on-year change; rice area and damage | PSA quarterly production; PRISM |
| Access | Food and rice CPI year-on-year (latest released month); retail rice prices; poverty incidence (SAE); unemployment (LFS); remittances | PSA, BSP |
| Utilization | Nutrition indicators from the latest NNS round | FNRI |
| Stability | Typhoon exposure; rainfall anomaly; ENSO status; disaster damage | IBTrACS, NASA POWER, PAGASA, NDRRMC |
| **News (NLP)** | FSSI v2 (volume-corrected food-stress index); attention (article volume relative to the province's past); BERTopic topic shares; event intensities for market, climate, employment, remittance, and poverty news | Publisher archive and GDELT, dated by publication time and collected continuously up to the issue date |
| Geospatial | Hazard exposure (DA AMIA CRVA); population density; agricultural land share; distance to major markets; island group | DA AMIA, PSA POPCEN 2024 |
| Label history | Latest released SWS reading for the area and its trend; the province's last measured HFIAS rounds | SWS, FNRI |

Label history is included because the reviewed studies consistently found the outcome's own history among the strongest predictors (Westerveld et al., 2021; Foini et al., 2023). News is the only input with no release lag. This is the property Balashankar et al. (2023) exploit.

## 4. Model architecture: three linked LightGBM stages

```
 News (continuous) ─┐
 FAO indicators ────┼─► Stage A0  Nowcast the SWS quarters not yet published (LightGBM)
 Latest SWS ────────┘        │
                             ▼
                     Stage A   Forecast area hunger, t+1 … t+4 (LightGBM, 4 areas pooled)
                             │
 HFIAS rounds ─► Stage B   Provincial relative risk (C4: cross-fitted LightGBM level
                             │                  + hierarchical survey anchor)
                             ▼
                     Stage C   Link area hunger and provincial risk to provincial
                               food insecurity, calibrated on the HFIAS rounds
                             │
                             ▼
              P(HIGH) per province × quarter, with interval → 142 LGU priorities
```

### Stage A0: nowcast the missing quarters
* **Why:** at the issue date, the most recent SWS rounds are often unpublished. HungerMap and Foini fill such gaps with real-time proxies.
* **Model:** a LightGBM regressor estimates the hunger level of each unpublished quarter. Inputs are that quarter's news and the government indicators already released.
* **Training rows:** every area-quarter with a published round. The nowcast enters Stage A as a feature.
* **Leakage control:** Stage A is trained on **out-of-fold** nowcasts, so it never sees an in-sample estimate.

### Stage A: forecast area hunger 1–4 quarters ahead
* **Model:** a LightGBM classifier (HIGH when area hunger is above its as-of trailing median) and a LightGBM regressor (hunger level). Both use the four SWS areas pooled.
* **Inputs:** Stage A0 nowcast, latest released reading, area news features, and area aggregates of the FAO indicators.
* **Horizon handling:** one model per horizon, or a single model with the horizon as a feature (the pooled-horizon design used by P0H4). The choice is made inside the training folds.
* **Settings:** shallow trees, monotone constraints where the sign is known (for example, higher food inflation does not lower risk), and calibration by Platt scaling on inner folds.
* **Regime shift:** a regime indicator covers the change in SWS respondents from household heads to adults in April 2025.

### Stage B: provincial relative risk (C4, already implemented)
* **Structural level:** cross-fitted LightGBM on poverty, prices, climate, and geography. Each province's level comes from a model that never saw its region.
* **Survey anchor:** hierarchical (region + province), estimated from how strongly measured deviations persisted between HFIAS rounds.
* **Output:** the relative logit *r̂_p* versus national, with its variance.
* **Current results** (survey-round walk-forward, E143): accuracy 0.903, precision 0.95, recall 0.90, F1 0.92, AUC 0.984, Brier score 0.190.

### Stage C: link the two scales
* **Link model:** logit(π_p,τ) = α + γ · logit(H_a(p),τ) + δ · r̂_p + ε, where:
  * π_p,τ is the province's HFIAS moderate-or-severe prevalence in survey quarter τ;
  * H_a(p),τ is the SWS hunger of the province's area in the same quarter.
* **Estimation:** fitted on every province-round nationwide (203 rows) across survey rounds, with survey errors as weights.
* **What it gives:** this is the step that turns a quarterly regional signal into a quarterly provincial forecast. γ measures how much provincial food insecurity moves with area hunger. If γ is not distinguishable from 0, the forecast collapses to Stage B and the time signal adds nothing.
* **Forecast:** Stage A's distribution for H_a(p),t+h is passed through the link with Stage B's *r̂_p*, by Monte Carlo. This gives P(π_p,t+h > national) with an interval that carries the uncertainty of all three stages.

### LGU disaggregation (Objective 3)
* **Priority score:** province P(HIGH) × vulnerability. Vulnerability is half PSA SAE 2021 poverty percentile and half POPCEN 2024 density percentile, across the 142 LGUs.
* **Interval:** the province interval is carried through.
* **Labelling:** reported as a vulnerability-weighted priority, not a municipal measurement.

## 5. News pipeline (Objective 1)

1. **Collection:** continuous, publication-dated collection from several outlets plus GDELT, so that every SWS area, not only CALABARZON, has news coverage. Articles that restate a released SWS or PSA statistic are flagged and excluded, so the label cannot leak into the inputs.
2. **Relevance and geotagging:** articles are tagged to province, LGU, and SWS area.
3. **Tier 1, sentiment:** zero-shot XLM-RoBERTa (Filipino–English) food-stress scores per article.
4. **Tier 2, topics:** BERTopic topics per province-quarter and area-quarter.
5. **Index:** FSSI v2 is the as-of composition anomaly with empirical-Bayes shrinkage, separating attention from content. Its volume dependence was reduced from 0.44 to 0.05.
6. **Accuracy check:** sentiment accuracy is measured on an independent, owner-approved labelled sample before any accuracy claim is made.

## 6. Evaluation design (Objectives 2 and 4)

All protocols are locked before any score is computed, every issued forecast is sealed, and every comparison uses identical rows and folds.

| Stage | Validated against | Design |
|---|---|---|
| A0 / A | SWS area-quarters (real labels) | Walk-forward expanding window; issue at quarter start; *h* = 1–4; pseudo-real-time (each issue date replays the data released by then) |
| B | HFIAS province-rounds | Rolling survey-round origins plus an untouched round (2013 now; 2021 ENNS when obtained) |
| C | HFIAS province-rounds | Leave-round-out: does the area-hunger link improve on Stage B alone? |
| Benchmark | 2023 NNS FIES (CALABARZON 19.1%) | Agreement only |

**Metrics:** accuracy, precision, recall, and F1 for the HIGH class; AUC-ROC; Brier score; calibration error; 90% interval coverage; confusion matrices; cluster-bootstrap confidence intervals.

**Baselines** (Chapter I §1.3, identical rows):

| Code | Baseline |
|---|---|
| B1 | Naive persistence (latest reading) |
| B2 | Logistic regression, combined features |
| B3 | Logistic regression, government indicators only (PSA-only) |
| B4 | Logistic regression, news only (NLP-only) |
| B5 | LightGBM, government indicators only |
| B6 | LightGBM, news only |

B4 and B6 become constructible at area level once every area has news coverage.

**Maximum reliable lead time (Objective 2.V):** the largest *h* at which every pre-registered criterion holds. The criteria are:
* AUC and recall thresholds;
* calibration;
* lower Brier score than persistence, with the confidence interval excluding zero.

The lead time is determined empirically and is not assumed to be 12 months.

**News contribution:** measured as the difference between the full model and B5 at each horizon. A news claim is made only where this difference is significant.

## 7. How each objective is addressed

| Objective | Delivered by |
|---|---|
| 1. NLP pipeline, bias-corrected FSSI, province-quarter patterns | Section 5; FSSI v2 and topics enter Stages A0 and A as inputs |
| 2. LightGBM evaluation and maximum reliable lead time | Stages A–C; walk-forward at *h* = 1–4 with all Chapter I metrics |
| 3. LGU rankings from province forecasts | Section 4, LGU disaggregation |
| 4. Comparison with persistence, PSA-only, NLP-only, logistic regression | Section 6 baselines B1–B6 on identical rows |
| 5. Dashboard, ISO/IEC 25010, NNS face validity | Quarterly sealed issue to the dashboard after the release gate; ISO/IEC 25010 with DA IV-A evaluators; agreement with NNS 2019 (HFIAS) and 2023 (FIES) |

## 8. What the methodology can claim, and what it needs

**It can claim:**
* A province-quarter forecast for quarters with no measurement, produced by borrowing measured labels at two scales, as HungerMap does for unsurveyed areas.
* Stage A is validated every quarter against real SWS outcomes.
* Stages B and C are validated against real provincial HFIAS outcomes.

**It cannot claim:** a direct accuracy score at the province-quarter level. No such measurement exists for CALABARZON. This is the same position as HungerMap's estimates for unsurveyed areas.

**Expected difficulty, stated in advance.**
* The literature's 3–12-month gains came from thousands of labelled district-periods.
* AIPHEED's earlier single-area test (FI9-N, 62 quarters) found that news improved next-quarter probability quality when the quarter's news was complete, but nothing discriminated at the two-quarter dashboard horizon.
* This design gives news its best chance by:
  * pooling four areas;
  * adding area-specific news;
  * nowcasting the unpublished quarters.
* The evaluation reports the result whichever way it falls.

**Data and decisions required:**

| # | Item | Why |
|---|---|---|
| 1 | SWS area history from 2010 (owner decision; the current study-window rule is 2021+) | About 250 labelled area-quarters instead of about 88. Stage C also needs SWS values at the 2013–2019 survey quarters |
| 2 | Area-level news for NCR, Visayas, and Mindanao (GDELT, public) | Pooling and the NLP-only baselines |
| 3 | FNRI 2021 ENNS provincial HFIAS | The untouched provincial test of Stages B and C |
