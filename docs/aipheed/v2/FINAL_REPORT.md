# AIPHEED v2: final report

**Tags:**
- VERIFIED: a command was run and its output is saved at the path given;
- INFERRED: reasoning from verified numbers or code;
- NOT VERIFIED.

**Branch:** `impl/backend-completion` (continued from `9f975ec`). Local only: nothing pushed, deployed or downloaded.

**Documents** (cross-linked, no duplication):
- `DIAGNOSIS.md`: Step 1, Gate 1;
- `PREREGISTRATION.md`: Steps 2–3, hashed before fitting;
- `METHODOLOGY_V2.md`: one page, flowchart;
- `MODEL_REPORT_V2.md`: metrics, CIs, baselines, overfitting, bias, leads;
- `TEST_REPORT.md`;
- `DEVIATIONS.md`;
- updated `../API.md`, `../ARCHITECTURE.md`, `../DATA_INVENTORY.md`;
- progress log `../PROGRESS.md`.

## 1. Three verdicts

### A. Software: YES

| Item | Evidence |
|---|---|
| New methodology integrated as an additive, read-only API path (`/api/v1/hunger-forecast/v2`). Inference loads only the hashed artifact, never refits, validates, fails loudly and stores provenance. | `tests/unit/test_v2_core.py` (VERIFIED) |
| Defects: D3, D4 and D9 handled (§4) | `test_v2_defects.py`, `test_v2_paths.py` (VERIFIED) |
| Tests: **1317 passed, 0 failed, 18 skipped (pre-existing)**; 37 new v2 tests | `results/final_tests_v2.txt` (VERIFIED) |
| Coverage, measured: **88.4 %** of lines (918/1038) in `app/forecasting/` (incl. v2 90.9 % and safe_load), the hunger-forecast router and `app/paths.py` | `results/coverage.txt` (VERIFIED) |
| Mutation spot-check: 5 planted bugs (as_of, lead/target, inner truth, news asof, FIRI prior), 5 killed | `results/mutation_check.txt` (VERIFIED) |
| E2E twice on real data: identical. Artifact hash, store, API and seal all reproduced. | `results/v2_e2e_run.json` (VERIFIED) |
| Validation rerun gives byte-identical results files | `git diff` empty after rerun (VERIFIED) |
| Protocol lock and pre-registration hashes, re-verified at the end | `test_protocol_lock.py`, `test_v2_preregistration.py` (VERIFIED) |

### B. Research: NO (75 % not met; Lead 2 not reliable; no reliable lead)

| Question | Answer |
|---|---|
| **Gate 1 oracle bound** | **75 % at Lead 2 is NOT ACHIEVABLE with existing measurements.** Knowing today's true level exactly gives 42.5 %. A forecaster would need to predict ≈ 85 % of the true 3-quarter change variance, and no held measurement predicts any of it repeatably (DIAGNOSIS). |
| **75 % on DEVELOPMENT data?** | **No.** V2 (= persistence, chosen by the pre-registered rule at all 22 issues) gets 16/40 = **40.0 % [95 % CI 25.0–57.5]** at Lead 2. The best of all models re-scored on the same rows is HFM-X at 50.0 % [32.5–67.5], not distinguishable from persistence. |
| **75 % on SEALED / FUTURE data?** | **Not yet testable.** No historical quarter was unseen (0 < 6), so the sealed set is future quarters. The prospective seal (2026-Q4 … 2027-Q3) has 0 scorable rows today. |
| **Lead 2 reliable?** | **No.** Development: N2, N4 and N5 fail. Future: NOT_YET_TESTABLE. |
| **Maximum reliable lead** | **None** (development); not yet testable (future) |

Development success would not have been reported as research success; here there was none.

### C. Data sufficiency

1. **Unseen SWS quarters:**
   - ≥ 10 unseen Lead-2 target quarters for N1: 2026-Q4 … 2029-Q1, complete about **2029-05** if every quarter has a round. The frozen W2 decision date is 2029-Q3.
   - 16–39 quarters for a decisive test of 75 %, if the true share is 0.90–0.85 (DIAGNOSIS Q4).
   - **Scheduled checks:** run `python -I backend/scripts/v2_score_sealed.py` after each SWS release. The first is 2026-Q4, scorable about 2027-02 (+120 days completeness rule).
