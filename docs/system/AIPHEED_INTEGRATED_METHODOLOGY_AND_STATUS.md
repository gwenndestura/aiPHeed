# aiPHeed: integrated methodology, implementation and objective status (2026-11-04)

> **Superseded in part by [FINAL_DECISION_REPORT_20261104.md](FINAL_DECISION_REPORT_20261104.md).** Corrections:
> * The next-quarter output is a structural relative-risk estimate carried into the display quarter. Its evidence is
>   survey-to-survey, not quarter-to-quarter.
> * Explanations are exact TreeSHAP.
> * HIGH, LOW and UNCERTAIN follow the 90 % interval.
> * LGU columns are named `priority_score`.
> * The FSSI correction does not remove volume bias.
> * The prospective scorer now computes the NAT, PERS and REGPREV baselines.

**Evidence base.**
* Branch `pfi/survey-anchored-final`.
* No result here comes from a new model search. The selected methodology rests on locked studies (FI5, FI6, FI9-Z,
  E137–E140).
* New in this step:
  * an operational next-quarter issue of the E140 LightGBM;
  * a provincial prospective-validation register;
  * an NLP convergent-validity check;
  * one API correctness fix.

**Companion documents.** `docs/release/THESIS_OBJECTIVES_AUDIT_20261104.md` (FAO sources, dashboard audit) and
`docs/e137`–`docs/e140` (protocols and results).

---

## A. Why aiPHeed has not yet met all objectives (diagnosis)

| Problem | Type | Root cause (evidence) |
|---|---|---|
| A price-pressure index was served as the forecast | **Conceptual / target** | The CH1/P0H4 target is built from the same price indicators it predicts, so its 0.84–0.91 accuracy is circular (forensic audit 11-03, evidence class B) |
| Provincial quarterly validation is impossible | **Data** | Provinces have measured food insecurity only for 2015 and 2018/19 (HFIAS) and 2023 regional FIES. The 2021 ENNS provincial reports are not public online (FNRI archive checked 11-04: 2021 national and 2023 regional files only). |
| LightGBM does not beat persistence on regional hunger | **Data / statistical** | 74 % of SWS HIGH/LOW labels lie inside the survey's margin of error (FI5). With about 300 respondents per area per round, last quarter's reading is the best available predictor (FI6, FI8). |
| Quarterly indicators add nothing | **Data / empirical** | Price, climate and production changes do not explain measured within-province change: 19 % worse than "no change" (E138). Removing all of them from E140 changes nothing. |
| The provincial LightGBM is not significantly better than a linear model | **Statistical (sample size)** | 125 survey rows. E140's trees give −0.010 expected Brier vs the linear prior, CI [−0.031, +0.012]; confirming it needs about 4–5 times more independent rounds (E140). |
| Fails on an unseen island group | **Data** | 9 % of residual variance is island-specific, and no available feature explains it (E140 diagnosis) |
| Employment and news groups cannot be modelled by province | **Data** | No provincial labour or remittance series 2014–2019. The news archive covers CALABARZON queries only. |
| Utilization is missing | **Data** | No nutrition, water or sanitation series held |

## B. FAO-guided risk framework

**Definitions.** Verified against FAO texts (details in the companion audit, section 2):
* WFS 1996 definition;
* FAO Policy Brief 2006: availability, access, utilization, stability;
* SOFI 2001 glossary: vulnerability = risk factors plus the ability to cope.

**How the framework shapes the method.**
* **Risk = exposure × (in)ability to cope.**
  * Coping capacity is represented by poverty, subsistence and poverty gap. These are also the strongest measured
    signal (E138/E139).
  * Exposure is represented by:
    * access shocks: food and rice CPI, food-threshold cost;
    * availability shocks: palay/corn and fisheries production;
    * stability shocks: rainfall anomaly, cyclones, ENSO.
* **Not covered:**
  * Utilization: no data.
  * Employment and remittances: national only.
* **The framework is not used to assign weights.** Each group's weight is learned from measured outcomes and tested
  by ablation, never set equal.
* **Measured result:** poverty and measured history carry the signal. Market and climate add no measured information
  (E138 nested tests; E140 ablation and quarterly test).

