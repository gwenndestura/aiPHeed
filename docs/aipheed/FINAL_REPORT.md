# AIPHEED backend completion: final report

**Tags:** VERIFIED (command run, output saved at the path given), INFERRED (read from code or documents), NOT VERIFIED.

**Branch:** `impl/backend-completion`, created from `aiPHeed/corrected-data-pipeline` @ `2d9a2d9`. Local only: nothing pushed or deployed.

**Commit and status:** see §9.

## 1. Three verdicts

**A. Software: YES**

| Item | Status | Evidence |
|---|---|---|
| Critical and High defects fixed | D2 (pickle integrity) and D10 (unhandled 500) are fixed. D1 (served target is a composite probability) is a research-validity defect that needs your decision. | AUDIT.md (VERIFIED by tests) |
| Tests | 1280 passed, 0 failed, 18 skipped (pre-existing) | `final_tests.txt` (VERIFIED) |
| End to end | Two runs are byte-identical | `results/e2e_run.json` (VERIFIED) |
| Reproducible | Rebuilt artifact hash equals the committed one; backend models equal the research implementations to < 1e-9 | `results/e2e_run.json`, `model_report.py` assertion (VERIFIED) |

Coverage was **not measured** (TEST_REPORT).

**B. Research: NO**

| Item | Result | Evidence |
|---|---|---|
| 75 % target met? | **No.** The best Lead-2 share within the frozen tolerance is HFM-X at 50.0 % [95 % CI 32.5–67.5] (20 of 40 rows, S-U). The selected model, persistence, reaches 40.0 % [25.0–57.5]. | `results/metrics.csv` (VERIFIED) |
| Lead 2 reliable? | **No.** No model passes N1–N7. Persistence fails N2, N4 and N5. | `results/reliability.csv` (VERIFIED) |
| Maximum reliable lead | **None** | `results/run_config.json` (VERIFIED) |

This is development evidence: all 2021–2026-Q3 values had been seen before.

**C. Data sufficiency: external measurements still needed**
1. **≥ 10 unseen Lead-2 SWS quarters** (2026-Q4 onward; the earliest decision is 2029-Q3), for N1 and confirmation.
2. **A leading indicator of hunger change** at SWS-area level. Regional quarterly LFS (in PSA releases) is untested.
3. **A provincial food-insecurity measurement** (CBMS 2024 FIES via an official request) for any provincial claim. Until then the provincial and LGU estimates are `null` / `AWAITING_GROUND_TRUTH`.

## 2. Model decision and why

- **The pre-declared rule** (`SELECTION_RULE.md`, committed before the run) selects **PERSIST**. Against persistence, Δ within at Lead 2 is:

  | Candidate | Δ within | Paired block-bootstrap 95 % CI |
  |---|---|---|
  | SEAS-LLM | +0.05 | [−0.10, +0.20] |
  | HFM-X | +0.10 | [−0.125, +0.325] |
  | TREND-D | −0.10 | — |

  None is distinguishable from zero, so the simpler model stays.
- **The new read-only endpoint serves SEAS-LLM**, because you approved it as the prospective primary (E134 Addendum 2). Every record shows its latest SWS reading (= persistence), the model hash, the vintage, the evidence status and `NOT_RELIABLE`.
- **The dashboard's served model is unchanged:** P0H4 Chapter I risk probability (AUDIT D1).
- **Decisions left to you:**
  - whether the new endpoint should serve PERSIST instead of SEAS-LLM;
  - whether anything should replace P0H4 on the dashboard.

## 3. Final metrics (S-U, P-DASH, Lead 2, 40 rows / 10 target quarters; VERIFIED)

| Model | n within | % within [95 % CI] | MAE | RMSE | Bias | High-tercile bias | Sharp increases within | 80 % coverage |
|---|---|---|---|---|---|---|---|---|
| PERSIST (selected) | 16 | 40.0 [25.0, 57.5] | 5.98 | 7.71 | −3.07 | −7.77 | 0/16 | 0.70 |
| TREND-D | 12 | 30.0 [20.0, 42.5] | 7.17 | 8.87 | −2.90 | −7.48 | 1/16 | n/a |
| SEAS-LLM (served on the new endpoint) | 18 | 45.0 [22.5, 67.5] | 5.72 | 7.58 | −3.19 | −7.64 | 3/16 | 0.73 |
| HFM-X | 20 | 50.0 [32.5, 67.5] | 4.87 | 6.42 | −2.53 | −7.14 | 8/16 | 0.75 |
| X-RED (reported only) | 19 | 47.5 [30.0, 65.0] | 4.79 | 6.23 | −2.97 | −7.38 | 3/16 | 0.75 |
| SIMPLE (reported only) | 19 | 47.5 [30.0, 65.0] | 4.75 | 6.15 | −2.98 | −7.29 | 3/16 | 0.80 |
| RIDGE-ALL (S-E132, 28 rows) | 11 | 39.3 [25.0, 53.6] | 7.36 | 9.30 | — | — | — | train-test MAE gap +5.28 |

