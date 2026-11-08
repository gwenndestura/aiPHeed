# aiPHeed thesis objectives audit (revised 2026-11-04)

**Scope and evidence.**
* This revision replaces the first draft of the same date.
* No experiment was run. Every conclusion cites a locked study, a source file or a live API response.
* Live responses come from `TestClient(app.main.app)` on branch `pfi/survey-anchored-final` @ `b2fe16cd`, at
  2026-11-04 00:51 PHT.

**Corrections to the first draft.**
* It read the dashboard's next-quarter target as FI6 "Lead 1". Under the dashboard's own issue rule (section 5), the
  correct comparison is **FI6 Lead 2**, which is weaker.
* It did not separate risk estimation from measurement, or from forecasting. Sections 1, 5 and 7 now do.

---

## 1. Corrected purpose and definition of aiPHeed

**What aiPHeed is.** A **geospatial food-insecurity RISK estimation and forecasting system** for DA Region IV-A.
It estimates the *possibility* that an area may experience food-insecurity conditions, using indicators linked to
food availability, access, utilization, stability and vulnerability.

**What it is not.** It does not measure, diagnose or confirm food insecurity, or the share of food-insecure
households.

| Output | Meaning | Not |
|---|---|---|
| HIGH risk | The available evidence points to a greater potential for food-insecurity conditions | a finding that the area is food insecure |
| LOW risk | The available evidence points to a comparatively lower potential | a guarantee of food security |
| Risk score | A model estimate, for example P(defined elevated-risk state) | the % of people who are food insecure |
| Forecast | An estimate of risk in a future quarter | a confirmation that food insecurity will occur |

**Measured outcomes still have a role.** They (HFIAS, FIES, SWS hunger) are the **reference evidence** used to test
whether risk estimates are credible. They are not the product.

## 2. FAO conceptual framework (verified against FAO texts)

**Definition.** "Food security exists when all people, at all times, have physical and economic access to
sufficient, safe and nutritious food…"
* Source: World Food Summit Plan of Action, para. 1, FAO, Rome, 1996,
  https://www.fao.org/4/w3613e/w3613e00.htm.

**Four dimensions.** From FAO, *Policy Brief: Food Security*, June 2006, Issue 2
(https://www.fao.org/fileadmin/templates/faoitaly/documents/pdf/pdf_Food_Security_Cocept_Note.pdf; text read
from the PDF):

| Dimension | FAO wording (paraphrased closely) |
|---|---|
| Food availability | sufficient quantities of food of appropriate quality, supplied through domestic production or imports (including food aid) |
| Food access | access by individuals to adequate resources (entitlements) for acquiring appropriate foods for a nutritious diet |
| Utilization | use of food through adequate diet, clean water, sanitation and health care to reach nutritional well-being |
| Stability | access to adequate food at all times, without risk of losing it to sudden shocks (economic or climatic crises) or cyclical events (seasonal food insecurity); it refers to both availability and access |

**Vulnerability.** "The presence of factors that place people at risk of becoming food-insecure or malnourished,
including factors that affect their ability to cope."
* Source: FAO, *The State of Food Insecurity in the World 2001*, Glossary,
  https://www.fao.org/4/y1500e/y1500e06.htm.
* The same glossary: food insecurity "may be chronic, seasonal or transitory".

**Not verified.** The EC-FAO *Introduction to the Basic Concepts of Food Security* (al936e) returned HTTP 403 and
was not used. No definition is attributed to it.

**How aiPHeed uses the framework.** Risk = exposure to factors that threaten availability, access or stability,
combined with the households' (in)ability to cope (poverty, density). Utilization is part of the concept, but
aiPHeed has no data for it (section 3).

## 3. Indicator → FAO dimension → risk mapping (actual datasets and code)

"Model input" means the feature appears in the implementation named.

