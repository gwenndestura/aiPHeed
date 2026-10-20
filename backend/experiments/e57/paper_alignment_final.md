# Paper alignment audit (final): THESIS 2 (14) vs the aiPHeed system

Read-only audit, 2026-10-18, branch `final-aipheed-integration` (working tree with uncommitted changes, as found).
Nothing was changed except this file. Every number cites the file it comes from; "recomputed" means computed for this
audit from stored predictions by `scratchpad/audit_metrics.py` (sklearn 1.8, numpy). Where something could not be
verified it says **NOT VERIFIED** and why.

Statuses: **ALIGNED** (does what the paper says), **PARTIAL** (part done, or done with a material difference),
**DEVIATES** (does something else on purpose), **NOT IMPLEMENTED**, **UNTESTABLE** (needs data that does not exist yet).

---

## 0. Integrity and tests

| File (backend/) | md5 now | Protected value | Match |
|---|---|---|---|
| data/e36/e36_record.json | 921f2130c2ab3380c3cd21c1b25fe31a | 921f2130... | yes |
| data/e48/e48_record.json | a2223c22f85cb4058c0e7e59229dcb67 | a2223c22... | yes |
| data/e49/e49_record.json | 14c818ea990b6959584fbff92afd3ade | 14c818ea... | yes |
| data/e49/model/E48-A1-LGBM_O2026-10-01.txt | 2b6be3e9ab5e63191aa03639a5640ab1 | 2b6be3e9... | yes |
| data/e49/model/E49_C2_calibration.json | 8f0eae02d81857f1d3c72ca5965409df | 8f0eae02... | yes |
| data/e53/e53_record.json | fa3d0a51939fae66d87bf77c3d15d738 | fa3d0a51... | yes |
| data/e53/model/E53_C2_calibration.json | 9986f6cb4b4a36a9e9d676709cb3aeee | 9986f6cb... | yes |

Tests (run 2026-10-18):
- **Backend:** `ENABLE_API_DOCS=false pytest`: **411 passed, 18 skipped, 0 failed**.
- **Frontend:** `vitest run`: **9 files, 35 passed, 0 failed**.

---

## 1. Sources used

**Manuscript**
- `C:\Users\User\Downloads\THESIS 2 (14).pdf`: the newest THESIS 2 file (15 Oct 2026), md5
  08b96f1ba79224e20b5ac847aecfd212. It is **outside the repo**: no manuscript PDF or DOCX is committed.
- Text was extracted with `pdftotext -layout`. Page numbers below are PDF page indices, which match the printed page
  numbers.

**Earlier audits** (all re-checked; corrections are listed in section 7)
- `backend/experiments/e57/objectives_audit.md`, which also holds the list of 16 deviations;
- `backend/experiments/e57/alignment_audit.md`;
- `backend/experiments/e57/label_audit.md`.

**Served records and calibration**
- `backend/data/e36/e36_record.json`, `e49/e49_record.json`, `e53/e53_record.json`;
- `backend/data/e49/model/E49_C2_calibration.json`, `backend/data/e53/model/E53_C2_calibration.json`.

**Prediction files** (raw and calibrated per-row probabilities)
- `backend/experiments/e49/runs/20261015T215405Z/predictions.csv` (arms C0 = raw, C2 = served);
- `backend/experiments/e53/runs/20261016T104745Z/predictions.csv` (arm A1, `p_raw` and `p`);
- `backend/experiments/e55/runs/20261016T122641Z/predictions.csv` (E55, lead 2);
- `aipheed-backend-aligned/experiments/E38_Lead2_Diagnosis_Tuning/runs/20261015T033922Z/predictions.csv`
  (E38-LGBM, lead 2).

**Experiment results**
- `backend/experiments/e59/E59_results.json` and `.md` (lead scan), `backend/experiments/e59/nns_face_validity.md`;
- `backend/experiments/e58/E58_results.md` (calibration), `backend/experiments/e56/E56_results.md` (labels);
- `backend/data/news_e31/topics/manifest.json` (BERTopic);
- `aipheed-backend-aligned/experiments/E25_Reliable_Forecasts_2021_2026/instruments/` (questionnaire and decision
  rules).

**Code**
- `backend/app/quarterly/verdicts.py`, `app/quarterly/alerts_e31.py`, `app/services/dashboard.py`,
  `app/news/fssi.py`, `app/news/relevance.py`, `app/ml/nlp/trigger_classifier.py`, `app/tasks/scheduler.py`,
  `app/api/v1/admin.py`, `app/api/v1/alerts.py`, `app/api/v1/forecast.py`, `app/services/feedback.py`,
  `app/ml/features/label_generator.py`;
- `backend/aipheed.db` (row counts, read with sqlite3).

---

## 2. Summary count

| Status | Count |
|---|---|
| ALIGNED | 22 |
| PARTIAL | 25 |
| DEVIATES | 9 |
| NOT IMPLEMENTED | 3 |
| UNTESTABLE | 3 |
| **Total items (a-f)** | **62** |

**The 16 known deviations (g):**
- 3 resolved: #6, #11 and #16. #16 is resolved at serving time only; the record text is still wrong.
- 1 partly resolved: #10.
- 12 still open.

Section 7 adds 8 findings that were not in the earlier list.

---

## 3. Alignment matrix

### (a) General and specific objectives (pp. 12-13)

| ID | Paper | System | Status | Evidence |
|---|---|---|---|---|
| A1 | GO: "To develop, validate, and deploy aiPHeed" (p.12) | Developed: FastAPI backend and React dashboard, serving E49 by default. Validated on development data only. Not deployed. | PARTIAL | Runs locally only. `aipheed.db`: admin_users 0, review_records 0. 2026-Q4 forecast frozen, "awaiting the SWS December 2026 round" (`e49_record.json` validation.prospective_2026Q4.status). |
| A2 | SO1: XLM-RoBERTa + BERTopic "two-tier pipeline" giving a bias-corrected FSSI and "latent food insecurity risk patterns" (p.12) | XLM-R gives intensity (`fssi_v2`). Relevance is decided by keyword rule R1.1. BERTopic was run but failed its stability gate, so it publishes no patterns. | PARTIAL | `e49_record.json` news.fssi_v2_manifest / validation.news_relevance.rule = "R1.1". `data/news_e31/topics/manifest.json` status "UNSTABLE". |
| A3 | SO2 I-IV: accuracy, precision/recall, F1, AUC-ROC (pp.12-13) | All computed and stored for the proposed model and six baselines | ALIGNED | `validation.model_evaluation.rows` in each record; section 4 of this file |
| A4 | SO2 V: lead-time performance by walk-forward expanding-window CV, to find the furthest reliable horizon (p.13) | E59 scanned k = 1..8 with the served E49 family. Maximum Reliable Lead Time = 1. | ALIGNED | `experiments/e59/E59_results.json` algorithm3.maximum_reliable_lead_time = 1. Window differences are under B8. |
| A5 | SO3: LGU rankings from "validated province-level forecasts", PSA poverty + population density (p.13) | 142 LGU rows using the p.45-47 formula. The province input is not validated against baselines. Density uses 2024 POPCEN, not the 2020 census. | PARTIAL | `e49_record.json` lgu_ranking.method / meaning ("has NOT been validated against baselines ... EXPERIMENTAL"); `app/services/dashboard.py:_municipal_frame` |
| A6 | SO4: compare against persistence, PSA-only, NLP-only and LR baselines (p.13) | B1-B6 plus always-HIGH, on the same 65 rows. The outcome is negative. | ALIGNED | `validation.model_evaluation.rows` / `paired_vs_baselines` |
| A7 | SO5: "deploy a public geospatial dashboard ... forecast maps and early-warning alerts" (p.13) | Dashboard, maps and alerts are implemented, locally only. No alert has ever been staged or confirmed. | PARTIAL | `aipheed.db` alert_records 0; `app/api/v1/alerts.py` confirm/dismiss routes |
| A8 | SO5: ISO/IEC 25010 evaluation with DA Region IV-A evaluators (p.13) | Instrument and decision rules exist; no responses | UNTESTABLE | `E25.../instruments/QUESTIONNAIRE.md`, `DECISION_RULES.md`, `RESPONSE_EXPORT_TEMPLATE.csv` (header only); `aipheed.db` feedback_records 0 |
| A9 | SO5: validate against DOST-FNRI NNS "2019 and 2023" (p.13) | 2023 only: CALABARZON 19.1%, the lowest region, and 2023 is the model's lowest year. The 2019 regional figure was not found. | PARTIAL | `experiments/e59/nns_face_validity.md` (source `data/e22/nns_fies_verified.json`) |

