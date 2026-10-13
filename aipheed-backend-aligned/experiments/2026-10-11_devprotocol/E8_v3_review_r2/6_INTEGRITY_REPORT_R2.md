# Integrity Report, Revision r2

**Scope.** This report covers both sessions that produced `E8_v3_review_r2/`:

| Session | Started | Produced |
|---|---|---|
| Previous | 2026-10-12 18:40:32 local | Items 1–2 |
| This task | 21:07:41 local | Items 3–6 |

**Methods:** file metadata, SHA-256 of raw bytes (binary, never decoded), git ref and object metadata, scheduled-task and session metadata, code reading, and this project's own JSON records.

**Not done:**

- No protected or potential-carrier file was opened, parsed or loaded.
- No session transcript was opened, and `list_task_runs` was not called.
- No test, training, forecast, evaluation, scoring, pipeline or dashboard check was run.
- No task or session was changed.
- No fetch, pull, push, commit or delete.

**Hashes vs access.** Matching hashes show that a file's **contents are unchanged**. They **do not show that the file was never read.** Reading leaves no trace on disk. Every "unchanged" below is about contents only.

## 1. Checks performed

| # | Check | Record | Result |
|---|---|---|---|
| 1 | E8 v3 documents 1–5 and the baseline file | Hashes listed in `E8_v3/6_INTEGRITY_VERIFICATION_REPORT.md` | **6/6 match** |
| 2 | `E8_v3/6_INTEGRITY_VERIFICATION_REPORT.md` | Hash recorded 2026-10-12 18:23 | **Match** |
| 3 | 55 protected and carrier files | `E8_v3/protected_and_carrier_files_sha256_20261012.txt` | **55/55 hashes match; no size or mtime change** |
| 4 | E1–E5 inputs and protocol files | Run `config.json` records | **All match** (122/100/122/122/100; 5/5 protocols) |
| 5 | E1–E7 outputs; E6 prediction artifacts | Run manifests | **163/163; 2/2 match** |
| 6 | Served artifacts and their inputs | `data/revised/*_meta.json` | **5/5; 6/6 match** |
| 7 | Production `backend/` (54 files) | `backend_before.sha` (2026-10-11) | **54/54 match** |
| 8 | E8 v1, E8 v2, S1 reference | Recorded hashes / prefix | **Match** |
| 9 | All 16 pre-existing E8 and review documents (v1, v2, v3 ×7, review ×5, r2 items 1–2) | Hashes taken at this task's start (21:07) | **16/16 OK** |
| 10 | Directory listing of `experiments/2026-10-11_devprotocol/` (depth 2) | Start-of-task listing (53 files) | End: 56 files. **The only differences are the three new files 3, 4, 5 in `E8_v3_review_r2/`.** This report (item 6) was written after the comparison. |
| 11 | Project trees changed since 18:40:32: `aipheed-backend-aligned`, `backend`, `frontend`, `Claude outputs`, `aipheed-lean`, `aiPHeed_Simplified_Methodology` (excluding venv, node_modules, .git) | mtime scan, completed (exit 0) | **Only r2 items 1–5.** Nothing in `backend/`, `frontend/` or elsewhere. |
| 12 | `backend/venv` since 18:40:32 | mtime scan, completed (exit 0) | **No changes** |
| 13 | Scheduled-task definitions and memory folder since 18:40:32 | mtime scan | **No changes** |
| 14 | `.git/index`, `.claude/settings.local.json`, `backend/.env` | mtime | Unchanged (2026-10-10 21:24, 2026-08-28, and 2026-10-11 18:59, the authorized edit) |
| 15 | git state | `git status --porcelain`, HEAD, reflog | 23 entries (unchanged); HEAD eee269b; last reflog entry is the 2026-10-06 checkout, so **no commit, checkout, fetch or push since** |
| 16 | Scheduled tasks (start and end of this task) | `list_scheduled_tasks` | Both **enabled**; next runs 2026-10-13 09:02:41 and 15:02:45 local; unchanged |
| 17 | Running sessions (end of this task) | `get_session` | Both still "running"; last activity 08:10:24Z and 08:10:41Z, unchanged |

**Files created** in `E8_v3_review_r2/` (new; nothing overwritten):

| File | SHA-256 |
|---|---|
| `1_DATA_ACCESS_RISK_MAP.md` | `02f778fcba873fd0…`, recorded at this task's start; the file was not hashed when it was created |
| `2_REPOSITORY_EXPOSURE_ASSESSMENT.md` | `2093298d22a004cc…`, same note as item 1 |
| `3_E8_PROTOCOL_REVIEW_R2.md` | `8594605b274318416074fc7619c7b6e58fbfa47065cea9e07051e9e2ce8ee2ee` |
| `4_APPROVAL_CHECKLIST_R2.md` | `525a7fe79ffcb6e87b969dc69f0ccd55fc21ca4b66b6fee5ccf8ef520bc04fba` |
| `5_COMPLETION_ROADMAP_R2.md` | `299fdbae2d4ece5ed2296589e06fb210ee67a66bba6462b3e6066b786d7bb962` |
| `6_INTEGRITY_REPORT_R2.md` | This file; not self-hashed |

**Scratchpad (outside the project):** `r2_start_listing.tsv`, `r2_end_listing.tsv`, `r2_start_hashes.txt`, `r2_integrity_result.json`.

## 2. What changed

**Only the six documentation files listed above.** No hash mismatch, no unexpected file, and no change outside `E8_v3_review_r2/` was found by the checks in §1.

## 3. What remains unknown, or was not checked

| Item | Reason |
|---|---|
| Whether any protected or carrier file has ever been **read**, by any session or person | Not detectable from file state |
| What the two scheduled sessions did, and whether a permission prompt is pending | Transcripts and run summaries are potential carriers; not opened |
| Coverage of carrier files | Requires content access |
| Whether origin still holds eee269b; repository visibility, forks, collaborators | Needs network (RP-1/RP-2); not done |
| Publication dates of the first 2026-Q4 outcome components | Not looked up, to avoid exposure |
| Whether any Q4 outcome information has already been published or seen | Unknown; not checkable safely |
| Full data-access trace of production `app.main` imports and of `test_generalization_protocol` | Code tracing not completed |
| Items 1–2 hashes at creation time | Not taken then. First recorded at 21:07; unchanged since. |
| `Claude outputs/` non-data files and `mlruns/` | Not in any hash record (metadata only) |
| Whether this report's own write produced any side effect | Covered only by the post-write check reported in the chat reply, not by this file |
