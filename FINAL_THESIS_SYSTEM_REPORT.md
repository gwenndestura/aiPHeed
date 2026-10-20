# aiPHeed: final thesis system report

**Date:** 2026-10-20
**Branch:** `final-thesis-system`, from `e69-food-insecurity-risk-framework` @ `feb9d4d` (the E69 head, verified equal to origin). The pushed commit SHA is recorded in §12 and in `aipheed-backend-aligned/experiments/FINAL_Thesis_System/out/commit_record.txt`.
**Thesis-demo configuration:** `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1` (`backend/config/thesis_demo.env`).
**Requirement basis:** Chapter I §1.5.2 and §1.7, verbatim from `THESIS 2 (11).pdf` (sha256 `88dd0b62…`; extract in `aipheed-backend-aligned/experiments/E25_Reliable_Forecasts_2021_2026/thesis_source/CHAPTER_I_verbatim.txt`).

---

## 1. What can be claimed, and what cannot

**Can be claimed (measured, reproducible):**

- **Working system.** aiPHeed is a complete, working geospatial system for CALABARZON:
  - Filipino-English news pipeline: XLM-RoBERTa food-stress intensity, FSSI-v3, BERTopic topics;
  - LightGBM Lead-2 forecasting with expanding-window walk-forward evaluation at leads 1–3;
  - comparison with the four Chapter I baselines;
  - provincial food-insecurity risk outlook;
  - priority rankings for all 142 cities and municipalities;
  - PDF reports;
  - a dashboard whose map, panels, rankings and API values agree.
- **Lead-2 metrics on development back-tests** (50 province-quarters, 10 quarters): accuracy 0.72, precision 0.63, recall 0.56, F1 0.59, AUC-ROC 0.65.
- **Against the Chapter I baselines,** LightGBM has a lower Brier score than all four on the same 45 rows. The advantage is statistically established (paired CI and quarter sign test) only against the PSA-only and the combined logistic regressions.
- **Province-level skill.** The LightGBM separates provinces within a quarter (within-quarter AUC 0.71), so it carries provincial information beyond the shared regional trend.
- **Honest risk statements.** The system states every forecast's issue date, target quarter, data status and limitations, and never reads a LOW price score as low food-insecurity risk.

**Cannot be claimed:**

- **Not a validated food-insecurity forecast.** The LightGBM's label (T43) equals provincial food-price pressure on every evaluated row, and no provincial food-insecurity outcome exists to test against.
- **No reliable horizon.** No lead meets the pre-registered reliability criterion, so the "furthest reliable horizon" of Objective 2 V is **"none established"**.
- **The > 75% Lead-2 accuracy goal is not demonstrated:**
  - 0.72 on 50 rows;
  - 0.78 on the 45 Objective 4 rows, not distinguishable from always predicting LOW at the quarter level;
  - every scored row was examined during development; no unseen quarter has been scored.
- **Not a provincial probability or validated classification.** The risk outlook (ELEVATED / WATCH / NO ELEVATED SIGNAL) is a transparent evidence summary.
- **Not municipal forecasts.** The LGU rankings are relative prioritizations, not municipal forecasts.
- **No measured effect for news and climate.** News sentiment, BERTopic topics and El Niño information have no measured effect on forecast accuracy.

---

## 2. Final acceptance matrix: Objectives 1–4 (exact Chapter I wording)

