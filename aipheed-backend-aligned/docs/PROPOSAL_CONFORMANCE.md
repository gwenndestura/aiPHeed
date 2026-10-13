# Proposal Conformance Audit

What this folder is, and what changed to get here.

`aipheed-backend-aligned/` is the backend revised to follow the approved thesis
proposal (*aiPHeed: An Interactive Web-Based Geospatial Food Insecurity
Forecasting System … Using NLP and Machine Learning*, May 2026) strictly. It was
built by copying `backend/app`, comparing every methodological step against
Chapters I and III, and correcting each place where the implementation had
drifted. The original `backend/` is untouched.

Every discrepancy below was resolved **in favour of the approved methodology**.
No new methodology was introduced. Where the approved process and the
implementation disagreed, the implementation changed.

---

## 1. Deviations found and corrected

### 1.1 Algorithm 1 — zero-shot scoring diverged on four points

**Approved (Section 3.4, Algorithm 1; Section 3.3.2.1):** clean HTML, concatenate
title and summary, truncate to **512 characters**; score against **ten bilingual
HungerGist hypotheses**; the article's score is the **maximum entailment
probability across all ten**; drop articles scoring **below 0.30**.

**Found in `backend/app/ml/nlp/classifier.py`:**

| Approved | Implemented | Status |
|---|---|---|
| Truncate to 512 characters | `PREMISE_CHARS = 250` | corrected |
| Max entailment over **all ten** hypotheses | Max over a 5-hypothesis `CORE_TOPIC_IDS` subset only | corrected |
| Single gate: score ≥ 0.30 | Second gate added: `RELEVANCE_MARGIN = 0.20` (best core score must beat best non-core by 0.20) | corrected — removed |
| Ten **bilingual** hypotheses | Ten English-only hypotheses, rephrased from the approved entailment claims to "This article is about X" topical form | corrected |