| Indicator (source; level; period) | FAO dimension | What it contributes to risk | Model input in |
|---|---|---|---|
| Food and rice CPI YoY (PSA; region monthly 1994+; province annual 2012=100 and 2018=100) | Access (affordability); Stability (price shocks) | Price rises reduce what poor households can buy | FI5/FI6 (`cpi_food_yoy`, `cpi_rice_yoy`, region); E137–E140 (`m_food_cpi_yoy`, `m_rice_cpi_yoy`, province); CH1/P0H4 (FIRI v2 price families) |
| Per-capita food threshold vs national (PSA; province; 2006–2023) | Access | Cost of the minimum food basket | E137–E140 (`m_food_threshold_rel`) |
| Poverty, subsistence incidence, poverty gap (PSA; province triennial; SAE 2021 municipal) | Access (economic); Vulnerability (ability to cope) | Share of households without the income to buy enough food | FI5/FI6 (`poverty_inc`, region); E137–E140 (main signal); LGU weights |
| Population density (PSA census 2010–2024) | Vulnerability (exposure; market dependence) | Dense, market-dependent populations are exposed to price shocks | E137–E140 (`p_density`); LGU weights |
| Palay + corn production (PSA quarterly; province 2012–2026) | Availability; Stability | Local supply and farm income | FI6 (`palay_yoy`, region); E137–E140 (`c_agri_pc`, `c_agri_yoy`) |
| Fisheries production (PSA quarterly; province) | Availability | Local fish supply and fisher income | E137–E140 (`c_fish_yoy`) |
| Rainfall anomaly (NASA POWER; province centroids) | Stability (climate shock) → availability | Drought or flood stress on production | FI6 (`rain_anom_3m`); E137–E140 (`c_rain_anom_6m`) |
| Tropical cyclones within 150–200 km (NOAA IBTrACS) | Stability | Shocks to supply, incomes and markets | FI6 (`tc_exposure_q`); E137–E140 (`c_tc_4q`, `c_tc_clim`) |
| ENSO (NOAA ONI) | Stability | Seasonal climate risk | FI5/FI6 (`oni`) |
| Unemployment rate (PSA LFS; **national only** on OpenSTAT) | Access (income) | Loss of income | FI5/FI6 (national); **not provincial** |
| OFW remittances (BSP via WDI; **national, annual**) | Access (income) | Household income buffer | FI5/FI6 (`remit_yoy`, national); **not provincial** |
| Fish kills (FIRI v2) | Availability (local) | Local supply shock | CH1/P0H4 lists it; live explainability reports `no_model_input` |
| News FSSI and topics (XLM-R zero-shot + BERTopic; CALABARZON queries; 2021+ Google News headlines; 2012+ publisher archive, 95 % Rappler) | Supporting evidence for access, availability and stability events | Timely reports of shortages, price spikes and disasters | FI5/FI6/FI6-N news composites (regional model); **not in E137–E140** (no national coverage) |
| Diet quality, nutrition, WASH, health | **Utilization** | — | **None.** No quarterly or provincial series held. FNRI NNS nutrition indicators are periodic and not loaded. |
| SWS involuntary hunger (Balance Luzon; quarterly 1998+) | Measured outcome (experience of hunger, severe end) | **Reference evidence**, regional | FI5/FI6 target. Also an *input* to CH1/P0H4's hunger term. |
| HFIAS (FNRI 2015, ENNS 2018/19, province) and FIES (PSA SDG 2.1.2; regional 2023) | Measured outcome (household food insecurity experience) | **Reference evidence**, provincial and regional | E137–E140 target (HFIAS); FIES used only for external agreement (E137 S11) |

**Representation of each dimension.**

| Dimension | Status | Reason |
|---|---|---|
| Availability | **Partially represented** | Production and fisheries; no stocks, trade or imports |
| Access | **Directly represented** for prices and poverty; **partially** for income | Employment and remittances are national only; no market-access measure |
| Utilization | **Missing** | No data held |
| Stability | **Partially represented** | Weather, cyclones, ENSO and YoY changes; no income-volatility measure |
| Vulnerability | **Represented** through poverty and density | — |

**The five contributor groups and FAO.**

