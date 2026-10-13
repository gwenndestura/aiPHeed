# E9: Data Eligibility and Feature-Availability Audit

## 1. Eligible data

**Window: 2021-Q1 to 2025-Q4.**

- No pre-2021 row is used: the study window.
- No row after 2025-Q4 is read: the protected period, enforced by the read-time row filter.
- **No 2026 value of any kind enters E9.** 2026 SWS rounds in the code registry are filtered out before use.

| Source | Provenance | Eligibility evidence |
|---|---|---|
| `psa_indicators.parquet` (food CPI YoY) | PSA OpenStat provincial food CPI, 2018 base. Byte-identical to git blob `03a4ec47…`, committed 2026-09-10. | Hash matches the E1–E7 records. Coverage beyond 2025-Q4 is **never read** (scan filter). Rows returned: 120, of which 2021–2025 used. |
| `features_fused.parquet` (4 columns) | Aligned pipeline output (2026-10-08). Columns: LFS unemployment, PSA poverty, regional headline CPI, food-minus-headline. | Same guard. News columns are **not projected** (never decoded). |
| `labels.parquet` | Aligned pipeline labels | Cross-check only (80/80 match S1) |
| SWS code registry (`sws_hunger_fetcher.SWS_BAL_LUZON_VERIFIED`) + `sws_balance_luzon_2025_raw.csv` | SWS releases with source URLs; supplementary 2025 rounds collected 2026-10-09 | Rounds ≤ 2025-Q4 only. The constant is loaded at import; entries after 2026-Q2 are excluded by the module's coverage end and are **not inspected**. |
| `cpi_final_month_release_dates.csv` | National CPI release dates per final month | Hash-pinned |

**Excluded inputs and why:**

| Input | Why excluded |
|---|---|
| News (FSSI, triggers) | Potential carriers; E7 sufficiency 0/100 |
| Rice price | 3 forward-filled cells |
| `food_cpi` index level | No approved 2026 source, so such a model could not be used prospectively. **No index level was derived from YoY.** |
| Fuel, FX, remittances, typhoons, rain, ENSO | Their zero-fill correction needs blocked source tables |

**No exact 0.0 values** were found in unemployment, headline CPI or poverty, so nothing was set to missing.

## 2. Availability at each test origin (from `runs/20261012T140816Z/input_frame.csv`)

| Target | Origin | SWS input (round quarter, published, status, age) | Last published label (quarter, date, status) | Provincial CPI ref. quarter (release, status) | Regional CPI release | Unemployment available (schedule) | Poverty survey |
|---|---|---|---|---|---|---|---|
| 2023-Q4 | 2023-10-01 | 2023-Q2, 2023-08-02, verified, 2 | 2023-Q2, 2023-08-02, proxy | 2023-Q2 (2023-07-19, proxy) | 2023-07-05, verified | 2023-08-15 | 2021 |
| 2024-Q1 | 2024-01-01 | 2023-Q3, 2023-11-20, verified, 2 | 2023-Q3, 2023-11-20, proxy | 2023-Q3 (2023-10-19, proxy) | 2023-10-05, verified | 2023-11-15 | 2021 |
| 2024-Q2 | 2024-04-01 | 2023-Q4, 2024-01-22, verified, 2 | 2023-Q4, 2024-01-22, proxy | 2023-Q4 (2024-01-19, proxy) | 2024-01-05, verified | 2024-02-15 | 2021 |
| 2024-Q3 | 2024-07-01 | 2024-Q1, 2024-04-30, verified, 2 | 2024-Q1, 2024-04-30, proxy | 2024-Q1 (2024-04-19, proxy) | 2024-04-05, verified | 2024-05-16 | 2021 |
| 2024-Q4 | 2024-10-01 | 2024-Q2, 2024-07-23, verified, 2 | 2024-Q2, 2024-07-23, proxy | 2024-Q2 (2024-07-19, proxy) | 2024-07-05, verified | 2024-08-15 | 2023 |
| 2025-Q1 | 2025-01-01 | 2024-Q3, 2024-10-17, verified, 2 | 2024-Q3, 2024-10-18, proxy | 2024-Q3 (2024-10-18, proxy) | 2024-10-04, verified | 2024-11-15 | 2023 |
| 2025-Q4 | 2025-10-01 | 2025-Q2 (June 2025), 2025-08-15, **verified-single**, 2 | 2025-Q1, 2025-04-18, proxy | 2025-Q2 (2025-07-18, proxy) | 2025-07-04, verified | 2025-08-15 | 2023 |

**Every input date is before its origin.** This is enforced in code, and every value in the table is earlier than the origin.

**Date status:**

- **Proxy, unverified:** every provincial CPI date (national + 14 days) and every label date that depends on it.
- **Schedule, unverified:** unemployment.
- **Verified:** SWS (one verified-single) and regional CPI.
- **Documented release:** poverty (2022-08-15; 2024-08-15, the latter from a news-sourced date).

**Consequence:** E9 is a **development-protocol historical simulation with proxy-dated inputs**. It supports no leakage-verified claim.

## 3. Missing values

| Rows | Missing | Kept as |
|---|---|---|
| Test rows (35) | **none** in any input | — |
| Training-only rows (2021-Q2–2023-Q3) | Early quarters lack lagged inputs (`last_published_stress` 20, CPI features 20, SWS 10, unemployment 5, poverty 30, because the 2018 survey is pre-2021) | **NaN**; never zero |

The training-only filter (more than 50% missing or constant) dropped **poverty** from M3 in the first two folds only.

## 4. Leakage checks performed

| Check | Result |
|---|---|
| Training labels per fold restricted to Rule-L1-published quarters (label vault; raises otherwise) | Passed (no exception) |
| Test outcomes revealed only after `predictions.csv` was written and hashed (`67b92ae4…`) | Passed |
| τ0 from labels published before the first test origin | 8 quarters, all ≤ 2023-Q2 |
| No feature from the target quarter: CPI and unemployment reference T−2; SWS and labels published before the origin | By construction; dates in §2 |
| Preprocessing, filtering and calibration within each training fold only | Yes. Calibration was **never** supportable (< 8 inner quarters); probabilities are uncalibrated. |
| Model selection used only the selection quarters (≤ 2024-Q4) | Yes (`selection.json`) |
| No quarter after 2025-Q4 anywhere | Asserted in the runner |

**Not leakage-free in one respect: reuse.** The design of the arms and settings was informed by E1–E7, which evaluated these same test quarters. The results are therefore **exploratory**.
