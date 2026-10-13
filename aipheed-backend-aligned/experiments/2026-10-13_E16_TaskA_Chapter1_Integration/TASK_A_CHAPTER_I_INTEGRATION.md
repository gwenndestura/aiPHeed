# Task A Results Mapped to the Chapter I Objectives (E16)

**Sources:**

| Source | Detail |
|---|---|
| Thesis | Chapter I only: `THESIS 2 (10).pdf` (sha256 `88dd0b62…`), sections 1.3 to 1.5, saved verbatim in `CHAPTER_I_extract_sections_1.3-1.5.txt` |
| Task A report | E13 `REGIONAL_HUNGER_FORECAST_REPORT.md` (sha256 `dad5dbdc…`) |

**Restrictions followed:**

- **Task A was not changed.** Its numbers are quoted, not recalculated.
- **Nothing was computed, and no data file was opened.**
- **No other thesis chapter was used.**

## 1. The objectives, exactly as written in Chapter I

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

## 2. What Task A is (unchanged from its report)

| Item | Task A |
|---|---|
| Target | SWS Balance-Luzon involuntary hunger, % of families. **One regional value per quarter. Continuous.** |
| Forecast | At the start of quarter T, using only rounds published before that date |
| Validation | Chronological expanding window; 9 test quarters (2023-Q4..2025-Q4); quarters examined before |
| Results (MAE in percentage points of hunger; **not classification accuracy**) | Latest published value **4.77** (RMSE 5.22); drift 4.89; historical mean 6.74; ridge AR(1) 6.57; AR(1) + regional food inflation 6.58 |
| Main limitations (as reported) | No model beat the latest value. Every method under-forecast the 2024–2025 rise. 80% intervals covered 2 of 9 quarters. One quarter without a rise, so direction calls are uninformative. Regional only. |

## 3. Three different forecasting tasks

| Task | Target | Geography | Type | Where it stands |
|---|---|---|---|---|
| **Regional hunger forecasting** (Task A) | SWS hunger level | Balance Luzon (one value for all five provinces) | Continuous (MAE, RMSE) | Done (E13) |
| **Provincial food-price forecasting** (Task B) | Provincial food inflation F and relative pressure D | Province | Continuous | Done (E13). These are price targets, not food insecurity. |
| **Provincial food-insecurity risk forecasting** (what Objectives 2 and 4 require) | HIGH or LOW risk class for each province and quarter, from the proposed LightGBM model | Province | **Binary classification** (accuracy, precision, recall, F1, AUC-ROC) | **Not yet evaluated under Chapter I's terms** |

**Task A cannot stand in for the third task.** It has a different target, geography, model and metric family.

## 4. Objective-to-evidence table

| Objective | What it requires | What Task A provides | Status from Task A |
|---|---|---|---|
| **General: develop, validate, deploy** | A working system, validation of its forecasts, and deployment | Validation evidence for **one input** of the system (regional hunger), not for its forecasts | **Partially supported, indirectly** |
| **1. Two-tier NLP pipeline (FSSI, topic patterns)** | Evidence the pipeline produces the FSSI and topic patterns per province-quarter | None. Task A uses no news or NLP features. | **Cannot address** |
| **2-I to 2-IV. Accuracy, precision and recall, F1, AUC-ROC of the proposed LightGBM model** | Classification metrics for HIGH/LOW province-level risk | None. Task A is a regression on a regional target, scored with MAE. **MAE is not accuracy.** | **Cannot address** |
| **2-V. Performance across lead times; furthest reliable horizon** | Walk-forward evaluation of the proposed model at several lead times | It uses the same **validation design** (walk-forward, expanding window), but at **one lead time**, for a **regional** target, without the proposed model | **Context only.** It shows that the regional hunger component of the risk label was not forecastable better than its latest value in 2023–2025, which suggests label changes driven by regional hunger will be hard to anticipate. **It does not establish any province-level lead time.** |
| **3. Municipal and city rankings** | Rankings from **validated** province-level forecasts, with PSA poverty and density weights | None | **Cannot address** |
| **4. Comparison with the four baselines** | The proposed LightGBM model compared with naive persistence, PSA-only, NLP-only sentiment and logistic regression | Only a **persistence-type baseline** (the latest published value) against regional models, for a different target | **Cannot address.** It only illustrates that persistence is a hard baseline to beat. |
| **5. Dashboard, ISO/IEC 25010 evaluation, face validity against FNRI NNS 2019 and 2023** | Deployment, a DA evaluator assessment, and a comparison with NNS prevalence | None. Task A uses SWS, not FNRI NNS. It does inform how a regional hunger figure should be shown (with its scope and its large uncertainty). | **Cannot address** |

