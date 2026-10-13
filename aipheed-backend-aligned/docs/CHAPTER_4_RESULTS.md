# CHAPTER IV
## RESULTS AND DISCUSSION

This chapter reports the results of aiPHeed as implemented under the approved
methodology of Chapter III, organized by the Specific Objectives in Section
1.5.2. Every figure is generated from the pipeline's artifacts by
`scripts/build_results_docs.py`.

### 4.1 Summary of Objective Accomplishment

**Table 4.1** *Objective, Method, Component, Output, Evidence and Status*

| Objective | Approved Method | Backend Component | Required Output | Evidence | Status | Remaining Gap |
|---|---|---|---|---|---|---|
| 1. Design a two-tier pipeline (zero-shot XLM-RoBERTa + BERTopic) producing the bias-corrected FSSI and latent risk patterns per province-quarter | Algorithm 1; Equations 1-2; BERTopic | `nlp/classifier.py`, `features/fssi_builder.py`, `nlp/topic_model.py` | FSSI, lags and acceleration per province-quarter; topic proportions per province-quarter | FSSI from 69 retained articles in 33 of 120 province-quarters; BERTopic: 66 topics over 5184 articles, proportions for 116 province-quarters | ACHIEVED | News coverage: 87 province-quarters carry no news and are filled under Section 3.3.2.6 (Rule 5 flags them) |
| 2. Evaluate the LightGBM model with accuracy, precision, recall, F1 and AUC-ROC, and determine the furthest reliable lead time | Algorithms 3 and 4; walk-forward CV; four-quarter holdout | `training/trainer.py` | Five metrics on the holdout; Maximum Reliable Lead Time | Accuracy 0.3000, precision 0.9125, recall 0.3000, F1 0.3495, AUC-ROC 0.7222; lead time 0 | ACHIEVED | The evaluation is complete. Targets: F1 not met, AUC-ROC not met; no forward lead time is reliable. Publication at lead time 0 is an open decision (Section 4.9) |
| 3. Produce municipal and city risk rankings from validated province forecasts using poverty incidence and population density | Algorithm 5; Equation 6 | `inference/disaggregator.py` | Ranked list of 142 LGUs per quarter with disaggregation label and data sufficiency flag | 142 LGUs ranked per quarter, every row labelled (verify_consistency) | PARTIALLY ACHIEVED | The province forecasts do not meet the Section 3.4.4 targets, so they are not 'validated' in that sense; agreement with DA evaluators (H4) awaits the System Accuracy Questionnaire |
| 4. Compare the LightGBM model against the baseline approaches | Same walk-forward folds, gap and hyperparameters for all | `training/evaluator.py` | Comparison table of the five metrics | Table 4.5 | ACHIEVED | The comparison is complete; whether the model is better is Hypothesis 3 |
| 5. Deploy a public geospatial dashboard with forecast maps and early-warning alerts; evaluate it under ISO/IEC 25010; validate against NNS 2019 and 2023 | FastAPI + React; Rule 7 alerts with review; ISO/IEC 25010 questionnaires; NNS anchor | `api/v1`, `frontend/`, `scripts/iso25010_summary.py`, `scripts/face_validity.py` | Public dashboard; ISO/IEC 25010 ratings; NNS comparison | Dashboard, province ranking, SHAP explanations, municipal rankings and confirmed alerts run locally | PARTIALLY ACHIEVED | Public deployment of this version not done; ISO/IEC 25010 responses not yet collected; NNS cycles unverified: NNS 2019, NNS 2023 |

### 4.2 Data

The news corpus holds 6,085 articles, 5,184 dated inside the
2020-Q1 to 2025-Q4 window, of which 804 were geocoded to a CALABARZON
province. The Food Stress Sentiment Index rests on 69 retained articles in
33 of the 120 province-quarters; the remaining province-quarters carry no news
and are forward-filled or zero-filled under Section 3.3.2.6, and Rule 5 flags them. The
model was trained on 95 labelled province-quarters (2020-Q2 to
2025-Q4), 47 HIGH and 48 LOW under Equation 3. Five
quarters carry no label because no SWS survey round was fielded in them.

### 4.3 Specific Objective 1 and Research Question 1

**Table 4.2** *SHAP Feature Attribution of the Served Model*

| Rank | Feature | Share of total attribution |
|---:|---|---:|
| 1 | Unemployment Rate | 21.9% |
| 2 | FSSI (2 Quarters Prior) | 19.9% |
| 3 | Food Stress Sentiment Index | 19.9% |
| 4 | Food CPI Growth vs Province's Recent Average | 11.7% |
| 5 | Rice Price Change | 10.8% |
| 6 | FSSI (Prior Quarter) | 9.6% |
| 7 | Climate & Hazard News Signal | 6.3% |
| 8 | FSSI Acceleration | 0.0% |
| 9 | OFW Remittance News Signal | 0.0% |
| 10 | Employment News Signal | 0.0% |
| 11 | Market & Price News Signal | 0.0% |
| 12 | Fish Kill / Aquaculture News Signal | 0.0% |

Food CPI deviation ranked 4 (11.7%),
and the Food Stress Sentiment Index family carried 49.4%, led by
FSSI (2 Quarters Prior) at rank 2. NLP features carried
55.7% of the attribution in total.

**Table 4.3** *Largest BERTopic Topics*

