# aiPHeed final report v2: E168 completion and updated compliance audit

**Date:** 2026-11-07
**Branch:** `aiPHeed/e158-thesis-model` in `C:\Users\admin\aipheed_e145`. Builds on the audit at `61f894a5`.
**Status of this version:** committed locally on `aiPHeed/e158-thesis-model` (latest `7f021ddb`); **not pushed and not deployed**.

**Pending items.** None. All runs have finished; their results are below.

**Reliability rule (project acceptance standard, owner decision 2026-11-07).** A lead is reliable when:
- pooled accuracy is ≥ 75 %, **and**
- the Brier score is significantly better than reusing the latest survey (95 % CI < 0).

The rule was set after E168's results were known; this is disclosed throughout. The thesis document's Algorithm 3 is not used as a criterion (owner instruction).

---

## 1. Verdict

### **PARTIALLY COMPLIANT**

**What changed since the audit (`61f894a5`):**
- The dashboard now runs entirely on the approved E168 model: map, province ranking, LGU ranking, explanations, summary, alerts and About panel. This is verified locally in tests and in the browser.
- The serving and validation feature paths are unified.
- E168-based alerts exist.
- Quarterly regeneration is automated, as staging only; the owner promotes each issue.
- FNRI face validity is implemented.
- BERTopic quality is measured.
- The ISO/IEC 25010 package is ready.

**What still prevents full compliance** (after re-grading the PARTIALs; see §2):
1. **Not deployed.** The public site still serves FIRI v2. Deploying needs the owner's go-ahead to push to `main`, the branch Render deploys.
2. **ISO/IEC 25010 not administered.** It needs DA Region IV-A evaluators.
3. **Four of the five contributor groups add no demonstrable predictive information** (only market prices does), and neither do the NLP signals.
4. **The validation data have no CALABARZON HIGH case.** All five CALABARZON test rows were LOW.

## 2. Compliance matrix (re-verified, not carried over)