| Group | FAO dimension | Evidence status |
|---|---|---|
| Market and food prices | access and stability | E138–E140: **no incremental information** for measured provincial risk |
| Climate and agricultural stress | availability and stability | No incremental information |
| Employment and OFW remittances | access | Not available provincially; context only |
| News and NLP | cross-cutting supporting evidence | Regional only |
| Poverty and social vulnerability | access and vulnerability | **The main measured signal** |

## 4. How available Philippine data address the measurement gaps

**The intended use.**
* Frequently updated indicators (monthly CPI, quarterly production, monthly rainfall, real-time cyclones, news)
  give a **continuous risk picture**.
* Triennial poverty statistics and rare HFIAS/FIES rounds **anchor and test** that picture.

**What the implementation does.**
1. **Release dates are kept for every series**, so no future value enters a historical forecast:
   * `app/fi5/sources.py`;
   * `app/e137/features.py` (tested in `test_e137.py` and `test_e139.py`).
2. **Measured outcomes are never interpolated or copied into provinces.**
   * E137–E140 train only on HFIAS rows that exist (125).
   * SWS stays regional.
   * The five uncertain survey rows (headline-only decks) are dropped, not filled.
3. **CPI, poverty and news are never used as outcomes** in E137–E140, FI5 or FI6.
   * Exception: **CH1/P0H4**, whose HIGH label combines a *price condition* built from the same price indicators it
     predicts with the SWS hunger reading. That makes it a model-defined proxy target (section 7d).
4. **Missing data are never treated as zero risk.** LightGBM keeps NaN. The linear models impute the training median
   and add explicit missing flags for survey history.

**The limit.** Indicators can be updated every quarter. A quarterly *validation* outcome exists only regionally (SWS),
not by province. This is a validation limitation. It does not by itself make quarterly risk estimation impossible.

## 5. Actual food insecurity, estimated risk and future risk forecasts

These are different tasks with different evidence:

| Task | Question | Evidence available |
|---|---|---|
| Measurement | What share of households is food insecure? | FNRI/PSA surveys only. aiPHeed does not do this. |
| Structural risk estimation | Which areas have greater potential for food insecurity? | E137–E140 against measured HFIAS |
| Current-quarter risk estimation | Risk this quarter | No quarterly provincial reference |
| **Next-quarter risk forecast** | Risk in Q+1, from information available now | Regional SWS only (FI5/FI6) |
| Geographic cross-validation | Does it work in places it did not see? | E137–E140 LORO/LOPO/ISLAND. **Not** evidence of forecasting skill. |

**The dashboard's next-quarter clock** (`/api/v1/quarters`, live):
* calendar quarter **2026-Q4**, target **2027-Q1**;
* origin 2026-10-01, information cutoff "2026-10-01 (exclusive)";
* latest complete data quarter 2026-Q3, `lead_from_latest_data_quarter: 2`;
* rule: "next calendar quarter after the one in which the dashboard is viewed (Asia/Manila)".

The target therefore **advances dynamically by one quarter**, which is correct.

**The information horizon is two quarters, not one.**
* Forecasts are issued at the **start** of the viewing quarter, using information published before it.
* The 2026-Q3 SWS reading (published 14 Oct) is not yet used.
* So the dashboard's "next quarter" forecast matches **FI6 Lead 2**: issued at the end of 2026-Q3, for 2027-Q1.
* It would match FI6 Lead 1 only if the forecast were re-issued after the previous quarter's SWS release
  (mid-quarter; possible in 20 of 23 quarters, E130), or at the end of the viewing quarter.

## 6. Reassessment of the four thesis objectives

**Objective 1: XLM-R zero-shot + BERTopic, bias-corrected FSSI and latent patterns per province-quarter.**
* **Implemented:**
  * `app/fi5/nlp.py`: 9,628 headlines (2021-01 to 2026-10). `joeddav/xlm-roberta-large-xnli` scored 3,794 that
    passed the relevance gate; 1,147 are domain-relevant. BERTopic gives 11 topics (fitted on 2021–22, then frozen).
  * **FSSI bias correction:** each event counted once, outlet weight 1/√n, share of collected events, province
    shrinkage (k = 10), as-of z-scores. Output: `data/fi5/nlp`.
  * `app/fi6/news_events.py`: 62,698 archive articles (2008–2026), 14,358 scored, 2,879 relevant events. Output:
    `data/fi6/news_archive`.
