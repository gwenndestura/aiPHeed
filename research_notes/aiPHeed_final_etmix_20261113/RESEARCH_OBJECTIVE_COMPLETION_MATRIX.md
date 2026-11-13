# aiPHeed research-objective completion matrix and final verdict: FINAL-ETMIX as primary model (2026-11-13)

**Statuses:** COMPLETED, PARTIALLY COMPLETED, NOT COMPLETED, INSUFFICIENT EVIDENCE.

**Models:**
- **FINAL-ETMIX** (`final-etmix-1.0-experimental`, protocol `a365da1f`, seal `71ebe142`) is the primary research model.
- **E196** stays production (unchanged).

**Owner statements applied:** 50 DA Region IV-A evaluators assessed the system; DA validated the news dataset (signed hard copy).

**Evidence base:**
- All model metrics are **retrospective** walk-forward results on 72 reused province-rounds.
- No synthetic data were used.
- No model change was accepted.
- No seal or earlier record was altered (sha256 re-verified).

## A. Objectives

| # | Objective | Status | Evidence | Remaining |
|---|---|---|---|---|
| 1 | Two-tier NLP (zero-shot XLM-R + BERTopic → bias-corrected FSSI, latent patterns, province-quarter outputs) | **COMPLETED** (as built and specified) | Pipeline and FSSI for 78 provinces × 56 quarters (`../aiPHeed_completion_audit_20261113/FINAL_NLP_AND_NEWS_PIPELINE_REPORT.md`, re-checked); NLP tests 9/9 pass today; DA sign-off. **Predictive role:** NLP-only baseline weakest; inside ETMIX the news group is *redundant* (retraining without it: ΔBA 0.000, 0 flips) | Disclose: no measurable forecast gain; 77 % single-outlet share; 63 % area fallback. Show the FSSI as context, not as a trigger |
| 2 | LightGBM evaluation (accuracy, precision, recall, F1, AUC; walk-forward; furthest reliable lead) | **PARTIALLY COMPLETED** | Lead 1: acc 0.861, precision 0.778, recall 0.840, F1 0.808, AUC 0.903. Max lead **5** (thesis rule) / **4** (robust) / **1** (strict per-round rule), all retrospective (`FINAL_ETMIX_FORECAST_AND_LEAD_TIME_REPORT.md`) | Independent confirmation: score the sealed ENNS 2022 forecasts (needs FNRI provincial HFIAS) |
| 3 | Municipal / city prioritisation from provincial forecasts × PSA poverty + density | **COMPLETED** (method; derived priorities only) | Approved `rank_lgus`, reproduced for ETMIX: 142 LGUs, max error 1e-16, 141 PSA SAE + 1 labelled substitute; every row says "not a municipal measurement" | Optional: flag Lucena's substitute value more prominently; propagate SAE uncertainty |
| 4 | Comparison with persistence, PSA-only, NLP-only, logistic regression | **COMPLETED** (retrospective) | ETMIX Brier significantly better than all four at all 8 leads; higher accuracy and precision at every lead; persistence keeps higher HIGH recall at lower precision (`FINAL_ETMIX_BASELINE_COMPARISON_REPORT.md`) | Disclose row reuse; ETMIX ≈ FINAL (no significant difference) |
| 5 | Public dashboard (maps, alerts); ISO/IEC 25010 with DA IV-A; face validity vs FNRI 2019 / 2023 | **PARTIALLY COMPLETED** | Public dashboard live with E196. ETMIX backend, API, alerts and LGU priorities implemented admin-only. Face validity: CALABARZON published values all LOW, matched by ETMIX at every lead; 2023 FIES 19.1 % directionally consistent (context only). ISO instrument and scorer exist | (a) Enter the 50 ISO/IEC 25010 responses and run the scorer: per-characteristic results are not in the repository. (b) Approve or decline ETMIX as the served model. (c) Face validity cannot test HIGH detection (no HIGH CALABARZON province) |
| G | Develop, validate and deploy aiPHeed | **PARTIALLY COMPLETED** | Developed and deployed (E196); ETMIX retrospectively validated and integrated as experimental | Independent validation pending |

## B. Final verdict (Part 18)

### Model

| # | Question | Answer | Status |
|---|---|---|---|
| 1 | Is FINAL-ETMIX independently validated? | **No.** The results are retrospective on reused rows. The sealed 2022 forecasts are the pending test | **NOT COMPLETED** |
| 2 | Accuracy, precision, recall, F1, AUC? | Lead 1: **0.861 / 0.778 / 0.840 / 0.808 / 0.903** (CI accuracy 0.78–0.93, AUC 0.82–0.96) | **COMPLETED** (retrospective) |
| 3 | HIGH-risk identification? | 21 of 25 HIGH found at Lead 1 (2018 8/8, 2019 11/13, **2021 2/4**); 6 false alarms. Weak where surveys are 6 years old | **PARTIALLY COMPLETED** |
| 4 | Beats all four baselines? | Yes on Brier (32/32 lead-baseline pairs significant), accuracy and precision; **no** on HIGH recall versus persistence and PSA-only | **COMPLETED** (retrospective, with that exception) |
| 5 | Maximum reliable lead? | **4** quarters (robust rule) or 5 (thesis rule), retrospective; **1** under the strict per-round rule; **none** established on independent evidence | **INSUFFICIENT EVIDENCE** (admissible) |

