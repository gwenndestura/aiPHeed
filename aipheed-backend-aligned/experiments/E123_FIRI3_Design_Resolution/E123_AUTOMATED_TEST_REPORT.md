# E123 automated test report

**Before E123 changes:** the full suite reproduced **1129 passed, 18 skipped**.

**After E123** (FIRI3 v1.2, local commit), from `backend/`, `python -m pytest tests -q`:

```
1140 passed, 18 skipped
```

**New file.** `tests/unit/test_e123_firi3.py`: 11 tests, all passing.

| Requirement | Test |
|---|---|
| Current Conditions Score | `test_current_conditions_score` (mean of available members; ≥ 3 of 4; band; missing members named; not computable with 2) |
| Structural Vulnerability Score | `test_structural_vulnerability_score` (both members required; position label, no band; regional `not_defined`) |
| Common core | `test_common_core_and_missing_indicators` (fixed core needs all four; cross-province core uses only indicators common to all five; `comparison_not_possible` below 3) |
| Missing indicators | Same (never filled; FIRI3 not computable) |
| Annual complete-year handling | `test_annual_latest_complete_year` (newer incomplete year skipped and named; unpublished year unavailable) |
| Publication-date restrictions | `test_publication_date_restriction` |
| FSSI article date restrictions | `test_fssi_article_dates` (real article stores: window 2021-01-01..2026-10-14; every as-of article in its quarter and published before the issue; no duplicate keys) |
| GDELT date restrictions | `test_real_outputs` (recomputed from raw daily data, from 2021-Q1, available after the quarter end) |
| Batangas source consistency | `test_real_outputs` (every value entering EHS equals the owner file, except 2024 unemployment = 100 − employment rate) |
| Indicator contributions | `test_real_outputs` (dominance table covers all six indicators) |
| Weighting sensitivity | `test_real_outputs` (variants present) |
| Missingness sensitivity | `test_real_outputs` (with exactly the core, FIRI3 equals the core) |
| Classification stability | `test_real_outputs` |
| Immutable prospective snapshots | `test_prospective_snapshot_immutable`: refuses before the issue date; refuses overwrite; a later observation is saved beside the snapshot without changing it; tampering is detected and blocks later recording |
| Protocol hash | `test_amendment_2_hash`; existing `test_amendment_hash` (E122) and the E121 protocol tests |
| FIRI v2 regression | `test_firi_v2_regression`, plus the existing E121 and E122 regression tests |
| Amendment 1 CPI base | `test_amendment1_cpi_base`; existing E122 tests |

**Changed existing test.** `tests/unit/test_e122_cutoff.py::test_annual_latest_year_and_incomplete` asserted the pre-Amendment-2 rule (incomplete latest year → unavailable). It now asserts the approved rule:
- the latest complete year is used and the skipped year is named;
- with no complete year, the feature is unavailable.

**One test expectation corrected** (pandas stores a missing core as NaN, not None). The module was not changed for it.
