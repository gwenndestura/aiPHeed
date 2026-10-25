# E109 source log (written as each source was read; facts quoted from the page itself)

## S1. SWS, "Social Weather Report | Hunger rises to 22.6% in September 2026 from 20.3% in June 2026"

- **URL:** https://sws.org.ph/social-weather-report-hunger-rises-to-22-6-in-september-2026-from-20-3-in-june-2026/
- **Accessed:** 2026-10-25. **Published:** October 14, 2026. **Prepared by:** Leo S. Laroza.
- **Fieldwork:** September 21–27, 2026. Face-to-face interviews.
- **Sample:** 1,500 adults: Balance Luzon 600; Metro Manila, Visayas and Mindanao 300 each.
- **Sampling error:** ±3% national; **±4% Balance Luzon**; ±6% Metro Manila, Visayas and Mindanao.
- **Question:** "In the last three months, did it happen even once that your family experienced hunger and not have anything to eat?" (Yes/No). If yes: "Only once, A few times, Often, or Always?"
- **Definitions:**
  - Moderate Hunger = "Only Once" or "A Few Times";
  - Severe Hunger = "Often" or "Always";
  - Total Hunger = Moderate + Severe.
- **Hunger by area:**

  | Area | June 2026 | September 2026 |
  |---|---|---|
  | Balance Luzon | 17.3% | 23.6% |
  | Metro Manila | 21.0% | 27.0% |
  | Visayas | 22.3% | 16.0% |
  | Mindanao | 24.0% | 23.7% |
  | National | 20.3% | 22.6% (Moderate 16.2 + Severe 6.4) |

  The project's `sws_rounds.csv` has Balance Luzon 2026-Q2 17.3 and 2026-Q3 23.6: **match**. (The page title's 20.3/22.6 are national figures.)
- **High/low:** the page gives **no threshold for high or low**. It calls the 2020 national average of 21.1% "record-high" and cites a 2025 average of 20.2%.
- **Series continuity:** the hunger question has been asked 119 times since July 1998. Respondent base:
  - household heads, July 1998 – December 2024;
  - registered voters, January – April 2025;
  - adult respondents, from April 23–28, 2025.
- **Weighting:** national estimates are weighted with PSA medium population projections.

## S2. SWS, "Social Weather Report | Hunger falls from 20.0% in April 2025 to 16.1% in June 2025"

- **URL:** https://sws.org.ph/social-weather-report-hunger-falls-from-20-0-in-april-2025-to-16-1-in-june-2025/
- **Accessed:** 2026-10-25. **Published:** Aug 15, 2025.
- **June 2025 round:** fieldwork June 25–29, 2025; 1,200 adults, **300 in Balance Luzon (±6%)**; Balance Luzon **15.3%** (file: 2025-Q2 15.3, match).
- **April 2025 round:** fieldwork April 23–28, 2025, adults; Balance Luzon **17.0%** (file: 2025-Q2 17.0, match).
- **Other 2025 national figures cited:** March 2025 national 27.2%; April 11–15, 2025 national 19.1%.
- **Respondent base:** household heads July 1998 – Dec 2024; registered voters Jan 2025 – April 11–15, 2025; adults from April 23–28, 2025.
- **Funding:** "non-commissioned … included on SWS's initiative and released as a public service."

## S3. SWS, "Social Weather Report | Hunger rises from 16.1% in June 2025 to 22.0% in September 2025"

- **URL:** https://sws.org.ph/social-weather-report-hunger-rises-from-16-1-in-june-2025-to-22-0-in-september-2025/
- **Accessed:** 2026-10-25. **Published:** Nov 5, 2025.
- **Fieldwork:** Sept 24–30, 2025; 1,500 adults, **Balance Luzon 600 (±4%)**.
- **Balance Luzon:** **23.8%** (file: 2025-Q3 23.8, match). Moderate 13.0 → 17.2; Severe 2.3 → 6.6.

## S4. SWS, "Social Weather Report | Hunger rises from 20.1% in November 2025 to 23.2% in March 2026"

- **URL:** https://sws.org.ph/social-weather-report-hunger-rises-from-20-1-in-november-2025-to-23-2-in-march-2026/
- **Accessed:** 2026-10-25, via search summary.
- **Balance Luzon:** 16.7% in November 2025 and 22.4% in March 2026 (+5.7). File: 2025-Q4 16.7 and 2026-Q1 22.4, match.
- Search-result text only; the page was not opened.

## S5. Stratbase-SWS, March 2025 (commissioned survey)

