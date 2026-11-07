# E180: test results

## Run during this audit (safe subset, 2026-11-07)
`tests/integration/test_api_thesis.py`, `test_api_dashboard.py`, `test_report_data_thesis.py`, `tests/unit/test_e166.py`,
`test_e171.py`-`test_e174.py`: **69 passed, 8 skipped, 0 failed** (172 s). Git status unchanged afterwards.

## Audit-specific checks (scripts in this folder)
- `recompute.py`: independent recomputation (scikit-learn plus a written-out C1 formula) reproduces E168 and SIMPLE Leads 1-3 exactly
  (`STATISTICAL_VALIDATION.csv`).
- In-process API checks: driver-share method (I04), map join 142/142, thresholds, and the Render-env model (I01).

## Full suite: not re-run in this audit
Reason: it rewrites a tracked file (`aipheed-backend-aligned/experiments/E107_.../__pycache__/e107_lib.cpython-313.pyc`), which the audit
must not modify. Results from the full runs earlier today (same code): **1612 passed, 32 failed, 22 skipped, 1 collection error**.
- 27 failures pre-date today's changes: lock-hash mismatches (E125, E128-E131, E137, E138, E140-E144, HFIAS); `test_e139.py` collection
  error (missing data file); `test_corrected_pipeline::test_raw_inputs_unchanged`; v2_defects; system_completion. These protect old
  experiments whose inputs changed; they do not test the served E168 path.
- 2 failures (E119-R2, E120 "production code unchanged") are caused by the four uncommitted service-file changes by design.
- 3 failures (dashboard news-count agreement, legacy report data) were fixed on 2026-11-07 and pass in the subset above.
