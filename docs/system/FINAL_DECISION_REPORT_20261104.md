# aiPHeed final decision report (2026-11-04)

**Basis.**
* Branch `pfi/survey-anchored-final`. The starting evidence is `AIPHEED_INTEGRATED_METHODOLOGY_AND_STATUS.md`
  (commit `deeac31e`). It was verified against the code, data, registry and live API.
* **Corrections made in this run** (details in D):
  1. The E140 candidate issue was tied to a fixed 2026-10-01 feature file. It now follows the quarter clock.
  2. Its explanations were approximate. They are now exact TreeSHAP and add up to each prediction.
  3. It forced HIGH/LOW. It now shows UNCERTAIN when the 90 % interval crosses 0.5.
  4. Its output said "lead 1". It now states the actual claim (survey-to-survey).
  5. The prospective scorer documented baselines and instrument separation it did not compute. Both are now
     implemented.
  6. The FSSI "bias correction" is shown **not** to remove news-volume dependence.
* Locked studies (FI5–FI9-Z, E137–E140), seals and protocols are unchanged.

## A. Final decisions

**What aiPHeed estimates.**
* For each CALABARZON province, aiPHeed estimates the probability that its household food insecurity (HFIAS
  moderate-or-severe, FNRI) is above the national level of the same survey. This is an **estimated relative risk**.
* It is not a measured prevalence and not a share of households.
* HIGH, LOW and UNCERTAIN are shown only as the 90 % interval allows.

**The target was audited and retained.**

| Question | Finding |
|---|---|
| Same instrument and population across rounds? | Yes: 9-item HFIAS, 30-day recall, households, FNRI scoring (E137 `OUTCOME_AUDIT.md`). FIES is never pooled with it. |
| Same reference period? | 2015 fieldwork July–November. The ENNS fieldwork months are not printed, so Q3 is an **assumption** (documented). |
| Is a quarter assignment justified? | Only as the survey's reference quarter. A survey value is never treated as a quarterly series. |
| Does issue-time information precede the target? | Yes. Features are frozen 1 quarter before the survey's reference quarter (Lead-1 training), and the release rules are tested. |
| Ranking or risk condition? | Relative: "above the national level". It is meaningful for prioritisation, not a prevalence threshold. |
| National reference comparable? | Within each round, yes. The pooled ENNS 2018–19 national value is used, because the round-printed values describe province subsets. |
| Survey error reflected? | Yes: the relative logit carries its survey SE and a soft label. NOT_DISTINGUISHABLE and INSUFFICIENT are kept. |

**What it can and cannot forecast.**
* The model's out-of-time evidence is **survey-to-survey**: train on 2015 + 2018, predict the 2019 provincial round.
* Its next-quarter output (dashboard viewed in 2026-Q4 → 2027-Q1) is therefore a **structural relative-risk
  estimate carried into the display quarter**.
* It is **not** a validated quarter-to-quarter forecast. No quarterly provincial food-insecurity measurement exists,
  so quarterly change cannot be identified.
* Regionally, LightGBM forecasts of SWS hunger do not beat persistence.

**Maximum genuinely validated horizon: none.**

**Model.**
* E140 LGBM-AUTO: LightGBM, 100 constant-leaf trees, chosen by nested CV.
* It is the strongest candidate on every development test except island-group transfer.
* It is **not adopted**. E140 decision C: trees are not significantly better than the linear prior; it fails
  island transfer and the comparison with the region's previous level.

**Contributor groups that actually contribute.** From the exact TreeSHAP of the served candidate, 2027-Q1, for
CALABARZON (relative-logit scale):

| Group | Contribution |
|---|---|
| Poverty and vulnerability | −0.20 to −0.34 |
| Geography (island group) | about −0.19 |
| Measured history | about −0.04 |
| Market | −0.02 to +0.03 |
| Climate | about −0.03 |
| Employment and remittances | not a model input (no provincial series) |
| News and NLP | not a model input (CALABARZON-only archive) |