* **Limits:**
  * Coverage is CALABARZON queries only. 95 % of the archive is one outlet.
  * Province attribution is mostly body mentions (283 articles tagged at province level, 1,875 at LGU level).
  * **There is no independent human-labelled check of sentiment or relevance accuracy.** A 200-article kit exists
    but is excluded by owner rule.
* **Status: PARTIALLY ACHIEVED.** Implemented; accuracy not validated.

**Objective 2: LightGBM; accuracy, precision, recall, F1, AUC-ROC; expanding-window walk-forward; multiple leads.**
* **Implemented:**
  * FI5 and FI6: expanding window, Leads 1–4, 62 target quarters (2010–2026), all metrics. The target is SWS hunger
    above its 5-year normal by more than its margin of error. That is a *risk-of-elevated-hunger* outcome, measured
    regionally.
  * E137–E140: provincial risk vs measured HFIAS.
* **Result:** no lead passes for LightGBM (FI5, FI6, FI9-Z). The required minimum (Lead 1) is not met (sections 7c
  and 9).
* **Status: implementation ACHIEVED; Lead ≥ 1 validated forecasting NOT ACHIEVED.**

**Objective 3: LGU rankings from validated province forecasts, weighted by PSA poverty and density.**
* **Implemented:** `/api/v1/provinces/{id}/municipalities` serves **142 LGUs**: Batangas 34, Cavite 23, Laguna 30,
  Quezon 41, Rizal 14.
  * Formula: the province CH1/P0H4 value × vulnerability (0.6 × poverty_norm + 0.4 × density_norm, PSA SAE 2021 and
    POPCEN 2024; `app/quarterly/lgu_audit.py`).
  * Label shown: "Indicative … not a measured municipal food-insecurity rate … EXPERIMENTAL".
* **Problem:** the province value is not a validated food-insecurity forecast. The weights (60/40) also differ from
  FI5/E139 (50/50).
* **Status: PARTIALLY ACHIEVED.** The rankings exist and are labelled as vulnerability, but not "from validated
  province forecasts".

**Objective 4: LightGBM vs persistence, PSA-only, NLP-only and logistic regression.**
* **Implemented:** FI5 and FI6, identical origins, targets, cutoffs and periods (section 8).
* **Result:** LightGBM beats PSA-only and logistic regression in Brier at Lead 1, but **never beats persistence**.
* **Status: ACHIEVED as a comparison.** The finding is that there is no improvement over persistence.

## 7. Results, kept separate

**(a) Structural risk estimation, validated against measured HFIAS** (E139/E140, development evidence).

| Model | Unseen region (LORO) |
|---|---|
| E139 linear-prior LightGBM (0 trees) | AUC 0.915, EB 0.192, accuracy 0.774 [0.66, 0.86], ECE 0.066 |
| E140 LightGBM trees | AUC 0.960, EB 0.182 |

* External agreement: regional PSA FIES 2023, Spearman 0.79 (E137 S11).
* **This establishes** that indicator-based risk ranks provinces in line with measured food insecurity in regions
  the model did not see.
* **It does not establish** quarterly changes, a forecast lead, or prevalence.
* **Gates:** E139 rejected (G2 beyond region history; G3 by 0.002); E140 rejected (T2 trees vs prior; G2; G8
  island transfer).

**(b) Geographic generalisation (E140 LightGBM).**
* LOPO: AUC 0.975.
* ISLAND: 0.353, which **fails**. E139's prior: 0.787.
* Geographic AUC is **not** evidence of next-quarter accuracy.

**(c) Next-quarter forecasting** (FI6, regional SWS, walk-forward, 62 quarters, 11 HIGH).

| Information horizon | LightGBM accuracy / recall / AUC / Brier | Persistence | Relevance to the dashboard |
|---|---|---|---|
| FI6 Lead 1 | 0.839 / 0.273 / 0.686 / 0.129 | **0.871 / 0.545 / 0.743 / 0.116** | the dashboard target *if* re-issued after the previous quarter's SWS release |
| **FI6 Lead 2** | **0.806 / 0.000 / 0.469 / 0.163** | 0.710 / 0.091 / 0.581 / 0.198 | **the dashboard target as currently issued** |

