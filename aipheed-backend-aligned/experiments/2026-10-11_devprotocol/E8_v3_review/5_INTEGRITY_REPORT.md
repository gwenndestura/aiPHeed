# Integrity Report: E8 v3 Review Task

**Performed 2026-10-12, 18:23–18:35 local (Asia/Manila).** A final scan at 18:35 confirmed that the only changed files are the five review documents.

**Methods used:**

- file metadata (size, mtime);
- SHA-256 of raw bytes, read in binary chunks and never decoded;
- git object and ref metadata;
- configuration metadata (`list_scheduled_tasks`, `get_session`);
- a process list;
- reading this project's own records, code, and the column headers and sample-size fields of exposed (not protected) collection files.

**Not done:**

- No protected or potential-carrier file was opened, parsed or loaded.
- No session transcript was read, and `list_task_runs` was not called.
- No evaluation, forecast, label, training or rescoring.
- No task, session, configuration, production, frontend or served-model change.
- No commit or push.

**Scripts and outputs:**

- Check script: the scratchpad's `e8v3_review_integrity.py`.
- Full result: the scratchpad's `e8v3_review_integrity_result.json`.

## 1. Checks performed (all against existing records)

| # | Check | Record compared against | Result |
|---|---|---|---|
| 1 | E8 v3 documents 1–5 and the hash baseline | SHA-256 listed in `E8_v3/6_INTEGRITY_VERIFICATION_REPORT.md` | **6/6 match** |
| 2 | `E8_v3/6_INTEGRITY_VERIFICATION_REPORT.md` | Hash taken at this task's start (18:23:08), since report 6 is not self-hashed | **Match**: `b2dc3574d25d4abb907f0d96a712f51cfea11dbd90f3a6474f053f8120047f2f` |
| 3 | 55 protected and carrier files | `E8_v3/protected_and_carrier_files_sha256_20261012.txt` | **55/55 hashes match. No size or mtime change.** |
| 4 | Inputs of E1–E5 | Each run's `config.json` (122, 100, 122, 122, 100 entries) | **All match**; none missing |
| 5 | Protocol files of E1–E5 | Each run's config | **5/5 match** |
| 6 | Outputs of E1–E7 | Each run's `manifest.json` / `manifest_posthoc.json` | **163/163 match** |
| 7 | E6 prediction artifacts | E6 manifest | **2/2 match** |
| 8 | Served artifacts and their inputs | `data/revised/*_meta.json` | **5/5 and 6/6 match** |
| 9 | Production `backend/` (54 files) | Scratchpad `backend_before.sha` (2026-10-11) | **54/54 match** |
| 10 | E8 v1 | Full hash `81e6e213…fb42` | **Match** |
| 11 | E8 v2 | Full hash `b328021a…ee26`, first recorded in report 6 | **Match.** This is the first hash comparison for v2. |
| 12 | `S1_FROZEN_REFERENCE_PROPOSAL.json` | Recorded prefix `dc77104476c28141` | **Match** |
| 13 | 2026-H1 supplementary collection (6 files) | Its own `COLLECTION_MANIFEST.json` | **6/6 match.** This closes a gap listed in report 6, §3. |
| 14 | Production JSON result files and `mlflow.db` | git index (`git ls-files -s` vs `git hash-object`) | Seven JSON files **tracked, working copy equals index**. `mlflow.db` **untracked, git-ignored**. Closes review P2. |
| 15 | Author vs committer date of protected-row files | `git log --format=%ad/%cd` | **Identical** for all checked files (review P6) |
| 16 | Commits, checkouts, pushes | `git log`, `git reflog` (HEAD, remote refs) | HEAD still eee269b (2026-09-29). Last HEAD movement: checkout 2026-10-06. No push recorded in local refs. `origin/backend+frontend` = eee269b (fetched 2026-10-06). |
| 17 | git working tree | `git status --porcelain` | **23 entries**, the same as at the start of this session. `.git/index` unchanged since 2026-10-10 21:24. |
| 18 | Scheduled tasks | `list_scheduled_tasks` | Both **enabled**, schedules and next runs unchanged (2026-10-13 09:02:41 and 15:02:45 local) |
| 19 | Running scheduled sessions | `get_session` | Both still marked running. Last activity **08:10:24Z and 08:10:41Z, unchanged.** |
| 20 | Task definitions and project settings | mtime, size, SHA-256 | `SKILL.md` files unchanged since May 2026 (hashes `50668f44…`, `ed54fae9…`). `settings.local.json` unchanged since 2026-08-28 (`01e6a4b0…`). |
| 21 | Production scheduler block | mtime of `backend/.env` (2026-10-11 18:59, the authorized edit); count-only `grep` carried over from the previous step | Not re-grepped in this task. The mtime has not changed since the edit. |
| 22 | Backend or pipeline processes | Windows process list (18:26 local) | **None running** (no `python`, `uvicorn` or pipeline process) |