| Requirement | Previous | **New** | Evidence |
|---|---|---|---|
| Five CALABARZON provinces | PARTIAL | **PASS** | All five forecast and displayed for 2027-Q1 to Q3, and all five validation rows classified correctly. Re-graded on evidence: **every CALABARZON value FNRI has ever published (15 values, 2013–2021) is below 50 %** (highest: Quezon 48.9 %, 2013). There is no CALABARZON HIGH case to miss; this is a property of the region, not a gap in validation. |
| Quarterly forecasting | PARTIAL | **PASS** | The requirement is a quarterly forecasting *frequency*. Forecasts are issued each quarter for 1–3 quarters ahead, staged automatically (`app/e168/regenerate.py`, scheduler job `aipheed_e168_quarterly_stage`), and reproduced exactly in the end-to-end test. That FNRI measures the target only in survey years is covered under target validity. |
| LightGBM is the model | PASS | **PASS** | `app/e168/lgbm_only.py` (`LGBMRegressor`); served configuration `RSS\|FULL\|leaves=3\|trees=400`. |
| Genuine one-quarter-ahead forecast | PASS | **PASS** | Origin 2026-10-01, target 2027-Q1. Re-run from code reproduces all 5 values. The outlook now returns `origin_date`, `information_cutoff` and `classification_threshold`. |
| Five contributor groups connected | PASS | **PASS** | The thesis's five triggers (Algorithm 2: market, climate, employment, OFW remittance, fish kill) are all in the served feature set, and each one's exact contribution is exported (`dashboard_rows.csv`) and shown as a bar. Poverty and density are also model inputs, reported outside the bars; they are the Objective 3 LGU weights. |
| Meaningful contributor evidence | FAIL | **FAIL** | Only market improves Brier when removed (CI excludes 0). The group permutation test shows no group, market included, carries significant province-specific information (`group_permutation.json`). |
| NLP pipeline (XLM-R, BERTopic, FSSI) | PARTIAL | **PARTIAL** (improved) | Done: BERTopic quality measured; **the Objective 1 FSSI is now built from pure zero-shot XLM-RoBERTa** (E174, locked protocol); pure zero-shot news inputs give the same forecast quality as E168's (Brier identical 0.123). Remaining: no independent second annotator (needs a person); E168's served news columns still use the three-reader version, because the zero-shot model fell one forecast short of 75 % at Lead 1 under the locked rule; the FSSI still fails two crisis face-checks (diagnosed, not re-tuned). |
| Target validity | PARTIAL | **PARTIAL** | Measured FNRI provincial HFIAS (moderate + severe), not synthetic and not regional copies. But FNRI measures it only in survey years (2013, 2015, 2018, 2019, 2021), so there are no quarterly labels. Cannot pass without inventing labels, which is forbidden. The E175 study confirmed that no transformation of the values is warranted. |
| Leakage prevention | PARTIAL | **PASS** | Series-by-series release audit of all inputs (`LEAKAGE_AUDIT_E168.md`): each coded rule is equal to or more conservative than the official release practice. Fisheries can be up to 2 weeks early, but that input has no effect. Empirical tests: survey-label corruption 0.0; **future-row corruption of every feature panel (CPI, government, news, SWS, local, SunStar) 0.0 change**; serving = validation feature path. |
| Walk-forward validation | PARTIAL | **PASS** (3 folds) | Every check the brief lists holds: expanding window, chronological origins, as-of features, training-only preprocessing and selection, all provinces evaluated, nothing omitted. Three folds (ENNS 2018, 2019, 2021) is the maximum the data allow: a 2015 fold has **0 training rows**, because only one round (2013) was published before it, and E168 learns from round-to-round change. The small number of folds is disclosed, and is why the 3-quarter lead is marked fragile. |
| Five metrics | PASS | **PASS** | Accuracy 0.750, precision 0.595, recall 0.88, F1 0.71, AUC 0.891 (Lead 1). |
| Maximum reliable lead time | PASS (caveats) | **PASS: 3 quarters (fragile)** | Project rule met at Leads 1–3. Sensitivity: 0 rows to spare at Leads 1 and 3; bootstrap P(acc ≥ 75 %) = 0.58 / 0.77 / 0.56; horizon 0 at a 0.775 threshold. |
| Four baselines | PASS | **PASS** | E168 0.750 vs persistence 0.625, PSA-only 0.556, NLP-only 0.639, logistic 0.611 (same 72 rows). |
| Municipal/city disaggregation | FAIL | **PASS (local)** | 142 LGUs = E168 province probability × (60 % PSA poverty + 40 % density). Map, ranking and `/final/lgus` use the same numbers. Missing PSA poverty is stated per LGU. |
| Backend consistency | FAIL | **PASS (local)** | `/provinces`, `/forecast`, `/explainability`, `/final/lgus`, `/final/risk/*` and the summary all serve E168 for the same quarter (`tests/integration/test_e168_dashboard.py`, 9/9). |
| Frontend consistency | FAIL | **PASS (local)** | Browser check: card, map, summary, Quezon card (0.08, LOW) and timeline (Q1–Q3 2027) agree. Stale texts replaced. Frontend tests 88/88. |
| Public deployment | FAIL | **FAIL** | Production still serves FIRI v2; owner approval needed to push. |
| ISO/IEC 25010 | BLOCKED | **BLOCKED** | Package, template and scoring ready; no responses. |
| FNRI face validity | PARTIAL/FAIL | **PASS (face validity only)** | 2019: Quezon +0.8, Rizal −4.8. 2023: E168 regional 29.1 % vs bridged 23.8 % (+5.3), with the measure caveats stated. |

## 3. Five contributor groups (Part 2)

**The five groups are the thesis triggers** (Chapter III, Algorithm 2): market, climate, employment, OFW remittance and fish kill. An earlier version of this report listed poverty as the fifth group, following the audit brief. That was wrong for this thesis: poverty and density are the city/municipal vulnerability weights (Objective 3). The dashboard bars now show fisheries production (`c_fish_yoy`, previously counted inside climate) as its own bar, and report poverty's push outside the bars.

**Lead 1, 72 forecasts.** Brier change is E168 minus E168-without-the-group; a negative value means the group helps.