**NLP.** The pipeline runs. One archive signal tracks real typhoon exposure. FSSI's correction reduces small-sample
noise but not volume bias. Sentiment accuracy is unknown, because there is no human-labelled set (owner rule).

**The 142 LGU rankings.** An **LGU vulnerability-weighted priority ranking** (province P × vulnerability). It is a
candidate pending provincial validation, not a municipal measurement.

**Production: CANDIDATE IMPLEMENTED, VALIDATION PENDING** (section F).

## B. Acceptance matrix

| Requirement | Status | Evidence | Fixable by |
|---|---|---|---|
| **Obj. 1** NLP two-tier pipeline, bias-corrected FSSI, province-quarter patterns | **PARTIALLY ACHIEVED** | `app/fi5/nlp.py` (XLM-R zero-shot, 11 BERTopic topics, province-quarter FSSI); `app/fi6/news_events.py` (62,698 archive articles, event dedup). `data/e140/out/nlp_validity.json`: archive risk share vs cyclones ρ 0.24 (p < 0.001, n 349); FI5 climate FSSI vs cyclones ρ 0.05; FI5 market FSSI vs food CPI ρ 0.01; **volume dependence 0.457 raw → 0.451 corrected** | Sentiment accuracy needs a human-labelled set (new evidence; owner rule). Volume bias needs a new correction method (methodology). |
| **Obj. 2** LightGBM metrics and walk-forward across leads; furthest reliable horizon | Evaluation **ACHIEVED**; Lead ≥ 1 **NOT ACHIEVED** (regional) / **CANNOT YET BE VALIDATED** (provincial) | FI5/FI6 (regional, 62 quarters); E139/E140 (provincial, LORO/LOPO/ISLAND/V2/TFWD); section C | New independent evidence only |
| **Obj. 3** LGU rankings from validated province forecasts | **PARTIALLY ACHIEVED** | 142 LGUs, unique PSGC, no missing poverty or density (Lucena from the PSA HUC table, flagged), interval carried through; `data/e140/out/lgus_next_quarter.csv` | Requires a validated province forecast (new evidence) |
| **Obj. 4** LightGBM vs persistence, PSA-only, NLP-only, logistic | **PARTIALLY ACHIEVED** | Regional FI6: all four on an identical task; LightGBM loses to persistence. Provincial: persistence, PSA-type (poverty logistic, E138/E139), logistic; **NLP-only cannot be built** (no national news). Not one equivalent four-model comparison. | Provincial NLP-only needs a national news archive (new data) |
| Risk defined with FAO; gaps explicit | **ACHIEVED** | Audit section 2–3; utilization missing; employment national only | — |
| Release-date discipline, no leakage | **ACHIEVED** | `app/e137/features.py`, `app/e139/live.py`; tests in `test_e137/139/system_completion.py` | — |
| No fabricated, interpolated or copied labels | **ACHIEVED** | E137–E140 train on 125 measured rows only | — |
| Dynamic next-quarter target | **ACHIEVED** | `app/quarterly/target.py`; tests for Q4→Q1, Q1→Q2, Q2→Q3 and the Manila-midnight edge | — |
| Genuine next-quarter forecasting ability | **NOT ACHIEVED** (regional) / **CANNOT YET BE VALIDATED** (provincial) | Section C | New evidence |
| Explanations match the model | **ACHIEVED** for the candidate (exact TreeSHAP, sum check) | `app/e140/issue.py::contributions`; test | — |
| Served dashboard contributor panel | **NOT ACHIEVED**: it is the legacy CH1 price index (Market 100 %, true for that model) | Live `/api/v1/explainability` | Owner decision on CH1 |
| Only correctly labelled outputs public | **ACHIEVED** | Registry `production: null`; outlook `validation_pending` with per-candidate check counts; candidates admin-only; CH1 labelled "price-pressure … not a food-insecurity forecast" | — |
| Prospective validation ready | **ACHIEVED** | `app/registry/prospective_provincial.py`: hash chain, write-once seals for E138/E139/E140, baselines, instrument separation, template | — |

## C. Model comparison (separate tasks, separate winners)

**1. Provincial HFIAS risk estimation, unseen region (LORO; 125 rows, 62 decisive).**

