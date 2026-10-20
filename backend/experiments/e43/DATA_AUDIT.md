# E43 data audit: the four non-market risk drivers

Scope: Climate Stress, Fish Kill, Employment, OFW Remittance. This is a read-only audit of `backend/data/processed/` and the ingestion code. No model was trained, and no existing file or data was changed.

**Verification status.** Items 1, 3 (as built here) and 4 are measured from the repository. Item 2 (newer releases) and the "other sources" in item 3 come from the ingestion code's own source notes plus general knowledge of the publishers. **They were not checked online in this audit** and are marked *to verify*.

## Summary table

| | Climate Stress | Fish Kill | Employment | OFW Remittance |
|---|---|---|---|---|
| **Processed file(s)** | `province_rainfall.parquet` (rainfall); `pagasa_climate.parquet` (storms, ENSO) | `food_availability_panel.parquet` (group `fisheries`); news store `data/news_e31/articles.jsonl` + `app/ml/nlp/trigger_classifier.py` | `psa_indicators.parquet` (`unemployment_rate`) | `bsp_macro.parquet` (`ofw_cash_remit_usd_bn`, `ofw_remit_yoy_pct`, `fx_usd_php_*`) |
| **Ingestion code** | `scripts/build_province_rainfall.py`, `scripts/extend_province_rainfall.py`, `app/ml/corpus/pagasa_climate_fetcher.py` | `scripts/build_food_availability_panel.py`; `app/ml/corpus/rss_fetcher.py` + trigger classifier | `app/ml/corpus/openstat_fetcher.py` (`_fetch_unemployment`) | `app/ml/corpus/bsp_macro_fetcher.py` (curated list `OFW_REMIT_QUARTERLY`) |
| **Original source** | NASA POWER PRECTOTCORR (MERRA-2); NOAA IBTrACS v04r01 (WP best track); NOAA CPC ONI. **Not PAGASA data**, despite the file name | PSA OpenStat fisheries production by subsector (`DB/2E/FS/0132E4GVFP1.px`); Google News RSS titles (E31 store) | PSA OpenStat Labor Force Survey (`DB/1B/LFS/0021B3FKEI2.px`; the old `0021B3GKEI2` returns 404) | BSP quarterly remittance press releases, typed in by hand (BSP returns HTTP 403 to scripts); FX from ECB via Frankfurter API |
| **Geographic level** | Rainfall: province (6 interior points per province). Storms: province centroid, 300 km radius. In practice only 1–2 distinct values across the five provinces per quarter, so storms are close to regional. ONI / drought_alert: global/national (identical for all provinces) | Production: province × subsector (16 series: aquaculture and inland for 5 provinces; commercial and marine for the 3 coastal provinces). News: province-attributed titles | **National only**; the fetcher copies it to every province | **National only**; copied to every province |
| **Frequency** | Rainfall monthly → quarter; storms per event → quarter; ONI monthly (3-month running) → quarter | Quarterly production; news daily → quarter | Quarterly (LFS rounds Jan/Apr/Jul/Oct mapped to Q1–Q4) | Quarterly (curated); FX daily → quarter |
| **First – last quarter in repo** | Rainfall 1991-Q1 – **2026-Q2**; storms and ONI 2021-Q1 – **2026-Q3** | Production 2021-Q1 – **2026-Q2**; news 2021-Q1 – 2026-Q4 | 2020-Q1 – 2026-Q4 in file, but **2026-Q4 is a forward-fill of 2026-Q3**, and 2026-Q1–Q3 provenance is not recorded (see item 4) | Remittance USD 2021-Q1 – **2025-Q4**; YoY % 2022-Q1 – **2025-Q4**; FX runs further |
| **Newer release through 2026?** *(to verify)* | NASA POWER **daily** endpoint is current (already used for 2026-Q1/Q2); the monthly endpoint lags. IBTrACS is updated weekly; ONI monthly. Option: CHIRPS v2.0 monthly (UCSB CHC) as a consistent gridded alternative | PSA quarterly fisheries release for 2026-Q3 (same OpenStat table `0132E4GVFP1`), expected about two months after quarter end. BFAR fish-kill/red-tide (shellfish) bulletins exist as advisories, not a structured series | PSA monthly LFS releases for 2026 (same OpenStat table). Values for 2026-Q1–Q3 are already in the file but unverified | BSP "Overseas Filipinos' Cash Remittances" statistics (monthly, by country of source; BSP External Accounts page), published about 6 weeks after each month, so Jan–Aug 2026 should exist. Requires manual curation (403) |
| **Regional / provincial version at the same source?** *(to verify)* | Already province-level (rainfall, storms). PAGASA station rainfall (e.g. Ambulong, Sangley Point, Infanta) exists but has no open API | Already province-level (production). BFAR advisories name water bodies (Taal Lake, Laguna de Bay), so a lake/bay-level flag is possible | PSA LFS publishes **regional** (Region IV-A) unemployment, quarterly in OpenStat; provincial LFS estimates are annual only | BSP: no regional breakdown by destination. PSA Survey on Overseas Filipinos (SOF): **regional** OFW counts and remittances, annual, lagged about a year |
| **Main consistency problem** | Rainfall source changes service in 2026 (daily vs monthly), with no overlap to test; storm signal nearly constant across provinces; `drought_alert` is derived from ONI, not a PAGASA advisory; `rainfall_anomaly_pct` in `pagasa_climate` is empty by design | Production is a **proxy**, not fish-kill incidents; PSA release dates are not verified; news is very sparse (17 titles, 8 of 120 province-quarters, one cell holds 7) | National series reused for all provinces; ingestion **forward- and back-fills** gaps silently with no observed flag; no `fetched_at`/source column in `psa_indicators` | Hand-curated (no automatic refresh); stops at 2025-Q4; national only; USD-denominated (peso value and prices ignored) |