| Topic | Articles | Top terms |
|---:|---:|---|
| 0 | 615 | philippines, manila, agriculture da, department agriculture, agriculture |
| 1 | 541 | central luzon, central, ndrrmc, agaton, province |
| 2 | 223 | urban farming, farming, agriculture, food crises, food crisis |
| 3 | 197 | food poverty, poverty pandemic, extreme poverty, reducing poverty, poverty alleviation |
| 4 | 140 | hunger community, rising hunger, addressing hunger, hunger poverty, hunger pandemic |
| 5 | 124 | food crisis, food supply, hunger, agriculture secretary, agri chief |
| 6 | 111 | manila bulletin, philippine, manila, filipino, philippines |
| 7 | 110 | agriculture, farmers nbsp, agricultural, vegetable, farming |
| 8 | 97 | philippines, philippine, food supply, food inflation, policy |
| 9 | 95 | manila philippines, philippine, filipino, manila, survey filipinos |

BERTopic grouped 5184 articles into 66 topics (1245 outliers) and expressed them as topic proportions for 116 province-quarters, the latent risk patterns Objective 1 asks for.

### 4.4 Specific Objective 2

**Table 4.4** *Lead Time Discovery (Algorithm 3)*

| k (quarters ahead) | Folds | Accuracy | Precision | Recall | F1 | AUC-ROC | Meets 75%? |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 7 | 0.6286 | 0.7962 | 0.6286 | 0.6652 | 0.4792 | No |

The Maximum Reliable Lead Time is 0: walk-forward accuracy did not reach 75% at any
forward horizon tested.

**Table 4.5** *Holdout Evaluation (Algorithm 4)*

| Metric | Value | Section 3.4.4 target |
|---|---:|---|
| Accuracy | 0.3000 | |
| Precision | 0.9125 | |
| Recall | 0.3000 | |
| F1-Score | 0.3495 | 0.75, not met |
| AUC-ROC | 0.7222 | 0.80, not met |

### 4.5 Specific Objective 3

Province probabilities were distributed to 142 cities and municipalities with
Algorithm 5 (0.6 x poverty incidence + 0.4 x population density, normalized within each
province). Every row carries the Rule 8 disaggregation label and the Rule 5 data
sufficiency flag. Agreement with DA Region IV-A evaluators' assessment (Hypothesis 4)
awaits the System Accuracy Questionnaire.

### 4.6 Specific Objective 4

**Table 4.6** *Comparison Against the Baseline Approaches*

| Approach | Accuracy | Precision | Recall | F1 | AUC-ROC |
|---|---:|---:|---:|---:|---:|
| **aiPHeed LightGBM (NLP + government)** | 0.5818 | 0.7453 | 0.5818 | 0.5518 | 0.6302 |
| Naive persistence | 0.8000 | 0.8080 | 0.8000 | 0.8016 | 0.8030 |
| Logistic regression, government indicators only | 0.5818 | 0.5787 | 0.5818 | 0.5801 | 0.5702 |
| Logistic regression, NLP features only | 0.5455 | 0.6029 | 0.5455 | 0.5415 | 0.6309 |
| Logistic regression, combined features | 0.5455 | 0.5489 | 0.5455 | 0.5470 | 0.5399 |
| LightGBM, government indicators only | 0.6000 | 0.6320 | 0.6000 | 0.6032 | 0.7121 |
| LightGBM, NLP features only | 0.6000 | 0.6222 | 0.6000 | 0.6040 | 0.6680 |

Outperforming the combined model on both accuracy and AUC-ROC: Naive persistence; LightGBM, NLP features only; LightGBM, government indicators only.

### 4.7 Specific Objective 5

The system runs as a FastAPI service and a React dashboard showing the provincial risk
map with each province's probability and rank, SHAP explanations including the features
that separate each province from the next one down, the municipal rankings, the news
evidence, and early-warning alerts. Alerts follow Rule 7 and appear only after an
administrator confirms them; forecasts move from STAGED to PUBLISHED only on review.

The ISO/IEC 25010 evaluation by 25 DA Region IV-A and 25 DEPDev Region IV-A evaluators
has not yet been conducted; `scripts/iso25010_summary.py` will summarise the two Google
Forms exports once collected. For the face-validity anchor, the verified NNS cycle on file is
NNS 2025 (CALABARZON 22.6%);
NNS 2019, NNS 2023 could not be verified and are not used.

### 4.8 Summary of Hypothesis Testing

| Hypothesis | Result | Basis |
|---|---|---|
| H1: FSSI and food CPI deviation among the strongest predictors | Partially supported | Table 4.2 |
| H2: reliable classification across multiple forward lead times | Not supported | Maximum Reliable Lead Time 0 |
| H3: the combined LightGBM outperforms all six baselines | Not supported | Table 4.6 |
| H4: municipal rankings consistent with DA evaluators | Pending | System Accuracy Questionnaire |
| H5: favorable ISO/IEC 25010 ratings | Pending | ISO/IEC 25010 questionnaires |

### 4.9 Methodology Decisions Awaiting the Adviser

1. **Publishing at a Maximum Reliable Lead Time of 0.** Section 3.4.4 states that a lead time or configuration below the thresholds is not published, and Rule 3 requires features from before the forecast period. The system publishes same-quarter estimates, labelled as such. Publish them, or show no forecast?
2. **Section 3.3.2.7 is cited but absent from the manuscript.** The selection procedure retains a different set of features from Equation 5's list on this data. The model trains on Equation 5's list. Which is authoritative?
3. **Food-nexus validity guard in Algorithm 1.** Articles with no food, hunger or eating term are scored 0 before the 0.30 threshold. Chapter III names the threshold as the only gate. Keep the guard, or remove it and rescore?
4. **Likert interpretation scale for the ISO/IEC 25010 questionnaires.** Chapter III does not state the verbal interpretation bands; scripts/iso25010_summary.py reports means and standard deviations and applies a scale only when one is supplied.
5. **NNS 2019 and 2023 CALABARZON prevalence figures.** Objective 5 names them as the face-validity anchor; no verified value is on file.

The outputs are potential risk indicators: they are indicative and not absolute, and
they are not to be construed as official food insecurity classifications or policy
recommendations.
