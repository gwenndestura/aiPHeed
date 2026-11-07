# E173 results: E168 plus official regional unemployment

- **Protocol:** `docs/e173/PROTOCOL.md` (blob 1c4007cf, commit e27c82ba), locked before this run.
- **Code:** `backend/app/e173/model.py`.
- **Outputs:** `backend/data/e173/out/rows.csv` and `results.json`.
- **Runs:** nine nested runs (ENNS 2018, 2019, 2021 × Leads 1–3), each run once.

**Data now used:**
- **Validation rows:** `unemp_region` is filled in every one (100 %). In E168 it was empty everywhere.
- **Training rows:** filled in 59–62 %. Origins before 2015-Q2 have no published regional rate, because the table starts in 2014.

## Results (the same 72 forecasts per lead)

| Lead | E173 accuracy | E168 accuracy | Persistence | E173 Brier | E168 Brier | E173 − E168 (95 % CI) | Beats persistence |
|---|---|---|---|---|---|---|---|
| 1 | 73.6 % | 75.0 % | 62.5 % | 0.1225 | 0.1230 | −0.0005 [−0.0062, +0.0056] | yes |
| 2 | 76.4 % | 77.8 % | 62.5 % | 0.1238 | 0.1221 | +0.0017 [−0.0056, +0.0090] | yes |
| 3 | 73.6 % | 75.0 % | 62.5 % | 0.1312 | 0.1352 | −0.0040 [−0.0115, +0.0031] | yes |

**Configuration choice.** Training-only selection chose a different configuration once regional unemployment was available. At the 2018 and 2019 origins it picked the government set with regional consumption; at 2021 it picked the government set.

## Decision (rule fixed in the protocol)

| Check | Result |
|---|---|
| 1. Better than E168 at Lead 1 (CI below 0) | **No.** The CI includes 0. |
| 2. Project rule at Leads 1–3 | **No.** Lead 1 and Lead 3 are at 73.6 %. |
| 3. No unpublished year used | **Yes** |

**E168 stays.** Official regional unemployment, filled into the column designed for it, adds **no measurable information** to the provincial forecast.

**What this means for the employment trigger.** The trigger was untestable in E168, because its inputs were all national. It has now been tested with the best official public data available, and it does not improve the forecast. This is reported as a finding, not as a data defect.
