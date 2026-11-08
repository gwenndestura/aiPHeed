# E127 regression test report

**New file.** `backend/tests/unit/test_e127_amendment3.py`: 11 tests, all passing.

## PAR event counts

| Requirement | Test |
|---|---|
| 2023-Q1, 2024-Q1, 2025-Q1 explicit zeros | `test_three_explicit_zeros` (real data) |
| A quarter with actual storms | `test_explicit_zero_and_storm_quarters` |
| A quarter with incomplete source coverage | `test_incomplete_and_missing_coverage_not_filled` (file ending inside a quarter → `not_covered`) |
| A quarter with missing source data | Same (quarter before the file starts → `not_covered`; not passed to FIRI3; never 0); real 2026-Q4 is `not_covered` |
| Duplicate storm identifiers | `test_duplicate_and_split_identifiers` (a repeated row counts once) |
| Multiple identifiers for one storm | Same (two SIDs sharing ATCF WP172026 → one storm; an early fix without an ATCF id joins its SID's storm) |
| Boundary inclusion and exclusion | `test_boundary_and_quarter_assignment` (5°N 115°E corner inside; 25.5°N and 114.9°E outside) |
| Quarter assignment | Same (a storm first inside on 1 July is counted in Q3, not Q2) |

## FIRI3 scoring

| Requirement | Test |
|---|---|
| Corrected historical scores; 9 regional origins; max \|Δ\| 0.041987; 2025-Q2 band change; no provincial change; no unintended changes | `test_history_rebuilt` |
| Corrected 2026-Q4 percentile (0.7105 → 0.7500, same count, +3 zero references) | `test_2026q4_percentile` |
| No future-data leakage | `test_no_leakage_and_amendments`; `test_2026q4_percentile` (0 future reference values) |

## Existing protections (all pass)

| Protection | Tests |
|---|---|
| Amendment 1, CPI cutoff | `test_no_leakage_and_amendments` (40 rows); E122 tests (33) |
| Amendment 2, annual fallback | `test_no_leakage_and_amendments` (2024 used, 2025 skipped); E123 / E126 tests |
| Duplicate-index handling in `firi3._dynamic` | E126 `test_latest_row_with_repeated_index_labels` |
| Missing vs zero; minimum indicator availability | `test_incomplete_and_missing_coverage_not_filled`; E121 / E123 completeness tests |
| Snapshot immutability | E124 (9), E125, E126 store tests; `test_store_registry_unchanged` |
| Protocol and configuration hash consistency | `test_version_hashes_and_configuration` |
| FIRI v2 regression | `test_firi_v2_untouched`, plus earlier regression tests |

## Earlier tests updated (states superseded by an approved version change)

| Test | Was | Now |
|---|---|---|
| `test_e123_firi3.py::test_amendment_2_hash` | `VERSION.endswith("1.2")` | version ≥ 1.2 |
| `test_e124_prospective.py::test_frozen_configuration_matches_module` | compared the E124 file with the current module version | checks the E124 file is still the intact **v1.2 record**; the active v1.3 configuration is checked by `test_version_hashes_and_configuration` |
| `test_e126_maintenance.py::test_amendment_3_not_applied` | asserted v1.2 and no Amendment 3 | renamed `test_amendment_3_proposal_record_kept`: the E126 proposal file (hash) and outputs are unchanged, and match the v1.3 results |

**Test-side correction.** The first version of `test_three_explicit_zeros` required every covered quarter to equal E114. 2026-Q3 differs (E114: 8; builder: 7) because of the known SAUDEL double count, which E119 never used. The test now asserts exactly that one documented difference.