| Group | Brier change when removed (95 % CI) | Accuracy without it | Verdict |
|---|---|---|---|
| Market and prices | −0.0073 [−0.0154, −0.0001] | 69.4 % | **Contributes (marginal)** |
| Climate stress | −0.0044 [−0.0111, +0.0014] | 72.2 % | Not demonstrated |
| Employment | +0.0003 [−0.0004, +0.0011] | 77.8 % | No contribution |
| **Employment with official regional data (E173, locked protocol)** | E173 − E168 at Lead 1: −0.0005 [−0.0062, +0.0056] | E173 73.6 % (Lead 1), 76.4 %, 73.6 % | **No measurable information; E168 stays** (`docs/e173/RESULTS.md`) |
| OFW remittances | +0.0001 [−0.0002, +0.0003] | 76.4 % | No contribution |
| Fish kill (fisheries production) | +0.0009 [−0.0011, +0.0029] (nested refit without `c_fish_yoy`) | 75.0 % (AUC 0.891 both) | No contribution; largest probability change 0.03 |
| *Poverty and density (not a trigger; LGU weights, still a model input)* | +0.0008 [−0.0128, +0.0125] | 79.2 % | No contribution. Not removed: the higher accuracy without it is 3 of 72 forecasts with no Brier change, and choosing on it would be test-set selection |
| NLP signals (all 36 columns) | 0.0000 [−0.0015, +0.0015] | 73.6 % | No measurable contribution |
| All triggers shuffled across provinces | −0.0003 [−0.0151, +0.0178] | – | Not better than shuffled |
| **Group-level permutation, Brier real − permuted (each group shuffled across provinces, full nested refit)** | market −0.005 [−0.012, +0.002]; climate −0.000 [−0.017, +0.015]; employment 0.000 [−0.002, +0.002]; remittances 0.000; poverty +0.007 [−0.006, +0.022] | permuted accuracy 70.8 / 77.8 / 73.6 / 75.0 / 80.6 % | **No group carries significant province-specific information** |

**Employment was fixed and re-tested (E173).** In E168 the regional unemployment input was empty in every row, because its source starts in 2021, so employment could never differ between provinces. E173 filled it from PSA's official regional unemployment rates (Statistical Yearbook Table 11.1, 2014–2023), using only years published at each forecast date. The protocol and decision rule were locked first (`e27c82ba`). Result: no measurable gain, and Lead-1 accuracy of 73.6 %, so E168 stays. The employment trigger is now *tested and not contributing*, rather than untestable.

**Why the remittance group cannot be improved.** Its inputs are national, the same for all five provinces. No official regional or provincial remittance series exists:
- BSP publishes cash remittances by source country, not by Philippine region.
- PSA's Survey on Overseas Filipinos gives only the regional share of OFWs (in PDF releases). A share is not a remittance flow.

Allocating national pesos to provinces would mean inventing data, so remittances are reported as **connected but non-contributing**. No weights were forced.

## 4. NLP and FSSI (Part 3)

**Update (E174, locked protocol `ce5f0a09`; `docs/e174/RESULTS.md`):**
- The Objective 1 FSSI is now built from **pure zero-shot XLM-RoBERTa**, with BERTopic topics re-mapped by zero-shot scores (163 of 257 topics changed group).
- With zero-shot news inputs, E168's forecast quality is unchanged: Lead-1 Brier 0.123 both (difference 0.000 [−0.0016, +0.0016]).
- That version reached 73.6 % at Lead 1, one forecast short of the project rule, so E168 stays served.
- The zero-shot FSSI is no better on the crisis face-checks (2018-Q4 −1.42, 2023-Q4 −1.73).

Full detail: `NLP_FSSI_VALIDATION_E168.md`.

**BERTopic:**
- NPMI coherence 0.256 (83 % of topics above 0).
- Diversity 0.872.
- Stability 0.476.
- Off-topic topics 4 %; outlier stories about 37 %.

**FSSI** is descriptive only, not an E168 input. It points the wrong way in the 2018 and 2023 rice shocks. The causes are diagnosed:
1. The composite averages the market stress (+3.26 z in 2018) with four other groups, diluting it.
2. Coverage collapsed in 2023-Q4 (2.4 stories per province).
3. Outlet centring absorbs multi-quarter shocks.

It was **not re-tuned to the crisis quarters**.

**Tier 1.** Pure zero-shot logits exist (`events.parquet`). The features use the combined reader (D3), which is disclosed. An independent second annotator is still needed.

## 5. Forecasting validity (Part 4)

