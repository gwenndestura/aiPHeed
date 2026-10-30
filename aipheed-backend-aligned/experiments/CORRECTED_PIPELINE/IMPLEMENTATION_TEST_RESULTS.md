# Implementation test results

| | |
|---|---|
| Branch | `aiPHeed/corrected-data-pipeline` (from a0f469b; local only, not pushed) |
| Commit | the commit that adds this file; see `git log -1 -- aipheed-backend-aligned/experiments/CORRECTED_PIPELINE` |

## Commands

```bash
cd aipheed-backend-aligned/experiments/CORRECTED_PIPELINE/runner
python pipeline.py && python reports.py
cd ../../../../backend
python -m pytest -q tests/integration/test_corrected_pipeline.py tests/integration/test_data_audit.py
python -m pytest -q -p no:cacheprovider
```

## Results (run 2026-10-31)

| Suite | Result |
|---|---|
| `tests/integration/test_corrected_pipeline.py` | **9 passed** |
| `tests/integration/test_data_audit.py` | **7 passed** (audit sources unchanged) |
| Full backend suite | **1044 passed, 18 skipped, 0 failed** (148 s) |

## What `test_corrected_pipeline.py` covers

| Required check | Test |
|---|---|
| All 12 indicator mappings | `test_indicator_and_domain_mappings`: registry = `firi.LABELS`; FIRI domain = `firi.DOMAIN_OF` |
| Five-domain mappings | same test: market {A1, A2, A3}, fish {C4}, climate {C1, C2, C3}, employment {E1}, OFW {E2} |
| Historical publication-date validity | `test_asof_thresholds_point_in_time_and_frozen_equivalence`, `test_publication_flags` |
| CPI vintage consistency | `test_publication_flags`: every row issued before 2022-06-07 is flagged |
| Geographic consistency / provincial duplication | `test_geography_no_copied_national_or_regional_values`: no national or regional column in the provincial profile; one context row per origin |
| Missing-value preservation | `test_missing_values_preserved_with_status`: every missing value carries a non-zero status; none is zero-filled |
| Feature construction | as-of thresholds equal the frozen thresholds exactly when the window is 2021-Q1 to 2022-Q4 |
| Lead-1 and Lead-2 alignment | `test_lead_alignment_regional_panel`: target = origin + lead; issue = day 1 of quarter t+1; latest reading ≤ origin |
| Training/inference consistency | `test_training_inference_consistency_latest_origin` |
| Data leakage | as-of thresholds use only quarters published before the issue; annual employment only from earlier years; too-early thresholds are missing, not zero |
| Regression against the original pipeline | `test_regression_against_original_pipeline`: every uncorrected value equals the served stack (to 1e-5); corrected E2 equals the stack E2; the regional panel equals E116 |
| Raw inputs unchanged | `test_raw_inputs_unchanged`: SHA-256 of all 13 inputs |

## Fixes during the work (disclosed)

| Problem found | How it was fixed |
|---|---|
| As-of thresholds first used only quarters that had an SWS round (they were taken from the label file) | switched to the PSA CPI YoY table. The frozen equivalence test now passes exactly. |
| The corrected remittance value had the opposite sign to E2 | fixed; equal to the stack |
| A1/A2 coverage counted the threshold status only | a combined status now also uses the CPI release evidence |
| Regional CPI counted back-cast rows as verified | fixed: 280 verified, 592 flagged back-cast |
| Outputs written at 6 significant digits | now 10, so regression can be checked to 1e-5 |

## Issues resolved vs unresolved

- **Resolved** (by design or flag): audit items 4, 6, 9 (resolution and refresh), 10, 11, 12, 13 and 16.
- **Flagged, not fixable with existing data:** items 1, 2, 3, 5, 7, 8, 14 and 15. See `REMAINING_DATA_GAPS.md`.
- **No predictive claim is made.**
