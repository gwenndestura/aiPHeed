# Chapter I extraction (verbatim, machine-extracted) and traceability

**Source:** `THESIS 2 (11).pdf` (SHA-256 in `thesis_source/SOURCE.txt`; identical to `THESIS 2 (10).pdf`). Only Chapter I (PDF pages 6–15) was extracted.

**Method:** the quotations below are copied programmatically from `thesis_source/CHAPTER_I_verbatim.txt`, with whitespace and page numbers normalized. Nothing is retyped.

**Redaction:** one clause in SOP Q5 that names a second evaluator group is replaced with a bracketed note, per the researchers' 2026-10-10 decision that DA Region IV-A is the only participating agency.

## 1.5.1 General Objective

> To develop, validate, and deploy aiPHeed: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using NLP and Machine Learning.

## 1.5.2 Specific Objectives (with 2-I…V and 4-I…IV)

> 1. To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus. 2. To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy, to measure overall correctness of high- and low-risk province-level classifications II. Precision and Recall, to assess the model's ability to correctly identify high-risk provinces while minimizing false alarms and missed detections respectively III. F1-Score, to capture the balance between Precision and Recall given the binary classification task IV. AUC-ROC, to evaluate the model's ability to distinguish between high- and low-risk provinces across classification thresholds V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable 3. To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights. 4. To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline 5. 5. To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor.

## 1.3 Statement of the Problem (SOP 1–5)

> 1. What variables most significantly predict food insecurity risk across the provinces of CALABARZON, as identified through SHAP feature attribution? 2. What is the furthest lead time at which aiPHeed can reliably forecast province-level food insecurity risk across CALABARZON? 3. How does the LightGBM model combining NLP-derived news signals and government statistical indicators compare against six baseline approaches, naive persistence, three logistic regression variants (combined features, government indicators only, and NLP features only), and two LightGBM ablation variants trained on each data source separately, in classifying provincial food insecurity risk? 4. How effectively do the city- and municipality-level food insecurity risk rankings derived from province-level forecasts reflect relative vulnerability across CALABARZON? 5. How do DA Region IV-A personnel, as system evaluators, [second evaluator group named in the manuscript — withdrawn by the researchers on 2026-10-10; DA Region IV-A is the only participating agency], assess aiPHeed under the ISO/IEC 25010 software quality model, in terms of functional accuracy and ease of use respectively?

## 1.4 Hypotheses (null form)

> This study tests five null hypotheses, each addressing the relationship between an independent variable and a dependent variable. The independent variables are the news-derived signals and the government socioeconomic indicators. The dependent variable is the binary food insecurity risk classification, either high or low, of a CALABARZON province in a given quarter. The study's assumptions are based on the null hypothesis that these independent variables do not carry predictive signals strong enough for aiPHeed to classify, forecast, disaggregate, or be judged useful for that purpose.

> 1. The Food Stress Sentiment Index (FSSI) and food CPI deviation will not be among the strongest predictors of food insecurity risk in CALABARZON when examined through SHAP feature attribution. 2. aiPHeed will not reliably classify whether a CALABARZON province is at high or low food insecurity risk across multiple forward-looking lead times. 3. The LightGBM model that combines news signals and government data will not outperform the six comparison models, naive persistence, three logistic regression variants (news-only, government data-only, and combined), and two LightGBM variants trained on only one data source at a time, in classifying provincial food insecurity risk across CALABARZON. 4. The vulnerability-weighted spatial disaggregation of province-level forecasts will not produce municipal and city risk rankings that are consistent with DA Region IV-A evaluators' assessments of relative food insecurity vulnerability across CALABARZON, as evaluated through the aiPHeed Post-Survey Questionnaire. 5. aiPHeed will not receive favorable functional suitability, accuracy, and usability ratings from DA Region IV-A evaluators under the ISO/IEC 25010 software quality model.

## Introduction sentence checked for Inconsistency 2

> Food insecurity remains a critical global and national challenge. According to DOST-FNRI (2024), food insecurity is intensified by rising food prices, climate-related agricultural disruptions, and unequal access to social protection, with 44% of households experiencing moderate to severe food insecurity in 2023. The issue is particularly evident in

## Traceability matrix