## 2. Did any files change during this task?

| Scope | Method | Result |
|---|---|---|
| Six project trees (`aipheed-backend-aligned`, `backend`, `frontend`, `Claude outputs`, `aipheed-lean`, `aiPHeed_Simplified_Methodology`), excluding venv and node_modules | mtime scan since 18:23:00 local | **Only the new review documents** in `E8_v3_review/` (items 1–4 at scan time; this report written afterwards) |
| `backend/venv` | Separate mtime scan | **No change** |
| Scheduled-task definitions, memory folder | mtime scan | **No change** |
| `.git/index`, `.claude/settings.local.json` | mtime | **No change** |
| All files with earlier hash records | Checks 1–14 | **No change detected** |

**Files created by this task** (all new; nothing overwritten; SHA-256 at the final scan):

| File (`experiments/2026-10-11_devprotocol/E8_v3_review/`) | SHA-256 |
|---|---|
| `1_E8_V3_CONSISTENCY_REVIEW.md` | `6b193133bac372d0b7d5fbe2223e28ba081532a76212052234f649ed80d714ee` |
| `2_SCHEDULED_TASK_SAFETY_DECISION_BRIEF.md` | `c926ec1510274d462307c6133e4b2cf5efb093d1ae5fac42b1f0b392d82509ce` |
| `3_APPROVAL_CHECKLIST_REVIEW.md` | `0aa90b8978cbab58af16bcf63152e9442326a325764276d76c95d6cbf878126b` |
| `4_SAFE_COMPLETION_ROADMAP.md` | `f345aafde94198c960df73c73ae0d04f3349a3f542df0c2cc96fbb772d411394` |
| `5_INTEGRITY_REPORT.md` | (this file; not self-hashed) |

**Scratchpad (outside the project):** `e8v3_review_integrity.py`, `e8v3_review_integrity_result.json`.

## 3. What could not be checked, or was not checked

| Item | Reason | Status |
|---|---|---|
| Whether any protected or carrier file has been **read** by any session | Reads leave no trace on disk | **Not checkable.** In this task, no protected or carrier file was opened except to hash its bytes. |
| What the two scheduled sessions did, and whether a permission prompt is pending | Transcripts (and run summaries) are potential carriers | **Not checked** |
| Coverage of carrier files (quarters, columns) | Requires content access | Not checked; treated as protected |
| Whether the scheduled sessions apply the project permission rules, and their permission mode | Not exposed in metadata | Not checked (expected behaviour only) |
| Release dates of the September 2026 SWS round and September 2026 provincial CPI | Looking them up risks exposure | Not checked |
| Full data-access trace of the production test suite and of modules imported by `app.main` | Code tracing not completed in this task | Partly checked (grep); see approval review B2 |
| `Claude outputs/` files other than the hashed types, and `mlruns/` | Not in any hash record | Metadata only (count: 42 files in `Claude outputs/`) |
| `backend/.env` content beyond the one-line count done in the previous step | Contains settings, possibly secrets | Not re-read |
| Whether a stopped session can be resumed | Would require stopping one | Not checked |

## 4. Permitted reads of non-protected content (disclosed for completeness)

| What was read | Classification |
|---|---|
| Code in the isolated and production backends (models, frame lineage, tests, scheduler) | Not protected |
| This project's own run configs, manifests and served-artifact meta (JSON) | Not protected |
| Header line of `provincial_food_cpi_yoy_2026H1_raw.csv` | **Exposed** 2026-H1 file; column names only |
| `round_fieldwork`, `sample` and `sampling_error_balance_luzon` fields of `sws_balance_luzon_2025_raw.csv` | **Exposed** 2025 file; **no hunger values printed** |
| `COLLECTION_MANIFEST.json` key structure and file hashes | Own record |
