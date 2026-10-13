# Reproducing E24

## Environment

| Item | Value |
|---|---|
| Python | `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe` (Python 3.13). Exact package versions are recorded in each run's `manifest.json`: LightGBM 4.6.0, scikit-learn 1.8.0, SciPy 1.17.1, NumPy, pandas. Also reportlab 5.0.1, pdfminer.six, openpyxl 3.1.5. |
| Node | 24.17. `dashboard_dev/node_modules` is a junction to `C:\Users\admin\aipheed\frontend\node_modules` (read-only use). |
| Working directory | `aipheed-backend-aligned/experiments/2026-10-14_E24_Resolve_Forecasting/` |
| Seeds | LightGBM `random_state` 42, `deterministic=True`, `n_jobs=1`; bootstrap/permutation seed 20261013; power simulation seed 20261014 |

## Commands, in order

| Step | Command | Output |
|---|---|---|
| 1 | `python -B runner/reproduce_and_audit.py` | Reproduces E23 from its seals; label decomposition and error analysis → `runs/reproduction_and_audit.json`, `PREDICTIONS_BY_QUARTER.csv`, `runs/e23_reproduced_metrics.csv` |
| 2 | `python -B runner/lgu_rankings_v2.py [--sae <authorized PSA workbook> --sae-year 2021]` | `LGU_RANKING_VALIDATION.csv`, `runs/lgu_validation.json` (and `data_v2/` only when a workbook is supplied) |
| 3 | `python -B runner/minimum_data.py` | `runs/minimum_data.json` |
| 4 | `python -B runner/run_e24.py` (≈ 7 min; refuses to run if the frozen files changed) | `runs/<id>/predictions_T1.csv`, `predictions_T2.csv` + SEALs, `results.json`, `metrics_all.csv`, `fold_meta_*.json`, `manifest.json` |
| 5 | `python -B runner/posthoc_ablation_tests.py <id>` | Descriptive post-hoc tests |
| 6 | From `backend_dev/`: `python -m scripts.quarterly_update run` | `backend_dev/data/quarterly_runs/2027-Q1/forecast_record.json` |
| 7 | `python -B runner/build_outputs.py <id>` | `BASELINE_COMPARISON.csv`, `FEATURE_ABLATION_RESULTS.csv`, `dashboard_dev/public/e24_dashboard.json`, PDF |
| 8 | `python -B -m pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/` | Python tests |
| 9 | In `dashboard_dev/`: `npx vitest run` and `npx vite build --outDir dist-e24` | Frontend tests and build |
| 10 | `python -B runner/seal_prospective.py --origin-quarter 2026-Q3` | Refuses until 2026 features are authorized (exit 2) |

## Recorded runs

| Run | Purpose |
|---|---|
| `runs/20261013T160107Z` | Primary |
| Second run | Reproducibility; seals compared in `TEST_RESULTS.md` |

**Folder file hashes:** `E24_FILES_SHA256.txt`.

**Data access.** Every read goes through `runner/guard.py`:

- the allowlist is imported from the E17/E18 guards and re-hashed before each read;
- reads of E23 outputs and of `data/reference/*.csv` are allowed;
- everything else in the project, databases, models, `~/.claude`, `subprocess` and `sqlite3` are blocked.
