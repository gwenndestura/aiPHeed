# Objectives audit: did aiPHeed meet what THESIS 2 (14) promised?

Read-only audit, 2026-10-17. Source text: `THESIS 2 (14).pdf` (Downloads), extracted with `pdftotext -layout`; page
numbers are the printed page numbers (they equal the PDF page index). Evidence: the served records
(`backend/data/e49/e49_record.json`, default; `backend/data/e53/e53_record.json`, preview), experiments E25-E58,
the backend code and database, and the running API (`AIPHEED_RECORD=e53`, `AIPHEED_MAX_LEAD=2`). Nothing was changed.

Verdicts: **MET** / **PARTIALLY MET** / **NOT MET** / **NOT EVIDENCED IN REPO**. For hypotheses, the result is stated
as "null rejected" or "null not rejected", with the test used.

All model numbers below are **development evidence**: a nested walk-forward over 65 province-quarters (13 target
quarters, 2023-Q1..2026-Q3, lead 1) whose outcomes were seen during model development. The first untouched test
is the frozen 2026-Q4 forecast (`validation.prospective_2026Q4`: "awaiting the SWS December 2026 round").

---

## 0. Re-grade after the completion work (2026-10-17, later the same day)

The code-side gaps found below were then worked on, in the backend and experiments only. No served model, record
probability, calibration, frontend or protected file changed. New evidence:

| Item | Before | Now | New evidence |
|---|---|---|---|
| RQ2 / SO2-V / Algorithm 3 | PARTIALLY MET (k = 1, 2 only) | **MET** (answered: **1 quarter**) | E59 (`experiments/e59/E59_results.md`): served E49 family scanned at k = 1..8 under a protocol written first. k = 1: 0.846 (CI 0.769-0.923), passes. k = 2: 0.709, halts. Maximum Reliable Lead Time = 1 quarter by both the point rule and the CI rule. k = 7-8 are not evaluable (3 and 1 dates), and reported as such. |
| H2 | null not rejected | **null not rejected** (confirmed over k = 1..8) | Only k = 1 is reliable. The k = 3-6 accuracies (0.73-0.96) come with balanced accuracy <= 0.5: they are not skill. |
| SO1 (BERTopic) | PARTIALLY MET (descriptive code, no output) | **PARTIALLY MET** (run; failed its stability gate) | `data/news_e31/topics/manifest.json`: 55 relevant articles gave 2 topics, 40% outliers, seed-stability ARI 0.31 / 0.45 (mean 0.38 < 0.5). Status UNSTABLE, so no proportions were published (gate fixed before the run). Exposed read-only at `/api/v1/insights/topics` and in a PDF section, both stating the numbers. |
| SO5 (NNS face validity) | NOT EVIDENCED | **PARTIALLY MET** (2023 only) | `experiments/e59/nns_face_validity.md`, using the verified DOST-FNRI figures in `data/e22/nns_fies_verified.json`. NNS 2023 CALABARZON FIES is 19.1% (lowest region; Philippines 31.4%), and the model's lowest year is 2023 (mean 0.469; 9/20 observed LOW). Consistent. 2019 and 2021 regional figures were not found; the exact list to provide is in that file. |
| Rule 7 (alert threshold) | PARTIALLY MET (fixed rules) | **MET** (in code) | `app/quarterly/alerts_e31.py` `ROLLING_THRESHOLD`: the province estimate > the 75th percentile of its own previous published estimates (trailing, at least 4). It stays STAGED until a DA admin confirms it, and the definition is in `reason_text` (also returned by the alerts API). 2026-Q4: E49 flags Quezon (0.914 > 0.886); E53 flags Cavite, Laguna, Rizal and Quezon; Batangas does not fire. |
| Deviation 16 (E49 verdict text) | wrong stored sentence | **fixed at serving time** | `app/quarterly/verdicts.py` composes the sentence from the stored numbers. E49 is served as "demonstrated (0.769 to 0.923)", E53 as "not demonstrated (0.646 to 0.908)". Both builders use the composer. The record file itself is unchanged (protected). |
| Tests | – | 402 passed, 18 skipped (backend, `ENABLE_API_DOCS=false`); frontend 35/35 | `tests/integration/test_objectives_completion.py` (13 tests) |

Unchanged verdicts: H1 (partly rejected, descriptive), H3 (null not rejected), SO2 I-IV (MET), SO3 (MET as a mechanism),
SO4 (MET, negative), the 75% target (E49 demonstrated, E53 not), F1/AUC (development data, no blind holdout).

**Still requires the researchers (cannot be done in code):**
1. **Evaluator survey (RQ4/H4, RQ5/H5, ISO/IEC 25010).** At least 30 valid DA Region IV-A responses to the prepared
   questionnaire (`E25.../instruments/`), analysed with the pre-declared rules. Nothing can be simulated.
2. **Deployment.** A public or DA-accessible host, and DA administrator accounts (`admin_users` = 0).
3. **DA review cycle.** Reviewers to approve or reject forecasts (`review_records` = 0) and to confirm or dismiss the
   staged alerts, including the new Rule 7 alerts (`alert_records` = 0). Also decide whether forecasts must be
   hidden until approved (the thesis is internally inconsistent; deviation 12).
4. **NNS figures.** The official 2019 and 2021 CALABARZON FIES values, with citations (list in
   `experiments/e59/nns_face_validity.md`).
