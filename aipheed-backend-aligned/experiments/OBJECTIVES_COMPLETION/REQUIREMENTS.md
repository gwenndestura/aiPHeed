# OBJECTIVES_COMPLETION, Step 1: requirements table

**Written:** 2026-11-03. **Scope:** the food-insecurity forecast (SWS Balance Luzon hunger > 11.3%; food prices are
inputs only), as final in IMPROVE_V2 (commits `89d109e`, `65c9f85`; the reference arm, sealed, SHA-256 `94c62596…`).
No model is retrained, tuned or added.

**Wording source:** Chapter I §1.5.2 of `THESIS 2 (11).pdf`, extract
`FINAL_THESIS_OBJECTIVES/sources/chapter1_THESIS2_11_extract.txt` (lines 173–219), quoted exactly below. The null
hypotheses (§1.4, lines 140–171) are listed where an objective is tested through one.

**Categories for what is missing:**
- **(a)** doable now from existing data and code;
- **(b)** blocked by data not yet available (named);
- **(c)** needs people.

## The one fact that limits Objectives 2, 3 and 4

The objectives speak of **"province-level classifications"** and **"validated province-level forecasts"**. The
food-insecurity outcome that exists is **regional**: SWS Balance Luzon hunger, one value per quarter for all of Luzon
outside Metro Manila. **No provincial or municipal food-insecurity outcome exists for 2010–2026** (CBMS 2024 LGU
results are not public: `FINAL_OBJECTIVE_ACHIEVEMENT/sources/LOCAL_DATA_SEARCH_LOG.md`). So the food-insecurity forecast
gives every CALABARZON province the same value, and a province-level food-insecurity classification **cannot be scored**
with data available today. This is not reworded away below.

## Objective 1

> "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic
> unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity
> risk patterns per province-quarter from a Filipino-English news corpus."

Related null hypothesis H1: "The Food Stress Sentiment Index (FSSI) and food CPI deviation will not be among the
strongest predictors of food insecurity risk in CALABARZON when examined through SHAP feature attribution."

| Item | Content |
|---|---|
| **Literally requires** | (i) Tier 1: zero-shot XLM-RoBERTa sentiment on Filipino-English news; (ii) Tier 2: BERTopic topics; (iii) a **bias-corrected FSSI**; (iv) **latent risk patterns per province-quarter**; (v) from a Filipino-English corpus |
| **Existing evidence** | Pipeline code: `backend/app/news/pipeline_v3.py` (FSSI-v3, bias-weighted intensity), `backend/app/ml/nlp/topic_model.py` and `backend/app/news/topics.py` (BERTopic). Corpus: 9,659 RSS headlines, 58,576 GDELT documents (`FIRI_V2_DATA_AUDIT/FIRI_V2_COMPLETE_DATA_AUDIT.md`). Validation: disaster news vs typhoon counts ρ = 0.81 (E112). Coverage: provincial FSSI-v3 sufficient in 20 of 115 province-quarters (17%); only 33% of headlines carry a province tag; regional N1R from 2021-Q3. Forecast value: none (IMPROVE_V2 §7: no arm gained from news, smallest p 0.11; news-only model worst; news share in SHAP 0.8–4.1%). BERTopic topics are mostly place names (`docs/final_system/THESIS_OBJECTIVE_ASSESSMENT.md`). |
| **Missing** | 1. One end-to-end description of the two tiers with their measured outputs, in one place. 2. A **per-province-quarter** FSSI: 83% of province-quarters are below the 5-headline minimum. 3. Topics that describe food-insecurity patterns rather than places. 4. H1: under SHAP, FSSI and food CPI are **not** among the strongest predictors (hunger history about 65%, world prices about 22%, food prices about 6%, news about 3%). |
| **Category** | 1: **(a)**. 2: **(b)**, more province-tagged Filipino-English news (the corpus is what it is; nothing to add without new collection). 3: **(a)** only as documentation of what BERTopic produced; re-tuning BERTopic would be new modelling, which this task excludes. 4: **(a)**, report the SHAP result (H1 not rejected). |

## Objective 2 I–IV

> "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics:
> I. Accuracy, to measure overall correctness of high- and low-risk province-level classifications
> II. Precision and Recall, to assess the model's ability to correctly identify high-risk provinces while minimizing
> false alarms and missed detections respectively
> III. F1-Score, to capture the balance between Precision and Recall given the binary classification task
> IV. AUC-ROC, to evaluate the model's ability to distinguish between high- and low-risk provinces across
> classification thresholds"

