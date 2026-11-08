# Design fixes implemented (corrected experimental data pipeline)

| | |
|---|---|
| Branch | `aiPHeed/corrected-data-pipeline`, from audit commit a0f469b (local only) |
| Folder | `aipheed-backend-aligned/experiments/CORRECTED_PIPELINE/` |
| Commit hash | in `IMPLEMENTATION_TEST_RESULTS.md` |

**Unchanged.**
- **Raw data:** every input's SHA-256 is recorded before and after the run in `out/pipeline_manifest.json`; the run stops if any changes.
- **Production:** the served model and its outputs, the dashboard and API, and the 12 FIRI indicators.
- **Earlier work:** the E109-E116 experiments and the audit.

**Nothing was trained.**

**Reproduce.**

```bash
cd aipheed-backend-aligned/experiments/CORRECTED_PIPELINE/runner
python pipeline.py      # out/provincial_profile.csv, out/national_context.csv, out/regional_forecast_panel.csv,
                        # out/indicator_registry.csv, out/remittances_quarterly_corrected.csv, out/pipeline_manifest.json
python reports.py       # CORRECTED_DATA_DICTIONARY.csv, CORRECTED_INDICATOR_COVERAGE.csv,
                        # POINT_IN_TIME_VALIDATION.csv, GEOGRAPHICAL_ALIGNMENT_RESULTS.csv
```

(Use the backend venv, so that `app.ml.inference.firi` and `pagasa_climate_fetcher` are importable.)

## Architecture: three separate products, never combined into one prediction

| Product | File | Content | What it supports |
|---|---|---|---|
| **A. Regional hunger forecasting data** | `out/regional_forecast_panel.csv` | SWS hunger by area (NCR, Balance Luzon, Visayas, Mindanao), 1998-2026, origin × lead (872 rows), with area-level CPI, fisheries and palay, and national ENSO, typhoons, unemployment and news. Status columns on each feature. | regional hunger forecasting at Leads 1-2 |
| **B. Provincial vulnerability profile** | `out/provincial_profile.csv` | 5 provinces × 23 origins (2021-Q1 to 2026-Q3), 115 rows: prices, rice, typhoon exposure, palay/corn, fisheries, annual provincial employment, news coverage, poverty profile. **No outcome and no forecast.** | describing relative provincial vulnerability |
| **C. National and regional context** | `out/national_context.csv` | one row per origin: El Niño (national), unemployment change (national), OFW remittances (national), Balance Luzon hunger outlook (regional) | context. These values are no longer copied into five provincial rows. |
| Indicator registry | `out/indicator_registry.csv` | each of the 12 indicators: FIRI domain, trigger domain, its role in A, in B, and in provincial forecasting ("not validated (no provincial outcome)") | — |

**Status vocabulary for every value:**
- `verified`
- `rule_unverified`
- `unavailable_at_issue`
- `not_collected`
- `insufficient_data`

**Strict and provisional use.**
- A strict point-in-time evaluation keeps only `verified` values.
- A provisional analysis may use `rule_unverified` values, but must label itself provisional.
- No value is shifted, imputed or zero-filled.

## Fixes, by audit issue

| Audit # | Issue | Fix implemented | Evidence it works |
|---|---|---|---|
| 4 | Price thresholds computed from 2021-22 data, used for earlier issues | `A1_food_asof`, `A1_gap_asof`, `A2_asof`: the same projections minus the P60 of quarters complete and published before each issue (expanding from 2021-Q1, minimum 4 quarters, else `insufficient_data`). The frozen values are kept beside them (`*_frozen`). | At issue 2023-01-20, the first with exactly 2021-Q1 to 2022-Q4 published, the as-of thresholds equal the frozen ones exactly (test). 20 early rows are `insufficient_data` instead of using future data. |
| 3 | 2018=100 CPI before it was public | `cpi_vintage_status` flags the 25 profile rows issued before 2022-06-07. The regional panel flags back-cast CPI before 2018 (592 rows). | flags tested |
| 2 | Archived vs final CPI values | `cpi_release_status`: `verified` only where an archived PSA release of that province-month predates the issue (35 of 115 rows). The 3 revised months are listed in the audit. As-released index values are not in the repository, so they are not reconstructed. | — |
| 6 | Poverty used before publication | V1 moved out of the dynamic features into a dated structural profile (`V1_status`: `unavailable_at_issue` before 2025-07-01 for 85 rows), with source and reference years kept. | tested |
| 5 | Unverified lags (rice, palay, fisheries, employment, remittances) | No shift applied. Each value is marked `rule_unverified` and excluded from strict evaluation. | coverage table |
| 9 | Remittances national, copied to provinces; model panel stale | E2 moved to `national_context` (one national value per quarter). Quarterly series from the BSP-release news ledger to 2026-Q2, with each quarter's first dated publication: `verified` only where every needed report is dated before the issue (2 quarters). Year-later and derived values are `rule_unverified`. | Corrected E2 equals the served stack's E2 at every origin (difference 0). The E107 `bsp_macro.parquet` panel differs from the ledger by up to 0.79 bn per quarter (both columns kept in national_context.csv). |
| 8 | Employment national only | National unemployment change kept in `national_context`. Owner's annual provincial file added at **annual** resolution (value of a year earlier than the issue year, `rule_unverified`; 2024 unemployment derived as 100 − employment rate and flagged). | tested: reference year < issue year |
| 7 | Typhoon counts identical across provinces | Investigated. Counts are computed per province (storms within 300 km of each centroid). The five centroids are closer than 300 km, so identical counts are genuine shared exposure, not copying. Added `C2_tc_local_100km` from the IBTrACS raw file. Rainfall stays unavailable (column empty; not interpolated). | 100 km counts differ across provinces in 17% of quarters (vs 35% at 300 km), mostly zero-storm quarters |
| 10 | News missing values | `N1_status` separates `observed` (20), fewer than 5 admitted articles (42) and 0 admitted articles with the corpus collected (53). Missing is never zero. | tested |
| 11, 12 | Hunger copied to provinces; circular price target | Balance Luzon hunger only in `national_context` and as the regional target in product A. The provincial profile has no outcome. | tested: no E2/C1/H1 column in the provincial profile |
| 13 | 11.3% presented as a threshold | The registry and products use hunger levels. No product applies 11.3. | — |
| 16 | 2026-Q3 typhoons incomplete | kept missing with `C2_status = incomplete` | tested |

## Feature engineering (only where the data support it)

**Kept from the existing builders:**
- YoY and 1-year changes (CPI, fisheries, palay);
- 3-month food momentum;
- hunger history (latest reading, gap to known mean, last change, staleness);
- national ENSO and typhoon changes.

**Added:**
- origin-available thresholds;
- local (100 km) typhoon exposure;
- annual provincial employment;
- per-value status.

**Not added**, because the data cannot support them without new observations:
- moving averages and volatility of quarterly provincial series (too few quarters from 2021);
- seasonal components;
- new cross-domain products (E116 found none useful).

**Consistency between training and inference.** The same functions (`asof_thresholds`, `cpi_status`, `remittance_series`) build every historical origin and the latest origin. A test recomputes the latest origin's corrected values from those functions.

**Not claimed:** that any indicator now contributes more predictive value. That needs a separate, pre-registered evaluation.