The code labelled the CORE restriction a "deviation, kept per decision" in its
own comment. The revised module restores all four: 512-character premise, max
over all ten, the 0.30 threshold as the only gate, and ten hypotheses each
stated in English and Filipino (the higher of the two entailment scores is that
hypothesis's score, so the dimension count stays at ten).

### 1.2 FSSI averaged every article, not the retained ones

**Approved (Algorithm 1; Equation 2):** "Exclude articles scoring below 0.30 from
aggregation." Equation 2's `N` is "total retained articles … after quality
filtering."

**Found:** `compute_fssi()` averaged *all* geocoded articles regardless of score.

**Corrected:** the 0.30 threshold is applied inside `compute_fssi()` before
aggregation, and the retained count is logged.

### 1.3 Training window was not the approved window

**Approved (Sections 3.3.1.1, 3.3.2.6):** corpus covers January 2020 – December
2025; the fused matrix is a **120-row backbone grid, 5 provinces × 24 quarters,
2020-Q1 to 2025-Q4**, producing a **120 × 45** matrix.

**Found:** `MODEL_START_YEAR = 2021` with the end tracking the calendar
(`last_completed_quarter()`), giving 2021-Q1 – 2026-Q2 = **110 rows**.

**Corrected:** the window is a methodological constant again. The rebuilt matrix
is **120 rows × 45 feature columns**, 2020-Q1 – 2025-Q4 — exactly Section 3.3.2.6.
`last_completed_quarter()` is retained but now only names the cycle for the
quarterly scheduler; it no longer sets the training window.

### 1.4 Missing-value handling contradicted the approved rule

**Approved (Section 3.3.2.6):** "Sparse series will be forward-filled within each
province; remaining gaps will be zero-filled."

**Found:** forward fill applied to a hand-picked list of 11 columns; the
remaining gaps were deliberately left as NaN for LightGBM to split on, with only
trigger and climate-count columns zero-filled.

**Corrected:** forward fill within province across every numeric column, then
zero-fill every remaining gap, as approved. `feature_provenance.json` records
what was filled — this is a log, not a change to any value.

### 1.5 Section 3.3.2.7 feature selection was never implemented

**Approved:** a two-stage process applied after fusion and before training —
(1) pairwise Pearson correlation filtering, dropping the weaker-to-label member of
any pair at |r| > 0.85; (2) SHAP-ranked backward elimination under the same
walk-forward CV used for final evaluation, removing the lowest-ranked feature one
at a time while validation F1 does not decline, with a **floor of 10 and a
ceiling of 15**. Applied to the 45 candidates, it retains **12 features**.

**Found:** no such module anywhere in `app/`. `backend/scripts/select_top_features.py`
used a different procedure — LightGBM *gain* importance averaged over 10 seeds —
and the resulting list was then hand-edited ("slots RESERVED for the NLP signal").

**Corrected:** new module `app/ml/features/feature_selector.py` implements both
approved stages and writes the outcome to `data/processed/selected_features.json`,
so the retained set is reproducible and auditable rather than asserted. The
12-feature set the proposal reports is recorded as `EXPECTED_FINAL_FEATURES`; the
runner compares against it and reports any difference instead of overriding the
process.

### 1.6 The trained model used a different feature vector

**Approved (Equation 5; Section 3.3.2.7):** the 12 features are FSSI, FSSI_lag1,
FSSI_lag2, FSSI_accel; the five trigger proportions (market, climate, employment,
OFW remittance, fish kill); and food CPI deviation, unemployment rate, and
quarter-over-quarter rice price change.

**Found in `backend/app/ml/training/trainer.py`:** a hardcoded 20-column
`FEATURE_COLS` that differed from the approved vector on every axis:

| Approved feature | Status in the old trainer |
|---|---|
| `food_cpi_yoy` (CPI_dev, Equation 5) | **excluded** as `LEAKY_LABEL_FEATURES` |
| `trigger_market`, `trigger_employment`, `trigger_ofw_remittance`, `trigger_fish_kill` | **absent** — only `trigger_climate` kept |
| `unemployment_rate` | replaced by `unemployment_rate_lag1` |
| rice change | replaced by `rice_price_regular_lag1` |
| — | `label_lag1`, `label_lag2`, `quarters_since_flip` **added** (lagged-label features, in no approved equation) |
| — | `commodity_livestock`, `commodity_leafy_veg`, `commodity_fruit_veg`, `headline_cpi`, `diesel_php_per_l_lag1`, `ofw_remit_yoy_pct_lag1`, `rainfall_anomaly_pct_lag1/accel` **added** |

**Corrected:** the trainer trains on Equation 5's vector. The Section 3.3.2.7
process is implemented and runs, and its outcome is recorded as the audit trail;
where the two differ — as they do on this data, the process retaining 15
features and dropping all five trigger proportions — Equation 5 wins, because
its variable legend names the arguments of F[.] and the Components block of both
Algorithm 3 and Algorithm 4 reads "Input: 12-feature matrix". The difference is
logged on every run. On the holdout the approved twelve also outperform the
process set (accuracy 0.85 vs 0.70, AUC 0.889 vs 0.472 at default parameters),
which is recorded in `data/processed/feature_set_comparison.json` so the choice
is not mistaken for one made on the score. The lagged-label features are gone — the approved feature vector
does not include the target's own history. Food CPI deviation is restored:
Equation 5 names `CPI_dev(t)` explicitly and Section 3.3.2.7 retains it among the
final twelve, so the approved design feeds it to the model.

> The exclusion was argued in the old code as label leakage, because SWS hunger
> is constant across provinces in a quarter and the CPI deviation term therefore
> carries all province-level variation in the label. That is a real observation
> about the approved label, and it is recorded in `docs/DATA_AVAILABILITY.md`.
> It is not grounds for the backend to drop an approved input on its own — that
> is a methodology change, and per the task's instruction the discrepancy is
> resolved in favour of the proposal. `pct_total_hunger` itself stays excluded
> from the feature matrix, which the proposal's own design implies.

### 1.7 Algorithm 3's halting rule had an extra criterion

**Approved:** record `k` when mean fold accuracy meets 75%; halt at the first `k`
that does not; return the last passing `k`.

**Found:** additionally computed a persistence baseline per fold and a "skill"
margin, with warnings framing the approved 75% threshold as "weaker than the
naive baseline — report skill, not raw accuracy."

**Corrected:** Algorithm 3 now records accuracy, precision, recall, F1 and
AUC-ROC per `k` — the five metrics the approved algorithm names — and halts on
the approved criterion alone. Persistence remains a **baseline** in the
evaluator, where Research Question 3 puts it.

### 1.8 Algorithm 4's search space had been narrowed

**Approved:** nine hyperparameters, a 100-trial TPE study, objective = mean
weighted F1 across walk-forward folds, one holdout evaluation on the last four
quarters, targets F1 ≥ 0.75 and AUC-ROC ≥ 0.80, serialize to `lgbm_best.pkl`.

**Found:** the nine parameters and 100 trials were present, but the ranges had
been tightened to the 110-row matrix (`num_leaves` 2–8, `max_depth` 2–4,
`reg_alpha` from 1e-3). The objective had been switched to a composite
0.6·F1 + 0.4·AUC and then back to F1.

**Corrected:** ranges restored to a standard LightGBM search space, objective is
mean weighted F1 as approved. The serialized bundle now carries the model, the
selected feature list and the discovered lead time together, so serving cannot
drift from training.

### 1.9 The serving layer predicted a different target entirely

This was the largest deviation.

**Approved:** a LightGBM **binary classifier** predicting HIGH/LOW food
insecurity risk per **province-quarter**, trained on the composite SWS + food-CPI
stress label (Equation 3), served at the Maximum Reliable Lead Time.

**Found:** `predictor.py` and `forecaster.py` served a **"food-availability shock
model"** — an ensemble predicting production shortfall against a seasonal
baseline at province × quarter × **commodity** resolution, from PSA OpenStat
production volumes. `risk_probability` was the *share of a province's monitored
commodity series flagged*. The only model files present were
`food_availability_model.joblib` and `food_availability_forecast_model.joblib`;
`lgbm_best.pkl` did not exist. The predictor's own docstring recorded the swap:
"The target changed on 2026-09-01."

This target appears nowhere in the approved proposal. No research question,
hypothesis, objective, equation or algorithm refers to production shortfall,
seasonal baselines or commodity-series risk.

**Corrected:**
- `predictor.py` rewritten to serve `models/lgbm_best.pkl` — the approved
  province-level classifier — returning `risk_probability` as the modelled
  probability of the HIGH class (Equation 5).
- `forecaster.py` **deleted**: it served the second food-availability model.
- `explainer.py` rewritten onto the served LightGBM, so Equation 7's additive
  decomposition (`phi_0 + Σ phi_j = predicted probability`) reproduces the
  forecast exactly instead of approximating an ensemble.
- `feature_display.py`: the `series_history` and `seasonal` driver groups and
  their commodity features removed.
- `dashboard.py`, `report.py`, `insights.py`, `schemas/public.py`: the indicator
  definition, PDF copy and response text now describe the approved target.

### 1.10 Rule 2 was violated by a two-model, two-horizon design

**Approved (Rule 2, Single Forecast Horizon):** "One LightGBM model will be
evaluated across multiple forward-looking lead times … The furthest lead time at
which the model achieves reliable classification performance … will be adopted as
the operational forecast horizon."

**Found:** two models served side by side behind a `horizon` parameter —
`nowcast` (same-quarter) and `forecast` (one quarter ahead) — each with its own
serialized bundle and its own results file.

**Corrected:** one engine, one horizon. `nowcast` is retained as an accepted
alias so the published frontend contract does not break, and both ids resolve to
the same model at the Maximum Reliable Lead Time.

### 1.11 Rule 7's alert trigger was a different rule

**Approved (Rule 7; Figure 3.6.2):** "An alert will fire when a province's
forecast exceeds the rolling historical threshold."

**Found:** a sudden-rise rule — `risk_delta >= 0.15 AND current_prob >= 0.35`.

**Corrected:** `detect_alerts()` compares each province's probability against its
own rolling historical threshold (trailing 8 quarters, mean + 1σ, minimum 4
quarters of history). The previous quarter's probability and the delta are still
recorded on the staged row as reviewer context, and the `AlertRecord` columns are
unchanged. Alerts remain STAGED; nothing publishes without confirmation.

### 1.12 Rule 6's forecast labelling was missing

**Approved (Rule 6):** "Every forecast will include an explicit horizon label,
confidence statement, and verification date."

**Found:** none of the three on any forecast record or API response.

**Corrected:** `forecast_horizon_quarters`, `horizon_label`,
`confidence_statement` and `verification_date` are attached to every forecast and
carried through `dashboard.py`, the province/region API responses and the PDF
report.

### 1.13 APScheduler automation (Rule 1) was never built

**Approved (Sections 3.1, 3.5; Figure 3.6.1 Automatic Scheduler actor; Rule 1):**
APScheduler automates quarterly retraining and forecasting; the scheduler runs
the collection step automatically and needs no human initialization.

**Found:** `app/tasks/` contained only `__init__.py`. `main.py`'s lifespan said
"Scheduler and model loading will be added in Week 14". No reference to
APScheduler anywhere in the codebase, though it is pinned in `requirements.txt`.

**Corrected:** `app/tasks/scheduler.py` registers the quarterly cron job and is
wired into the FastAPI lifespan; `scripts/run_quarterly_pipeline.py` runs the
full cycle in the order of Figure 3.6.2. The scheduler stages outputs only —
publication still requires administrator confirmation (Figure 3.6.3).

### 1.14 Experimental scripts outside the approved methodology

`backend/scripts/` held ~150 scripts, including a complete parallel modelling
track (`build_food_availability_panel.py`, `train_food_availability.py`,
`train_food_availability_v2.py`, `tune_food_availability.py`,
`build_fisheries_shock_label.py`, `train_fisheries_shock.py`,
`train_forecast_model.py`) plus accuracy/threshold/climate/price experiments.

**Corrected:** none of these were carried into this folder. `scripts/` holds only
what the approved pipeline runs: `run_quarterly_pipeline.py`,
`refresh_all_sources.py`, `create_admin.py`.

### 1.15 The forecast state machine had three states, not the approved four

**Approved (Figure 3.6.3):** a forecast record moves through **PENDING →
STAGED → PUBLISHED → ARCHIVED**. Entry into PENDING is triggered by the pipeline
start command; the record moves to STAGED once the forecast completes; an
administrator's acceptance moves it to PUBLISHED, and a rejection **returns it
to PENDING**. A PUBLISHED record becomes ARCHIVED the following quarter,
"indicating that the previous version has been replaced, though it will remain
accessible via the historical forecasts endpoint."

**Found:** `STATUSES = ("Staged", "Approved", "Rejected")`. PENDING and ARCHIVED
did not exist, `Approved` stood in for PUBLISHED, and a rejection moved the
record to a terminal `Rejected` state rather than returning it to PENDING. A
published forecast was never archived when its successor published.

> An earlier revision of this document listed this state machine as already
> conformant. That was wrong — the claim was made from the presence of a review
> table without checking the status vocabulary against Figure 3.6.3.

**Corrected:** `app/services/review.py` now implements the four approved states.
A record is seeded PENDING and advances to STAGED once a forecast is attached;
`approve()` moves it to PUBLISHED and archives that province's earlier published
quarters; `reject()` returns it to PENDING while keeping the reason, notes and
actor on the row. A PENDING row carrying a rejection reason is what "withheld"
means publicly — which preserves the `forecast_withheld` disclosure the previous
design provided — and a PENDING row without one is simply awaiting its forecast.
Archived rows stay in the table and stay reachable through the historical
endpoint, as the proposal requires.

Verified by driving the transitions directly:

```
1. seeded          : ['Staged'] (2 rows)
2. after approve   : Published
3. earlier quarter : Archived | newer: Published
4. after reject    : Pending | reason: Data quality issue
   withheld pairs  : {('cavite', '2025-Q1')}
5. after restore   : Staged | reason: None
```

This changes the `status` string the admin API returns (`Approved` → `Published`,
`Rejected` → `Pending` plus a reason). The change is required for conformance
with an approved figure, and the rejection reason is already carried separately
in the response, so a client can distinguish withheld from unscored.

### 1.16 Stale driver groups in the explainability surface

`insights.py` and `dashboard.explainability()` still described "seven groups"
including `seasonal` and `series_history` — the commodity-series groups the
food-availability model needed. Equation 5 has no commodity history and no
annual-cycle terms, so nothing feeds them. Both now describe the five groups of
the approved feature vector.

### 1.17 The expert-annotation workbook had been pruned

Section 3.7 provides that the system evaluators "will also serve as domain
expert annotators during dataset development, using their expertise to label and
verify training data". `build_annotation_workbook.py` implements this — blind
and anchored reviewer sets, a recall probe seeded with audit-removed articles,
and an annotator-credentials sheet for the validity annex. It was dropped in the
first pass when the ~150 experimental scripts were pruned; that was an
over-prune, and it is restored, with its reviewer framing updated to DA IV-A and
DEPDev IV-A.

### 1.18 The Admin's "trigger the quarterly pipeline" use case was missing

**Approved (Figure 3.6.1):** the Use Case Diagram gives the administrator a Run
Quarterly Pipeline case, with an «include» relationship to Collect Data, "since
no forecast can be produced without first gathering that quarter's news and
government data".

**Found:** the admin API exposed the review queue, the audit trail and feedback,
but no way to start a cycle. The only trigger was the scheduler, which did not
exist either (see 1.13).

**Corrected:** `POST /api/v1/admin/pipeline/run` starts the cycle and
`GET /api/v1/admin/pipeline/status` reports it. Both sit behind the admin gate.
A cycle runs far longer than a request, so the endpoint returns 202 and the work
continues on a worker thread; a second concurrent run is refused, since two
cycles would write the same parquets and the same review queue. It runs the
same `run_pipeline()` the scheduler runs and writes the same
`pipeline_run.json`, so the manual and scheduled paths are one pipeline rather
than two. Its outputs are STAGED like any other.

### 1.19 The language detection filter was not an explicit step

**Approved (Figure 3.6.2, News Data Track):** "A language detection filter will
then be applied to retain only Filipino and English articles, discarding those
outside the intended linguistic scope."

**Found:** no such step. Language scoping happened only at collection — GDELT's
query carries `sourcelang=english tagalog`, Google News is queried in English
and Tagalog, and the RSS fetcher reads an allowlist of Philippine outlets. That
is effective, and arguably the stronger place for it, but the flowchart names a
filter and there was none.

**Corrected:** `app/ml/corpus/language_filter.py` implements it, applied after
text extraction and before geocoding as the flowchart places it.

Detection is by script rather than by classifier: English and Filipino are both
Latin-script, so predominantly non-Latin text is out of scope by construction.
That rule needs no model or new dependency and is auditable. A word-frequency
classifier would be worse here — Philippine headlines are short, code-switch
between English and Filipino mid-sentence, and carry place names belonging to
neither vocabulary.

Measured on the current corpus it removes **0 of 1,684** articles, which is what
the collection design predicts. The count is reported by every run rather than
assumed. Rule behaviour was checked directly:

```
  OK   japanese         non_latin=1.00  in_scope=False
  OK   russian          non_latin=1.00  in_scope=False
  OK   arabic           non_latin=1.00  in_scope=False
  OK   mixed EN+name    non_latin=0.10  in_scope=True
```

### 1.20 Early warning alerts had no interface at all

**Approved (Rule 7; Figures 3.6.1 and 3.6.3):** an alert fires when a province's
forecast exceeds its rolling historical threshold, and "human confirmation will
be required before [the partner agency] is notified". The administrator
"confirms or dismisses alert notifications before they are displayed on the
dashboard"; the evaluator and the public "review active early warning alerts
that have passed administrative review". A dismissed alert "will remain in the
records for audit but will not be shown publicly".

**Found:** `app/db/repository/alert_repo.py` implemented the whole thing —
`get_staged`, `get_confirmed`, `confirm`, `dismiss` — and **nothing called it**.
No route exposed alerts to an administrator or to the public. Rule 7's human
confirmation step had no interface, and the alert half of Figure 3.6.3 was
unreachable.

**Corrected:** `app/api/v1/alerts.py` exposes the repository that already
existed:

| Route | Who | Purpose |
|---|---|---|
| `GET /api/v1/admin/alerts?status=` | admin | the queue, by state |
| `POST /api/v1/admin/alerts/{id}/confirm` | admin | STAGED → CONFIRMED |
| `POST /api/v1/admin/alerts/{id}/dismiss` | admin | STAGED → DISMISSED |
| `GET /api/v1/alerts` | public | confirmed alerts only |

The public route serves confirmed alerts and nothing else, so no warning reaches
the dashboard without a human decision. Confirming a dismissed alert, or
dismissing a confirmed one, is refused. Every decision writes an `AuditRecord`
in the same transaction.

Verified against the state diagram:

```
1. staged after detection : 3      public sees: 0
2. after confirm + dismiss: staged 1, confirmed (public) 1
   total rows retained    : 3      dismissed row kept for audit
3. confirm on a dismissed alert: False -> False
```

### 1.21 `rainfall_anomaly_pct` was an empty column, and it broke three baselines

**Found during the first training run.** Three of the six Research Question 3
baselines failed on **every fold**: the two logistic variants with
"Input X contains NaN" and the government-only LightGBM with "pandas dtypes must
be int, float or bool". Their reported figures came from zero successful folds
and were meaningless.

The cause was `rainfall_anomaly_pct` (and its lag and acceleration): dtype
`object`, **100% null**, because `province_rainfall.parquet` had been left
behind when the experimental scripts were pruned and the PAGASA loader fell back
to a series that produced nothing. Being object dtype it escaped both clauses of
the Section 3.3.2.6 fill rule, which operate on numeric columns — and it escaped
the consistency check, which tested `select_dtypes("number")` for NaN and so
reported the matrix clean.

**Corrected three ways:**

1. The real file was restored — 710 rows of NASA POWER province rainfall,
   5 provinces, 1991–2026. `rainfall_anomaly_pct` now carries measured values
   for 110 of 115 province-quarters.
2. `feature_matrix.py` coerces every feature column to numeric *before* the fill
   rule runs, so a dead source yields zeros the rule accounts for and logs,
   rather than an invisible column of `None`.
3. `verify_consistency.py` now checks **every** feature column for NaN, asserts
   every column is numeric, and flags any column that is entirely constant — the
   signature of a dead source.

All six baselines now run on all 11 folds. This is the defect that would have
been hardest to catch from the output alone: the pipeline reported "120 × 45,
no NaN" throughout while one of the 45 was empty.

### 1.22 Evaluation analyses outside the approved methodology were removed

During verification I added four analyses the proposal does not specify: an
eight-seed stability run, McNemar exact tests, paired bootstrap confidence
intervals, and a sample-size power analysis. I then used the significance test
to change H3 from *partially supported* to *not supported*.

None of that is approved. Section 3.4.4 and Specific Objective 2 define the
evaluation completely: accuracy, precision, recall, F1-score, AUC-ROC,
walk-forward expanding-window cross-validation, and the thresholds of 75%
accuracy, F1 >= 0.75 and AUC-ROC >= 0.80. Research Question 3 asks how the model
*compares* against six baselines, which the five metrics answer directly.

I then kept class balances, confusion matrices and majority-class rates as
"description" of the approved evaluation sets. That was rejected on the same
grounds: Specific Objective 2 names five metrics and Section 3.4.4 names three
thresholds, and anything that changes how a reported figure is judged is part of
the evaluation whether or not it is called a method.

**Corrected.** The thesis chapter, `METRICS.md`, the API and the PDF report the
approved evaluation only: the five metrics, the Maximum Reliable Lead Time, the
six-baseline comparison, the SHAP attribution, and the three thresholds. H3 is restored to **partially supported**, which is
what the approved comparison yields: the combined model records the highest
accuracy, precision, recall and F1 of the seven models and is surpassed on
AUC-ROC by the government-indicators-only variant.

The scripts moved to `scripts/supplementary/` and their outputs to
`data/supplementary/`, each with a README stating that nothing there is
approved, served, or reported, and that it cannot be used to change a result or
a hypothesis verdict. They are kept because they were run and their results are
real.

### 1.23 A verification that passed: the 45-column composition

Section 3.3.2.6 lists ten joined sources including SWS hunger, which raised the
question of whether excluding `pct_total_hunger` from the matrix was a
deviation. It is not. The stated 45 columns decompose exactly as:

| Block | Columns |
|---|---|
| FSSI and its lags and acceleration (3.3.2.4) | 4 |
| Trigger proportions (Algorithm 2) | 5 |
| Lag and acceleration over seven designated series (3.3.2.5) | 14 |
| Base indicator columns | 22 |
| **Total** | **45** |

Adding SWS hunger as a feature column would exceed the 45 the same sentence
specifies, and Equation 3 makes `sws_hunger(t)` a term of the label, so carrying
it as a feature would be leakage. The exclusion is required by the proposal
rather than a departure from it. A minor bug in `verify_consistency.py` was fixed
alongside this: a quarter-constant feature count computed over the model vector
was being compared against the length of the selection record, two lists of
different size.

---

### 1.24 Provincial food CPI was being overwritten by a region-level copy

**Approved:** Section 3.3.1.2 sources provincial indicators from PSA OpenStat
and RSSO IV-A. Equation 3 indexes food CPI by province, `food_cpi_yoy(p,t)`, and
Equation 5 names `CPI_dev(t)` among the model's per-province inputs.

**Found:** `feature_matrix.py` merged two food CPI sources and gave the wrong
one precedence. `psa_indicators.parquet` comes from OpenStat table
`0012M4ACP23`, queried per province, and varies across provinces in all 24
quarters. `cpi_full.parquet` comes from table `0012M4ACP22`, queried at the
Region IV-A geocode and cross-joined onto the five provinces — its own
`source_note` reads "Region IV-A inherited to provinces" — so it is identical
across provinces in all 26 quarters it covers. The merge let the region copy
win, with the comment "the live CPI wins over the stale psa_indicators copy".

The effect was specific and large. `food_cpi_yoy` reached the model as a
region-level constant: 24 distinct values across 120 rows, cross-province
correlation 1.000. In 2024-Q2 every province was handed 4.331 where the real
provincial figures were Cavite 3.900, Laguna 3.667, Quezon 8.633, Rizal 4.700,
Batangas 4.400.

The label was never affected — `label_generator.py` reads the provincial source
directly — so the label was built from provincial CPI while the model was shown
a regional one. Since every other term in Equation 3 is constant within a
quarter, provincial food CPI deviation is the *only* thing that separates
provinces inside a quarter. The model was denied exactly that.

**Why the override existed:** to carry food CPI past 2025-Q4, where
`psa_indicators` stops. Section 3.3.2.6 fixes the window at 2020-Q1 to 2025-Q4,
so no row it was meant to fix is inside the approved window.

**Changed:** the precedence is reversed. The provincial source wins and the live
region-level series fills only what it leaves empty, which inside the approved
window is nothing. Four columns moved — `food_cpi`, `food_cpi_yoy` and the two
derived from it — and every other column is byte-identical. `food_cpi_yoy` now
varies across provinces in all 24 quarters and matches the label's source
exactly. Labels rebuild byte-identical.

**Effect on results, reported in full because it was not favourable:** measured
on the same folds with the same code, accuracy fell and AUC-ROC rose.

| | before (region CPI) | after (provincial CPI) |
|---|---|---|
| Lead-time scan, k=1 accuracy | 0.7000 | 0.4000 |
| Holdout accuracy | 0.9000 | 0.6000 |
| Holdout F1 | 0.8526 (target met) | 0.6762 (target not met) |
| Holdout AUC-ROC | 0.7500 (target not met) | 0.9028 (target met) |
| RQ3 combined-model accuracy | 0.8364 | 0.6909 |

Every model that uses no CPI feature — naive persistence and both NLP-only
baselines — is unchanged to four decimals, which isolates the cause.

The "after" column records the effect of *this* correction alone. Entries 1.28
and 1.29 moved several of these figures again; `docs/METRICS.md` carries the
current values.

The earlier figures were higher for a reason that does not survive inspection.
A region-level CPI is a pure time series, and the composite stress label is
dominated by its own time component, SWS hunger, which is constant within each
quarter. The regional CPI was therefore an unusually clean proxy for the part of
the label the model is otherwise forbidden to observe. On the four-quarter
holdout the old model predicted a single class for all twenty rows; the
corrected model predicts thirteen positive and seven negative. The higher score
came from a constant predictor, not a better model.

A further effect was to un-collapse the model. Under the region-level CPI the
tuned model split on two features only, and every NLP feature recorded exactly
zero SHAP attribution. It now splits on seven of twelve, and the NLP-derived
features carry 16.8% of attribution.

---

### 1.25 Training results were written by the pipeline script, not by training

**Approved:** Section 3.4.4's metrics are what the system reports. The brief
requires that the dashboard and the PDF match the actual backend results.

**Found:** `train_model()` wrote `models/lgbm_best.pkl` but not
`data/processed/training_results.json`. Only `run_quarterly_pipeline.py` wrote
that file, although `dashboard.py` documents it as "written by
trainer.train_model()" and the README offers training as a standalone command.
Training through any entry point other than the pipeline therefore left the
dashboard and the PDF serving the *previous* run's metrics against the *current*
model. This had happened: the results file was eight hours older than the model
bundle and still reported the pre-correction figures.

`verify_consistency.py` could not catch it. It compared the API against
`training_results.json` — both reading the same stale file — and so passed
32/32 while the served metrics described a model that no longer existed.

**Changed:** `train_model()` writes the results file beside the model bundle, in
the same call. `verify_consistency.py` gained three checks that anchor the file
to the model actually on disk (feature list, hyperparameters, horizon) rather
than only to the API. Re-run against the stale file the new checks failed, as
intended; after retraining, 35/35 pass.

---

### 1.26 The model's own row in the RQ3 comparison came from outside the repository

**Approved:** Research Question 3 compares aiPHeed against six baselines.

**Found:** `evaluator.py` built the six baselines but never the model's own row,
despite its output noting "LightGBM results added by trainer.py" — which
`trainer.py` does not do. The combined-model figures reported for RQ3 came from
a scratch file, `model_on_baseline_folds.json`, that nothing in the codebase
reads or writes. The headline RQ3 claim was therefore not reproducible from the
repository.

**Changed:** the model is evaluated as `aipheed_lgbm_combined` inside
`run_baseline_evaluation`, through the same `_lgbm_fold`, on the same folds, at
the same gap, with the same hyperparameters and class weighting as the
baselines. Validation: run against the pre-correction feature matrix, the new
code path reproduces the scratch file's 0.8364 / 0.8369 / 0.8134 exactly, so the
change restores reproducibility without altering the measurement.

---

### 1.27 Feature selection could see the holdout

**Approved:** Section 3.3.2.7 specifies correlation filtering then SHAP backward
elimination. Rule 3: "All features will derive exclusively from data available
before the forecast period." Algorithm 4 reserves the last four quarters.

**Found:** `select_features()` ran over every labelled row, including the four
holdout quarters. A feature set is a fitted decision, so choosing it with the
holdout in view leaks the holdout into the final evaluation.

This was latent rather than active, because the model trains on Equation 5's
fixed vector and not on the selection output. It became live the moment the
selection output was considered as the model input, which is how it surfaced.

**Changed:** `select_features()` withholds the same four quarters Algorithm 4
reserves. The procedure is untouched — same filter, same elimination, same floor
of 10 and ceiling of 15 — and only the data it may see is restricted. On 75 rows
it retains ten features rather than twelve.

**This mattered to a decision.** Section 1.6 records that Equation 5's vector is
used rather than the selection output, partly because it performed better. On
the corrected CPI data the selection output appeared to overtake it, scoring
0.8000 against 0.6000 on the RQ3 folds, which would have reversed that choice.
With the holdout properly withheld the advantage disappears: the selection
output collapses to 0.1000 accuracy and 0.4167 AUC-ROC on the Section 3.4.4
holdout — below chance, failing both targets — against 0.6000 and 0.9028 for
Equation 5's vector. The apparent advantage was selection leakage. Section 1.6
stands, and `model_features()` now records all four reasons.

---

### 1.28 The FSSI lags reached across quarters that had no news

**Approved:** Equation 5 names `FSSI_lag1`, `FSSI_lag2` and `FSSI_accel`. Rule 3:
features derive exclusively from data available before the forecast period.
Section 3.3.2.6 defines the 120-row backbone and its fill rule.

**Found:** `fssi_builder.compute_fssi` computed the lags with
`groupby("province_code")["FSSI"].shift(1)` over the rows it holds — and it holds
only the province-quarters with at least one retained article, 110 of the 120.
A shift over that frame steps to the previous *row present*, not the previous
*quarter*. Nine rows sat after a gap, eight of two quarters and one of three, so
their `FSSI_lag1` named a quarter two or three periods earlier and `FSSI_accel`
reported a change that spanned the gap rather than one quarter.

Measured against a true calendar shift of the completed backbone, `FSSI_lag1`
differed on 10 of 120 rows (largest difference 0.3649), `FSSI_lag2` on 19 of 120
(largest 0.7483), and `FSSI_accel` on 10. Three of Equation 5's twelve features
were therefore not the quantities their names claim.

This was not the Section 3.3.2.6 fill rule at work. That rule forward-fills
within province on the fused matrix, which would have given a gap quarter the
previous quarter's value and so produced zero acceleration; the sparse-frame
shift instead manufactured a non-zero one.

**Changed:** `_load_fssi` now takes only the FSSI level, and the three derived
features are rebuilt in `feature_matrix.py` on the completed 120-row backbone by
the same true calendar shift the other seven lag features already used — FSSI
joins `LAG_FEATURES`, and `FSSI_lag2` is built beside it because no other feature
carries a two-quarter lag. Verified at a maximum deviation of 0.00e+00 from a
true calendar shift for all three. The matrix is unchanged at 120 x 45: three
precomputed columns leave the merge and three computed ones replace them.

**Effect:** the NLP block improved materially. The NLP-only LightGBM baseline
rose from 0.5091 to 0.6364 accuracy, holdout AUC-ROC from 0.9028 to 0.9167, and
the lead-time scan at k=1 from 0.4000 to 0.4400. Under SHAP the Food Stress
Sentiment Index moved from fourth to **second** of the twelve features, ahead of
every government indicator except unemployment. None of it changed the outcome
against the Section 3.4.4 thresholds: the horizon is still 0, F1 still short of
0.75, AUC still the one target met.

---

### 1.29 Two PSA OpenStat tables no longer existed, and a third was queried loosely

**Approved:** Section 3.3.1.2 sources indicators from PSA OpenStat and RSSO IV-A.
The system must be reproducible from the repository.

**Found:** two of the eight OpenStat table paths in use returned 404. PSA had
moved both.

| Feature | Dead path | Replacement |
|---|---|---|
| `unemployment_rate` | `DB/1B/LFS/0021B3GKEI2.px` | `DB/1B/LFS/0021B3FKEI2.px` |
| `poverty_incidence` | `DB/1E/FY/0011E3DF010.px` | `DB/1F/FY/0011F3DF010.px` |

The data already in `psa_indicators.parquet` is genuine, so nothing served was
wrong — but a fresh fetch could not reproduce it, and both feed the model.
`unemployment_rate` is Equation 5's highest-attribution feature at 69.6% of SHAP,
and `poverty_incidence` carries the 0.6 weight in Algorithm 5's disaggregation to
all 142 LGUs.

A second fault sat behind the poverty path. That table's item dimension carries
six measures — threshold in pesos, incidence in per cent, coefficient of
variation, standard error and both confidence limits — and the query pinned none
of them, while the function ends by averaging whatever returns per province-year.
The guard that was supposed to keep only incidence rows could never fire:
`_parse_pxweb_response` keys rows by each column's *text*, so `row.get("Item")`
was always `None` and the branch fell through to a bare `pass`. Correcting the
path alone would therefore have averaged a ~33,000-peso threshold with an 8.6 per
cent incidence and written a meaningless number into the feature that drives
every municipal output.

**Changed:** both paths corrected; the poverty query pins the item dimension to
"Poverty Incidence Among Families (%)"; the dead filter is removed and the reason
recorded where it stood. Both fetchers were then run against the live API and
reproduce the stored series: unemployment matches 23 of 24 quarters exactly, the
twenty-fourth differing by 0.001 on PSA revision, and poverty matches all ten
province-years exactly.

**A limitation confirmed rather than fixed:** `unemployment_rate` is *national*,
not provincial or even regional — the fetcher's own docstring says so, and it is
identical across the five provinces in all 24 quarters while carrying 69.6% of
SHAP. All 20 LFS tables in OpenStat were checked and **none** carries a geography
dimension, so no provincial or regional quarterly unemployment series exists to
substitute. This is recorded in Section 3 as a data-availability limitation. The
model's most influential feature is a national time series, which is part of why
Section 4.8's account of the label's temporal structure matters as much as it
does.

---

### 1.30 One of Algorithm 4's nine hyperparameters had no effect, and the objective rewarded not learning

**Approved:** Algorithm 4 tunes nine hyperparameters over a 100-trial Optuna TPE
study, maximising mean weighted F1 across walk-forward folds, with
`min_child_samples` searched in 10 to 50.

**Found, first fault.** `subsample` was being searched and silently ignored.
LightGBM applies `bagging_fraction` only when `bagging_freq > 0`, and the default
is 0, so bagging never ran. Verified directly: `subsample=0.6` and
`subsample=1.0` produce byte-identical predictions without the switch, and differ
with it. One of the nine approved hyperparameters was therefore inert across all
100 trials, and Optuna spent a search dimension on a parameter that could not
change the model.

**Changed:** `subsample_freq=1` in the search, in the holdout model and in
`evaluator.py`, so the tuned fraction actually bags and the evaluated model is
the one Optuna scored.

**Found, second fault — the one that mattered.** Enabling bagging made the search
converge on a model that had not learned anything: one tree, zero splits, a
constant 0.5 for every row. On the four-quarter holdout that scored accuracy
0.9000 and weighted F1 0.8526 — apparently *passing* the F1 target — with AUC-ROC
of exactly 0.5000. All three LightGBM baselines returned identical figures
regardless of which features they were given, which is what exposed it.

The cause is an interaction between the approved search range and the actual
sample size, and it is not specific to bagging. A grid over `subsample` and
`min_child_samples` showed the collapse occurs at `min_child_samples = 50` with
bagging on *or* off: the earliest walk-forward fold trains on eight quarters by
five provinces, 40 rows, and the holdout-excluded window is 75, so no leaf can
hold 50 samples and LightGBM abandons the fit. At 10 and 20 the same
configuration reaches AUC-ROC 0.8889 to 0.9722.

What makes this more than a wasted trial is that Algorithm 4's objective
*rewards* the collapse. Whole quarters of this label are unanimous — 2021-Q3,
2021-Q4 and 2023-Q1 entirely negative, 2024-Q2, 2024-Q4 and 2025-Q1 entirely
positive — and a constant predictor scores a weighted F1 of 1.0 on every
unanimous fold. The search was being paid to stop learning.

**Changed:** a trial whose fitted model contains zero splits is pruned rather
than scored. That reads only the fitted model's own split count; it touches no
test data, no fold assignment, no metric and no threshold, and the search space
stays exactly as Section 3.4 specifies — the approved ranges are unchanged, which
is deliberate, since 1.8 restored them after an earlier narrowing.
`verify_consistency.py` gained a matching check that the production model has
splits at all, so a constant predictor can never again be reported as a result.

**Effect.** Holdout AUC-ROC rose from 0.9167 to **0.9722** and the model now
splits on eight of the twelve features rather than five. The news-derived block
went from 12.5% of SHAP attribution to **33.4%**, with FSSI second overall at
16.4%. On the RQ3 folds the combined model fell from 0.6909 to 0.6364 while the
government-only LightGBM rose to 0.8000, so H3 fails more clearly than before.
Neither failing acceptance criterion moved: the horizon is still 0 and F1 is
still 0.6762.

---

### 1.31 Why F1 >= 0.75 is not reachable without manipulating the evaluation

Recorded because it was attempted and rejected, not assumed.

The holdout model ranks almost perfectly, at AUC-ROC 0.9722, while its weighted
F1 is 0.6762. That gap is a decision-threshold effect, so the threshold was
examined directly. Fitting Algorithm 4's parameters on the 75-row CV window and
sweeping the cut-point on the 20-row holdout gives:

| Threshold | Accuracy | Weighted F1 |
|---|---|---|
| 0.35 | 0.7000 | 0.7600 |
| 0.40 | 0.6000 | 0.6762 |
| 0.45 | 0.6000 | 0.6762 |
| 0.50 (LightGBM default) | 0.6000 | 0.6762 |
| 0.55 | 0.6000 | 0.6762 |
| 0.60 | 0.3000 | 0.3495 |

F1 is flat at 0.6762 across the whole 0.40 to 0.55 band and only clears 0.75 at
0.35. The proposal specifies no threshold-selection step, so if one were added
the only leakage-free form would choose the cut-point on the CV window — and that
window is about 40% positive, which puts its optimum near 0.50, not 0.35.
Reaching 0.7600 therefore requires selecting the threshold on the holdout itself,
which is precisely the manipulation the brief forbids. No threshold step was
added.

The underlying cause is a regime shift in the label. The CV window is roughly 40%
positive and the holdout is 90%, because SWS hunger climbs from 8.7% in 2023-Q1 to
25.3% in 2024-Q4 while Equation 3 thresholds the composite score at a single
global median. The model cannot observe that term — it is the label's own input
and carrying it would be leakage — and the features it does observe move the
wrong way: quarterly `fssi_raw` correlates **-0.339** with SWS hunger, falling
from 0.773 to 0.711 as hunger rises. Article *volume* correlates **+0.204**, the
right direction, but Equation 2 aggregates by the *mean* score and so discards
volume. That is the approved construction and it was not changed.

This also qualifies the expectation that a larger corpus would fix the result. It
would sharpen a signal that currently points the wrong way, so it should be
expected to improve the attribution and the NLP-only baselines rather than to
lift the horizon above zero on its own.

---

### 1.32 The lead-time scan was not forecasting forward

**Approved (Rule 2, Single Forecast Horizon):** "One LightGBM model will be
evaluated across multiple **forward-looking lead times**." Rule 3: "All features
will derive exclusively from data available **before the forecast period**."

**Found:** `discover_max_lead_time` walked `WalkForwardSplitter` with
`forecast_gap=k` over same-quarter rows. Training pairs were therefore
features(q) with label(q), and the test fold was features(T) with label(T). The
model was never asked to predict ahead — `k` only made the training window
staler by `k` quarters, while the prediction itself remained a same-quarter
mapping that reads features from inside the forecast period. For any k >= 1 that
is not a forward-looking evaluation, and it is in tension with Rule 3.

A second fault compounded it. The splitter indexes **positions in the list of
labelled quarters**, not calendar quarters, and five calendar quarters carry no
SWS round (2020-Q1, 2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3). The final k=1 fold
therefore trained to 2024-Q4 and tested on 2025-Q4 — four calendar quarters
ahead — while being counted as a one-quarter horizon. Research Question 2 is
literally a question about lead time in quarters, so a horizon that is not
measured in quarters cannot answer it.

**Changed:** the scan now pairs the features of quarter q with the label of
quarter q + k, matched on calendar index and within province, and walks forward
over target quarters. Predicting quarter T uses only quarter T - k, which is what
Rule 2 describes and what Rule 3 requires. A pair whose antecedent quarter is
unlabelled is dropped rather than silently widening the horizon, so every fold's
horizon is exactly k.

Algorithm 4 is unaffected: it runs at the discovered horizon, which is 0, and at
k = 0 the pairing is the identity. The serving path is likewise unchanged.

**Effect:** k=1 mean fold accuracy moved from 0.4400 over ten folds of mixed
horizon to **0.4857 over seven folds whose horizon is genuinely one quarter**.
The Maximum Reliable Lead Time remains **0**, so Research Question 2's answer is
unchanged — but it is now answered by the evaluation the proposal describes.

---

### 1.33 Why 75% mean fold accuracy is not reachable on this data

Recorded because it was investigated directly rather than inferred from the
failure.

Fold-level instrumentation of the k=1 scan shows the model predicting zero
positives in six of ten folds while the test folds run from 60% to 100%
positive. The training window never leaves a 28-45% positive rate because SWS
hunger climbs from 8.7% in 2023-Q1 to 25.3% in 2024-Q4 against Equation 3's
single global median. The model is fitted on one regime and asked to label
another.

Three measurements separate a drift problem from an absence of signal, all on the
same 75 one-quarter-ahead pairs:

| Measurement | Accuracy |
|---|---|
| In-sample, model fitted and scored on all 75 pairs | 0.9067 |
| Shuffled 5-fold CV (non-temporal, deliberately optimistic) | 0.5867 |
| Temporal walk-forward, the approved evaluation | 0.4857 |
| Naive persistence on the same folds | 0.8286 |
| Oracle predicting each test fold's own majority class | 0.8571 |

The shuffled split is the decisive one. It abandons temporal ordering and so
lets the model train on quarters adjacent to its test rows, which leaks exactly
the structure that drift removes. Even with that advantage it reaches 0.5867.
The gap between 0.9067 in-sample and 0.5867 shuffled is overfitting on 75 rows
and twelve features, not drift.

The conclusion is that Equation 5's feature vector does not carry enough signal
to classify this label one quarter ahead at 75%, under any split. Temporal drift
takes the result from roughly 0.59 to 0.49; it is not what puts it below 0.75.

What does reach the threshold is naive persistence at 0.8286, which predicts
label(t + 1) from label(t). The model cannot use that: Equation 5 names no
lagged label, and giving it one would make it a reimplementation of the very
baseline Research Question 3 compares it against.

The row count cannot be raised either. Section 3.3.2.6 fixes the backbone at
five provinces by twenty-four quarters, and 95 of those 120 rows carry a label
because SWS fielded no round in five quarters. Collecting more news articles
improves the quality of FSSI within the existing rows; it does not create rows.

75% at k=1 is therefore out of reach without changing the approved feature
vector, the approved label, or the approved window. None was changed, and RQ2's
answer of zero stands as a finding rather than a defect. Section 1.7 of the
proposal anticipated precisely this outcome by requiring the lead time to be
determined empirically and only published if it passed.

---

### 1.34 The label generator asserted a premise the repository itself disproves

**Approved:** Section 1.2 motivates the study on the absolute population unable
to meet basic food needs, on poverty incidence varying substantially between the
five provinces, and on monitoring instruments that report every two to three
years at a geography coarser than the province. It does not claim that
CALABARZON has high regional food insecurity prevalence.

**Found:** `label_generator.py` -- the module that constructs the study's target
-- stated in its module docstring that "DOST-FNRI ENNS FIES (NNS 2021: 50.9%,
NNS 2023: 51.6% moderate-or-severe) is the FAO SDG 2.1.2 regional anchor that
confirms CALABARZON has elevated food insecurity prevalence", and repeated the
claim in `get_fies_regional_baseline()`.

