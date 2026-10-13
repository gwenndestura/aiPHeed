# Data Authorization Record and Approved-File Allowlist (E17 v3)

## 1. Authorization status

**No authorization for 2026 data has been given.** Your brief says it is not itself authorization, and none was given in this conversation. **No 2026 observation was opened, loaded or derived.** Phase 5 (the 2026 holdout) is therefore **not run**.

## 2. Approved files used (hash-pinned in `runner/guard.py`; footer max 2025-Q4)

| File | SHA-256 | Variables used | Level | Period | Purpose |
|---|---|---|---|---|---|
| E12 `realized_components_2021_2025.csv` | `6719baf7…432e67ce1` | F, mean5, D | Province | 2021-Q1..2025-Q4 | F and D targets and inputs; regional food inflation (mean5) |
| E12 `details.json` → `two_layer.regional_layer_rounds` | `ee022c35…281a6865c` | Per-round H, fieldwork quarter, publication date, series | Balance Luzon | 2021-Q2..2025-Q4 (21 rounds) | H target and inputs |
| `data/processed/features_fused.parquet` | `0080dd5c…a2fda1292` | `unemployment_rate` (national LFS; the same value for every province) | National | 2021-Q1..2025-Q4 | One indicator for candidate C7 |

**Runtime checks in every script:**

- the hashes are verified before each read;
- the read-time filter limits rows to 2021-Q1..2025-Q4;
- loaders assert that no quarter after 2025-Q4 is returned;
- the integrity log is written to `runs/<run>/integrity_log.json`.

## 3. Authorization request, file by file (for you, and your adviser if required)

**How this list was built:** file names and parquet footer row ranges only. **Nothing below has been opened.** Publication dates are to be verified **before** any access.

| # | File | Variables needed | Level | Reference periods held (footer) | Category | Purpose if approved |
|---|---|---|---|---|---|---|
| 1 | `aipheed-backend-aligned/data/supplementary/collection_2026-10-09/provincial_food_cpi_yoy_2026H1_raw.csv` | Provincial food CPI YoY | Province | 2026 H1 (from the file name) | **Jan–Jun 2026** | F and D holdout for 2026-Q1 and 2026-Q2; shortens h to 3 |
| 2 | `aipheed-backend-aligned/data/supplementary/collection_2026-10-09/cpi_2026_release_dates.csv` | Release dates | National and provincial | 2026 | Jan–Jun 2026 (contents unknown) | Verify CPI publication dates for 2026 |
| 3 | `aipheed-backend-aligned/data/processed/cpi_full.parquet` | `food_cpi_yoy` | Province | 2020-Q1..**2026-Q2** | Mixed: 2020–2025 **plus Jan–Jun 2026** | Alternative source for item 1 |
| 4 | `backend/data/processed/sws_hunger.parquet` (production) | Hunger %, round dates | Balance Luzon | 2024-Q3..**2026-Q2** | Mixed: **Jan–Jun 2026** rounds | H holdout for 2026-Q1 and 2026-Q2; shortens h to 3 |
| 5 | `aipheed-backend-aligned/data/supplementary/collection_2026-10-09/sws_existing_value_verification.csv` | Round values and dates | Balance Luzon | Unknown | Unknown | Release-date reconciliation for SWS |
| 6 | `backend/data/processed/psa_indicators.parquet` (production) | Food CPI | Province | 2020-Q1..**2026-Q4** | Mixed, **including Jul–Dec 2026 rows** | **Do not authorize without inspection rules.** Its footer reaches 2026-Q4, inside the protected range. |
| 7 | News, climate, macro and rice files (`fssi_quarterly`, `trigger_proportions`, `corpus_*`, `bias_weights`, `bsp_macro`, `oil_prices`, `pagasa_climate`, `psa_rice_prices`, `province_*`) | Features | Province or national | to **2026-Q3** | Mixed, **including Jul–Sep 2026** | Needed only for the thesis classifier at 2027-Q1. Jul–Sep 2026 news may report protected SWS or CPI values. |

**Categories as your brief requires:**

| Category | Status |
|---|---|
| **January–June 2026** | Items 1–4 (and possibly 5). Not protected under the stated rule (which protects July–December), but **not authorized**. Some values were exposed in earlier project records. |
| **July–September 2026** | Items 6–7 hold such rows. **Protected.** |
| **October–December 2026** | Item 6's footer reaches 2026-Q4. **Protected.** Also incomplete, since 2026-Q4 is still under way. |

**What becomes possible if items 1 and 4 alone are approved,** with publication dates verified first:

- a descriptive 2026-Q1/Q2 holdout for H, F and D;
- a shorter horizon (h = 3) for the 2027-Q1 forecast.

**Without approval,** both remain undone.
