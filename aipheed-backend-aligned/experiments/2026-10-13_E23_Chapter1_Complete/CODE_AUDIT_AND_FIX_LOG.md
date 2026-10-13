# Code audit and bug-fix log (E23, 2026-10-13)

**Scope.** The isolated development backend `aipheed-backend-aligned/` and the E23 dashboard copy.

- `backend/`, `frontend/`, production models and deployed systems were **not modified**.
- A pre-edit copy of every edited backend file is in `docs/*.before`.
- Nothing was committed, pushed or deployed.

## Fixes

| # | Defect (cause) | Files | Before → after | Regression test | Effect on conclusions |
|---|---|---|---|---|---|
| F1 | **Quarter boundaries in UTC, not Philippine time.** Articles were assigned to a quarter using the timestamp's own offset (feeds and GDELT give UTC). `build_curated_corpus.py` explicitly converted to UTC. An article published 00:00–07:59 PHT on a quarter's first day was counted in the **previous** quarter: up to 8 hours of next-quarter news inside a quarter whose forecast origin had passed. | `app/ml/corpus/_dates.py` (new `published_in_ph`, `quarter_of_publication`), `app/ml/corpus/bias_weighter.py`, `scripts/build_curated_corpus.py` | `2025-12-31T19:00Z` → 2025-Q4 **before**, 2026-Q1 **after**. A naive timestamp is read as PHT. | `tests/test_quarterly_pipeline.py::test_quarter_of_publication_uses_philippine_time` (7 cases) | **Unknown in size.** Measuring the affected articles requires reading the news corpus, which is not authorized. Stored `features_fused` was **not rebuilt**, so E23 results use the pre-fix features. Expected effect: at most a few boundary articles. |
| F2 | **Missing province forecast became zero risk.** `Disaggregator` defaulted `risk_probability` to 0.0, so every LGU of a province without a forecast was ranked as the safest in the region. | `app/ml/inference/disaggregator.py` | 0.0 → `risk_index = null`, flag `NO_PROVINCE_FORECAST`, sorted last. Also exposes `vulnerability_index` and `poverty_is_province_fallback`. | `tests/test_disaggregator_fix.py` (2 tests); `runner/build_rankings.py` check | None for the existing rankings (all five provinces had forecasts). Prevents silent zero rankings when data are insufficient, which is the 2027-Q1 situation. |
| F3 | **No forecast cutoff, news window or authorization check in the quarterly cycle.** `scripts/run_quarterly_pipeline.py` forecasts "the latest available quarter" from whatever features exist (a nowcast). It has no forecast origin, no publication-time filter and no record of which inputs were used. | New package `app/quarterly/` (`periods`, `config`, `registry`, `eligibility`, `completeness`, `update`), `scripts/quarterly_update.py`, `config/forecast_period.json`, `config/quarterly_sources.json`, `app/api/v1/quarterly.py`, `app/api/router.py` | Target, news window and cutoff now come from configuration. News is eligible **only by original publication time (PHT)** within window and cutoff; undated news is quarantined. Inputs are hash-registered with vintages. Output is one forecast record shared by the API, dashboard and PDF. The cycle reports INSUFFICIENT_DATA instead of reusing stale data. | `tests/test_quarterly_pipeline.py` (25 tests incl. the 2027-Q1 → 2027-Q2 transition) | The old pipeline is left in place (not deleted). The new process is the documented one. |
| F4 | **Withdrawn second agency in user-facing text and the admin e-mail allowlist.** | `app/main.py`, `app/services/report.py` (PDF header), `app/services/security.py`, `app/db/models.py`, `app/tasks/scheduler.py`, `app/config.py` (`ADMIN_EMAIL_DOMAINS` default now DA only; env can override), `scripts/run_quarterly_pipeline.py`, `scripts/iso25010_summary.py`, `scripts/build_results_docs.py`, `scripts/build_annotation_workbook.py`, `app/ml/features/label_generator.py` | Only DA Region IV-A is named. | `grep` returns 0 hits in `app/`, `scripts/`, `config/` | None |
| F5 | E23's own code (caught by its tests before use): `quarter_complete` compared 23:59:59 against 23:59:59.999999, and a run-clock string made records non-idempotent. | `app/quarterly/config.py`, `app/quarterly/update.py` | Fixed. | `test_full_update_ready_and_consistent`, idempotency check (2 identical content hashes) | None |

## Audit findings that are NOT code defects (disclosed, not "fixed")

| Area | Finding | Evidence |
|---|---|---|
| **Label** | S1 = H + 2D. **68% of label variance is the regional hunger level shared by all five provinces.** Under a training-window median threshold, the 2023-Q4…2026-Q1 test quarters are **37 HIGH / 3 LOW** at lead 1 because hunger rose after 2023. | `runs/20261013T152113Z/data_audit.json`; E23 tables |
| **SWS** | 4 quarters lack a production round (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3), so they have no label. 3 of 21 rounds have single-source verified dates. | `data_inventory/completeness_report.json` |
| **Unemployment** | National series, identical across provinces in every quarter (no provincial LFS table). | same |
| **Constant features** | `trigger_employment` and `trigger_ofw_remittance` are all zero in 2021–2025. They are dropped in-fold automatically (no effect). | `data_audit.json` |
| **Missing government features** | 2021-Q1 rows lack t−1 values (2020-Q4 is outside the window). They are left missing, never zero. | `data_audit.json` |
| **Poverty incidence** | Excluded as a model feature: stored values do not follow PSA release dates (E17). | E17 timing audit |
| **LGU poverty** | **126 of 142 LGUs use the province-mean fallback.** Within-province order for those LGUs comes from density alone. Disclosed on every ranking row. | `rankings/ranking_verification.json` |
| **Model behaviour** | The largest SHAP contributions come from trending price **levels** (`food_cpi`, commodity prices). These act as a time proxy. The FSSI ranks 7th of 44 under the primary target at lead 1, and the news block carries 5.7% of SHAP. | `runs/.../fold_meta_origin.json` |
| **News corpus** | Duplicates, irrelevant or mis-assigned articles, and publication versus retrieval dates **could not be re-audited**: the corpus files are mixed with 2026 rows and are not authorized (hash-only). Earlier audits (E9–E17) found FSSI forward-filled in most cells and false geocodes (for example, the "Lopez" surname). | `AUTHORIZATION_ALLOWLIST.md`; prior reports |
| **API / map / PDF agreement** | The served API (`aipheed.db`, models) could not be run: those files are hash-only. The new quarterly endpoint is tested in isolation and serves the same record as the dashboard JSON and PDF (content hash test). | `tests/test_quarterly_pipeline.py::test_api_router_serves_the_same_record`; `dashboard_dev/src/test/e23.test.ts` |
| **Frontend dependencies** | `npm audit --omit=dev`: 20 vulnerabilities (16 high, 4 moderate), e.g. `@remix-run/router`, `brace-expansion`. Not fixed: `node_modules` is a junction to the original `frontend/`. | `DASHBOARD_AND_TECHNICAL_QUALITY.md` |
| **Python environment** | `pip check`: weasyprint 68.1 wants tinycss2 ≥ 1.5.0 (1.4.0 installed). Not changed. | same |

## Did any fix change a scientific conclusion?

**No.**

- F1 cannot be measured without the corpus, and the features were not rebuilt.
- F2–F5 affect serving and process, not the evaluation data.
- The E23 conclusions rest on the eligible `features_fused` and the label components, exactly as in E17/E18.
