# Missing data and corrections

## Corrections made (frozen in `FINAL_THESIS_OBJECTIVES/ADDENDUM_1_DATA_CORRECTIONS.md`, sha `a5d108e3…`, before the rerun)

| Indicator | What was wrong | Evidence | Correction | Effect on model columns (`out/feature_change.csv`) |
|---|---|---|---|---|
| E2 remittances | Held quarterly levels disagreed with BSP releases (Q1 2025 held 8.65 vs BSP 8.44 bn USD; Q2 2021 7.96 vs 7.28) and 2026-Q1/Q2 had never been collected | 22 BSP press-release figures (Q1, H1, 9M, full year, 2021–2026), each with its URL in `data/bsp_cash_remittances_cumulative.csv` | quarterly levels rebuilt by differencing the cumulative figures (`data/bsp_cash_remittances_quarterly.csv`) | 90 of 115 rows changed, 10 newly available, largest change 3.55 points |
| C2 typhoons | 300 km counts came from undocumented centroids; 2026-Q3 was fetched mid-quarter | recomputed from IBTrACS v04r01 (last fix 2026-10-22) with area-weighted centroids of `frontend/public/ph-provinces.json`; 108/115 equal, 7 differ by one storm (`out/typhoons_compare.json`) | the recomputation replaces the held counts | 5 rows changed (origins 2021-Q4, 2023-Q3, 2024-Q4, 2025-Q4), by 1 |
| A3 rice | 2026-Q3 held July–August only | fresh PSA pull has all three months | complete 3-month means | 75 rows changed by at most 0.024 points (a recomputed quarterly mean); evaluation rows unaffected |
| H1 / target | backend SWS series included the commissioned 2025-Q1 round and dropped regular 2025-Q2/Q3 rounds | SWS release pages (verified earlier, `FINAL_THESIS_OBJECTIVES/sources/`) | verified non-commissioned series (fixed before the first scoring, in the frozen protocol) | the hunger condition and labels use the verified series |
| Implementation | E107 `feature_table` caches on the identity of the CPI data object only, so corrected inputs could silently be ignored | rerun produced identical features until the object was replaced | corrected inputs get a distinct object (`dataclasses.replace(d)`) | ensures the corrections above reach the model |

## Missing values that remain, and how they are handled

| Indicator | Gap | Handling |
|---|---|---|
| A3, C3, C4, E1, E2 | no value before origin 2022-Q2 (YoY needs a 2021 base and the window starts in 2021) | left NaN; LightGBM routes missing values natively; never zero-filled |
| A3 | Laguna, Quezon, Batangas quarters with fewer than 3 published months (e.g. Quezon 2024-Q1/Q2: 0 months) | quarterly mean over the months that exist; NaN when none |
| E1 | 4 months not surveyed by LFS | quarter mean over surveyed months |
| N1 (FSSI-v3) | sufficient (≥ 5 admitted headlines) in 20 of 115 province-quarters (17%) | NaN, never zero; a regional version (N1R) was tested under Addendum 2 |
| H1 | 3 quarters without a regular SWS round (2021-Q1, 2022-Q1, and 2025-Q1, which has only the commissioned round); these quarters get no label | π_H uses the newest round published before O(t); its σ grows with the true horizon |
| V1 | Lucena City has no own SAE estimate | Quezon province value substituted; disclosed in the LGU layer |
| C1 | no PAGASA El Niño item before 2023-03-24 | 0 (no alert in force), which is what PAGASA's record shows for 2021–22 (La Niña / neutral) |

## Data searched for but not available without a request to an agency

- CBMS 2024 LGU food-insecurity items: not published openly.
- FNRI provincial FIES for years other than 2021 and 2023: not published.
- Provincial SWS hunger: SWS publishes four areas only.

No values were imputed from other provinces or years, no labels were created for quarters without an SWS round, and
no observation was duplicated.