Leads 1, 3 and 4 and the S-E132 rows are in `MODEL_REPORT.md` and `results/metrics.csv`.

## 4. Key fixes

| ID | Fix | Evidence |
|---|---|---|
| D2 | Pickled artifacts are loaded only through `app/forecasting/safe_load.py`: a SHA-256 manifest check, and only files under `backend/models/`. All 6 `joblib.load` sites now use it. | `test_safe_load.py` (VERIFIED) |
| D10 | A missing legacy assessment artifact now gives 503 with a JSON message, not an unhandled 500 | `api_audit_run.txt`, test (VERIFIED) |
| D5 (new path) | One point-in-time selector (`as_of`) with leak tests that **fail when a leak is injected** | `leak_injection_demo.txt` (VERIFIED) |

**Logged, not changed** (they need your approval or carry risk to the served system):
- D1: the served target is a composite;
- D3: scikit-learn 1.7.2 pickle against the 1.8.0 pin;
- D4: cwd-relative paths;
- D6: API surface;
- D9: missing legacy pickle.

## 5. Files

**Created:**
- `backend/app/forecasting/` (12 modules): the forecasting core.
- `backend/app/api/v1/hunger_forecast.py`: read-only routes.
- `backend/scripts/{build_protocol_lock, model_report, api_audit, e2e_hunger_forecast}.py`: reproducible evidence.
- `backend/data/forecasting/`:
  - `sws_area_rounds.csv`: a byte-identical copy of the E110 target file, so the backend does not depend on `experiments/`;
  - `artifacts/seas_llm_2026-10-01.json`;
  - `forecasts/09ee23b09a0207c8_2026-08-24_2026-10-01.json`;
  - `.gitattributes`.
- `backend/models/MODEL_MANIFEST.json`: force-added, because `backend/models/` is gitignored.
- `backend/tests/unit/{test_protocol_lock, test_safe_load, test_forecasting_core}.py`.
- `docs/aipheed/*`:
  - PROTOCOL_LOCK (+ sha256, manifest), AUDIT, DATA_INVENTORY, SELECTION_RULE, MODEL_REPORT, METHODOLOGY, ARCHITECTURE, API, TEST_REPORT, FINAL_REPORT, PROGRESS;
  - `results/*`;
  - test logs.

**Modified:**
- `app/api/router.py`: registers the new router (additive).
- `app/api/v1/assessments.py` and `app/services/assessment.py`: D10.
- `app/ml/inference/{explainer, forecaster, predictor, thesis_explainer, thesis_predictor}.py` and `app/services/report_data.py`: D2 (one import plus the call).

**Removed:** none. No experiment package, seal or model artifact was deleted or overwritten.

## 6. Remaining external needs

See §1 C. No data was fetched and no credentials were used in this work.

## 7. Reproduction (from the repository root, backend virtual environment)

```
python -I backend/scripts/build_protocol_lock.py
cd backend
python -m pytest -q -p no:cacheprovider
python -m app.forecasting.artifact build 2026-10-01
python -m app.forecasting.store run 2026-10-01 data/forecasting/artifacts/seas_llm_2026-10-01.json
cd ..
python -I backend/scripts/model_report.py
python -I backend/scripts/api_audit.py
python -I backend/scripts/e2e_hunger_forecast.py 2026-10-01
```

Notes:
- The protocol-lock builder refuses to rebuild if any locked source changed.
- The artifact build is write-once: it refuses if the file exists. The E2E script rebuilds into a temporary directory and checks the hash.
- The store run is a no-op if the forecast is already stored with identical content.

## 8. Limitations of this work

- **Risk-directed audit:** the served path was traced and all modules were grep-scanned, but not all 185 modules were read line by line.
- **Legacy feature paths** (FIRI, NLP, quarterly) were not rerouted through `as_of`.
- **The NLP pipeline** was not re-executed (needs the article store and model weights): NOT VERIFIED end to end.
- **FIRI** was audited from code, not recomputed.
- **API routes** with path parameters and authenticated flows were covered only by the existing tests.

## 9. Git state and test results at the final commit

**Code state:** the commit that adds this report also contains every code change listed in §5. Its code is the code tested in `final_tests.txt` (1280 passed, 0 failed, 18 skipped).

**`git status`:** the 15 untracked paths that predate this work remain untracked and untouched.

**Commit hash:** recorded in `PROGRESS.md` (final entry), written right after the commit.

---

## Superseded by v2 (2026-11-01)

The v2 methodology redesign (diagnosis, pre-registration, nested validation, integration) is reported in **`docs/aipheed/v2/FINAL_REPORT.md`**. That report holds the current three verdicts, files, metrics and reproduction commands. The sections above remain the record of the backend-completion run and are not repeated there.