### (b) Algorithms, formulas and rules (pp. 30-60)

| ID | Paper | System | Status | Evidence |
|---|---|---|---|---|
| B1 | Data integration: 12 features on a 120-135-row panel, fused from a 120 x 45 matrix (pp.30, 36-37, 42, 56) | E49: 18 inputs. E53: 23 inputs. 75 training rows at the 2026-Q4 origin. Includes regional SWS hunger inputs and the last label `y_last`. | DEVIATES | `served_engine.config.features` and `config.training_rows = 75` in each record |
| B2 | Algorithm 1: XLM-R zero-shot scoring. pp.37-38: maximum over 10 hypotheses, drop < 0.30, text truncated to 512 characters. pp.30/59/65: core score >= 0.30 **and** margin >= 0.20, truncated to 250. The manuscript is inconsistent. | XLM-R (`joeddav/xlm-roberta-large-xnli`) scores intensity only. Relevance comes from the R1.1 keyword rule, because the XLM-R gate measured precision 0.618 and recall 0.129 on 355 titles. | PARTIAL | `validation.news_relevance.development_sample.e28_gate`; `app/news/relevance.py` (VERSION_DEPLOYED = "R1.1") |
| B3 | Eq.1 spatial bias weight w = log(1+median)/log(1+n) (p.49) | Implemented | ALIGNED | `app/news/fssi.py` l.5 docstring and builder |
| B4 | Eq.2 FSSI, plus FSSI_lag1, lag2 and acceleration (pp.38, 50, 53) | FSSI is implemented (`fssi_v2`). The lags and acceleration are not among the served inputs. | PARTIAL | feature lists (B1): only `fssi_v2`, `fssi_missing` |
| B5 | Algorithm 2: regex triggers in 5 bilingual categories, as proportions (pp.39-40) | Implemented. The 5 `trig_*` proportions are served inputs. Titles only. | ALIGNED | `app/ml/nlp/trigger_classifier.py` `classify_triggers`, `compute_trigger_proportions`; feature lists |
| B6 | Eq.3 label: SWS hunger + 2 x CPI deviation from the regional mean, above the **global median** of all 120 province-quarters, giving "a 50/50 class balance" (pp.51-52) | S1 = H + 2D > **trailing** median of published quarters before the origin. 53 of 65 development labels are HIGH (82%). | DEVIATES | `target_definition.tau`; E59 k = 1 HIGH_rows 53 / LOW_rows 12 |
| B7 | Eq.4 secondary robustness label (p.51) | Exists only in the legacy pipeline. Not used or evaluated with the served E36-schema models. | PARTIAL | `app/ml/features/label_generator.py` l.54, 241; `app/ml/inference/thesis_predictor.py` l.10 |
| B8 | Algorithm 3: k = 1..8, 75% mean fold accuracy, halt at the first failure; minimum training window of 8 quarters; "a default LightGBM" (pp.41-42) | E59 implements the scan and the halting rule exactly: k = 1 0.846 passes, k = 2 0.709 halts. Differences: the training minimum is >= 10 rows (2 quarters x 5 provinces), not 8 quarters, and the model uses nested grid selection rather than defaults. | PARTIAL | `E59_results.md` pre-registration; `E59_results.json` algorithm3.trail |
| B9 | Algorithm 4: 100-trial Optuna TPE over 9 hyperparameters, mean weighted F1 (pp.43-44) | Not used. Nested choice of 2 feature sets x 4 fixed grids (G1-G4); the served grid is G2. | DEVIATES | `served_engine.config.grid_id = "G2"`; objectives_audit.md 2.4 |
| B10 | Stage 4 blend 0.4 LGBM + 0.4 LR(gov) + 0.2 LR(triggers), HIGH at 0.712 (p.30) | LightGBM alone, threshold 0.5 | DEVIATES | `app/quarterly/verdicts.py` / E59 "threshold 0.5"; quarter rows `threshold` field is tau, not a cutoff |
| B11 | Eq.5 forecast function inputs: FSSI(t, t-1, t-2), dFSSI, triggers, CPI_dev (rolling provincial mean), unemployment, rice change (pp.52-53) | Different inputs (B1). CPI deviation follows Eq.3 (regional mean), not Table 3.4.2.4 (rolling provincial mean). No provincial unemployment input. | DEVIATES | feature lists in each record |
| B12 | Probability calibration: **not in the paper** | C2 shrinkage p' = a*p + (1-a)*base rate, fitted on earlier dates. Brier improves a little, but the 10-bin ECE gets worse (section 4.2). | DEVIATES (addition, not described) | `experiments/e49/runner/e49_run.py` l.8-9; calibration JSONs; recomputed ECE |
| B13 | Eq.7 SHAP TreeExplainer, exact additive attribution (pp.54-55) | Exact TreeSHAP per input, in log-odds, for every province-quarter. Computed on the raw LightGBM, before calibration. | ALIGNED | quarter rows `driver_method`, `drivers` (18 / 23 entries), `shap_expected_value_logodds` |
| B14 | BERTopic topic modelling (pp.12, 29-30) | Fitted on 55 articles: 2 topics, 40% outliers, seed ARI 0.31 / 0.45 (mean 0.38 < 0.5). The gate failed, so it is descriptive and unpublished. | PARTIAL | `data/news_e31/topics/manifest.json` |
| B15 | Algorithm 5 / Eq.6 disaggregation: 0.6 poverty_norm + 0.4 density_norm, min-max within province, clamped [0,1]; PSA 2021 SAE + **2020 census** density (pp.45-47, 53-54) | Same formula. Density is 2024 POPCEN. Lucena City uses a province substitute (unverified). | PARTIAL | `e49_record.json` lgu_ranking.method, provenance, input_checks.province_mean_substitutes = 1 |
| B16 | Rule 1: automatic quarterly retrain, outputs staged for mandatory review before publication (p.48) | APScheduler is off unless `AIPHEED_ENABLE_SCHEDULER=1`. The served records are frozen. Forecasts appear before review (see F7). | PARTIAL | `app/tasks/scheduler.py` l.45-46, 127 |
| B17 | Rule 2: the furthest reliable lead becomes the operational horizon (p.48) | Lead 1 is served by default (`AIPHEED_MAX_LEAD=1`) | ALIGNED | `app/quarterly/verdicts.py` max_reliable_lead -> lead 1 for E36/E49/E53 (recomputed) |
| B18 | Rule 3: no look-ahead (p.48) | Publication-date filters at every origin; calibration fitted on earlier dates only. Caveat: current data vintages and retroactive news retrieval. | ALIGNED | `E58_results.md` "Leakage check: 0"; E59 pre-registration (eligible earlier dates) |
| B19 | Rule 4: disaggregate "validated province forecasts only" (p.48) | Applied to unvalidated province estimates | PARTIAL | lgu_ranking.meaning |
| B20 | Rule 5: LIMITED_SIGNAL below 5 articles, propagated to all 142 LGUs (pp.35, 48, 65) | Implemented | ALIGNED | `app/services/dashboard.py:1390` `limited_signal` |
| B21 | Rule 6: horizon label, confidence statement, verification date (p.49) | Returned by `/forecast` | ALIGNED | `app/api/v1/forecast.py` l.99-122 |
| B22 | Rule 7: alert when the forecast "exceeds the rolling historical threshold"; "Human confirmation will be required before DSWD 4A is notified" (p.49) | Rolling rule implemented (above the 75th percentile of the province's own earlier estimates, at least 4). Alerts stay STAGED until confirmed. **No DSWD notification exists.** A fixed 0.60 "Alert" level is also used for display. | PARTIAL | `app/quarterly/alerts_e31.py` l.41-59; `app/api/v1/alerts.py` l.119-141; grep "DSWD" in `app/` finds only data-source comments |
| B23 | Rule 8: every LGU index carries a disaggregation_label (p.49) | Yes | ALIGNED | `municipality_summary` docstring; lgu rows `evidence_status` |
| B24 | 3.4.4: a lead time that does not clear the thresholds "will not be published to the dashboard" (pp.57-58) | Default lead 1 clears them. With `AIPHEED_MAX_LEAD=2`, a lead-2 preview that fails 75% (E55 0.673) is shown, labelled experimental. | PARTIAL | `e53_record.json` quarters 2027-Q1 status text; `next_quarter_evaluation.verdict` |

### (c) Hypotheses (pp. 11-12)

| ID | Null hypothesis | Test used | Statistic | Verdict | Status |
|---|---|---|---|---|---|
| C1 | H1: FSSI and food CPI deviation will not be among the strongest predictors (SHAP) | None. The paper names no test; SHAP ranks are descriptive. | Recomputed mean \|SHAP\| over 5 provinces x 14 lead-1 quarters (2023-Q1..2026-Q4). **Dnow rank 1** in E49 and E53 (top 3 in 13/14 quarters, top 5 in 13/14; rank 6 in 2023-Q1). **fssi_v2 rank 8 (E49) / 13 (E53)**, top 5 in 1/14. | Not rejected for FSSI; rejected for CPI deviation. As stated jointly, **not rejected**. | PARTIAL (no inferential test) |
| C2 | H2: will not reliably classify across multiple lead times | Algorithm 3 point rule (75%) and CI rule, E59 | k = 1: 0.846 (0.769-0.923). k = 2: 0.709 (0.582-0.836) | **Null not rejected**: reliable at one lead only | ALIGNED |
| C3 | H3: combined LightGBM will not outperform the six baselines | Two-sided sign-flip test on per-date Brier, Holm over 6 (the paper names no test) | E49 raw p 0.090-0.415, Holm 0.54-0.83. E53 raw p 0.142-0.514, Holm 0.85-1.0. Accuracy is below persistence (0.877) for both. | **Null not rejected** | ALIGNED |
| C4 | H4: LGU rankings not consistent with evaluators | Pre-declared one-sided Wilcoxon (DECISION_RULES.md) | none: 0 responses | untested | UNTESTABLE |
| C5 | H5: no favourable ISO/IEC 25010 ratings | Pre-declared median >= 4.0, Wilcoxon vs 3.0, Holm | none: 0 responses | untested | UNTESTABLE |

C1 sources: recomputed from `quarters[].provinces[].drivers[].contribution` in `e49_record.json` / `e53_record.json`.
C3 source: `validation.model_evaluation.paired_vs_baselines`.

### (d) Data sources and periods

| ID | Paper | System | Status | Evidence |
|---|---|---|---|---|
| D1 | SWS quarterly hunger (pp.15, 32, 51) | SWS Balance Luzon, one regional value for all five provinces. 2025-Q2/Q3 rounds are recorded as supplementary, so those quarters have no label. | ALIGNED | `regional_hunger.what`, `geographic_level`; served gap reason (`dashboard._e31_unavailable_reason`) |
| D2 | PSA provincial food CPI (pp.15, 32, 51) | PSA provincial CPI, giving D and Dnow | ALIGNED | `target_definition.D` |
| D3 | News corpus: RSS + Google News + GDELT, Jan 2020-Dec 2025, 17,791 raw / 6,085 / 371 audited (pp.30-31) | Google News RSS titles, 2021-01-01..2026-10-14: 8,320 collected / 2,820 province-attributed / 140 admitted | PARTIAL | `news.source`, `news.totals` |
| D4 | PSA LFS/NRP, BSP, DOE, PAGASA, PhilRice (pp.15, 32) | No DOE, PAGASA or PhilRice input. E53 adds national LFS/BSP conditions plus NASA POWER and NOAA IBTrACS. | DEVIATES | feature lists; `e53_record.json` limitations[2] (national-level indicators) |
| D5 | NNS 2019 and 2023 (p.13) / NNS 2021 and 2023 (p.51) as a face-validity anchor | 2023 regional figure verified (19.1%). 2019 and 2021 regional figures not found; 2021 provincial decks exist for Batangas and Cavite only. | PARTIAL | `experiments/e59/nns_face_validity.md` l.15-23 |
| D6 | PSA 2021 SAE poverty + 2020 census density (pp.45-46, 60) | PSA 2021 SAE (141/142 LGUs) + 2024 POPCEN | PARTIAL | `lgu_ranking.provenance` |

### (e) Target, 75% threshold and evaluation protocol

| ID | Paper | System | Status | Evidence |
|---|---|---|---|---|
| E1 | L0 target with a global-median threshold and balanced classes (pp.51-52) | Trailing median. Class balance 53 HIGH / 12 LOW on the 65 development rows. E56 tried 4 alternatives and none was eligible. | DEVIATES | `target_definition`; recomputed n_high / n_low; `experiments/e56/E56_results.md` |
| E2 | 75% mean accuracy threshold (pp.41-42, 57) | E49: 0.846, CI 0.769-0.923, demonstrated. E53: 0.785, CI 0.646-0.908, point only. E36: 0.815, CI 0.738-0.892, point only. | ALIGNED (E49) | `compose_75pct_verdict` via `verdict_from_record` (recomputed) |
| E3 | Walk-forward expanding window, one quarter per fold, minimum 8 training quarters (pp.41-42) | Nested walk-forward, one target quarter per fold, 13 folds (2023-Q1..2026-Q3, excluding 2025-Q2/Q3). Training minimum >= 10 rows. Accuracy CI by date bootstrap (the paper names no CI method). | PARTIAL | `validation.model_evaluation.basis`, `.dates` |
| E4 | Blind four-quarter holdout 2025-Q4..2026-Q3, never exposed to tuning (pp.30-31, 43-44) | None: all 13 dates were examined during development. The only untouched test is the frozen 2026-Q4 forecast, not yet scorable. | DEVIATES | quarter rows `status` ("the outcome had been examined in earlier experiments"); `prospective_2026Q4` |
| E5 | F1 >= 0.75 and AUC-ROC >= 0.80 (pp.44, 57, 59-60, 65) | E49 F1 0.900, AUC 0.855. E53 0.851 / 0.880. Met, but on development data, not a blind holdout. | PARTIAL | `model_evaluation.rows` E36-LGBM |

### (f) System features stated in the paper

| ID | Paper | System | Status | Evidence |
|---|---|---|---|---|
| F1 | Interactive map with risk levels, per province and CALABARZON (pp.14-15) | Dashboard map; CALABARZON index = mean of the five provinces | ALIGNED | `/api/v1/provinces`; `svc.region_forecast` |
| F2 | "factors influencing each forecast" / SHAP panel (pp.15, 62) | `/api/v1/explainability` (province / region / municipality); 0% drivers omitted | ALIGNED | `app/api/v1/insights.py:126`; `tests/integration/test_explainability_alignment.py` |
| F3 | Province ranking (p.62) | `/api/v1/ranking` | ALIGNED | `app/api/v1/dashboard.py:150` |
| F4 | Municipal rankings for 142 LGUs (pp.14, 62) | `/api/v1/provinces/{id}/municipalities`; 142 rows | ALIGNED | `lgu_ranking.input_checks.rows_roster = 142` |
| F5 | Early-warning alerts, admin confirm/dismiss (pp.13, 49, 62, 67) | Implemented (staged, confirm, dismiss, public list). Never exercised. | PARTIAL | `app/api/v1/alerts.py` l.100-166; alert_records 0 |
| F6 | Downloadable PDF report with scores, SHAP, metrics, data sufficiency, per province and CALABARZON (p.15) | Backend PDFs (`/quarterly/e31/report.pdf`, report routes) and the Visualization PDF (`/report/data`) | ALIGNED | `tests/integration/test_report_payload.py`; samples in `experiments/e57/report_samples/` |
| F7 | DA admin review: STAGED, then approve or reject (pp.60, 66-67) | Admin review routes exist. Forecasts are visible before approval and are only withheld when rejected. That matches pp.60/66, but not p.67 ("no forecasts ... without human decision-making"). No admin account exists. | PARTIAL | `app/api/v1/admin.py` l.5-24, 161-211; admin_users 0, review_records 0 |
| F8 | Post-Survey Questionnaire (Google Form), ISO/IEC 25010 (p.67) | In-app SUS form (`/feedback`) plus the questionnaire as a document. 0 responses. | PARTIAL | `app/services/feedback.py` SUS_VERSION "sus-v1"; feedback_records 0 |
| F9 | History of past predictions (p.62) | `/forecast/timeseries` | ALIGNED | `app/api/v1/forecast.py` |
| F10 | APScheduler run on the 15th of Jan/Apr/Jul/Oct at 02:00 PHT; admin can start a run (p.59) | Cron is implemented but disabled by default. `/admin/pipeline/run` exists. | PARTIAL | `app/tasks/scheduler.py` l.46, 127; `admin.py:244` |
| F11 | Public deployment (pp.13, 62) | None. Local only. | NOT IMPLEMENTED | no deployment config or host in the repo (NOT VERIFIED outside the repo) |
| F12 | DSWD 4A notified after confirmation (pp.49, 52) | No notification channel | NOT IMPLEMENTED | grep "DSWD" in `backend/app` |
| F13 | DA evaluators "serve as domain expert annotators" (p.67); articles enter the audited set "only after a reviewer has read it" (p.59) | Relevance labels were made by the AI assistant. There is no reviewer-read queue for articles. | NOT IMPLEMENTED | `validation.news_relevance.annotator` = "AI assistant (Claude) ... researcher re-review recommended" |

### (g) The 16 known deviations (from objectives_audit.md section 3)

| # | Deviation | Status 2026-10-18 | Evidence |
|---|---|---|---|
| 1 | Label threshold: trailing vs global median | **Open** (E56/E57 found no eligible alternative) | E1 |
| 2 | CPI deviation: Eq.3 (regional mean) vs Table 3.4.2.4 (rolling provincial mean) | **Open** (manuscript wording) | B11 |
| 3 | Model: Optuna blend at 0.712 vs LightGBM alone + C2 at 0.5 | **Open** | B9, B10 |
| 4 | Features: 12 vs 18/23; no FSSI lags; y_last and H inputs added | **Open** | B1, B4 |
| 5 | Validation: blind holdout vs development walk-forward | **Open** (2026-Q4 forecast frozen, awaiting the outcome) | E4 |
| 6 | Lead scan k = 1..8 | **Resolved** (E59) | A4, B8 |
| 7 | Minimum training window 8 quarters vs >= 10 rows | **Open** | B8, E3 |
| 8 | Relevance gate: XLM-R vs R1.1; AI-made labels | **Open** | B2, F13 |
| 9 | Corpus size and period | **Open** | D3 |
| 10 | BERTopic | **Partly resolved**: run with output stored, gate failed, not published | B14 |
| 11 | Alert rule: rolling threshold | **Resolved in code** (`ROLLING_THRESHOLD`). The fixed 0.60 display level remains, and DSWD notification is missing. | B22 |
| 12 | Review visibility (pp.60/66 vs p.67) | **Open** (manuscript inconsistency plus a design decision) | F7 |
| 13 | Data sources (PAGASA, PhilRice, DOE, DOST-FNRI) | **Open** | D4 |
| 14 | Density year 2020 vs 2024 | **Open** | D6 |
| 15 | Evaluators (DEPDev in RQ5 vs 50 DA in scope/3.7) | **Open** | A8 |
| 16 | E49 stored 75% verdict sentence wrong | **Resolved at serving time** (`app/quarterly/verdicts.py`). The record file still holds the wrong sentence (protected). | section 4.1 |

---

## 4. Model metrics (served records)

### 4.1 Lead 1, 65 development rows (13 target quarters 2023-Q1..2026-Q3, excluding 2025-Q2/Q3), threshold 0.5

Class balance: 53 HIGH / 12 LOW (81.5% HIGH). Source: recomputed from `quarters[mode=BACKTEST, lead=1]` in each record.

| Metric | E49-C2 (default) | E53-A1 (preview) | E36 (baseline record) | Source |
|---|---|---|---|---|
| Correct / n | 55/65 | 51/65 | 53/65 | record `model_evaluation.rows[E36-LGBM]`; recomputed identical |
| Accuracy (95% date-bootstrap CI) | **0.846 (0.769-0.923)** | **0.785 (0.646-0.908)** | **0.815 (0.738-0.892)** | record; recomputed CI identical |
| Balanced accuracy | 0.841 | 0.836 | 0.822 | record; recomputed identical |
| Precision HIGH / LOW | 0.957 / 0.556 | 0.976 / 0.458 | 0.956 / 0.500 | HIGH: record; LOW: recomputed |
| Recall HIGH / LOW | 0.849 / 0.833 | 0.755 / 0.917 | 0.811 / 0.833 | HIGH: record (LOW = record specificity) |
| F1 HIGH / LOW | 0.900 / 0.667 | 0.851 / 0.611 | 0.878 / 0.625 | HIGH: record; LOW: recomputed |
| Macro precision / recall / F1 | 0.757 / 0.841 / 0.783 | 0.717 / 0.836 / 0.731 | 0.728 / 0.822 / 0.751 | recomputed |
| ROC-AUC | 0.855 | 0.880 | 0.850 | record; recomputed identical |
| PR-AUC (HIGH, average precision) | 0.960 | 0.966 | 0.949 | recomputed |
| Brier | 0.151 | 0.150 | 0.154 | record; recomputed identical |
| Log loss | 0.489 | 0.482 | 0.508 | recomputed |
| Confusion (TP / FN / FP / TN; HIGH = positive) | 45 / 8 / 2 / 10 | 40 / 13 / 1 / 11 | 43 / 10 / 2 / 10 | recomputed |
| Lead time | 1 quarter | 1 quarter | 1 quarter | `max_reliable_lead` (recomputed) |
| 75% target (`compose_75pct_verdict`) | point met; **demonstrated** (lower bound 0.769 >= 0.75) | point met; **not demonstrated** (0.646) | point met; **not demonstrated** (0.738) | `verdicts.verdict_from_record` on each record (recomputed) |
| Baselines on the same rows | persistence 0.877, always-HIGH 0.815 | same | same | record `model_evaluation.rows` |

The recomputed numbers match the record values exactly. The record's served probabilities also match the run files'
calibrated arm (E49 C2, E53 A1) within 5.0e-05, and every label matches.

`e49_record.json` `validation.threshold_75pct` says `demonstrated: true`, but its stored `verdict` sentence says
"reaches below 75%, so the target is not demonstrated". The record contradicts itself; the served text is composed
correctly.

### 4.2 Calibration before and after C2 (lead 1, 65 rows)

ECE = 10 equal-width bins, weighted |mean predicted - observed HIGH share|. It is recomputed and noisy at n = 65. No
ECE exists in any record or report: E58 reports 5-bin reliability tables, not ECE.

| Model | State | Accuracy | Brier | Log loss | ECE (10-bin) | ROC-AUC | Source |
|---|---|---|---|---|---|---|---|
| E49 | raw E48-A1 (arm C0) | 0.815 | 0.154 | 0.520 | **0.156** | 0.839 | recomputed, `e49/runs/.../predictions.csv` |
| E49 | C2 (served) | 0.846 | 0.151 | 0.489 | **0.178** | 0.855 | recomputed |
| E53 | raw (A1 `p_raw`) | 0.785 | 0.152 | 0.499 | **0.169** | 0.864 | recomputed, `e53/runs/.../predictions.csv` |
| E53 | C2 (served) | 0.785 | 0.150 | 0.482 | **0.209** | 0.880 | recomputed |
| E36 | no calibration | 0.815 | 0.154 | 0.508 | 0.187 | 0.850 | recomputed from the record |

- C2 lowers Brier and log loss slightly for both models.
- C2 **raises** the 10-bin ECE for both (E49 +0.022, E53 +0.040). By that measure it does not make the
  probabilities better calibrated.
- E49_results reports the Brier gain over raw as "not significant" (`served_engine.evidence_status`).

### 4.3 Lead 2 (55 rows, 11 target quarters 2023-Q3..2026-Q3; 49 HIGH / 6 LOW)

| Metric | E38-LGBM (E49's lead-2 row) | E55 (E53 lead-2 preview) | Source |
|---|---|---|---|
| Correct / n | 39/55 | 37/55 | record `next_quarter_evaluation.rows` |
| Accuracy (95% CI) | 0.709 (0.582-0.836) | 0.673 (0.545-0.800) | record. Recomputed CI: E38 identical; E55 0.527-0.800 (different bootstrap seed) |
| Balanced accuracy | 0.544 | 0.670 | record |
| Precision / Recall / F1, HIGH | 0.902 / 0.755 / 0.822 | 0.943 / 0.673 / 0.786 | recomputed from the run files |
| Precision / Recall / F1, LOW | 0.143 / 0.333 / 0.200 | 0.200 / 0.667 / 0.308 | recomputed |
| Macro F1 | 0.511 | 0.547 | recomputed |
| ROC-AUC | 0.655 | 0.811 | recomputed (E59's own lead-2 rerun gives 0.738; see the note below) |
| PR-AUC (HIGH) | 0.938 | 0.972 | recomputed |
| Brier | 0.200 | 0.214 | record; recomputed identical |
| Log loss | 0.591 | 0.630 | recomputed |
| ECE (10-bin) before / after calibration | NOT AVAILABLE (no raw column in the E38 run file) / 0.212 | 0.314 / 0.299 | recomputed |
| Confusion TP / FN / FP / TN | 37 / 12 / 4 / 2 | 33 / 16 / 2 / 4 | recomputed (E55 LOW recall 4/6 matches the record) |
| 75% target | not met | not met | record `next_quarter_evaluation.verdict` |
| Persistence / always-HIGH on the same rows | 0.800 / 0.891 | same | record |

**Note on lead-2 AUC.**
- The E38 run file (arm `E38-LGBM`) gives AUC 0.655.
- E59's k = 2 rerun of the **E49** family (with C2) gives accuracy 0.709, matching E38, but AUC 0.738 and Brier 0.218
  instead of 0.200 (`E59_results.json` leads[1]).
- So the E59 k = 2 model and the E38 row are not the same predictions; their accuracy coincides. **NOT VERIFIED**
  which one the record's lead-2 row reflects beyond accuracy and Brier, which match E38.

### 4.4 E59 Algorithm 3 lead scan (served E49 family; `experiments/e59/E59_results.json`)

| k | Dates | Rows (LOW) | Accuracy (95% CI) | Balanced | AUC | Brier | Persistence acc | Evaluable | Algorithm 3 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 13 | 65 (12) | 0.846 (0.769-0.923) | 0.841 | 0.855 | 0.151 | 0.877 | yes | pass |
| 2 | 11 | 55 (6) | 0.709 (0.582-0.836) | 0.544 | 0.738 | 0.218 | 0.800 | yes | **halt** |
| 3 | 9 | 45 (3) | 0.733 (0.622-0.844) | 0.393 | 0.591 | 0.213 | 0.756 | yes | after halt |
| 4 | 7 | 35 (2) | 0.800 (0.629-0.943) | 0.424 | 0.515 | 0.193 | 0.800 | yes | after halt |
| 5 | 5 | 25 (1) | 0.960 (0.880-1.000) | 0.500 | 0.250 | 0.092 | 0.880 | yes | after halt |
| 6 | 4 | 20 (1) | 0.900 (0.800-1.000) | 0.474 | 0.816 | 0.082 | 0.900 | yes | after halt |
| 7 | 3 | 15 (1) | 0.933 (0.800-1.000) | 0.964 | 0.964 | 0.052 | 0.867 | no (3 dates < 4) | after halt |
| 8 | 1 | 5 (0) | 1.000 (1.000-1.000) | n/a | n/a | 0.008 | 1.000 | no (1 date) | after halt |

- **Maximum Reliable Lead Time = 1 quarter** by the point rule and by the CI rule (`algorithm3`, `algorithm3_ci`).
- The high accuracies at k = 3-6 come with balanced accuracy <= 0.5 and very few LOW rows. They reflect predicting
  HIGH in an 85-96% HIGH period, not skill.
- E59 confirms that k = 1 reproduces E49 (`k1_reproduces_E49: true`), and its md5s are unchanged from start to end.

### 4.5 BERTopic stability (`backend/data/news_e31/topics/manifest.json`, created 2026-10-17T13:37:05Z)

| Item | Value | Gate (fixed before the run) | Pass |
|---|---|---|---|
| Articles | 55 (authorized, title-geocoded, XLM-R score >= 0.3) | >= 30 | yes |
| Topics | 2 | >= 2 | yes |
| Outlier share | 0.40 (22 of 55) | <= 0.5 | yes |
| Seed-stability ARI (seeds 43, 44 vs 42) | 0.311, 0.449; mean 0.380 | >= 0.5 | **no** |
| Status | **UNSTABLE**: "publication gate failed: stability". No topic proportions published. | | |

Model: paraphrase-multilingual-MiniLM-L12-v2 embeddings, UMAP 5-d, HDBSCAN, min_topic_size 10. It is descriptive
only, not a forecast feature.

---

## 5. What still blocks full alignment

| Blocker | What closes it | Who / what |
|---|---|---|
| H4, H5, SO5 ISO/IEC 25010, RQ4/RQ5 (A8, C4, C5) | >= 30 valid DA Region IV-A responses to the Post-Survey Questionnaire, analysed with `DECISION_RULES.md` | **Survey data** (researchers + DA) |
| Blind test (E4, deviation 5) | Score the frozen 2026-Q4 forecast after the SWS December 2026 round; 2027-Q1 after its round | **Time/data** (SWS release), then a code run |
| Deployment, admin review, alert confirmation (A1, A7, F5, F7, F11) | Host the system; create DA admin accounts; run one review and alert cycle | **Researchers + DA** (ops), little code |
| DSWD notification (F12, Rule 7) | Implement a notification after alert confirmation, or remove "before DSWD 4A is notified" from Rule 7 | **Code** or **manuscript wording** |
| Review visibility (F7, deviation 12) | Pick one rule. Either hide STAGED forecasts until approved (code), or change p.67 to match pp.60/66 (wording). | **Decision**, then code or wording |
| Label, model, features, Optuna, blend, CPI_dev definition, training window (B1, B6, B9-B11, E1, E3; deviations 1-4, 7) | Rewrite Chapter 3 to describe what was built (trailing-median L0, LightGBM + C2 at 0.5, nested grid selection, 18/23 inputs, >= 10 training rows) and report the global-median design as replaced | **Manuscript wording** |
| C2 calibration (B12) | Describe C2 in Chapter 3, and state that it improves Brier slightly but not ECE | **Manuscript wording** |
| Relevance gate and annotation (B2, F13, deviation 8) | Researcher (or DA) re-review of the AI-made relevance labels; describe R1.1. Also fix the p.30/59/65 vs p.37-38 inconsistency (5 core vs 10 hypotheses; 250 vs 512 characters). | **Researchers** + **manuscript wording** |
| FSSI lags/acceleration (B4) | Add them as inputs and re-evaluate (a new experiment; changes the model), or drop them from Eq.5 / Table 3.4.2.4 | **Code + new experiment** or **wording** |
| BERTopic (A2, B14) | A larger reviewed corpus and a refit, or describe it as attempted and unstable | **Data** or **wording** |
| NNS anchor (A9, D5) | Official 2019 and 2021 CALABARZON FIES values with citations; fix p.13 ("2019 and 2023") vs p.51 ("2021 and 2023") | **Data (DOST-FNRI)** + **wording** |
| Data sources and density year (D4, D6, deviations 13-14) | State the sources actually used (no PAGASA/PhilRice/DOE input; 2024 POPCEN) | **Manuscript wording** |
| Lead-2 preview vs 3.4.4 (B24) | Keep `AIPHEED_MAX_LEAD=1` for any public instance, or state the preview exception in 3.4.4 | **Config** or **wording** |
| Rule 1 automatic retraining (B16, F10) | Enable the scheduler in deployment and show that a cycle rebuilds the served record | **Code/ops** |
| Evaluator group (deviation 15) | Make RQ5 (DEPDev) consistent with the scope and 3.7 (50 DA personnel) | **Manuscript wording** |
| E49 record verdict sentence (deviation 16) | Rebuild the record with the composer (changes a protected file), or note the error | **Researcher decision** (protected file) |

---

## 6. Neutral reading

- The default model (E49) meets the paper's 75% lead-1 accuracy target, including the CI lower bound (0.769), and
  meets the F1/AUC targets. It does so only on development data, never on a blind holdout.
- It does **not** beat any of the six baselines significantly, and naive persistence is more accurate (0.877 vs
  0.846).
- The Maximum Reliable Lead Time is one quarter.
- News signals add no measurable skill (B5 government-only LightGBM ties E49 at 0.846).
- Two of five hypotheses (H4, H5) and the ISO evaluation cannot be tested without survey responses.
- A large part of Chapter 3 (label threshold, Optuna, blend, features, holdout) describes a design that was replaced.
  Those items need manuscript changes, not code.

---

## 7. Findings not in the earlier deviation list, and corrections

1. **NNS years inconsistent in the manuscript:** p.13 says NNS 2019 and 2023; p.51 says NNS 2021 and 2023.
2. **Algorithm 1 inconsistent in the manuscript:**
   - pp.37-38: maximum over 10 hypotheses, keep >= 0.30, truncate to 512 characters.
   - pp.30/59/65: core-food score >= 0.30 with margin >= 0.20, truncate to 250 characters.
3. **Lead-2 preview vs 3.4.4 (p.58):** with `AIPHEED_MAX_LEAD=2`, a lead that fails the 75% threshold is shown. It is
   labelled experimental, and it is off by default.
4. **DSWD notification (Rule 7, p.49) is not implemented.**
5. **Evaluators as annotators (p.67) / reviewer-read article queue (p.59):** not done. The relevance labels were made
   by the AI assistant.
6. **Stale self-description in the E49 record (protected):**
   - `served_engine.name` ends in "- PREVIEW";
   - `served_engine.why_served` says "the official system serves E36";
   - since commit 430a347, E49 is served by default.
7. **C2 calibration worsens the 10-bin ECE** (section 4.2), although it lowers Brier and log loss.
8. **Correction to objectives_audit.md H1:** food-CPI deviation (`Dnow`) is in the top 5 in **13 of 14** quarters,
   not 14/14 (rank 6 in 2023-Q1). It is in the top 3 in 13/14. Recomputed from the stored drivers in both records.

---

## 8. Updates after E60-E63 (2026-10-18)

This section supersedes the statuses above where they differ. Sections 0-7 are kept as written on the morning of
2026-10-18; the corrections are listed here instead of being edited in.

**Sources**
- `backend/experiments/e60/E60_results.md`, `e61/E61_results.md`, `e62/E62_results.md`;
- `e63/ISO25010_objective_report.md`;
- `scripts/rebuild_served_record.py` and `tests/integration/test_rebuild_record.py`;
- `tests/integration/test_alignment_flags.py`.

Each experiment was pre-registered and md5-stamped before it was computed. The 7 protected md5s were unchanged
throughout.

### E60: sensitivity of the served E49 family (report only)

- **FSSI lags (FSSI_lag1, FSSI_lag2, FSSI_accel)** added to the inputs: no effect. The Brier difference vs E49 is
  +0.0002 (sign-flip p = 0.90), with identical accuracy (0.846).
  - **B4 is closed:** the lags are not in the served model, and that is now an evidence-based, documented deviation
    rather than a gap.
  - Status: **PARTIAL -> DEVIATES (justified by E60)**.
- **Eq. 4 robustness label:** run with the repository's own label code, extended to 2026-Q3. The label is
  **degenerate**: 62 of 65 rows are HIGH, and the model catches 0 of the 3 LOW rows (balanced accuracy 0.492).
  - Its significant Brier gain over persistence (p = 0.013) comes from confident HIGH predictions on a nearly
    constant label, not from skill.
  - The secondary sanity check the paper describes has now been performed; it does not change any L0 conclusion.
  - Status: **B7 PARTIAL -> ALIGNED (performed; result degenerate)**.
- **Algorithm 3 with the paper's 8-quarter minimum training window (k = 1, 2):** Maximum Reliable Lead Time = **2 by
  the point rule** (k = 2: 0.760 on only 5 dates; balanced accuracy 0.41; 0 of 2 LOW caught; below persistence
  0.880), and **1 by the CI rule** (lower bound 0.48).
  - The served model is equally accurate on those 5 dates (0.760). The point-rule pass comes from dropping the
    harder early dates, not from a better model.
  - **The operational lead stays 1.**
  - Status: B8 stays **PARTIAL** (the literal window is now tested; its answer depends on the rule).

### E61: BERTopic on the full province-attributed corpus

- **Gate:** the same pipeline and the same gate as E59, on all 2,820 authorized province-attributed titles. It
  **passes**: 59 topics, outlier share 0.384, mean seed-stability ARI 0.654 (0.651 / 0.657). The 55-article E59 fit
  had failed (ARI 0.38).
- **Content:** only about **15 of the 59** topics are food-related (floods, typhoons and calamities, fisheries,
  crops); most are place names, tourism, projects, crime and politics.
- **Files:** written to `data/news_e61/topics/` and not wired into the API.
- **SO1 and B14:** nearly met.
  - Stable topics now exist; they are descriptive (fitted on all quarters).
  - Calling them "food insecurity risk patterns" needs **human labelling** of the topics.
  - Status: stays **PARTIAL**.

### R1: Rule 1 quarterly rebuild

- **What it does:** `scripts/rebuild_served_record.py` rebuilds the E49-family record (walk-forward + freeze, E49-C2
  calibration, the record builder) into `data/rebuild/<YYYYMMDD>/`, never `data/e49/`.
- **Reproduction at the current cutoff:** all **70 of 70** served lead-1 probabilities are reproduced, with a max
  difference of **0.0**; the C2 parameters are identical. Nothing under the served record folders or
  `frontend/public` changed.
- **Scheduler:** the job is behind `AIPHEED_REBUILD_RECORD=1` (default off) and honours `AIPHEED_SCHEDULER_DRY_RUN`.
- **B16:** **PARTIAL -> ALIGNED.**
  - A tested quarterly retraining path now exists.
  - Promoting a rebuilt record stays a human step, which matches "staging all outputs for mandatory review".
  - Still to do: the scheduler must be switched on in deployment (F10, unchanged).

### Part A switches (same day, before E60; every one off by default)

- **A1:** an e-mail to `AIPHEED_DSWD_NOTIFY_EMAIL` is sent when an admin confirms an alert, and audited.
  **F12: NOT IMPLEMENTED -> PARTIAL** (implemented and tested; off by default; never used in production).
- **A2:** `AIPHEED_REQUIRE_APPROVAL=1` withholds unapproved forecasts. F7 stays **PARTIAL**: off by default, and
  deviation 12 still needs a decision.
- **A3:** `AIPHEED_COMPOSED_SELF_DESCRIPTION=1` serves an accurate engine name and why-served text (section 7, item 6).
  This is a serving-layer fix; the record file is unchanged.
- **A4:** scheduler dry-run and a deployment env example (`deploy/scheduler.env.example`, 02:00 PHT on the 15th of
  Jan/Apr/Jul/Oct).

### E62: robustness of the served E49 family (lead 1)

- **H1 permutation test** (input-value permutation, B = 200):

  | Input | Rank | p | Holm |
  |---|---|---|---|
  | Dnow | 1 | 0.005 | **0.015** |
  | fssi_v2 | 8 | 0.020 | **0.040** |
  | D_last | 7 | 0.363 | 0.363 |

  - fssi_v2's 8th rank is not unusual (rank p 0.12).
  - H1 now has an inferential test: food-price pressure is the strongest input and not by chance. The FSSI carries a
    small, above-chance attribution but is not among the strongest.
  - Status: **C1 PARTIAL -> ALIGNED.**
- **H3 power:**
  - With 13 dates, the minimum Brier gain detectable with 80% power is **0.062-0.090** against B1-B4 and B6, so "not
    significantly better" cannot exclude small gains.
  - Against B5 (government-only LightGBM) the minimum detectable gain is **0.019**, and the observed gain is -0.006:
    fairly direct evidence that news adds no measurable skill.
  - C3 stays **ALIGNED**, with this caveat added.
- **Seed robustness:** seeds 1-10 all give accuracy 0.846 and balanced accuracy 0.841. AUC is 0.855-0.858 and Brier
  0.150-0.152, so the 75% result is **seed-robust**.
- **Per province:** E49 beats persistence in Quezon and Batangas, and is worse in Cavite, Laguna and Rizal. It catches
  the same LOW quarters as persistence in every province.
- **Calibration: correction of section 4.2 and section 7, item 7.** The earlier statement "C2 worsens ECE" is
  **not supported**.
  - With the pre-registered [lo, hi) bins, ECE is C0 0.147 and C2 0.197.
  - The C2 - C0 difference is +0.051, 95% date-bootstrap CI **-0.034 to +0.076**, which includes 0.
  - The earlier 0.156 / 0.178 used right-closed bins.
  - Correct wording: "C2 slightly lowers Brier and log loss; there is no evidence that it changes the calibration
    error (ECE), with 65 rows."

### E63: objective ISO/IEC 25010 measurements

Recorded in `e63/ISO25010_objective_report.md`. They **complement the DA evaluator survey (H5); they do not replace
it**. H5, A8 and C5 stay **UNTESTABLE** until the survey responses exist.

- **Performance efficiency:** about 50 req/s saturation with one worker on the development laptop. p95 is 0.46 s at
  10 users and 7.4 s at 100 users; there were 0 errors.
- **Reliability:** 0 errors in 9,000 requests. After a kill, the server recovered in 5.3 s; 120 requests were lost
  during the restart and none after.
- **Security:**
  - every admin route refuses missing, expired and wrong-role tokens (48 new tests);
  - no personal data appeared on 20 public routes.
  - **Finding:** the reviewer's free-text rejection notes are public on `/rejections`. They name no reviewer, but any
    personal detail typed there is published.
- **Functional correctness:** every score is identical across `/provinces`, `/forecast`, `/ranking`,
  `/explainability` and the PDF payload, for all 14 quarters.

### Updated summary count (items a-f)

| Status | Before (section 2) | Now | Changes |
|---|---|---|---|
| ALIGNED | 22 | **25** | + B7 (Eq. 4 performed), + B16 (R1 rebuild), + C1 (H1 permutation test) |
| PARTIAL | 25 | **22** | - B4, - B7, - B16, - C1; + F12 |
| DEVIATES | 9 | **10** | + B4 (FSSI lags tested, no effect; documented deviation) |
| NOT IMPLEMENTED | 3 | **2** | - F12 (DSWD notification now exists, off by default) |
| UNTESTABLE | 3 | **3** | unchanged (A8, C4, C5: survey data) |
| **Total** | **62** | **62** | |

**The 16 known deviations:**
- **Resolved (3):** #6, #11, #16.
- **Partly resolved (2):**
  - #10 BERTopic: now passes its gate, but needs human labelling.
  - #12 review visibility: a switch exists; the decision is still open.
- **Open (11).**
- **Still blocking:** the evaluator survey (H4, H5, ISO 25010), the first blind test (2026-Q4, after the December 2026
  SWS round), deployment, and the manuscript wording listed in section 5.

---

## 9. Final served system

Branch `simplified-merge`, 2026-10-18, uncommitted. This section replaces the "default" / "preview" labels used in
sections 4 and 8. Those sections describe the state before the final integration, when E49-C2 was the default.

### 9.1 The served model is E53-A1

- **What it is:** E48-A1's inputs plus the five measured driver conditions (`cond_*`), with shrinkage calibration.
  Its record is `data/e53/e53_record.json`.
- **How it is selected:** E53 is served when `AIPHEED_RECORD` is unset (`e31_engine.DEFAULT_RECORD = "e53"`).
  `AIPHEED_RECORD=e49` and `AIPHEED_RECORD=e36` still serve those records.
- **Engine text:** the name and "why served" text are composed from the served record by default
  (`app/quarterly/self_description.py`; `AIPHEED_COMPOSED_SELF_DESCRIPTION=0` serves the stored text). The stored
  E53 text says "the default system serves E49", which is no longer true. The record file itself is unchanged.
- **Accuracy on development dates** (lead 1, 65 rows, 13 target quarters; record `model_evaluation.rows[E36-LGBM]`):

| Metric | E53-A1 |
|---|---|
| Accuracy | **0.785** (51/65) |
| 95% date-bootstrap CI | **0.646-0.908** |
| ROC-AUC | **0.880** |
| F1 (HIGH) | **0.851** |
| Precision / recall (HIGH) | 0.976 / 0.755 |
| Balanced accuracy | 0.836 |
| Brier | 0.150 |

- **The 75% target is not demonstrated with confidence.** The point estimate (0.785) is above 75%. The lower
  bound of the CI (0.646) is below 75%, so 75% accuracy is not shown with confidence. E49-C2 did show it (0.846,
  0.769-0.923), and it is still selectable.
- **No baseline is beaten significantly.** On the same rows, persistence scores 0.877 and always-HIGH 0.815.
- **The served scores are the record's own.**
  - Every province score is the record's `p_high`, and the region score is the mean of the five, rounded to 4
    decimals. Region 2026-Q2 is 0.7539, 2026-Q3 is 0.896 and 2026-Q4 is 0.7894.
  - A comparison against 262e81e checked 207 score values: none differs from the E53 record.
  - With the E49 record on both sides, no score, share or SHAP value differs between this branch and 262e81e.
- **SHAP audit (E53, re-run after the changes):**
  - *Additivity:* base + sum(SHAP) matches the raw log-odds within 2.8e-4 (the effect of 4-decimal rounding). The
    saved model file reproduces 2026-Q4.
  - *Grouping:* every input is in its Eq. 5 group.
  - *Shares and signs:* every share, region share and direction matches the record for 2025-Q1 to 2026-Q4.

### 9.2 Changes in the simplified merge

1. **All five drivers are listed again**, including a driver whose share rounds to 0%. The note says that such a
   driver "had no measurable effect on this forecast", and the PDFs print "no measurable effect" for it. When all
   five shares are 0 (the constant 2023-Q1 model), no driver is listed, as in 262e81e.
2. **Tied ranks** (E39, credit: **Angel Melindo**). Provinces with equal scores share one rank (competition
   ranking), and `rankTied` marks them. Scores are unchanged.
3. **Article counts** (D2). Every surface quotes the validated articles of the estimate's evidence quarter,
   de-duplicated, and `LIMITED_SIGNAL` uses the same count.
4. **Trigger status** (E42, credit: **Angel Melindo**). Each driver carries `status` (contributes / no_effect /
   no_model_input / no_data) and a plain `statusNote`.

The final integration also added two sentences to the explainability note:
- **Calibrated records (E49, E53):** "The bars explain the model's estimate before calibration. Calibration pulls
  every estimate toward the long-run rate, so it lowers or raises the index but does not change the shares."
- **CALABARZON only:** "For CALABARZON, a factor can raise the risk in some provinces and lower it in others; its
  bar shows the total size of its effect and its colour shows the net direction across the five provinces."

### 9.3 Known limitations

- **0% drivers are grouped by direction in the frontend.** A 0% driver has a SHAP of exactly 0, which the backend
  labels "increases_risk". The dashboard groups drivers by direction only and does not read `status`
  (`frontend/src/components/RightAnalyticsPanel.tsx:152-153`). So a 0% driver can appear under "Factors pushing risk
  up" with its risk wording; under E53 this affects 8 driver cards from 2025-Q1 to 2026-Q4. The API marks these
  drivers `status: "no_effect"` and the PDFs label them correctly. The frontend change was declined.
- **Rejection leak when `AIPHEED_REQUIRE_APPROVAL` is off** (the default). A province that a reviewer has rejected is
  withheld from `/provinces` and `/forecast`, but it still shows in:
  - `/explainability` (its score and drivers; the regional explainability score still includes it);
  - its LGUs' `riskIndex`;
  - `/report/data`.

  The leak was found in E63 and confirmed in the merge preview. These surfaces are withheld only with
  `AIPHEED_REQUIRE_APPROVAL=1`.
- **Lead 2 is only an experimental preview.** The 2027-Q1 row (E55, E53-A1 at lead 2) is served as a preview, and
  `AIPHEED_LEAD2_PREVIEW` is now on by default (`=0` turns it off). Its development accuracy is 0.673 (CI
  0.545-0.800, 55 rows), below both 75% and persistence (0.800). It raises no alerts. The API still labels it
  (`isPreview`, `belowAccuracyTarget`, `previewNote`), and lead 1 (2026-Q4) stays on the timeline. Every default
  other than the opening quarter stays on lead 1: the current quarter, the forecast target, quarter resolution, the
  PDF and the LGU ranking.
- **The dashboard opens on the 2027-Q1 lead-2 forecast** (E55, development accuracy 0.673, below 75% and below
  persistence 0.800) without an on-map label, by the researchers' decision. This deviates from 3.4.4 (a lead time
  that fails the thresholds is not published as a normal forecast); the accuracy is still stated in the methodology,
  /config and the PDF reports.
- **Resolved: every quarter's news card lists the news its estimate used.** For every quarter, backtests
  (2023-Q1 to 2026-Q3) included, the "News articles analyzed" card lists the validated articles of the record row's
  own `news_evidence_window.evidence_quarter`. That is the quarter before it, and every listed article was published
  before the row's origin.
  - `articleCount`, `limitedSignal`, `provinceCounts.limited` and `/news?view=used` are that one set.
  - It is also the evidence quarter used to split the news SHAP across the five drivers. All 15 served quarters were
    checked, on E53 and E49, with no difference.
  - Audit item e had counted a backtest's own-quarter news. Those articles were published after the backtest's
    origin, so the estimate never used them; they remain available as `view=published`.
  - No score, probability or SHAP value changed.
