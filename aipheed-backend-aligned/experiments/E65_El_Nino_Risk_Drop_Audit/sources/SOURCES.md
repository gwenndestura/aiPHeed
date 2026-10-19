# E65 sources (written as found, 2026-10-19)

All web lookups were limited to PAGASA (pagasa.dost.gov.ph, pubfiles.pagasa.dost.gov.ph) and PNA domains.
No PSA, BSP or SWS searches were run in E65. No CPI or hunger value was read from any web page.

## PAGASA ENSO status pages and advisories (2026)

| Date issued | Item | Source | Status text (paraphrased; short quotes only) |
|---|---|---|---|
| 2026-03-09 | La Niña Final Advisory | https://pagasa.dost.gov.ph/press-release/201 (title and date from the press-release list page 3) | La Niña ended |
| 2026-03-25 | El Niño Watch | https://pagasa.dost.gov.ph/press-release/207 | ENSO-neutral; El Niño probability rising for JAS 2026 |
| 2026-04-22 | El Niño Alert | https://pagasa.dost.gov.ph/press-release/209 | "79% chance of El Niño emerging in June-July-August (JJA) 2026"; likely to persist until early 2027 |
| 2026-06-09 | El Niño Advisory No. 1 | press-release/216; PDF `pagasa_pdfs/EN_Advisory_1_2026-06-09.pdf` | El Niño conditions present; rSSTA reached +0.5 °C in May 2026; >80% chance of a full El Niño, persisting until early 2027 |
| 2026-07-06 | El Niño Advisory No. 2 | PDF `EN_Advisory_2_2026-07-06.pdf` | weak to moderate El Niño; models suggest very strong by OND 2026 |
| 2026-08-06 | El Niño Advisory No. 3 | PDF `EN_Advisory_3_2026-08-06.pdf` | moderate El Niño; continue until H1 2027; may reach very strong before end of 2026. August outlook: below-normal rainfall in most of Southern Luzon |
| 2026-09-07 | El Niño Advisory No. 4 | PDF `EN_Advisory_4_2026-09-07.pdf` | moderate to strong; continue until H1 2027; may reach very strong, peak toward end of 2026. August assessment: above-normal rain in most of Luzon; the enhanced SW monsoon + TCs Luis/Maymay/Neneng affected regions including CALABARZON (NDRRMC SitRep 30, 01 Sep 2026: agricultural damage > PHP 2.2 billion across all affected regions). September outlook: near- to above-normal rain for most of Luzon |
| 2026-09-23 | Climate Advisory for "Very Strong" El Niño | https://pagasa.dost.gov.ph/press-release/225 | strong El Niño active; expected to intensify to very strong in SOND 2026; persisting through H1 2027; risk of agricultural dry spells and water stress |
| 2026-10-07 | El Niño Advisory No. 5 | PDF `EN_Advisory_5_2026-10-07.pdf`; https://www.pagasa.dost.gov.ph/climate/el-nino-la-nina/monitoring ("Updated 07 October 2026") | "A strong to very strong El Niño is present"; continue until H1 2027; may peak before end of 2026. October outlook: below-normal rain over most of Luzon; dry conditions likely in Quezon by end-October. September assessment: patches of above-normal rain incl. Cavite |

Advisory list: https://www.pagasa.dost.gov.ph/climate/el-nino-la-nina/advisories (lists Nos. 1–5 with dates; no 2025 entries).
PDF text was extracted with `pdftotext -layout` into the `.txt` files beside each PDF. The PDF metadata dates (creation) match the issue months.

## PAGASA ENSO status history 2021–2026 (press-release archive, https://pagasa.dost.gov.ph/press-release?page=N)

| Date | Press release | Status |
|---|---|---|
| 2021-07-16 | 89 La Niña Watch | La Niña Watch |
| 2021-09-14 | 94 La Niña Alert | La Niña Alert |
| 2021-10-15 | 95 Onset of La Niña (La Niña Advisory #1) | La Niña Advisory |
| 2022 (all year) | no 2022 ENSO press release listed; PAGASA 2022 climate publication (pubfiles .../CLIMATOLOGICAL PUBLICATIONS/2022.pdf, via search summary) says La Niña "persisted throughout the year 2022" (triple dip) | La Niña Advisory (inferred continuity: **not** a dated advisory) |
| 2023-03-24 | 129 El Niño Watch | El Niño Watch (La Niña over) |
| 2023-05-02 | 137 El Niño Alert | El Niño Alert |
| 2023-07-04 | 140 El Niño is present | El Niño Advisory |
| 2024-03-07 | 150 El Niño Advisory No. 9 / La Niña Watch | El Niño Advisory + La Niña Watch |
| 2024-06-07 | 158 El Niño Final Advisory | El Niño ended; La Niña Watch continues |
| 2024-07-12 | 161 La Niña Alert | La Niña Alert |
| 2025-01-06 | 170 La Niña condition is present | La Niña Advisory |
| 2025-04-04 | 175 Termination of La Niña Alert | none (neutral) |
| 2025-08-26 | 185 La Niña Watch | La Niña Watch |
| 2025-09-15 | 187 La Niña Alert | La Niña Alert |
| 2025-10-10 | 189 La Niña conditions are present | La Niña Advisory |
| 2025-12-04 | 195 La Niña Advisory #1 | La Niña Advisory |
| 2026-03-09 | 201 La Niña Final Advisory | none |
| 2026-03-25 | 207 El Niño Watch | El Niño Watch |
| 2026-04-22 | 209 El Niño Alert | El Niño Alert |
| 2026-06-09 | 216 El Niño Advisory | El Niño Advisory |

Limitations of this timeline:
- The press-release list skips IDs (e.g. 125–126, 131, 136, 139, 141, 147–148, 154, 159, 163, 165, 167–168, 176–178, 182, 184, 191, 196–198, 202, 206, 208, 210–212, 215, 218, 220–224). Some ENSO items may exist only as advisory PDFs.
- Origin 2022-01-01 through 2023-01-01 is coded La Niña Advisory from the 2021-10-15 onset plus the 2022 climate summary, not from a dated advisory.
- PAGASA's official **forecasts of strength** (e.g. "very strong") exist only from 2026-07-06 in this window. No comparable strength forecast exists for the 2023–24 event in the press list, so strength forecasts cannot be trained on.

## NOAA data already in the pipeline

- ONI: https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt, through `aipheed-backend-aligned/data/processed/pagasa_climate.parquet` (`fetched_at` 2026-09-09T03:18Z). Built by `backend/app/ml/corpus/pagasa_climate_fetcher.py`: the quarter value is the mean of the ONI seasons whose centre month falls in the quarter, then classified into phase and intensity.
- IBTrACS WP v04r01: storms within 300 km of the province centroid, same file.
- `drought_alert` = El Niño phase AND quarter-mean ONI ≥ 1.0. It is derived from ONI and is **not** a PAGASA drought advisory.