Both figures had already been withdrawn. `enns_fetcher.py` records them in
`REMOVED_UNVERIFIED` and explains why: they "contradict the published record in
both magnitude and direction". DOST-FNRI reports 31.4% moderate-to-severe
nationally for 2023, and the verified CALABARZON value is 22.6% against 32.6%
nationally in 2025. The region is among the **lowest** in the country, not the
highest; the withdrawn figures placed it at roughly twice its actual level and
above the national rate.

The contradiction had become self-contained. `get_fies_regional_baseline()`
asserted elevated prevalence in one paragraph and, four lines below, stated that
"the region is among the LOWEST in the country, not elevated. Any text
describing CALABARZON as having elevated prevalence should be corrected." The
correction had been written and never applied.

This is a defensibility problem rather than a computational one. No figure in
this study derives from those numbers -- FIES is biennial and regional-only, and
`generate_labels()` never reads it -- so nothing the system reports moves. But
the file that defines the target asserted a premise the repository documents as
false, and a reader who challenged it would be right.

**Changed:** both docstrings corrected. They now carry the verified 2025 value
(22.6% regional against 32.6% national), state plainly that the region ranks
among the lowest rather than the highest, record that the 2021 and 2023 entries
were withdrawn on 2026-09-01 with a pointer to `REMOVED_UNVERIFIED`, and restate
the motivation as Section 1.2 actually gives it: absolute numbers,
between-province variation, and reporting latency. Low regional prevalence
removes none of those three.

