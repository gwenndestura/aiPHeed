# Scheduled-Task Safety Decision Brief

**Status: for your decision, 2026-10-12. No task was changed, paused, run or stopped. No session was stopped. No transcript was read.**

**Sources (configuration metadata and task definitions only):**

| Source | When | What |
|---|---|---|
| `list_scheduled_tasks` | 2026-10-12, about 18:28 local | Schedule, enabled state, next and last run |
| `get_session` | Same time | Metadata of the two running sessions; no conversation content |
| The two `SKILL.md` files and `.claude/settings.local.json` | Read 2026-10-12 about 17:55; unchanged since (mtime and size re-checked) | Task prompts and permission rules |
| Process list | 18:26 local | No `python`, `uvicorn` or pipeline process running |
| Run history | Seen once at about 17:55 | **Not re-queried**, because `list_task_runs` can return run summaries written inside the runs |

**Labels:**

- **Confirmed:** read directly from configuration or metadata.
- **Expected:** standard product behaviour, not observed for these sessions.
- **Not observed:** possible, with no evidence either way.

## 1. What each task is scheduled to do

| | `aipheed` | `aipheed-auditing` |
|---|---|---|
| Prompt (**confirmed**) | "review deeply and thoroughly. audit. check deeply if it is working correctly, effectively, efficiently and the best of best. NO ISSUES!" | "check deeply if this methodology and data used in the system is correct, credible, legit, have credible sources. it is right and not just assumptions" |
| Prompt file (**confirmed**) | `~/.claude/scheduled-tasks/aipheed/SKILL.md`, 199 bytes, mtime 2026-05-02, sha256 `50668f44…` | `~/.claude/scheduled-tasks/aipheed-auditing/SKILL.md`, 201 bytes, mtime 2026-05-03, sha256 `ed54fae9…` |
| Schedule (**confirmed**) | Daily `0 9 * * *` (09:00 local), jitter 161 s | Daily `0 15 * * *` (15:00 local), jitter 165 s |
| Enabled (**confirmed**) | Yes | Yes |
| Next run (**confirmed**) | 2026-10-13 09:02:41 local | 2026-10-13 15:02:45 local |
| Start time in practice (**inference**) | Recent runs started at app-open times (12:44, 16:10, 16:41, 18:16, 20:44), not at 09:00 | One run on schedule (10-09, 15:02); the others started together with `aipheed` |
| Working folder and model (**confirmed**) | `C:\Users\admin\aipheed` (repository root); claude-opus-5-5; effort medium; local | Same |
| Current session (**confirmed**) | `local_f3c4b65e…`: running since 08:10:12Z; **last activity 08:10:24Z** (unchanged at 18:28 local) | `local_918f3167…`: running since 08:10:12Z; **last activity 08:10:41Z** (unchanged) |
| Permission mode | **Unknown**: reported only for sessions this session started | Unknown |

**Practical effect.** Both prompts ask for open-ended "deep" audits of the system's data and methodology. Neither names protected data, but neither excludes it.

## 2. Files and data sources it can access