| Objective | SOP | Null hypothesis | Implementation (isolated dev backend) | Required evidence | Responsible | E23 status |
|---|---|---|---|---|---|---|
| **O1** Two-tier NLP pipeline (XLM-RoBERTa zero-shot + BERTopic) → bias-corrected FSSI and latent risk patterns per province-quarter | Q1 (FSSI as a predictor) | H1 (FSSI part) | `app/ml/nlp/classifier.py`, `topic_model.py`, `app/ml/corpus/bias_weighter.py`, `app/ml/features/fssi_builder.py`; FSSI + lags + accel + 5 trigger shares in `features_fused` | FSSI present for every in-window province-quarter; BERTopic shares; timing rule | Researcher/system | **Built.** FSSI present for 100/100 cells in 2021–2025. Earlier audits found most cells forward-filled from sparse news (E9–E17). The PHT quarter-boundary fix was applied to code, but **features were not rebuilt**: that needs the news corpus, which is not authorized. |
| **O2** Evaluate LightGBM: I accuracy, II precision/recall, III F1, IV AUC-ROC, V lead times via walk-forward expanding window | Q2 (furthest reliable lead) | H2 | `runner/run_e23.py` (frozen); `runner/run_e23b.py` (improvement) | Per-lead metrics on identical origins; reliability rule | Researcher/system | **Metrics computed** at leads 1–6. **No lead evaluable** under the primary target (≤ 3 LOW test rows). Maximum reliable lead: **none**. |
| **O3** Disaggregated LGU rankings using PSA poverty + density | Q4 | H4 (ranking consistency) | `app/ml/inference/disaggregator.py` (fixed); `runner/build_rankings.py` | 142 rankings independently reproduced; agreement with evaluators | Researcher/system (rankings); **50 DA Region IV-A evaluators** (H4) | **Rankings verified: 142/142 identical.** The 2027-Q1 ranking is unavailable (no forecast). **H4 awaits participant data.** |
| **O4** Compare LightGBM vs I persistence, II PSA-only, III NLP-only, IV logistic regression | Q3 (six baselines) | H3 | Six baselines B1–B6 plus a literal PSA-only supplement, on identical rows | Paired tests on identical origins | Researcher/system | **Done.** Not testable under the primary target. Not rejected under the sensitivity target. E23-B does not beat persistence. |
| **O5** Deploy public dashboard (maps, early-warning alerts); ISO/IEC 25010 evaluation with DA Region IV-A; NNS 2019/2023 face validity | Q5 | H5 | E23 `dashboard_dev` (`/forecast-period`), PDF report, `/api/v1/quarterly/forecast-period`; `instruments/` | Working dashboard; ratings from 50 DA evaluators; verified NNS figures | Researcher/system (dashboard, checks); **50 DA Region IV-A evaluators** (H5) | **Development dashboard works locally. Not deployed** (needs your approval). NNS 2023 verified; NNS 2019 not verified. **H5 awaits participant data.** |
| **General objective:** develop, validate, deploy | all | all | — | — | — | Developed. Validated with the limits above. **Not deployed.** |

## Inconsistencies found in Chapter I

### 1. Six baselines (SOP Q3, H3) vs four baselines (Objective 4)

All six H3 baselines were run. Objective 4 maps onto them as follows:

| Objective 4 baseline | H3 baseline |
|---|---|
| I naive persistence | B1 |
| II PSA-only indicator | B3, government-only logistic regression |
| III NLP-only sentiment | B4, news-only logistic regression |
| IV logistic regression | B2, combined logistic regression |

- The literal reading of II (logistic regression on the 20 PSA series only) is reported beside B3 as a supplement.
- B5 and B6 (the LightGBM single-source ablations) appear only in SOP Q3 and H3.

**Recommendation:** align Objective 4 with H3, or state the mapping in Chapter III.

### 2. "44% of households … moderate to severe food insecurity in 2023" attributed to DOST-FNRI (2024)

The DOST-FNRI primary source does not support this figure. The 2023 NNS "Household & Food Security" chapter (enutrition.fnri.dost.gov.ph; file SHA-256 `987a6c5d…` in `docs/FNRI_SOURCES.md`) reports:

- **31.4% of households nationally** with moderate-to-severe food insecurity;
- **CALABARZON at 19.1% (95% CI 17.0–21.1), the lowest of the 17 regions.**

"About 44%" matches the FAO/UN population-based prevalence of moderate or severe food insecurity for 2021–2023, as reported by secondary sources. That figure was **not verified in an FAO primary source here**. It also uses a different population base (people, not households) and a different method.

**Recommendation:** replace the sentence with 31.4% (DOST-FNRI 2023 NNS), or cite FAO correctly for the 44% figure.

### 3. Objective 5's "NNS 2019 and 2023 CALABARZON prevalence" anchor

| Anchor | Finding |
|---|---|
| **2023** | Verified: 19.1% (95% CI 17.0–21.1), as above. |
| **2019** | **Not verified.** Secondary sources report that the 2018–2019 ENNS measured household food insecurity with the **HFIAS** scale, not FIES. The FNRI 2018–2019 "Facts and Figures" report is 428 image-only pages, and its CALABARZON value was not located. Even if found, it would not be comparable with the 2023 FIES value. |
| **Stored anchor** | `nns_fies.parquet` holds **22.6% labelled "NNS 2025"**, from secondary reporting. It is a different cycle and does not equal the verified 2023 value. |

**Recommendation:** anchor Objective 5 to the 2023 value, and drop or re-source 2019.

A comparison against one regional figure is **descriptive**. It cannot validate provincial forecasts.

### Other Chapter I items needing your decision

| Item | Issue |
|---|---|
| SOP Q5 | Still names a second evaluator group (redacted above). |
| Section 1.7 | Says news "from 2020 to 2025". The approved study window used in all experiments is 2021–2026. |
| "Reliable" (O2-V, SOP Q2, H2) and "favorable" (H5) | Undefined in Chapter I. E23's rules are researcher-declared and need adviser approval. |