## C. Selected risk target (what the model predicts)

### Comparison of approaches

| Criterion | A. Survey-anchored relative risk (HFIAS) | B. FAO composite index as target | C. Future adverse condition (e.g. regional SWS, assistance events) | D. Hybrid latent (survey + SWS + indicators) |
|---|---|---|---|---|
| FAO alignment | experience-based food insecurity (access/stability) | high on paper | SWS: severe hunger | high |
| Food-insecurity risk rather than price stress | yes | **no**: measured evidence shows its dynamic parts (prices, climate) carry no food-insecurity information (E138, E140) | SWS yes; assistance events = transitory shocks | partly |
| Provincial coverage | yes (78 provinces × 1–2 rounds) | yes | SWS: **region only** | provincial dynamics would be the regional series copied (forbidden) |
| Supports a next-quarter forecast | yes, as P(elevated) for Q+1; quarter-to-quarter changes are unsupported | only of the index itself | yes (regional) | no identifiable provincial dynamics |
| Independent validation | **yes**: held-out regions, forward rounds, prospective seals | **circular** unless validated against measured outcomes (it fails them) | SWS yes (persistence wins) | PFI v1.0 rejected (B6/B10) |
| Leakage or circularity risk | low (target ≠ predictors) | high | low | medium |
| DA interpretability | "province more likely above national food insecurity" | intuitive but unvalidated | regional only | complex |

**Selected: A**, with the regional SWS outlook kept as separate context (C, regional) and no composite target (B
rejected on evidence).

### The target

* **What is predicted:** P(the province's household food insecurity, HFIAS moderate-or-severe, is above the national
  level of the same survey). For each province and target quarter, the forecast is that probability for the quarter
  after the viewing quarter, using information public at the start of the viewing quarter.
* **Classes.** HIGH (P ≥ 0.5) means the evidence points to a greater potential for food insecurity than the national
  average. LOW means comparatively lower potential. Neither is a measured status.
* **Data used:**
  * FNRI 2015 FSS and ENNS 2018/2019 HFIAS, with survey errors and the pooled national reference (E137 audit);
  * predictors from PSA, NASA POWER and IBTrACS, release-dated.
* **Data excluded as labels:** SWS, FIES, CPI, poverty and news.
* **Why it is not circular.** The label is a household measurement that is never a predictor. Validation uses rows
  outside training: held-out regions, the next survey round, and sealed future rounds.
* **Limits:**
  * The quarterly dynamics of risk are not identified (no quarterly provincial measurement).
  * The Q+1 forecast therefore carries structural information plus the latest measurements. That is stated, not
    hidden.

## D. Integrated methodology (as implemented)

| Component | Implementation |
|---|---|
| Data processing and release dates | `app/e137/features.py`, `app/e139/live.py`. Annual CPI public on 15 Feb of the next year; poverty round R from 1 Jan R+2; production 45 days after the quarter; NASA monthly 30 days after the month; cyclones in real time. Missing values stay missing (never zero risk). |
| Target and uncertainty | `app/e137/outcomes.py`: relative logit, survey SE, soft label, ELEVATED / LOWER / NOT_DISTINGUISHABLE / INSUFFICIENT |
| LightGBM (primary) | `app/e140/model.py` LGBM-AUTO. Inside each training set, nested CV chooses linear trees or compact constant-leaf trees; zero trees not allowed. Final: **100 constant-leaf trees**. Features: poverty (3), history (2), island group, food CPI, cyclones. |
| Next-quarter issue | `app/e140/issue.py`. Target = viewing quarter + 1. Model trained on Lead-1 features (one quarter before each survey), the same information gap as the live issue. Outputs: P(elevated) per province, 90 % region-bootstrap interval, group effects with FAO dimension, plain sentences. |
| Baselines | E139/E140 (provincial): persistence, previous region level, national base rate, ridge, logistic, linear prior. FI6 (regional): persistence, PSA-only, NLP-only, logistic. |
| Validation | Geographic (LORO/LOPO/ISLAND); forward in time (V2, TFWD); prospective (`app/registry/prospective_provincial.py`, hash-chained seals for E138/E139/E140; `app/fi9/prospective.py` for regional SWS) |
| NLP | `app/fi5/nlp.py`, `app/fi6/news_events.py`. Convergent validity: `app/e140/nlp_validity.py`. |
| LGU rankings | `app/e140/issue.py`: province P × vulnerability (½ PSA SAE 2021 poverty percentile + ½ POPCEN 2024 density percentile, region-wide; equal weights because no outcome exists to fit them), with the province interval carried through. All 142 LGUs, labelled as a ranking. |
| Serving | Admin route `/api/v1/admin/candidates/e140-lgbm-native-1.0/{outlook,evaluation,model,lgus,register}`. Public `/api/v1/final/food-insecurity/outlook` serves E140 **only** if the registry approves it (the production server entry is in place). |

