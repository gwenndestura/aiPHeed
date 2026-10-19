# E58 against the approved thesis (Chapter I, `THESIS 2 (11).pdf`)

## 1. What Chapter I specifies

| Item | Chapter I text (extracted) | Mismatch with E58 |
|---|---|---|
| General objective | "To develop, validate, and deploy aiPHeed: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using NLP and Machine Learning." | "Validate" and "deploy" are not yet met (sections 2 and 3). |
| Intended users | DA Region IV-A (and LGU social welfare officers, §1.6). Evaluation by 50 DA IV-A evaluators (§1.7). SOP Q5 still names DEPDev IV-A usability evaluators. | DEPDev appears in SOP Q5 but was removed from the study design (project memory, 2026-10-10). This inconsistency in the thesis text needs the author's correction. |
| Target | "composite food stress label combining SWS quarterly hunger data and PSA province-level food CPI deviation, anchored to the FAO SDG 2.1.2 baseline established by the DOST-FNRI ENNS" (§1.2). "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk" (§1.7). | T43 combines SWS hunger and PSA food prices (consistent). Its thresholds are 2021–22 percentiles, **not** anchored to the FNRI ENNS/FIES baseline, and it is a conjunction, not the Eq. 3 additive composite (which E38 serves). On evaluated rows it reduces to price pressure. |
| Horizon | "furthest lead time at which aiPHeed can reliably forecast" (SOP Q2); "multiple lead times via walk-forward expanding-window cross-validation" (Obj 2.V) | **No fixed horizon** in Chapter I. E58 is evaluated at one horizon only (two quarters). The furthest reliable lead time was not determined in E55–E58. |
| Accuracy target | none in Chapter I (the 75% reliability rule is in Chapter III) | The 75% figure is used here as the brief's development goal, not as a Chapter I criterion. |
| Baselines | SOP Q3 / H3: **six** (naive persistence; LR combined, LR government-only, LR NLP-only; LightGBM government-only, LightGBM NLP-only). Obj 4: **four** (persistence, PSA-only, NLP-only, LR). | All six were reproduced on 45 common rows (E55 baseline run). None can forecast 2024-Q2: too little training history. |
| Triggers | "trigger composition scores" (§1.2); five groups not enumerated | see `E58_TRIGGER_IMPLEMENTATION_AUDIT.md` |
| Rankings | 142 LGUs from province forecasts, weighted by PSA poverty and density, "indicative and not absolute" | implemented as relative prioritization |

## 2. Objective-by-objective

| Objective (Chapter I §1.5.2) | Implemented | Evidence | Status |
|---|---|---|---|
| **1.** Two-tier NLP (zero-shot XLM-RoBERTa sentiment + BERTopic) → bias-corrected FSSI and latent risk patterns per province-quarter | yes: `app/ml/nlp/{sentiment,topic_model,trigger_classifier,classifier}.py`, `app/ml/features/fssi_builder.py`, `app/ml/corpus/bias_weighter.py`, `data/news_e31/fssi_v2_panel.csv` | E31: relevance holdout precision 0.85, recall 0.40 (not re-run here). In E56/E58 the news trigger shares are almost always zero, FSSI is not a model input, and news reached a tree split twice in 12 origins. | **Partially achieved.** The pipeline exists, but its outputs carry almost no forecasting signal and recall is low. |
| **2.** Evaluate the LightGBM model: accuracy, precision/recall, F1, AUC-ROC, and multiple lead times (walk-forward) | metrics at one horizon (two quarters) on 50 rows, rolling origin | E58-EW / E56: accuracy 0.78 / 0.72; HIGH precision 0.667 / 0.625; HIGH recall 0.778 / 0.556; F1 0.718 / 0.588; AUC 0.786 / 0.649 | **Partially achieved.** All metrics are reported, but **lead times are not evaluated** beyond two quarters, and the furthest reliable horizon is undetermined. |
| **3.** Municipal and city rankings from **validated** province forecasts, weighted by PSA poverty and density | yes: 142 LGUs; SAE 2021 (141 own values; Lucena a province substitute, unverified) + POPCEN 2024 | API `/provinces/{id}/municipalities`; serving tests | **Partially achieved.** Rankings are built, but the province forecasts are **not validated**, and H4 needs DA evaluators. |
| **4.** Compare LightGBM with persistence, PSA-only, NLP-only and logistic regression | yes, all six SOP-Q3 variants (45 common rows) | `E58_BASELINE_COMPARISON.csv`: E56 = E58-EW 0.778 / balanced 0.760 vs the best baseline, NLP-only LR (0.667 / 0.523); persistence 0.600; every baseline below on Brier and balanced accuracy | **Achieved on development data.** Not statistically confirmed at quarter level, and on rows that informed the design. |
| **5.** Public geospatial dashboard with maps and early-warning alerts; ISO/IEC 25010 evaluation with DA IV-A; face validity against DOST-FNRI NNS 2019/2023 | dashboard yes (local; E58 behind a flag; production serves E38); alerts staged for admin confirmation | backend 402 passed, frontend 45 passed; live local preview verified | **Partially achieved.** Built and tested, but E58 is not deployed (27 commits unpushed). **ISO/IEC 25010 evaluation: Pending.** **FNRI face validity: Pending** (only regional FIES 2023 is available; no provincial anchor). |

## 3. Hypotheses (§1.4)

| Hypothesis | Status |
|---|---|
| H1 (FSSI and food-CPI deviation not among the strongest SHAP predictors) | **Partially rejected:** food-CPI terms dominate (Market first in nearly every entry). **Not rejected for FSSI**, which is not a model input. |
| H2 (no reliable classification across multiple lead times) | **Cannot be rejected.** Only one lead was evaluated, and reliability is not established (see generalization). |
| H3 (does not outperform the six models) | **Rejected on development data** (Brier and balanced accuracy vs all six on 45 rows). Quarter-level significance is not established, so this is a tentative rejection. |
| H4, H5 (rankings consistent with DA evaluators; favourable ISO 25010 ratings) | **Pending** the DA IV-A post-survey. |
