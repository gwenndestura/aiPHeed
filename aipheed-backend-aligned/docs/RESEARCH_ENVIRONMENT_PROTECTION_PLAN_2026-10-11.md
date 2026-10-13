# Research Environment Protection Plan (2026-10-11)

**Scope:** inspection and planning only.

**Not changed:** no configuration, code, scheduled task, model, data, forecast, thesis or pre-registration file. Neither scheduled task was paused, edited, deleted or triggered.

**Not run:** no backend, no tests, no admin endpoint, no pipeline. No model was trained or scored.

**Not accessed:** no SWS value or 2026 CPI value.

**Earlier reports:** preserved.

---

## 1. Daily Claude scheduled tasks

### 1.1 Current state (read via the scheduled-tasks tools)

| | `aipheed` | `aipheed-auditing` |
|---|---|---|
| Prompt file | `C:\Users\admin\.claude\scheduled-tasks\aipheed\SKILL.md` | `C:\Users\admin\.claude\scheduled-tasks\aipheed-auditing\SKILL.md` |
| Prompt (summary) | Review, audit and check deeply that everything works "correctly, effectively, efficiently"; "NO ISSUES!" | Check deeply that the methodology and data are correct, credible and legitimately sourced |
| Schedule | `0 9 * * *`, 09:03 local, with up to ~3 min jitter | `0 15 * * *`, 15:03 local |
| Enabled | **Yes** | **Yes** |
| Next run | 2026-10-12 09:02 (01:02 UTC) | 2026-10-12 15:02 (07:02 UTC) |
| Run history | 73 runs | 80 runs |
| Latest run | `local_926e4240-…`, started 2026-10-11 10:16 UTC, status **"running"**, last activity 10:16:53 | `local_9d9d135f-…`, started 2026-10-11 10:16 UTC, status **"running"**, last activity 10:16:46 |

**Observations:**

- Recent start times (12:44 UTC on 10-10, 10:16 UTC on 10-11) do not match the cron times. Missed runs appear to fire when the app next opens.
- **Both of today's runs are still open sessions.**

### 1.2 Why pause them

**The prompts are open-ended, unattended and have no restrictions.**

- They invite actions that "fix" issues, which risks changes to code, `.env`, models or data.
- The auditing prompt explicitly asks for source checks. That invites browsing SWS and PSA pages, which could show September or December 2026 SWS results or July–December 2026 provincial CPI. Both are components of the protected 2026-Q3/Q4 outcomes.
- **An exposure like that cannot be undone.** It would void the protected evaluation (v3 §13.2: "outcomes seen before forecasts frozen").

**Recommendation:** pause both tasks until the protected 2026-Q3/Q4 forecasts are frozen, hashed and verified. Also stop the two open runs.

### 1.3 Exact steps (each needs your authorization)

**Step 1. Pause automatic runs.** Use either route.

- **Claude app:** open the scheduled-tasks panel and switch off `aipheed` and `aipheed-auditing`.
- **Tool calls I can make once you authorize them:**
  - `update_scheduled_task(taskId="aipheed", enabled=false)`
  - `update_scheduled_task(taskId="aipheed-auditing", enabled=false)`

**Verify:** `list_scheduled_tasks` shows `"enabled": false` for both.

**What pausing does and does not do:**

- It does not delete the prompts or the run history.
- It does **not** block a manual "Run now".
- To resume later, set `enabled=true`.

**Step 2. Stop the two open runs.** Pausing does not stop sessions already running. Use either route.

- **Claude app:** stop or archive the sessions "Aipheed" and "Aipheed auditing" started at 10:16 UTC today.
- **Tool calls on authorization:** stop sessions `local_926e4240-cc63-4dbe-85ff-2ad952fa0bf0` and `local_9d9d135f-56ad-46ad-b258-4fb1b9ea9407`.

**Step 3 (optional, later).** Before re-enabling, replace the prompts with restricted versions that forbid:

- starting servers;
- running the pipeline, training or scoring;
- downloads;
- browsing SWS or PSA for 2026 results;
- editing `.env`, code, models, data or pre-registration files.

The original prompts would be preserved.

**Rejected alternative:** deleting the tasks. Pausing is reversible and enough.

## 2. Scheduler configuration: the working-directory gap

### 2.1 How settings are loaded

- `backend/app/config.py` uses pydantic-settings with `env_file=".env"`, resolved from the process's working directory.
- Priority order: **environment variable > `.env` > code default (`True`)**.
- Today, `backend/.env` contains `SCHEDULER_ENABLED=false`, so:
  - from `backend/`, the setting reads `False`;
  - from the repo root, it reads `True`.

### 2.2 The two options

| | Option 1: user-level environment variable | Option 2: anchor the `.env` path in code |
|---|---|---|
| Change | `[Environment]::SetEnvironmentVariable('SCHEDULER_ENABLED','false','User')` | `config.py`: `env_file = str(Path(__file__).resolve().parents[1] / ".env")`, plus `from pathlib import Path` |
| Production code touched | No | **Yes** |
| Independent of the working directory | Yes, highest-priority source | Yes, for every `.env` key |
| Takes effect | New processes only. Terminals, IDE and the Claude app need restarting. Existing processes keep their old environment. | The next process start |
| Reversible | One command: set it back to `$null` | A code revert |
| Side effects | Every program run by this Windows user sees `SCHEDULER_ENABLED=false`. No other project here uses that name: the aligned backend uses `AIPHEED_ENABLE_SCHEDULER`. Scheduler unit tests monkeypatch the value, so they are unaffected. | Changes how **all** settings load. Needs the `backend/` test suite, and those tests run application startup (`TestClient` lifespan), which you excluded for now. |
| Visible in the repo | No: machine-local, like `.env` | Yes: appears in the diff, and the thesis documents `backend/` |
| Fixes root startup in general | No | **No.** `DATABASE_URL` in `.env` is `sqlite+aiosqlite:///./…`, a path relative to the working directory. A root start would still open a different database. |