2. **A leading indicator of hunger change** at SWS-area level that predicts ≈ 85 % of three-quarter change variance. This is the only route to 75 % (Gate 1).
   - Untested candidate: regional quarterly LFS.
   - It needs an external download and owner approval; it was not done here.
3. **A provincial food-insecurity measurement** (for example CBMS 2024 FIES via an official request) for any provincial or LGU claim. Until then, provincial and LGU values stay `null` / `AWAITING_GROUND_TRUTH`.

## 2. Decisions and why

| Decision | Why |
|---|---|
| Diagnose before modelling; Gate 1 first | Operating principle 1: legitimacy over success. The bound shows 75 % needs information that does not exist in the repository. |
| Only 3 candidates: PERSIST, LL, LL-K | Only the anchor's sampling noise was found forecastable. Seasonality, trend, mean reversion, bias correction, exogenous drivers and ensembles were each rejected with evidence before fitting (PREREGISTRATION §1.3). |
| Nested inner-fold selection with a paired block-bootstrap CI | Prevents choosing a model on the outer rows; the simplest model wins ties |
| Sealed set = future only | All 2021–2026-Q3 quarters had been seen; sealing them would be theatre |
| V2 serves persistence | The pre-registered rule chose it at every issue. Explained honestly as "last observed value carried forward", with a conformal interval. |
| P0H4 relabelled "price-pressure risk index" at the API; computation and `id` unchanged | The number varies across provinces only through prices; it must not be presented as food insecurity |
| `firi.py` and `scheduler.py` excluded from the D4 rewrite | `firi.py` is hash-frozen by 7 experiment guard tests. The scheduler's test sandboxes by `chdir`. Both stay cwd-relative (correct under Docker and from `backend/`). |
| D9 pickle not restored | It exists in history but was deliberately removed in `8725531e` (abandoned pipeline). It still fails loudly. Restoring it is the owner's call. |
| Frontend copy not changed | About 25 strings (for example the landing title "Food Insecurity Risk Forecasting System") are approved UI copy and part of the thesis framing. The API now carries the corrected label and a pointer to the hunger forecast. |

## 3. Final metrics (DEVELOPMENT; S-U, P-DASH; VERIFIED, `results/v2_metrics.csv`)

| Lead | V2 within [95 % CI] | MAE | RMSE | Bias | High-tercile bias | 80 % coverage | N1–N7 |
|---|---|---|---|---|---|---|---|
| 1 | 47.7 % [31.8, 65.9] (21/44) | 5.05 | 6.76 | −2.38 | −6.75 | 0.64 | NOT_RELIABLE |
| **2** | **40.0 % [25.0, 57.5] (16/40)** | 5.98 | 7.71 | −3.07 | −7.66 | 0.725 | **NOT_RELIABLE** |
| 3 | 36.1 % [13.9, 58.3] (13/36) | 6.46 | 8.49 | −3.83 | −9.45 | 0.75 | NOT_RELIABLE |
| 4 | 37.5 % [12.5, 62.5] (12/32) | 6.51 | 8.99 | −4.56 | −10.06 | 0.81 | NOT_RELIABLE |

Baselines, overfitting, by-period results and leakage controls are in MODEL_REPORT_V2.

## 4. Defects

