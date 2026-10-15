# E39 deviations (written after the single evaluation run; no scored result is affected)

## D-1. Lead-2 forecast for 2027-Q1 was not issued by the evaluation run

- The evaluation walk-forward computed its last origin as (last observed quarter + 1) - k. For lead 2 that is O(2026-Q2) = 2026-07-01 (target 2026-Q4), so the dashboard's next-quarter target 2027-Q1, from the latest origin 2026-10-01, was never issued.
- Effect on scores: none. 2027-Q1 has no outcome and would have been "No outcome yet".
- Correction: the evaluation was NOT rerun. `runner/e39_issue_forecasts.py` reruns the same deterministic walk-forward up to O(2026-Q3). It asserts that every prediction of the evaluation run is reproduced exactly (tolerance 1e-12), and extracts only the forecast-only rows into `frozen/E39_FORECASTS_2026Q4_2027Q1.json`.
