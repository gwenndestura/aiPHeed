# aiPHeed Two-Layer View: Development Mock (2025-Q4)

> **Development prototype.** It is built from eligible data through 2025-Q4 and is **not connected to the dashboard or the production API**. It shows measured values, not forecasts. Source run: `runs/20261013T024905Z/`.

## 1. Regional context: hunger in Balance Luzon (one value for the region)

| Item | Value |
|---|---|
| Hunger, 2025-Q4 | **16.7% of families** |
| Scope | Balance Luzon (wider than CALABARZON) |
| Round | November 2025 SWS Survey: 16.7%, published 2026-01-14 (verified-single, production series) |
| Change | -7.1 points against 2025-Q3 (1 quarter earlier) |

## 2. Provincial layer: relative food-price pressure

Unweighted five-province mean food inflation, 2025-Q4: **1.32%**. D is each province's food inflation minus this mean.

| Rank (1 = highest) | Province | Food inflation, YoY % | D, points | Tied with |
|---|---|---|---|---|
| 1 | Laguna | 2.77 | +1.45 | — |
| 2 | Cavite | 1.90 | +0.58 | — |
| 3 | Rizal | 1.23 | -0.09 | — |
| 4 | Quezon | 1.20 | -0.12 | — |
| 5 | Batangas | -0.50 | -1.82 | — |

**Ranking by quarter** (1 = highest relative pressure; — means no rank, because a province is missing):

| Province | 2025-Q1 | 2025-Q2 | 2025-Q3 | 2025-Q4 |
|---|---|---|---|---|
| Batangas | 4 (-2.0) | 3 (-0.3) | 4 (-0.7) | 5 (-1.8) |
| Cavite | 3 (-0.7) | 4 (-0.5) | 1 (+0.7) | 2 (+0.6) |
| Laguna | 2 (-0.3) | 1 (+1.5) | 2 (+0.6) | 1 (+1.4) |
| Quezon | 1 (+5.2) | 2 (+1.2) | 3 (+0.1) | 4 (-0.1) |
| Rizal | 5 (-2.1) | 5 (-2.0) | 4 (-0.7) | 3 (-0.1) |

## 3. Regional hunger by quarter, 2021–2025

| Quarter | Hunger, % | Change, points (against) | Rounds | Series | Last published |
|---|---|---|---|---|---|
| 2021-Q1 | — | — | 0 | no round | — |
| 2021-Q2 | 15.3 | — | 2 | production | 2021-07-28 |
| 2021-Q3 | 10.3 | -5.0 (2021-Q2) | 1 | production | 2021-12-06 |
| 2021-Q4 | 9.2 | -1.1 (2021-Q3) | 1 | production | 2022-03-25 |
| 2022-Q1 | — | — | 0 | no round | — |
| 2022-Q2 | 11.8 | +2.6 (2021-Q4) | 2 | production | 2022-09-10 |
| 2022-Q3 | 9.6 | -2.2 (2022-Q2) | 1 | production | 2022-10-29 |
| 2022-Q4 | 11.3 | +1.7 (2022-Q3) | 1 | production | 2023-01-19 |
| 2023-Q1 | 8.7 | -2.6 (2022-Q4) | 1 | production | 2023-05-11 |
| 2023-Q2 | 11.3 | +2.6 (2023-Q1) | 1 | production | 2023-08-02 |
| 2023-Q3 | 10.3 | -1.0 (2023-Q2) | 1 | production | 2023-11-20 |
| 2023-Q4 | 14.3 | +4.0 (2023-Q3) | 1 | production | 2024-01-22 |
| 2024-Q1 | 15.3 | +1.0 (2023-Q4) | 1 | production | 2024-04-30 |
| 2024-Q2 | 19.6 | +4.3 (2024-Q1) | 1 | production | 2024-07-23 |
| 2024-Q3 | 18.1 | -1.5 (2024-Q2) | 1 | production | 2024-10-17 |
| 2024-Q4 | 25.3 | +7.2 (2024-Q3) | 1 | production | 2025-01-14 |
| 2025-Q1 | 24.0 | -1.3 (2024-Q4) | 1 | production | 2025-03-29 |
| 2025-Q2 | 16.1 | -7.9 (2025-Q1) | 2 | supplementary | 2025-08-15 |
| 2025-Q3 | 23.8 | +7.7 (2025-Q2) | 1 | supplementary | 2025-11-05 |
| 2025-Q4 | 16.7 | -7.1 (2025-Q3) | 1 | production | 2026-01-14 |

## 4. Legacy composite (secondary)

*legacy composite, not validated as food insecurity.* S1 = H_A + 2 * D; HIGH if S1 > threshold (strict), else LOW, threshold 10.843. H_A (production-series rounds) = 16.7. Status: AVAILABLE.

| Province | S1 | Legacy label |
|---|---|---|
| Batangas | 13.06 | HIGH |
| Cavite | 17.86 | HIGH |
| Laguna | 19.59 | HIGH |
| Quezon | 16.46 | HIGH |
| Rizal | 16.53 | HIGH |

Across 2021–2025 the legacy label is HIGH in 56 of 80 province-quarters. It is unavailable in quarters without a production-series SWS round.

## 5. Caveats (always shown)

- A ranking always yields a top province, even when conditions are uniform across provinces.
- The five-province mean is unweighted: each province counts equally, regardless of population.
- Balance Luzon is wider than CALABARZON; the regional hunger value is not a provincial measurement and is shown once per quarter.
- No independent provincial outcome exists; neither layer has been validated against a measured provincial outcome.
- D and its rank describe relative food-price pressure only.
- The legacy composite (S1) is shown for continuity, in a secondary position, and is not validated.

## 6. What this view deliberately does not show

- **No province is described in terms of household hunger or need.** No provincial outcome exists to support that.
- **The regional hunger value is never repeated as a provincial value.**
- **No D or rank is shown for a quarter with a missing province.** Missing values are never filled with 0.
- **No forecast is shown.** Forecasts await the prospective protocol (`PROSPECTIVE_VALIDATION_PROTOCOL.md`).
