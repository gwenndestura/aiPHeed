# E43-data: refresh of the four driver series

Refreshed files are in `backend/experiments/e43/data/`, and the scripts that produced them are in `backend/experiments/e43/scripts/`. Nothing in `backend/data/processed/` and no ingestion code was changed. No model was trained. Data were fetched on **2026-10-15**.

**What could be reached** (`scripts/net_check.py`):

| Source | Status |
|---|---|
| NASA POWER API | **200**, used |
| PSA OpenStat PXWeb API | **200**, used |
| psa.gov.ph (release calendars, special-release PDFs) | **403** |
| bsp.gov.ph (statistics pages, xlsx) | **403** (also 403 to the web-fetch tool) |
| Web search (news reports of BSP/PSA releases) | available, used as a **secondary** source and marked as such |

**Timing note** (applies to all four drivers). For the Q4 2026 forecast (origin 2026-10-01, lead 1), every driver uses data of **2026-Q2** (quarter t−1).

---

## 1. Climate Stress: rainfall rebuilt from ONE service

`scripts/rain_daily.py` → `data/rainfall_daily_province.{parquet,csv}`, `data/rainfall_daily_vs_monthly_2021_2025.csv`

**Method.** NASA POWER **daily** PRECTOTCORR from 1991-01-01 to the latest day, at the same 30 interior points (6 per province, `data/reference/calabarzon_rainfall_points.csv`). The 1991–2020 normal is built from the same daily data. Each quarter is the mean of its three monthly anomalies, the same formula as the served 1991–2025 build. Only complete quarters are written (every day of every point present).

| | Before (served `province_rainfall.parquet`) | After (E43) |
|---|---|---|
| Coverage | 1991-Q1 – 2026-Q2 | 1991-Q1 – **2026-Q3** (2026-Q4 incomplete, not written) |
| Service | monthly 1991–2025 (700 rows) + daily 2026-Q1/Q2 (10 rows) | **daily only** (715 rows) |
| Observed / filled | 710 / 0 | **715 / 0** |
| Anomaly formula | mean of monthly anomalies for 1991–2025, but **ratio of quarterly means for 2026** | mean of monthly anomalies throughout |

**Daily vs monthly service, 2021–2025 (anomaly, percentage points):**

| Province | Quarters | Mean abs. diff | Max abs. diff | Correlation |
|---|---|---|---|---|
| Cavite | 20 | 0.02 | 0.05 | 1.000 |
| Laguna | 20 | 0.02 | 0.05 | 1.000 |
| Quezon | 20 | 0.01 | 0.02 | 1.000 |
| Rizal | 20 | 0.03 | 0.07 | 1.000 |
| Batangas | 20 | 0.04 | 0.11 | 1.000 |

**Finding.** The two NASA services are equivalent; the differences are rounding. The real inconsistency was elsewhere: the served 2026 rows (`scripts/extend_province_rainfall.py`) compute the quarterly anomaly as (quarter precipitation − quarter normal) ÷ quarter normal. The 1991–2025 rows average the monthly anomalies. The precipitation and normals are identical, but the anomaly differs:

| Province | Served 2026-Q2 | E43 2026-Q2 | Gap |
|---|---|---|---|
| Cavite | −43.41% | −59.13% | −15.7 pp |
| Laguna | −55.65% | −63.16% | −7.5 pp |
| Quezon | −55.34% | −61.63% | −6.3 pp |
| Rizal | −51.66% | −59.11% | −7.5 pp |
| Batangas | −48.23% | −61.10% | −12.9 pp |

2026-Q1 differs by 3.7–7.2 pp (`scripts/rain_2026_check.py`). The E43 file is consistent from end to end.

**Storms and ENSO** (`pagasa_climate.parquet`, IBTrACS/ONI) were not refreshed in this task. They already run to 2026-Q3.

**Verified online:** `https://power.larc.nasa.gov/api/temporal/daily/point` (PRECTOTCORR, community AG). NASA POWER is near-real-time and has no formal release date, so `release_date` is empty.

## 2. Employment: observed LFS values only

`scripts/lfs_fetch.py` → `data/unemployment_monthly.csv`, `data/unemployment_quarterly.{csv,parquet}`, `data/unemployment_served_vs_psa.csv`

**Source.** PSA OpenStat `DB/1B/LFS/0021B3FKEI2.px`, "Rates Key Employment Indicators: April 2005 to August 2026" (national, **monthly**; table updated 2026-10-07). Fetched without any fill.

| | Before (served `psa_indicators.parquet`) | After (E43) |
|---|---|---|
| Coverage | 2020-Q1 – 2026-Q4 | monthly 2021-01 – **2026-08** (68 months); quarterly 2021-Q1 – 2026-Q3 |
| Quarter definition | one survey month per quarter (Jan/Apr/Jul/Oct), forward- and back-filled | mean of the released months, plus the survey-month value kept for comparison |
| Observed / filled | not recorded; **2026-Q4 is a fill** (= 2026-Q3) | months: 68 observed, 0 filled. Quarters: **22 observed** (all three months released), **1 partial** (2026-Q3: Jul + Aug; September not released) |