## E. Forecasting evidence (three kinds, kept separate)

**1. Measured-outcome and risk-estimation validation (provincial, against HFIAS; development evidence).**
* Held-out region (LORO): E140 AUC 0.960, accuracy 0.871 on 62 decisive rows, expected Brier 0.182, ECE 0.039.
* Benchmarks: linear prior 0.192; ridge 0.193.
* Regional agreement with FIES 2023: ρ 0.79 (E137).

**2. Next-round (forward-in-time) forecasting, provincial.**

| Test | n | LightGBM | Persistence | Previous region level |
|---|---|---|---|---|
| TFWD: train 2015 + 2018 → predict 2019 | 25 provinces, 19 decisive | AUC 0.971, accuracy 0.947, EB 0.148 | 0.188 | 0.161 |
| ENNS rows, LORO | 47 | **beats persistence significantly**: −0.136 to −0.024 (CI on EB difference) | — | — |

* At Lead 1, E139 gives TFWD AUC 0.857.
* **Limits:**
  * development data (the 2019 provinces were seen in earlier studies);
  * one forward round;
  * E140 rejected by its gate (decision C): trees are not significantly better than the linear prior, and it fails
    island transfer and the comparison with the previous region level.

**3. Next-quarter forecasting against a quarterly measured outcome (regional SWS, FI6, 62 quarters).**
* LightGBM, Lead 1: accuracy 0.839, HIGH recall 0.27, AUC 0.69, Brier 0.129. Persistence: 0.871 / 0.55 / 0.74 /
  0.116.
* At Lead 2, the dashboard's current timing, LightGBM has no skill (recall 0, AUC 0.47).
* **LightGBM does not beat persistence.**

**Maximum reliable horizon: none validated.**
* Provincial next-quarter forecasting: **cannot yet be validated**. No quarterly provincial measurement exists. The
  first confirmatory score comes from the sealed predictions when the next provincial round is published.
* Regional next-quarter forecasting with LightGBM: **not achieved**.

## F. Objective-by-objective status

| Objective | Status | Evidence | Remaining requirement |
|---|---|---|---|
| **1. XLM-R + BERTopic NLP; bias-corrected FSSI; latent patterns per province-quarter** | **PARTIALLY ACHIEVED** | Implemented (FI5: 9,628 headlines, 11 topics, province-quarter FSSI; FI6-N: 62,698 archive articles). Convergent validity (`nlp_validity.json`): archive risk share vs cyclones ρ 0.24 (p < 0.001, n = 349); FI5 climate FSSI vs cyclones ρ 0.05 (n = 120); FI5 market FSSI vs food CPI ρ 0.01 (n = 35). News helps regional Lead-1 Brier only (−0.0099). | Sentiment accuracy **cannot yet be validated**: needs a human-labelled set (excluded by owner rule); national news coverage for provincial modelling |
| **2. LightGBM with accuracy, precision, recall, F1, AUC; walk-forward; multiple leads; at least Lead 1** | Implementation **ACHIEVED**; Lead-1 validation **NOT ACHIEVED** (regional) / **CANNOT YET BE VALIDATED** (provincial) | Section E; FI6 RESULTS; E140 results | One confirmatory provincial round scored by the register; at least 12 prospective SWS quarters with at least 3 HIGH (FI9-Z rule) |
| **3. LGU rankings from validated province forecasts (PSA poverty, density)** | **PARTIALLY ACHIEVED** | 142 LGUs, vulnerability-weighted, with interval, from the E140 provincial forecast (`lgus_next_quarter.csv`) | The province forecast must pass validation first. Until then the ranking inherits candidate status. |
| **4. LightGBM vs persistence, PSA-only, NLP-only, logistic** | **ACHIEVED** (comparison) | Regional FI6: LightGBM beats PSA-only and logistic in Brier, ties NLP-only, loses to persistence. Provincial E140: beats persistence (significant) and the base rate (significant); lower expected Brier than logistic regression (0.182 vs 0.212, E139 run on the same folds; not bootstrapped against E140); ties ridge and the linear prior. NLP-only cannot be built provincially. | — |