| Model | EB | AUC | Accuracy | HIGH recall | ECE |
|---|---|---|---|---|---|
| **E140 LightGBM** | **0.182** | **0.960** | **0.871** | 0.875 | 0.039 |
| E139 linear prior (0 trees) | 0.192 | 0.915 | 0.774 | 0.900 | 0.066 |
| Ridge, all features | 0.193 | 0.941 | 0.871 | 0.950 | 0.060 |
| Logistic, all features (E139 run, same folds) | 0.212 | 0.900 | 0.839 | 0.875 | 0.079 |
| Poverty-only logistic | 0.212 | 0.851 | 0.726 | 0.725 | 0.058 |
| Region's previous level | 0.218 | 0.632 | 0.694 | 0.875 | 0.188 |
| National base rate | 0.258 | — | 0.645 | — | 0.283 |

**E140 detail.**
* **Confusion matrix:** TP 35, FP 3, TN 19, FN 5.
* **By survey:** accuracy 0.875 (2015), 0.895 (2018), 0.842 (2019).
* **Calibration bins (mean predicted vs mean soft label):** 0.13/0.04, 0.33/0.49, 0.48/0.46, 0.73/0.72, 0.90/0.88.
  The lowest bin over-predicts.
* **Difference vs the linear prior:** −0.010 [−0.031, +0.012], not significant.
* **Most of the AUC comes from separating island groups.** Within Luzon (CALABARZON's group), AUC is **0.70**
  (25 decisive rows). Visayas and Mindanao cannot be evaluated alone.

**2. Provincial forward round (survey-to-survey; development data).**

| Test | Result |
|---|---|
| TFWD (train 2015 + 2018 → predict 2019; 25 rows, 19 decisive) | E140 EB 0.148, AUC 0.971, accuracy 0.947; linear prior 0.148; ridge **0.128**; region's previous level 0.161; persistence 0.188 |
| ENNS rows under LORO | E140 beats persistence: EB difference CI [−0.136, −0.024] |

* **Best on TFWD:** ridge, by EB. E140 has the best AUC.

**3. Geographic generalisation.**
* LOPO: E140 AUC 0.975; same-survey regional base rate 0.963.
* **ISLAND (unseen island group): E140 AUC 0.353**, against 0.787 for the linear prior.
* **Best:** the linear prior for unseen island groups; E140 for unseen provinces or regions within known island groups.

**4. Regional SWS next-quarter forecasting (FI6, 62 quarters, 11 HIGH).**

| Lead | LightGBM accuracy / HIGH recall / AUC / Brier | Persistence | Other baselines |
|---|---|---|---|
| 1 | 0.839 / 0.27 / 0.69 / 0.129 | **0.871 / 0.55 / 0.74 / 0.116** | PSA-only 0.191, NLP-only 0.174, logistic 0.169 (Brier) |
| 2 (the dashboard's current issue timing) | 0.806 / 0.00 / 0.47 / 0.163 | 0.710 / 0.09 / 0.58 / 0.198 | — |

* **Best:** persistence at Lead 1; no model at Lead 2.

**5. Prospective.**
* Sealed provincial predictions: E138 `e324433c…`, E139 `0bcb5584…`, E140 (`sealed_prediction_2026-10-01.json`,
  in the register).
* Sealed regional forecasts: FI5/FI6 for 2026-Q4 onward.
* **No prospective outcome has been published yet.**

## D. Implementation record (this run)

**Changed.**
* `backend/app/e140/issue.py`:
  * the issue date comes from the quarter clock;
  * live features are rebuilt for that date (`LV.build(issue, write=False)`, so E139's stored file is untouched);
  * explanations are exact TreeSHAP with a sum check;
  * the class rule HIGH/LOW/UNCERTAIN follows the 90 % interval;
  * the output carries `claim`, `issue_quarter`, `display_lead`, `interval_note` and `explanation_method`;
  * LGU columns are named `priority_score*`, `priority_rank_in_region` and `status`.
* `backend/app/e140/serve.py`: the outlook flags `current: false` once the viewing quarter passes the issue quarter.
* `backend/app/e139/live.py`: optional `write` argument; default behaviour unchanged.
* `backend/app/registry/prospective_provincial.py`: NAT, PERS and REGPREV baselines; per-instrument scoring
  (HFIAS = confirmation, FIES = agreement); input column validation; confusion matrix and recall.
* `backend/app/e140/nlp_validity.py`: V4 volume-dependence test of the FSSI correction.

**Created.**
* `backend/data/registry/provincial_round_TEMPLATE.csv`.
* `docs/system/FINAL_DECISION_REPORT_20261104.md` (this file).
* Regenerated E140 candidate outputs (`forecast_next_quarter.json`, `lgus_next_quarter.csv`, `nlp_validity.json`).
  The seal is write-once and unchanged.

**Tests changed.** `backend/tests/unit/test_system_completion.py` adds:
* scorer baselines and instrument split;
* rejection of incomplete round files;
* the explanation sum check;
* the quarter clock;
* the stale-issue flag;
* LGU completeness and status.

**Intentionally unchanged.**
* Locked experiments, protocols and seals (FI5–FI9-Z, E137–E140).
* The registry production pointer (`null`).
* The CH1/P0H4 map layer and served LGU list (owner decision; labelled as price-pressure context).
* The dashboard design.

**API routes.**
* `/api/v1/quarters`: dynamic.
* `/api/v1/final/food-insecurity/outlook`: `validation_pending` with per-candidate `checks_total`.
* `/api/v1/admin/candidates/e140-lgbm-native-1.0/{outlook,evaluation,model,lgus,register}`: admin only.

**Tests executed.** See section D.1, filled in from the final run.

**Unresolved inconsistency (owner decision).** The served LGU list (CH1, `app/quarterly/lgu_audit.py`) uses 60/40
weights with min-max scaling inside each province. The candidate uses 50/50 region-wide percentiles. They are
different products, and the served one is labelled EXPERIMENTAL.

### D.1 Test results

(Recorded below by the final verification step.)

## E. Exact remaining external evidence

**1. A provincial HFIAS round not yet seen by any model.**
* **What:** moderate-or-severe % with its SE and the national value of the same round, for as many provinces as
  possible, at least 20 with at least 5 measured above national.
* **Sources:**
  * FNRI ENNS 2021 provincial results (the 2021 rolling round). They exist, but are not on FNRI's public eNutrition
    pages or in the Internet Archive (checked 2026-11-04).
  * Any later FNRI NNS with provincial HFIAS.
* **Format:** `backend/data/registry/provincial_round_TEMPLATE.csv` (province, survey, year, p, se_p, ref,
  instrument).
* **Scoring:** `python -m app.registry.prospective_provincial score <file>`. It scores E138, E139 and E140 against
  NAT, PERS and REGPREV on the same rows.
* **Confirmation rule (pre-stated here):** E140 EB below every baseline, and AUC ≥ 0.75 on decisive rows.
* A provincial FIES round would be scored as agreement only.
2. **Regional SWS releases** for 2026-Q4 onward, published by SWS. They are scored by `app/fi9/prospective.py`
   against the FI6 seals. FI9-Z's pre-set requirement: at least 12 quarters with at least 3 HIGH before a Lead-1
   claim.
3. **For quarter-to-quarter provincial forecasting:** a provincial food-insecurity measure taken at least quarterly
   (for example a PSA or FNRI quarterly FIES module). None exists today.

## F. Production decision

**CANDIDATE IMPLEMENTED — VALIDATION PENDING.**
* This matches the registry: `production: null`, E140 `rejected` by its development gate.
* It matches the API: the public outlook is `validation_pending`; the candidate is admin-only and flagged
  `CANDIDATE_NOT_APPROVED`.
* It matches the dashboard: no candidate number is shown; CH1 is labelled as price-pressure context.
* The candidate is complete as software:
  * it issues each quarter;
  * its outputs and explanations are consistent with the model;
  * its 142 LGU rows are complete;
  * its seals are registered for confirmation.
