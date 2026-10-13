# Two-Layer Output Schema (E15 development prototype, version `e15-two-layer-0.1`)

**Machine-readable schema:** `TWO_LAYER_SCHEMA.json` (JSON Schema 2020-12, `additionalProperties: false` at every level).

**Builder:** `runner/two_layer.py`. **Example output:** `runs/20261013T024905Z/two_layer_output.json`.

**Not connected to the production API.**

## 1. Structure

```
{ schema_version, status, data_through, caveats[6],
  quarters: [ { quarter,
                regional_layer   { ... one record per quarter ... },
                provincial_layer { ... five provinces ... },
                legacy_layer     { ... secondary ... } } ] }
```

## 2. Regional layer (shown once per quarter; never per province)

| Field | Type | Meaning |
|---|---|---|
| `indicator` | string | "SWS involuntary hunger (total), % of families" |
| `scope` | const `"Balance Luzon"` | Survey area. It is wider than CALABARZON. |
| `status` | `AVAILABLE` or `NO_ROUND` | `NO_ROUND` when no SWS round was fielded in the quarter (2021-Q1, 2022-Q1) |
| `level_pct` | number or null | Mean of all eligible rounds assigned to the quarter |
| `rounds[]` | array | `round`, `value_pct`, `published` (date), `date_status` (verified or verified-single), `series` (`production` or `supplementary`) |
| `latest_publication_date` | date or null | When the quarter's last round was published |
| `trend` | object or null | `change_pct_points` against `compared_with_quarter`, the most recent earlier quarter with a value. `quarters_apart` records any gap (for example, 2022-Q2 is compared with 2021-Q4, 2 quarters apart). |

## 3. Provincial layer: relative food-price pressure

| Field | Type | Meaning |
|---|---|---|
| `label` | const | "relative food-price pressure" |
| `status` | `COMPLETE` or `INCOMPLETE_NO_D_OR_RANK` | `COMPLETE` only when all five provinces have F |
| `missing_provinces` | array | Provinces without F in the quarter |
| `five_province_mean_F_pct_unweighted` | number or null | Unweighted mean of the five F. Null if any F is missing. |
| `rank_rule` | string | The tie rule (§5) |
| `provinces[5]` | array, listed alphabetically | `food_inflation_yoy_pct` (F; null if missing, **never 0**); `relative_pressure_D_pp` (D = F − mean; null unless complete); `relative_pressure_rank` (1 = highest D; null unless complete); `tied_with` |

## 4. Legacy layer (secondary placement)

| Field | Type | Meaning |
|---|---|---|
| `label` | const | "legacy composite, not validated as food insecurity" |
| `placement` | const | "secondary" |
| `formula` | const | "S1 = H_A + 2 * D" |
| `threshold`, `threshold_display` | 10.84335, "10.843" | Recorded value of τ0. On all 80 eligible rows, 10.843, 10.8433333 and 10.84335 give identical labels (runtime check). |
| `rule` | string | HIGH if S1 > threshold (strict), else LOW |
| `H_A_production_rounds_pct` | number or null | Mean of the production-series (`definition_A`) rounds only, as S1 was defined in E9–E13 |
| `status` | `AVAILABLE`, `UNAVAILABLE_NO_PRODUCTION_ROUND` or `UNAVAILABLE_INCOMPLETE_PROVINCES` | `UNAVAILABLE_NO_PRODUCTION_ROUND` applies to 2025-Q2 and 2025-Q3 |
| `provinces[5]` | array | `S1` and `label` (HIGH, LOW or null) |

## 5. Rules

| Rule | Specification |
|---|---|
| **Missing data** | No imputation. A missing F is null, and that quarter has no mean, no D, no rank and no legacy S1. |
| **Ties** | D values equal after rounding to 9 decimals share the **lowest rank of the group**, and the next rank is skipped (1, 2, 2, 4). Tied provinces are named in `tied_with`. Uniform conditions give every province rank 1. |
| **Regional once** | `level_pct` appears exactly once per quarter. No provincial record has a hunger field. |
| **Wording** | No key or string may contain "food insecure" (as an adjective) or "risk". The only mention of food insecurity is in the mandated legacy label, "not validated as food insecurity". The builder and the report renderer both check this. |
| **Caveats** | All six caveats are always included in `caveats[]` and in any rendered view (§7). |

## 6. CSV layout (`runs/<run>/`)

| File | One row per | Columns |
|---|---|---|
| `regional_layer.csv` | quarter | quarter, scope, status, level_pct, n_rounds, series, latest_publication_date, trend_change_pct_points, compared_with_quarter, quarters_apart |
| `provincial_layer.csv` | quarter × province | quarter, status, province_code, province, food_inflation_yoy_pct, five_province_mean_F_pct_unweighted, relative_pressure_D_pp, relative_pressure_rank, tied_with |
| `legacy_layer.csv` | quarter × province | quarter, status, province_code, province, H_A_production_rounds_pct, S1, label, threshold |

## 7. Caveats carried by every output

1. A ranking always yields a top province, even when conditions are uniform across provinces.
2. The five-province mean is unweighted: each province counts equally, regardless of population.
3. Balance Luzon is wider than CALABARZON. The regional hunger value is not a provincial measurement and is shown once per quarter.
4. No independent provincial outcome exists. Neither layer has been validated against a measured provincial outcome.
5. D and its rank describe relative food-price pressure only.
6. The legacy composite (S1) is shown for continuity, in a secondary position, and is not validated.
