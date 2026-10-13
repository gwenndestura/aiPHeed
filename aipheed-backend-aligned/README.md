# aiPHeed — backend, aligned to the approved proposal

An interactive web-based geospatial food insecurity forecasting system for
Region IV-A (CALABARZON), using zero-shot Filipino-English NLP and a LightGBM
ensemble.

This folder is the backend revised to follow the approved thesis proposal
strictly. Read **[docs/PROPOSAL_CONFORMANCE.md](docs/PROPOSAL_CONFORMANCE.md)**
for what was found and what changed, and
**[docs/DATA_AVAILABILITY.md](docs/DATA_AVAILABILITY.md)** for where the data
came from. **[docs/METRICS.md](docs/METRICS.md)** has the model results, and
**[docs/CHAPTER_4_RESULTS.md](docs/CHAPTER_4_RESULTS.md)** is the thesis write-up.

The original `../backend/` is unchanged.

**Validating agencies:** Department of Agriculture Region IV-A (DA IV-A) and
Department of Economy, Planning, and Development Region IV-A (DEPDev IV-A).

---

## The approved pipeline

Six stages, as Section 3.2 and Figure 3.6.2 lay them out.

| Stage | What runs | Module |
|---|---|---|
| 1. Collect | RSS, Google News RSS, GDELT; PSA, BSP, DOE, PAGASA, PhilRice, SWS | `app/ml/corpus/` |
| 2. Preprocess | HTML strip → concat → truncate to 512 chars; three-stage PSGC geocoding; inverse-coverage bias weights; LIMITED_SIGNAL below 5 articles | `classifier.clean_text`, `geocoder`, `bias_weighter` |
| 3. NLP | Algorithm 1 zero-shot XLM-RoBERTa over 10 bilingual HungerGist hypotheses, max entailment, 0.30 threshold → FSSI + lags + acceleration; Algorithm 2 regex triggers across 5 bilingual categories; BERTopic (optional) | `nlp/`, `features/fssi_builder.py` |
| 4. Fuse & select | 120-row backbone (5 provinces × 24 quarters, 2020-Q1–2025-Q4) → 45 candidate columns → Section 3.3.2.7 two-stage selection → 12 features | `features/feature_matrix.py`, `features/feature_selector.py` |
| 5. Train | Algorithm 3 lead-time discovery (k = 1…8, 75% accuracy floor); Algorithm 4 Optuna TPE, 100 trials, 9 hyperparameters, 4-quarter holdout, F1 ≥ 0.75 and AUC ≥ 0.80 | `training/trainer.py` |
| 6. Serve | Equation 5 province probabilities; Equation 7 SHAP attribution; Algorithm 5 disaggregation to 142 LGUs; Rule 7 rolling-threshold alerts; all STAGED for review | `inference/`, `api/`, `services/` |

Key constants, all from the proposal:

```
window           2020-Q1 .. 2025-Q4      (24 quarters × 5 provinces = 120 rows)
CPI_dev          food_cpi_yoy − the province's mean over its previous 4 quarters (Eq. 5 legend)
hypotheses       10, bilingual            premise 512 chars, threshold 0.30
geocoding        alias → substring → thefuzz token_set_ratio @ 85
bias weight      w(p,t) = log(1+median) / log(1+count)
LIMITED_SIGNAL   < 5 geocoded articles in a province-quarter
label            stress = sws_hunger + 2·(food_cpi_yoy − regional_mean), > global median
selection        |r| > 0.85 filter, then SHAP backward elimination, floor 10 / ceiling 15
lead time        k = 1..8, halt below 75% mean fold accuracy
tuning           100-trial Optuna TPE, 9 hyperparameters, objective = mean weighted F1
targets          F1 ≥ 0.75, AUC-ROC ≥ 0.80
disaggregation   0.6 × poverty_norm + 0.4 × density_norm, within-province, 142 LGUs
```

---

## Running it

```bash
pip install -r requirements.txt
cp ../.env.example .env        # set SECRET_KEY; the app refuses to sign tokens otherwise
```

One quarterly cycle:

```bash
python -m scripts.run_quarterly_pipeline
```

```bash
python -m scripts.run_quarterly_pipeline --skip-collect --skip-train
```

Individual stages:

```bash
python -m app.ml.corpus.sws_hunger_fetcher
python -c "from app.ml.features.feature_matrix import build_feature_matrix; build_feature_matrix()"
python -c "from app.ml.features.label_generator import generate_labels; generate_labels()"
python -c "from app.ml.features.feature_selector import select_features; select_features()"
python -c "from app.ml.training.trainer import train_model; print(train_model())"
```

The API:

```bash
uvicorn app.main:app --reload
```

The quarterly scheduler is off unless you ask for it, so importing the app in a
test never starts a background thread:

```bash
AIPHEED_ENABLE_SCHEDULER=1 uvicorn app.main:app
```

---

## Current state