## G. Implementation in this step

**New:**
* `backend/app/e140/issue.py`: next-quarter candidate issue (forecast, explanations, LGUs, write-once seal).
* `backend/app/e140/serve.py`: admin candidate views.
* `backend/app/e140/nlp_validity.py`: NLP convergent validity.
* `backend/app/registry/prospective_provincial.py`: hash-chained provincial register and scorer, with
  `score <round.csv>`.
* Data:
  * `backend/data/e140/out/{forecast_next_quarter.json, lgus_next_quarter.csv, sealed_prediction_2026-10-01.json, nlp_validity.json}`;
  * `backend/data/registry/prospective_provincial.jsonl` (E138, E139 and E140 seals).
* Tests: `backend/tests/unit/test_system_completion.py`.

**Changed:**
* `backend/app/api/v1/registry.py`:
  * E140 candidate route and gated production server;
  * per-candidate `checks_total` instead of a constant 16.
* `backend/app/registry/__init__.py`: `checks_total` in the summary.
* `frontend/src/components/FoodInsecurityStatus.tsx` and `frontend/src/lib/apiTypes.ts`: the existing sentence uses
  each candidate's own check count. Text only; no new element.

**Unchanged:** the CH1/P0H4 map layer (owner decision), the dashboard design, and the registry production pointer
(`null`).

## H. Final system acceptance

| # | Requirement | Status |
|---|---|---|
| 1 | Food-insecurity risk estimated with a defensible FAO-guided framework | **ACHIEVED** (framework and survey-anchored target); utilization missing |
| 2 | Philippine indicators used appropriately (release dates, no fabricated labels) | **ACHIEVED** |
| 3 | NLP outputs produced | **ACHIEVED**; accuracy **CANNOT YET BE VALIDATED** |
| 4 | LightGBM used as the forecasting model | **ACHIEVED** (E140: 100 trees) |
| 5 | All four baselines evaluated | **ACHIEVED** (regional all four; provincial three, NLP-only not buildable) |
| 6 | Genuine next-quarter forecasting ability demonstrated | **NOT ACHIEVED** regionally; **CANNOT YET BE VALIDATED** provincially (forward-round development evidence is favourable; confirmation pending) |
| 7 | Maximum reliable horizon determined | **ACHIEVED**: none validated |
| 8 | Provincial risk estimates | **ACHIEVED** as a candidate (admin route); not released |
| 9 | 142 LGU vulnerability-weighted rankings | **ACHIEVED** as a candidate; labelled; not released |
| 10 | Next quarter computed dynamically | **ACHIEVED** (`/api/v1/quarters`; E140 issue targets viewing quarter + 1) |
| 11 | Results communicated as risk, not confirmed food insecurity | **ACHIEVED** in API text; dashboard text partly (audit section 10) |
| 12 | Only correctly labelled outputs exposed | **ACHIEVED**: public outlook `validation_pending`; candidates admin-only; CH1 labelled as price-pressure context |

**Minimum additional evidence to complete objectives 2, 3 and acceptance item 6.**
1. **One new provincial food-insecurity round** that no model has seen. Options:
   * FNRI ENNS 2021 provincial results (they exist but are not online);
   * a future FNRI NNS with provincial estimates;
   * PSA provincial FIES.

   Scoring is one command: `python -m app.registry.prospective_provincial score <round.csv>`. It scores the E138, E139
   and E140 seals against persistence-type baselines.
2. **Prospective SWS quarters** for the regional outlook (FI9 register). The first is 2026-Q4, expected in early
   2027.
3. **Owner decision** on the CH1/P0H4 price-pressure map layer.
