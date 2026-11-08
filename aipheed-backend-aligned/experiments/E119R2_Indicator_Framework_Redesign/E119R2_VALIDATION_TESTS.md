# E119-R2 validation tests

**How it runs.** `runner/validate.py`, after `runner/analyze.py`. Results are in `out/validation_results.csv`. The run stops if any check fails. The same checks run in `backend/tests/integration/test_e119r2_framework.py`.

**Result: 21 of 21 PASS.**

| # | Check | Detail | Result |
|---|---|---|---|
| 1 | Every FIRI v2 indicator reviewed, with labels equal to `firi.LABELS` | 12 of 12 | PASS |
| 2 | Every FIRI v2 indicator assigned to a proposed indicator | — | PASS |
| 3 | Every E118 inventory dataset mapped | 38 of 38 E118 rows | PASS |
| 4 | Every E118 acquired clean table mapped | 20 of 20 tables | PASS |
| 5 | Every E119 feature mapped to a dataset | 70 of 70 (feature dictionary, annual table, both datasets) | PASS |
| 6 | All mapped dataset ids exist | — | PASS |
| 7 | Every dataset has an indicator, a role and a reason | 54 datasets | PASS |
| 8 | Every proposed indicator has at least one acquired dataset | 7 of 7 | PASS |
| 9 | All four FAO dimensions represented | Utilization only indirectly (disclosed) | PASS |
| 10 | Provincial units are exactly the five provinces | Batangas, Cavite, Laguna, Quezon, Rizal | PASS |
| 11 | Quezon City and Lucena never appear as province units | — | PASS |
| 12 | National and regional values carry their own unit, never a province name | Region IV-A, CALABARZON proxy, PHILIPPINES, GLOBAL | PASS |
| 13 | No national/regional value copied to provinces; no annual value spread to quarters | Flag column in the coverage CSV, backed by check 12 and by annual data kept in its own table | PASS |
| 14 | Regional forecasting predictors all have a regional or national series | D03 D07 D20 D21 D22 D24 D31 D34 D35 D40 D62 D70 | PASS |
| 15 | No supervised provincial food-insecurity label claimed | — | PASS |
| 16 | No pre-2021 observation in any analysed series | Minimum 2021-Q1 | PASS |
| 17 | Computed changes start 2022-Q1 or later (2021+ base only) | Minimum 2022-Q1. PSA-published 2021 CPI YoY is the declared exception. | PASS |
| 18 | Every value becomes available after its period starts | — | PASS |
| 19 | Production code, dashboard, E118 and E119 files unchanged | `git status` of backend/app, frontend/src, backend/data, E118, E119 is empty | PASS |
| 20 | Inputs read only | 38 files, SHA-256 equal before and after | PASS |
| 21 | No model fitted in this phase | No fitting code in the runner | PASS |

## Finding for E119 (not fixed here, because E119 files must not change)

In E119's per-indicator outputs (`E119_Preprocessing/out/indicators/*/observations_clean.csv`), the 392 **Region IV-A** rows carry `resolution = province`. E119 sets resolution once per feature, not per unit.

- **The unit is correct.** These rows are never copied to provinces, and the E119 regional and provincial datasets are unaffected.
- **Only the label is wrong.** E119-R2 derives resolution from the unit, which is what check 10 tests.

The rebuild proposed in the final recommendation should fix the label.

## What these checks do not prove

- **Release dates are still mostly rules.** That a value is available before its issue date is only as reliable as the rule.
- **Correlations describe 2021–26 only.** They are short series dominated by one post-COVID cycle, and do not establish causation.
