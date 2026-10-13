# Reproducing E24v2

## Environment

| Item | Value |
|---|---|
| Python | `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe` (3.13). Package versions are written to each run's `manifest.json` (LightGBM 4.6.0, scikit-learn 1.8.0, SciPy 1.17.1, pandas, NumPy). Also `requests` (acquisition), reportlab and pdfminer.six (PDF). |
| Node | 24.x. `dashboard_dev/node_modules` is a junction to `C:\Users\admin\aipheed\frontend\node_modules`, used read-only. |
| Working directory | `aipheed-backend-aligned/experiments/2026-10-14_E24v2_Reliable_Forecasting/` |
| Seeds | LightGBM `random_state` 42, `deterministic=True`, `n_jobs=1`; permutation, sign-flip and bootstrap seed 20261013 (50,000 Monte Carlo assignments when there are more than 16 origins) |
| Frozen files | `FROZEN_EVALUATION_PROTOCOL.md` (`runner/PROTOCOL_SHA256.txt`, `c8bce7ce…`) and `PROTOCOL_AMENDMENTS.md` (`runner/AMENDMENTS_SHA256.txt`, `dd8a2208…`). The runners refuse to start if either changed. |

## Commands, in order

| Step | Command | Output |
|---|---|---|
| 1 | `python -I acquisition/fetch_openstat.py` (network; PSA OpenSTAT) | `acquisition/*.csv`, `acquisition/raw/*` (byte-exact responses and queries), `ACQUISITION_MANIFEST.json`. Refuses any year ≥ 2026. **PSA may update the tables. Compare the manifest hashes; if they differ, the comparability gate re-tests the new vintage.** |
| 2 | `python -B runner/bx_data.py` | `data/monthly_yoy_1995_2025.csv`, `data/quarterly_D_1995_2025.csv`, `data/dnow_1995_2025.csv`, `data/comparability_gate.json` |
| 3 | `python -B runner/run_bx.py` (about 30 min; refuses unless the gate passed and the protocol is unchanged) | `runs/BX_<id>/`: predictions + SEAL, `results_BX.json` (confirmatory HB1–HB4, lead time), metrics, manifest |
| 4 | `python -B runner/run_dev_v2.py` (about 2 min) | `runs/DEV_<id>/`: development predictions (E24 rows + new arms), 2026-Q1/Q2 check, noise ceiling, C1–C9 |
| 5 | `python -B runner/seal_v2.py --verify runs/SEAL_20261013T164218Z` and `python -B runner/seal_v2_a3.py --verify runs/SEAL_20261013T222814Z` | Recomputes the sealed forecasts and compares their hash with the seal (`ac8babbc…`, `356cc22f…`). **Writes nothing.** Running them without `--verify` would create an extra seal, which the scorer would pool, so do not. |
| 6 | `python -B runner/lgu_rankings_v2.py [--sae <PSA workbook> --sae-year 2021]` | `data_v2/lgu_vulnerability_table.csv`, `runs/lgu_validation.json` |
| 7 | `python -B runner/export_pipeline_inputs.py` | `backend_dev/data/inputs/*` + registry `backend_dev/config/quarterly_sources.json` |
| 8 | `python -B runner/build_outputs_v2.py BX_20261013T163710Z DEV_20261013T222827Z` | Evidence status → pipeline cycles (live 2027-Q1, replay 2026-Q3) → `BASELINE_COMPARISON.csv`, `PREDICTIONS_BY_QUARTER.csv`, `FEATURE_ABLATION_RESULTS.csv` → `dashboard_dev/public/e24v2_dashboard.json` + 2 PDFs |
| 9 | `python -B runner/lgu_analysis.py` | `LGU_RANKING_VALIDATION.csv`, `runs/lgu_analysis.json` |
| 10 | Pipeline only, from `backend_dev/`: `python -B -m scripts.quarterly_update run` and `python -B -m scripts.quarterly_update replay --config config/replay_2026Q3.json` | The same records step 8 writes |
| 11 | `python -B -m pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/` | 68 Python tests |
| 12 | In `dashboard_dev/`: `npx vitest run`; `npx vite build --outDir dist-e24v2` | 21 frontend tests; build |

## Steps that need your input

| Step | Command | Refuses unless |
|---|---|---|
| T1 back-cast (amendment A2) | `python -B runner/run_bx_t1.py --sws <SWS 1998–2020 CSV> --authorization <json>` | The CSV is named, with its SHA-256, in your authorization JSON; it contains no row after 2020-Q4; the protocol and amendments are unchanged |
| Score the prospective seals | `python -B runner/score_prospective.py --outcomes <csv> --authorization <json>` | Every seal still matches its hash; the outcome file is authorized by hash |

## Recorded runs

| Run | Purpose |
|---|---|
| `runs/BX_20261013T163710Z` | Confirmatory back-cast (primary) |
| `runs/BX_20261013T223930Z` | Reproducibility re-run (seal compared in `TEST_RESULTS.md`) |
| `runs/DEV_20261013T222827Z` | Development (primary); `DEV_20261013T164041Z` is an earlier complete run, identical on all common arms (max diff 0.0) |
| `runs/SEAL_20261013T164218Z`, `runs/SEAL_20261013T222814Z` | Blind prospective seals |

**Folder file hashes:** `E24V2_FILES_SHA256.txt`.

## Data access

Every runner imports `runner/guard.py` (E24's guard plus read access to E24's own outputs):

- allowlisted files are re-hashed before every read;
- files inside this folder (the acquired public data and derived files) are readable;
- protected data, databases, models, `~/.claude`, `subprocess` and `sqlite3` are blocked.

The acquisition script and the PDF/dashboard builder do not read any project data outside this folder.
