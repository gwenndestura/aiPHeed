# E134 data acquisition log

**Rules followed:**
- 2021+ only: every query is restricted to Year ≥ 2021 or start = 2021-01-01, and every loader asserts it.
- Raw files are saved unchanged, with the query, URL, sha256 and fetch time recorded in `data/acquisition_log.json`.
- No SWS, PSA or BSP "latest" web searches; no values for any sealed target quarter. SWS has not published 2026-Q4.

## Acquired (`runner/e134_acquire.py`, 2026-11-01)

| File(s) | Source / URL | Content | Use in E134 |
|---|---|---|---|
| `nasa_power_daily_<region>.json` (18) | NASA POWER daily point API, community AG, `PRECTOTCORR,T2M`, 2021-01-01 … 2026-09-30 | Daily precipitation and temperature at one regional centre per region of the 4 SWS areas | Area rainfall-deficit driver aR |
| `nasa_power_daily_<province>.json` (5) | Same API, E118 province centroids | Cavite, Laguna, Batangas, Rizal, Quezon | Provincial climate context (§ provincial report) |
| `psa_palay_corn_production_quarter_2021_2026.csv` + query | OpenSTAT `DB/2E/CS/0012E4EVCP0.px` | Palay and corn production by quarter, region and province, 2021-Q1 … 2026-Q3 | Area palay-drop driver aP (2022+ YoY) |
| `psa_fies2023_t8_income_expenditure_savings.csv` + query | OpenSTAT `DB/1E/IE/0081E3AIES0.px` | FIES 2023: average income, expenditure and savings by province and decile (constant 2021 prices) | Provincial household stress (savings of the poorest decile) |
| `psa_fies2023_t7_expenditure_by_group.csv` + query | OpenSTAT `DB/1E/IE/0071E3ATME0.px` | FIES 2023: expenditure shares by major group (food) by decile and province | Provincial food-expenditure share |

**Notes:**
- PSA FIES tables are Latin-1 encoded.
- Quezon is published as "QUEZON (Excluding City of Lucena)".
- Negros Island Region has no palay values for its early quarters, so YoY is computed on the regions present in both quarters.

## Already held and re-used

E131 regional CPI; E133 bottom-30 % CPI; E119 point-in-time regional dataset (ONI, typhoons, unemployment, remittances, GDELT); FSSI v2 panel; POPCEN 2024 CALABARZON; E131 poverty; FIES 2023 PUF route (E131).

## Investigated, not acquired (reason)

| Source | Reason |
|---|---|
| PAGASA station rainfall | Formal data request required |
| NDRRMC situation reports | Event PDFs with no machine-readable panel. Manual coding would be needed, and dating them to the forecast issue date is unreliable. |
| DA crop-damage reports | Event reports, not a panel |
| DSWD 4Ps / Listahanan | Registry not public |
| CBMS 2024 FIES | LGU/PSA request (unsent; owner decision E87/E131) |
| FIES 2021 PUF | PSA archive registration |
| SWS provincial microdata | Request needed; too few respondents |
| PSA Survey on Overseas Filipinos | Annual and regional; would be a slow vulnerability input, not a quarterly driver; not acquired in E134 |
| LFS regional quarterly tables | Not on OpenSTAT (national only, E131/E132). Published in releases; would need manual extraction with release dates. |
| **Pre-2021 SWS and covariates** | Already held on branch `aiPHeed/e114-genuine-forecast` (`sws_rounds_1998_2026.csv`, `cov_*.csv`). **Not loaded:** owner rule 2021+ (E134 §6 feasibility). |