### Forecasting contributors

| # | Question | Answer |
|---|---|---|
| 6 | Which individual features genuinely contribute? | **`hh_grdp_rel`** (regional GRDP per capita relative to national): retraining without it, ΔBA −0.106 and ΔBrier +0.025. As groups: provincial food CPI relative to national, poverty / subsistence incidence and density, agricultural output growth |
| 7 | Which groups carry meaningful information? | **Regional economy (core);** food prices, agriculture & fish production, poverty & social vulnerability (supporting). Agriculture's retraining Brier loss is significant; food prices' and poverty's are not |
| 8 | Which are redundant, contextual or unsupported? | **Redundant:** news / NLP, `income_rel`. **Contextual / unsupported:** climate and typhoon exposure (0.1 % of attribution), employment (never selected). **Excluded:** fish-production growth, remittances, regional unemployment (unavailable) |
| 9 | Which contributors should appear on the dashboard? | Four factor groups (Regional economy, labelled regional; Food prices and inflation; Poverty and social vulnerability; Agriculture and fish production). Plus the survey starting point and survey age. Climate, news and employment as context only |
| 10 | Evidence per group | `FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md` and `FINAL_ETMIX_DASHBOARD_TRIGGER_GROUP_REPORT.md`. **Caveat:** the regional-economy and poverty inputs are not selected by the fits trained on the newest data (2021 Leads 1–2 and the live issue), so explanations must be per forecast |

### System

| # | Question | Answer | Status |
|---|---|---|---|
| 11 | Backend correctly integrated? | Yes, as an **experimental, admin-only** module and API. Reproduces the sealed protocol (< 1e-9); exact explanations; correct cut-off (enforced) | **COMPLETED** (experimental scope); production integration **NOT COMPLETED** (needs approval) |
| 12 | Frontend correctly integrated? | Not changed. The public dashboard shows E196. Switching to ETMIX is a backend data change after approval | **NOT COMPLETED** (for ETMIX, by design) |
| 13 | Maps, alerts and explanations accurate? | ETMIX API: classes, alerts (none now), LGU priorities and explanations agree with the artifact (tested). The E196 public trigger groups differ from the evidence-based ETMIX groups | **PARTIALLY COMPLETED** |
| 14 | Integration tests passed? | 32 / 32 in the relevant suites, including 6 new ETMIX tests (executed today). Full-suite and frontend runs not repeated (no E196 change) | **COMPLETED** (scope stated) |
| 15 | Deployment-ready? | E196 stays deployed. ETMIX is **not** deployment-ready: no independent validation, not approved | **NOT COMPLETED** (ETMIX) |

### Research objectives

| # | Objective | Status |
|---|---|---|
| 16 | NLP | **COMPLETED** (no predictive gain; disclosed) |
| 17 | Forecasting | **PARTIALLY COMPLETED** (retrospective only) |
| 18 | Geospatial prioritisation | **COMPLETED** |
| 19 | Baseline comparison | **COMPLETED** (retrospective) |
| 20 | Deployment and validation | **PARTIALLY COMPLETED** (ISO results not in the repository; ETMIX not deployed; face validity contextual) |

## C. Exact remaining dependencies (only you, FNRI or DA can supply them)
1. **FNRI provincial HFIAS (moderate + severe) for the 2022 ENNS provinces** (or a later round). Then score the sealed ETMIX forecasts (`71ebe142`) once under PROTOCOL_SA. This is the first admissible validation and lead-time evidence.
2. **The 50 DA evaluators' ISO/IEC 25010 responses**, entered into `aipheed_e196/docs/final/iso25010/responses_template.csv`, then run `python -m app.iso25010.score`.
3. **Your decision:** keep E196 in production (current), or approve ETMIX as the replacement after step 1. The four-group display then becomes a backend change.
4. **Optional:** approval to commit the uncommitted ETMIX module, API and tests on `aiPHeed/setup-h-cw-dashboard` (nothing was committed).

## D. Deliverables (this folder: `research_notes/aiPHeed_final_etmix_20261113/`)

**Reports:**
1. `FINAL_ETMIX_ROOT_CAUSE_REPORT.md`
2. `FINAL_ETMIX_INPUT_FEATURE_AUDIT.md`
3. `FINAL_ETMIX_OPTIMIZATION_REPORT.md`
4. `FINAL_ETMIX_FORECAST_AND_LEAD_TIME_REPORT.md`
5. `FINAL_ETMIX_BASELINE_COMPARISON_REPORT.md`
6. `FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md`
7. `FINAL_ETMIX_DASHBOARD_TRIGGER_GROUP_REPORT.md`
8. `FINAL_ETMIX_INDEPENDENT_VALIDATION_REPORT.md`
9. `FINAL_ETMIX_BACKEND_FRONTEND_COMPLETION_REPORT.md`
10. this file

**Supporting material:**
- **Scripts:** `scripts/etmix_eval.py`, `contrib_jobs.py`, `contrib_eval.py`.
- **Evidence:** `evidence/` (ETMIX_*, C1–C9, `contributor_registry.json`, run logs).
- **Raw fits:** `parts/`.
- **Hashes:** `HASHES.sha256`.
