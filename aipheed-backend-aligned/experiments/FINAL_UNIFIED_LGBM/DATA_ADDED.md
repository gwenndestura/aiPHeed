# Data added for the unified model

## World Bank Commodity Price Data (Pink Sheet), monthly

| Item | Value |
|---|---|
| Publisher | World Bank, Prospects Group |
| File | `data/raw/pinksheet_monthly.xlsx` (sheet "Monthly Prices"), SHA-256 `ea1c3508…a5b33154` |
| Link | https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx, found on https://www.worldbank.org/en/research/commodity-markets, downloaded 2026-10-26 |
| Parsed to | `data/pinksheet_monthly.csv` by `runner/pinksheet.py` (standard library xlsx reader) |
| Series kept | Thai 5% rice, Viet Namese 5% rice, US HRW wheat, maize, palm oil, soybean oil, world sugar, urea, crude oil average |
| Coverage used | 2018-01 to 2026-09 (2018–2020 only as year-earlier bases for 2021+ YoY; no pre-2021 outcome is used) |
| Release timing | monthly, around the 2nd–3rd business day of the following month; the model uses months ≤ month 2 of the origin quarter, published before the issue date |
| Vintage | latest release (October 2026). Commodity spot prices are rarely revised; the vintage is disclosed |

**Why this data.** The model fails at Lead 2+ because provincial food inflation two or more quarters ahead is not
predictable from domestic data published by the issue date. The Philippines imports a large share of its rice, and
world rice and cereal prices pass through to domestic prices with a lag of one to two quarters. They are the most
credible openly available leading indicator of food-price pressure.

**Families.** World rice YoY and 3-month change → A3 (rice prices); cereal YoY → A1 (food-price pressure); crude oil
YoY → A2 (headline inflation); urea YoY → C3 (production inputs). No new family is created; the 12 FIRI v2 families stay
the model's structure.

## Four SWS areas for the hunger-condition model (HG)

No new collection: the verified non-commissioned SWS series (`FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv`)
already holds NCR, Balance Luzon, Visayas and Mindanao. Each area's reading is a real measurement of that area. The HG
model learns from all four areas how hunger above 11.3% persists or changes, and is evaluated only on Balance Luzon.
No area's reading is ever used as a CALABARZON or provincial outcome.

## Searched, not usable

- Provincial or municipal food-insecurity outcomes 2021+ (CBMS 2024 LGU tables; FNRI provincial FIES beyond 2021/2023):
  not openly published.
- Pre-2021 SWS and CPI history: outside the primary window (sensitivity only, E114).
