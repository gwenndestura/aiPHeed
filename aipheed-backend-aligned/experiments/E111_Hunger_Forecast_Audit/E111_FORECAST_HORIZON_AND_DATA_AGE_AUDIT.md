# E111 Forecast horizon and data-age audit

**Full table:** `out/horizon_table.csv`, one row per issue date (`runner/horizon_table.py`). It gives:
- the issue date;
- the newest SWS quarter known on that date, its fieldwork and its publication date;
- the age of that observation;
- the target and **true horizon** of Leads 1–4;
- the cutoff of every predictor.

## Definitions (reported separately throughout E111)

| Term | Meaning |
|---|---|
| Issue date O(*t*) | day 1 of quarter *t* + 1 |
| **Lead *k*** | target quarter = *t* + *k*. Lead 1 is the quarter that starts on the issue date. |
| **Observation age** | issue quarter − fieldwork quarter of the newest SWS round published before the issue date |
| **True horizon** | target quarter − fieldwork quarter of the newest SWS round known at the issue date |

## Result

| | Value |
|---|---|
| Issue dates with any SWS round known | 21 (from 2021-10-01) |
| Observation age 2 quarters | **19 of 21** issue dates |
| Observation age 1 quarter | 2 (2022-07-01 and 2025-07-01: an April round of the same quarter had been published by then) |
| True horizon of Lead 1 | **2 quarters** at 19 issue dates, 1 quarter at 2 |
| True horizon of Lead *k* | usually *k* + 1 |
| Median days from the newest SWS publication to the issue date | 57 |

**Example:** issue date 2026-10-01.

| Item | Value |
|---|---|
| Newest SWS reading | 2026-Q2 (June 20–29, 2026), published 2026-08-24 |
| Target, Lead 1 | 2026-Q4: true horizon 2 quarters |
| Target, Lead 2 | 2027-Q1: true horizon 3 |
| Not yet available | The September 2026 round (2026-Q3) was published 2026-10-14, after the issue date |

## Predictor cutoffs at an issue date (E107 rules, unchanged and tested in E107/E108)

| Source | Latest value used | Publication assumption |
|---|---|---|
| PSA CPI (food, all items) | month 2 of quarter *t* | about 1 month lag (conservative) |
| PSA LFS (unemployment) | months of quarter *t* − 1 | about 1–2 months |
| PSA production, rice prices; BSP remittances | quarter *t* − 1 (remittances end 2025-Q4) | about 1–2 months |
| IBTrACS typhoons | quarter *t* | near real time |
| NOAA ONI (ENSO) | quarter *t* − 1 | 1 month |
| PAGASA El Niño items | items dated before the issue | dated releases |
| News headlines (FSSI-v3) | headlines of quarter *t* published before the issue | timestamped |
| SWS hunger | rounds published before the issue (verified dates) | 10 days – 3.5 months after fieldwork |

## Consequences for the thesis

- A "one-quarter-ahead" hunger forecast in aiPHeed is **a forecast two quarters beyond the newest observed hunger**. It is not a nowcast and not a validated one-quarter forecast.
- The latest-reading baseline is therefore a two-quarter persistence projection. Its error (Balance Luzon about 3.3–3.7 points at Lead 1) is a two-quarter-change error.
- Results in E111 are reported by **lead** and by **true horizon** (`results.json` → `by_true_horizon`).