| Obj | Approved objective (verbatim) | Required outcome | Implemented components | Tests / reproducible evidence | Measured results | Known limitations | Status |
|---|---|---|---|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | FSSI and latent patterns per province-quarter, used by the system | `backend/app/news/pipeline_v3.py` (corpus 9,667 titles from 2021-01-01 to 2026-10-14; classifier v2; province attribution; syndication de-duplication; publication-date cutoff at each issue date; XLM-RoBERTa intensities in `data/news_v3/scores.jsonl`); `fssi_v3()` (bias weight log(1 + median n) / log(1 + n)); BERTopic outputs in `data/news_v3/` (152 topics, 120 province-quarter rows). The thesis mode serves the v3 news feed, FSSI-v3 and the top topics per province (`summary.newsEvidence`, the news panel, the PDF). | `tests/integration/test_thesis_system.py::test_news_evidence_from_the_objective1_pipeline` (served values equal `pipeline_v3`); `test_e64_news_pipeline.py` | 695 admitted articles. FSSI-v3 for 2026-Q3: Cavite 0.40 (n 10), Laguna 0.28 (12), Rizal 0.28 (13), Batangas 0.19 (13); Quezon 1 article, so withheld. Classifier v2 precision 0.92 / recall 0.75 on **AI-annotated** titles. | Titles only; collected retrospectively; annotation not human-validated. The bias correction is **not validated** and inflates single-article provinces (Quezon raw 3.12 from n = 1), hence the SUFFICIENT-only display. BERTopic topics are mostly geographic; 39.7% outliers. News adds no measured forecasting gain. | **Implemented but not validated** |
| 2 I–IV | "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC" | The four metric families for the proposed LightGBM | E56-TUNED LightGBM, expanding-window walk-forward with issue-date cutoffs; `final_evaluation.py` computes from sealed predictions; served by `/api/v1/config` `modelPerformance` and the PDF | `test_final_evaluation_reproduces_sealed_predictions` (reproduces E63 to 1e-5; confusion TP 10 / FP 6 / FN 8 / TN 26 at Lead 2) | Lead 2: Acc 0.72, Prec 0.63, Rec 0.56, F1 0.59, AUC 0.65, Brier 0.214 (§6) | Development evidence; target is price pressure | **Implemented; metrics reported; performance not validated** |
| 2 V | "Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | Multi-lead evaluation and a furthest reliable lead under a stated criterion | Leads 1–3 (lead 4 not computable under the CPI cutoff); criterion pre-registered 2026-10-19 (E63 §8, sha `5b3ee7e9`) and adopted unchanged | same test; `furthestReliableLead = None` | No lead qualifies. Lead 1 is closest: Brier beats persistence and climatology on the CI, but only 9 of 12 quarter wins | 9–12 quarters per lead | **Implemented; outcome: no reliable horizon established** |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | 142 LGU rankings from province forecasts with poverty and density weights | Approved 0.6 poverty (PSA SAE 2021) + 0.4 density (POPCEN 2024) weighting × province score, exact ranks; every LGU labelled "relative prioritization, not a municipal forecast"; province risk outlook beside it | `test_142_lgus_finite_mapped_and_coloured`; browser: all 142 dashboard values equal the API (§11) | 142 unique LGUs, finite, mapped (34/23/30/41/14), coloured, 0 ties | Province forecasts are **not validated** (the objective's premise). Inside a province the order is the vulnerability order. Lucena's poverty value is a substitute. | **Implemented; premise ("validated province-level forecasts") unmet → partially met** |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | A fair comparison on the same rows, issue dates and target | 45 identical rows (targets 2024-Q3..2026-Q3), the same T43 labels and issue dates, plus the majority class; paired Brier tests and McNemar | `test_final_evaluation_reproduces_sealed_predictions` | Brier: LightGBM 0.178 vs 0.400 (I), 0.598 (II), 0.235 (III), 0.646 (IV), 0.311 (majority); established only vs II and IV (§7) | Development rows only; accuracy not above majority at the quarter level | **Implemented; partial superiority on examined rows; not validated on unseen quarters** |

**Discrepancy recorded, not changed:** the run brief names DEPDev IV-A among the users. Chapter I §1.7 names "50 DA Region IV-A evaluators" only, and the user removed DEPDev on 2026-10-10.

---

## 3. Final scientific decisions

### 3.1 Concepts kept separate

