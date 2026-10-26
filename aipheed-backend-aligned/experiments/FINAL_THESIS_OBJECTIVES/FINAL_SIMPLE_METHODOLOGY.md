# Final simple methodology

## In one paragraph

Each quarter, on its first day, aiPHeed forecasts whether each CALABARZON province will be at **high or low
food-insecurity risk** in the quarter that is starting. As Chapter I defines it, a province is high risk when regional
hunger (SWS, Balance Luzon) is above 11.3% **and** the province's food prices are rising unusually fast (PSA). The
forecast is the chance of the hunger condition (from the latest SWS survey) times the chance of the price condition
(from one LightGBM model that uses all 12 indicator families). The 142 cities and municipalities are then ranked for
attention by multiplying the province forecast by their poverty and population density.

## Diagram

```
  Published before the issue date (first day of the quarter)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ SWS hunger, Balance Luzon (H1)          PSA CPI food & headline (A1, A2)      │
 │                                         PSA rice (A3) · palay/corn (C3)        │
 │                                         fisheries (C4) · LFS (E1) · BSP (E2)   │
 │                                         PAGASA (C1) · IBTrACS (C2) · SAE/POPCEN│
 │                                         (V1) · news FSSI + GDELT (N1)          │
 └──────────────┬──────────────────────────────────────┬─────────────────────────┘
                │                                      │
                ▼                                      ▼
   π_H = chance hunger > 11.3%            π_P = LightGBM: chance of unusual
   (latest reading and its past            food-price pressure in the province
    errors)                                (12 families, trained on past quarters)
                │                                      │
                └───────────────►  P(HIGH) = π_H × π_P  ◄┘
                                          │
                       HIGH if ≥ 0.50 ─────┤
                                          ▼
                 Province risk (5)  ──►  × LGU vulnerability (0.6 poverty + 0.4 density)
                                          │
                                          ▼
                          LGU priority ranking (142) ── dashboard
```

## Steps

1. **Label the past.** For every quarter with an SWS round (2021+), mark each province HIGH if Balance Luzon hunger
   > 11.3% and its food YoY or food-minus-headline gap exceeds its 2021–22 60th percentile. 100 labelled
   province-quarters, 19 HIGH.
2. **Build features** at each issue date from data already published then (one table per lead; see
   `../FIRI_V2_DATA_AUDIT/INDICATOR_FEATURE_LINEAGE.md`).
3. **Train** the price LightGBM on quarters complete before the issue date only; pick its size by inner
   chronological cross-validation.
4. **Forecast** P(HIGH) for each province.
5. **Evaluate** walk-forward on 2023–2026 against always-LOW, same-information persistence, climatology, and the
   Chapter I logistic-regression and LightGBM comparators; apply the frozen reliability rule.
6. **Rank** LGUs from the province forecast.
7. **Serve** the forecast, its tested accuracy, data freshness and news context on the dashboard.

## What it can and cannot say

- Reliable one quarter ahead (accuracy 0.914 on 70 province-quarters, 14 quarters).
- Not reliable two or more quarters ahead.
- HIGH is a risk class built from a regional survey and provincial prices, not a measured provincial or municipal
  hunger rate.
- LGU values are a priority ranking.