- **Sources:** https://sws.org.ph/wp-content/uploads/2026/07/pr20250329-Stratbase-SWS-Mar-2025-Hunger-in-Families-media-release.pdf and GMA News (https://www.gmanetwork.com/news/topstories/nation/941035/hunger-survey-sws-march-2025/story/). Accessed 2026-10-25 via search results; the PDF could not be text-extracted.
- **Survey:** fieldwork March 15–20, 2025; **1,800 registered voters**, 900 in Balance Luzon.
- **Values:** national 27.2%; **Balance Luzon 24.0%**, up 4.9 points from 19.1% in February 2025.
- **File:** 2025-Q1 24.0, `definition_A = True`: match.
- **Status:** a **commissioned** survey on a different respondent base (registered voters). The February 2025 (Balance Luzon 19.1%) and April 11–15, 2025 rounds are **not** in the project file.

## S6. SWS fourth-quarter 2024 and third-quarter 2023 releases (spot checks)

- **December 12–18, 2024:** national 25.9% (18.7 moderate + 7.2 severe); **Balance Luzon 25.3%**, up from 18.1% in September 2024; 2,160 adults, 1,080 in Balance Luzon. Sources: GMA News https://gmanetwork.com/news/topstories/nation/933009/hunger-rises-to-25-9-highest-since-pandemic-sws/story; SWS PDF https://sws.org.ph/wp-content/uploads/2026/06/pr20250114-SWR2024-IV-Hunger-in-Families-media-release-1.pdf. File: 2024-Q4 25.3 and 2024-Q3 18.1, **match**.
- **September 28 – October 1, 2023:** **Balance Luzon 10.3%**, down from 11.3% in June 2023. Sampling error ±5.7% for Balance Luzon in September (300 respondents) and ±4.0% in June (larger sample). Sources: PNA https://alpha.pna.gov.ph/articles/1214033, Inquirer https://newsinfo.inquirer.net/1863123/. File: 2023-Q3 10.3 and 2023-Q2 11.3, **match**.
- **Hunger categories** (news reports of SWS releases): respondents who did not state a frequency are classified under Moderate Hunger.

## S7. PSA official poverty statistics (full-year 2023, with 2021 comparison)

- **URLs:**
  - https://psa.gov.ph/statistics/poverty/node/1684064820 (HTTP 403 to automated access);
  - PSA press release PDF https://psa.gov.ph/sites/default/files/phdsd/Press%20Release_2023%20Full%20Year%20Official%20Poverty%20Statistics.pdf;
  - PSA RSSO IV-A https://rsso04a.psa.gov.ph/node/1684057429 (403).
- **OpenStat table** https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__3S__C2/0111E2BFTE0.px/ shows a bot-verification page in the built-in browser. It was not bypassed, so it was **not opened**.
- **Definitions** (PSA, via search summary):
  - poverty threshold = minimum income needed to meet basic food and non-food requirements;
  - food threshold = minimum income needed to meet basic food requirements;
  - subsistence incidence = share of the population whose per capita income is below the food threshold.
- **Coverage:** official full-year estimates for 2018, 2021 and 2023 (triennial), national/regional/provincial.
- **CALABARZON 2023 population poverty incidence** (PSA RSSO via search): Quezon 10.2, Rizal 8.5, Laguna 7.9, Batangas 7.6, Cavite 6.7. CALABARZON monthly poverty threshold for a family of five: PHP 15,457 (national 13,873).
- **Project file** `backend/data/inputs/psa_subsistence_population_2021_2023.csv`: subsistence incidence (population) by province for 2021 and 2023, with CVs of 17–62%, publication date 2024-08-15, acquired in E54. **Not re-verified online in E109** (PSA blocks automated access).

## S8. FIES naming: two different instruments

- **World Bank Microdata catalog 5042:** https://microdata.worldbank.org/catalog/5042/data-dictionary/F1?file_name=PHL_2017_FIES_v01_EN_M_v01_A_OCS
  - **"Food Insecurity Experience Scale 2017"**, Philippines, producer **FAO Statistics Division**.
  - Eight items: worried, healthy, few foods, skipped, ate less, ran out, hungry, whole day.
  - Rasch-based probability of moderate+severe and of severe food insecurity.
  - This is **not** PSA's Family Income and Expenditure Survey, which shares the acronym.
  - Single year (2017), national only, before the study window: **not usable as a target**.
- **FAO** https://www.fao.org/measuring-hunger/en: FIES is "an experience-based metric of food insecurity severity". FIES-based moderate or severe prevalence is **SDG indicator 2.1.2**. The page gives no population-level high/low prevalence threshold.
- **CALABARZON FIES value in the project:** E87 cites FNRI NNS 2025 moderate+severe 22.6% (press report; a single regional value).