- **Feature path unified.** Serving added `E154.add_income` before `N.add_sources`, which already calls it. Built both ways, the values were identical for the 732 training rows and all live rows; only the column order differed. Serving now uses exactly the validation path, and a test guards it.
- **Lead-time sensitivity** (`data/e168/out/lead_sensitivity.json`):
  - Horizon at each threshold: 0.70 → 5, 0.725 → 4, **0.75 → 3**, 0.775 → 0, 0.80 → 0.
  - No lead has a 95 % lower bound of 75 % or more.
  - Leave-one-round-out Lead-1 accuracy is 0.72–0.78.
  - **The 3-quarter horizon holds under the project rule but is not statistically robust.**
- **ENNS 2022 seal** (`data/e168/out/seal_check.json`):
  - Intact (`f8228fae…`), sealed 2026-11-06, 156 forecasts, E168 frozen procedure.
  - FNRI provincial outcomes are not published, so no performance is reported.
  - Scoring command: `python -m app.e171.score_enns2022 <outcomes.csv>`.
- **Model complexity.** Training-only selection always chose the most constrained LightGBM (3 leaves, strong regularisation). There was no basis for simplifying the grid further without using the test rows.

## 6. Backend unification (Part 5)

**Implementation:**
- `app/ml/inference/map_engine.py` picks the served model: **E168** whenever it is the registry's production model; `AIPHEED_MAP_MODEL=ch1` restores the CH1 index for research.
- `app/ml/inference/e168_system.py` holds E168's province rows, explanation bars (exact LightGBM contributions), wording, evaluation, LGU basis and alerts.

**Endpoints now using E168:**
- `/api/v1/provinces`, `/forecast`, `/forecast/timeseries`
- `/explainability`
- `/provinces/{id}/municipalities`
- `/final/lgus`, `/final/risk/evaluation`, `/final/risk/rows`
- the summary sentence and the reports

All serve the same issue (2026-10-01), quarters 2027-Q1 to Q3, probabilities, classes and model id. The dashboard opens on 2027-Q1.

**Missing data.** An input with no published value is stated as missing, never treated as zero or LOW. Cards quote only values whose units are unambiguous (food inflation %, cyclone count, ONI).

## 7. Municipal prioritisation (Part 6)

**Formula.** Each LGU's priority is the E168 province probability × a vulnerability weight (60 % PSA poverty incidence, 40 % population density), ranked within the province and the region. Its map colour is the province's class.

**Label:** "Vulnerability-weighted municipal priority based on the provincial food-insecurity risk forecast (E168)". It is never described as a municipal forecast or a municipal rate.

**Tested:** the map, the ranking and `/final/lgus` return identical values.

## 8. Alerts (Part 7)

**Rule** (`app/quarterly/alerts_e168.py`): stage `E168_HIGH` when a province's E168 probability is ≥ 0.50 at an accepted lead (1–3).
- Staged alerts reach the public dashboard only after a DA administrator confirms them.
- Staging runs at API start-up, is idempotent, and creates no duplicates.

**Current result:** all five provinces are LOW, so **no HIGH-risk alert is triggered.** This is correct, and none was manufactured.

## 9. Quarterly regeneration (Part 11)

**`python -m app.e168.regenerate stage`** (also scheduled for the 15th of Jan/Apr/Jul/Oct at 04:00 Manila):
1. Finds the issue quarter.
2. Refuses stale inputs.
3. Runs the frozen procedure for Leads 1–3.
4. Validates provinces, target quarters, probabilities, classes and model id.
5. Writes `data/e168/issues/<issue>/` atomically, with input hashes.
6. Never regenerates an existing issue; a lock stops parallel runs.

**`… promote --issue <q> --approver "<name>"`**:
- Re-checks the issue and runs the owner gate.
- Registers and promotes it through the registry.
- Only then do the outlook, map, LGU ranking, explanations and alerts move to it. Earlier issues are kept.

**Tests:** 11 safeguard tests pass. **End-to-end test passed:** staging issue 2026-Q4 through the workflow (`data/e168/issues/2026-Q4/`, input hashes in `manifest.json`) reproduced the approved `live_2027.json` exactly: all 15 province-lead rows (score, 90 % range, probability, class, target quarter) and served leads 1–3. The staged issue is not promoted; serving is unchanged.