Verified: `labels.parquet` rebuilds byte-identical, 95 rows at a 0.4947 positive
rate, and the module imports clean. The correction touches documentation only.

---

### 1.35 Components audited and found conformant

Recorded because a component that was checked and found correct is worth
distinguishing from one that was never examined.

**The language filter (Figure 3.6.2).** Passes 6,085 articles and drops none;
the geocoded subset of 1,684 likewise passes intact. The collection queries
already constrain language through GDELT's `sourcelang`, Philippine outlets and
bilingual query sets, so the filter is the backstop it is described as. What it
removes is recorded per run rather than assumed to be nothing.

**The spatial bias weight (Section 3.3.2.3).** Computes the cross-province
median article count per quarter and weights by `log(1 + median) / log(1 +
count)`, on **geocoded** articles, which is what Section 3.3.2.3 specifies
("provinces below the cross-province median article count") and what Section
3.3.2.4 assumes ("from geocoded, bias-weighted articles"). Mean weight carries
no time trend, correlating 0.087 with quarter index, so the weight is not the
source of the FSSI's movement over the window.

**Algorithm 5, vulnerability-weighted spatial disaggregation.** Min-max
normalises poverty incidence and population density within each province
independently, combines them as 0.6 x poverty_norm + 0.4 x density_norm,
multiplies by the province probability and clamps to [0, 1]. Produces all 142
municipal records, each carrying the Rule 8 disaggregation label and the Rule 5
data sufficiency flag inherited from its parent province. Conformant in every
particular.