## Detail by driver

### Climate Stress
- **Rainfall.** 710 province-quarters. 700 come from POWER's monthly endpoint (1991–2025, fetched 2026-09-01) and 10 from the daily endpoint (2026-Q1/Q2, fetched 2026-09-04).
  - `extend_province_rainfall.py` argues the two services are equivalent (same PRECTOTCORR parameter; a monthly mean of daily mm/day). But no month exists in both, so this was never measured.
  - The anomaly uses the 1991–2020 normal: a fixed reference, not data from the study window.
- **Storms.** `tc_count`, `tc_max_signal` (wind-speed class, not an official PAGASA signal) and `tc_severe_flag`, all within 300 km of the province centroid. With a 300 km radius, the five provinces nearly always share one value.
- **ENSO.** The ONI phase and intensity are global. `drought_alert` = El Niño with ONI ≥ 1.0, a derived rule rather than an issued advisory.

### Fish Kill
- **Production.** PSA provides 352 rows (16 province-subsector series × 22 quarters, 2021-Q1 to 2026-Q2). It measures supply, not mortality: a fall can come from a fish kill, a fishing ban, a typhoon or market factors. It is labelled "proxy (fisheries production)" in the risk indicator layer.
- **News.** 8,320 titles in the E31 store, 2,820 attributed to a province (120 province-quarters, median 20 titles each).
  - The classifier tags **17 fish-kill titles in 8 of 120 cells**: Cavite 2023-Q4 (7); Laguna 2021-Q1 and 2026-Q3 (2 each); Batangas 2021-Q3, 2022-Q3 (2) and 2023-Q3; Quezon 2026-Q2; Rizal 2026-Q3.
  - The classifier's own notes record that a broader keyword list raised the number of cells with any fish-kill title from 20 to 43 and made every headline metric worse.

### Employment
- **Source.** National LFS unemployment rate, mapped to all five provinces.
- **Filling.** `openstat_fetcher.py` merges with `ffill().bfill()` per province, so missing LFS quarters are filled with neighbouring values and no flag is kept.
  - In the file, **2026-Q4 = 2026-Q3 = 6.005**, a forward-fill.
  - 2026-Q1 = 5.806, 2026-Q2 = 4.706 and 2026-Q3 = 6.005 have no recorded fetch date. Earlier work treated them as "not verified" and used only values through 2025-Q4.
- **News.** Employment titles are almost absent: **1** in 120 cells.

