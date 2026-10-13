# E11 Data Eligibility Audit

E11 used exactly the E9 data, rebuilt by E9's own code under the E11 access guard. The rebuilt input frame was checked equal to E9's `input_frame.csv`, and the run stops otherwise.

## 1. Sources (all hash-pinned; any mismatch stops the run)

| File | Used for | SHA-256 (prefix) | Eligibility |
|---|---|---|---|
| `data/processed/psa_indicators.parquet` | Provincial food CPI YoY (targets, provincial inputs) | `947be05f` | Byte-identical to git blob `03a4ec47` (committed 2026-09-10). Read with the scan filter `quarter <= 2025-Q4`; pre-2021 rows dropped. |
| `data/processed/features_fused.parquet` | Unemployment, poverty, headline CPI, food-minus-headline only | `0080dd5c` | Same guard. News columns never read. |
| `data/processed/labels.parquet` | Cross-check of S1 stress only | `eeb55983` | Same guard |
| SWS code registry + `sws_balance_luzon_2025_raw.csv` | Regional hunger and SWS publication dates | `1d7bd40a` (CSV) | Rounds ≤ 2025-Q4 for E11 |
| `cpi_final_month_release_dates.csv` | CPI release dates | `38ea7310` | — |
| `config/governing_model.json` | Read at module import (configuration) | `c9697b6b` | — |

**Guard log (run `20261012T145620Z`):** three parquet reads (120, 120 and 95 rows returned, each filtered to ≤ 2025-Q4) and three small file opens. **No protected file, carrier, production file, database, model file or transcript was opened.** Allowlist hashes were identical at the start and end.

## 2. Eligible window and labels

- **Data window:** 2021-Q1 to 2025-Q4. Nothing after 2025-Q4 is read, and nothing before 2021 is used.
- **S1 labels:** 16 complete quarters (80 province rows): 2021-Q2–Q4, 2022-Q2–Q4, 2023-Q1–Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4.
  - 2021-Q1 and 2022-Q1 have no SWS round.
  - 2025-Q2/Q3 have only supplementary (input-only) rounds.
- **Evaluation quarters:** 7 (2023-Q4 to 2025-Q4), each with ≥ 8 eligible training quarters. **All 7 were already used in E1–E9.**

## 3. Release dates

| Input family | Date basis | Status |
|---|---|---|
| SWS rounds | Registry publication dates | **Verified** (one round verified-single) |
| Provincial food CPI (and labels, which depend on it) | National release + 14 days | **Proxy, unverified** (verified only for 2024-Q4) |
| Regional headline CPI, food-minus-headline | National release date | **Verified** |
| LFS unemployment | Quarter end + 45 days | **Schedule, unverified** |
| Poverty | Release 2022-08-15 (2021 survey), 2024-08-15 (2023 survey) | Documented release (2024 date news-sourced) |
| `anchor_dev`, `lps_change`, `dev_change` (new in E11) | Built from labels published before the origin (Rule L1) | Inherit the label proxy dates |

**Availability check:** 0 violations in 95 frame rows; every non-null input is dated strictly before its origin (E10 audit). The three new E11 features are built only from labels whose publication dates precede the origin, and are unit-tested on synthetic data.

## 4. Missing values (inputs; NaN kept, never zero)

| Rows | Missing |
|---|---|
| Test rows (35) | **None** |
| Early training rows (2021-Q2 to 2023-Q3) | `last_published_stress` 20, CPI features 20, SWS 10, unemployment 5, poverty 30 (the 2018 survey is pre-2021), `anchor_dev`, `lps_change`, `dev_change` and the S1-rule input 20 each |

**Impossible zeros:** none found in unemployment, headline CPI or poverty.

## 5. Excluded inputs

| Input | Reason |
|---|---|
| News (FSSI, triggers, corpus) | The files are potential carriers of protected values, and E7 found 0/100 province-quarters with ≥ 5 relevant geocoded articles. Relevance, geography and coverage are not defensible. |
| Rice price | 3 residual forward-filled cells |
| `food_cpi` index level | No approved 2026 source, so a model using it could not run prospectively. Not derived from YoY. |
| Fuel, FX, remittances, typhoons, rain, ENSO | Their zero-fill correction needs blocked source tables |
| Population | Only a 2020 census snapshot exists, with no time variation; it cannot help a quarterly forecast. Not loaded. |

**Revisions:** CPI values are the current stored vintage, not the vintage available at each origin; earlier releases cannot be reconstructed from the approved files.