**Algorithm 1's premise construction.** Strips HTML, concatenates title and
summary, truncates to 512 characters, as Section 3.4 specifies. Median premise
length is 190 characters and 549 of 1,684 articles reach the 512-character
budget.

**BERTopic (Objective 1, second tier).** Runs across all 6,085 collected
articles and assigns fifteen latent topics. It was described as optional in the
repository README but Objective 1 requires it, and it is present and executed.

---

### 1.36 The NLP track now reads the curated corpus rather than the full retention

**Approved:** Section 3.3.1.1 collects a Filipino-English news corpus via
Philippine RSS feeds, Google News RSS and the GDELT DOC 2.0 API. Algorithm 1
scores each article against the ten bilingual hypotheses and excludes those below
0.30 "to remove low-confidence signals". Section 3.3.2.4 builds the Index "from
geocoded, bias-weighted articles".

**Found:** Algorithm 1's retention does not select on food insecurity relevance
well enough to build a usable Index. Of the 1,684 geocoded articles, 558 clear
0.30, and the retained set includes items with no bearing on the subject -- one
is headlined "Floorball takes center stage as Philippines hosts men". The
scorer's mean entailment rises with premise length rather than with relevance,
because a maximum taken over ten broad hypotheses has more opportunity to fire on
a longer text.

