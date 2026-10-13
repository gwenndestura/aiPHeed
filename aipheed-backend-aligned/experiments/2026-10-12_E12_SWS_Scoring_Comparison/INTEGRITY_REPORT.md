# E12 Integrity Report (2026-10-12, final checks at 23:16 local)

**Hashes vs access.** Matching hashes show that file **contents are unchanged**. They are **not** evidence that a file was never read. Evidence about reads comes only from the guard log of the E12 processes.

## 1. What ran

| Process | Guard | Data | Result |
|---|---|---|---|
| `runner/investigate_s1.py` (S1 reproduction investigation) | E12 | Allowlist parquet (≤ 2025-Q4) + E9 S1 reference (read-only) | `s1_reproduction_investigation.json` |
| Synthetic tests (9) | E12 | None | **9 passed** |
| `runner/run_e12.py` (run `20261012T151208Z`) | E12 | 4 parquet scans (`psa_indicators` 120 rows, `features_fused` 120, `labels` 95 twice), each filtered to ≤ 2025-Q4; 3 small allowlisted files; E9 reference and frame (read-only) | Gate 3.55e-15 vs E9; 6 CSV deliverables; details and manifest |

**No guard denial. No protected file, carrier file, production file, database, model or transcript opened.** Allowlist hashes were identical at the start and end.

## 2. Verification against existing records

| Check | Result |
|---|---|
| 865 recorded hashes (protected baseline, E1–E7, served artifacts, 54 production files, E8 v1/v2) | **865/865 match.** No protected size or mtime change. |
| E9, E10 (both lists), E11 file lists; E8 v3, the first review, r2 | **All match** (0 failures) |
| E12 protocol vs the hash recorded at run start | **Unchanged** |
| E12 run outputs (3) and CSV deliverables (6) vs the manifest | **All match** |

## 3. What changed

| Scope | Result |
|---|---|
| Change scan since 23:07 (project trees; excluding venv, node_modules, .git; completed) | **Only files in `2026-10-12_E12_SWS_Scoring_Comparison/`** |
| `backend/venv` | No change |
| Scheduled tasks | Both still **disabled** |
| Git | HEAD eee269b; 23 status entries; `.git/index` unchanged; no commit, push or fetch |
| Production, frontend, served artifacts, thresholds, dashboard, E9, E10, E11 | Unchanged |

## 4. Disclosed decisions and limits

1. **S1 gate:** passed against the E9 full-precision reference (3.55e-15). Against the 4-decimal stored `labels.parquet` column it is 3.33e-5, fully explained as rounding (80/80 rows equal after round(·, 4)). The run proceeded on the full-precision values; see `S1_BASELINE_REPRODUCTION.md`.
2. **Category B is internal consistency only** (target = S1), on 7 reused quarters.
3. **No independent provincial outcome exists,** so food-insecurity accuracy is not evaluable.
4. **Not verifiable:** official provincial release dates; reads by other sessions or people.
