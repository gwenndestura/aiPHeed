# Reproducing E25

## Setup

| Item | Value |
|---|---|
| Python | `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe` (3.13). Package versions are recorded in every run's `manifest.json`. |
| Working directory | `aipheed-backend-aligned/experiments/E25_Reliable_Forecasts_2021_2026/` |
| Seeds | LightGBM `random_state` 42, `deterministic=True`, `n_jobs=1`; tests and bootstraps 20261013; simulation 20261014 |
| Branch | Run on branch `ui/no-data-quarters-risk-band`. The read-only experiments and the E12 inputs exist complete only in commit 5113ae5 (branch `e25-window-2021-2026`), so step 0 extracts them read-only, without switching branches. |

## Commands, in order

| Step | Command | Output |
|---|---|---|
| 0 | `git -c core.autocrlf=false archive 5113ae5 aipheed-backend-aligned \| tar -x -C <scratch>` (from the repo root) | Read-only snapshot |
| 1 | `python -B runner/verify_readonly.py <scratch>` | `runs/readonly_verification.json`, `docs/READONLY_VERIFICATION.md` |
| 2 | `python -B runner/materialize_inputs.py <scratch>` | `inputs/` (byte-identical to the pins), `inputs/PINS.json`, `inputs/INPUTS_MANIFEST.json` |
| 3 | `python -B runner/inspect_inputs.py > runs/inspect_inputs.txt` | Structure of the authorized inputs |
| 4 | `python -B runner/reachability.py` | **Before any model:** `runs/reachability.json`, `docs/REACHABILITY.md` |
| 5 | `python -B runner/power_sim.py` | Synthetic power: `runs/power_sim.json`, `docs/POWER_SIMULATION.md` |
| 6 | (frozen) `runner/PROTOCOL_SHA256.txt` | Protocol, idea log part 1, `e23_lib.py`, `pcf.py`; runners refuse if they changed |
| 7 | `python -B runner/run_e25.py --synthetic 1` | Debug on synthetic data only (`runs/SYNTH_*`) |
| 8 | `python -B runner/run_e25.py` (about 4 minutes) | **Primary run** `runs/20261014T002026Z/`: predictions + SEALS, details, fold metadata, `results.json`, `metrics_all.csv`, `tests_all.csv`, `manifest.json` |
| 9 | `python -B runner/run_e25.py` again | Repeat `runs/20261014T002520Z/` |
| 10 | `python -B runner/monthly_d_eval.py` (twice) | `runs/MONTHLY_*` |
| 11 | `python -B runner/reproduce.py <run1> <run2> <monthly1> <monthly2>` | `runs/reproducibility.json` (C8) |
| 12 | `python -B runner/seal_e25.py`, then `--verify` | `runs/SEAL_E25_20261014T002548Z/` (written once) |
| 13 | `python -B runner/completeness.py` | `DATA_COMPLETENESS_MATRIX.csv`, `runs/completeness_summary.json` |
| 14 | `python -B runner/lgu_rankings.py [--sae PATH --sae-sha256 HASH]` | `LGU_RANKING_VALIDATION.csv`, `runs/lgu_validation.json` |
| 15 | `python -B runner/export_pipeline_inputs.py 20261014T002026Z` | `backend_dev/data/inputs/*`, `backend_dev/config/*` |
| 16 | In `backend_dev/`: `python -B -m scripts.quarterly_update run` | `backend_dev/data/quarterly_runs/2027-Q1/forecast_record.json` |
| 17 | `python -B runner/build_outputs.py 20261014T002026Z` | `BASELINE_COMPARISON.csv`, `PREDICTIONS_BY_QUARTER.csv`, `FEATURE_ABLATION_RESULTS.csv`, the timeline record (3 identical copies), the PDF |
| 18 | `python -B -m pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/` | 38 tests |
| 19 | In `dashboard_dev/`: `npx vitest run`; `npx vite build --outDir dist-e25` | 18 tests; build |
| 20 | Score sealed forecasts (**only after you authorize outcomes**): `python -B runner/score_sealed.py runs/SEAL_E25_20261014T002548Z` | Refuses (exit 2) until `inputs/AUTHORIZED_OUTCOMES.json` exists |

**Folder hashes:** `E25_FILES_SHA256.txt` (generated last). It excludes `node_modules`, `.vite-cache`, `dist-e25` and `__pycache__`.
