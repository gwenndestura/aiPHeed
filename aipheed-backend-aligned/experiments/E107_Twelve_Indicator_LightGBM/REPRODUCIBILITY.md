# E107 Deliverable F: reproducibility and integration

## Files

| Kind | Path (from `aipheed-backend-aligned/experiments/E107_Twelve_Indicator_LightGBM/`) |
|---|---|
| Protocol and addenda (hash-frozen) | `PROTOCOL.md`, `ADDENDUM_1.md`, `ADDENDUM_2.md`; hashes and UTC times in `runner/*_SHA256.txt`, `runner/*_FROZEN_AT.txt` |
| Feature/label library | `runner/e107_lib.py` (indicator inventory, issue-date cuts, the 13 columns, T43/R labels, label availability) |
| Model, arms, metrics | `runner/e107_model.py` (grid, nested selection, SP prior, logistic baselines, sealed comparators, metrics, paired tests) |
| Runner | `runner/run_e107.py` (phases `dev`, `final`, `diag`, `prospective`, `export`) |
| Extra inputs (byte copies, hashed) | `data_inputs/pagasa_climate.parquet`, `bsp_macro.parquet`, `psa_rice_prices.parquet`, `SHA256SUMS.txt` |
| Development outputs | `out/dev/` (predictions per target and lead, `metrics.json`, `origin_records.json` with per-origin configuration, inner log-loss, SHAP and gain, `run.json` with the git commit) |
| Final-block outputs | `out/final/` (same layout; scored once) |
| SP development rows | `out/dev_sp/` (primary probabilities asserted identical to `out/dev/`) |
| Combined predictions | `out/predictions_{T43,R,T43ext}_lead{1..4}.csv` (every arm per row) |
| Results and decisions | `out/results.json` |
| Diagnostics | `out/diagnostics.json` (ablations, SHAP and gain shares, common rows, sensitivities S1–S3) |
| Sealed prospective forecasts | `out/sealed_prospective.csv`, `.sha256`, `out/prospective_record.json` |
| Tests | `backend/tests/unit/test_e107.py` |
| Read-only API | `backend/app/api/v1/e107.py` (`/api/v1/e107/evaluation`, `/forecast`, `/indicators`), files in `backend/data/e107/` |

## Commands (Windows; the backend virtual environment of the main checkout was used)

```bash
cd aipheed-backend-aligned/experiments/E107_Twelve_Indicator_LightGBM/runner
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e107.py dev
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e107.py final
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e107.py diag
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e107.py prospective
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e107.py export
```

`final` refuses to run when `out/final/` already exists (the final block is scored once); `combine` rebuilds `results.json` from
stored predictions without re-scoring.

Environment: Python 3.13, LightGBM 4.6.0, SHAP 0.51.0, pandas 2.3.3, scikit-learn 1.8.0. LightGBM runs with `deterministic=True`,
`force_row_wise=True`, one thread and seed 107, so the predictions are reproduced exactly (test `test_stored_predictions_reproduce`).

## Commit trail (branch `aipheed/e107-twelve-indicator-lightgbm`)

| Commit | Content | Before or after scoring |
|---|---|---|
| `1d95a77` | Audit (Deliverable A) and the three hashed input files | before any change |
| `ab01ef2` | Protocol (sha `f652327b…`, frozen 02:18 UTC) and the feature/label library | before scoring |
| `9dfbae4` | Model, runner, leakage tests | before scoring |
| `ec0f2f3` | Addendum 1 (eligibility) and its code | after the development run printed row counts; no metric seen |
| `55887c3` | Development results and Addendum 2 (one exploratory revision) | after development, before the final block |
| `6c720c2` | SP arm code | **the commit the final block was scored with** (`out/final/run.json`, runner clean) |
| `650e4d3` | Final block, diagnostics, sealed forecasts, reports, read-only API | after |

**Changes to the runner after the final run** (`650e4d3`), none of which affects the final-block predictions:
- a fix to the S1 helper's empty-frame handling;
- the SP/STRUCT columns in the prospective phase;
- the export phase.

**Prospective seal.** The seal (`out/sealed_prospective.csv`, sha `246700a8…`) was produced before `650e4d3` with that code uncommitted. Re-running `phase_prospective` from the committed code reproduces the file byte-for-byte (same SHA-256; checked 2026-10-25).

## Verification run on 2026-10-25

- `backend/tests/unit/test_e107.py`: **51 passed**. Coverage:
  - completeness;
  - future perturbation (24 cases);
  - backend as-of inputs;
  - split integrity (8 cases);
  - target alignment, horizons and window;
  - reproduction of stored predictions;
  - frozen protocol;
  - seal;
  - API.
- Full backend suite: **621 passed, 18 skipped, 0 failed** (pytest, 2 min 3 s).
- The frontend is untouched: `git diff 9433f9e -- frontend` is empty.

## Deployment status

- **Local only.** Nothing is merged into `main`, the branch Render deploys from.
- The production dashboard and API still serve FIRI v2 / E56, unchanged.
- The new `/api/v1/e107/*` routes exist only on this branch and were verified through FastAPI's TestClient, not on a deployed server.
- The branch was pushed to `origin` on 2026-10-25 as **`aiPHeed/e107-twelve-indicator-lightgbm`** (head `cf649d5`, then this note).
  - Windows case-folding stored the local ref under the existing `aiPHeed/` folder, so this is the same branch that the documents call `aipheed/e107-twelve-indicator-lightgbm`.
  - Pushing does not deploy.