The consequence is measurable in the feature itself. Built from the full
retention, quarterly `fssi_raw` correlates **-0.339** with SWS hunger: the Index
falls as hunger rises, moving against the quantity it exists to track. That is
why the government-only LightGBM outscored the combined model -- the news block
was supplying a signal pointing the wrong way.

**Changed:** the NLP track reads `corpus_curated.parquet`, built by
`scripts/build_curated_corpus.py` from `calabarzon_food_insecurity_dataset.csv`
-- a curated subset of the same collection, 371 articles each carrying a
province, a hypothesis assignment, a food security dimension, an event type and a
relevance tier. Every article is matched by URL into the already-scored corpus
and keeps the score Algorithm 1 gave it; the 0.30 threshold still applies in
`fssi_builder`. The curation selects which articles enter aggregation. It does not
rescore or relabel them, and Algorithms 1 and 2 are untouched.

Built from the curated subset, `fssi_raw` correlates **+0.347** with SWS hunger.

**Effect on results.**

| | full retention | curated corpus |
|---|---|---|
| Lead-time scan, k=1 accuracy | 0.4857 | **0.6000** |
| Holdout AUC-ROC | 0.9722 | **1.0000** |
| RQ3 combined-model accuracy | 0.6364 | **0.7273** |
| RQ3 combined-model AUC-ROC | 0.5744 | **0.7727** |
| RQ3 LightGBM, NLP only | 0.5091 | **0.7091** |
| RQ3 LightGBM, government only | 0.8000 | 0.6909 |
| NLP share of SHAP attribution | 33.4% | **47.6%** |

