# Data-Access Risk Map (review revision r2)

**Status: 2026-10-12, review only. No test was run or modified. No data file was loaded.** Sources: code reading (grep and line reads) and file metadata.

**Labels:**

- **Carrier:** coverage unknown, treated as protected.
- **Protected:** P1/P2 rows documented, or fetched live from the source.

## 0. Scheduled tasks: authorization check and status

**Authorization: none.** No message in this conversation authorizes disabling the tasks or stopping their sessions; earlier messages prohibited it. **Nothing was changed.**

**Status recorded 2026-10-12, 18:40 local:**

- Task `aipheed`: enabled, next run 2026-10-13T01:02:41Z.
- Task `aipheed-auditing`: enabled, next run 2026-10-13T07:02:45Z.
- Session `local_f3c4b65e…`: running, last activity 08:10:24Z.
- Session `local_918f3167…`: running, last activity 08:10:41Z.

**Prepared steps, for your review only. Do not run them without approval.**

| # | Tool call (exact) | UI equivalent | Effect |
|---|---|---|---|
| 1 | `update_scheduled_task(taskId="aipheed", enabled=false)` | Scheduled tasks → aipheed → toggle off | Pauses automatic runs. Manual "Run now" still works. Reversible. |
| 2 | `update_scheduled_task(taskId="aipheed-auditing", enabled=false)` | Same, for aipheed-auditing | Same |
| 3 | `stop_session(session_id="local_f3c4b65e-be65-409f-a1c9-1e29c11d1321")` | Open the session → Stop | Interrupts its in-flight turn. **The session stays open and idle**; a queued message would run next. Do not open the transcript. |
| 4 | `stop_session(session_id="local_918f3167-4ff0-47f4-bc3b-115ea28d8055")` | Same | Same |
| 5 | Re-run `list_scheduled_tasks` and `get_session` | — | Records the "after" status |

**Correction to the previous review:** `stop_session` interrupts a turn; it does not close the session (from the tool definition). To close a session fully, archive it, which would be a separate decision.

## 1. Tests that load protected or carrier data

The previous review said four test files did this. **The correct count is at least 11.**

| Test file | Path to data | Data reached | Class |
|---|---|---|---|
| `test_devprotocol_rule_l`, `test_e2_relative_cpi`, `test_e3_compact_lgbm`, `test_e4_risk_definitions`, `test_e5_scoring`, `test_exploratory_runner`, `test_datadriven_trainer`, `test_revised_scoring` | `development_frame()` → `window2021_study.window_frame` → `improvement_study.corrected_features` / `reliability_diagnostics.load` | `sws_hunger.parquet` (lines 53/110/126), `corpus_geocoded.parquet` (W:77), `fssi_quarterly`, `trigger_proportions`, `oil_prices`, `bsp_macro`, `pagasa_climate`, `province_rainfall`, `features_fused`, `labels`, `psa_indicators` | **Carriers:** `sws_hunger`, corpus, news tables. `oil_prices`/`bsp_macro` have unknown coverage. |
| `test_improvement_corrections` | `corrected_features()`, `corrected_frame()`; direct reads of `oil_prices`, `province_rainfall`, `psa_indicators`; iterates frame `sws_hunger` values (line 77) | As above | Carriers; a failing assertion could print values |
| `test_window2021`, `test_origin_info` | `window_frame` / `window_features(extend=True)`; `origin_info_study` reads `corpus_geocoded` and `data/processed/{tab}` | Corpus, news, `sws_hunger` | Carriers |
| `test_api_dashboard`, `test_api_ranking` | Real `models/lgbm_best.pkl` through `Predictor`/`Explainer`, plus `features_fused`, `bias_weights`, `trigger_proportions`. `dashboard.py` reads `corpus_geocoded` (line 826). | Model (P4?), corpus | Carriers |
| `tests/conftest.py` | Loads `models/lgbm_best.pkl` if present (line 106) | Model | P4? |
| `test_governing_model`, `test_risk_score_v2`, `test_api_assessments` | `features_fused`, `labels`, `psa_indicators`, served artifact | Allowlist candidates and this session's own artifacts | Low |
| `test_generalization_protocol` | Imports `generalization_study`. Whether it calls `data_audit()`, which reads `cpi_full` and `feature_provenance.json`, **was not traced**. | Possibly `cpi_full` | Carrier, if called |
| **Production** `test_quarterly_pipeline` | `tmp_path` sandbox with stubbed stages (lines 25–41) | Appears isolated; not fully traced | Low (unverified) |
| **Production** `test_api_admin` | Temporary database | — | Low |
| **Production** `conftest.py` | Imports `app.main`. The modules it imports were not traced. | Unknown | Unknown |

## 2. Scripts and services that can reach protected data

| Code | Reaches | Class |
|---|---|---|
| Production `app/services/dashboard.py` → `thesis_predictor` / `thesis_explainer` | `data/thesis/panel.parquet` + `thesis_food_insecurity_model.joblib` | **Protected (P3).** **Running the production backend and opening the dashboard** (frontend default API `http://localhost:8000`, `/api/v1/provinces?quarter=…`) can display panel-derived 2026-Q3 values. |
| Fetchers: `openstat_fetcher`, `cpi_full_fetcher`, `sws_hunger_fetcher`, gnews/rss (both backends); `refresh_all_sources.py`, `run_quarterly_pipeline.py` (isolated), `quarterly_pipeline.py` (production) | Live PSA/SWS/news sources up to the run date | **Direct P1/P2 acquisition.** Never run during the blind period. |
| `generalization_study.data_audit` | `cpi_full`, `feature_provenance.json` | Carrier |
| GN group (`datadriven_trainer.GROUPS`) includes `headline_cpi` and `food_minus_headline_yoy` | National CPI series | P2 for 2026-07 to 2026-12 reference months. Inputs at T−2 only. |
| E1–E7 runners | `development_frame` (carriers as in §1) | Carrier (already run) |

**Whether earlier runs printed or used 2026-H2 rows:** no evidence either way. Passing tests and finished runs printed no values that this session saw; that is the only evidence.

## 3. Proposed isolated test fixture (not implemented)

1. **`tests/fixtures/safe_frame/`**, built by a deterministic generator script with a fixed seed and no input files.
   - Five province codes, quarters 2021-Q1 to 2025-Q4 only.
   - Synthetic SWS rounds, provincial food CPI YoY and `poverty_incidence`, with the same column names and dtypes as the real frame.
   - No real values, and no quarter at or after 2026-Q3.
2. **Path redirection** through a pytest fixture that monkeypatches the module path constants (`P` in `reliability_diagnostics`, `improvement_study` and `window2021_study`; `LABELS_PATH`/`PSA_PATH` in `revised_trainer`; `SUPP_SWS`/`CPI_DATES` in `devprotocol_rule_l`; the `Predictor`/`Explainer` paths) to the fixture directory.
3. **Session-wide guard** in `conftest.py`:
   - an audit hook plus wrappers around `pd.read_parquet`, `pyarrow.parquet.*` and `joblib.load`;
   - any test touching the deny-list fails. The deny-list is: the `backend/` data and models, `cpi_full*`, `sws_hunger*`, `corpus_*`, `fssi_quarterly`, `trigger_proportions`, `topic_proportions`, `zs_rescore`, `*.db`, `mlruns`, `models/*.pkl`.
4. **Optional approved-historical layer:** hash-pinned copies of allowlist files restricted to quarters ≤ 2025-Q4. Building those copies needs a key-filtered read (approval required).
5. **Markers:** `@pytest.mark.real_data` for tests that must touch real files. These are excluded by default and run only under the guard with approval.