| Item | Content |
|---|---|
| **Literally requires** | Accuracy, precision, recall, F1 and AUC-ROC of the proposed LightGBM, on **high/low province-level** classifications |
| **Existing evidence** | IMPROVE_V2 `RESULTS.md` §2, `out/results.json`: the reference LightGBM on the regional food-insecurity target, 62 quarters (2010–2026). Lead 1: accuracy 0.790, precision 0.812, recall 0.907, F1 0.857, AUC 0.702, Brier 0.188, TP/FP/FN/TN 39/9/4/10. Lead 2: the same classification counts, AUC 0.704, Brier 0.184. |
| **Missing** | 1. One clean metrics table with confusion matrices (the numbers exist, spread across files). 2. **The province level**: the metrics are of one regional classification per quarter, not of provinces. |
| **Category** | 1: **(a)**. 2: **(b)**, a provincial food-insecurity outcome (provincial FIES or CBMS 2024 LGU food-security aggregates). |

## Objective 2 V

> "Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically
> determine the furthest horizon at which reliable forecasting is achievable"

Related H2: "aiPHeed will not reliably classify whether a CALABARZON province is at high or low food insecurity risk
across multiple forward-looking lead times."

| Item | Content |
|---|---|
| **Literally requires** | Walk-forward expanding-window evaluation at several leads, and the **furthest reliable horizon** determined from it |
| **Existing evidence** | IMPROVE_V2 §3: walk-forward expanding window from 1998-Q3, Leads 1 and 2, unchanged R1–R7 rules counted in quarters. **No lead passes; maximum reliable lead = 0.** The reference fails only R7 (thirds 0.952 / 0.571 / 0.850). Seal: Lead 2 for 2027-Q1 (`IMPROVE_V2/SEAL_LEDGER.md`). HISTORY_RETRAIN gives the same verdict. |
| **Missing** | 1. The method and result written as one Objective-2V section, with the prospective schedule (dates). 2. "Multiple lead times": the food-insecurity forecast was tested at Leads 1–2 only. Leads 3+ were tested only for the earlier targets (E109–E112: none reliable). 3. **Prospective confirmation**: no sealed quarter can be scored before SWS publishes 2027-Q1. |
| **Category** | 1: **(a)**. 2: **(a)** only as a report of the earlier lead-3+ results. A new lead-3+ run of the food-insecurity model would be new model output, so I have not proposed it. 3: **(b)**, SWS 2027-Q1 and later readings. Lead-1 issuance waits for the 2027-01-01 issue date. |

## Objective 3

> "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level
> forecasts, using PSA published poverty incidence and population density as vulnerability weights."

Related H4: "The vulnerability-weighted spatial disaggregation of province-level forecasts will not produce municipal
and city risk rankings that are consistent with DA Region IV-A evaluators' assessments of relative food insecurity
vulnerability across CALABARZON, as evaluated through the aiPHeed Post-Survey Questionnaire."

| Item | Content |
|---|---|
| **Literally requires** | Municipal and city rankings, **from validated province-level forecasts**, weighted by PSA poverty incidence and population density |
| **Existing evidence** | IMPROVE_V2 `out/lgu_rankings.csv`: 142 LGUs, approved method (0.6 poverty + 0.4 density within province × probability), for 2027-Q1 (P = 0.860), labelled "priority ranking, not a measured food-insecurity rate". Backend limitation: many LGUs carry a province-mean poverty substitute. |
| **Missing** | 1. The rankings packaged with their method and labels for the thesis. 2. **"Validated"**: the forecast passes no reliability rule, so it is not validated. 3. **"Province-level"**: the forecast is regional, so all provinces get the same value and the order comes from the weights alone. 4. External check of the rankings against an LGU outcome. 5. H4: comparison with DA evaluators' assessments. |
| **Category** | 1: **(a)**. 2: **(b)**, sealed 2027+ quarters that pass R1–R7 (at least 10). 3: **(b)**, a provincial food-insecurity outcome. 4: **(b)**, CBMS 2024 LGU food-security results (not public). 5: **(c)**, DA Region IV-A evaluators (Post-Survey Questionnaire). |

## Objective 4

> "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches:
> I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic
> regression baseline"

Related H3: "The LightGBM model that combines news signals and government data will not outperform the six comparison
models, naive persistence, three logistic regression variants (news-only, government data-only, and combined), and two
LightGBM variants trained on only one data source at a time…"

