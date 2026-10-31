# E130 sources log

Searches made under protocol section 6, after the freeze. The protocol was committed at `b58c48e`, with the seal at sha256 `94a08cd1…`.

**Search rules:**
- explicit years only;
- no "latest", "current" or "release" queries for PSA, BSP or SWS series;
- sws.org.ph blocked.

## S1 · PSA FIES-based provincial poverty and subsistence after 2023 (2026-10-31)

**Query:** "PSA 2025 Family Income and Expenditure Survey full year poverty statistics provinces subsistence incidence" (web search, sws.org.ph blocked).

**Result.** PSA has published **2025 Full Year Poverty Statistics**, including a regional and provincial press release. The 2025 FIES was fielded in July 2025 and January 2026, and the figures are labelled preliminary.

**URLs returned:**
- https://psa.gov.ph/sites/default/files/phdsd/Regional%20and%20Provincial%20Press%20Release_%202025%20Full%20Year%20Poverty%20Statistics_0.pdf
- https://psa.gov.ph/content/poverty-incidence-all-regions-declined-between-2023-and-2025
- https://psa.gov.ph/statistics/poverty/node/1684084074 ("Proportion of Poor Families Reduced to 6.4 Percent in 2025")
- https://psa.gov.ph/content/subsistence-incidence-s-0 (definition)
- https://psa.gov.ph/statistics/poverty/technical-notes
- https://www.panaynews.net/psa-18-regions-recorded-drop-in-poverty-incidence-among-families/ (secondary)

**Values seen in the search summary.** None is a seal target; see `CONTAMINATION_LOG.md`.
- National: poverty incidence among families 6.4 % in 2025, and 9.7 % of the population (secondary report).
- Regional: all 18 regions decreased significantly from 2023 to 2025.
- Provincial: no province has poverty incidence above 30 % in 2025.
- National subsistence incidence 2023: 2.7 % of families, 4.3 % of the population.

**No provincial subsistence value was seen.**

**OpenSTAT.** The cached E118 listing shows the full-year tables, for example `DB/1F/FY/0071F3DF040.px` ("Table 4. Annual Per Capita Food Threshold and Subsistence Incidence Among Population …"), updated 2026-08-03.

## S2 · FNRI 2022 ENNS provincial FIES (2026-10-31)

**Query:** "2022 Expanded National Nutrition Survey FNRI household food insecurity FIES Laguna Quezon Rizal province".

**Result.**
- Only national 2022 FIES appeared: 33.4 % moderate or severe and 2.0 % severe (PIA).
- A 2023 national figure also appeared (31.4 %).
- **No provincial 2022 values for Laguna, Quezon or Rizal were found.**
- A 2018–2019 ENNS facts PDF lists Quezon and Rizal, but it is pre-2021 and was not opened.

**URLs returned:**
- https://pia.gov.ph/regions/survey-reveals-decline-in-undernutrition-increase-in-obesity-across-all-ages/
- https://enutrition.fnri.dost.gov.ph/uploads/2024%20National%20Nutrition%20Summit_Part%201.pdf
- https://ghdx.healthdata.org/record/philippines-expanded-national-nutrition-survey-2021-2022

## S1b · Attempted acquisition of the PSA 2025 regional and provincial release (2026-10-31)

**PDF on psa.gov.ph.** `curl` returned **HTTP 403** with a Cloudflare "Just a moment…" challenge, which is bot detection. **It was not bypassed**, and the 5,947-byte challenge page was deleted. The browser was not used to get past it (standing rule: PSA bot checks are never bypassed).

**OpenSTAT (metadata only, no values read).**
- `DB/1F/FY/0071F3DF040.px` (provincial subsistence incidence among the population) still covers only 2018, 2021 and 2023.
- Every `DB/1F/FY` table was updated 2026-08-03 and stops at 2023.
- **No 2025 provincial table is on OpenSTAT yet.**

## S3 · Secondary reports of 2025 CALABARZON provincial figures (2026-10-31)

**Query:** "CALABARZON 2025 full year poverty statistics provinces Batangas Cavite Laguna Quezon Rizal subsistence incidence PSA".

**Result.** A Daily Tribune report of the PSA IV-A briefing gives 2025 **poverty incidence among families** (not subsistence, not population):

| Area | 2025 |
|---|---|
| CALABARZON | 2.7 % (5.3 % in 2023) |
| Quezon | 8 % |
| Laguna | 3.1 % |
| Rizal | 2.7 % |
| Cavite | 1.2 % |
| Batangas | 0.9 % |

**Release dates.** The 2025 official poverty statistics were first released on 21 August 2026. The PSA IV-A presentation was on 28 October 2026.

**No 2025 provincial subsistence value was found.**

**URLs:**
- https://tribune.net.ph/2026/10/29/calabarzon-family-poverty-rate-falls-to-27
- https://rsso04a.psa.gov.ph/content/2023-full-year-poverty-statistics-calabarzon (2023; PSA regional site, not visited)
- https://www.pna.gov.ph/articles/1234821
- https://opinyon.net/national/psa-poverty-declines-in-calabarzon

**Consequence.**
- The seal's target (2025 provincial subsistence incidence among the population, with CVs) is published but **not obtainable automatically**.
- Scoring waits for the owner to download the PSA "Regional and Provincial Press Release – 2025 Full Year Poverty Statistics" (or the 2025 statistical tables) into `data/owner_supplied/`.

## S4 · CBMS 2024 provincial or LGU FIES tables (2026-10-31)

**Query:** "2024 CBMS food insecurity experience scale results CALABARZON province Batangas Quezon Laguna Rizal Cavite households moderate severe".

**Result.**
- **No CBMS 2024 FIES figures were found for any CALABARZON province or LGU.**
- A PSA presentation lists the FIES indicator and says the data go to LGUs in 2025.
- The NNC Region IV-A profile cites an earlier, non-comparable survey.

**URLs:**
- https://www.events.psai.ph/2024/ac/ppt/PS_1B.1_ppt.pdf
- https://nnc.gov.ph/luzon-region/region-iv-a-profile/

**Unchanged from E129 / OUTCOME_GAP_RESOLUTION:** the data are held by PSA and the LGUs and are not public.

## S5 · NNC OPT Plus (not searched again)

E129 recorded NNC 403 to automated access. The measure is child undernutrition, which the E130 gate rejects at G1 as a food-insecurity target. Not searched again.

## S6 · Owner-supplied PSA 2025 workbook (2026-10-31)

**File.** `2025 Full Year Official Poverty Statistics_24Aug2026_0.xlsx`, downloaded by the owner. It is copied unchanged to `data/owner_supplied/psa_2025_fy_workbook/` (411,840 bytes; sha256 `ea80fe8d488bd082056d14bbfde5c39e744e11e5fc615a6dece2ed696eb8b4f8`). It was hashed before any value was read.

**Contents** (titles and headers only were read):
- Five sheets, `tab1`, `tab2`, `tab5`, `tab6` and `tab15`:
  - Table 1: poverty incidence among families;
  - Table 2: poverty incidence among population;
  - Table 5: magnitude of poor families;
  - Table 6: magnitude of poor population;
  - Table 15: grouping of provinces.
- All by region and province, for **2021, 2023 and 2025** (no pre-2021 column).
- No external links and no macros.

**No subsistence-incidence or food-threshold table is in the workbook.** The seal's target is not here, so the seal is **not scored**. No numeric value was extracted.
