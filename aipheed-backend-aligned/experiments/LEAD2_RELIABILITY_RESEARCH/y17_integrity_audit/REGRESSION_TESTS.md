# Y18 regression and test results

All runs used `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`. Every write went to pytest temporary directories or to `y17_integrity_audit/out/`.

## 1. Y16 suite (`y16_kalman_prospective/tests/test_y16.py`)

**19 passed (114 s).** This includes the historical-parity test: issued PERS and KAL equal Y15 to < 1e-4, so the **forecast values are unchanged**.

Edits to the test file (fixtures and API only; no assertion was weakened):

| Change | Reason |
|---|---|
| Synthetic overlay rows now use `https://example.org/...` URLs and entry times on or after publication | Required by X2 |
| Future-dated rows for the same area and quarter now carry different values (40.0 / 41.0) | Identical values would trip the X3 probable-duplicate rule |
| `AssertionError` expectations → `ValueError` / `IntegrityError` | X1 |
| The no-overwrite check is now two checks | A second valid seal is refused with `ReissueError`; a second dry-run seal with the same timestamp still raises `FileExistsError` (exclusive create) |
| Evaluation tests on pseudo-seals pass `allow_clock_override=True` | Their seals use a caller-supplied clock, which the real evaluation refuses (F9) |
| New assertion | The primary output contains the Amendment-1 sensitivity analysis and supplementary calibration |

## 2. Y18 regression suite (`tests/test_regression_y18.py`)

**71 passed (233 s).** One or more passing tests for every confirmed Y17 defect.

| Fix | Y17 finding | Regression tests (all pass) |
|---|---|---|
| X1 | F1 | No `assert` statement in any runner file (AST scan). Under `python -O` (subprocess) each of these is still rejected, with a non-zero exit and the named exception: <br>• a changed plan; <br>• a changed amendment; <br>• 5 invalid issue dates; <br>• an invalid overlay; <br>• a tampered seal; <br>• an out-of-window issue (which also writes no folder). |
| X2 | F2, F3 | 24 single-field-invalid rows. **Each row has exactly one bad field**, so each rejection is attributable to it, and the error names the row and field: H 150 / −3 / nan / inf / text; MoE −4 / 0 / 20; quarter Q9 / two-digit year; area XX / leading space; published `01/12/2027`, with time, with timezone, 2026-02-30, empty, before its quarter, after entry; entry time without time or with an offset; URL empty / http / bare. <br>Also: header mismatch rejected; a valid row keeps its source metadata; rows on or after the cutoff are excluded, listed in the seal, and leave the forecast unaffected. |
| X3 | F4, F5 | Rejected: an exact duplicate; conflicting values; the same value under a different date; a conflict with the project series; a project value under another date. <br>An exact project duplicate is ignored and reported. A legitimate second round is added and reported. A failed validation leaves the previously installed series untouched. |
| X4 | F7, F12 | The seal holds the exact rows used (URL, dates), a snapshot hash that recomputes, the overlay hash, plan and amendment hashes, model-file hashes (including `evaluate.py` and `attest.py`) and environment versions (F16). Appending to the overlay changes neither the seal nor its verification. An altered or removed used row stops the evaluation. |
| X5 | F8 | Detected: a deleted registered seal, an unregistered file and a malformed registry line. A re-issue is refused. A manually planted second valid seal is reported as a re-issue, and only the first counts. A consistent rewrite of seal and registry is **not** detectable locally, and the code states this limit instead of claiming protection. |
| X6 | F9 | The attestation payload contains issue, target, seal SHA-256, plan and amendment hashes, and the write time. Status is `pending` at issuance; the operator records `completed` or `unavailable`, and `pending` cannot be set by hand. Empty evidence is rejected. The evaluation reports the status. No networking module is imported by any runner file. A caller-supplied clock is marked in the seal and refused by the real evaluation. |
| X7 | F11 | Failed real attempts are logged with timestamp, requested date, error type, message and versions, and the **original exception type is preserved**, for each of: invalid date (`ValueError`), invalid overlay (`OverlayError`), existing seal (`ReissueError`), outside the window (`IssueWindowError`), plan mismatch (`IntegrityError`). No seal is created, and nothing enters `load_seals`. Dry runs are not attempts and are never valid. The CLI refuses and logs a non-canonical overlay for a real issue (F17). |
| Evaluation | F6, F10, F11, F14, F18 | **F6:** the primary lock is written once, an identical rerun is accepted, a differing rerun raises, and the file is never rewritten. <br>**F10:** calibration is supplementary; bins are always computed; the slope is "unavailable" when n < 10. <br>**F11:** missed issues are counted only after the window closes. <br>**F14:** the block bootstrap uses L = 4, is deterministic, is "unavailable" when n < 8, and gives the same mean difference as the primary; the verdict logic means a failed primary result is never rescued. <br>**F18:** the Manila date is used. <br>The amendment hash matches and is enforced (the Y17 copy is byte-identical). The plan hash is unchanged. |

## 3. Original Y17 adversarial suite (`tests/test_adversarial.py`, kept unchanged as audit evidence)

**28 passed, 24 failed, 4 xfailed (116 s).** Outputs: `out/y18_adversarial_rerun.txt`, `out/y18_adversarial_reasons.txt`, `out/y18_adversarial_fixture_failures.txt`.

Every change from the Y17 result (36 passed, 20 xfailed) is explained below. None indicates a regression.

| Group | Tests | Why |
|---|---|---|
| **16 XPASS(strict)**, counted as failures by the strict marker | A4, A6, B4, B7, D1 ×8, D3, D5, D8, E4 | **The defects are fixed.** The strict marker reports the unexpected pass for review. (The D1 cases use the source URL `u`, so they now also fail X2 for that reason. The regression suite isolates each field properly.) |
| 2 failures: new exception types | A3 (expects `AssertionError`, gets `IntegrityError`); D2 (expects `AssertionError`, gets `OverlayError`) | Correct rejections, under the explicit exceptions required by X1 |
| 5 failures: fixtures now invalid | B6 ×3, C3, D4 | The synthetic rows have entry times before publication, the URL `u`, or a time in `published`, so X2 rejects them before the property is reached. The properties (cutoff exclusion, persistence = newest reading, ignoring project duplicates) are re-tested with valid rows in the Y16 suite and the regression suite. |
| 1 failure: now refused | D7 | `load_seals` without the test flag refuses a caller-supplied clock (F9). The consistent-rewrite limit is re-tested in `test_X5_documented_limit_...`. |
| 4 remaining XFAIL | C4, E6 (invalid fixtures: entry before publication, URL `u`); D9 (the re-issue is refused at source by `ReissueError`); E5 (caller-supplied clock refused) | They fail on the new protections, **not** on the old defects. Each property is covered by a passing regression test. |

The Y17 evidence file was not edited, so its original findings remain reproducible against the pre-fix code. `test_regression_y18.py` is the authoritative regression suite going forward.
