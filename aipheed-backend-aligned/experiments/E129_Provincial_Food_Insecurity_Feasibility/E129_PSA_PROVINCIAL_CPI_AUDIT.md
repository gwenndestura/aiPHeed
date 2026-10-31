# E129 PSA provincial CPI and food-price audit

**Source and method**
- `runner/cpi_audit.py` → `out/cpi_audit.json`.
- Monthly PSA provincial YoY series (E40 file, 2021-01 .. 2026-09; the E118 cleaned bottom-30 CPI and retail rice).
- Complete quarters only: 23 quarters × 5 provinces.
- Decomposition: a two-way quarter × province split of the variance.

## Can the five series distinguish provinces?

| Series | Variance shared by all provinces (quarter) | Persistent province difference | Province × quarter (transient) | Median max−min spread | Median pairwise r | Highest province, count of 23 quarters |
|---|---|---|---|---|---|---|
| Food CPI YoY | **74 %** | **1 %** | 25 % | 4.1 pp | 0.80 | Rizal 7, Quezon 7, Batangas 5, Laguna 3, Cavite 1 |
| All-items CPI YoY | 71 % | 7 % | 22 % | 2.7 pp | 0.72 | Rizal 9, Laguna 6 |
| Food − headline gap | 70 % | 1 % | 29 % | 3.1 pp | 0.73 | Laguna 9, Quezon 6 |
| Bottom-30 % food CPI YoY | 69 % | 1 % | 30 % | 4.8 pp | 0.75 | Quezon 6, Rizal 5, Laguna 5 |
| Retail regular rice, price level | 81 % | 6 % | 13 % | ₱4.8 | 0.88 | Cavite 9, Batangas 9 |
| Retail regular rice YoY (19 quarters) | 81 % | 0 % | 19 % | 15.9 pp | 0.81 | Batangas 8 |

**How long a province's deviation from the five-province mean lasts** (food CPI YoY; pooled autocorrelation)

| Lag (quarters) | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Autocorrelation | 0.74 | 0.55 | 0.29 | −0.05 |

**Example (2024-Q4 to 2025-Q1).** Quezon's food inflation ran 4.6–5.2 pp above the five-province mean. By 2025-Q3 it was back at the mean.

## Findings

1. **The series do distinguish provinces, but only transiently.**
   - About a quarter of the variation in food inflation is province-specific in a given quarter. Spreads are typically 4 pp, at most 7 pp.
   - Almost none of it is a stable difference: the persistent province effect is 1 %.
   - The "highest" province changes in 73 % of quarters.
   - **Provincial price data can support province-specific signals one to two quarters ahead. They carry essentially no province identity beyond three quarters.**
2. **Most of the movement is common** (70–81 %). It is regional or national inflation, which any single regional indicator already captures.
3. **These are price conditions, not food insecurity.**
   - CPI measures the price change of a fixed basket.
   - It does not measure household income, access, or experienced hunger.
   - A high provincial food-inflation quarter is a **risk condition**, not a measured food-insecure quarter.
4. **Release timing is partly unverified.** CPI availability ledger (180 province-months):

   | Evidence class | V1 | V2 | P | U | N |
   |---|---|---|---|---|---|
   | Province-months | 22 | 10 | 61 | 79 | 8 |

   Verified release dates (V1 and V2) cover 32 of 180 (18 %). The provisional and undated classes need verification before strict point-in-time claims.
5. **Bottom-30 % CPI is nearly redundant** with food CPI (E118: r 0.94). It adds no independent province signal.
6. **Retail rice prices** are provincial and complete from 2021. Most of their variance (81 %) is the national rice cycle (2023–24 surge, 2025 decline).

## Consequence for the provincial objective

**Provincial food CPI is why the system can produce province-differentiated forecasts at all.**
- Most other inputs are national or regional (see `E129_FIVE_TRIGGER_GROUP_GEOGRAPHIC_AUDIT.csv`).
- But a model that forecasts provincial food CPI is forecasting **provincial food-price pressure**.
- Calling that provincial food insecurity requires a measured provincial food-insecurity outcome, which does not exist as a series (see `E129_TARGET_VALIDITY_DECISION.md`).
