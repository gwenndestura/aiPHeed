# E11 Integrity Report (2026-10-12, final checks at 23:02 local)

**Hashes vs access.** Matching hashes show that file **contents are unchanged**. They are **not** evidence that a file was never read. Evidence about reads comes only from the guard's access log, and only inside the guarded E10 and E11 processes.

## 1. What was run

| Run | Guard | Data read | Result |
|---|---|---|---|
| E10 Q4 forecast (`q4_forecast.py`, issued 14:51:50 UTC) | E10 guard + the 2026-H1 CPI file (hash-pinned) | Allowlist only; parquet scans filtered to ≤ 2025-Q4; the 2026-H1 CPI file (January–June, exposed, not protected) | Sealed; 5 read-only files; outputs match the manifest |
| E11 synthetic tests (7) | E11 guard | None (synthetic) | **7 passed** |
| E11 experiment (`run_e11.py`, run `20261012T145620Z`) | E11 guard | Allowlist only: 3 parquet scans (120, 120 and 95 rows, ≤ 2025-Q4) + 3 small files | 48 outputs; frame equals E9's; two identical passes; sealed before reveal; **no guard denial** |

**Not run:**

- no existing project test;
- no production pipeline or dashboard;
- no evaluation on any 2026 outcome;
- no network access.

## 2. Verification against existing records

| Check | Result |
|---|---|
| 865 recorded hashes: protected and carrier baseline (55), E1–E7 inputs, protocols and outputs, served artifacts and their inputs, 54 production `backend/` files, E8 v1/v2 | **865/865 match.** No size or mtime change in the protected baseline. |
| E9: 43 listed files + `08_INTEGRITY_REPORT.md` + the list | **All match** (unchanged) |
| E8 v3, the first review, r2 items 1–6 | **All match** |
| E10: 11 listed files | **All match.** The Q4 protocol still hashes to `55c96b54…`. |
| E10 sealed Q4 files vs `q4/manifest.json` | **All match.** Manifest hash `a3903086…`; files read-only. |
| E11 run outputs vs its manifest | **8/8 match.** Allowlist hashes identical at the start and end. |
| E11 protocol vs the hash in the run manifest | **Identical** (`878b8b4d…`) |

## 3. What changed

| Scope | Result |
|---|---|
| Change scan since 22:39 (project trees; excluding venv, node_modules, .git; completed) | Only files in `2026-10-12_E10_selection_alignment_q4/` (`runner/q4_forecast.py`, `q4/`) and `2026-10-12_E11_LightGBM_Improvement/` |
| `backend/venv` | No change |
| Scheduled tasks | `aipheed` and `aipheed-auditing` both still **disabled** |
| Git | HEAD eee269b; 23 status entries; `.git/index` unchanged; no commit, push or fetch |
| Production `backend/`, `.env`, frontend, served artifacts, thresholds, dashboard | Unchanged |

## 4. Not verifiable

- Reads of any file by other sessions or people, or before the guards existed.
- Official RSSO IV-A provincial CPI release dates.
- The current state of the remote repository.
- Whether 2026-Q4 outcome components have been published. Deliberately not looked up; checked only at outcome collection.
