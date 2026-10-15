# E31: Complete, validate and finalize aiPHeed (Chapter I objectives)

**Dates:** 2026-10-14 to 2026-10-15. **Branch:** `e31-chapter1-completion` (created from `e25-e26-experiments-on-latest-ui` at 96e388e).
**Folder:** `aipheed-backend-aligned/experiments/E31_Chapter1_Completion/`, with isolated `backend_dev/` and `dashboard_dev/` (copied from E29).
**Not modified:** `backend/`, `frontend/`, E25–E30. Nothing was pushed or deployed.

**Authorizations given by the researcher on 2026-10-14:**
- data released up to 2026-10-14;
- meta-description lead text from public pages, provided robots.txt allows it (in practice not obtainable, see §4);
- integration into the main app on a new git branch (deferred until after E32, so the main app carries the engine that passes E32).

**No new forecasting model was trained in E31.** PCF21 (E24v2/E25) and P45 (E25) were rescored on new data; nothing was refitted. E31 fixed the data, news, timing, integration and workflow failures. Building a new model is E32.

## 1. Bottom line

| Chapter I objective | Built and verified | Goal achieved? | Evidence |
|---|---|---|---|
| 1. Two-tier NLP → bias-corrected FSSI per province-quarter | Yes. Validated relevance gate; FSSI-v2 versioned beside FSSI-v1 | **Partly.** The evidence is thin (titles only): 7/120 province-quarters sufficient | §4–5 |
| 2. LightGBM metrics and the furthest reliable horizon | Yes: every metric by lead, plus one unseen quarter (2026-Q3) | **No.** No lead is reliable; no model beats persistence or always-HIGH | §7 |
| 3. LGU rankings from *validated* province forecasts | Yes: 142/142 rankings, audited; map, API and PDF agree | **Partly.** The province forecasts are not validated; 126/142 LGUs use a poverty substitute | §8 |
| 4. Comparison with the four baselines | Yes: same rows, same metrics | **Done; the result is negative.** The proposed LightGBM does not beat persistence | §7 |
| 5. Dashboard, ISO 25010 evaluation, NNS anchor | Dashboard works locally on the corrected pipeline; 55 live/UI tests | **No.** This needs the 50 DA evaluators, approval to deploy and a verified NNS 2019 figure | §9 |