| Capability | Status | Basis |
|---|---|---|
| Read any file under `C:\Users\admin\` without a prompt: production P3 files, potential carriers, other sessions' transcripts, memory files | **Confirmed rule** | `settings.local.json` allows `Read(//c/Users/admin/**)`. It applies to these sessions as **expected** behaviour for their working folder (not observed). |
| Parse and print parquet or CSV via `python -c '…'` or `./venv/Scripts/python.exe -c '…'` without a prompt | **Confirmed rule** | Allow entries `Bash(python -c ' *)` and `Bash(./venv/Scripts/python.exe -c ' *)` |
| Web search without a prompt | **Confirmed rule** | Allow entry `WebSearch` |
| Fetch a web page without a prompt | **Not allowlisted** (no `WebFetch` entry), so it would prompt unless the permission mode skips prompts | Settings file; mode unknown |
| Edit or write files without a prompt | **Not allowlisted** (no `Edit`/`Write` entries), so it would prompt unless the mode skips prompts. Shell commands that write files are partly allowlisted (e.g. `cp`, `mkdir` patterns, `python -c`). | Settings file |
| Stage, commit and push | **Confirmed rules**: `git add *`, `git push *`, several `git commit -m '…'` patterns | Settings file |
| Install packages | **Confirmed rules**: `pip install *`, `winget install *` | Settings file |
| Deny rules | **None** in project or user settings | Settings files |

The **protected-row files are already on the remote** (`origin/backend+frontend` = eee269b, **confirmed** from git refs). So any session can also reach them through `git show origin/...`, and anyone with repository access can read them.

## 3. Can it search for or retrieve protected 2026 outcomes?

| Route | Capability | Observed? |
|---|---|---|
| Read production `psa_indicators.parquet` / `panel.parquet` (documented 2026-H2 rows) or carriers | **Yes** (confirmed rule) | **Not observed.** No evidence either way; reads leave no trace. |
| Web-search September 2026 SWS hunger or July–September 2026 PSA inflation | **Yes** (confirmed rule) | **Not observed** |
| Print such values into its transcript | Yes, as a consequence of either route | **Not observed.** Transcripts are not read. |
| Change files or commit and push | Possible: shell rules allowlisted; edits depend on the unknown mode | **No file changes observed** in the six project trees since 16:10 local (mtime scan). No commits since 2026-09-29. No push recorded in local refs since the 2026-10-06 fetch. |

## 4. Risks of leaving the tasks active

| Risk | Status | Consequence |
|---|---|---|
| R1. Reads a protected or carrier file during a "deep audit" | Capability **confirmed**; occurrence **not observed** | Blind outcome appears in a transcript. If you or any later session read it, E8's two blind quarters are compromised. |
| R2. Web-searches SWS or PSA 2026 figures to "check credible sources" (the `aipheed-auditing` wording invites this) | Capability **confirmed**; occurrence **not observed** | Same as R1, and the value may surface in a summary you read |
| R3. Edits or regenerates data, models or documents | Depends on the unknown mode; **not observed** | Hash baseline breaks. Detected afterwards (mtime and hash checks), not prevented. |
| R4. Commits or pushes | Rules allowlisted; **not observed** | Unreviewed changes published. The protected-row files are already on the remote. |
| R5. A pending permission prompt in a stalled session is approved by mistake | Both sessions have been "running" with no activity since 08:10Z; **whether a prompt is pending is unknown** | Any of R1–R4 |
| R6. Production quarterly pipeline (2026-10-15 02:00) | Separate mechanism. **Blocked:** `SCHEDULER_ENABLED=false` present, and no backend process running at 18:26 | Would add July–September 2026 CPI to production and retrain. Only possible if someone starts the backend after re-enabling it, or runs the pipeline by hand. |

**Value of the tasks today (inference from metadata).** The four most recent completed runs of each task recorded 0–8 seconds between start and last activity. This suggests the daily audits currently do little, but it is **not** evidence of what they did.

## 5. Consequences of disabling the tasks and stopping their sessions

| Action | Consequences | Reversible? |
|---|---|---|
| Disable `aipheed` and `aipheed-auditing` (`enabled=false`) | No new daily runs, and no catch-up runs when the app opens. You lose the automated daily review until re-enabled. Task definitions and earlier transcripts are kept. | **Yes**: re-enable at any time, with no data change |
| Stop session `local_f3c4b65e…` | Its in-progress run ends; any pending permission prompt or unfinished work is discarded. The transcript remains on disk, as a carrier, unread. | **Partly**: the run cannot be continued as it was; whether the session can be resumed was not verified |
| Stop session `local_918f3167…` | Same | Partly |
| Do neither | Next runs start 2026-10-13 (09:02 / 15:02, or when the app next opens) | — |

**Disabling without stopping** leaves the two stalled sessions open. Risk R5 stays until they are stopped, or until you check and decline any prompt yourself.

## 6. Recommended action (needs your explicit approval; not done)

**Recommended (7a + 7c):**

1. Disable both tasks.
2. Stop both running sessions without opening their transcripts.
3. Leave `SCHEDULER_ENABLED=false` and the production backend stopped.

Keep this until E8's outcome collection and evaluation are finished, or until you decide otherwise.

**Lesser alternatives, with residual risk:**

| Option | Residual risk |
|---|---|
| Disable both tasks only, without stopping sessions | R5 stays open for the two stalled sessions |
| Keep the tasks, but add a protected-data rule to their prompts and project deny rules for protected paths, `WebSearch` and `WebFetch` | Prompt compliance is not guaranteed; `Bash` and `python -c` can bypass `Read` deny rules. Persistent configuration changes. R1–R4 are reduced, not removed. |
| Leave everything as is | R1–R5 remain. This is **your** decision to accept; this brief does not accept it. |

**If you decide later:** before opening the app tomorrow, be ready to decline any prompt from either task that reads `backend/data/**`, `*.db` or `models/**`, searches the web for SWS or PSA 2026 figures, or commits or pushes.