5. **First blind test.** Score the frozen 2026-Q4 forecast after the December 2026 SWS round.
6. **Relevance labels.** A researcher re-review of the AI-assisted relevance labels (`validation.news_relevance`).
7. **Manuscript.** Align Chapter 3 with what was built (section 3), and use the section 4 wording, updated with the
   numbers above.

---

## 1. Summary table (original audit; see section 0 for the re-grade)

| # | Item (page) | Verdict | Key evidence |
|---|---|---|---|
| GO | Develop, validate and deploy aiPHeed (p.12) | **PARTIALLY MET** | Built and runs end to end (local). Validation is development-only plus one frozen prospective forecast not yet scored. No public deployment or evaluator use in the repo. |
| RQ1 | Strongest predictors by SHAP (p.10) | **MET** (answered) | Food-CPI deviation `Dnow` is #1 by mean \|SHAP\| in E49 and E53. Regional hunger inputs follow. FSSI ranks 8th (E49) / 13th (E53). |
| RQ2 | Furthest reliable lead time (p.10) | **PARTIALLY MET** | Lead 1 only: E49 0.846 (CI 0.769-0.923), E53 0.785 (CI 0.646-0.908). Lead 2 fails: E55 0.673, E38 0.709. Leads 3-8 were not run for the served model family. |
| RQ3 | LightGBM vs six baselines (p.10) | **MET** (answered) | All six named baselines were run on the same 65 rows. The proposed model beats none significantly, and is below persistence on accuracy. |
| RQ4 | Do LGU rankings reflect relative vulnerability? (p.10) | **NOT EVIDENCED IN REPO** | Rankings exist (142 LGUs), but no evaluator responses are stored to judge them. |
| RQ5 | ISO/IEC 25010 assessment by DA / DEPDev (p.11) | **NOT EVIDENCED IN REPO** | Instrument and decision rules exist. 0 responses (`feedback_records` = 0; empty response template). |
| H1 | FSSI and food CPI deviation not among strongest predictors (p.11) | **Partially rejected** (descriptive, no test) | Food-CPI deviation: strongest (rank 1, top 5 in 14/14 quarters). FSSI: not among the strongest (top 5 in 1/14 quarters). As stated (both), the null is **not rejected**. |
| H2 | Not reliable across multiple lead times (p.11) | **Null not rejected** | Point accuracy >= 75% at lead 1 only. Lead 2 is below 75% and below persistence. |
| H3 | Combined LightGBM will not outperform six baselines (p.11) | **Null not rejected** | Two-sided sign-flip test on per-date Brier, Holm over the six. E53: raw p 0.14-0.51, Holm 0.85-1.0. E49: Holm 0.54-0.83. |
| H4 | Disaggregated rankings not consistent with evaluators (p.12) | **NOT EVIDENCED IN REPO** (untested) | Pre-declared Wilcoxon rule in `E25.../instruments/DECISION_RULES.md`. No responses. |
| H5 | No favourable ISO 25010 ratings (p.12) | **NOT EVIDENCED IN REPO** (untested) | Pre-declared rule (median >= 4.0, Wilcoxon vs 3.0, Holm). No responses. |
| SO1 | XLM-R + BERTopic pipeline, bias-corrected FSSI (p.12) | **PARTIALLY MET** | FSSI-v2 from `joeddav/xlm-roberta-large-xnli`, with a coverage bias weight. BERTopic is descriptive only (not a feature; no stored output). Relevance is decided by a keyword rule (R1.1), not by the XLM-R thresholds. 140 admitted articles. |
| SO2 I-IV | Accuracy, precision, recall, F1, AUC (p.12-13) | **MET** (computed) | E53: acc 0.785, P 0.976, R 0.755, F1 0.851, AUC 0.880. E49: 0.846 / 0.957 / 0.849 / 0.900 / 0.855. |
| SO2 V | Lead-time performance by walk-forward CV (p.13) | **PARTIALLY MET** | Leads 1 and 2 for the served family. Leads 1-6 only for the older PCF21 family (E25: no reliable lead). |
| SO3 | Disaggregated LGU rankings (p.13) | **MET** (with caveats) | 142 rows, `risk_index = p x (0.6 poverty_norm + 0.4 density_norm)`, labelled EXPERIMENTAL. Built from forecasts that are not validated against baselines. |
| SO4 | Compare vs baselines I-IV (p.13) | **MET** (done); outcome negative | B1 persistence, B3/B5 government-only, B4/B6 NLP-only, B2 LR combined. The proposed model is not better. |
| SO5 | Public dashboard + alerts, ISO 25010 evaluation, NNS face validity (p.13) | **PARTIALLY MET** | Dashboard, SHAP, alerts workflow and PDF report all work. ISO evaluation: no data. NNS 2019/2023 anchor: not found anywhere. |
| T-75 | 75% accuracy threshold (p.41-42, 57) | **PARTIALLY MET** | Point >= 0.75 at lead 1 (both models). Lower CI bound >= 0.75 only for E49. Persistence 0.877 and always-HIGH 0.815 are both higher than E53. |
| T-F1/AUC | F1 >= 0.75, AUC-ROC >= 0.80 on a blind 4-quarter holdout (p.44, 57, 59-60, 65) | **PARTIALLY MET** | E53 F1 0.851, AUC 0.880 (E49 0.900 / 0.855), but on development walk-forward, **not** on a blind holdout never seen by tuning. |
| Scope | 142 LGUs, map, PDF report, data sources, disclosure, 50 evaluators (p.14-15) | **PARTIALLY MET** | See section 2.5. |
| Rules 1-8 | Algorithm rules (p.48-49) | **PARTIALLY MET** | Rules 3, 4, 5, 6 and 8 met. Rule 1 partial (scheduler off by default; served record frozen). Rule 2 at lead 1 only. Rule 7 deviates. |

