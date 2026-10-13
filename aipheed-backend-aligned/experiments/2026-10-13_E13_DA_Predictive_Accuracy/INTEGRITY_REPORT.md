# E13 Integrity Report (2026-10-13; final checks at 10:38 local)

**Hashes and access are different things.** Matching hashes show that file **contents are unchanged**. They are **not** evidence that a file was never read. Evidence about reads comes only from the E13 guard and its access log, which cover E13's own Python processes.

## 1. What ran and what it opened

| Process | Guard | Files opened (from the access log) | Result |
|---|---|---|---|
| `runner/inspect_inputs.py` | E13 | The 5 allowlisted files only | Input inventory |
| Synthetic tests (twice) | Guard decisions tested without opening data | None | 23 passed, both times |
| `runner/run_e13.py`, primary (`20261013T022702Z`) and replicate (`20261013T023112Z`) | E13 | The 5 allowlisted files only, each hash-verified before reading. Parquet reads filtered to 2021 ≤ year ≤ 2025. | Identical outputs |
| `runner/post_raw_coefficients.py`, `runner/post_province_tables.py` | E13 | Only this experiment's `scored_rows.csv` | Descriptive tables |

**No guard denial occurred.** E13 opened no protected, mixed, carrier, production-code, database, model or transcript file.

- **One production file was read:** `backend/data/processed/psa_subsistence.parquet`, which contains years 2018–2023. It was read through the guard and **was not changed**.
- **No web page of PSA, SWS or RSSO was opened.** Two searches were restricted to the DOST-FNRI domains.
- **Allowlist hashes** were identical at the start and end of every run.

## 2. Verification against existing records

| Check | Start (10:17) | End (10:38) |
|---|---|---|
| 865 recorded hashes: protected baseline (55), E1–E7 run records, served model metadata, 54 production files, E8 v1/v2 | 865/865 match | **865/865 match.** The start and end result files are identical apart from their timestamp. |
| E9 (43), E10 (11 + 6), E11 (28) and E12 (30) file hash lists | 0 failures | **0 failures** |
| E13 protocol against its frozen hash | — | **Unchanged** (`c379c039…`) |

**A disclosed mistake:** the first attempt to compare the start and end integrity files printed "identical" because of a path error, which made both inputs empty. The comparison was redone correctly, and the result above is from the corrected comparison.

## 3. What changed

| Scope | Result |
|---|---|
| Files modified since 10:17:09 in the project tree (excluding `backend/venv`, `node_modules`, `.git`) | **Only files inside `2026-10-13_E13_DA_Predictive_Accuracy/`** |
| `backend/venv` | Used as the interpreter. Not modified (excluded from the scan; production hash checks pass). |
| Production backend, frontend, served models, thresholds, dashboard, thesis chapters | Unchanged |
| E9, E10 (including the sealed Q4 forecast), E11, E12 | Unchanged |
| Scheduled tasks `aipheed` and `aipheed-auditing` | Both still **disabled** (checked with `list_scheduled_tasks`; no run history or transcript read) |
| Git before the push step | HEAD `eee269b`; 23 status entries; `.git/index` unchanged (`d58b4059…`) |

## 4. Git push (requested by the user during the run)

Partway through E13, you asked to "push this to another new branch". That overrides the brief's original no-push rule for this folder only.

**Planned method:**

- Create a new branch from the current HEAD (`eee269b`, already on `origin/backend+frontend`).
- Add **one commit** containing **only** this folder.
- Push only that branch.

**What the method avoids:**

- It uses a temporary index, so `.git/index`, the working tree and the checked-out branch (`backend+frontend`) are not touched.
- It includes nothing from production, `aipheed-backend-aligned/data`, `Claude outputs/` or the other uncommitted changes.
- The repository has no active hooks. None are configured and only the sample hooks exist.

**Where the outcome is reported:** the branch name and commit hash are in the final report, because this file is part of the commit.

## 5. Disclosed limits

1. **Not a new independent test.** All test quarters were examined in E1–E12. The analyst was not blind.
2. **Provincial CPI release dates are proxies.** The T−2 rule is a calendar argument, not a verified date check.
3. **Inputs 1 and 2 were derived by E12** from mixed files read with a filter. E13 trusts their contents through the hashes recorded by E12.
4. **No independent provincial food-insecurity outcome exists,** so provincial food-insecurity accuracy was not evaluated.
5. **The web-search summaries about FNRI provincial ENNS** were not checked against FNRI's primary tables.
6. **Not verifiable:** reads by other sessions or people.
