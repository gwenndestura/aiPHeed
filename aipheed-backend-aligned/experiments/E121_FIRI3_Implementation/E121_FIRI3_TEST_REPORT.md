# E121 FIRI3 test report

**Full backend suite.** Run after the local commit, from `backend/` (`python -m pytest tests -q`). Result:

```
1096 passed, 18 skipped
```

| Test file | Tests | Covers |
|---|---|---|
| `tests/unit/test_firi3.py` | 23 | See the table below |
| `tests/integration/test_e121_firi3.py` | 5 | Protocol hash; deterministic and equal to E120; all leakage checks; result geography, missing handling, completeness and bands on the real outputs; snapshot files match their manifests (23) |
| `tests/integration/test_e120_firi_design.py`, `test_e119r2_framework.py` | 2 + 2 | Unchanged; they also check that `backend/app` has no uncommitted change, so they pass once `firi3.py` is committed |

**Requirement → unit test(s) in `test_firi3.py`:**

| Requirement | Test(s) |
|---|---|
| Individual feature calculation | `test_percentile_direction_and_history`, `test_abs_transform_for_rainfall_departure` |
| Directionality | `test_percentile_direction_and_history` (production drop = highest risk) |
| Normalization | Same; `test_annual_rank_latest_published_year_no_expansion` |
| Minimum history and staleness | `test_insufficient_history_and_stale_are_not_scored` |
| Component aggregation (counts once) | `test_component_counts_once_and_indicator_mean` |
| Indicator aggregation and half-of-components rule | `test_indicator_needs_half_of_components` |
| Overall FIRI3, equal weights, completeness | `test_overall_equal_weights_completeness_and_band`, `test_regional_needs_four_of_five_and_has_no_psv` |
| Missing-data handling | `test_missing_never_zero`, `test_insufficient_history_and_stale_are_not_scored` |
| Provincial / regional separation | `test_geographic_separation_of_specs`, `test_regional_needs_four_of_five_and_has_no_psv` |
| Annual data | `test_annual_rank_latest_published_year_no_expansion`, `test_annual_incomplete_year_not_scored` |
| Point-in-time availability | `test_point_in_time_availability` |
| Pre-2021 exclusion | `test_pre2021_rows_rejected` |
| Target leakage prevention | `test_target_and_index_series_refused` (4 cases), `test_no_feature_uses_target_or_index` |
| Determinism | `test_deterministic` (shuffled inputs give identical output) |
| Risk classification | `test_bands` |
| FIRI v2 isolation | `test_firi3_independent_of_firi_v2` |
| FIRI v2 regression | `test_firi_v2_regression_unchanged`: `score_v2` on a fixed input = 0.3929012345679012 (LOW), recorded before E121. `test_firi_v2_files_unchanged`: SHA-256 of `firi.py`, `firi2_history.csv` and `firi2_reference.json` |
| Prospective snapshot integrity | `test_snapshots_immutable_and_intact` (integration), plus the runner's refuse-on-change check |

**Corrections made while writing the tests.** Two test expectations were wrong; the module was not:
- **PIT test.** A value published on the issue day itself is *not* before the issue, so the expected period was one quarter earlier.
- **Regional completeness test.** AFP with 2 of 4 components is available (⌈4/2⌉ = 2).

Both tests were corrected to match the frozen protocol.