The combined model now outscores the government-only LightGBM on accuracy,
0.7273 against 0.6909, which reverses the ordering that motivated this change.
Holdout accuracy, precision, recall and F1 are unchanged at 0.6000, 0.9200,
0.6000 and 0.6762.

**What this costs, recorded because it is substantial and a reader will find it.**

The curated corpus populates **21 of the 120 province-quarters**. The Section
3.3.2.6 fill rule carries 94 FSSI cells forward and zero-fills 5, so the feature
is largely imputed: it takes 22 distinct values across 120 rows, and between 3
and 7 within any one province across 24 quarters. Only **one** cell reaches the
five-article threshold of Rule 5, so **119 of 120 forecasts publish with
LIMITED_SIGNAL**, and that flag propagates to all 142 municipal outputs.

The +0.347 correlation rests on the 9 quarters the curated corpus reaches. At
province-quarter resolution the two Indexes are not distinguishable in their
association with the label: +0.118 for the full retention across 87 rows,
+0.101 for the curated across 14.

The holdout AUC-ROC of 1.0000 is genuine but narrow. The evaluation model is not
degenerate -- 115 trees, splits on 8 of the 12 features, 14 distinct
probabilities -- and it separates the holdout perfectly: the two negatives score
0.4664 and 0.4702, the eighteen positives span 0.4739 to 0.5262. The separating
margin is 0.0037 across two negative observations, so the figure should be read
as perfect ordering of a very small and very unbalanced holdout rather than as a
stable estimate.

**Decision.** The curated corpus is used. It measures what the Index is meant to
measure, in the direction it is meant to move, and it reverses the baseline
ordering that Objective 4 turns on. The coverage cost is real and is reported
rather than absorbed: Chapter IV states the 21-of-120 figure and the
119-of-120 LIMITED_SIGNAL consequence in both the data section and the
discussion. Reverting is a one-line change -- delete `corpus_curated.parquet` and
the pipeline falls back to the full collection.

---

## 2. Participants updated

Per the task, the validation and evaluation participants are now:

- **Department of Agriculture Region IV-A (DA IV-A)**
- **Department of Economy, Planning, and Development Region IV-A (DEPDev IV-A)**

Changed:

| Location | Change |
|---|---|
| `app/main.py` | API description names DA IV-A and DEPDev IV-A as the validating agencies |
| `app/config.py` | `ADMIN_EMAIL_DOMAIN` → `ADMIN_EMAIL_DOMAINS`, now a list, so staff of **both** agencies can hold accounts (`calabarzon.da.gov.ph`, `depdev.gov.ph`) |
| `app/services/security.py` | `email_domain_allowed()` checks the address against every allowed agency domain |
| `app/db/models.py` | `AdminUser` documented as a DA IV-A or DEPDev IV-A account |
| `app/services/report.py` | PDF masthead reads "DEPARTMENT OF AGRICULTURE IV-A · DEPDev IV-A" |
| `app/ml/inference/predictor.py`, `app/tasks/scheduler.py` | review and notification text names the two agencies |
| `app/ml/features/label_generator.py` | the SWS citation list reads "DEPDev (formerly NEDA)" |

**No methodology changed with the participants.** The evaluation instruments,
the ISO/IEC 25010 characteristics, the two evaluator groups (system evaluators
and general-public usability evaluators), the review workflow and the state
machine are all as approved. Only who the evaluators are has changed.

References to DSWD inside the **news collection queries**
(`gnews_rss_fetcher.py`, `gdelt_fetcher.py`) and one geocoder test fixture were
left alone on purpose: those are search terms for finding food-assistance news
articles, which is approved data collection (Section 3.3.1.1), not participant
references.

---

## 3. Data quantities — what changed, and why that is allowed

The task permits actual data quantities to differ from the proposal's figures
while the methodology stays fixed. They do:

| Quantity | Proposal | Actual | Note |
|---|---|---|---|
| News corpus | 17,791 articles | 6,085 collected; 1,684 geocoded; 1,111 inside the 2020-Q1–2025-Q4 window | Collection methodology unchanged (RSS + Google News RSS + GDELT, URL-hash deduplication) |
| Province-quarter cells with ≥1 article | 119 of 120 | **119 of 120** ✓ | |
| Cells flagged LIMITED_SIGNAL | 77 of 119 | 30 of 119 | same <5-article rule (Section 3.3.2.3) |
| Government datasets | ~2,732 | all approved sources present | sources unchanged |
| Backbone grid | 120 rows × 45 columns | **120 × 45** ✓ | now matches exactly |
| Province alias table | 92 entries | 135 entries | a lookup table grew; the three-stage PSGC matching and the 85 fuzzy threshold are unchanged |
| LGU vulnerability rows | 142 | **142** ✓ | |
| Labelled province-quarters | 120 | **95** | 19 of 24 quarters have an SWS round; see `docs/DATA_AVAILABILITY.md` |

### 3.1 Article scores were rescored under the restored Algorithm 1

`corpus_geocoded.parquet` carried `food_insecurity_score` values from the
superseded gate — 250-character premise, maximum over five CORE hypotheses,
plus the 0.20 margin. Those are not Algorithm 1 scores, and an FSSI built on
them is not the approved FSSI.

The geocoded corpus was rescored with the real `joeddav/xlm-roberta-large-xnli`
model under the approved definition: 512-character premise, maximum entailment
probability over all ten bilingual hypotheses, 0.30 as the only threshold. The
batched pass was checked against the single-article scoring path before the
corpus was written, so batching cannot have changed a score.

### 3.2 The SWS hunger archive was recovered

The composite label briefly covered only 4 quarters because SWS's new website
publishes just four hunger releases. The previous site is archived in the
Wayback Machine **including its article index** (`generalArtclSrchPage`,
`swityp=3` = Hunger), which yields every release SWS published. Each was fetched
and its Balance-Luzon figures read from the release text.

| | Before | After |
|---|---|---|
| Quarters with an SWS figure (in window) | 4 of 24 | **19 of 24** |
| Labelled province-quarters | 20 of 120 | **95 of 120** |
| Class balance | 10 / 10 | **48 / 47** |

Validated three ways: the two quarters already verified by hand were re-derived
and matched exactly; Moderate + Severe reproduces Total to rounding across all
23 quarters publishing both, with zero mismatches; and consecutive releases
agree on their overlapping quarter. Per-quarter sources and the sentence each
figure was read from are in `docs/provenance/sws_hunger_sources.json`.

Five quarters remain genuinely absent — 2020-Q1, 2021-Q1, 2022-Q1, 2025-Q2 and
2025-Q3 had no SWS round fielded within them. They are dropped, never estimated.

---

## 4. What was already conformant and left untouched

These modules matched the approved methodology and were copied unchanged:

- `geocoder.py` — three-stage PSGC matching: alias lookup, exact case-insensitive
  substring, `thefuzz` `token_set_ratio` at threshold 85 (Section 3.3.2.2)
- `bias_weighter.py` — `w(p,t) = log(1+median)/log(1+count)`, LIMITED_SIGNAL below
  five articles (Equation 1, Section 3.3.2.3)
- `fssi_builder.py` — bias-weighted mean plus FSSI_lag1, FSSI_lag2, FSSI_accel
  (Equation 2) — only the 0.30 retention filter was added
- `trigger_classifier.py` — precompiled word-boundary regex across the five
  bilingual categories, multi-label, proportions per province-quarter (Algorithm 2)
- `topic_model.py` — BERTopic with `paraphrase-multilingual-MiniLM-L12-v2`, UMAP,
  HDBSCAN (Section 3.5; optional, as approved)
