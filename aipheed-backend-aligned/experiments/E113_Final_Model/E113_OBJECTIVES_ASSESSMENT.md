# E113 Objectives 1–5 (Chapter I §1.5.2)

**Basis.** Objective wording follows `../Lead1_Objectives_Assessment/LEAD1_OBJECTIVES_1_4_ASSESSMENT.md`. Every result is development evidence on quarters seen in E109–E112.

**Status key.** Achieved / Partial / Not achieved.

| Objective | E113 evidence | Status | Change from E112 |
|---|---|---|---|
| **1.** Two-tier NLP pipeline (zero-shot XLM-R + BERTopic) producing the bias-corrected FSSI and latent food-insecurity risk patterns per province-quarter | Pipeline intact (FSSI-v3, BERTopic; E64). Four interpretable dense composites, all dated and cut at the issue date. **Validated:** disaster news vs typhoon counts (ρ = 0.81); price-news direction leads food-inflation changes by two quarters (GDELT ρ = 0.70, Holm p = .016). **No forecast gain:** news family Holm p = 1 at every lead; placebo permutation p = .63. | **Partial.** The pipeline and its outputs exist and are partly validated; they do not improve hunger forecasts. | Price news moved from "not validated" to "validated as a leading CPI signal" |
| **2 I–IV.** Accuracy, precision/recall, F1, AUC-ROC of the proposed model | Continuous metrics are reported for every model and lead: MAE, RMSE, MASE, bias, directional accuracy, 80% coverage, interval score. Surge classification gives precision and recall; at most 13 events per lead, and no alert claim is supported. The binary HIGH/LOW readings stay one-class (E109). | **Partial** | Added MASE, interval score and the surge precision/recall/Brier |
| **2 V.** Walk-forward expanding window to the furthest reliable horizon | Rolling origin; 14 / 12 / 11 / 9 / 7 / 6 evaluable quarters at Leads 1–6; pre-registered R1–R4 | **Not achieved.** No reliable lead (none established). The calibrated persistence band holds at Lead 1 only (coverage 0.75). | More quarters at every lead; still no reliable lead |
| **3.** Municipal and city rankings from **validated** province-level forecasts, weighted by poverty and density | No provincial or LGU food-insecurity outcome exists. The consistency check of provincial vulnerability against PSA subsistence incidence is inconsistent (ρ = 0.74 in 2021, −0.56 in 2023; n = 5). | **Not achieved** as specified. Rankings remain labelled vulnerability rankings. | Subsistence check added; no change in status |
| **4.** Compare the proposed model with the persistence, PSA-only, NLP-only and logistic-regression baselines | All four were compared on the same rows. Linear regression stands in for logistic regression because the outcome is continuous. MA2, damped trend, AR(1) and ETS were added. DM with Holm correction, plus the Model Confidence Set. | **Achieved (the comparison).** No candidate beats persistence. Linear regression is worst at every lead. The MCS cannot separate most models at Leads 1–5. | Wider baseline set; MCS added |
| **5.** Dashboard deployment, ISO/IEC 25010 evaluation, DA IV-A evaluators | Read-only API `/api/v1/e113/*`, model card and plain-language summary prepared for the evaluators. Dashboard design unchanged (standing rule). No ISO 25010 survey has been run in E113. | **Not achieved in E113.** It needs the researchers' evaluation with the DA IV-A respondents. | Supporting materials added |

## What would change each status

| Objective | What is needed |
|---|---|
| 1 | Prospective evidence that news improves forecasts (seals A and B), or local news matched to local outcomes |
| 2 V | Scoring of seals A and B on SWS 2026-Q4 onward. About 8 unseen quarters are needed for a Lead-1 test. |
| 3 | CBMS 2024 LGU food-security aggregates, or FNRI provincial FIES |
| 5 | The planned ISO/IEC 25010 evaluation by DA IV-A staff |
