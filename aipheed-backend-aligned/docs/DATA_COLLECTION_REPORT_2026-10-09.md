# Authorized Data Collection Report (2026-10-09)

**Scope:** step 3 of `docs/POST_DECISION_ACTION_PLAN_2026-10-09.md`, as authorized by the researcher on 2026-10-09.

**Not changed:** no label, feature, production file, hand-curated SWS table, frozen forecast or thesis text. No model was run. Nothing about September or December 2026 SWS results was searched for, opened or retrieved. Nothing was committed or deployed.

## 1. Gaps confirmed before collection (existing files)

| Gap | Evidence |
|---|---|
| SWS April, June and September 2025 rounds absent | Not in `app/ml/corpus/sws_hunger_fetcher.py` (its 2025 entries: March 15–20 and November only), `docs/provenance/sws_hunger_sources.json` (2025-Q1, 2025-Q4 only) or `data/processed/sws_hunger.parquet` |
| Provincial food CPI ends at 2025-Q4 | `data/processed/psa_indicators.parquet` (`cpi_full` holds the region only) |

## 2. What was collected

### 2.1 Provincial food CPI, January–June 2026 (30 of 30 authorized values)

| Item | Detail |
|---|---|
| Source | PSA OpenStat `DB/2M/PI/CPI/2018NEW/0012M4ACP23.px`, "Year-on-Year Changes of the Consumer Price Index in Percent by Commodity Group (2018=100): January 2019 – September 2026" |
| Query | Geolocation 33–37 (Batangas, Cavite, Laguna, Quezon, Rizal); commodity `2` = "01.1 – FOOD", the same code used by `openstat_fetcher.py` for the label series; year 2026; January–June |
| Retrieved | 2026-10-09 14:40:49 UTC; HTTP 200 |
| Values | 30 reported, 0 suppressed (`provincial_food_cpi_yoy_2026H1_raw.csv`). The raw response is kept unmodified (SHA-256 `1c9932b5…`). |
| Units | Year-on-year % change in the 2018=100 index |
| Geography | Province. PSA lists "City of Lucena (Capital)" separately from Quezon; the project's existing series uses the same "Quezon" definition. |
| National release dates (`cpi_2026_release_dates.csv`) | January → 2026-02-05; February → 03-05; March → 04-07; April → 05-05; May → 06-05; June → 07-07 [dated news reports] |
| Provincial release dates | **Unverified.** RSSO IV-A publishes CALABARZON provincial CPI at its own regional release; in the one verified case it came 6 days after national. |
| Limitations | Current vintage (PSA CPI revisions, if any, are not visible). The value "0.0" for Batangas in June 2026 is a reported value, not a blank. |

### 2.2 SWS Balance-Luzon hunger, 2025 (3 of 3 authorized rounds)

