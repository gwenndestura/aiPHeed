# E9: Environment, Provenance and Containment Record

**Experiment:** E9, "S1 targets, guarded allowlist-only inputs, walk-forward comparison".

| Item | Value |
|---|---|
| Folder | `aipheed-backend-aligned/experiments/2026-10-12_E9_S1_safe_training/` (new; nothing earlier overwritten) |
| Primary run | `runs/20261012T140816Z` |
| Deviation run (identical outputs) | `runs/20261012T140723Z` |

## 1. Scheduled-task containment (authorized 2026-10-12)

**Identities were verified before acting:**

- task `aipheed` ↔ session `local_f3c4b65e-be65-409f-a1c9-1e29c11d1321`;
- task `aipheed-auditing` ↔ session `local_918f3167-4ff0-47f4-bc3b-115ea28d8055`;
- both `scheduledTaskId` values matched.

| Item | Before (21:53 local) | Action | After |
|---|---|---|---|
| Task `aipheed` | enabled; next 2026-10-13 09:02:41 | `update_scheduled_task(enabled=false)` | **disabled**, no next run |
| Task `aipheed-auditing` | enabled; next 2026-10-13 15:02:45 | Same | **disabled**, no next run |
| Session `local_f3c4b65e…` | running; last activity 08:10:24Z | `stop_session` (interrupts the current turn only) | not running; last activity 13:53:18Z |
| Session `local_918f3167…` | running; last activity 08:10:41Z | Same | not running; last activity 13:53:21Z |

**What was not done:**

- No session was archived or deleted. Both stay open and idle; a message already queued in them would run next.
- No transcript was opened.
- No other task or setting was changed.

**Known and unknown about earlier access:**

- **Known:** the two sessions recorded no activity between 08:10Z and the interruption.
- **Unknown:** what they, or any earlier run, read or searched. This is not checkable without opening transcripts, which was not done.

## 2. Which system is deployed (identified, not assumed)

| Component | What serves it | Status 2026-10-12 |
|---|---|---|
| **Production `backend/`** | Model `models/thesis_food_insecurity_model.joblib` (blend), production label `label_cpi`, cutoff 0.712 (`REVISED_SCORING_REPORT.md` §G) | **Not running** (no python/uvicorn process at 18:26 or 22:10). Scheduler blocked (`SCHEDULER_ENABLED=false`). |
| Frontend | Calls `VITE_API_BASE_URL` (default `http://localhost:8000`) | No live API to call |
| Isolated backend | Served M6 artifact (τ0 = 10.843) via `/api/v1/assessments` | Not consumed by any UI (`REVISED_SCORING_REPORT.md` §G); not running |
| Public deployment | The memory index records Vercel as an old frontend prototype | **Not verified** |

The memory index records that the thesis documents **production `backend/`** (your choice, 2026-10-09). **E9 is a research experiment in the isolated backend.** It does not change any served model, threshold or dashboard.

## 3. Starting state

| Item | Value |
|---|---|
| Git HEAD | `eee269b92b47482d07aac769c54dd1d6c558c5ce` (branch `backend+frontend`); 23 status entries; no commit or push by E9 |
| Interpreter | `backend/venv` Python 3.13.2 (read-only use, run with `-B`), Windows 11 |
| Packages | pandas 2.3.3, numpy 2.4.4, scikit-learn 1.8.0, lightgbm 4.6.0, pyarrow 23.0.1 |
| Seed | LightGBM `random_state=42`; bootstrap seed 42 |
| Pre-run integrity (22:07) | All existing hash records matched: 55 protected/carrier files, E1–E7 inputs, outputs and protocols, served artifacts, 54 production files, E8 v1/v2 |

**Input data versions (SHA-256; each matched the hash recorded when E1–E7 used it):**

| File | SHA-256 | Use |
|---|---|---|
| `data/processed/psa_indicators.parquet` | `947be05f…a9ff4c` | Provincial food CPI YoY (targets and inputs) |
| `data/processed/features_fused.parquet` | `0080dd5c…da1292` | Unemployment, poverty, headline CPI, food-minus-headline (projected columns only) |
| `data/processed/labels.parquet` | `eeb55983…ae32d1e` | Cross-check of S1 stress only |
| `data/supplementary/collection_2026-10-09/sws_balance_luzon_2025_raw.csv` | `1d7bd40a…789580` | 2025 SWS rounds (inputs) |
| `evidence/2026-10-09_readiness/cpi_final_month_release_dates.csv` | `38ea7310…3de6` | CPI release dates |
| `config/governing_model.json` | `c9697b6b…dcc1` | Read at module import (configuration) |

**Code reused unchanged:**

- `app/ml/features/risk_score_v2.py` (S1);
- `scripts/supplementary/devprotocol_rule_l.py`: `sws_rounds`, `sws_known`, `cpi_published`, `label_published`;
- `app/ml/corpus/sws_hunger_fetcher.py`: the registry constant, imported only.

The full hashes are in each run's `manifest.json`.

## 4. Guard evidence (from the run's `manifest.json` access log)

**Parquet reads (3), each hash-verified, column-projected and filtered to `quarter <= 2025-Q4` during the scan:**

| File | Rows returned |
|---|---|
| `psa_indicators` | 120 |
| `features_fused` | 120 |
| `labels` | 95 |

**Other files opened:** only the SWS 2025 CSV, the CPI release-date CSV and `config/governing_model.json`.

**Not opened:** no protected or carrier file, no production file, no database, no model file and no transcript.

**Allowlist hashes:** identical at the start and end of the run.

**One guard denial (deviation run only):**

- joblib/loky tried to start `wmic` to count CPU cores; the guard blocked the subprocess, and loky fell back to the logical core count.
- The primary run set `LOKY_MAX_CPU_COUNT=21`, which skips that call. It had **no denial**, and **all eight output files are byte-identical** to the deviation run.
