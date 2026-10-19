# Chapter I objective compliance matrix (E62)

**Source:** Chapter I of `THESIS 2 (11).pdf`, §1.5 and §1.7, sha256 `88dd0b62…` (extracted text in `out/thesis_p1_40.txt`).
**Rule applied:** only Chapter I is used as the requirement basis. Chapter I sets no accuracy threshold, so no 75% criterion is applied here.

**Status scale:**
- **Met:** the function works and was verified in E62.
- **Partially met:** some required parts work; others are missing or unverified.
- **Not met:** the required result does not exist.
- **Not yet verifiable:** needs evidence that has not been collected.

## General objective

> "To develop, validate, and deploy aiPHeed: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using NLP and Machine Learning."

| Part | Evidence | Status |
|---|---|---|
| Develop | Backend, frontend and model pipeline exist. 423 backend tests pass (18 skipped); 46 frontend tests pass; the production build passes. | **Met** |
| Validate | There is no independently observed provincial food-insecurity outcome. Development back-tests use 50 rows from one hunger regime. No prospective quarter has been scored yet. | **Not met** |
| Deploy | The code default is still E38; the E58 model runs only behind `AIPHEED_LEAD2_MODEL=e58`. E62 checked the local stack only. The Render/Vercel deployment was not reachable from this audit. | **Partially met** |

## Specific objectives (§1.5.2)

| # | Objective (verbatim, shortened only where marked …) | Required result | Implementation | Evidence (E62) | Status | Defects found and actions |
|---|---|---|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | FSSI and topic patterns per province-quarter from a Filipino-English corpus | `app/ml/nlp/*`, `fssi_builder.py`; E31 `fssi_v2_panel`; E60 classifier v2 (rule-based mechanism phrases, not XLM-RoBERTa) | FSSI-v2 exists for 2021–2026. The served E56/E58 model has no FSSI input (`r5`: schema news columns are E40 keyword shares only). E31 relevance holdout P 0.85 / R 0.40. E60 v2 relevance P 0.92 / R 0.75 on 16 relevant titles annotated by AI, not humans. The corpus is titles only, collected retrospectively in October 2026. | **Partially met** | The pipeline exists, but its output does not reach the forecast. BERTopic output was not re-verified in E62. Human verification of the annotations is pending. |
| 2 | "To evaluate the performance of the proposed LightGBM forecasting model using … I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | Metrics I–IV, plus V: several lead times and the furthest reliable horizon | E57/E58 rolling origin (expanding window), 10 origins, 50 rows, one lead (two quarters) | Re-scored independently (`r2`). E56: acc 0.72 [cluster CI 0.58–0.84], HIGH precision 0.625, recall 0.556, Brier 0.214. E58-EW: acc 0.78 [0.70–0.86], bal 0.78. E58-EW ROC-AUC 0.786 (E60). | I–IV **met** (development evidence); V **not met** | Only one lead time was evaluated for the served model. "Reliable" is undefined in Chapter I, and the furthest reliable horizon has not been determined. |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | 142 LGU rankings weighted by poverty and density, from validated province forecasts | `/provinces/{id}/municipalities`. PSA SAE 2021 (141 own values) at 60% and POPCEN 2024 density at 40%. | `r6` C5: 142 unique LGUs, finite indices, rank order follows the index. Every LGU carries "not an independent municipal forecast". Ties occur at 4-decimal precision (competition ranking). | **Partially met** | The province forecasts are **not validated**, so the rankings inherit that status. H4 needs the DA evaluators. The Lucena SAE substitute is unverified. |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against … I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | Comparison against the four baselines | E55/E59 baseline run (six SOP-Q3 variants, 45 rows). E62 re-scored persistence, majority and climatology on 50 rows. | E56 Brier 0.214 vs persistence 0.440 and majority 0.360. E58-EW 0.78 vs persistence 0.56. The best Chapter I baseline (NLP-only LR) scores 0.667 on 45 rows (E59). | **Met as a comparison.** Superiority is shown on development rows only. | Not statistically confirmed at quarter level. All rows had been seen by earlier experiments. |
| 5 | "To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor." | Public dashboard, maps and alerts; ISO 25010 evaluation; FNRI face validity | Dashboard (approved UI). Map with 142 LGUs. E58 early warnings appear in the summary sentence. Alerts are staged for the administrator. | Live local check (`r6`, browser): province, region and series values equal the record; explanations equal the record. No ISO 25010 data exist in the project. FNRI: only the regional FIES 2023 figure exists; there is no provincial anchor. | **Partially met** (dashboard). ISO 25010: **not yet verifiable**. FNRI face validity: **not met**. | Fixed D-E62-1/2/3 (see `DEFECTS_AND_CHANGES.md`). Not invented: no evaluator ratings, no FNRI validation. |