| Round (fieldwork) | Fieldwork quarter | Total | Moderate | Severe | Respondents | Sample / Balance-Luzon error | Published | Source |
|---|---|---:|---:|---:|---|---|---|---|
| April 23–28, 2025 (SWS: "First Quarter 2025 SWS") | 2025-Q2 | 17.0 | 13.9 | 3.1 | Adults 18+ | 1,500 (600 Balance Luzon) / ±4% | 2025-06-27 | [SWS release](https://sws.org.ph/social-weather-report-hunger-at-20-0-by-end-of-april-2025/) |
| June 25–29, 2025 | 2025-Q2 | 15.3 | 13.0 | 2.3 | Adults 18+ | 1,200 / ±6% | 2025-08-15 | [SWS release](https://sws.org.ph/social-weather-report-hunger-falls-from-20-0-in-april-2025-to-16-1-in-june-2025/) |
| September 24–30, 2025 (SWS: "Third Quarter 2025 SWS") | 2025-Q3 | 23.8 | 17.2 | 6.6 | Adults 18+ | 1,500 / ±4% | 2025-11-05 | [SWS release](https://sws.org.ph/social-weather-report-hunger-rises-from-16-1-in-june-2025-to-22-0-in-september-2025/) |

**Checks:**

- Moderate + severe equals the total for all three rounds.
- Each value is restated identically in the next release (17.0 in the June release, 15.3 in the September release, 23.8 in the November release).

**Verification of an existing value** (`sws_existing_value_verification.csv`): the November 24–30, 2025 round matches the stored **16.7** (12.7 + 4.0) on [its release](https://sws.org.ph/social-weather-report-hunger-eases-slightly-from-22-0-in-september-2025-to-20-1-in-november-2025/), **posted 2026-01-14**. That page date upgrades the earlier [L] evidence to [V].

**Respondent populations, now verified on the releases** (resolves verification item 2.1):

| Period | Respondents |
|---|---|
| Up to December 2024 | Household heads |
| January 2025 to the April 11–15, 2025 survey | Registered voters |
| From April 23–28, 2025 | Adults 18+ |

**Method and its limitation:**

- The SWS release pages on sws.org.ph were read through an extraction step restricted to the article body: title, posted date, fieldwork, respondents and Balance-Luzon sentences, with sidebars and any 2026 content excluded so that no later round could be exposed.
- The raw HTML was not saved (a tool limitation), and archived copies were unavailable today (Internet Archive internal error).
- The values are corroborated by the internal sums and by each next release. A person may want to confirm them on the SWS PDF media releases.

## 3. Gaps that remain open

| Gap | Status | Reason |
|---|---|---|
| January and February 2025 Stratbase-SWS rounds | Not collected | Not authorized (conditional on D3) |
| **April 11–15, 2025 round (newly found; registered voters)** | Not collected; existence documented | Cited in the April 23–28 release. Not in the authorized list. A second, different-population round in 2025-Q2 that bears on D3. |
| Provincial CPI release dates (2026 and earlier) | Unverified | RSSO IV-A site behind Cloudflare; not bypassed |
| June 2026 SWS publication date | Not collected | Not part of this authorization (action plan item 2.4) |
| September and December 2026 SWS | Protected | Not searched or opened |
| Raw HTML of the SWS pages | Not archived | Tool limitation; PDFs or archive copies needed for a byte-level audit trail |

## 4. Effect on data completeness (raw data only; no labels rebuilt)

| Item | Before | After collection |
|---|---|---|
| SWS rounds from 2021 to 2025 with a value and a verified publication date | 18 (17 [V] + 1 [L]) | **21 values in hand, all 21 [V]**: 18 stored + 3 collected; November upgraded to [V] |
| 2025-Q2 SWS inputs | None | April 23–28 (published 2025-06-27) and June 25–29 (2025-08-15) |
| 2025-Q3 SWS inputs | None | September 24–30 (published 2025-11-05) |
| Labels **possible** for 2025-Q2 / 2025-Q3 | Not possible | Possible **after the D3 decision**. 2025-Q2 now has two collected adult rounds plus one uncollected registered-voter round (April 11–15). |
| Latest SWS round available at the 2025-Q4 / 2026-Q1 origins | Missing from the project | June 2025 / September 2025 now in hand |
| Provincial food CPI | Through 2025-Q4 | Through **June 2026** (monthly, raw) |
| 2026-Q3 / Q4 forecast inputs (provincial CPI for 2026-Q1 / Q2) | Missing | Available as raw monthly values |
| 2026-Q1 training label (needs January–March 2026 CPI) | Not computable | CPI available. The SWS value is already stored but exposed (disclosed-check status unchanged). |

## 5. Files

**Added** (all new; SHA-256 in the manifest):

- `data/supplementary/collection_2026-10-09/README.md`
- `data/supplementary/collection_2026-10-09/COLLECTION_MANIFEST.json`
- `data/supplementary/collection_2026-10-09/provincial_food_cpi_yoy_2026H1_raw.csv`
- `data/supplementary/collection_2026-10-09/openstat_0012M4ACP23_2026H1_raw_response.json`
- `data/supplementary/collection_2026-10-09/openstat_0012M4ACP23_2026H1_query.json`
- `data/supplementary/collection_2026-10-09/cpi_2026_release_dates.csv`
- `data/supplementary/collection_2026-10-09/sws_balance_luzon_2025_raw.csv`
- `data/supplementary/collection_2026-10-09/sws_existing_value_verification.csv`
- `docs/DATA_COLLECTION_REPORT_2026-10-09.md` (this report)

**Not changed:**

- `data/processed/*` (including `sws_hunger.parquet`, `labels.parquet`, `psa_indicators.parquet`)
- `app/ml/corpus/sws_hunger_fetcher.py`
- `docs/provenance/sws_hunger_sources.json`
- `models/`
- all frozen forecasts
- the thesis chapters
- earlier reports

**Stopping here.** Rebuilding labels or features, or running any model, waits for your approval and the D3 label decision.

### Sources

- **SWS releases:** [April 2025](https://sws.org.ph/social-weather-report-hunger-at-20-0-by-end-of-april-2025/); [June 2025](https://sws.org.ph/social-weather-report-hunger-falls-from-20-0-in-april-2025-to-16-1-in-june-2025/); [September 2025](https://sws.org.ph/social-weather-report-hunger-rises-from-16-1-in-june-2025-to-22-0-in-september-2025/); [November 2025](https://sws.org.ph/social-weather-report-hunger-eases-slightly-from-22-0-in-september-2025-to-20-1-in-november-2025/)
- **PSA OpenStat** [`0012M4ACP23`](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M/PI/CPI/2018NEW/0012M4ACP23.px)
- **CPI national releases:**
  - January 2026: [Philstar 2026-02-05](https://www.philstar.com/business/2026/02/05/2505952/inflation-picks-20-january-2026)
  - February 2026: [DZRH](https://www.dzrh.com.ph/post/ph-inflation-accelerates-to-24percent-in-february-psa)
  - March 2026: [Trading Economics](https://tradingeconomics.com/philippines/inflation-cpi/news/539462)
  - April 2026: [ABS-CBN 2026-05-05](https://www.abs-cbn.com/news/business/2026/5/5/inflation-quickens-to-7-2-percent-in-april-0906)
  - May 2026: [Philstar 2026-06-05](https://www.philstar.com/headlines/2026/06/05/2533026/inflation-slows-68-may-2026-amid-easing-transport-food-costs)
  - June 2026: [Trading Economics](https://tradingeconomics.com/philippines/inflation-cpi/news/564621)
