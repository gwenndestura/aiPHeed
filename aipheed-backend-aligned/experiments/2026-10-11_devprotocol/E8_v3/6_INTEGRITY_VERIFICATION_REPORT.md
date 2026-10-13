# E8 v3: Integrity Verification Report

**Performed 2026-10-12, 17:50–18:08 local (Asia/Manila).** Only file metadata, SHA-256 of raw bytes, git object hashes and this project's own JSON records were used.

- **No protected or potential-carrier file was parsed, decoded or printed.**
- **No session transcript was opened.**
- **No evaluation, forecast, label, training or rescoring was run.**

Scripts and outputs:

- Check script: the scratchpad's `e8v3_integrity.py`. It hashes in binary chunks and parses only run configs, manifests and served-artifact meta.
- Full result: the scratchpad's `e8v3_integrity_result.json`.
- New baseline: `protected_and_carrier_files_sha256_20261012.txt` (this folder).

## 1. Checks performed and results

| # | Check | Reference record | Result |
|---|---|---|---|
| 1 | Inputs of each earlier run vs the input hashes in its `config.json` | E1 (122), E2 (100), E3 (122), E4 (122), E5 (100), recorded 2026-10-11 | **All match**: 122/122, 100/100, 122/122, 122/122, 100/100. None missing. |
| 2 | Protocol file of each run vs the protocol SHA-256 in its config | E1–E5 configs | **All match** (5/5) |
| 3 | Code hashes recorded in each config (runner, devprotocol, helper) | E1–E5 configs | **Every recorded hash matches a current file of the expected name**: `run_exploratory.py`, `run_e2_relative_cpi.py`, `run_e3_compact_lgbm.py`, `run_e4_risk_definitions.py`, `run_e5_scoring.py`, `scripts/supplementary/devprotocol_rule_l.py` |
| 4 | Run outputs vs `outputs_sha256` in each manifest | E1 `manifest.json` (61 files), E2 (14), E3 (31), E4 (31), E5 (17), E6 (2), E7 `manifest_posthoc.json` (7) | **All match**: 163/163 |
| 5 | E6 prediction artifacts vs `prediction_artifacts_sha256` | E6 manifest | **Match** (2/2): served retrospective artifact; approved-reference evaluation artifact |
| 6 | Served artifacts and their inputs vs their meta `sha256` blocks | `data/revised/revised_forecasts_retrospective_meta.json` (5 entries); `datadriven_forecasts_retrospective_meta.json` (6 entries) | **All match** (5/5, 6/6): artifact, labels, psa, `revised_trainer.py`, `datadriven_trainer.py`, `risk_score_v2.py` |
| 7 | Production `backend/` vs the pre-change baseline | Scratchpad `backend_before.sha` (54 files, recorded 2026-10-11 before the `.env` edit) | **All match**: 54/54 |
| 8 | Production files with documented or possible 2026-H2 rows: working copy vs git HEAD blob | git objects | **16/16 tracked files equal HEAD** (list in checklist 3, §2.1). Last commits are 2026-09-02 to 2026-09-29; none after. |
| 9 | Untracked production files | `git ls-files --error-unmatch`, `git check-ignore` | `cpi_full.pre2026.parquet` and `feature_provenance.json` are **untracked and git-ignored** (`backend/.gitignore:25`). **No earlier hash record exists for them**; their hashes are recorded now in the baseline. |
| 10 | E8 v1 unchanged | Recorded prefix `81e6e2132ec772b9` | **Match**: `81e6e2132ec772b98fa2a7b556dcbd3dab1de1ab162b23f5740f9b464229fb42` |
| 11 | E8 v2 unchanged | **No earlier hash record** | Hash now `b328021ac585a036e5ceff27aa2092bcf3c9c342715bf36e6ab8e38d9e6aee26`. Its mtime (2026-10-12 17:36) is its creation time in this session, and it has not been modified since. "Unchanged" rests on the mtime, not on a hash comparison. |
| 12 | `S1_FROZEN_REFERENCE_PROPOSAL.json` unchanged | Recorded prefix `dc77104476c28141` | **Match** |
| 13 | Aligned `cpi_full.parquet` vs production copies | Hash equality | **Byte-identical to production `cpi_full.parquet`** (committed 2026-09-10); differs from `cpi_full.pre2026.parquet` |
| 14 | Production scheduler block | `grep -c '^SCHEDULER_ENABLED=false$' backend/.env` (count only; no other line printed) | **Present** (1) |
| 15 | APScheduler output folders | `ls` | `backend/data/pipeline_runs/` and `backend/models/candidates/` **do not exist**, so no pipeline run has produced outputs |
| 16 | Served artifacts' target quarters (to confirm no 2026-Q3/Q4 forecast exists) | `target_quarter` column of this session's own served parquet files | **Latest target is 2025-Q4** in both |
| 17 | Earlier frozen 2026 forecasts | Session records of 2026-10-09 files | Targets 2026-Q1/Q2 only (from earlier session records; **not re-opened today**) |
| 18 | git working-tree status | `git status --porcelain` | **23 entries, identical entry for entry to the snapshot at the start of this session** (14 modified, 9 untracked). An earlier note in this session expected 20; that figure was wrong, not a change in the tree. `.git/index` was last written 2026-10-10 21:24. |

