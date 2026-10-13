# Evidence for the Remaining Objectives (1, 3, 5 and the General Objective)

**Implementation evidence** (the feature exists and runs) is kept apart from **evaluation evidence** (it was shown to work as intended). Sources:

- `runs/supporting_20261013T034830Z/objective_evidence.json`
- code inspection
- `docs/CHAPTER_4_RESULTS.md` (project record of 2026-10-08/09)

## Objective 1: two-tier NLP pipeline producing the FSSI and latent risk patterns per province-quarter

| Evidence | Result |
|---|---|
| Code | Zero-shot XLM-RoBERTa scoring, the trigger classifier, the FSSI builder with bias weighting, BERTopic topic proportions (`app/ml/nlp/`, `app/ml/features/`) |
| Outputs, 2021–2025 (`features_fused`, `topic_proportions`) | **FSSI non-zero in 96 of 100 province-quarters** (Quezon 16/20; the others 20/20). **Topic proportions for 96 of 100** province-quarters. |
| Trigger outputs (non-zero province-quarters) | Market 2; climate 48; fish kill 7; **employment 0; OFW remittance 0** |
| Corpus size (project record) | The FSSI rests on **69 retained articles** out of 804 geocoded to CALABARZON (2020–2025) |
| Is the FSSI valid as a measure of food stress? | **Not evaluated.** There is no ground truth for sentiment. As a predictor, the NLP-only sentiment baseline was the weakest arm (accuracy 0.23 at k = 1). |

**Status: partially achieved.** The pipeline is implemented and produces the FSSI and topic outputs for almost every province-quarter. Two of the five trigger categories never fire, and the FSSI rests on very few articles. **Chapter I states no success criterion,** so "achieved" can only mean "implemented and producing outputs".

## Objective 3: municipal and city rankings from **validated** province-level forecasts, using poverty and density weights

| Evidence | Result |
|---|---|
| Code | `inference/disaggregator.py`. Vulnerability V = 0.6 × poverty_norm + 0.4 × density_norm, then LGU score = province score × V. |
| Inputs | 142 LGUs matched. **126 of 142 use province-mean poverty (fallback)**, leaving only 3–5 distinct poverty values per province. |
| What drives the ranking within a province | The Spearman correlation between the V rank and the density rank is **0.67–0.82** across the five provinces, so density drives much of it |
| Stability | V is static (2021 poverty, 2020 census), so **the order within each province never changes between quarters**. Only the province score changes, and it moves all of a province's LGUs together. |
| "Validated province forecasts" precondition | **Not met.** The province classifier did not outperform simple baselines (Objective 2 and 4 results). |
| Agreement with DA evaluators (Hypothesis 4) | **Not yet collected** (project record) |

**Status: partially achieved.** The rankings are produced as specified. Their precondition (validated province forecasts) is not met. They are **not independent outcomes**, being a fixed rescaling of province scores. No evaluation of their accuracy exists.

## Objective 5: public dashboard, ISO/IEC 25010 evaluation with DA evaluators, face validity against NNS 2019 and 2023

| Part | Evidence | Status |
|---|---|---|
| Public geospatial dashboard with forecast maps and early-warning alerts | The FastAPI and React code exists and runs locally (project record). **Public deployment of the current version: not done** (project record). | Implemented locally; **not deployed publicly** |
| ISO/IEC 25010 evaluation with DA Region IV-A evaluators | Questionnaires exist (`DA-Pre/Post-Survey-Questionnaire.docx`, not opened). Summary script `scripts/iso25010_summary.py`. **Responses not yet collected** (project record). | **Not done** |
| Face validity against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence | The project holds **only NNS 2025** (22.6%, regional, secondary source, repeated in five rows). The 2023 value was removed as unverifiable; 2019 is not in the project. | **Not possible as written** |

**Status: not achieved,** pending deployment, the survey and an available anchor.

## General Objective: develop, validate and deploy aiPHeed

| Part | Status |
|---|---|
| Develop | **Largely achieved** (the system exists and runs locally) |
| Validate | **Not achieved.** Forecasts do not beat baselines, and the target is a constructed label. |
| Deploy | **Not achieved** for the current version |