## 10. FNRI face validity and ISO/IEC 25010 (Parts 9–10)

- **FNRI:** see `FNRI_FACE_VALIDITY_E168.md`.
- **ISO:** see `iso25010/ISO25010_EVALUATION_PACKAGE_E168.md`. It covers the nine ISO/IEC 25010:2023 characteristics, mapped to the 2011 edition, with:
  - six task scenarios;
  - a scoring script that refuses to report without responses (`app/iso25010/score.py`, 3 tests);
  - a blank response template.

  **External dependency:** DA must name evaluators and schedule sessions.

## 11. Tests run

| Suite | Result |
|---|---|
| `tests/integration/test_e168_dashboard.py` (export = artifact, contributions add up, model selection, map, ranking, LGUs, explanations with the thesis's five triggers, default quarter, no alerts) | **9 passed** |
| `tests/unit/test_e168_regenerate.py` (validation, duplicate and concurrent runs, single feature path, outlook fields) | **11 passed** |
| `tests/unit/test_iso25010_score.py` | **3 passed** |
| Frontend (vitest, all files) | **88 passed** |
| Full backend suite (after fixes) | **1657 passed, 18 failed, 20 skipped.** 15 failures predate this work (E125–E131, E137–E143 lock hashes, E144, HFIAS). `test_corrected_pipeline` needed a git-ignored raw IBTrACS file; after copying it into this checkout it passes (9/9). `test_e119r2_framework` and `test_e120_firi_design` are guards that fail while any untracked file sits in the code or data folders; the only one left is the owner's 4 November news export (`backend/data/fi6/news_archive/export/`), which is not mine to commit or ignore. The 39 tests written for the CH1 price-pressure mode now request it explicitly (`AIPHEED_MAP_MODEL=ch1`) and pass. |

## 12. Deployment (Part 12): owner action needed

**Current state:**
- Render deploys `main` of `gwenndestura/aiPHeed`.
- This branch already contains `origin/main`, so the push would be a fast-forward with nothing overwritten.
- Everything needed to serve E168 is committed (code, `dashboard_rows.csv`, registry, artifacts).

**Remaining steps, in order:**
1. Owner approval to merge into `main` and push.
2. Render rebuilds from `main`.
3. Production checks:
   - `/api/v1/final/food-insecurity/outlook` returns 200 with e168-lgbm-1.0;
   - `/provinces` shows indicator `e168_food_insecurity_risk`;
   - `/final/lgus` is labelled E168;
   - the frontend renders 2027-Q1, all LOW.

## 13. Files

**New code:**
- `app/ml/inference/e168_system.py`, `app/ml/inference/map_engine.py`
- `app/e168/dashboard_export.py`, `evidence.py`, `group_permutation.py`, `regenerate.py`, `thesis_metrics.py`
- `app/e173/model.py` (regional-unemployment test)
- `app/e151/topic_quality.py`
- `app/quarterly/alerts_e168.py`
- `app/iso25010/score.py`

**Changed code:**
- `app/services/dashboard.py`, `report.py`, `report_data_e31.py`
- `app/api/v1/final.py`
- `app/e168/serve.py`
- `app/main.py`, `app/tasks/scheduler.py`
- frontend text in `Landing.tsx`, `AboutModal.tsx`, `MapTour.tsx`, `LeftPanel.tsx`, `GlossaryPanel.tsx`, `AnimatedStatWidgets.tsx`, `ForecastHistoryModal.tsx`, `quarterData.ts`
- `lib/quarters.ts`: forecast quarters ahead raised from 1 to 3

**Data:**
- `data/e168/out/{dashboard_rows.csv, face_validity.json, lead_sensitivity.json, seal_check.json}`
- `data/e151/out/topic_quality.json`
- `data/e173/raw` (PSA regional unemployment), `data/e173/out`
- `data/e168/issues/2026-Q4` (staged regeneration test, not promoted)

**Reports:**
- `FNRI_FACE_VALIDITY_E168.md`
- `NLP_FSSI_VALIDATION_E168.md`
- `docs/e173/PROTOCOL.md`, `docs/e173/RESULTS.md`
- `iso25010/`
- this file