| Step | State |
|---|---|
| Corpus pipeline — geocode, bias weight, score, FSSI, triggers | runs |
| Article scores | rescored under the restored Algorithm 1 (512 chars, max over all ten bilingual hypotheses, 0.30 threshold) |
| Feature matrix | **120 × 45**, 2020-Q1 – 2025-Q4, no NaN — matches Section 3.3.2.6 exactly. Food CPI is the **provincial** PSA series; a region-level copy had been overwriting it (PROPOSAL_CONFORMANCE 1.24) |
| SWS hunger series | **19 of 24 quarters** recovered from the Wayback-archived SWS releases |
| Composite stress label | **95 of 120 rows**, balanced 48 / 47 |
| CPI robustness label (Equation 4) | all 120 rows |
| Two-stage feature selection (3.3.2.7) | runs — the four holdout quarters withheld from it; 10 retained (audit trail; the model trains on Equation 5's twelve) |
| Algorithms 3 and 4 | run. Maximum Reliable Lead Time **0**. Current holdout figures are generated into [docs/METRICS.md](docs/METRICS.md) |
| RQ3 baselines | run; accuracy, AUC and ranking metrics for all six in [docs/METRICS.md](docs/METRICS.md) |
| Province ranking (rank, gap to next, ties, SHAP reasons) | runs; `/api/v1/ranking` and every `/api/v1/provinces` row |
| Spatial disaggregation, SHAP, API, review workflow, scheduler | run |

### Audit and fixes, 2026-10-08

A revision made on 2026-10-07 (regional-mean CPI_dev, monotone constraint,
log-loss tuning, bootstrap priority tiers) was found to fall outside Chapter III
and is withdrawn; it is archived, unserved, in `archive/`. The backend now
follows Chapter III, with four defects fixed: CPI_dev is built as Equation 5's
legend defines it, Algorithm 2 actually runs in the pipeline, only matched
articles are scored, and BERTopic stays out of the fused matrix. Record and open
decisions: [PROPOSAL_CONFORMANCE Section 7](docs/PROPOSAL_CONFORMANCE.md).
Results documents are generated:

```bash
python -m scripts.run_quarterly_pipeline --skip-collect
python -m scripts.shap_attribution
python -m scripts.face_validity
python -m scripts.build_results_docs
```

The SWS archive that had blocked training was recovered on 2026-09-23. SWS's
current site publishes only four hunger releases, but its previous site is
archived in the Wayback Machine **including its article index**, which yields
every release it published. Each was fetched and its Balance-Luzon figures read
from the release text — validated against the two quarters already verified by
hand, against the Moderate + Severe = Total identity across all 23 quarters that
publish both, and against the overlap between consecutive releases.
Per-quarter sources are in
[docs/provenance/sws_hunger_sources.json](docs/provenance/sws_hunger_sources.json).

Five quarters remain genuinely absent — 2020-Q1, 2021-Q1, 2022-Q1, 2025-Q2 and
2025-Q3 had no SWS round fielded in them. They are dropped, never estimated.

### Checks

```bash
python -m scripts.verify_consistency    # pipeline <-> API <-> PDF agree
python -m pytest tests/ -q
```

`verify_consistency.py` asserts that the metrics in `training_results.json` are
the ones the dashboard serves and the ones the PDF prints, that the model was
trained on the selected feature set, and that Equation 7 reproduces the served
probability. The dashboard and the PDF both read `model_performance()`, so they
cannot diverge by construction.

---

## The review workflow (Figures 3.6.1 and 3.6.3)

Nothing the pipeline produces is public until a person says so.

```
forecast   PENDING --scored--> STAGED --admin accepts--> PUBLISHED --next quarter--> ARCHIVED
              ^                   |
              +--- admin rejects -+        (the reason stays on the row; that is "withheld")

alert                          STAGED --admin confirms--> CONFIRMED  (shown publicly)
                                  \---- admin dismisses-> DISMISSED  (kept for audit only)
```

| Route | Who | Purpose |
|---|---|---|
| `POST /api/v1/admin/pipeline/run` | admin | trigger the quarterly cycle (includes Collect Data) |
| `GET  /api/v1/admin/pipeline/status` | admin | state of the current or last cycle |
| `GET  /api/v1/admin/review?quarter=&status=` | admin | the forecast review queue |
| `POST /api/v1/admin/review/{id}/approve` | admin | STAGED → PUBLISHED |
| `POST /api/v1/admin/review/{id}/reject` | admin | → PENDING, with a required reason |
| `GET  /api/v1/admin/alerts?status=` | admin | the alert queue, by state |
| `POST /api/v1/admin/alerts/{id}/confirm` | admin | STAGED → CONFIRMED |
| `POST /api/v1/admin/alerts/{id}/dismiss` | admin | STAGED → DISMISSED |
| `GET  /api/v1/alerts` | public | confirmed alerts only |
| `GET  /api/v1/ranking?quarter=` | public | published provinces ranked by risk probability, with SHAP reasons |
| `GET  /api/v1/rejections` | public | what a reviewer withheld, and why |

Accounts are restricted to the validating agencies' domains
(`calabarzon.da.gov.ph`, `depdev.gov.ph`), enforced server-side.

---

## Layout

```
app/
  api/v1/          FastAPI routes — dashboard, forecast, insights, report,
                   admin (review + pipeline), alerts, auth
  db/              models, migrations, repositories
  ml/
    corpus/        fetchers, geocoder, language_filter, bias weighter
    features/      fssi_builder, feature_matrix, feature_selector, label_generator
    nlp/           classifier (Algorithm 1), trigger_classifier (Algorithm 2), topic_model
    training/      cross_validation, trainer (Algorithms 3–4), evaluator (baselines)
    inference/     predictor (Eq. 5), explainer (Eq. 7), disaggregator (Algorithm 5)
  services/        dashboard, report, review, pipeline_runs, security
  tasks/           scheduler — Rule 1 quarterly cycle
scripts/           run_quarterly_pipeline, refresh_all_sources, create_admin,
                   build_annotation_workbook (Section 3.7), verify_consistency,
                   label_reference_points, compare_feature_sets
scripts/supplementary/  diagnostics OUTSIDE the approved methodology; not used
                   by the pipeline, the API, the PDF or Chapter IV
data/supplementary/  their outputs, same exclusion
docs/              PROPOSAL_CONFORMANCE.md, DATA_AVAILABILITY.md, METRICS.md,
                   CHAPTER_4_RESULTS.md, provenance/
data/processed/    parquet inputs and outputs
models/            lgbm_best.pkl, optuna_study.pkl
```