## 2. Did any files change?

| Scope | Method | Result |
|---|---|---|
| Earlier artifacts, inputs, served models, production backend | Checks 1–10, 12 | **No change detected** in any file with a prior hash record |
| Six project trees (`aipheed-backend-aligned`, `backend`, `frontend`, `Claude outputs`, `aipheed-lean`, `aiPHeed_Simplified_Methodology`) since the scheduled sessions started (2026-10-12 16:10 local) | mtime scan, excluding venv and node_modules | 41 files changed **before** this step, all this session's own E6/E7/E8 v1/v2 work in `aipheed-backend-aligned/`. **None in `backend/`, `frontend/` or the other trees.** |
| Same trees since 17:40 local (this step) | mtime scan, plus a separate scan of `backend/venv` | **Only the six files in this `E8_v3/` folder.** No change in `backend/venv`. |

**Files created by this step** (all new; nothing overwritten; SHA-256 at completion of items 1–5):

| File | SHA-256 |
|---|---|
| `1_E8_PREREGISTRATION_DRAFT_v3.md` | `4f221ec57d17903a96f088e5d0b080900f804b69a0ba24836f50e9c1ad23068a` |
| `2_HISTORICAL_SIMULATION_AND_LEAKAGE_CHECKLIST.md` | `98d73742f544ed7cb8d2fa75a691816d8ef97703e470ff8769d94319203ac397` |
| `3_PROTECTED_DATA_ACCESS_CHECKLIST.md` | `8b4c9cd44de0e77f8cda8e719e4252c7b364e5c44c81a55844c788be0cdccbc2` |
| `4_SCHEDULED_TASK_REVIEW.md` | `bb55977e67bc2455680354e7fdec862b5ba10723e2142ab1e3f9b0df31036a8c` |
| `5_APPROVAL_CHECKLIST.md` | `9c7bf405f0147c65df13b55fa57284d3478a9f3ad2d5464ee3a056e552a87f1e` |
| `protected_and_carrier_files_sha256_20261012.txt` (55 files) | `9821bf645b5dde4502aefbb91a6e3b09a42f4e947bce1006fe2e4a5732fc0e59` |
| `6_INTEGRITY_VERIFICATION_REPORT.md` | (this file; not self-hashed) |

**Scratchpad (outside the project):** `e8v3_integrity.py`, `e8v3_integrity_result.json`.

## 3. What could not be checked safely, or was not checked

| Item | Why | Status |
|---|---|---|
| Whether any protected file has been **read** by this or another session | Reads leave no trace on disk; hashes and mtimes detect only changes | **Not checkable.** This session's own command history contains no content access to protected or carrier files during this step. |
| What the two running scheduled sessions did | Their transcripts are potential carriers | **Not checked.** Metadata only: last activity 08:10:24Z and 08:10:41Z; no file changes in the project trees. |
| Coverage (quarters, columns) of every carrier file | Would require reading content | **Not checked.** Treated as protected. |
| Production `psa_indicators.parquet` and `panel.parquet` 2026-H2 contents | Protected | Not checked. Described from earlier session records only. |
| `Claude outputs/*.docx`, `*.html` | Outside the baseline's file types | Metadata only. **Not hashed.** |
| `mlruns/` folders (225 files in aligned) | Many small files | Metadata only. **Not hashed.** |
| `backend/data/processed/food_availability_tuned.json` | Omitted from the baseline list | **Not hashed** |
| Aligned `data/supplementary/collection_2026-10-09/*` against its `COLLECTION_MANIFEST.json` | Not re-run today; covered indirectly by E1/E3/E4 input records (122 entries) | **Matched via check 1**, not via its own manifest |
| E8 v2 against a prior hash | No prior record | mtime only (check 11) |
| Release dates of any input | No lookup authorized | Not verified (checklist 2) |

## 4. Corrections made during this step (before the documents were finalized)

1. **Script flag.** The integrity script first marked `cpi_full.pre2026.parquet` as "tracked". `git rev-parse` echoes the spec for a missing path, so the flag was a false positive. `git ls-files` confirms the file is untracked (row 9).
2. **Leakage checklist B3.** The first draft said 2026 labels "fail L1 at C3". That is wrong for 2026-Q1, which was computable by 2026-05-12. It now says the exclusion is a design rule (approval A6).
3. **Leakage checklist E3.** The first draft said the served artifact covers quarters up to 2026-Q2. The checked target quarters end at 2025-Q4 (row 16).
4. **Protocol §8.1.** The SWS margin justification cited a sampling error from memory. It was replaced with the worst-case binomial arithmetic, and the sample sizes are marked unverified.

## 5. Not done

No scheduled task was changed, paused, run or stopped. No configuration was changed. Nothing was committed, pushed, deployed or served. No protocol step was executed.