---

## 2. Evidence per item

### 2.1 General objective (p.12)

> "To develop, validate, and deploy aiPHeed: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using
> NLP and Machine Learning."

- **Develop: done.** The FastAPI backend (`backend/app`) and React dashboard (`frontend/`) serve two frozen records.
  E49 is the default (E48-A1 LightGBM with five trigger proportions + C2 shrinkage). E53 is a preview (E48-A1
  inputs + five measured driver conditions).
- **Validate: partly.** Nested walk-forward on 65 development rows (`validation.model_evaluation`), plus one
  prospective forecast for 2026-Q4, frozen but not yet scorable. There is no untouched holdout result.
- **Deploy: not evidenced.** The system runs locally (`localhost:8080` / `:8000`). The repo has no public
  deployment, no DA reviewer account (`admin_users` = 0) and no review decisions (`review_records` = 0).

### 2.2 Research questions and hypotheses

**RQ1 (p.10).** "What variables most significantly predict food insecurity risk across the provinces of
CALABARZON, as identified through SHAP feature attribution?"

**H1 (p.11).** "The Food Stress Sentiment Index (FSSI) and food CPI deviation will not be among the strongest
predictors of food insecurity risk in CALABARZON when examined through SHAP feature attribution."

Evidence: the exact TreeSHAP stored per province-quarter in the records. I ranked features by mean \|SHAP\| over
the five provinces, for each of the 14 lead-1 quarters (2023-Q1..2026-Q4).

| Record | Overall top features (mean \|SHAP\|) | Food CPI deviation (`Dnow` / `D_last`) | FSSI (`fssi_v2`) |
|---|---|---|---|
| E49 (default) | Dnow, H_last, H_trend, trig_climate, H_margin, y_last, D_last, fssi_v2, rice_rel, news_reg | Dnow **rank 1** overall (D_last 7). Top 3 in 13/14 quarters, top 5 in 14/14. | **rank 8** overall. Top 5 in 1/14 quarters (rank 1 only in 2026-Q3). |
| E53 (preview) | Dnow, H_last, cond_employment, cond_market, y_last, H_trend, H_margin, D_last, cond_fish, cond_ofw | Dnow **rank 1** (D_last 8). Top 3 in 13/14, top 5 in 14/14. | **rank 13** overall. Top 5 in 1/14 (rank 4 in 2026-Q3). |

- **Verdict:** RQ1 is answered. **H1 is partly rejected:** food CPI deviation is the strongest predictor, but FSSI
  is not among the strongest. Since H1 names both jointly, its null is **not rejected** as written.
- **Test:** none. SHAP ranks are descriptive. The older E25 model ran a permutation check, where removing FSSI
  changed Brier by −0.002 (CI −0.005 to +0.000): `E25_Reliable_Forecasts_2021_2026/FINAL_REPORT.md` line 164.
- **Caveat:** the label itself contains the price term (S1 = H + 2D), so a CPI-deviation input partly mirrors
  the target's own definition.

**RQ2 (p.10).** "What is the furthest lead time at which aiPHeed can reliably forecast province-level food
insecurity risk across CALABARZON?"
**SO2-V (p.13).** "Forecast performance across multiple lead times via walk-forward expanding-window
cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable."
**Algorithm 3 (p.41-42).** "iterate forecast horizons k from 1 to 8 quarters … If mean fold accuracy meets the 75%
threshold, k will be recorded … When accuracy first drops below 75%, the search will halt and returns the last
passing k as the Maximum Reliable Lead Time."
**H2 (p.11).** "aiPHeed will not reliably classify whether a CALABARZON province is at high or low food insecurity
risk across multiple forward-looking lead times."

