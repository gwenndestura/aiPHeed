# E9 Integrity Report

**Task window: 2026-10-12, 21:53 to about 22:18 local.**

**Methods:** SHA-256 of raw bytes, file metadata, git metadata, task and session metadata, and the E9 guard's access log.

**Hashes vs access.** Matching hashes show that contents are **unchanged**. They do **not** show that a file was never read; only the guard log covers reads, and only inside the E9 processes.

## 1. Actions taken (authorized)

| Action | Verified result |
|---|---|
| Disable task `aipheed` | `enabled: false`; no next run (checked at 21:53 and again at the end) |
| Disable task `aipheed-auditing` | `enabled: false`; no next run |
| Interrupt session `local_f3c4b65e…` | `isRunning: false`; last activity 13:53:18Z; not archived |
| Interrupt session `local_918f3167…` | `isRunning: false`; last activity 13:53:21Z; not archived |

No transcript was opened. No other task, session or setting was changed.

## 2. Checks against existing records (final, 22:15)

| Check | Result |
|---|---|
| 865 recorded hashes: 55 protected and carrier files; E1–E5 inputs and protocols; E1–E7 outputs; E6 prediction artifacts; served artifacts and their inputs; 54 production `backend/` files; E8 v1/v2 | **865 match, 0 mismatches.** No size or mtime change in the protected baseline. |
| E8 v3 documents, the first review, and r2 items 1–6 | **All match** their recorded hashes |
| E9 protocol (`03_FROZEN_PROTOCOL.md`) vs the hash recorded in both run manifests | **Unchanged since the runs** |
| E9 runner code vs the manifests | **Unchanged** (`guard`, `metrics`, `run_e9`, `safe_frame`, `vault`) |
| E9 run outputs vs their manifests | **8/8 match** in both runs |
| S1 code (`risk_score_v2.py`) | Hash `5b6c83d6…`, identical to the served-artifact record |
| Allowlisted inputs, start vs end of each run | Identical |

## 3. What changed

**Change scan since 21:53 (excluding venv, node_modules, .git; completed):** only the **43 files** in `experiments/2026-10-12_E9_S1_safe_training/`. Their hashes are listed in `E9_FILES_SHA256.txt`, which excludes itself and this report.

**Unchanged:**

- `backend/venv` (scanned separately; no change, as runs used `-B`);
- the task definition files and memory folder (no mtime change; the task state is held by the app);
- `.git/index`, `backend/.env`, `.claude/settings.local.json`;
- git: 23 status entries, HEAD eee269b, no commit, push or fetch.

**Not changed:** production `backend/`, the frontend, served model artifacts, thresholds, dashboard classifications and deployment.

## 4. Data access during E9 (guard log)

**Parquet reads:** only `psa_indicators`, `features_fused` (4 columns) and `labels`. Each was hash-verified and filtered to `quarter <= 2025-Q4` during the scan.

**Other files opened:** the 2025 SWS CSV, the CPI release-date CSV, `config/governing_model.json` and project code.

**Never opened:** no protected or carrier file, production file, database, model file, transcript or memory file. The one guard denial (a `wmic` CPU-count subprocess) is deviation D1; it involved no data and changed no output.

**The synthetic tests** (35 passed) used only in-memory and temporary synthetic data. **No existing project test was run.**

## 5. Unknown, or not checkable

- Whether any protected or carrier file was ever read outside the E9 processes, by earlier sessions, the scheduled tasks or people.
- What the two scheduled sessions did before they were interrupted.
- The contents of the code-registry constant beyond 2026-Q2. It is loaded at import, filtered by the module, and never inspected.
- Whether the remote still holds commit eee269b, and the repository's visibility. These need network access, which was not used.