### 2.3 Recommendation

**Choose Option 1:** the user-level environment variable.

- It is the smallest change, needs no production code and no test run that starts the app, and can be reversed with one command.
- It closes the scheduler gap from any directory.

**Keep the operating rule anyway:** start `backend/` only from `backend/`. A root start is wrong for other reasons, such as the relative database path.

**Option 2** can be considered later as a general robustness fix, together with the database path.

**Verification after Option 1** (once authorized; no server, no pipeline):

1. In a **new** shell, from the repo root:

   ```bash
   PYTHONPATH=backend backend/venv/Scripts/python.exe -c "from app.config import settings; print(settings.SCHEDULER_ENABLED)"
   ```

   It must print `False`.
2. The same check from `backend/` must also print `False`.
3. `[Environment]::GetEnvironmentVariable('SCHEDULER_ENABLED','User')` returns `false`.

**What neither option does:** neither blocks `POST /api/v1/admin/pipeline/run` or `python -m app.tasks.quarterly_pipeline`. Those stay governed by the operating rule in §3.

## 3. Restrictions in force until the protected forecasts are frozen and verified

| # | Restriction | Covers |
|---|---|---|
| R1 | **No pipeline runs**: scheduled, manual admin endpoint (`POST /api/v1/admin/pipeline/run`), or CLI (`python -m app.tasks.quarterly_pipeline`), for either backend | `backend/`, aligned |
| R2 | **No model retraining or promotion.** The served `backend/models/thesis_food_insecurity_model.joblib` (SHA-256 `cbab63f8…`) and the aligned `models/lgbm_best.pkl` stay as they are. | Served models |
| R3 | **No changes** to frozen forecasts, `data/processed/*`, `data/thesis/panel.parquet`, label files, `data/supplementary/*` collections or evidence folders | Evaluation data |
| R4 | **No retrieval or inspection of September or December 2026 SWS results**, including SWS home and listing pages, search results and news. Any authorized SWS verification uses only the four direct 2025 release URLs. | Protected outcomes |
| R5 | **No access to July–December 2026 provincial or regional CPI** (OpenStat, PSA, RSSO, news) before the forecast freeze, except through a separately authorized freeze-then-collect procedure. The `backend/` government stage would fetch it, so this is also why R1 applies. | Protected outcomes |
| R6 | **No changes** to the thesis, `PREREGISTRATION_DRAFT*.md`, or earlier reports. New versions are new files. | Documentation |
| R7 | **No unattended agent sessions** on this project while R4/R5 apply (§1) | Process |
| R8 | **Start `backend/` only from `backend/`** (§2) | Configuration |

## 4. Remaining risks and consequences

| Risk | Consequence if it happens | Fix | Needs your authorization |
|---|---|---|---|
| A daily agent session browses SWS or PSA 2026 pages | Protected outcome exposed; the 2026-Q3/Q4 evaluation can no longer be a valid unseen test (irreversible) | Pause the tasks and stop the open runs (§1.3) | **Yes** |
| A daily agent session edits code, `.env`, models or data | Served model or evaluation data altered; provenance broken | Same | **Yes** |
| `backend/` started from the repo root | Scheduler on; a run at 02:00 on the 15th could retrain, promote, and fetch 2026-Q3 CPI | Option 1 (§2.3), plus R8 | **Yes** |
| Manual pipeline triggered (admin endpoint or CLI) | Same as above, at any time | R1. Optional code guard later. | Code guard: yes |
| An existing session keeps the old environment after Option 1 | The gap persists in that process | Restart terminals, IDE and the app after Option 1 | — |
| Hashes not re-checked | A silent change goes unnoticed | Checklist below | — |

## 5. Protection checklist

**Actions needing your authorization:**

- [ ] 1. Pause `aipheed` and `aipheed-auditing` (§1.3 step 1), then verify `enabled: false`.
- [ ] 2. Stop the two open runs (§1.3 step 2).
- [ ] 3. Set the user-level `SCHEDULER_ENABLED=false` (§2.3) and restart terminals, IDE and the app. Verify that it prints `False` from the repo root and from `backend/`.

**Already in place (verified earlier today):**

- [x] 4. `backend/.env` contains `SCHEDULER_ENABLED=false`, and the original 13 lines are unchanged.
- [x] 5. The aligned scheduler is off: `AIPHEED_ENABLE_SCHEDULER` is unset.
- [x] 6. No Windows task, startup item or session cron launches either backend, and nothing is listening on port 8000.

**Ongoing:**

- [ ] 7. No pipeline run of any kind (R1), and no use of the admin pipeline endpoint.
- [ ] 8. **On or after 2026-10-15**, re-check, read-only:
   - the served model SHA-256 is `cbab63f867e8f51fe0b93c99d8bdba3ace52a83d69dd77884763a69b9bc79dda`;
   - `panel.parquet` is `49af3ee1…`;
   - `psa_indicators.parquet` is `305ac1b3…`;
   - `models/archive/`, `models/candidates/` and `data/pipeline_runs/` still do not exist.
- [ ] 9. R4/R5 observed by every human and agent session. Any authorized SWS verification uses only the four direct 2025 URLs.
- [ ] 10. Before the protected freeze, record the hashes of the aligned `data/processed/*`, `models/*` and `sws_hunger_fetcher.py`.
- [ ] 11. Resume the scheduled tasks only after the protected forecasts are frozen, hashed and verified, preferably with restricted prompts (§1.3 step 3).

**Stopping here.**
