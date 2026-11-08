# Indicator source and coverage matrix (FIRI v2, 12 families)

Audit date 2026-10-26. Machine-readable version: `out/coverage_matrix.csv` (built by `runner/audit_build.py`).
Study window 2021-Q1 to 2026-Q3 (23 quarters). "Missing" counts quarters (or months for monthly series) inside
that window with no value for at least one province. "Issue-date rule" is what may be used by a forecast issued on
O(t) = day 1 of quarter t+1.

| # | Family | Source (table / file) | Frequency | Geography | Valid obs 2021+ | First – last | Missing | Issue-date rule | Validation result | Action |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Food-price pressure (projected food YoY and food-minus-headline gap vs province P60) | PSA OpenSTAT 0012M4ACP22, CPI 2018=100, food and all items, plus PSA-published YoY | monthly | province (5) | 345 | 2021-01 – 2026-09 | 0 | month m used if m ≤ month 2 of quarter t (PSA releases about day 5 of m+1) | 690/690 index values equal a fresh PSA pull; published YoY equals recomputed YoY within 0.05 points | none needed |
| A2 | Headline inflation above the usual level | same CPI table | monthly | province (5) | 345 | 2021-01 – 2026-09 | 0 | same as A1 | same as A1 | none needed |
| A3 | Wholesale rice price change | PSA OpenSTAT 0052M4AWB01, regular-milled rice, wholesale | monthly → quarterly mean | province (5) | 112 | 2021-Q1 – 2026-Q3 | 3 | quarter t−1 at O(t) | 107/112 equal; the 5 that differ are all 2026-Q3, held when only Jul–Aug were published | 2026-Q3 replaced by the complete 3-month mean |
| V1 | Poverty and population density | PSA 2021 municipal SAE poverty, POPCEN 2024, land area (`lgu_vulnerability.csv`) | static | 142 LGUs → province | 142 LGUs | SAE 2021, POPCEN 2024 | 1 LGU (Lucena: province SAE substitute) | used at every origin (FIRI Amendment 1) | 142/142 LGUs; 141 own SAE | disclosed as static; no time variation |
| C1 | PAGASA El Niño alert or advisory in force | PAGASA ENSO Alert and Warning System items (`enso_context.PAGASA_ENSO`) | event | national | 20 items | 2023-03-24 – 2026-10-07 | 0 | items dated before O(t) | checked against the PAGASA monitoring page (strong El Niño; page updated 2026-10-21, after the last issue date) | none needed |
| C2 | Typhoons within 300 km | NOAA IBTrACS v04r01 Western Pacific best tracks | 6-hourly → quarterly count | province centroid, 300 km | 115 | 2021-Q1 – 2026-Q3 | 0 | quarter t (complete at O(t)) | 108/115 equal on recomputation; 7 differ by exactly 1 storm | replaced by the documented recomputation |
| C3 | Palay/corn production drop | PSA OpenSTAT 0012E4EVCP0 | quarterly | province (5) | 220 | 2021-Q1 – 2026-Q2 | 0 | quarter t−1 at O(t) | 220/220 equal to the fresh pull | none needed |
| C4 | Fisheries production drop | PSA OpenSTAT 0132E4GVFP1 | quarterly | province (5) | 110 | 2021-Q1 – 2026-Q2 | 0 | quarter t−1 at O(t) | 220/220 values equal to the fresh pull | none needed |
| E1 | Unemployment change | PSA OpenSTAT 0021B3FKEI2, LFS unemployment rate | monthly (some months not surveyed) | national | 68 months | 2021-01 – 2026-08 | 4 months not surveyed | months of quarter t−1 at O(t) | 68/68 equal to the fresh pull | none needed; one national value for all provinces |
| E2 | Remittance decline | BSP OFW cash remittances | quarterly | national | 22 (after rebuild) | 2021-Q1 – 2026-Q2 | 0 after rebuild (3 before) | quarter t−1 at O(t) (BSP releases about day 15 of the second month after the quarter) | **defect**: held levels disagreed with BSP releases (e.g. Q1 2025 8.65 vs BSP 8.44; Q2 2021 7.96 vs 7.28) and 2026-Q1/Q2 were missing | rebuilt from 22 cited BSP cumulative figures; 2026-Q1/Q2 added |
| N1 | Food Stress Sentiment Index and news covariates | project RSS corpus (9,659 headlines) → FSSI-v3; GDELT GKG (58,576 documents); E113 GDELT price-news composite | daily → issue-date windows | region (province tag on 33% of headlines) | 9,659 headlines | 2021-Q1 – 2026-Q4 | FSSI-v3 sufficient in 17% of province-quarters; GDELT 0% missing from 2022 | items published before O(t) | coverage measured; sparse FSSI disclosed | none; regional FSSI tested separately (Addendum 2) |
| H1 | Regional hunger outlook above 11.3% | SWS involuntary hunger, Balance Luzon, verified non-commissioned series | quarterly rounds | Balance Luzon (region) | 20 quarters with a reading (23 rounds) | 2021-Q2 – 2026-Q3 | 3 quarters without a round | rounds published before O(t) | **defect fixed in FINAL_THESIS_OBJECTIVES**: the backend series included the commissioned 2025-Q1 round and dropped regular 2025-Q2/Q3 rounds | verified series used |

## Geographic resolution, stated plainly

- **Provincial (vary by province):** A1, A2, A3, C2, C3, C4, and V1 (static).
- **Regional (one value for all five provinces):** H1 (Balance Luzon covers all of Luzon outside Metro Manila, not
  only CALABARZON), N1 (most headlines carry no province tag).
- **National (one value for all five provinces):** C1, E1, E2.

So six of twelve families give no province-to-province contrast in a quarter. The forecast can separate provinces only
through the price, production, typhoon and static vulnerability families.

## Data that exist but could not be used

| Data | Why not used |
|---|---|
| CBMS 2024 LGU food-insecurity items | not published openly; the PSA site is behind a bot check (search log: `FINAL_OBJECTIVE_ACHIEVEMENT/sources/LOCAL_DATA_SEARCH_LOG.md`) |
| FNRI ENNS/NNS provincial FIES | 2021 and 2023 only, too few points to train on; used for face validity (Objective 5) |
| SWS hunger before 2021 | outside the 2021+ study window; the E114 long-history arm is a separate sensitivity only |
| SWS commissioned 2025-Q1 round | not part of the regular series; excluded |