* At Lead 2 LightGBM never predicts HIGH: its 0.806 accuracy comes from "always LOW" (climatology 0.823).
* There is no provincial quarterly outcome, so provincial next-quarter forecasts are **not testable**.

**(d) The CH1/P0H4 accuracies are not food-insecurity validation.**
* Reported accuracies: 0.84–0.91 (`/api/v1/final/risk/evaluation`).
* P0H4's target multiplies a price condition (built from the price indicators the model uses) by the SWS hunger
  probability.
* Validating it with its own price predictors is circular. The forensic audit (11-03) classes it as evidence
  class B (proxy).

## 8. LightGBM vs all four baselines (FI6, identical origins and cutoffs)

Brier difference = LightGBM − baseline (negative favours LightGBM).

| Lead | Model | Accuracy | BA | Precision | Recall | F1 | AUC | Brier | Brier difference [95 % CI] |
|---|---|---|---|---|---|---|---|---|---|
| 1 | LightGBM | 0.839 | 0.617 | 0.600 | 0.273 | 0.375 | 0.686 | 0.129 | — |
| 1 | Naive persistence | 0.871 | 0.743 | 0.667 | 0.545 | 0.600 | 0.743 | 0.116 | +0.012 [−0.02, +0.06] |
| 1 | PSA-only | 0.742 | 0.522 | 0.222 | 0.182 | 0.200 | 0.567 | 0.191 | −0.062 [−0.11, −0.01] |
| 1 | NLP-only | 0.806 | 0.597 | 0.429 | 0.273 | 0.333 | 0.533 | 0.174 | −0.045 [−0.09, −0.01] |
| 1 | Logistic regression | 0.742 | 0.594 | 0.308 | 0.364 | 0.333 | 0.668 | 0.169 | −0.041 [−0.08, 0.00] |
| 2 | LightGBM | 0.806 | 0.490 | 0.000 | 0.000 | 0.000 | 0.469 | 0.163 | — |
| 2 | Naive persistence | 0.710 | 0.467 | 0.111 | 0.091 | 0.100 | 0.581 | 0.198 | −0.035 [−0.09, +0.02] |
| 2 | PSA-only | 0.677 | 0.412 | 0.000 | 0.000 | 0.000 | 0.390 | 0.227 | −0.063 [−0.10, −0.02] |
| 2 | NLP-only | 0.790 | 0.587 | 0.375 | 0.273 | 0.316 | 0.561 | 0.161 | +0.003 [−0.05, +0.04] |
| 2 | Logistic regression | 0.629 | 0.489 | 0.167 | 0.273 | 0.207 | 0.442 | 0.247 | −0.084 [−0.16, −0.02] |

* Source: `docs/fi6/RESULTS.md`; Leads 3–4 are in the same table.
* FI6-N at Lead 1: government + news Brier 0.119 vs government only 0.129 (−0.0099 [−0.021, −0.002]). It is still
  not better than persistence (0.116).
* **Conclusion:**
  * LightGBM is better calibrated than the weak baselines.
  * It does **not** improve on persistence at Lead 1.
  * At Lead 2 none of the five models has skill (AUC ≤ 0.58).

## 9. Maximum scientifically supported forecast horizon

* **LightGBM: none.** No lead passes the locked reliability rules (FI5, FI6, FI9-Z).
* **The only passing method:** naive persistence at FI6 Lead 1, under FI6's rule. It fails FI9-Z's HIGH-recall
  requirement (0.55 < 0.60).
* **Provincial forecasting:** no horizon can be tested (no quarterly provincial outcome). E139/E140 show no quarterly
  skill: removing every quarterly indicator changes nothing.
* **The mandatory minimum** (a validated Lead 1 forecast whenever viewed) is **not met**.

## 10. Dashboard and API audit (live)

