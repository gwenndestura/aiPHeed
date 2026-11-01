# v2 Test report

**Command:** `cd backend && python -m pytest -q -p no:cacheprovider -rfs` (backend venv).

## 1. Full-suite runs

| Run | Executed | Passed | Failed | Skipped | Evidence |
|---|---|---|---|---|---|
| Start of v2 (previous final, `9f975ec`) | 1298 | 1280 | 0 | 18 | `../final_tests.txt` |
| After the D4 path rewrite, uncommitted | 1322 | 1294 | **10** | 18 | `results/tests_after_d4.txt` (VERIFIED) |
| **Final (after all v2 work)** | 1335 | **1317** | **0** | 18 | `results/final_tests_v2.txt` (VERIFIED) |

**Classification of the 10 failures after the D4 rewrite.** No test was deleted, skipped or weakened.

| Failure | Count | Classification | Resolution |
|---|---|---|---|
| `test_e119r2_framework::test_all_validation_checks_pass`, `test_e120_firi_design::test_e120_checks_pass` | 2 | **Intended change.** These experiment self-checks require `git status -- backend/app` to be clean, and the edits were uncommitted. | Pass after commit, as in the earlier phase-1 run |
| `test_e126 / e127 / firi3::test_firi_v2_untouched`, `test_e128 / e129 / e131::test_production_untouched`, `test_e130::…_untouched` | 7 | **Regression caused by me.** The D4 rewrite edited `app/ml/inference/firi.py`, which 7 frozen-experiment guards pin byte-for-byte. | `firi.py` reverted to its frozen bytes; documented as a D4 exception |
| `test_e83_monthly_refresh::test_monthly_refresh_logs_success` | 1 | **Regression caused by me.** The test sandboxes the monthly refresh with `chdir`; the rewrite made it read the real article store (9 667 articles instead of 1). | `app/tasks/scheduler.py` reverted; documented as a D4 exception |

The 18 skips are the pre-existing `E34 superseded by the E31 promotion` skips, unchanged.

## 2. New v2 tests (37)

| File | Tests | Covers |
|---|---|---|
| `test_v2_preregistration.py` | 2 | Pre-registration SHA-256 (LF-normalised) frozen; an edit is detected |
| `test_v2_core.py` | 23 | See below |
| `test_v2_defects.py` | 3 | **D3:** re-export identical on 135/135 panel rows and no version warning. **D9:** the missing legacy pickle fails loudly. **P0H4 relabel:** price-pressure, not food insecurity; `id` and computation unchanged. |
| `test_v2_paths.py` | 2 | **D4:** `backend_path` resolution; 6 API routes byte-identical from `backend/` and from the repo root (fresh subprocesses, fixed clock) |
| `test_v2_legacy_leakage.py` | 7 | FIRI v2 prior excludes the same and later origins; news `asof` drops articles at or after O(t); dashboard cutoff exclusive. Each has a positive control. |

**`test_v2_core.py` covers:**
- **Leakage:**
  - injected rounds on or after the issue do not change the forecast;
  - one day earlier they **do** (positive control);
  - a feature row at the issue raises;
  - inner truth uses only values known at the outer issue;
  - context indicators are point-in-time.
- **Alignment:** Lead k = D − 1 + k and Lead 2 = the dashboard target, at 3 issues.
- **Models:**
  - LL equals the independent E131 local level on 272/272 rows;
  - PERSIST = latest;
  - κ stays in its grid.
- **Selection rule:** replaces only with a CI above 0 on ≥ 6 quarters (synthetic cases); conformal rank rule and minimum.
- **Decision table** labels.
- **Artifacts:** tamper, config, model and status edits are refused; write-once; the rebuild reproduces the hash.
- **Inference:** never refits (fit patched to raise); fails loudly; store = fresh inference.
- **Explanations:** exact, hash-bound, "last observed value carried forward".
- **Status:** the served status equals the mechanical verdict; frozen N1–N7 re-applied reproduce the committed labels.
- **Geography:** 142 LGUs; injected duplicate + drop and wrong province are detected.
- **API:** 200 / 404 / 405 / 422, context, legacy "superseded".
- **Seal:** hash unchanged and reproducible; only unpublished targets.

## 3. Coverage (measured)

**Measured with:** `cd backend && python -I scripts/v2_coverage.py`.
- **Method:** standard-library `sys.settrace` + `threading.settrace` line tracing. Executable lines are the code-object line tables (`co_lines`).
- **Why not coverage.py:** coverage.py / pytest-cov are not installed, and nothing was downloaded.
- **Scope:** `app/forecasting/**` (including v2 and `safe_load`), `app/api/v1/hunger_forecast.py` and `app/paths.py`, over the 7 forecasting/v2 test files.

| Scope | Lines hit / executable | % |
|---|---|---|
| **Total** | **918 / 1038** | **88.4 %** |
| `app/forecasting/v2/*` | 381 / 419 | 90.9 % |
| `app/api/v1/hunger_forecast.py` | 77 / 82 | 93.9 % |
| `app/forecasting/safe_load.py` | 43 / 48 | 89.6 % |

**Lowest files:** `store.py` 57.5 %, `v2/store.py` 62.5 % and `artifact.py` 59.7 %. Their command-line `__main__` blocks and the legacy SEAS-LLM build path are exercised by the E2E and model-report scripts, not by unit tests.

**Per-file detail and missed line numbers:** `results/coverage.json` (VERIFIED).

## 4. Mutation-style spot check (vacuous-test hunt)

**Command:** `cd backend && python -I scripts/v2_mutation_check.py` → `results/mutation_check.txt` (VERIFIED). Each mutant is planted, the guarding tests run, and the file is restored with its hash verified.

| Mutant | Result |
|---|---|
| `as_of`: strictly before → on or before (+1 day) | KILLED |
| v2 lead/target: D − 1 + k → D + k | KILLED |
| v2 inner truth: known at I → all rounds (hindsight) | KILLED |
| News `asof`: `<` O(t) → `<=` O(t) | KILLED |
| FIRI prior: earlier origins → including the origin | KILLED |

**5 of 5 killed: no vacuous guard found.** Two tests were fixed while writing them:
- my first duplicate-LGU injection also removed the duplicated row, so the test could not have failed;
- the two-cwd API test compared a response that echoes the current time; the clock is now pinned with `AIPHEED_NOW`.

## 5. End to end (real data, twice)

**Command:** `python -I backend/scripts/v2_e2e.py` → `results/v2_e2e_run.json` (VERIFIED). It ran as two script invocations of two internal runs each: 4 runs, and the two output files are byte-identical (`cmp`).

**Steps:**
1. Source validation (0 problems).
2. `as_of` (88 area-rounds before 2026-10-01).
3. Walk-forward and inner selection.
4. Artifact built in a temp dir; hash `2614c8ce…` equals the committed one.
5. Leads 1–4 (16 records).
6. Explanations: max decomposition error 0.0; explanation hash = forecast hash.
7. Geography: 142 LGUs, 5 provinces.
8. Store: temp store = committed store.
9. API body = inference.
10. Prospective seal reproduced.

## 6. Hash re-verification at the end

| Item | Result |
|---|---|
| Protocol lock: `PROTOCOL_LOCK.md` SHA-256 `8bae6962…dd0d3`; every locked excerpt | Unchanged (`test_protocol_lock.py`, 4 passed in the final run) |
| Pre-registration `90ad51a9…a691b` | Unchanged (`test_v2_preregistration.py`) |
| Seal `e88f7bb2…25d7` | Unchanged (`test_v2_core.py::test_seal_unchanged_and_reproducible`) |