### OFW Remittance
- **Source.** A curated list in `bsp_macro_fetcher.py` (2020-Q1 to 2025-Q4). The fetcher refuses to run past `REMIT_COVERAGE_END = (2025, 4)` unless asked to truncate.
- **Coverage.** YoY growth starts in 2022-Q1, because the 2020 values are not in the 2021+ window.
- **News.** No OFW/remittance titles at all (**0** in 120 cells).

## Proposed composite features for a 4-feature E43 test

**Shared timing rule.** At origin O(t) (the first day of quarter t+1), use data of quarter t−1 and news of quarter t. References are expanding (2021-Q1 to t−1, pooled over provinces), so no future data enters.

**Shared notation.**
- PR(x) is the percent rank of x within that expanding reference, divided by 100 so it lies in 0–1.
- z(x) is the z-score against the expanding mean and standard deviation of 2021-Q1 to t−1.

| Driver | Composite (one feature) | Inputs | Level | Notes |
|---|---|---|---|---|
| **Climate Stress** | `CLIM = max( PR(|rain_anom_{p,t−1}|), PR(tc_max_signal_{p,t−1}) )` | NASA POWER rainfall anomaly (rebuilt from **one** service; see recommendation 1), IBTrACS max signal | province | "Worse of" two hazards on a common 0–1 scale; no tuned weights. ENSO left out (national and slow; can be a later test) |
| **Fish Kill** | `FISH = max( PR(max(0, −ln(V_{p,t−1}/V_{p,t−5}))), 1[fish-kill titles_{p,t} ≥ 1] )` | PSA total fisheries production (all four subsectors), fish-kill news flag | province | Decline only; a news report sets the value to 1. Keep the **proxy** label. With 8 news cells, the news part is almost always 0 |
| **Employment** | `EMP = ½·z(u_{t−1}) + ½·z(u_{t−1} − u_{t−5})` | LFS unemployment level and year-on-year change; **Region IV-A series if available** (recommendation 3), otherwise national | regional or national | The YoY difference removes LFS seasonality. E42: national unemployment was the only driver that improved E36 (small, fragile) |
| **OFW Remittance** | `OFW = max(0, −g^real_{p,t−1})`, where `g^real = (1+g_USD)(1+g_FX)/(1+π^food_{p}) − 1` | BSP cash-remittance YoY (USD), USD/PHP YoY (live), provincial food CPI YoY (PSA) | province (through food CPI) | The peso buying power of remittances; only a fall counts. Becomes province-varying through local food inflation. Needs BSP 2026 data (recommendation 4); otherwise carried forward with a stale flag |

## Recommendations (before E43)

1. **Rainfall: use one service end to end.** Rebuild 1991–2026 entirely from the NASA POWER **daily** endpoint, including the 1991–2020 normal, so the 2026 quarters are on the same basis. Alternatively, run the daily endpoint over 2021–2025 alongside the monthly values and measure the difference before mixing the two.
2. **Unemployment: record what is observed.** Add `observed`/`fetched_at` columns at ingestion and stop the silent `ffill().bfill()`. Then confirm whether the 2026-Q1–Q3 values are released LFS figures (PSA OpenStat `0021B3FKEI2`).
3. **Use a regional unemployment series.** If PSA OpenStat has quarterly Region IV-A unemployment, it is closer to the target than the national rate. Provincial LFS is annual only, so it doesn't suit a quarterly model.
4. **Extend remittances by hand.** Curate BSP monthly cash remittances for January–September 2026 into `OFW_REMIT_QUARTERLY`, with the release dates. That removes the carried-forward values at the Q4 2026 origin.
5. **Fisheries: verify release timing.** Record PSA release dates for the quarterly fisheries tables, so the "published before the origin" assumption for quarter t−1 can be checked.
6. **News triggers: don't expect a signal yet.** Fish-kill (17 titles), employment (1) and OFW (0) titles are too sparse to carry one. If fish-kill reports matter, BFAR advisories mapped to Taal Lake, Laguna de Bay and coastal municipalities would make a better flag than headline keywords.
7. **Plan E43 against what E42 learned.** Four composites (one per driver) on top of E36's 13 inputs is the right size. E42 showed that eight separate driver features added noise, and only national unemployment helped. Fix the adoption rule and the multiple-comparison handling (for example, Holm across the four single-driver arms) before running.