| Item | Content |
|---|---|
| **Literally requires** | The proposed LightGBM compared with the four named baselines |
| **Existing evidence** | IMPROVE_V2 §6, same quarters, Holm across five comparisons. REF beats persistence (Holm p 0.001), NLP-only (0.008 / 0.014) and ALWAYS-HIGH (0.028 / 0.023). It is **not** significantly better than PSA-only (Holm p 0.511 / 0.080) or logistic regression (0.511 / 0.080). PSA-only, NLP-only and LOGIT are logistic regressions on government-only, news-only and combined inputs, so H3's three LR variants are covered. |
| **Missing** | 1. One clean comparison table stating where the model is and is not superior. 2. **H3's two single-source LightGBM variants** (LightGBM on government data only, and on news only) were not run for the food-insecurity target. Note that the "proposed" model carried forward (REF) uses no news, so it is itself a government-data LightGBM. |
| **Category** | 1: **(a)**. 2: technically (a), but it means **fitting new models**, which this task forbids. I need your decision whether H3 is reported as tested only against the four objective baselines. |

## Objective 5

> "To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the
> ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI
> NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor."

Related H5: "aiPHeed will not receive favorable functional suitability, accuracy, and usability ratings from DA Region
IV-A evaluators under the ISO/IEC 25010 software quality model."

| Item | Content |
|---|---|
| **Literally requires** | (i) A deployed public geospatial dashboard with forecast maps and early-warning alerts; (ii) an ISO/IEC 25010 evaluation with DA Region IV-A evaluators; (iii) validation against **FNRI NNS 2019 and 2023 CALABARZON** prevalence |
| **Existing evidence** | (i) The dashboard is deployed and works (map, forecasts, drivers, news, history; tests pass), but it shows the served Chapter I combined proxy (P0H4), **not** the food-insecurity forecast. (ii) An evaluation package exists: `E114_Final_Run/E114_OBJECTIVE5_EVALUATION_PACKAGE.md` (SUS, sections B–D, an ISO/IEC 25010 section E, scenarios, analysis plan). It was written for an earlier outlook design (its scenarios describe a carried-forward reading and an 80% band). (iii) FNRI: the project audit (`2026-10-13_E13…/OUTCOME_DATA_AUDIT.md`) keeps **one** regional FIES value (2025, 22.6%). It says the 2021 and 2023 CALABARZON values were removed on 2026-09-01 as unverifiable, and that 2018–2019 used HFIAS, not FIES. **Conflict:** `FIRI_V2_DATA_AUDIT/FINAL_THESIS_OBJECTIVE_ASSESSMENT.md` cites "2023 CALABARZON 19.1%". |
| **Missing** | 1. The dashboard showing the food-insecurity forecast, with its labels fixed. In the frontend, `MapTour.tsx:45` says "Forecasts are reviewed by Department of Agriculture staff before they are published" and `pdfReport.ts:635` says "REVIEWED BY · DA REGION IV-A"; I have found no evidence of such a review. "Observed" labels appear in the timeline and history. 2. An instrument and test checklist matched to the food-insecurity dashboard. 3. The evaluation itself. 4. Verified NNS 2019 and 2023 CALABARZON figures. |
| **Category** | 1: **(a)** to specify; implementing it **needs your approval** (Step 3). 2: **(a)**. 3: **(c)**, DA Region IV-A evaluators. 4: **(b)**, verified FNRI NNS 2019 and 2023 CALABARZON prevalence. The 2023 value conflicts between files and the 2019 survey used HFIAS. A face-validity check can be done now only against what is verified (2025, 22.6%), and it would be reported as a substitute, not as the objective. |

## Summary: what Step 2 would complete (category (a) only)

| Objective | Step 2 deliverable |
|---|---|
| 1 | End-to-end pipeline document with measured outputs (coverage, validation ρ = 0.81, BERTopic output), the forecast-value result, and the H1 SHAP result |
| 2 I–IV | One metrics table with confusion matrices, Leads 1–2, from IMPROVE_V2 outputs, labelled as **regional** classifications |
| 2 V | Method plus result (maximum reliable lead = 0; R7 only), the earlier lead-3+ results cited, and the prospective calendar (`seal_next.py`, `score_seal.py`, ≥ 10 quarters) |
| 3 | The 142 rankings packaged and labelled; validation and H4 listed as blocked or waiting |
| 4 | Comparison table with raw and Holm p, where superior and where not |
| 5 | An ISO/IEC 25010 questionnaire (Likert, every characteristic) and a test checklist for the food-insecurity dashboard; the needed dashboard changes listed; FNRI 2025 face-validity check reported as a substitute |

**Two decisions for you before Step 2:**
1. **H3:** report it as tested against the four objective baselines only, or approve fitting the two single-source
   LightGBM variants? Fitting them is new modelling, so this task currently excludes it.
2. **FNRI:** do you have verified NNS 2019 and 2023 CALABARZON figures? Without them, Objective 5's validation stays
   "waiting for data", and only the 2025 regional value (22.6%) is used, as a labelled substitute.
