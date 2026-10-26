# Indicator-to-feature lineage

How each FIRI v2 indicator family travels from its published source to a column of the CH1-LGBM price model, and
then to the served dashboard. Code paths are relative to the repository root.

## Path for every column

```
published source ──(runner/pull_public.py: fresh pull, raw kept in data/raw/)──► reconcile.py (held vs fresh)
held repo data (E107 data_inputs, backend/data/...) ──► audit_build.corrected_data()  (E2 rebuilt, C2 recomputed, A3 2026-Q3 complete)
      ──► E107 e107_lib.feature_table(k, origins, d, x)     13 columns, one row per (origin t, province)
      ──► FINAL_THESIS_OBJECTIVES ch1_lib.build_X(k, ...)  H1 → corrected π_H; + A_mom, G_pri_yoy, NG_gap_price
      ──► out/training_table_lead{k}.csv                    (audited training table, with issue-date bookkeeping)
      ──► ch1_lib.run_lead(k, X)                             expanding-window LightGBM π_P × π_H, scored on T43c
      ──► out/ch1_audited/predictions_lead{k}.csv, results.json, sealed_prospective.csv
      ──► FINAL_THESIS_OBJECTIVES runner/export_ch1.py ──► backend/data/ch1_engine/rows.csv, evaluation.json
      ──► backend/app/ml/inference/ch1_system.py ──► /api/v1/provinces, /explainability, /final/risk/*  ──► dashboard
```

The served rows are checked equal to the evaluated predictions (`export_ch1.py` asserts it;
`backend/tests/integration/test_api_ch1_risk.py::test_served_lead1_rows_equal_the_evaluated_predictions`).

## Per family

| Family | Raw field | Transformation at origin t, lead k | Model column(s) | Available at issue date O(t) because |
|---|---|---|---|---|
| A1 | CPI food and all-items index, province, monthly | latest published index held flat to the target months of t+k; YoY against the same months a year earlier; minus the province's frozen 2021–22 P60 food and gap thresholds. A_mom = 100 × (log food index month m0 − log m0−3) | `A1_food`, `A1_gap`, `A_mom` | uses months ≤ month 2 of quarter t; PSA releases about day 5 of the following month |
| A2 | CPI all-items YoY | latest two published months minus the province's 2021–22 headline P60 | `A2` | as A1 |
| A3 | wholesale regular-milled rice price, monthly | quarterly mean; YoY % of t−1 vs t−5 | `A3` | quarter t−1 complete before O(t) |
| V1 | 2021 SAE poverty, POPCEN 2024, land area | 0.6 × min-max poverty + 0.4 × min-max density across the 5 provinces | `V1` | static profile (FIRI Amendment 1) |
| C1 | PAGASA ENSO items | 1 if the latest El Niño item before O(t) is an Alert or Advisory in force | `C1` | item dates before O(t) |
| C2 | IBTrACS 6-hourly fixes | distinct storms with a fix within 300 km of the area-weighted province centroid in quarter t | `C2` | quarter t ends before O(t) |
| C3 | PSA palay, corn production | −(lower of palay and corn YoY %, t−1 vs t−5) | `C3` | quarter t−1 |
| C4 | PSA fisheries production | −(fisheries YoY %, t−1 vs t−5) | `C4` | quarter t−1 |
| E1 | PSA LFS unemployment rate | quarter mean t−1 minus t−5 (points) | `E1` | months of t−1 |
| E2 | BSP cash remittances (rebuilt quarterly levels) | −(YoY %, t−1 vs t−5) | `E2` | quarter t−1; BSP releases about 45 days after quarter end, before O(t) |
| N1 | admitted headlines (FSSI-v3), GDELT price-news composite, GDELT gap features | FSSI-v3 bias-weighted mean intensity (NaN if < 5 headlines); GDELT price-news YoY; GDELT price-news between SWS fieldwork end and O(t) | `N1`, `G_pri_yoy`, `NG_gap_price` | items with publication time before O(t) (`news_latest_published` column) |
| H1 | SWS Balance Luzon hunger, verified non-commissioned rounds | π_H = Φ((h_last − 11.3)/σ), σ from earlier same-true-horizon errors (≥ 4 errors, else 4.0) | `H1` (= π_H) and the π_H factor | rounds whose publication date is before O(t) (`sws_newest_published` column) |

## Target lineage (not a feature)

T43c(p, q) = [H_BL(q) > 11.3] AND [food YoY_p(q) > P60food_p OR food − headline_p(q) > P60gap_p]. H_BL comes from the
verified SWS series; YoY from the same PSA CPI table; thresholds from `E40_SWS_CPI_Tiers/label_spec.json` (frozen
2026-10-15). Labels for target quarters 2026-Q4 and later are absent from every training table (checked: 0 non-null).

## Columns in the audited training tables

`origin, issue_date, province_code, target_quarter, lead_days, sws_newest_q, sws_newest_published, true_horizon,
psa_newest_month, news_latest_published` (bookkeeping) · the 16 model columns above · `y` (T43c), `price`, `hunger`
(the two conditions), `H` (target-quarter Balance Luzon hunger), `F`, `HL` (target-quarter food and headline YoY).
115 rows per lead (23 origins × 5 provinces); labelled rows: 100 (Lead 1), 95, 90, 85 (Lead 4).