| Check | Finding | Status |
|---|---|---|
| The next-quarter target advances dynamically | Yes: `/api/v1/quarters` gives 2026-Q4 → 2027-Q1 (Asia/Manila clock) | **ACHIEVED** |
| The displayed next-quarter output is a food-insecurity risk forecast | **No.** The map, left panel and LGU list show CH1/P0H4 for 2027-Q1, for example Quezon 0.9521, and four provinces have the same 0.9521. Registry status: `legacy_incumbent`, never gate-approved. Labelled in `AboutModal.tsx`, `FoodInsecurityStatus.tsx` and `AnimatedStatWidgets.tsx` as a "price-pressure risk index … not a food-insecurity forecast". | **NOT ACHIEVED** (labelled honestly) |
| Released forecasts separated from validation-pending outputs | Yes. `/api/v1/final/food-insecurity/outlook` returns `validation_pending`, `forecast: null`; candidate routes need admin. But the card says "N of 16 checks", a constant hard-coded in `api/v1/registry.py`, which is wrong for E137–E140 (11–14 checks). | **PARTIALLY ACHIEVED** |
| The contributor panel reflects the five groups | **No.** `/api/v1/explainability`: Market / Prices 100 %; Climate, Fish Kill and Employment `no_model_input`; OFW `no_data`. Poverty and News are not groups. Fish Kill is. This is a true account of a price-only model, but not of the five FAO-linked groups. | **NOT ACHIEVED** |
| All 142 LGUs, with accurate vulnerability labels | 142 served; the label says not a measured rate and EXPERIMENTAL. But most LGUs show `riskLevel: high` from the price index. | **PARTIALLY ACHIEVED** |
| HIGH/LOW explained as a possibility, not confirmation | The About modal and status card explain it is not a food-insecurity forecast. No place states the FAO-based HIGH/LOW meaning in section 1. | **PARTIALLY ACHIEVED** |
| Data cutoffs, source dates, uncertainty visible | The API provides them (information cutoff, SWS fieldwork and publication dates, `asOf`). No dashboard component renders `forecastTarget.information_cutoff`. Uncertainty is shown only for the regional SWS card history. | **PARTIALLY ACHIEVED** |

## 11. Limitations and missing evidence

1. **No quarterly provincial measured outcome.** HFIAS exists for 2015 and 2018/19 by province; FIES for 2023 by
   region. Provincial next-quarter forecasts cannot be validated out-of-time.
2. **The regional quarterly outcome (SWS) is noisy.** About 300 respondents per area per round. 74 % of HIGH/LOW
   labels lie inside the margin of error (FI5). This caps how far any model can improve on persistence.
3. **Prospective test not yet scored.** The sealed FI5/FI6 forecasts for 2026-Q4 to 2027-Q3 are scored when SWS
   publishes them (from about Jan–Feb 2027). FI9-Z needs at least 12 prospective quarters with at least 3 HIGH.
4. **Utilization is unmeasured.** Employment and remittances are national only. News covers CALABARZON only and has
   no human-validated accuracy.
5. **E139/E140 are development evidence.** All HFIAS rows were seen before. Sealed predictions await the next
   provincial round (E138 `e324433c…`, E139 `0bcb5584…`).

## 12. Changes needed to align the manuscript and the software

**Manuscript.**
1. Define the target as **food-insecurity risk** (section 1), grounded in FAO 1996/2006 and the SOFI 2001
   vulnerability concept. Remove any wording that implies prevalence or confirmed hunger.
2. Separate three kinds of validation:
   * measured-outcome agreement (HFIAS, FIES, SWS);
   * structural risk validation (E137–E140);
   * next-quarter forecast validation (FI5/FI6).
   Do not cite geographic AUC or CH1/P0H4 accuracy as forecasting skill.
3. Report the FI6 results in full, including Lead 2 (section 8), and that the dashboard's issue rule corresponds to
   Lead 2.
4. Objective 3: state that the rankings are vulnerability-weighted and inherit the province estimate's unvalidated
   status.
5. Limitations: the items in section 11.

