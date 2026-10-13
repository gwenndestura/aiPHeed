# E8 v3: Scheduled-Task Review

**Status: review only, 2026-10-12. Neither task was changed, paused, run or stopped.**

**Sources (metadata only):**

- `list_scheduled_tasks` and `list_task_runs`;
- `get_session` on the two running sessions;
- the two `SKILL.md` prompt files;
- `C:\Users\admin\aipheed\.claude\settings.local.json` and `C:\Users\admin\.claude\settings.json`.

**The scheduled sessions' transcripts were not opened.** If a session read protected data, its transcript would contain it.

## 1. What each task runs

| Item | `aipheed` | `aipheed-auditing` |
|---|---|---|
| Prompt (`SKILL.md`, unchanged since May 2026) | "review deeply and thoroughly. audit. check deeply if it is working correctly, effectively, efficiently and the best of best. NO ISSUES!" | "check deeply if this methodology and data used in the system is correct, credible, legit, have credible sources. it is right and not just assumptions" |
| Schedule | Daily 09:00 local (`0 9 * * *`, jitter 161 s) | Daily 15:00 local (`0 15 * * *`, jitter 165 s) |
| Enabled | **Yes** | **Yes** |
| Next run | **2026-10-13 09:02:41 local** (01:02:41Z) | **2026-10-13 15:02:45 local** (07:02:45Z) |
| Total runs | 74 | 81 |
| Current run | Session `local_f3c4b65e…`: started 2026-10-12 08:10:12Z (16:10 local), **still marked running**, last activity 08:10:24Z | Session `local_918f3167…`: started 08:10:12Z, **still marked running**, last activity 08:10:41Z |
| Session settings | Model claude-opus-5-5, effort medium, local, cwd `C:\Users\admin\aipheed` (the repository root) | Same |
| Permission mode | **Not reported** (shown only for sessions this session started) | Not reported |
| Recent completed runs (5 each) | Status "succeeded", 0–8 s of recorded activity each | Same |

Both current sessions have shown no activity for several hours while marked running. They may be waiting at a permission prompt or may have ended without updating their status. **Which of these is true cannot be determined without reading the transcripts.**

## 2. Data sources and permissions available to them

The prompts name no data source. The tasks start in the repository root, so they can reach `backend/`, `aipheed-backend-aligned/`, `frontend/`, `Claude outputs/`, `aipheed-lean/` and `aiPHeed_Simplified_Methodology/`.

**Project permission rules allowed without prompting** (`.claude/settings.local.json`, relevant entries only):

| Rule | Effect for protected data |
|---|---|
| `Read(//c/Users/admin/**)` | Can read **every P3 file and potential carrier** (checklist 3), the session transcripts and the memory files |
| `WebSearch` | Can search for, and see snippets of, **September 2026 SWS results or July–September 2026 PSA inflation** (P1/P2 at source) |
| `Bash(python -c ' *)`, `Bash(./venv/Scripts/python.exe -c ' *)` | Can parse and print parquet files |
| `Bash(git add *)`, `Bash(git push *)`, and several `git commit -m '…'` patterns | Can stage and push changes |
| `Bash(pip install *)`, `Bash(winget install *)` | Can change the environment |

- No `deny` rules exist in either settings file.
- User-level `settings.json` holds only a plugin flag and a theme.

**Outputs.** Session transcripts go to `~/.claude/projects/C--Users-admin-aipheed/<session>.jsonl`. Files are written wherever the session chooses, subject to its unknown permission mode.

**Observed writes.** A metadata scan (mtime after 2026-10-12 16:10 local, when both sessions started) of the six project trees found 41 changed files. All are this session's own E6, E7 and E8 work in `aipheed-backend-aligned/`. **Nothing changed in `backend/`, `frontend/`, `Claude outputs/`, `aipheed-lean/` or `aiPHeed_Simplified_Methodology/`.**

This shows no file changes in those trees. It cannot show whether anything was **read** or **searched**.

## 3. Can they access protected 2026 outcomes?

**Yes.** Both tasks can do all of the following without a permission prompt:

- read the production P3 files;
- search the web for P1/P2 figures;
- print the results into their transcripts.

Whether any run has done so is **unknown**. The transcripts of all 155 runs (153 completed, 2 running) are potential carriers and must not be read.

**Second scheduled mechanism.** The production **APScheduler quarterly pipeline** (`backend/app/tasks/scheduler.py`; cron `0 2 15 1,4,7,10 *`, Asia/Manila):

- **would fetch OpenStat CPI through the run date on 2026-10-15**, adding July–September 2026 CPI to `psa_indicators.parquet`, then retrain the model and possibly promote it;
- it is **currently blocked**: `SCHEDULER_ENABLED=false` is present in `backend/.env` (checked 2026-10-12), and the scheduler runs only inside a started backend process. No `data/pipeline_runs/` or `models/candidates/` folder exists, so no run has happened.

## 4. Risk statement (defined, not accepted)

| Risk | Likelihood | Consequence |
|---|---|---|
| R1. A daily task reads a P3 file or a carrier while "auditing" the system | Plausible: the prompts ask for deep checks of data and methodology | The protected outcome appears in a transcript. If you or a later session read that transcript, the blind quarters are exposed. |
| R2. A daily task web-searches SWS or PSA figures to check that the data is "credible" | Plausible: `aipheed-auditing` asks for credible sources | September 2026 SWS or July–September 2026 CPI is seen |
| R3. A daily task edits or regenerates files (data, models, docs) | Unknown (permission mode unknown) | Breaks the hash baseline. Detected by X4, not prevented. |
| R4. A daily task commits or pushes | Possible: the git rules are allowlisted | P3 files or edits are published. The files are already tracked in git. |
| R5. A pending permission prompt in a running session is approved by mistake | Possible: both sessions are stalled while "running" | Any of R1–R4 |
| R6. The production pipeline runs on 2026-10-15 | Low while `.env` and the stopped backend hold | Automatic acquisition of P2 into production and retraining |

**This review does not accept any of these risks on your behalf.**

## 5. Recommended safe action (needs your approval: A7)

| Option | Exact action | Data touched | Reversible | Residual risk |
|---|---|---|---|---|
| **7a (recommended)** | 1. `update_scheduled_task(taskId="aipheed", enabled=false)`. 2. `update_scheduled_task(taskId="aipheed-auditing", enabled=false)`. 3. `stop_session` on `local_f3c4b65e…` and `local_918f3167…`, **without reading their transcripts**. Keep disabled until the 2026-Q4 evaluation is reported. | Task configuration only. No data files. | Yes (re-enable) | R1–R5 remove the daily trigger. Earlier transcripts remain carriers and stay unread. |
| 7b | Keep the tasks, but (i) add a protected-data rule to both prompts and (ii) add the project deny rules X6 (checklist 3) for protected paths, `WebSearch` and `WebFetch` | Task prompts and the project settings file (persistent configuration) | Yes | Prompt compliance is not guaranteed, and `Bash` / `python -c` can bypass `Read` deny rules. **R1–R4 are reduced, not removed.** |
| 7c | Keep `SCHEDULER_ENABLED=false`; do not start the production backend or run `quarterly_pipeline` manually until after E8 | None (already in place) | — | Covers R6 only |

**Recommendation: 7a + 7c.** Option 7b is weaker and changes persistent configuration.

**Timing.** If no decision is made, the next runs start **2026-10-13 at 09:02 and 15:02 local**.

**Until you decide:** if either running session shows a permission prompt, decline any request that would:

- read `backend/data/**`, `*.db` or `models/**`;
- search the web for SWS or PSA 2026 figures;
- commit or push.
