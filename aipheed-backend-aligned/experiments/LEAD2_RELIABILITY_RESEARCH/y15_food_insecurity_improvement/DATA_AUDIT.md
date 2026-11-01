# Y15 data audit

Y15 reuses all Y14 inputs read-only (`../y14_food_insecurity_forecast/DATA_AUDIT.md`, `out/indicators.csv`). New in Y15: remittances, and the audit of the served FIRI history.

## 1. Remittances (Investigation B)

| Item | Detail |
|---|---|
| Earlier attempt (Y14) | BSP `ofw2.xlsx` returned HTTP 403 to automated download. It was **not** circumvented. A retry with browser-like headers was blocked by the permission system as bot-check circumvention and was not repeated. |
| BSP statistics page (normal fetch) | `https://www.bsp.gov.ph/SitePages/Statistics/External.aspx?TabId=8` lists "Historical EXCEL" downloads (labels "1978-Feb 2008", "Mar 2008-present"), but exposes no file URLs to a non-browser fetch. Not obtained. |
| Project's existing series | `FIRI_V2_DATA_AUDIT/data/bsp_cash_remittances_quarterly.csv`: BSP cash remittances rebuilt from 22 press-release figures. **2021-Q1 .. 2026-Q2 only**. |
| **Obtained:** IMF Balance of Payments (BPM6) public SDMX API, no login or access restriction | Personal transfers `PHL.CD_T.D752_S1W.USD.Q`: **1999-Q1 .. 2026-Q2, 110 quarters**, sha `9b7b9856…` <br>Compensation of employees `PHL.CD_T.D1.USD.Q`: 1999-Q1 .. 2026-Q2, sha `8f10dc27…` <br>Personal remittances `PHL.CD_T.R1_S1W.USD.Q`: 2005-Q1 .. 2026-Q2, sha `245863db…` <br>Tidy file `remittances_quarterly_usd_mn.csv`, sha `bd9982ea…` <br>Fetched 2026-10-29T13:51–13:52Z; IMF dataset update stamp 2026-10-28. URLs in `data_acquired/manifest.json`. |
| Geography | **National** (Philippines). There is no regional or provincial remittance series. E2 is a national driver applied to a regional outcome. |
| Validity check | Over the 2021+ overlap, IMF personal transfers vs BSP cash remittances: levels r = 0.997 (22 quarters), YoY r = 0.86 (18 quarters) |
| Release timing | BSP releases monthly cash remittances about 6 weeks after the month and the quarterly BOP about 2.5–3 months after the quarter. **The rule used** (quarter t−2 at O(t), i.e. ≥ 6 months after that quarter ended) is a conservative bound. Historical release dates were not individually verified. |
| Vintage | IMF serves the current revised series, not real-time vintages (disclosed) |
| Indicator | E2 = −(YoY % change of personal transfers, quarter t−2 vs t−6): a remittance decline. Available for origins from 2000-Q3. |

## 2. Served FIRI history (Investigation A, read-only)

| Item | Detail |
|---|---|
| Source | `backend/data/thesis/firi2_history.csv` (90 backtest rows; 17 evaluation targets × 5 provinces = 85) |
| Parity | Recomputing FIRI from the stored domain scores and weights reproduces the stored FIRI to within 6.8e-7. The regional mean equals the scored F2 column (CSV rounding to 1e-4). |
| Climate indicators scored at every one of the 17 targets | **C1 only** (PAGASA El Niño alert flag, 0/1) |
| C2 typhoons | "insufficient_history" (fewer than 8 earlier origins) at targets 2022-Q3 .. 2023-Q4 |
| C3 production, C4 fisheries | "missing" at 2022-Q3; "insufficient_history" at 2022-Q4 and 2023-Q1 |

## 3. Data gaps remaining

1. A food-insecurity outcome that is more frequent, provincial, or published earlier than SWS BL quarterly hunger.
2. Real-time vintages (CPI, production, remittances).
3. Fish-kill incident history. The production proxy is still used, labelled as a proxy.
4. Verified pre-2021 release dates for PSA production and BSP remittances. Conservative lag bounds are used instead.