| Lead | Model | Accuracy (95% date-bootstrap CI) | Balanced | Persistence | Source |
|---|---|---|---|---|---|
| 1 | E49 (default) | 55/65 = **0.846** (0.769-0.923) | 0.841 | 0.877 | `e49_record.json` validation.model_evaluation |
| 1 | E53 (preview) | 51/65 = **0.785** (0.646-0.908) | 0.836 | 0.877 | `e53_record.json` validation.model_evaluation |
| 2 | E38 (E49's lead-2 row) | 39/55 = 0.709 (0.582-0.836) | 0.544 | 0.800 | `e49_record.json` validation.next_quarter_evaluation |
| 2 | E55 (E53's lead-2 row) | 37/55 = **0.673** (0.545-0.800) | 0.670 | 0.800 | `e53_record.json` validation.next_quarter_evaluation |
| 3-8 | served family | not run | – | – | – |
| 1-6 | older PCF21 / E23 family | "Furthest reliable horizon: none (no lead evaluable)" | – | – | `E25.../FINAL_REPORT.md` l.209, 219 |

- **Algorithm 3 by its own point rule:** Maximum Reliable Lead Time = **1 quarter** (k = 1 passes, k = 2 fails).
- **Requiring the CI lower bound to clear 75%:** only E49 at lead 1 is "demonstrated" (lower bound 0.769). E53
  is not (0.646).
- **Verdict:** RQ2 is PARTIALLY MET: answered for k = 1-2 only; k = 3-8 was not run for the served models.
  **H2: null not rejected.** There is no second reliable lead, so "multiple lead times" is not shown.
  Lead 2 E55 vs persistence: exact McNemar p = 0.167 (Holm 0.33); persistence is better.

**RQ3 (p.10).** "How does the LightGBM model combining NLP-derived news signals and government statistical
indicators compare against six baseline approaches, naive persistence, three logistic regression variants
(combined features, government indicators only, and NLP features only), and two LightGBM ablation variants
trained on each data source separately …?"
**H3 (p.11).** "The LightGBM model that combines news signals and government data will not outperform the six
comparison models …"
**SO4 (p.13).** "I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline
IV. Logistic regression baseline"

Same 65 rows, lead 1 (both records hold identical baseline rows):

| Arm | Acc | Bal | Precision | Recall | F1 | AUC | Brier |
|---|---|---|---|---|---|---|---|
| **E53-A1 (proposed, preview)** | 0.785 | 0.836 | 0.976 | 0.755 | 0.851 | 0.880 | 0.150 |
| **E49 (proposed, default)** | 0.846 | 0.841 | 0.957 | 0.849 | 0.900 | 0.855 | 0.151 |
| B1 Naive persistence | 0.877 | 0.860 | 0.959 | 0.887 | 0.922 | 0.860 | 0.123 |
| B2 LR, combined | 0.862 | 0.818 | 0.940 | 0.887 | 0.913 | 0.840 | 0.120 |
| B3 LR, government only | 0.846 | 0.809 | 0.939 | 0.868 | 0.902 | 0.866 | 0.102 |
| B4 LR, NLP only | 0.708 | 0.692 | 0.905 | 0.717 | 0.800 | 0.658 | 0.198 |
| B5 LightGBM, government only | 0.846 | 0.841 | 0.957 | 0.849 | 0.900 | 0.870 | 0.145 |
| B6 LightGBM, NLP only | 0.677 | 0.673 | 0.900 | 0.679 | 0.774 | 0.736 | 0.195 |
| Always HIGH (diagnostic) | 0.815 | 0.500 | 0.815 | 1.000 | 0.898 | 0.500 | 0.185 |

- **Test** (`aipheed-backend-aligned/experiments/E36_LightGBM_One_Quarter_Ahead/runner/e36_evaluate.py`
  l.150-165): two-sided sign-flip test on per-date Brier differences, Holm-adjusted over the six baselines. Exact
  McNemar on correctness is also computed.
  - E53 raw p: B1 0.433, B2 0.348, B3 0.158, B4 0.225, B5 0.514, B6 0.142. Holm 0.85-1.0.
  - E49 raw p: 0.415, 0.243, 0.090, 0.207, 0.357, 0.097. Holm 0.54-0.83.
- **Verdict:** RQ3 and SO4 MET (the comparison was done exactly as specified). **H3: null not rejected.** The
  proposed model is significantly better than none of the six, and is less accurate than B1, B2, B3 and B5.
  News adds no measurable skill: B5 (government only) ties or beats the combined model (records' `limitations`).

**RQ4 (p.10).** "How effectively do the city- and municipality-level food insecurity risk rankings derived from
province-level forecasts reflect relative vulnerability across CALABARZON?"
**H4 (p.12).** "… will not produce municipal and city risk rankings that are consistent with DA Region IV-A
evaluators' assessments … as evaluated through the aiPHeed Post-Survey Questionnaire."

- **What exists:** the rankings (`lgu_ranking.rows`, 142 rows; API `/provinces/{id}/municipalities`) and a
  pre-declared test: a one-sided Wilcoxon on top/bottom-third agreement vs 1/3, plus a median RK1 rating >= 4.0
  (`E25.../instruments/DECISION_RULES.md`).
- **What's missing:** responses. `RESPONSE_EXPORT_TEMPLATE.csv` has only its header; there is no response file.
- **Verdict:** NOT EVIDENCED IN REPO; H4 untested.

**RQ5 (p.11).** "How do DA Region IV-A personnel, as system evaluators, and DEPDev Region IV-A personnel, as
usability evaluators, assess aiPHeed under the ISO/IEC 25010 software quality model …?"
**H5 (p.12).** "aiPHeed will not receive favorable functional suitability, accuracy, and usability ratings from
DA Region IV-A evaluators under the ISO/IEC 25010 software quality model."

- **What exists:**
  - The questionnaire (`E25.../instruments/QUESTIONNAIRE.md`).
  - Decision rules: median >= 4.0 and a one-sided Wilcoxon vs 3.0 with Holm, for each of FS / AC / US, with
    >= 30 valid responses.
  - An in-app SUS form (`app/services/feedback.py`).
- **What's missing:** any responses. `feedback_records` = 0 rows in `backend/aipheed.db`, and there are no
  ISO 25010 responses anywhere.
- **Inconsistency:** RQ5 names DEPDev usability evaluators, while scope (p.15) and 3.7 (p.67) name a single
  group of 50 DA personnel.
- **Verdict:** NOT EVIDENCED IN REPO; H5 untested.

### 2.3 Specific objectives

**SO1 (p.12).** "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment
extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and
latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus."

- **XLM-RoBERTa FSSI: done.** `news.fssi_v2_manifest.intensity_model_key` =
  `joeddav/xlm-roberta-large-xnli@b227ee8435ce`. The coverage bias weight `w = log(1+median)/log(1+n)` is
  applied in `app/news/fssi.py`.
- **Relevance: decided differently from the thesis.** The thesis gate is "core food score at least 0.30 and its
  margin over the non-food hypotheses at least 0.20" (p.30, 59, 65). The code uses keyword rule R1.1
  (`app/news/relevance.py`), because the XLM-R gate measured precision 0.62 and recall about 0.13 on 355
  reviewed titles (`validation.news_relevance`). XLM-R keeps only the intensity role.
- **BERTopic: descriptive only.** `app/news/topics.py` says its proportions "are DESCRIPTIVE … NOT used as
  forecast features", and no topic output is stored in `data/news_e31/`.
- **Corpus.** The thesis says 17,791 raw, 6,085 articles and a 371-article audited set (p.30-31). The record
  has 8,320 collected, 2,820 province-attributed and **140** admitted (`news.totals`).
- **FSSI lags and acceleration:** promised (p.35, 53); not in the served feature lists (only `fssi_v2`,
  `fssi_missing`).
- **Verdict:** PARTIALLY MET.

**SO2 (p.12-13).** "I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance
across multiple lead times …"

- **I-IV: MET.** Every metric is computed and stored (table in 2.2). Specificity, balanced accuracy and Brier
  are also reported.
- **V: PARTIALLY MET** (see RQ2).

**SO3 (p.13).** "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated
province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights."

- **Done:** 142 LGU rows. `risk_index = province probability x (0.6 poverty_norm + 0.4 density_norm)`,
  normalised within each province (p.45-47 formula). Every row carries `disaggregationLabel` and
  `evidenceStatus` = EXPERIMENTAL.
- **Data:** PSA 2021 SAE poverty for 141 of 142 LGUs (Lucena uses an unverified province substitute), and 2024
  POPCEN density (the thesis says the 2020 census).
- **Caveats:** "validated province-level forecasts" is not strictly true, since the province estimates are not
  validated against baselines. LGU levels equal the province level by design.
- **Verdict:** MET as a mechanism; its validity (RQ4/H4) is untested.

**SO4 (p.13):** see RQ3. MET (done); the result does not favour the proposed model.

**SO5 (p.13).** "To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate
it under the ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts
against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor."

- **Dashboard and maps: MET (locally).** Province and LGU map, rankings, SHAP driver panel, news card,
  history/timeseries (`/forecast/timeseries`, 15 points), downloadable PDF (`/quarterly/e31/report.pdf`, HTTP 200).
- **Early-warning alerts: implemented, never exercised.** Candidates are STAGED and become public only after
  CONFIRMED (`app/quarterly/alerts_e31.py`; `app/api/v1/forecast.py:175`). `alert_records` = 0.
- **ISO/IEC 25010 evaluation: NOT EVIDENCED** (see RQ5).
- **NNS 2019/2023 face-validity check: NOT EVIDENCED.** The strings NNS, FNRI, FIES and face appear 0 times in
  the e53 record, and no validation against them is in the repo.
- **Verdict:** PARTIALLY MET.

### 2.4 Numeric targets and evaluation criteria

| Target (page) | Quote | Result | Verdict |
|---|---|---|---|
| 75% mean accuracy (p.41-42, 57) | "If mean fold accuracy meets the 75% threshold, k will be recorded" / "requiring the model to be right three times out of four" | E49 0.846 (CI low 0.769), E53 0.785 (CI low 0.646); lead 2 0.673 / 0.709 | Lead 1 point: MET. Demonstrated: E49 only. Lead 2: NOT MET. |
| k = 1..8, min 8 training quarters (p.41-42) | "iterate forecast horizons k from 1 to 8 quarters … minimum training window of 8 quarters" | Served family: k = 1, 2. Older family: k = 1-6 (7-8 had no dates). The walk-forward requires >= 10 training rows (2 quarters x 5), not 8 quarters. | PARTIALLY MET |
| F1 >= 0.75 and AUC-ROC >= 0.80 on the last 4 holdout quarters never exposed to tuning (p.44, 57, 59-60, 65) | "targeting F1 ≥ 0.75 and AUC-ROC ≥ 0.80" | Development walk-forward: E53 F1 0.851 / AUC 0.880; E49 0.900 / 0.855. No blind 4-quarter holdout (2025-Q4..2026-Q3 were all examined during development). | PARTIALLY MET |
| 100-trial Optuna TPE over 9 hyperparameters (p.43-44) | "A 100-trial Optuna TPE study will optimize nine LightGBM hyperparameters" | Not used by the served models. They use nested selection over 2 feature sets x 4 fixed grids (G1-G4). Optuna appears only in legacy scripts (`scripts/tune_food_availability.py`). | NOT MET (method changed) |
| Blend 0.4 LGBM + 0.4 LR(gov) + 0.2 LR(triggers), HIGH at 0.712 (p.30) | "a province-quarter will be classified HIGH when the blended score reaches 0.712" | Served: LightGBM alone + C2 shrinkage, threshold 0.5 (`decision_threshold` 0.5). The blend was tested in E50/E51 (arm B) and not adopted. | NOT MET (method changed) |
| Relevance >= 0.30 and margin >= 0.20 (p.30, 59, 65) | "tagging an article as relevant only when its core food score is at least 0.30 and its margin … at least 0.20" | Keyword rule R1.1 (2.3, SO1). | NOT MET (method changed, with a documented reason) |
| LIMITED_SIGNAL < 5 articles (p.35, 48, 59, 65) | "If a province-quarter holds fewer than five articles, it will be flagged LIMITED_SIGNAL, and the flag will be carried through to every municipal output" | `limitedSignal` = fewer than 5 validated articles, carried to all LGUs (`app/services/dashboard.py` `limited_signal`, since the news audit fix) | MET |
| Disaggregation 0.6 / 0.4, clamped [0,1] (p.45-47, 53-54) | "risk_index = province_risk_prob x (0.6 x poverty_norm + 0.4 x density_norm)" | Same formula, 142 LGUs | MET |
| Label: global median over all 120 province-quarters, 50/50 classes (p.51-52) | "The global median threshold across all 120 province-quarter pairs will guarantee a balanced class split." | Trailing median of published quarters before each origin. 53 of 65 development labels are HIGH (82%; 93% in 2024-26). | NOT MET (deviation; see E56/E57) |
| 50 DA evaluators, ISO/IEC 25010 (p.15, 67) | "Evaluation will involve 50 DA Region IV-A evaluators" | 0 responses | NOT EVIDENCED |

### 2.5 Scope items (p.14-15)

| Scope item (quote) | Evidence | Verdict |
|---|---|---|
| "forecasts food insecurity risk for the 142 cities and municipalities in Region IV-A" | Province forecasts, disaggregated to 142 LGU indices (relative ranking, not LGU forecasts) | MET (as rankings) |
| "an interactive map showing food insecurity risk levels and rankings, together with the factors influencing each forecast" | Dashboard map, rankings and SHAP driver panel | MET |
| "A downloadable PDF assessment report containing forecast scores, SHAP driver breakdowns, performance metrics, and data-sufficiency disclosures … for each province and CALABARZON" | `/api/v1/quarterly/e31/report.pdf` (HTTP 200) plus report routes | MET |
| "Filipino and English news articles from 2021 to 2025" | Google News RSS titles 2021-01-01..2026-10-14 (`news.source`); titles only, no lead text | PARTIALLY MET (titles only; period extended to 2026) |
| "publicly available data from PSA, DOST-FNRI, SWS, PAGASA, PhilRice, BSP, and DOE" | Served inputs: SWS, PSA CPI, PSA LFS, PSA fisheries, BSP remittances, NASA POWER rainfall, NOAA IBTrACS (E53). No PAGASA, PhilRice, DOE or DOST-FNRI input. | PARTIALLY MET |
| "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk" | S1 = H + 2D (record `target_definition`) | MET |
| "DOST-FNRI data will provide regional food security references" | Not found | NOT EVIDENCED |
| "City and municipal estimates … using PSA Small Area Estimates and population data … will not represent official … classifications" | `disaggregationLabel` says so on every row | MET |
| "Areas with limited news coverage will also be identified" | `limitedSignal` on provinces and LGUs; "Limited data" chip | MET |
| "Evaluation will involve 50 DA Region IV-A evaluators using the ISO/IEC 25010" | 0 responses | NOT EVIDENCED |

### 2.6 Algorithm rules (p.48-49)

| Rule (quote) | Evidence | Verdict |
|---|---|---|
| 1 "automatically retrain LightGBM each quarter … staging all outputs for mandatory review before publication" | `app/tasks/scheduler.py`: APScheduler job on the 15th of Jan/Apr/Jul/Oct, **off unless `AIPHEED_ENABLE_SCHEDULER=1`**. It runs `scripts/quarterly_update cycle`, not verified to rebuild the served E49/E53 records (frozen, built by `scripts/build_record_e36.py`). Outputs are not held back before review (see Rule 7 row and deviation 12). | PARTIALLY MET |
| 2 "The furthest lead time at which the model achieves reliable classification … will be adopted as the operational forecast horizon" | Lead 1 is served by default (`AIPHEED_MAX_LEAD=1`). Lead 2 appears only as an experimental preview. | MET (lead 1) |
| 3 "All features will derive exclusively from data available before the forecast period" | Publication-date filters at every origin; leakage checks in E53-E58 (0 violations). Caveat: current data vintages, retroactive news retrieval. | MET (with caveats) |
| 4 "municipal rankings will apply PSA vulnerability weights to validated province forecasts only" | Applied to the served province forecasts, which are not validated against baselines | PARTIALLY MET |
| 5 "Provinces below the minimum article threshold will display a LIMITED_SIGNAL badge, propagated to all 142 municipal outputs" | Yes | MET |
| 6 "Every forecast will include an explicit horizon label, confidence statement, and verification date" | `/forecast` returns `horizonLabel`, `confidenceStatement`, `verificationDate` | MET |
| 7 "An alert will fire when a province's forecast exceeds the rolling historical threshold. Human confirmation will be required" | Alerts use three evidence rules (P >= 0.80 with price pressure >= +1.0 pp; rise >= 0.20 to >= 0.65; regional hunger), plus a **fixed 0.60** "Active alert" badge (`reference.ALERT_THRESHOLD`). Human confirmation: yes (STAGED -> CONFIRMED). | PARTIALLY MET |
| 8 "All municipal risk indices will carry a disaggregation_label" | Yes, on every LGU row | MET |

---

## 3. Deviations from the thesis text

1. **Label threshold.** Thesis: global median over all 120 province-quarters, "guarantees a 50/50 class balance"
   (p.51-52). Code: trailing median of the published quarters before each origin (no look-ahead). Result: 82% HIGH
   in development, 93% in 2024-26. E56 (8- and 4-quarter windows, cross-province) and E57 (y_last, "worsening")
   found no eligible alternative.
2. **CPI deviation definition.** Eq. 3 (p.51) and the label use the province minus the regional mean. Table
   3.4.2.4 (p.53) defines CPI_dev as "food CPI deviation from the rolling provincial mean". The code follows Eq. 3.
3. **Model.** Thesis: Optuna-tuned LightGBM in a 0.4/0.4/0.2 blend, HIGH at 0.712 (p.30, 43-44, 59-60, 65).
   Code: LightGBM alone, nested choice of 2 feature sets x 4 fixed grids, C2 linear shrinkage calibration,
   threshold 0.5.
4. **Features.** Thesis: a 12-feature panel (FSSI, two lags, acceleration, five triggers, CPI_dev, unemployment,
   rice change) on 120-135 rows. E49: 18 inputs. E53: 23 inputs, including regional SWS hunger inputs (H_last,
   H_gap, H_trend, H_margin), the last label y_last, and five measured condition ranks. No FSSI lags. 75 training
   rows at the 2026-Q4 origin.
5. **Validation design.** Thesis: a blind four-quarter holdout (2025-Q4 to 2026-Q3) never seen by tuning (p.30-31,
   43-44). Code: nested walk-forward over development dates that were all examined during development. The only
   untouched test is the frozen 2026-Q4 forecast, not yet scorable.
6. **Lead-time scan.** Thesis: k = 1..8 with a 75% stopping rule (p.41-42). Served family: k = 1 and 2 only. The
   older PCF21 family scanned 1-6 (E25) and found no reliable lead.
7. **Minimum training window.** Thesis: 8 quarters (p.41-42). Code: >= 10 training rows with both classes
   (2 quarters x 5 provinces).
8. **Relevance gate.** Thesis: XLM-R score >= 0.30 and margin >= 0.20 (p.30, 59, 65). Code: keyword rule R1.1;
   XLM-R used only for intensity. The relevance labels used for validation were made by the AI assistant, and a
   researcher re-review is pending (`validation.news_relevance.annotator`).
9. **Corpus size and period.** Thesis: 17,791 raw / 6,085 / 371 audited articles, 2020-2025 (p.30-31). Record:
   8,320 / 2,820 / 140, 2021-01-01..2026-10-14, titles only.
10. **BERTopic.** Thesis: part of the two-tier pipeline producing "latent food insecurity risk patterns" (p.12).
    Code: descriptive only, explicitly not a feature; no stored output.
11. **Alert rule.** Thesis: "exceeds the rolling historical threshold" (p.49). Code: fixed evidence rules plus a
    fixed 0.60 badge.
12. **Review visibility.** The thesis contradicts itself:
    - **Pages 60 and 66:** STAGED forecasts "remain visible on the dashboard until a DA administrator approves it
      or rejects it". The code follows this.
    - **Rule 1 (p.48) and the state diagram (p.66-67):** outputs are staged "for mandatory review before
      publication", and "no forecasts or warnings appear on the public dashboard without human decision-making".
      The code meets this only for alerts.
13. **Data sources.** Thesis: PAGASA, PhilRice, DOE, DOST-FNRI (p.15, 32). Served inputs: NASA POWER
    (reanalysis) and NOAA IBTrACS instead of PAGASA; national LFS and BSP for Employment and OFW (the same value
    for every province); no PhilRice or DOE; no DOST-FNRI anchor.
14. **Disaggregation density year.** Thesis: 2020 census (p.45-46, 60). Code: 2024 POPCEN.
15. **Evaluators.** RQ5 names DEPDev usability evaluators (p.11). Scope and 3.7 name a single group of 50 DA
    personnel (p.15, 67). Neither group's responses are in the repo.
16. **E49 record text error.** `e49_record.json` `validation.threshold_75pct` has `demonstrated: true` and CI
    0.769-0.923, but its `verdict` sentence says the interval "reaches below 75%, so the target is not
    demonstrated". The sentence is a template (`scripts/build_record_e36.py` l.210-218) and is wrong for E49. The
    record is protected and was not changed.

---

## 4. Suggested honest wording

For Chapter 4 (Results) and Chapter 5 (Conclusions and Recommendations), for every item that is not fully met.
Numbers are from the served records; replace "E53" with "E49" if the default model is the one reported.

**General objective.**
- Ch. 4: "aiPHeed was developed as a working system (FastAPI backend and React dashboard) and validated on 65
  development estimates by nested walk-forward evaluation. A forecast for 2026-Q4 was frozen before its outcome
  existed and will be scored after the December 2026 SWS round. Deployment to DA Region IV-A users had not taken
  place at the time of writing."
- Ch. 5: "The system was developed and internally validated; operational deployment and evaluation with DA Region
  IV-A personnel remain to be done."

**RQ1 / H1.**
- Ch. 4: "By mean absolute SHAP value, provincial food-CPI deviation in the first two months of the quarter was the
  strongest input in every one of the 14 quarters examined (rank 1 overall), followed by the regional SWS hunger
  inputs. The Food Stress Sentiment Index ranked 8th overall (13th in the preview model) and was among the five
  strongest inputs in only one quarter. H1 is therefore rejected for food CPI deviation but not for the FSSI; as
  stated jointly, it is not rejected. No significance test was applied to the SHAP ranks; because the label itself
  contains the price term, the CPI result partly reflects the label's definition."
- Ch. 5: "Government price data, not news sentiment, drove the forecasts. Future work should test whether a news
  signal adds skill once a larger, reviewed article set is available."

**RQ2 / H2 / SO2-V / the 75% target.**
- Ch. 4: "Following Algorithm 3, accuracy reached the 75% threshold one quarter ahead (0.846 for the default model,
  95% CI 0.769-0.923; 0.785 for the preview model, CI 0.646-0.908) but not two quarters ahead (0.709 and 0.673).
  The Maximum Reliable Lead Time is therefore one quarter. Scanning k = 1 to 8 with the same model family (E59), the
  search halts at k = 2 (0.709). The higher accuracies at k = 3 to 6 (0.73 to 0.96) come with balanced accuracy at
  or below 0.5, the result of predicting HIGH when nearly every target quarter is HIGH, and k = 7 and 8 have too few
  scored quarters to evaluate. H2 is not rejected: reliable classification was not shown at more than one lead
  time."
- Ch. 5: "aiPHeed can support planning one quarter ahead; two-quarter-ahead outputs are experimental and should not
  be used for decisions."

**RQ3 / H3 / SO4.**
- Ch. 4: "All six comparison models were evaluated on the same 65 estimates. The proposed model did not
  significantly outperform any of them (two-sided sign-flip test on per-date Brier scores, Holm-adjusted;
  smallest adjusted p = 0.54 for the default model, 0.85 for the preview), and naive persistence was more
  accurate (0.877). H3 is not rejected. The government-only LightGBM performed as well as the combined model,
  so the news features added no measurable skill."
- Ch. 5: "Persistence remains a strong benchmark because most quarters since 2024 are HIGH; the model's distinct
  value is identifying LOW quarters (11 of 12 caught, balanced accuracy 0.836), which always-HIGH cannot do."

**RQ4 / H4, RQ5 / H5, ISO/IEC 25010.**
- Ch. 4: "The evaluator survey had not been administered at the time of writing; H4 and H5 could not be tested.
  The instrument and the decision rules (Wilcoxon signed-rank tests with predeclared thresholds) were prepared in
  advance."
- Ch. 5: "Administer the aiPHeed Post-Survey Questionnaire to at least 30 DA Region IV-A evaluators before drawing
  conclusions on usability, functional suitability or ranking consistency."

**SO1.**
- Ch. 4: "XLM-RoBERTa (zero-shot) scored the food-stress intensity of 140 relevant, province-attributed news
  titles (2021-2026), aggregated into a bias-corrected FSSI. Because the XLM-RoBERTa relevance gate reached only
  0.62 precision and about 0.13 recall on a 355-title reviewed sample, relevance was decided by a transparent
  keyword rule (R1.1). BERTopic was applied descriptively only; its topics were not used as forecast features,
  because a topic model fitted on all quarters would leak later information into earlier ones. On the 55 relevant
  articles it found two topics, left 40% of articles unassigned, and was not stable across random seeds (mean
  adjusted Rand index 0.38, below the 0.5 set in advance), so no topic patterns are reported."
- Ch. 5: "Expand and manually review the article set, and refit topic models at each forecast origin if topics
  are to be used as features."

**SO3 / Rule 4.**
- Ch. 4: "Province estimates were disaggregated to all 142 LGUs using PSA 2021 poverty (60%) and 2024 population
  density (40%). Because the province estimates were not shown to outperform the baselines, the LGU rankings are
  labelled experimental and indicate relative priority within a province, not municipal forecasts."

**SO5 (NNS face validity, alerts).**
- Ch. 4: "The dashboard presents maps, rankings, SHAP explanations, forecast history and a PDF report.
  Early-warning alerts, including the thesis's rolling-threshold rule (a province's estimate above the 75th
  percentile of its own earlier estimates), are staged for DA confirmation; none had been confirmed during the
  study. Against DOST-FNRI's 2023 NNS, CALABARZON had the lowest moderate-or-severe household food insecurity of all
  regions (19.1%, 95% CI 17.0-21.1; Philippines 31.4%), and 2023 was also the model's lowest year (mean probability
  0.47; 9 of 20 province-quarters observed LOW). Regional 2019 and 2021 figures were not available, so the anchor
  rests on one survey year and is not a statistical validation."
- Ch. 5: "Obtain the 2019 and 2021 regional NNS figures and any post-2023 survey round to anchor the 2024-2026 rise,
  and run a live alert-review cycle with DA administrators."

**F1 / AUC targets and blind holdout.**
- Ch. 4: "On the development evaluation, F1 was 0.851 and AUC-ROC 0.880 (default model: 0.900 and 0.855), above
  the 0.75 and 0.80 targets. These figures are not from a blind holdout: the four most recent quarters were also
  examined during development. The first untouched test is the frozen 2026-Q4 forecast."

**Label (deviation 1).**
- Ch. 4: "The label threshold was implemented as the trailing median of published quarters available at each
  forecast origin, rather than the global median of all quarters, to avoid using future outcomes. Because hunger
  rose after 2023, 82% of development labels are HIGH (93% in 2024-2026), so the label indicates hunger above its
  2021-2023 level rather than a balanced high/low split. Alternative windows and label definitions (E56, E57)
  did not perform better under pre-registered rules."

**Review workflow (deviation 12).**
- Ch. 3/4: state one rule consistently. Either: "forecasts are published automatically and can be withheld by a
  DA reviewer; alerts require confirmation" (the current system), or implement the stricter rule before claiming
  that no forecast appears without human decision-making.
