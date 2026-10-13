# Reproducing E23

**Interpreter:** `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe` (LightGBM 4.6.0, scikit-learn 1.8.0, SHAP 0.51.0, SciPy 1.17.1, reportlab 5.0.1). Node 24.17.

**Working directory:** this folder.

| Step | Command |
|---|---|
| 1. Frozen experiment (≈ 4 min) | `python -B runner/run_e23.py`. Refuses to run if `E23_PROTOCOL.md`, `e23_lib.py`, `run_e23.py` or `guard.py` differ from `runner/PROTOCOL_SHA256.txt`. |
| 2. Improvement experiment | `python -B runner/run_e23b.py <E23 run id>` (checks `runner/PROTOCOL_E23B_SHA256.txt` and the E23 seals) |
| 3. Rankings | `python -B runner/build_rankings.py <E23 run id>` |
| 4. Data inventory | `python -B runner/data_inventory.py` |
| 5. Quarterly cycle | From `aipheed-backend-aligned/`: `python -m scripts.quarterly_update run` |
| 6. Dashboard JSON + PDF | `python -B runner/build_outputs.py <E23 run> <E23B run>` |
| 7. Results tables | `python -B runner/build_results_md.py <E23 run> <E23B run>` |
| 8. Tests | `python -B -m pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/`, and in `dashboard_dev/`: `npx vitest run` |

**Recorded runs:**

| Run | What it is |
|---|---|
| `runs/20261013T152113Z` | Primary |
| `runs/20261013T152524Z` | Identical repeat |
| `runs/20261013T152838Z_E23B` | Improvement |

Each run folder has `manifest.json`, which records:

- the allowlist hash verification;
- the integrity assertions;
- the access log of every data read;
- the output hashes.

**Guard.** Every data read goes through `runner/guard.py`. A read of any non-allowlisted project data file, a database, a model, `~/.claude`, `subprocess` or `sqlite3` raises an error.

**File hashes** for this folder: `E23_FILES_SHA256.txt`.