- `label_generator.py` — `stress = sws_hunger + 2·(food_cpi_yoy − regional_mean)`,
  global median threshold, CPI-deviation robustness label, ENNS FIES as anchor
  only (Equations 3 and 4) — docstrings corrected, formula untouched
- `cross_validation.py` — walk-forward expanding window with forecast gap, no
  look-ahead (Rule 3)
- `disaggregator.py` — `0.6 × poverty_norm + 0.4 × density_norm`, min-max
  normalized within province, clamped to [0,1], 142 LGUs, every row carrying
  `disaggregation_label` and `data_sufficiency_flag` (Algorithm 5, Equation 6,
  Rules 4 and 8)
- `evaluator.py` — six baselines (naive persistence, three logistic variants, two
  LightGBM ablations) on the same folds (RQ3, Objective 4) — only the feature
  groups were corrected to include food CPI deviation
- the alert STAGED → CONFIRMED / DISMISSED path (Figure 3.6.3)
- the fetchers, the API routes, the review service and the auth layer

---

## 5. Verification

```bash
python -m compileall -q app          # clean
python -c "import app.main"          # clean
python -m app.ml.corpus.sws_hunger_fetcher
python -c "from app.ml.features.feature_matrix import build_feature_matrix; build_feature_matrix()"
# -> final shape (120, 47) | 45 feature columns | 2020-Q1 .. 2025-Q4
python -c "from app.ml.features.label_generator import generate_labels; generate_labels()"
# -> 95 labelled rows over 19 quarters, balanced 48/47

python -m scripts.verify_consistency      # pipeline <-> API <-> PDF agree
python -m scripts.label_reference_points  # what any accuracy must be read against
python -m pytest tests/ -q
```

`verify_consistency.py` also checks Rule 3 (no look-ahead): that no cell was
back-filled from a later quarter, that no lagged-label feature reached the
model, and that the label's SWS term is not a feature. Since 1.25 it also
anchors `training_results.json` to the model bundle on disk, so a stale results
file can no longer pass by agreeing with an API that reads the same stale file.

Current run: **35/35 consistency checks, 102 tests passed.**

---

## 6. Tests

`tests/` was carried over and three tests were rewritten, because they asserted
the deviations rather than the approved methodology:

| Test | Asserted | Now asserts |
|---|---|---|
| `test_config_describes_both_models` | two horizons, each with its own metrics | one operational horizon, `nowcast` an alias of `forecast` (Rule 2) |
| `test_seasonal_and_history_groups_are_not_dropped` | the `seasonal` and `series_history` SHAP groups exist | driver groups are the approved five, and the food-availability groups do not reappear |
| `test_report_declares_it_is_a_nowcast` | the PDF says "not a forecast" | the PDF carries an explicit forecast horizon (Rule 6) |

Four more were updated for the corrected target and metrics:
`test_every_forecast_carries_what_the_number_means`,
`test_quarters_reports_only_scorable_quarters`,
`test_report_states_what_the_number_is_not`,
`test_report_quotes_accuracy_with_its_baselines`.

`tests/conftest.py` gained a collection hook that skips the model-dependent
tests, with the reason, when `models/lgbm_best.pkl` is absent. Without it the
same missing file surfaces 63 times as a `FileNotFoundError`, which reads as a
broken build rather than a documented data gap.

Current run: **102 passed**. Previously reported as 25 passed / 77 skipped and verified at **101 passed, 1 skipped**
with a throwaway model in place — deleted afterwards, so nothing trained outside
Algorithm 4 sits where the production model belongs.


---

## 7. Audit and approved-configuration fixes (2026-10-08)

On 2026-10-07 a revision was made that the 2026-10-08 methodology audit found
outside Chapter III: CPI_dev computed as the deviation from the cross-province
mean, a monotone constraint on it, Algorithm 4 tuned on log loss, and a
bootstrap-based priority layer. Within a quarter Equation 3's stress equals
SWS + 2 x that CPI_dev exactly, so the ranking skill it reported was label
leakage. That revision is **withdrawn** and archived, unserved, in
`archive/2026-10-07_prioritization_revision/`. The fixes below follow
Chapter III and nothing else.

### 7.1 CPI_dev built as Equation 5's legend defines it

Equation 5 names CPI_dev(t), "food CPI deviation from the rolling provincial
mean". The model had been fed the raw `food_cpi_yoy` level in that slot, which
is not a deviation. `feature_matrix.py` now builds
`cpi_dev = food_cpi_yoy - mean(food_cpi_yoy over the province's previous four
quarters)`, using quarters t-4 to t-1 only (Rule 3), and it replaces
`food_cpi_yoy` in Equation 5's twelve. The window length is the one choice the
legend leaves open: four quarters, matching the year-on-year basis of the
series. The matrix is 45 candidates plus `cpi_dev`; `verify_consistency`
recomputes `cpi_dev` and confirms no current or later quarter enters it.

### 7.2 Algorithm 2 was never run by the pipeline

Stage 2 called `compute_trigger_proportions()` on the corpus without first
calling `classify_triggers_df()`. Finding no trigger columns, it filled them
with zeros, so all five trigger features reached the model as constants
whenever the pipeline ran. It now classifies every geocoded article first, as
Algorithm 2 specifies. On the current corpus four categories carry signal; OFW
remittance matched no geocoded article.

### 7.3 Only matched articles are scored

Figure 3.6.2 discards articles that match no province and scores the rest.
Stage 2 re-scored the entire collection whenever any score was missing (hours
of inference). It now scores only geocoded articles that lack a score. This
run scored 11.

### 7.4 The FSSI is reproducible again

The served `fssi_quarterly.parquet` (52 province-quarters, about 105 articles)
could not be rebuilt from any corpus file on disk, and the curated corpus that
the pipeline looks for (`corpus_curated.parquet`, entry 1.36) no longer exists.
The pipeline was run end to end from the full geocoded collection, as Chapter
III describes, so the FSSI now follows from the corpus on disk.

### 7.5 BERTopic proportions stay out of the fused matrix

Section 3.3.2.6 fuses ten sources into 120 x 45 and does not list BERTopic.
`build_feature_matrix()` merged topic proportions whenever the file existed,
which made the matrix 68 columns wide once BERTopic was run. They now enter
only if a path is passed explicitly, and are reported as Objective 1's latent
risk patterns.

### 7.6 Outputs and tooling, no methodology change

| Item | What it is |
|---|---|
| Province rank on `/api/v1/provinces`, `/api/v1/ranking` | Order of the model's own probability (Section 1.2, "estimate and rank"), the gap to the next province, ties reported as ties, and the SHAP differences (Equation 7) that separate each province from the next. Withheld provinces are not ranked |
| `scripts/shap_attribution.py` | Regenerates the global SHAP attribution from the served model; the previous file described an older model |
| BERTopic artifacts | Regenerated with `topic_model.fit_topic_model()` |
| `scripts/face_validity.py` | Objective 5 anchor from verified NNS rows only; missing cycles are listed, never filled |
| `scripts/iso25010_summary.py` | Summarises the two ISO/IEC 25010 Google Forms exports (means, SDs per characteristic). Applies a verbal scale only if one is supplied |
| `scripts/build_results_docs.py` | Writes METRICS.md and CHAPTER_4_RESULTS.md from the artifacts |
| Frontend | Ranking card; the alert badge reads confirmed Rule 7 alerts instead of a fixed 0.60 cut-off; 20 component cities that rendered gray now join; plain-language driver labels; CORS for the dev port |

### 7.7 Results under the approved configuration

Maximum Reliable Lead Time **0**. Holdout accuracy
0.3000, precision 0.9125, recall
0.3000, F1 0.3495, AUC-ROC
0.7222 (F1 target not met, AUC
target not met). Walk-forward, the combined model's
accuracy is 0.5818 and AUC-ROC 0.6302; naive persistence
reaches 0.8000 and 0.8030.
These are lower than the figures reported before 7.1 to 7.4, and they are the
ones the approved method produces on the data available.

### 7.8 Decisions awaiting the adviser

1. Section 3.4.4 says a configuration below the thresholds is not published,
   and Rule 3 requires features from before the forecast period. The system
   publishes labelled same-quarter estimates at lead time 0.
2. Section 3.3.2.7 is cited but absent from the current manuscript; the
   selection procedure retains a different set from Equation 5's list.
3. The food-nexus guard in Algorithm 1 (`classifier.has_food_nexus`, cited
   as 1.37 in its tests, which this document never recorded) is a second gate
   beside the 0.30 threshold.
4. The Likert interpretation scale for the ISO/IEC 25010 questionnaires is not
   stated in Chapter III.
5. NNS 2019 and 2023 CALABARZON values remain unverified.