| ID | Status | Evidence |
|---|---|---|
| D1 served target is a composite | **Relabelled** at the API: "Price-pressure risk index", `is_food_insecurity_measurement: false`, pointer to `/api/v1/hunger-forecast/v2`. Computation unchanged. | `test_v2_defects.py` |
| D3 sklearn pin vs pickle | **Fixed.** Re-exported to `models/thesis_food_insecurity_model_skl180.joblib` (manifest entry; original kept). Scores identical on 135/135 panel rows; no version warning; loaders switched. | `scripts/reexport_thesis_model.py`, test |
| D4 cwd-relative paths | **Fixed**, with 2 documented exceptions. `app/paths.py`; 141 literals in 48 modules; `.env` and relative SQLite in `config.py`. The API is identical from `backend/` and the repo root (fresh subprocesses). | `test_v2_paths.py` |
| D5 legacy feature paths without as_of | **Leak tests added** that fail when the leak is injected: FIRI v2 prior, news `asof`, dashboard cutoff | `test_v2_legacy_leakage.py`, mutation check |
| D9 missing `lgbm_best.pkl` | **Documented, not restored** (§2); fails loudly | test |

## 5. Files

**Created:**
- **Package:** `backend/app/paths.py`; `backend/app/forecasting/v2/` (`__init__`, `models`, `select`, `verdict`, `artifact`, `inference`, `explain`, `store`).
- **Scripts:** `backend/scripts/v2_diagnosis.py`, `v2_validate.py`, `v2_seal.py`, `v2_score_sealed.py`, `v2_context.py`, `v2_e2e.py`, `v2_coverage.py`, `v2_mutation_check.py`, `reexport_thesis_model.py`.
- **Tests:** `backend/tests/unit/test_v2_preregistration.py`, `test_v2_core.py`, `test_v2_defects.py`, `test_v2_paths.py`, `test_v2_legacy_leakage.py`.
- **Data:**
  - `backend/data/forecasting/artifacts/v2_2026-10-01.json` (SHA-256 `2614c8ce…4011`);
  - `backend/data/forecasting/forecasts_v2/2614c8ceec0d2c0e_2026-08-24_2026-10-01.json`;
  - `backend/data/forecasting/context/context_2026-10-01.json`;
  - `backend/models/thesis_food_insecurity_model_skl180.joblib`.
- **Docs:** `docs/aipheed/v2/*` (6 documents, `results/`, `sealed/`).

**Modified:**
- `app/api/v1/hunger_forecast.py`: v2 routes; legacy status text.
- `app/ml/inference/ch1_system.py`: indicator label only.
- `app/ml/inference/thesis_predictor.py`, `thesis_explainer.py`: re-exported pickle.
- `app/config.py`: `.env` and SQLite path.
- 48 modules: `backend_path` for relative paths.
- `backend/models/MODEL_MANIFEST.json`: one entry added.
- `.gitattributes`: v2 sealed/results stored byte-for-byte.
- `docs/aipheed/{API, ARCHITECTURE, DATA_INVENTORY, PROGRESS}.md`: v2 sections appended.

**Removed:** none. No experiment package, seal, artifact or earlier result was deleted or overwritten. A stray empty `aipheed.db`, created in the repo root by one of my own test runs before the SQLite path fix, was removed.

## 6. Reproduction (repository root, backend venv)

```
python -I backend/scripts/v2_diagnosis.py
python -I backend/scripts/v2_validate.py
python -I backend/scripts/v2_score_sealed.py
python -I backend/scripts/v2_e2e.py
cd backend
python -m pytest -q -p no:cacheprovider
python -I scripts/v2_coverage.py
python -I scripts/v2_mutation_check.py
```

**Write-once steps:** `v2_seal.py`, `python -m app.forecasting.v2.artifact build`, `python -m app.forecasting.v2.store run` and `reexport_thesis_model.py` refuse to overwrite. The E2E run rebuilds the artifact and store in a temporary directory and compares them.

## 7. Limitations of this work

- **No external data:** no data were downloaded (regional LFS untested) and no credentials were used.
- **Not re-executed:** the NLP model pipeline (article store and model weights) was not re-executed. The news leak test exercises the `asof` selector with injected articles.
- **Frontend copy** still says "food-insecurity risk" for the P0H4 value (owner decision, §2).
- **Coverage method:** coverage was measured with a standard-library tracer, not coverage.py; the method is stated in `results/coverage.json`.

## 8. Git state

See TEST_REPORT §1 and PROGRESS (final entry) for the final commit hash and `git status`. The 15 untracked paths that predate this work remain untracked and untouched.
