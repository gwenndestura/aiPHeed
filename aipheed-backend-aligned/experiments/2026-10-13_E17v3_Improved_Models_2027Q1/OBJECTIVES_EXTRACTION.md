# Objectives of the Study: Exact Extraction (E17)

**Source:** `THESIS 2 (10).pdf` (sha256 `88dd0b62…`), Chapter I, sections 1.5.1 and 1.5.2.

**Verbatim text:** `thesis_source/CHAPTER_I_SOP_HYPOTHESES_OBJECTIVES_extract.txt`.

**Reading restrictions:**

- Only Chapter I defines the requirements here.
- The Statement of the Problem and the hypotheses (also in Chapter I) are used only as supporting context, where an objective is ambiguous.

## Objectives, exactly as written

**General Objective (1.5.1)**

> To develop, validate, and deploy aiPHeed: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using NLP and Machine Learning.

**Specific Objectives (1.5.2)**

1. To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus.
2. To evaluate the performance of the proposed LightGBM forecasting model using the following metrics:
   - I. Accuracy, to measure overall correctness of high- and low-risk province-level classifications
   - II. Precision and Recall, to assess the model's ability to correctly identify high-risk provinces while minimizing false alarms and missed detections respectively
   - III. F1-Score, to capture the balance between Precision and Recall given the binary classification task
   - IV. AUC-ROC, to evaluate the model's ability to distinguish between high- and low-risk provinces across classification thresholds
   - V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable
3. To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights.
4. To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches:
   - I. Naive persistence baseline
   - II. PSA-only indicator baseline
   - III. NLP-only sentiment baseline
   - IV. Logistic regression baseline
5. To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor.

**Notes on the text:**

- The manuscript numbers the fifth objective "5. 5.". That is a typing error; the wording is kept.
- **No objective states a success threshold.** None defines "reliable" or how much better than a baseline is needed.

## Wording points that matter for the evaluation

| Point | Effect |
|---|---|
| **Objective 2-V asks for "the furthest horizon at which reliable forecasting is achievable"** but does not define "reliable" | No reliability threshold is stated in Chapter I |
| **Objective 4 names four baselines** | The Statement of the Problem (Q3) and Hypothesis 3 name six: persistence, three logistic regression variants and two LightGBM ablations. **The objectives govern here, so the four are used.** The discrepancy is recorded. |
| **Objective 4 does not define "PSA-only indicator baseline" or "NLP-only sentiment baseline" as model types** | The SOP calls the comparisons logistic regression variants. That is used as context for choosing logistic regression (see the protocol). |
| **Objective 5 names NNS 2019 and 2023** as the face-validity anchor | — |
| **No objective mentions SHAP** | SHAP appears in 1.2 and in SOP Q1 and Hypothesis 1, so it is outside the objectives. It is not evaluated here. |