**Do the served 2026 values match PSA?** **Yes for 2026-Q1, Q2 and Q3.** The served 5.806, 4.706 and 6.005 are exactly PSA's January, April and July 2026 releases. The same holds for every quarter 2021-Q1 to 2026-Q3. **2026-Q4 (6.005) is not a PSA value**; it is the forward-fill of July 2026.

**Note on the quarter definition.** One survey month can differ a lot from the quarter's average. For example, 2025-Q3 is 5.331 in July against a 4.342 mean for July–September, and 2026-Q3 is 6.005 against 5.637 for July–August. E43 should use the **quarter mean** (`value`). For the Q4 2026 origin this uses 2026-Q2 (all three months released by August 2026), so there is no timing problem.

**Regional (Region IV-A) quarterly unemployment on OpenStat: not available.**
- The LFS folder `DB/1B/LFS` holds 20 tables, all national; none has a region dimension.
- An OpenStat search for "unemployment region" / "CALABARZON unemployment" found only national or annual tables. Examples: `DB/3K/E2/0193K3E2020.px` (national, annual 1995–2018) and `DB/3E/CH/LE/0063E3D67B0.px` (national, 2006–2016).
- PSA publishes regional LFS estimates in special releases on psa.gov.ph (HTTP 403 here) and through the PSA Region IV-A office. These would need to be collected by hand.

**Verified online:** `https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1B/LFS/0021B3FKEI2.px`.

## 3. OFW Remittance: 2026 extension

`scripts/remit_prepare.py` → `data/remittance_monthly_2026.csv`, `data/remittance_quarterly.{csv,parquet}`, `data/remittance_manual_template.csv`, `data/real_peso_inputs.{csv,parquet}`

**Primary source blocked.** bsp.gov.ph returns HTTP 403, so the BSP tables could not be read. The 2026 values below are **BSP figures as reported** by news outlets and the government news agency. Every row carries its URL and `verified_primary = 0`.