## Scope and limitation items (§1.7)

| Item (§1.7) | Evidence | Status |
|---|---|---|
| Forecasts for the 142 cities and municipalities of Cavite, Laguna, Batangas, Rizal and Quezon | `r6` C5: 142 LGUs served. These are disaggregations, not municipal forecasts. | **Met as relative prioritization**, as the scope itself states ("will not represent official food insecurity classifications") |
| Interactive map with risk levels, rankings and influencing factors | Browser check: map, province panel, trigger composition, LGU list | **Met** |
| Downloadable PDF assessment report per province and for CALABARZON (forecast scores, SHAP drivers, performance metrics, data-sufficiency disclosures) | `test_plain_report.py` and `test_api_report.py` pass. The report path was not re-verified in E58 mode. | **Partially verified** |
| Filipino and English news from 2020 to 2025 | The corpus covers 2021-01 to 2026-10-14, following the user's study-window rule (no pre-2021 data). It is titles only. | **Deviation, documented**. The thesis text should state 2021–2026. |
| PSA, DOST-FNRI, SWS, PAGASA, PhilRice, BSP and DOE data | PSA CPI, LFS and production; SWS; NOAA IBTrACS/ONI used instead of PAGASA; BSP remittances end 2025-Q4 (2026 needs a manual download); FNRI regional only | **Partially met** |
| "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk" | T43 = SWS hunger > 11.3 AND provincial price pressure. Labels reproduce from the raw files with 0 mismatches (`r1`). | **Met** (definition), but **not validated** as food insecurity |
| Areas with limited news coverage identified | `r6` C9: the sufficiency label matches the record's input coverage. The thin-news flag is served. | **Met** |
| Evaluation by 50 DA Region IV-A evaluators using ISO/IEC 25010 | No evaluation data | **Not yet verifiable** |

## Hypotheses (§1.4), as far as current evidence goes

| Hypothesis | Status |
|---|---|
| H1: FSSI and food-CPI deviation not among the strongest SHAP predictors | **Rejected for food CPI.** The CPI projection dominates every province at every origin (`r3`). **Not testable for FSSI**, which is not a model input. |
| H2: no reliable classification across multiple lead times | **Cannot be rejected.** Only one lead was evaluated, and "reliable" is undefined. |
| H3: does not outperform the six comparison models | **Tentatively rejected on development data** (E59, 45 rows). There is no quarter-level significance and no unseen data. |
| H4: LGU rankings consistent with DA evaluators | **Pending** the DA post-survey. |
| H5: favourable ISO/IEC 25010 ratings | **Pending** the DA post-survey. |

## Thesis text inconsistencies to correct (author's decision)

- **SOP Q5 still names DEPDev Region IV-A** as usability evaluators. The study design is DA Region IV-A only (project decision of 2026-10-10).
- **§1.2 describes the label as anchored to the FAO SDG 2.1.2 / FNRI ENNS baseline.** T43 uses frozen 2021–2022 percentiles of SWS and PSA data, not an FNRI anchor.
- **§1.7 gives the news period as 2020–2025.** The implemented window is 2021-01 to 2026-10-14.