## 5. Interpretation of Task A

**What it means for the thesis:**

- **It answers a narrower question than the thesis asks:** "Can the regional hunger level be forecast better than its latest published value?" Over 9 previously examined quarters, the answer is no.
- **The latest published value had the lowest error** (MAE 4.77 percentage points).
- **The models were worse.** Nothing improved detection of rises, and uncertainty was larger than past errors suggested.

**What it does not mean:**

| Not established | Why |
|---|---|
| Province-level forecasting accuracy | Task A has no province-level target |
| Classification accuracy, precision, recall, F1 or AUC-ROC | No classification was made |
| A maximum reliable lead time for provinces | One lead time, regional target |
| That the proposed LightGBM model succeeds or fails | It was not evaluated |
| That food insecurity was predicted | SWS hunger is a regional survey measure |

**Why it is still relevant:** the province-level risk label in the current implementation adds this **same regional hunger value** to every province. Task A therefore warns that the part of the label shared by all provinces is difficult to anticipate. That should be considered when the province-level classifier is evaluated.

## 6. Unresolved objectives (need separate evaluation with the current implementation and eligible data)

| Objective | What is unresolved |
|---|---|
| **2 (I–V)** | Classification performance of the proposed LightGBM model on its province-level HIGH/LOW target, at several lead times, under walk-forward validation. **Chapter I gives no reliability criterion**, so "reliable" must be defined by you and your adviser or reported as undetermined. |
| **4** | The same model compared with the four named baselines, on identical forecast origins |
| **1** | Evidence that the pipeline produces the FSSI and topic patterns for every province-quarter, separate from whether they predict anything |
| **3** | Municipal rankings exist only as a transformation of province forecasts. Chapter I requires **validated** province forecasts first. Any check of the rankings needs evaluator judgement or an independent municipal outcome. |
| **5** | The deployment status of the public dashboard; the ISO/IEC 25010 evaluation with DA evaluators (not yet carried out in the project records); face validity against **NNS 2019 and 2023** CALABARZON figures. The project holds neither: the 2023 regional value was removed as unverifiable, and 2019 is not in the project. Only a 2025 regional value exists. |
| **General** | "Validate" depends on Objectives 2 to 5 |

## 7. Prioritized next steps

1. **Objectives 2 and 4.** Evaluate the current implementation's LightGBM classifier on its own province-level HIGH/LOW target:
   - eligible 2021–2025 data and timing-valid features;
   - walk-forward expanding-window validation at lead times of 1 to 8 quarters where the data allow;
   - all four Chapter I metrics, plus confusion matrices and per-quarter results;
   - the four named baselines on identical origins.

   **This is now running as E17** (`2026-10-13_E17_Objectives_Evaluation`).
2. **Decisions for you and your adviser,** because Chapter I leaves them open:
   - a reliability criterion for "furthest horizon at which reliable forecasting is achievable";
   - whether the label (a composite of regional hunger and provincial price deviation) may be called food-insecurity risk;
   - a replacement face-validity anchor, since NNS 2019 and 2023 regional values are not available in the project.
3. **Objective 5 evaluation:** carry out the ISO/IEC 25010 survey with DA Region IV-A evaluators, and record the dashboard's deployment status.
4. **Objective 3:** once province forecasts are validated, evaluate the rankings, for example with the evaluators' assessments.
5. **Objective 1:** document pipeline coverage per province-quarter, including LIMITED_SIGNAL cases.

## 8. Direct answer

**What should be evaluated next is Objectives 2 and 4:** the proposed LightGBM model's **province-level HIGH/LOW classifications**, using:

- eligible 2021–2025 data;
- walk-forward expanding-window validation across several lead times;
- the five Chapter I measures (accuracy, precision and recall, F1, AUC-ROC, performance by lead time);
- the four named baselines on the same forecast origins.

**Task A's regional hunger results cannot show whether aiPHeed fulfills its purpose.** They address a different, regional, continuous target.

**Because Chapter I does not say what counts as "reliable",** that criterion, and the meaning of the risk label, need your adviser's decision before any lead time can be called reliable.
