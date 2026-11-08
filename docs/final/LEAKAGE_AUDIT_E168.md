# E168 leakage audit: every input, its publication rule, and empirical tests

2026-11-07. This answers the audit finding "feature publication dates not verified series by series".

**What "as-of" means here.** Each feature for a forecast issued at the start of quarter *i* is read from a panel row (province, *i*). That row was built only from values published before the start of quarter *i*.

## 1. Series by series

| Input (E168 column) | Source | Coded availability rule (code) | Official release practice | Margin |
|---|---|---|---|---|
| `cpi_food_yoy`, `cpi_rice_yoy`, `cpi_food_3m`, `cpi_food_accel`, `cpi_food_rel_nat`, `cpi_since` | PSA provincial CPI (monthly) | Month *m* usable from the first day of month *m* + 2 (`app/e150/panel.py`, `cpi_panel`) | PSA releases monthly CPI, provincial tables included, in the first week of the following month | about 3 weeks conservative |
| `c_agri_yoy`, `agri_since` | PSA palay and corn production (quarterly) | Quarter usable 45 days after quarter end (`app/e137/features.py`, `_published_quarters`) | PSA's quarterly crop production reports appear about 6 weeks after the quarter | about equal |
| `c_fish_yoy` (fish kill) | PSA fisheries production (quarterly) | 45 days after quarter end (same rule) | PSA's quarterly fisheries reports appear about 6–8 weeks after the quarter | 0 to 2 weeks **early** in some quarters; see §3 |
| `c_tc_4q`, `tc_rate_since` | IBTrACS tropical-cyclone tracks | Storms with track time before the issue date, in the last 365 days (`app/e137/features.py`) | Storm passage is known in real time (PAGASA bulletins) | real time |
| `c_rain_anom_6m`, `rain_since` | NASA POWER rainfall | 6 months ending the month before (issue − 30 days) (`app/e147/features.py`) | NASA POWER updates within days | about 1 month conservative |
| `c_soil_anom_3m`, `soil_since` | NASA soil moisture | 3 months ending 2 full months before the issue (`app/e146/soil.py`) | Updates within weeks | about 1 month conservative |
| `oni` | NOAA CPC Oceanic Niño Index | Usable 10 days after the period ends (`app/fi5/sources.py`, `oni`) | CPC publishes early in the following month | about equal |
| `unemp_rate`, `unemp_yoy`, `unemp_chg_since` | PSA Labor Force Survey (national) | Usable 45 days after month end (`app/fi5/sources.py`, `lfs`) | PSA releases LFS about 5–6 weeks after the reference month | about equal or conservative |
| `remit_yoy`, `remit_since` | BSP cash remittances (annual) | Year *y* usable from 15 February of *y* + 1 (`app/fi5/sources.py`, `remittances`) | BSP releases full-year remittances in mid-February | equal |
| `p_poverty`, `p_subsistence`, `p_poverty_gap` | PSA official poverty statistics (2018, 2021, 2023 rounds) | Year *y* usable from 1 January of *y* + 2 (`app/e147/features.py`, `gov_row`) | PSA releases full-year poverty statistics between August and December of *y* + 1 | about 1–5 months conservative |
| `p_density` | PSA census population and land area | Fixed census values | Census 2020 released 2021; POPCEN 2024 released 2025 | slow-moving; see §3 |
| `income_growth`, `income_rel` (regional consumption; available in the search) | PSA regional accounts | Year *Y* usable from Q3 of *Y* + 1 (`app/e154/model.py`, `available_year`) | PSA releases regional accounts in April–May of *Y* + 1 | about 1 quarter conservative |
| `h2` (SWS hunger signal) | SWS survey releases | Only releases published before the issue date (`app/e151/sws.py`, `published < q_start(i)`) | Release dates recorded per round | exact |
| 36 news columns (event shares, BERTopic topics, province, area and national streams) | Collected news stories | Only stories published before the issue date; BERTopic fitted only on stories before each origin (`app/e151/features.py`, `topics.py`) | Publication timestamp per story | exact |
| Survey anchors and training labels (FNRI HFIAS) | FNRI NNS/ENNS | A round is used from 6 quarters after its reference quarter (`ANCHOR_LAG = 6`, `app/e148/panel.py`; `M.released`) | FNRI disseminates provincial results about 12–18 months after fieldwork | equal or conservative |

## 2. Empirical tests

| Test | What it checks | Result |
|---|---|---|
| **Survey-label corruption** (`results.json` `leakage_max_abs_change`) | Unpublished survey rounds replaced with noise; the full procedure re-run | **0.0 change** |
| **Future-row corruption, all feature panels** (`app/e168/leakage_audit.py` → `feature_leakage_test.json`) | Every row dated after the origin, in the CPI, government, news, SWS, local and SunStar panels, replaced with noise; the full procedure re-run at ENNS 2018, 2019 and 2021 (Lead 1) | **0.0 change** in every forecast (72 rows; largest change in log-odds and in probability both exactly 0). **Passed.** |
| **Serving = validation feature path** (`tests/unit/test_e168_regenerate.py`) | The live forecast builds its features exactly like the validation | values identical (732 training rows and all live rows) |
| **Regeneration reproduces the approved forecast** | Staging 2026-Q4 from inputs published before 2026-10-01 | identical, 15 of 15 rows |

## 3. Residual risks (stated, not hidden)

- **Fisheries:** the 45-day rule can be up to about two weeks earlier than the slowest PSA fisheries releases. At any one issue, this affects at most one quarter of one input. Removing fisheries entirely changed nothing (the fisheries test in the final report: Brier difference +0.0009 [−0.0011, +0.0029]). So it cannot have produced any accuracy.
- **Revisions:** values are the latest published vintages, not the first releases (PSA revises CPI and production slightly). No first-release archive is public for these series. This is a minor and standard limitation.
- **Population density:** census figures are treated as fixed. They change little between censuses.
