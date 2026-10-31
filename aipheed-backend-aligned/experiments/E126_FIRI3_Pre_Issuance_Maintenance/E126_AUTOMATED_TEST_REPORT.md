# E126 automated test report

**Full backend suite.** Run from `backend/` with `python -m pytest tests -q`, after the E126 work commit:

| Result | Count |
|---|---|
| Passed | **1172** |
| Failed | **0** |
| Skipped | **18** (long-standing "E34 superseded" tests) |

**Baseline at E125:** 1159 passed, 0 failed, 18 skipped. E126 adds 13 tests in `tests/unit/test_e126_maintenance.py`, all passing. All earlier FIRI3 tests (E121–E125, 91 tests) still pass after the C-E126-1 code fix.

| Requirement | Test |
|---|---|
| PAR zero-storm verification | `test_par_zero_quarters_verified` |
| Storm identifier de-duplication | `test_zero_versus_missing_and_dedup` (two SIDs, one ATCF id → one storm) |
| Quarter completeness | `test_par_zero_quarters_verified` (a file not covering the quarter is "source does not cover the full quarter", never a zero) |
| Zero vs missing event counts | `test_zero_versus_missing_and_dedup`, `test_amendment_3_not_applied` |
| September LFS refresh | `test_lfs_refresh_blocked_without_september`, `test_real_lfs_status` |
| Full-quarter unemployment calculation | `test_full_quarter_both_methods` (mean of rates and level-based) |
| Source publication-date validation | `test_source_status_and_readiness` (READY only for verified dates); E125 `test_cpi_release_evidence` |
| Feature eligibility | `test_source_status_and_readiness` |
| Historical score reconciliation | `test_historical_reconciliation_versions` (73 / 10 / 12 changes; proposed rows labelled) |
| Amendment 1 / Amendment 2 | `test_amendments_active` |
| Snapshot immutability, duplicate issuance | `test_store_controlled_records`, `test_real_store_and_hashes` |
| Protocol hash consistency | `test_real_store_and_hashes` |
| FIRI v2 regression | `test_firi_v2_untouched` (score and `firi.py` hash) |
| firi3 robustness (C-E126-1) | `test_latest_row_with_repeated_index_labels` |

**Corrections to the tests while writing them.** These were in the tests, not the code:
- empty CSV fields read back as NaN;
- the clean-tree check can only pass once the `firi3.py` fix is committed.