| Month 2026 | Cash remittances (USD bn) | YoY (reported) | Source |
|---|---|---|---|
| Jan | 3.02 | +3.5% | [BusinessWorld via Metrobank](https://wealthinsights.metrobank.com.ph/news/cash-remittances-hit-9-month-low-in-february) |
| Feb | 2.79 | +2.6% | [PNA](https://www.pna.gov.ph/articles/1272959) |
| Mar | 2.874 | – | [GMA](https://www.gmanetwork.com/news/money/economy/991477/remittances-hit-11-month-low-in-april-2026/story/) |
| Apr | 2.718 | +2.0% | [GMA](https://www.gmanetwork.com/news/money/economy/991477/remittances-hit-11-month-low-in-april-2026/story/) |
| May | 2.713 | +2.0% | [SunStar](https://www.sunstar.com.ph/davao/cash-remittances-rise-to-us271b-in-may) |
| Jun | 3.04 | +1.7% | [Tribune](https://tribune.net.ph/2026/08/17/bsp-remittances-reach-half-year-high-in-june) |
| Jul | 3.24 | +1.9% | [Migrant Times](https://migrantimes.com/remittance-finance/18-09-2026/philippine-cash-remittances-rise-to-324-billion-in-july-central-bank) |
| Aug | 3.03 | +1.9% | [BusinessWorld](https://bworldonline.com/top-stories/2026/10/15/787129/philippine-cash-remittances-drop-to-3-month-low-in-august/) (released 2026-10-15) |
| Sep | **missing** | – | not released yet (BSP publishes about 6 weeks after the month; expected about mid-November 2026) |

**Quarterly cross-checks.**
- **2026-Q1** = 8.684, matching the reported Jan–Mar total of 8.68 (+2.8%, [PIA](https://pia.gov.ph/press-release/cash-remittances-reach-us2-9b-in-march-2026/)).
- **2026-Q2** = 8.471, matching the reported Jan–Jun total (17.15, +2.4%) minus Q1. Its YoY (**+2.0%**) is derived from those two reported growth rates.
- **2026-Q3** is not complete (observed = 0).

**Problem found in the served series.** BSP's 2026 releases imply Jan–Mar 2025 = 8.444 and Jan–Jun 2025 = 16.748. The hand-curated `bsp_macro.parquet` has 8.65 and 17.35, which is **3.6% too high for the first half**. Its 2025 total (35.85) is also above BSP's reported full year of 35.634 ([BusinessWorld](https://www.bworldonline.com/top-stories/2026/02/16/730762/ofw-remittances-soar-to-all-time-high-35-63-billion-in-2025/)). The curated **quarterly split**, and so the curated 2022–2025 YoY rates, cannot be trusted as they are.

| | Before | After |
|---|---|---|
| Coverage | 2021-Q1 – 2025-Q4 (curated) | + 2026-Q1, 2026-Q2 (reported, secondary); 2026-Q3 partial |
| Observed / filled | 20 curated, not verified | 22 quarters with a value (0 filled), **0 verified against BSP primary**; 2026-Q3 missing |

**Real-peso composite inputs** (`data/real_peso_inputs.*`): remittance YoY, USD/PHP YoY (live ECB/Frankfurter, through 2026-Q3) and provincial food CPI YoY (`psa_indicators`, read only, through 2026-Q3), with g_real computed. All three inputs are present for 2022-Q1 to 2026-Q2 (18 quarters × 5 provinces).

**To fill by hand** (`data/remittance_manual_template.csv`) from BSP "Overseas Filipinos' Cash Remittances" (BSP Statistics → External Accounts, monthly by country):
- January–August 2026: confirm the reported values.
- September 2026: add when released.
- 2024-Q1 to 2025-Q4: re-curate from BSP's monthly table, so that all YoY rates share BSP's basis.

## 4. Fish Kill: fisheries production and release timing

`scripts/fish_fetch.py` → `data/fisheries_production.{csv,parquet}`, `data/fisheries_release_dates.csv`

**Source.** PSA OpenStat `DB/2E/FS/0132E4GVFP1.px`, "Fisheries: Volume of Production by Geolocation, Subsector, Year and Quarter". Fetched for Region IV-A and the five provinces, all subsectors, 2020–2026.

| | Before (served `food_availability_panel.parquet`) | After (E43) |
|---|---|---|
| Coverage | 2021-Q1 – 2026-Q2 | 2020-Q1 – 2026-Q2 (province + **Region IV-A** totals) |
| 2026-Q3 | – | **not released** (cells return `..` on 2026-10-15) |
| Agreement | – | served totals = PSA now for all 110 province-quarters (max diff 0.01 t) |
| Observed / filled | all observed | all observed, 0 filled |

**Release dates.**
- **Verified:** only the OpenStat table update stamp, **2026-08-06**, which corresponds to the 2026-Q2 data. OpenStat exposes only the latest update, not a history.
- **Not verified:** the PSA release calendar (psa.gov.ph) returns 403. A web search summary gave **2021-08-23** for Q2 2021 and **2022-09-05** for Q2 2022 (special-release PDFs on psa.gov.ph), but the PDFs could not be opened.
- **Not found:** every other quarter. I have not assumed any dates.

What the evidence supports: the 2026-Q2 data was online before the Q4 2026 origin (2026-10-01), and the two unverified historical Q2 dates also fall before the following quarter's start. Whether this held for every quarter from 2021 to 2026 **is not verified**.

**Verified online:** `https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/FS` (update stamp) and `.../0132E4GVFP1.px` (data).

---

## Still missing (exactly)

| Driver | Missing | Where to get it |
|---|---|---|
| Climate | nothing for E43 (2026-Q4 is incomplete because the quarter is under way) | — |
| Employment | September 2026 (not released); a quarterly Region IV-A series (not on OpenStat) | PSA LFS monthly release (psa.gov.ph); PSA RSSO IV-A regional LFS releases |
| OFW | BSP-primary confirmation of Jan–Aug 2026; September 2026 (not released); BSP-consistent 2024–2025 quarterly values | BSP Statistics → External Accounts → Overseas Filipinos' Cash Remittances (monthly, by country); template `data/remittance_manual_template.csv` |
| Fish Kill | 2026-Q3 production (not released); release dates for 2021-Q1 – 2026-Q1 | PSA Fisheries Situation Report special releases and the PSA advance release calendar (psa.gov.ph) |

## Verdict for the E43 run

| Driver | Verdict | Why |
|---|---|---|
| **Climate Stress** | **READY** | One service, 1991–2026-Q3, every quarter observed. The daily and monthly services agree (r = 1.000, mean difference ≤ 0.04 pp). The served 2026 anomaly formula error is avoided by using the E43 file |
| **Fish Kill** | **READY** (proxy) | Production observed through 2026-Q2 (what the Q4 2026 origin needs) and identical to PSA. Caveats: proxy, not incidents; release timing verified only for the latest release |
| **Employment** | **READY** (national) | Observed monthly LFS, no fills, 22 complete quarters through 2026-Q2. Use the quarter mean. No regional series exists on OpenStat |
| **OFW Remittance** | **NOT READY** | 2026 values come only from secondary reports (not checked against BSP), and the curated 2022–2025 quarterly split disagrees with BSP's own figures by up to 3.6%, which distorts the YoY input. A provisional run is possible with `remittance_quarterly.csv`, but it should be labelled provisional until the template is filled from BSP |