| Concept | What aiPHeed uses | Output |
|---|---|---|
| Observed food insecurity | SWS involuntary hunger, Balance Luzon (region), quarterly, n 300–600, margin of error ±4–6 pts | Regional hunger outlook |
| Food affordability stress | PSA provincial food and headline CPI; the LightGBM T43 score | Exploratory food-price-pressure score (map colour, province score, LGU index) |
| Hazards and exposure | PAGASA El Niño advisories (dated); provincial palay/corn production; typhoons; fisheries production; national employment and remittances | Components of the risk outlook; data-status list |
| Vulnerability | PSA poverty 2021 (SAE), subsistence 2021/2023, population density | LGU weights; vulnerability profile (with CVs) |
| News evidence | Pipeline v3, FSSI-v3, BERTopic | Warning signal, never proof |

### 3.2 Selected target and methodology

- **Score.** E56-TUNED LightGBM, Lead-2, label T43, kept as the Chapter I "proposed LightGBM". It is named for what it measures: an *exploratory food-price-pressure score*.
- **Risk outlook** (E69, computed at runtime from the served record):

  | Tier | Condition |
  |---|---|
  | ELEVATED | regional hunger expected above 11.3% AND (price-pressure score ≥ 0.5 OR headline inflation above the province's usual 2021–22 level OR (PAGASA El Niño advisory in force AND local palay/corn production down ≥ 10%)) |
  | WATCH | hunger expected high AND an El Niño advisory only |
  | NO ELEVATED SIGNAL | otherwise |

- **Regional hunger outlook.** The latest approved SWS round posted before the issue date, with an interval from its own past Lead-2 errors. No tested method was better (E69: MAE 3.9 points over 18 quarters).
- **Reliability criterion.** E63 §8 (pre-registered): paired Brier better than persistence AND climatology, each with a quarter-cluster 95% CI below 0 and a two-sided quarter sign test p < 0.05.

### 3.3 Alternatives considered and why they were rejected

| Alternative | Evidence | Reason rejected |
|---|---|---|
| Replace T43 with a combined outcome-and-driver label | — | Circular: it would validate drivers against themselves |
| Affordability target T-AFF (E68) | LightGBM = always-LOW (HIGH recall 0) | Not forecastable |
| Province-only inputs, no national employment/OFW (E68 N1) | Brier −0.022, CI below 0, but Holm sign p 0.22 | Not better by the frozen rule; would change the frozen forecast |
| El Niño projection shift (E68 K1) | 2023–24 errors were negative (disinflation) | Encodes no El Niño effect |
| News-only, news-augmented, climate-aware and stable-configuration variants (E60–E66) | none better by the rule | No gain |
| Logistic regressions (E66 N1/N2; Chapter I baselines II and IV) | worse or unstable | Worse |
| Deep learning | ~23 effective observations | Not identifiable |
| Colouring the map by the outlook tier | the approved map colours a numeric score | Would turn an unvalidated tier into a fake probability. The tier is stated first in every panel and PDF instead. |
| Forcing El Niño provinces to HIGH | — | Not done. El Niño enters only through the documented outlook rule. |

---

## 4. Thesis-demo system: startup and configuration

From a fresh checkout of `final-thesis-system`. On Windows, clone with long paths enabled: one old experiment
snapshot path exceeds 260 characters, and a plain clone fails with "Filename too long".

```
git -c core.longpaths=true clone https://github.com/gwenndestura/aiPHeed.git
cd aiPHeed
git config core.longpaths true
git checkout final-thesis-system
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
cd ..\frontend
npm install
cd ..\backend
venv\Scripts\python.exe scripts\start_thesis_demo.py
```

This starts the API on http://localhost:8000 and the dashboard on http://localhost:8080. It runs with `AIPHEED_LEAD2_MODEL=thesis` and `AIPHEED_STRICT_MODEL=1`, migrates a scratch SQLite database if `DATABASE_URL` is unset, and generates a random `SECRET_KEY` if unset.

**Options and checks:**
- `--api-only`, `--api-port`, `--ui-port` adjust the startup.
- `GET /api/v1/config` → `servingModel` reports the mode, model, issue date, target quarter and lead.

**Exact settings:**

| Setting | Value |
|---|---|
| Mode | `AIPHEED_LEAD2_MODEL=thesis` |
| Strict start | `AIPHEED_STRICT_MODEL=1`: refuses to start unless the mode is `thesis` and every required artifact exists and passes its integrity check (`thesis_system.validate`); no silent fallback |
| Score record | `backend/data/e58/e58_record.json` (E56-TUNED, configuration 23 at the 2026-10-01 issue, Lead-2, target 2027-Q1; integrity hash checked) |
| Model artifacts | `backend/data/e56/model/` |
| Evaluation | `backend/data/thesis/final_evaluation.json` (from `aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/final_evaluation.py`) |
| Hunger | `backend/data/inputs/sws_rounds.csv` (approved rounds, posted before issue) |
| News | `backend/data/news_e31`, `news_e60`, `news_v3` (classifier v2 sha `327f9431…`) |
| LGU | `backend/data/inputs/lgu_vulnerability.csv` |
| Climate | `app/ml/inference/enso_context.py` (PAGASA items with dates) |

**Rollback:** remove the two variables (or set `AIPHEED_LEAD2_MODEL=e38`) and restart. The E38 production default is unchanged and untouched by this branch.

**Target quarter.** The target follows the Asia/Manila clock (`app/quarterly/target.py`): 2027-Q1 until 2026-12-31. From 2027-01-01 the target becomes 2027-Q2. The frozen record is then **not** served for it: the dashboard says no estimate exists, and `servingModel.servesTargetNow = false`.

**Next quarter.** Refresh the data, then run:

```
venv\Scripts\python.exe -B scripts\build_record_e56.py
venv\Scripts\python.exe -B scripts\build_record_e58.py
```

The thesis outlook, input status and news evidence are computed at runtime from the new record.

---

## 5. Objective 1 findings (NLP)

| Item | Finding |
|---|---|
| Corpus | 9,667 Google News titles, 2021-01-01..2026-10-14, Filipino and English. Collected retrospectively: 2,118 of 2,132 E60 articles were first seen after their issue date. |
| Relevance | Classifier v2: precision 0.92 / recall 0.75 against **AI annotations** (no human-validated set) |
| Attribution and timing | Province from title geocoding; quarter from the Philippine publication date; only articles published before the issue date are used (`pipeline_v3.asof`) |
| De-duplication | Article key plus syndication merge (3 days) |
| FSSI-v3 | Mean XLM-RoBERTa intensity × bias weight log(1 + median n) / log(1 + n). The weight is from the approved Equation 2, **not validated**; with n = 1 it multiplies by up to 3.7, so FSSI is served only with ≥ 5 articles (SUFFICIENT). Missing evidence gives no FSSI, never 0. |
| BERTopic | 152 topics, 39.7% outliers, titles only, mostly geographic themes. Served as the top 3 topics of the province-quarter; descriptive. |
| Forecast value | No measured gain: news-only Brier 0.445–0.507; adding news to LightGBM changes Brier by ≤ 0.01 (E60/E64/E66–E68) |

---

## 6. Objective 2: lead-time table (sealed E63 walk-forward predictions; `FINAL_Thesis_System/out/lead_time_table.csv`)

| Lead | Rows / quarters | Model | Acc | Prec | Rec | F1 | AUC | Brier | TP / FP / FN / TN |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 60 / 12 | **LightGBM** | 0.850 | 0.833 | 0.714 | 0.769 | 0.901 | 0.130 | 15 / 3 / 6 / 36 |
| 1 | | Persistence | 0.683 | 0.550 | 0.524 | 0.537 | 0.647 | 0.317 | 11 / 9 / 10 / 30 |
| 1 | | Majority (LOW) | 0.650 | — | 0 | 0 | 0.500 | 0.350 | 0 / 0 / 21 / 39 |
| 1 | | Climatology | 0.650 | — | 0 | 0 | 0.344 | 0.284 | 0 / 0 / 21 / 39 |
| 2 | 50 / 10 | **LightGBM** | 0.720 | 0.625 | 0.556 | 0.588 | 0.649 | 0.214 | 10 / 6 / 8 / 26 |
| 2 | | Persistence | 0.560 | 0.400 | 0.444 | 0.421 | 0.535 | 0.440 | 8 / 12 / 10 / 20 |
| 2 | | Majority (LOW) | 0.640 | — | 0 | 0 | 0.500 | 0.360 | 0 / 0 / 18 / 32 |
| 2 | | Climatology | 0.640 | — | 0 | 0 | 0.214 | 0.304 | 0 / 0 / 18 / 32 |
| 3 | 45 / 9 | **LightGBM** | 0.622 | 0.400 | 0.429 | 0.414 | 0.620 | 0.251 | 6 / 9 / 8 / 22 |
| 3 | | Persistence | 0.511 | 0.300 | 0.429 | 0.353 | 0.488 | 0.489 | 6 / 14 / 8 / 17 |
| 3 | | Majority (LOW) | 0.689 | — | 0 | 0 | 0.500 | 0.311 | 0 / 0 / 14 / 31 |
| 4 | — | not computable: the year-earlier CPI base month falls after the issue-date cutoff | | | | | | | |

**Reliability rule** (Brier difference LightGBM − baseline, quarter-cluster 95% CI, quarter wins / losses, two-sided sign p):

| Lead | vs persistence | vs climatology | Reliable? |
|---|---|---|---|
| 1 | −0.187 [−0.287, −0.083], 9/3, p 0.146 | −0.155 [−0.260, −0.056], 9/3, p 0.146 | no (sign test) |
| 2 | −0.226 [−0.388, −0.055], 7/3, p 0.344 | −0.090 [−0.192, +0.0001], 5/5, p 1.0 | no |
| 3 | −0.237 [−0.410, −0.065], 7/2, p 0.180 | −0.015 [−0.112, +0.083], 6/3, p 0.508 | no |

- **Furthest reliable lead:** none.
- **The > 75% Lead-2 goal:** not demonstrated.
- The early-warning reading of the same model (price part ≥ 0.5) reaches 0.78 at Lead 2. That rule was defined after inspecting these rows, so it is reported, not claimed.

---

## 7. Objective 4: baseline comparison (45 identical rows, targets 2024-Q3..2026-Q3, T43, the same issue dates; `FINAL_Thesis_System/out/baseline_table.csv`)

| Model | Acc | Prec | Rec HIGH | Rec LOW | F1 | AUC | Brier | Δ Brier (LightGBM − baseline) [95% CI] | Quarter wins / losses (sign p) | Brier advantage established? | McNemar (LightGBM right only / baseline right only, p) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **LightGBM E56-TUNED** | 0.778 | 0.625 | 0.714 | 0.806 | 0.667 | 0.763 | 0.178 | — | — | — | — |
| I. Naive persistence | 0.600 | 0.400 | 0.571 | 0.613 | 0.471 | 0.592 | 0.400 | −0.222 [−0.409, −0.037] | 6/3 (0.254) | **no** | 13/5, p 0.096 |
| II. PSA-only indicator (LR) | 0.378 | 0.150 | 0.214 | 0.452 | 0.176 | 0.295 | 0.598 | −0.420 [−0.656, −0.199] | 8/1 (0.020) | **yes** | 23/5, p 0.001 |
| III. NLP-only sentiment (LR) | 0.667 | 0.400 | 0.143 | 0.903 | 0.211 | 0.488 | 0.235 | −0.057 [−0.122, +0.008] | 7/2 (0.090) | **no** | 12/7, p 0.359 |
| IV. Logistic regression (combined) | 0.333 | 0.136 | 0.214 | 0.387 | 0.167 | 0.247 | 0.646 | −0.467 [−0.670, −0.276] | 9/0 (0.002) | **yes** | 25/5, p < 0.001 |
| Majority class (always LOW) | 0.689 | — | 0 | 1 | 0 | 0.500 | 0.311 | −0.133 [−0.304, +0.021] | 6/3 (0.254) | **no** | 10/6, p 0.454 |

**Generalization.** Every row was examined during development, so no advantage is shown to generalize to unseen quarters. The sealed 2026-Q4 and 2027-Q1 forecasts (E68 `sealed/prospective.csv`, E69 `sealed/outlook_forward.csv`) are the first independent test.

---

## 8. Climate, affordability, hunger and vulnerability findings

**El Niño causal chain at the 2026-10-01 issue:**

| Link | Status | Evidence |
|---|---|---|
| Official status | Measurable | PAGASA Climate Advisory (2026-09-23) in force; Advisory No. 5 issued later, on 2026-10-07 |
| Rainfall and drought | Not measurable | No dated 2021–2026 archive |
| Production | Partly measurable | Provincial palay/corn YoY for 2026-Q2: drops ≥ 10% in Cavite, Laguna and Batangas |
| Prices | Measurable | Projected food inflation for 2027-Q1 is 0.8–2.1%, below every HIGH line. The single in-window El Niño (2023–24) came with falling inflation, so no El Niño price effect can be estimated. |
| Hunger | Regional only | Latest 17.3%, P(> 11.3%) = 0.88 |

**Affordability.** At issue, headline inflation was above the usual 2021–22 level in Laguna (6.9 vs 4.7), Quezon (6.1 vs 5.1) and Rizal (6.6 vs 6.1). The T43 gap rule counts this as *less* food-price pressure; the outlook counts it as an affordability hazard.

**Outlook for 2027-Q1:** ELEVATED in all five provinces.
- **Cavite and Batangas:** hunger plus El Niño advisory plus crop drop.
- **Laguna, Quezon and Rizal:** hunger plus affordability (Laguna also has a crop drop).

**Hunger.**
- Two quarters ahead, no method beat the latest reading: MAE 3.9 points against a survey-noise floor of 1.8.
- "Above 11.3%" was right in 12/18 quarters, below always-above (13/18).
- None of the 4 sharp rises was foreseen.

**Vulnerability.**
- PSA subsistence incidence for 2021 and 2023 has CVs of 17–62%, so it cannot rank provinces. It is shown as context.
- Poverty 2021 (LGU mean): Quezon 20.3%, Cavite 11.1%, Batangas 8.6%, Laguna 7.9%, Rizal 6.9%.

**Trigger groups:**

| Group | Status |
|---|---|
| Market / prices | carries the skill |
| Climate | observed only |
| Fisheries | production (no fish-kill event series) |
| Employment and OFW | national figures; remittances missing for 2026 |

Removing any single group changes Lead-2 Brier by ≤ 0.012 (n.s.).

---

## 9. Data limitations that affect the thesis conclusions

1. **No provincial or municipal food-insecurity outcome** (CBMS, provincial FIES, caseloads). Provincial food-insecurity accuracy cannot be established.
2. **SWS hunger is regional,** with ±4–6 point sampling error. Quarter-to-quarter movement is mostly noise.
3. **Only 10–12 independent quarters per lead;** about 23 effective observations at Lead 2.
4. **All development rows have been examined.** The independent test (sealed 2026-Q4 / 2027-Q1) awaits PSA CPI for Oct 2026–Mar 2027 and the SWS 2026-Q4 and 2027-Q1 rounds.
5. **One El Niño episode in 2021–2026,** confounded with disinflation; no dated rainfall or drought archive.
6. **News:** titles only, collected retrospectively, AI-annotated evaluation, thin per province.
7. **BSP remittances end 2025-Q4;** employment and remittances are national only.
8. **Lucena's poverty value** is an unverified substitute (it ranks 1st or 22nd of 41 depending on the value).
9. **The pre-2021 exclusion** (user rule) limits label thresholds to the 2021–22 window.

---

## 10. Integration work completed in this run

| Area | Change |
|---|---|
| Thesis mode | `backend/app/ml/inference/thesis_system.py`: runtime regional hunger outlook (equal to sealed E69), runtime risk outlook (equal to sealed E69 tiers), runtime input-status classification, news evidence (FSSI-v3 + BERTopic), final evaluation |
| Serving registry | `e41_lead2` registers `thesis`. Dashboard, insights, news feed (pipeline v3), `/config` (`servingModel`, `modelPerformance`), PDF reports (outlook block, honest score label, Objective 2/4 tables) and report data. |
| Strict start | `app/main.py` `strict_model_check()` |
| Startup | `backend/config/thesis_demo.env`, `backend/scripts/start_thesis_demo.py` |
| Final evaluation | `aipheed-backend-aligned/experiments/FINAL_Thesis_System/runner/final_evaluation.py` produces `backend/data/thesis/final_evaluation.json` |
| Frontend bug (pre-existing, also in the approved tag) | double-clicking "← Back to CALABARZON" passed `null` to the region handler and blanked the whole dashboard (`PhilippineMap.tsx`, `MapDashboard.tsx`; null guard; no visual change) |
| Fixed during the run | the `model_performance` cache now has no mode leakage; the PDF method block crashed on the new performance shape |

**Approved design unchanged:** no colours, legends or layout elements changed; all new explanations use the existing text fields.

---

## 11. Tests, build and browser results (2026-10-20)

| Check | Result |
|---|---|
| Backend full suite (`pytest -q tests`) | **518 passed, 18 skipped, 0 failed** (`FINAL_Thesis_System/out/backend_full_suite.txt`); includes 13 new thesis-system tests |
| Backend, committed tree only (another session's uncommitted E46 D-1 hunks swapped out, then restored byte-identical) | **509 passed, 18 skipped, 0 failed** (`FINAL_Thesis_System/out/backend_committed_tree_suite.txt`) |
| Fresh checkout (`git -c core.longpaths=true clone` of commit e5af602, committed files only) | full suite **509 passed, 18 skipped, 0 failed**; the startup script starts in strict thesis mode and serves the 2027-Q1 outlook; wrong mode with strict exits with code 3 (`FINAL_Thesis_System/out/fresh_checkout_check.txt`). A clone without long paths fails on Windows: documented in §4. |
| Frontend vitest | 46/46 |
| Production build (`vite build`) | passed |
| `tsc --noEmit` | 6 errors, **pre-existing**, all in `src/data/mockData.ts`; the mock data is not rendered in the dashboard |
| Browser end-to-end | real startup script, real clock, strict mode, desktop 1280×860 (details below) |
| Pre-existing console errors | "Wrong magic number for PMTiles archive" (basemap tiles only) |

**Browser end-to-end details:**
- `/config` reports `mode: thesis`, `strict: true`, target 2027-Q1, issued 2026-10-01.
- The regional panel starts with "FOOD-INSECURITY RISK OUTLOOK, 2027-Q1: ELEVATED in Cavite, Laguna, Quezon, Rizal, Batangas".
- All five province panels show their outlook first. Every LGU in the panel equals the API value to 2 dp:

  | Province | LGUs matched |
  |---|---|
  | Cavite | 23/23 |
  | Laguna | 30/30 |
  | Rizal | 14/14 |
  | Quezon | 41/41 |
  | Batangas | 34/34 |
  | **Total** | **142/142** |

- Every LGU polygon has the approved colour.
- The archive quarter Q4 2026 shows its sealed outlook, and its news is limited to before its issue date.
- Data and Visualization pages load.
- PDF reports render (province and region).
- The double-click crash was reproduced, fixed, and re-tested.

---

## 12. Branch and commit

**Push record:** `aipheed-backend-aligned/experiments/FINAL_Thesis_System/out/commit_record.txt`, written after the push.

**Not done (no authorization):**
- merge;
- public deployment;
- change of the production default.

The branch is a tested, reproducible thesis-demo configuration, **not** a live deployment.

**Preview deployment, if authorized later:**
- set `AIPHEED_LEAD2_MODEL=thesis` and `AIPHEED_STRICT_MODEL=1` on the API service;
- point the frontend's `VITE_API_BASE_URL` at it.
