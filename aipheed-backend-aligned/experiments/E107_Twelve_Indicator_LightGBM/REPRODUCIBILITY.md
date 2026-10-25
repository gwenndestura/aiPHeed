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
