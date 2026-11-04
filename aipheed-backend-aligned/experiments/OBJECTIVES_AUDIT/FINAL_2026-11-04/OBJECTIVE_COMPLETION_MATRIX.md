# Objective completion matrix (2026-11-04)

**Labels:** Completed · Partially completed · Pending external action · Blocked by data · Not achieved.

| Objective | Technical implementation | Empirical validation | Statistical evidence | Human validation | Adviser decision | Prospective validation | **Overall** |
|---|---|---|---|---|---|---|---|
| 1. NLP (XLM-R, BERTopic, FSSI) | Completed | Completed (temporal safety; coverage; BERTopic fails NPMI and place-name rules) | Not achieved (news Brier gain 0.001; early warning n.s.) | **Pending external action** (0/300 labelled) | — | — | **Partially completed** |
| 2. Forecasting (LightGBM, walk-forward, MRLT) | Completed | Completed (all metrics; MRLT 3) | Not achieved (R3 0.690/0.679; R7 middle third 0.524) | — | Adoption of C-E2/S1 | Pending (not sealed) | **Partially completed** |
| 3. Geospatial (5 provinces, 142 LGUs) | Completed | Completed (recomputed; sensitivity; uncertainty) | — | — | **Pending** (D3.1, D3.2) | — | **Completed technically; weighting pending adviser** |
| 4. Baselines (7 comparators) | Completed | Completed (identical quarters) | **Not achieved for "beats all"**: 4/14 significant; all 14 favour C-E2 on average | — | — | Pending (2027 holdout) | **Partially completed** |
| 5. System (ISO/IEC 25010, FNRI) | Completed (backend; config fixed; 1,022 tests) | Completed (backend checks) | — | **Pending external action** (50 evaluators, ongoing) | Survey build | — | **Pending external action** |

## Per objective

**1. NLP**
- **Implemented:** the pipeline, time-safe BERTopic, the annotation workflow v2.
- **Tested:** ablation, redundancy, early warning.
- **Reports:** `NLP_VALIDATION_REPORT.md`, `FSSI_VALIDATION_REPORT.md`, `BERTOPIC_TEMPORAL_VALIDATION.md`,
  `HEADLINE_ANNOTATION_PACKAGE.md`.
- **Blocker:** human labels.

**2. Forecasting**
- **Tested:** C-E2 reproduced; failure analysis with label uncertainty.
- **Blockers:** 13 of 62 labels are uncertain under SWS sampling error, and the accuracy ceiling is about 0.925.
  Regime 2015–2020. Five fixes failed.
- **Reports:** `FORECASTING_FAILURE_ANALYSIS.md`, `R1_R7_VALIDATION.md`, `FORECAST_CANDIDATE_COMPARISON.md`.

**3. Geospatial**
- **Reports:** `GEOSPATIAL_VALIDATION.md`, `LGU_WEIGHTING_ADVISER_DECISION.md`.
- **Blocked by data:** no municipal hunger outcomes for validation.

**4. Baselines**
- **Reports:** `BASELINE_STATISTICAL_COMPARISON.md`, `POWER_AND_SAMPLE_SIZE_ANALYSIS.md`.
- **Unproven:** logistic combined, logistic government-only, logistic NLP-only, LightGBM NLP-only and always-HIGH, at
  both leads. LOGIT at Lead 1 would need about 19,000 quarters.

**5. System**
- **Reports:** `BACKEND_TECHNICAL_READINESS.md`, `API_CONFIG_FIX_REPORT.md`, `BACKEND_TEST_REPORT.md`.
