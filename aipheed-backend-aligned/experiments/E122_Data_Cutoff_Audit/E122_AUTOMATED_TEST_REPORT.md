# E122 automated test report

**Full backend suite.** Run after the local commit, from `backend/`, with `python -m pytest tests -q`:

```
1129 passed, 18 skipped
```

**New file.** `tests/unit/test_e122_cutoff.py`: 33 tests, all passing.

| # | Requirement | Test(s) |
|---|---|---|
| 1 | Pre-2021 raw observations excluded | `test_pre2021_raw_rows_excluded` |
| 2 | Pre-2021 lags excluded | `test_2021_change_rows_rejected[*]`: 21 change-type series, each a lag or comparison at t−4 |
| 3 | Pre-2021 rolling windows excluded | Same (anomalies compare against earlier same-quarter years; 3-month windows start at 2021-01); real-data re-derivation in `test_real_data_audit_outputs` |
| 4 | Pre-2021 YoY comparison excluded | `test_2021_change_rows_rejected[cpi_food_yoy_pct]` and the other YoY series; `test_level_series_keep_2021` (level series keep 2021) |
| 5 | Pre-2021 normalization references excluded | `test_2021_yoy_rejected_before_normalization` |
| 6 | At least 8 earlier observations for a percentile | `test_min_eight_history` |
| 7 | Historical issue-date availability | `test_issue_date_availability_and_future_rows` |
| 8 | Publication-date restrictions | Same (a later-published row of the same period is not used) |
| 9 | Future observations excluded | Same; `test_percentile_reference_excludes_current_and_unpublished` |
| 10 | Annual latest-year handling | `test_annual_latest_year_and_incomplete` (latest *published* year; an incomplete latest year is not used; a year, never a quarter) |
| 11 | Provincial separation | `test_provincial_and_regional_separation` |
| 12 | Regional separation | Same |
| 13 | National values not replicated into provinces | `test_national_not_replicated_into_provinces` |
| 14 | Final score traceability | `test_real_data_audit_outputs`: every computed score reproduces from its features; all inputs from 2021 on and available before the issue; 34 of 34 features PASS; re-derivation agrees; snapshot hashes match |
| 15 | Deterministic calculations | `test_deterministic_under_row_order` |
| 16 | FIRI v2 regression protection | `test_firi_v2_untouched`, plus the E121 tests `test_firi_v2_regression_unchanged` and `test_firi_v2_files_unchanged` |

**The test runs also found a defect.** An unknown provincial unit could be dropped by the date rules before the geography check ran (C2 in the corrections report). It is fixed, and `tests/unit/test_firi3.py::test_geographic_separation_of_specs` covers it.

**Two expectations in the new tests were corrected:**
- **`test_min_eight_history`.** A value published on the issue day is not *before* the issue, so the test used the wrong origin.
- **`test_2021_yoy_rejected_before_normalization`.** The expected reference count was restated as exactly 40.

The module was not changed for either.
