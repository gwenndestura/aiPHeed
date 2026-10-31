# E124 automated test report

**Full backend suite.** Run after the local commit, from `backend/`, with `python -m pytest tests -q -rs`:

| Result | Count |
|---|---|
| Passed | **1149** |
| Failed | **0** |
| Skipped | **18** |

**The 18 skips are long-standing**, marked "E34 superseded by the E31 promotion": `test_api_dashboard.py` 8, `test_api_report.py` 4, `test_plain_report.py` 3, `test_report_data.py` 3. None is an E124 test.

**Baseline before E124:** 1140 passed, 0 failed, 18 skipped (at `e78d7d4`). E124 adds 9 tests (`tests/unit/test_e124_prospective.py`), all passing.

| Requirement | Test(s) |
|---|---|
| Frozen protocol configuration | `test_frozen_configuration_matches_module` |
| Issue-date handling | `test_issue_before_issue_date_is_blocked_and_logged`, `test_real_readiness_outputs` (nothing issued early) |
| 2021+ cutoff | `test_trace_excludes_missing_and_never_zero` (snapshot trace); E122 `test_e122_cutoff.py` (33) |
| Amendment 1 comparison base | `test_trace_excludes_missing_and_never_zero`; `test_real_readiness_outputs` (73 rows); E122 / E123 tests |
| Amendment 2 annual complete-year fallback | `test_real_readiness_outputs` (10 rows); E123 `test_annual_latest_complete_year`; E122 `test_annual_latest_year_and_incomplete` |
| Publication-date eligibility | `test_trace_excludes_missing_and_never_zero` (scored values available before the issue); E123 `test_publication_date_restriction` |
| Geographic integrity | `test_trace_excludes_missing_and_never_zero`; `test_issue_hash_reproducible_and_immutable` |
| Missing data | `test_trace_excludes_missing_and_never_zero` |
| Snapshot immutability | `test_issue_hash_reproducible_and_immutable` |
| Hash reproducibility | Same (`Store.reproduce`) |
| Duplicate issuance prevention | Same (`FileExistsError`) |
| Correction record preservation | `test_correction_kept_beside_original` |
| Source-data revision handling | `test_revision_vs_new_information` |
| FIRI v2 regression | `test_firi_v2_untouched`, plus the E121–E123 regression tests |
| Prospective monitoring status | `test_real_readiness_outputs` (release-status categories, feature eligibility, comparison) |

The two test-side corrections are described in `E124_SNAPSHOT_IMMUTABILITY_TESTS.md`.
