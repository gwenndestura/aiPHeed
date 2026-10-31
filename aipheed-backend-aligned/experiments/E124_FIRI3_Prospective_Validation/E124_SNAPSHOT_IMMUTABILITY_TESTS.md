# E124 snapshot immutability tests

**File.** `backend/tests/unit/test_e124_prospective.py`.

**Test data.** Only **controlled synthetic records** (cyclone counts and palay YoY for the five provinces), written to pytest temporary folders. Nothing is written to the real `store/`.

| Requirement | Test | Result |
|---|---|---|
| No issue before the issue date; the attempt is logged | `test_issue_before_issue_date_is_blocked_and_logged` | PASS (the attempt is recorded as `attempt_blocked`, no forecast folder) |
| Eligibility failure blocks issuance even on the issue date | `test_eligibility_failure_blocks_even_on_issue_date` | PASS (missing inputs logged) |
| An existing forecast id cannot be overwritten / re-issued | `test_issue_hash_reproducible_and_immutable` | PASS (`FileExistsError` on a second issue) |
| Silent modification is detected | Same (an edited band fails `verify`) | PASS |
| Reproducible hash | Same: shuffled identical inputs reproduce the content hash; a different configuration hash does not | PASS |
| Snapshot carries protocol / amendment hashes, all six indicators, all five provinces | Same | PASS |
| Missing values never 0; exclusion reasons recorded; values available before the issue; Amendment 1 base; provincial separation | `test_trace_excludes_missing_and_never_zero` | PASS |
| A correction is a separate record; the original stays accessible and verified | `test_correction_kept_beside_original` | PASS |
| Later source revisions do not alter the forecast and are classified as revisions | `test_revision_vs_new_information` | PASS (original unchanged; the revised period is labelled "data revision (same period, new value)") |
| Frozen configuration equals the module | `test_frozen_configuration_matches_module` | PASS |
| Real readiness outputs: nothing issued early; release-status categories valid; Amendment 1/2 effects (73 / 10 rows) | `test_real_readiness_outputs` | PASS |
| FIRI v2 regression | `test_firi_v2_untouched` | PASS |

**Two test-side corrections** made while writing the tests:
- **The revision test** first changed a period the forecast does not use: values published on the issue day are not before it.
- **The tamper test** first replaced a string that does not occur in the snapshot.

Both now test what they claim. The store code was not changed for them.
