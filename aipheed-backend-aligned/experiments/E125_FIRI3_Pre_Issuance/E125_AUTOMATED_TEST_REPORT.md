# E125 automated test report

**Full backend suite.** Run after the local commit, from `backend/`, with `python -m pytest tests -q`:

| Result | Count |
|---|---|
| Passed | **1159** |
| Failed | **0** |
| Skipped | **18** (the long-standing "E34 superseded" tests; none from E124 or E125) |

**Baseline at E124:** 1149 passed, 0 failed, 18 skipped. E125 adds 10 tests (`tests/unit/test_e125_pre_issuance.py`), all passing.

| Requirement | Test |
|---|---|
| Refreshed NASA POWER coverage | `test_nasa_power_coverage` (2026-01..09 for 5 provinces × 2 parameters; nothing interpolated; E119 method reproduced; 2026-Q3 complete) |
| Quarterly cyclone completeness | `test_cyclone_quarter_complete_and_deduplicated` (last fix ≥ 2026-09-30) |
| PAR and local geographic consistency | Same (provinces / PHILIPPINES); `test_local_counts_match_track_distances` (counts recomputed from raw tracks and centroid distances) |
| No storm counted twice | `test_cyclone_quarter_complete_and_deduplicated` (7 distinct storms; SAUDEL once) |
| September LFS inclusion / complete quarter | `test_september_lfs_and_complete_quarter` (July and August only, so BLOCKED) |
| CPI actual publication-date restrictions | `test_cpi_release_evidence` (0 scored uses with evidence on or after the issue; margin > max archived delay) |
| Amendment 1 / Amendment 2 | `test_all_34_feature_decisions` (base rule; EHS uses 2024); E122 and E123 tests |
| All 34 feature eligibility checks | `test_all_34_feature_decisions` (READY only for verified dates; nothing promoted) |
| FIRI3 score reproducibility | `test_reconciliation_explained_and_reproducible` |
| FIRI v2 regression | `test_firi_v2_untouched`, plus earlier regression tests |
| Snapshot store immutability / duplicate issuance | `test_real_store_untouched_and_duplicate_issue_refused` (on a copy; the real store stays empty with one blocked event); E124 store tests |
| Protocol hash consistency | `test_frozen_configuration_and_hashes` |

**IBTrACS file not in git.** The raw IBTrACS file (11.7 MB) follows the E114 practice: its SHA-256 is in `data/refresh_log.json`. `test_local_counts_match_track_distances` skips when the file is absent.
