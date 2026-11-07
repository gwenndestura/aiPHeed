# Test coverage report

## Executed (safe, read-only; 2026-11-07)
`tests/integration/test_api_thesis.py`, `test_api_dashboard.py`, `test_report_data_thesis.py`; `tests/unit/test_e166.py`,
`test_e171.py` - `test_e174.py`: **69 passed, 8 skipped, 0 failed**; Git status unchanged afterwards.
Audit checks: `recalculate.py` (E168 metrics, all 8 leads, independent of `leads.py`, all match); E168 lock re-hash (0 changes);
in-process API checks (indicator, map join 142/142, driver shares, timeseries, alerts, thresholds, Render-env model).

## Not executed, and why
- **Full suite:** it rewrites a tracked file (`aipheed-backend-aligned/experiments/E107_.../__pycache__/e107_lib.cpython-313.pyc`), a
  protected-artifact change. Last full results (same code, 2026-11-07): 1612 passed, 32 failed, 22 skipped, 1 collection error. 27 are
  legacy lock/data failures; 2 are by design ("production unchanged" checks fail while the 4 service files are uncommitted).
- **E168 / E169-E179 evaluation scripts:** they refit models (forbidden here).
- **Scheduler / quarterly-cycle tests that write staged forecasts or alerts:** they could mutate the database.

## Coverage by area
| Area | Covered by tests | Notes |
|---|---|---|
| C1-C6 calculation | yes (`test_e166`, thesis route) plus independent recalculation | verified |
| Thesis routes and E168 serving (indicator, 142 LGUs, all quarters, sealed = live) | yes | verified |
| Driver aggregation method | no test of the required |SHAP| formula | gap (F02) |
| Map join | no automated test | verified by audit script |
| Frontend labels | `foodInsecurityStatus.test.tsx` only | no test catches the "Price-pressure risk" label |
| Leakage | E168 corruption control; `test_e171` SWS published-before | verified |
| Deployment env | none | gap (F01) |
