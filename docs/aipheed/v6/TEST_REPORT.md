# v6 Test report

## 1. Full suite

**Command:** `cd backend && python -m pytest -q -p no:cacheprovider -rfs` → `results/final_tests_v6.txt` (VERIFIED).

| Run | Passed | Failed | Skipped |
|---|---|---|---|
| End of v4 | 1331 | 0 | 18 |
| **v6 final** | **1350** | **0** | **18** (the same pre-existing `E34 superseded` skips) |

- **New tests:** 19 (17 in `test_v6_core.py`, 2 in `test_v6_preregistration.py`). No test was deleted, skipped or weakened.
- **Scope note:** a separate v9/v10 session works in this same worktree. The suite collects whatever test files were present at that moment, so the total may include that session's tests.

## 2. What the new tests cover

| Area | Tests |
|---|---|
| **Integrity** | Both v6 seals' hashes; only unpublished targets; seal reproducible; development rows and verdict labels; scorer covers all 8 baselines |
| **Leakage** | An injected round on the issue day or after never changes LightGBM forecasts; the same round a day earlier does (positive control); training truth known at the issue; history features point-in-time |
| **LightGBM** | Configuration equals the pre-registration; deterministic (identical model text); fallback under 30 rows; TreeSHAP + expected value = prediction; **learns a planted signal** (correlation > 0.7, so "no gain on hunger" is not a broken learner) |
| **Rules** | Selection rule (replaces only with CI above 0 on ≥ 6 quarters); DM-HLN statistic against a hand computation |
| **Serving** | Tamper refused; rebuild reproduces the hash; write-once; never refits (`fit` patched to raise); store = inference; status = verdict file; forced LightGBM path matches the seal and explains exactly |
| **Geo, API** | 142 LGUs, 5 provinces, `null` estimates; 200 / 404 / 405 / 422 |

## 3. Coverage (measured)

`cd backend && python -I scripts/v2_coverage.py v6` (standard-library tracer, as in v2; coverage.py is not installed and nothing was downloaded):
- **90.1 %** (1685 / 1870) of `app/forecasting/**`, the hunger-forecast router and `app/paths.py`;
- **v6 package 92.8 %** (346 / 373).

The other session's `app/forecasting/v9` is excluded from this scope. Per-file figures: `results/coverage.txt`.

## 4. Mutation spot check, including one mistake of mine

**First version (file-editing).** It planted bugs in the source files on disk, one at a time, and restored them.
- **Result:** 6 of 7 killed, and **one survived**: the `as_of` leak. My injected-round test only used a round dated 3 days after the issue, so a boundary leak of up to 1 day passed. **Fixed:** the test now also injects on the issue day.
- **Incident:** this worktree is shared with another session, so the temporary edits (about 12:07–12:11 PHT on 2026-11-02) were visible to it. That session noticed `num_leaves = 31`.
  - All files were restored, and `git diff` was verified empty.
  - That session reran its stage after the window and reports byte-identical output (its report; not checked by me).

**Current version.** `backend/scripts/v6_mutation_check.py` now patches **in a subprocess only and edits no file** (`results/mutation_check.txt`, VERIFIED):

| Mutant | Result |
|---|---|
| `as_of` on or before issue + 1 day | KILLED |
| History features use every round (hindsight) | KILLED |
| Selection: challenger always replaces | KILLED |
| Snapshot guard disabled | KILLED |
| LightGBM minimum rows 30 → 3 | KILLED |
| LightGBM `num_leaves` 4 → 31 | KILLED |

**6 of 6 killed.** The seventh earlier mutant (change not added to the anchor) was killed in the first run and was not carried into the in-process version. `backend/scripts/v2_mutation_check.py` still edits files on disk; **do not run it while another session shares the worktree.**

## 5. End to end

`python -I backend/scripts/v6_e2e.py`: 2 script runs × 2 internal runs; output files byte-identical (`cmp`). Artifact hash = committed, store = committed, API = inference, seal reproduced, 142 LGUs, decomposition error ≤ 1e-3 (VERIFIED, `results/v6_e2e_run.json`).

## 6. Hashes at the end

`PROTOCOL_LOCK.md` `8bae6962…dd0d3`, the v2, v4 and v6 pre-registrations, and the tier and seal hashes are all unchanged: the hash tests are part of the 1350 passed, and the lock was re-checked with `sha256sum`.