**The 75% requirement** (the researcher's criterion; Chapter I states no number):
- At lead 1, P45 reaches 0.825 and PCF21 0.867, both above 75%.
- Always-HIGH reaches 0.911 and persistence 0.889.
- Accuracy above 75% therefore shows no skill. A constant forecast meets it, because 91% of test labels are HIGH.

## 2. Frozen-before-outcome evaluation of 2026-Q3 (first unseen quarter)

**Frozen before any Q3 outcome was retrieved:**
- PCF21 and its references: git `70d8770`, 23:31:58 PHT;
- P45 and the model baselines at lead 2: git `bbbe104`.

The E24v2 seal (git `96e388e`) also covers 2026-Q3.

**Outcome:**
- H = 23.6, from the SWS 21–27 September round (posted 2026-10-14).
- D comes from PSA July–September 2026 food CPI.
- All five provinces are HIGH, against a threshold of 14.3.

**Scores** (`runs/e31_q3_scores.json`):

| Arm | Lead | Brier | Accuracy |
|---|---|---|---|
| Persistence (E31) | 1 | 0.000 | 1.0 |
| Always-HIGH | 1 | 0.000 | 1.0 |
| PCF21 | 1 | 0.097 | 1.0 |
| PCF21 | 2 | 0.100 | 1.0 |
| P45 | 2 | 0.194 | 0.6 |
| E24v2 M2 | 1 | 0.038 | 1.0 |

This is one regional observation (five rows sharing one H), so it supports no statistical claim.

## 3. Root causes and resolutions

| # | Failure | Root cause | Resolution | Evidence |
|---|---|---|---|---|
| R1 | News filter kept irrelevant stories and missed relevant ones | XLM-R zero-shot over 10 hypotheses scores responses (food aid) lower than food-business features; the guard lexicon missed "fishers" and similar words | Rule R1 written from a rubric, frozen (git `752d587`) and validated on a fresh blind holdout; R1.1 fixes the holdout's false-positive patterns | §4 |
| R2 | Earlier counts of "558 articles" looked like lost data | Those came from the unguarded scorer (precision 0.33; FSSI correlated −0.34 with hunger) | Not restored: no regression | `classifier.py` notes; §4 |
| R3 | No explicit forecast-vs-nowcast news rule | — | `app/news/alignment.py` and 9 tests; provenance block on every output | §5 |
| R4 | Data limit fixed at 2026-06 | Authorization | `authorized_through` date limit; 2026-Q3 data; verified SWS posting dates (March 12 May, June 24 Aug, September 14 Oct) and sample sizes | `data_acquired/` |
| R5 | The main map dashboard served the old LightGBM (trained on 2020 data) and the old corpus | The service read `data/processed` artefacts | E31 data layer (`app/ml/inference/e31_engine.py`): engine, explainer (exact drivers) and disaggregator from one record; `AIPHEED_DATA_LAYER=legacy` restores the old behaviour | 13 live E2E tests |
| R6 | No alert was ever staged | `AlertRepository.insert` had no caller | `app/quarterly/alerts_e31.py` with documented evidence rules; only admin-confirmed alerts are public | live test |
| R7 | The municipalities endpoint returned 500 for every quarter | The schema required a string after E28 removed LGU bands; it also dropped the rank fields | Schema fixed | live test |
| R8 | The record held NaN (invalid JSON) | Undefined metrics | Sanitised to null; `allow_nan=False` | live test |
| R9 | A fresh deployment had no tables | Missing `alembic.ini`; migrations undocumented | `runner/start_e2e_server.sh` runs `alembic upgrade head` | §9 |
| R11 | The Visualization PDF export and the legacy PDF failed (404 and 500); the brief pages used URLs without `/api/v1` (silent fallback, dead PDF links); the map's explanation text described a model that is not served; a forecast quarter showed 0 news | Endpoints missing or stale after the engine change | `/report/data` from the record; `/report` fixed; URLs fixed; E31 explanation note; news shown from the forecast's evidence quarter (`sourceQuarter`); legend labelled "Estimate (unvalidated)" | live tests; screenshots |
| R10 | Explanations came from a different model | SHAP of the old LightGBM | Exact decomposition of the served engine, S1 − τ = (H − τ) + 2D; recomputed backtests equal E25 to 1e-6 (assert) | builder |

## 4. News coverage audit

**Source:**
- Google News RSS, titles only.
- Credible-domain policy v1.
- 2021-01-01 to 2026-10-14: 1,545 requests, 8,320 articles.

**Lead text could not be obtained compliantly:**
- news.google.com's robots.txt disallows `/articles` and `/rss` for generic crawlers, and Claude agents outright.
- Inquirer and DSWD block their REST APIs (login required).
- mb.com.ph and pia.gov.ph return 403.
- BusinessMirror and Rappler disallow crawlers.
- Sitemaps list recent items only.
- Only Interaksyon allowed it, about 1.5% of articles.

So no partial lead-text series was built. **Decision for the researcher:** robots.txt also covers `/rss`, the source E28 collected from.

**Funnel (whole corpus):**
- 8,320 collected;
- 2,820 province-attributed;
- 140 relevant under R1.1;
- 0 syndicated copies;
- 140 in FSSI-v2.

| | Sufficient | Limited | None |
|---|---|---|---|
| FSSI-v2 province-quarters | 7 | 46 | 67 |
| FSSI-v1 (same store) | 0 | 35 | 85 |

FSSI-v1 has 55 articles in total.

**Relevance validation** (`validation/`; annotated by the AI assistant, blind to scores; **researcher re-review recommended**):

| Gate | Sample | Precision | Recall | F1 |
|---|---|---|---|---|
| E28 gate (guard + XLM-R ≥ 0.30) | dev, 355 (unbiased for E28) | 0.62 | 0.13 | 0.21 |
| R1 (frozen) | **fresh holdout, 238** | **0.85** (0.77–0.92) | **0.40** (0.26–0.69) | 0.54 |
| R1.1 (deployed) | holdout, *optimistic* | 0.99 | 0.39 | 0.56 |
| R-NLI single hypothesis | dev | AUC 0.66 | — | TEST-half F1 0.37 |

Other checks:
- Geography: 504/513 reviewed province-attributed titles concern the attributed province; 7 are wrong ("Rizal Memorial", the film "Quezon"), 2 unclear.
- Dates: 0 articles outside their quarter or after the limit.

## 5. Quarterly alignment

| Mode | News used | Cutoff rule |
|---|---|---|
| FORECAST, target T, lead k | Quarter T−k | Cutoff ≤ start of T |
| NOWCAST, target T | Quarter T | Published by the cutoff; never the previous quarter |

- Violations raise an error.
- Every output stores: mode, target, lead, generated_at, information cutoff, evidence window (FULL/PARTIAL with days), news-store hashes and a hash of the article set used.
- Operational outputs:
  - **2026-Q4 NOWCAST**, cutoff 2026-10-14; supporting news 1–14 October, 14/92 days;
  - **2027-Q1 FORECAST**, evidence quarter 2026-Q4, PARTIAL.
- PCF21 uses no news; this is stated in the provenance.

## 6. Does the better news signal help? (exploratory, development quarters)

The frozen E28 protocol was rerun with the news panel swapped (`runs/e31_eval_v1`, `runs/e31_eval_v2`); lead-1 T1 results:

| Arm | v1 accuracy | v1 Brier | FSSI-v2 (R1.1) accuracy | FSSI-v2 (R1.1) Brier |
|---|---|---|---|---|
| NLP_LR | 0.267 | 0.309 | 0.378 | 0.260 |
| NLP_LGBM | 0.400 | 0.273 | 0.422 | 0.239 |
| PROPOSED | 0.533 | 0.312 | 0.578 | 0.301 |
| LR_COMB | 0.511 | 0.308 | 0.578 | 0.288 |

- Better news helps the news-based arms modestly.
- All remain far below persistence (0.889 / 0.111) and always-HIGH.
- v1 on the E31 store reproduces E28 exactly.

## 7. Model validation (Objectives 2 and 4)

Basis:
- The E28 frozen protocol (d897f56d).
- Lead 1: 45 rows, 9 dates, 41 HIGH / 4 LOW.
- Full metrics with confidence intervals and stability flags are in `runs/e28_eval/results.json` and the record's `validation`.

| Arm | Acc | Bal. acc | ROC-AUC | Brier |
|---|---|---|---|---|
| Persistence | 0.889 | — | 0.826 | 0.111 |
| Always-HIGH | 0.911 | 0.50 | 0.50 | 0.089 |
| PCF21 | 0.867 | — | 0.762 | 0.103 |
| P45 | 0.825 | — | 0.658 | 0.133 |
| PSA-only LR | 0.600 | — | 0.756 | 0.280 |
| NLP-only LR | 0.267 | — | 0.122 | 0.309 |
| LR combined | 0.511 | — | 0.652 | 0.308 |
| Proposed (E28 inputs) | 0.533 | — | 0.720 | 0.312 |

AUC values are unstable: fewer than 5 LOW rows.

## 8. DA-facing outputs

**Province estimates:**

| Province | 2026-Q4 nowcast P(S1 above threshold) | 2027-Q1 forecast |
|---|---|---|
| Quezon | 0.98 | 0.93 |
| Rizal | 0.97 | 0.92 |
| Cavite | 0.96 | 0.91 |
| Laguna | 0.96 | 0.91 |
| Batangas | 0.76 | 0.77 |

- The drivers show that regional hunger supplies about 80% of the margin.
- Provinces are told apart only by measured food prices. Quezon is +1.17 pp above the five-province average; Batangas is −2.63 pp below it.

**Alerts:** the rules give exactly two candidates:
- one regional hunger alert;
- one provincial price-pressure alert, for Quezon.

They are not five copies of the regional signal, and both are STAGED until a DA administrator confirms them.

**LGU top 3:** Gen. Mariano Alvarez (Cavite), Sariaya (Quezon), Rodriguez (Rizal). These are relative positions only.

## 9. Tests and reproducibility

- **Backend:** 146 passed and 2 skipped (live tests run separately). This includes the new alignment, date-limit and record tests. Two inherited tests were updated for the new data limit: the refusal test no longer makes live requests.
- **Live E2E** against a running server (`tests/test_e31_e2e_live.py`): **16/16**. It covers map, ranking, explanations, LGUs, news (including forecast evidence quarter), both report paths, PDF hash, error codes, admin login and the alert workflow.
- **Visual check:** headless Edge screenshots of `/dashboard`, `/da-brief` and `/news` against the live backend.
- **Dashboard:** 43/43 vitest (7 new); build succeeds; 11 TypeScript errors, identical to the E29 baseline (none new).
- **Commands:** see `REPRODUCE.md`.

## 10. Remaining blockers and decisions

1. **Unseen outcomes.** 2026-Q4 SWS round (about January 2027) and Q4 CPI. This is the only route to a reliability claim.
2. **Target design** (adviser). The label is about two-thirds regional hunger, so in most quarters all provinces are HIGH. Options are investigated in E32.
3. **Google News robots.txt** and licensed lead text (N-TEXT).
4. **Municipal poverty.** A 2021 municipal SAE extract without the 2018 columns (O8).
5. **Researcher re-review** of the relevance annotations.
6. **Objective 5:** DA evaluators, deployment approval, NNS 2019.
