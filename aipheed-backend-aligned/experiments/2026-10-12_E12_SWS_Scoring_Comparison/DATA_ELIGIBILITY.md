# Data Eligibility (E12)

**Guard:** E12 (copy of the E9 guard, with read-only access to the E9 folder). Parquet reads are hash-pinned and filtered to `quarter <= 2025-Q4` during the scan; pre-2021 rows are dropped. **No protected or carrier file was opened.** The run manifest's access log lists only the allowlisted files.

| Data | Source | Coverage used | Publication-date status |
|---|---|---|---|
| H (SWS Balance Luzon) | SWS code registry (definition-A rounds); 2025 supplementary rounds shown in the regional layer only | 16 labelled quarters (2021-Q2 to 2025-Q4; no round in 2021-Q1 or 2022-Q1; 2025-Q2/Q3 have only input rounds) | Verified (one verified-single) |
| F (provincial food CPI YoY) | `psa_indicators.parquet` (hash `947be05f…`, byte-identical to the blob committed 2026-09-10) | **20 of 20 quarters complete for all five provinces** (2021-Q1 to 2025-Q4) | Proxy: national + 14 days, **unverified** (verified only for 2024-Q4) |
| D | Derived from F | 20 complete quarters | As F |
| S1 reference | E9 `s1_targets_2021_2025.csv` (read-only) | 80 rows | — |
| Origin inputs (Category B) | E9 `input_frame.csv` (read-only; equal to the frame rebuilt in E11) | 2021-Q2 to 2025-Q4 targets | As in E9 |

**Independent units:** 16 labelled quarters, i.e. 16 regional hunger observations. They are **not** 80 independent observations: the 5 provincial rows of a quarter share one H.

**Category B folds:**

- **7 evaluable:** 2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4.
- **9 skipped:** they have fewer than 8 eligible training quarters (0–7), listed in `OPTION_B_STANDARDIZED_GRID.csv`. **The minimum of 8 was not reduced.**
- **All 7 evaluable quarters were reused in E1–E11, so the results are exploratory.**

**Not used:**

- any 2026 value;
- news;
- rice;
- `food_cpi` index level;
- production files.
