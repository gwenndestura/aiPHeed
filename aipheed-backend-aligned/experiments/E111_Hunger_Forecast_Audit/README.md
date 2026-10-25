# E111: audited SWS hunger forecasting with true horizons, surge costs and indicator screening (2021+)

**Branch:** `aiPHeed/e111-hunger-forecast-audit` (from E110 `560970c`). **Status:** evaluated; not served; production unchanged.

| Deliverable | File |
|---|---|
| 1. E110 metric and implementation audit | `E111_E110_METRIC_AND_IMPLEMENTATION_AUDIT.md` (`out/audit_e110.json`, `out/audit_dm_kernel.json`) |
| 2. Forecast horizon and data age | `E111_FORECAST_HORIZON_AND_DATA_AGE_AUDIT.md` (`out/horizon_table.csv`) |
| 3. Model experiments | `E111_MODEL_EXPERIMENTS.md` |
| 4. Quarterly generalization | `E111_QUARTERLY_GENERALIZATION.md` |
| 5. Maximum reliable lead time | `E111_MAXIMUM_RELIABLE_LEAD_TIME.md` |
| 6. Thesis objectives and final answers | `E111_THESIS_OBJECTIVE_ASSESSMENT.md` |
| Protocol | `PROTOCOL.md` (sha `7086aeb1…`, frozen before scoring) + `ADDENDUM_1.md` (Newey-West correction) |
| Scripts | `runner/audit_e110.py`, `runner/horizon_table.py`, `runner/dm_kernel_audit.py`, `runner/e111_lib.py`, `runner/run_e111.py` |
| Tests | `backend/tests/unit/test_e111.py` |
| Outputs | `out/results.json` (corrected DM), `out/results_first_scoring.json`, `out/panel_lead{1..6}.csv`, `out/bl_lead{1..4}.csv` |
| Seal | `out/sealed_prospective.csv` (sha `adf27ba9…`); E107 to E110 seals preserved |
| Read-only API | `/api/v1/e111/{evaluation,forecast}` |

## Reproduce

```bash
cd aipheed-backend-aligned/experiments/E111_Hunger_Forecast_Audit/runner
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe audit_e110.py
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe horizon_table.py
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe dm_kernel_audit.py
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e111.py score
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e111.py prospective
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e111.py export
```

## Verification (2026-10-25)

- `pytest tests/unit/test_e111.py`: **14 passed**.
- Full backend suite: **723 passed, 18 skipped, 0 failed**.
- The E107 to E110 seals are unchanged (tested).
- The frontend is untouched.
- **Deployment:** the branch is pushed, not merged.
