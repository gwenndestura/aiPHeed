# Quarterly data quality audit

Per-province, per-feature detail: `backend/data/e150/out/feature_availability.csv`. File hashes: `backend/data/e150/out/data_manifest.csv`. Labels: `docs/e147/DATA_INVENTORY.md`.

## By trigger group (mean over the five provinces, issues 2013-Q1 to 2026-Q4)

| Group | Feature | Geography | Frequency | Missing | Quarters changed | Release rule |
|---|---|---|---|---|---|---|
| Market | `cpi_food_yoy`, `cpi_food_3m`, `cpi_food_accel`, `cpi_food_rel_nat` | **Province** | Monthly | 0.00 | 0.98 | First day of second following month |
| Market | `cpi_rice_yoy` | **Province** | Monthly | 0.00 | 0.98 | Same |
| Market | `m_food_threshold_rel` | Province | Triennial | 0.00 | 0.04 | Survey year + 2 |
| Climate | `c_soil_anom_3m` | Province centroid | Monthly | 0.00 | 0.98 | 2-month delay |
| Climate | `c_rain_anom_6m` | Province centroid | Monthly | **0.20** | 0.98 | 1 to 2 months; **file ends in 2023** |
| Climate | `c_tc_4q` | 150 km of centroid | Event | 0.00 | 0.49 | Before issue |
| Climate | `c_agri_yoy`, `c_fish_yoy` | Province | Quarterly | 0.00 | 0.80 | E137 publication rule |
| Climate | `oni` | National | Monthly | 0.00 | 0.98 | FI5 rule |
| Employment | `unemp_rate`, `unemp_yoy` | **National** | Quarterly rounds | 0.00 | 0.98 | FI5 rule |
| Employment | `unemp_region` | Region | Annual, 2021 on | **0.79** | 0.17 | Following year |
| Remittances | `remit_yoy` | **National** | Annual | 0.00 | 0.25 | FI5 rule |
| Remittances | `remit_q_yoy` | **National** | Quarterly, 2022 on | **0.68** | 0.94 | About 2 months |
| Poverty | `p_poverty`, `p_subsistence`, `p_poverty_gap` | Province | Triennial | 0.00 | 0.09 | Survey year + 2 |
| Poverty | `p_density` | Province | Census | 0.00 | 0.02 | Census + 2 |
| News | `fv2_*` | Province sentence | By publication | 0.00 (`fv2_fssi_chg` 0.07) | 0.85 to 0.98 | Before issue |

## What improved

**Market is now a real quarterly provincial signal.** PSA monthly CPI by province, 1994 to 2026, replaces annual values that were stale after 2018.

* **Food-only:** `01.1 FOOD` and rice only, never "food and non-alcoholic beverages".
* **Comparability:** year-on-year is computed inside one base (2012 base through December 2018, 2018 base after). The indices are never spliced.
* **Gap:** Mountain Province, Occidental Mindoro and Oriental Mindoro have no CPI match. They stay missing, with no imputation.

## What did not improve

| Limit | Reality | Consequence |
|---|---|---|
| **Employment by province** | OpenSTAT's LFS tables reviewed are national. A provincial table exists only for 2021 to 2025 and was not usable as history | **National values cannot separate provinces, and no such claim is made** |
| **Remittances by province** | No provincial history held. PSA FIES 2023 gives one year only | Same |
| Poverty | Slow; rounds in 2015, 2018, 2021, 2023 | Mostly locational, not a quarterly signal |
| Rain | The acquired file ends in 2023 | Shown as missing live, not filled |

**No value is interpolated, forward-filled or extrapolated as an observation.** Inputs carried at their latest release are real, dated values, and each row states the release rule. LightGBM handles missing values natively. Staleness and missingness appear per province in `issue/province_trace.json`.

## Survey timing

Survey reference quarters are approximated as Q3, and anchor availability as 6 quarters after reference. 2021 standard errors are approximated at 3 points because the Heat Map doesn't publish them. Each is a stated assumption, not verified fieldwork data.

## Label checks

* **Workbook:** the 2018 and 2019 "moderate-to-severe" values are HFIAS moderate only.
* **Heat Map:** 2015 has mislabelled duplicate moderate and severe rows; any-level is clean. Two mismatches: Cebu 2019, Basilan 2013. One or more released city rows have no value and are dropped.
* **Coverage collected but incomplete:** 7 of 152 BusinessWorld phrase queries did not finish, and a few full-text batches returned 502 or 504.
