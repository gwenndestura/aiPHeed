# Objective Completion Matrix (E18)

**Basis:** the Chapter I objectives, quoted verbatim in `OBJECTIVES_EXTRACTION.md`. Chapter I states **no numerical success criteria**, so none is invented. The reliability rule used for 2-V is an **E18 working criterion that needs adviser approval.**

**Each objective as a checklist:**

| # | Objective (short) | Measurable requirements | Evidence (E13–E18) | Status | Remaining action |
|---|---|---|---|---|---|
| G | Develop, validate, deploy aiPHeed | (a) System runs; (b) forecasts validated; (c) deployed | (a) Runs locally (project records); E18 dev view runs (`DASHBOARD_INTEGRATION.md`). (b) Not validated (Objectives 2 and 4). (c) Current version not publicly deployed. | **Partially achieved** | Validation needs data (below). Deployment is your decision. |
| 1 | Two-tier NLP pipeline → bias-corrected FSSI and latent risk patterns per province-quarter | (a) Code exists; (b) FSSI and topic outputs for each province-quarter; (c) bias correction applied | (a) yes; (b) FSSI 96/100, topics 96/100 (2021–2025); (c) bias-weight code. The FSSI rests on 69 articles; 2 of 5 triggers never fire. | **Partially achieved** | Expand the corpus. No validity test of the FSSI exists (no ground truth). |
| 2-I–IV | Accuracy, precision and recall, F1, AUC-ROC of the proposed LightGBM | Metrics measured with timing-valid walk-forward validation | E17 (strict timing, k = 1): 0.629 / 0.905 / 0.633 / 0.745 / 0.667. E18 (h = 1–5) in `RESULTS_BY_HORIZON.md`. | **Achieved as measurement.** Performance is not better than baselines. | — |
| 2-V | Furthest horizon of reliable forecasting | Performance by lead time + a reliability rule | E18: h = 1–5 evaluated. No candidate selected. h ≥ 3 has < 5 test quarters on set A. Working criterion met at **no** horizon. | **Not achieved / inconclusive** | Adviser to adopt a reliability criterion; obtain more quarters with LOW cases (2026-H2+, needs authorization) |
| 3 | Municipal and city rankings from **validated** province forecasts, with poverty and density weights | (a) Rankings produced; (b) province forecasts validated; (c) weights as specified | (a) yes (code); (c) yes, but 126/142 LGUs use province-mean poverty, so the within-province order is largely density-driven and static; (b) **no** | **Partially achieved** | Depends on Objective 2. Evaluator assessment (Post-Survey) not collected. |
| 4 | Compare the proposed LightGBM with naive persistence, PSA-only, NLP-only sentiment and logistic regression baselines | All four on identical origins | E17 + E18: done at every horizon. SOP's two LightGBM ablations also reported. The model does not beat persistence or the PSA-only and LR baselines. | **Achieved** (comparison done; model not superior) | — |
| 5 | Public geospatial dashboard with maps and early-warning alerts; ISO/IEC 25010 with DA IV-A evaluators; face validity against NNS 2019 and 2023 | (a) Public deployment; (b) survey with evaluators; (c) NNS 2019 and 2023 figures compared | (a) Local only; the E18 development view shows real outputs. (b) Questionnaires exist; responses not collected. (c) NNS 2019 and 2023 CALABARZON values not available or verified (only 2025 regional). | **Not achieved** | (a) Your deployment decision. (b) Administer to 50 DA Region IV-A evaluators. (c) Obtain FNRI tables, or adopt a substitute anchor with your adviser. |

**What the brief listed that Chapter I's objectives do not explicitly require:**

| Item | Status |
|---|---|
| **SHAP** | Computed descriptively in E18. Not an objective, so no status is assigned. |
| **Forecast history, data-sufficiency flags, admin confirmation of alerts** | Implemented in the existing system (project records). Not evaluated here. |
