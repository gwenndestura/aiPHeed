# E18 Integrity and Reproducibility

## 1. Sequence

| Time (2026-10-13) | Step |
|---|---|
| ~12:05–12:12 | Authorized Jan–Jun 2026 sources verified (manifest hashes, README, footer range ≤ 2026-Q2, retrieval timestamps before the origin) |
| **12:13:17** | **Protocol frozen:** `E18_PROTOCOL.md`, SHA-256 `85c50682…` |
| **13:15–13:20** | **A git operation outside this session** (two commits reset away; `stash -u`; checkout of `e13-da-predictive-accuracy`; stash pop with conflicts). It converted many untracked files to CRLF line endings and staged 1,532 files, including protected data. |
| After | At your instruction: `git reset` (unstage only); the 9 conflicted E13 files restored from `stash@{0}`; E13 committed alone and pushed (`bcd7080`). `stash@{0}` kept. |
| After | **Line endings restored** only where the CR-stripped bytes reproduce the recorded SHA-256 exactly: E9–E12 (61 files), E15–E17 v3 (134 files), devprotocol and evidence records (23 files), and the E18 files. **No content was changed.** |
| 14:55 | E18 run `runs/20261013T065509Z` |
| — | Replicate run: **6 output tables byte-identical** |

## 2. Checks

| Check | Result |
|---|---|
| E18 synthetic tests | **10 passed** (`tests/pytest_output.txt`) |
| Dashboard copy tests | **8 passed**; build OK; preview OK |
| Runtime assertions (`integrity_log.json`) | Allowlist hashes matched at the start and end. Components ≤ 2025-Q4, rounds ≤ 2025-Q4, features ≤ 2025-Q4, SWS 2026 ≤ 2026-Q2. CPI 2026 = 2026-01..06, 30 rows. Stratum is balance_luzon. **No guard denials.** |
| **865 recorded hashes** (protected baseline, E1–E7, served metadata, 54 production files, E8) | **865/865 match** after the line-ending restoration |
| Protected file **modification times** | Changed at **13:20:40**, when the stash pop re-created the untracked tree. Contents are **unchanged** (hashes match). |
| E9–E12, E15, E16, E17, E17 v3 file lists | All match after restoration |
| E13 | **Exception:** git-tracked and committed (`5f7765f`, `bcd7080`). Its working copy now has CRLF line endings from the checkout. The pinned files `e13_lib.py` and `run_e13.py` match E15's pins with CR stripped. |

## 3. Rerun

```
cd aipheed-backend-aligned/experiments/2026-10-13_E18_Objectives_Improvement
../../../backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
../../../backend/venv/Scripts/python.exe -B runner/run_e18.py
../../../backend/venv/Scripts/python.exe -B runner/build_dashboard_json.py <run>
cd dashboard_dev && npx vitest run
```

## 4. State left for you

| Item | State |
|---|---|
| Git | On branch `e13-da-predictive-accuracy`; nothing staged; 14 of your backend and frontend edits uncommitted; `stash@{0}` and `stash@{1}` kept |
| `.claude/launch.json` | One entry added, `e18-dashboard-dev` |
| E18 | Not committed or pushed |