**Software** (no new model; no new UI elements without the owner's approval).
1. **Issue timing.** Re-issue the next-quarter forecast after the previous quarter's SWS release, so the dashboard's
   Q+1 uses the FI6 Lead-1 information horizon. This changes timing only. It does not create skill: persistence
   still beats LightGBM at Lead 1.
2. **Check counts.** Replace the hard-coded `acceptance_checks_total: 16` with each candidate's own count from the
   registry.
3. **One set of LGU weights.** Use either 60/40 (`lgu_audit.py`) or 50/50 (FI5/E139), and document the choice.
4. **CH1/P0H4 on the map.** Keep it as a labelled price-pressure context layer, or withdraw it. This is an owner
   decision. It must never be presented as the food-insecurity forecast.
5. **Contributor panel.** Its backend text should say that the served model covers the market group only, and list
   poverty, climate, employment and news as "not model inputs" with the FAO dimension of each. Text fields only,
   under the no-new-UI rule.

## 13. Final acceptance checklist

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Purpose defined as risk, not prevalence | **PARTIALLY ACHIEVED** | This audit; About modal; manuscript not yet revised |
| 2 | FAO framework, verified | **ACHIEVED** (in this audit) | FAO 1996, 2006, 2001 (section 2) |
| 3 | Indicators mapped to FAO dimensions | **ACHIEVED** | Section 3 |
| 4 | Availability represented | PARTIALLY ACHIEVED | production and fisheries only |
| 5 | Access represented | PARTIALLY ACHIEVED | prices and poverty; income is national only |
| 6 | Utilization represented | **NOT ACHIEVED** | no data |
| 7 | Stability represented | PARTIALLY ACHIEVED | climate, cyclones, ENSO |
| 8 | Release-date discipline, no leakage | **ACHIEVED** | `fi5/sources.py`, `e137/features.py`, tests |
| 9 | No fabricated, interpolated or copied labels | **ACHIEVED** (E137–E140, FI5/FI6) | — |
| 10 | No model-defined proxy target shown as validation | **NOT ACHIEVED** for CH1/P0H4 | Section 7d |
| 11 | Obj. 1 NLP pipeline implemented | **ACHIEVED** | `fi5/nlp.py`, `fi6/news_events.py` |
| 12 | Obj. 1 NLP accuracy validated | **CANNOT YET BE VALIDATED** | no human-labelled set (owner rule) |
| 13 | Obj. 2 LightGBM walk-forward, all metrics, multiple leads | **ACHIEVED** (implementation) | FI5, FI6 |
| 14 | Obj. 2 validated forecast at Lead ≥ 1 | **NOT ACHIEVED** | Sections 8 and 9 |
| 15 | Mandatory one-quarter-ahead risk forecast, validated, on the dashboard | **NOT ACHIEVED**; provincial version **CANNOT YET BE VALIDATED** | Sections 5, 7c, 10 |
| 16 | Dynamic next-quarter target | **ACHIEVED** | `/api/v1/quarters` |
| 17 | Structural provincial risk validated against measured outcomes | **PARTIALLY ACHIEVED** (development evidence; gates rejected) | E139/E140 |
| 18 | Obj. 3 LGU rankings, 142 LGUs, vulnerability-labelled | **PARTIALLY ACHIEVED** | API; `lgu_audit.py` |
| 19 | Obj. 3 rankings from validated province forecasts | **NOT ACHIEVED** | no validated province forecast |
| 20 | Obj. 4 comparison with all four baselines | **ACHIEVED** | FI5, FI6 |
| 21 | LightGBM beats persistence | **NOT ACHIEVED** | FI6 Lead 1 +0.012 [−0.02, +0.06] |
| 22 | Released vs pending outputs separated in the API | **ACHIEVED** (wrong check count) | `api/v1/registry.py` |
| 23 | Contributor panel reflects the five groups | **NOT ACHIEVED** | Market 100 % |
| 24 | Cutoffs, source dates and uncertainty visible on the dashboard | **PARTIALLY ACHIEVED** | API yes; UI partial |
| 25 | Prospective (sealed) forecast scoring | **CANNOT YET BE VALIDATED** | first SWS release for 2026-Q4 expected about Jan–Feb 2027 |
