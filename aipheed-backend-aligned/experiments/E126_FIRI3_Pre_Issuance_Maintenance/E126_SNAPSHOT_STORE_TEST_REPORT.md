# E126 snapshot store retest

**Store.** The E124 append-only store `runner/store.py` is unchanged.

**Test data.** Controlled synthetic records in pytest temporary folders. **The real store was not written to:**
- `store/forecasts/` is still empty;
- the registry still holds the single E124 `attempt_blocked` event.

| Property | Test | Result |
|---|---|---|
| Forecast IDs are unique (`FIRI3-1.2-<origin>`) | `test_store_controlled_records` (a second issue of the same id is refused); E124 `test_issue_hash_reproducible_and_immutable` | PASS |
| Early issuance refused | `test_store_controlled_records`; E124 `test_issue_before_issue_date_is_blocked_and_logged`; E125 `test_real_store_untouched_and_duplicate_issue_refused` (2026-Q4 on a copy of the real store) | PASS |
| Duplicate issuance refused | Same | PASS |
| Existing snapshot cannot be overwritten | Same (`FileExistsError`) | PASS |
| Content hash reproducible | `test_store_controlled_records` (`Store.reproduce`) | PASS |
| Tampered snapshot fails verification | `test_store_controlled_records` (an edited band fails `verify`) | PASS |
| Corrections stored separately | `test_store_controlled_records` (`corrections/C001.json`; the original still verifies) | PASS |
| Later source revisions do not modify the issued forecast | `test_store_controlled_records` (observation recorded; `original_unchanged = true`); E124 `test_revision_vs_new_information` | PASS |
| Real store state | `test_real_store_and_hashes` (no forecast; one blocked event; hashes match) | PASS |

**No new record was added to the real registry in E126.** The readiness result is recorded in `out/summary.json`, not as a new issuance attempt.
