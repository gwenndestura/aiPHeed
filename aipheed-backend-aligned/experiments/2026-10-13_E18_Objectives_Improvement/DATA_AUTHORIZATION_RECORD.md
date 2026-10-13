# Data Authorization Record (E18)

## Authorization given (2026-10-13, in this conversation)

You selected **"Jan–Jun 2026 only"**:

- authorized: `provincial_food_cpi_yoy_2026H1_raw.csv` and the January–June 2026 SWS rounds, **after verifying publication dates**;
- **July–December 2026 stays protected.**

## Files read (hash-pinned in `runner/guard.py`)

| File | SHA-256 | Content verified before use | Publication evidence |
|---|---|---|---|
| E12 `realized_components_2021_2025.csv`, E12 `details.json`, aligned `features_fused.parquet`, `config/governing_model.json` | As in E17 | Eligible through 2025-Q4 | As in E13 and E17 |
| `data/supplementary/collection_2026-10-09/provincial_food_cpi_yoy_2026H1_raw.csv` | `57f09e91…` (equals the collection manifest) | **30 rows: five provinces × 2026-01..2026-06** (README, manifest and the loaded rows agree) | **National** release dates 2026-02-05 to 2026-07-07 (`cpi_2026_release_dates.csv`, press sources). **Provincial dates unverified.** Upper bound: retrieved 2026-10-09T14:40Z, so certainly public before the 2027-Q1 forecast origin (2026-10-13). |
| `.../cpi_2026_release_dates.csv` | `9a7d4805…` (equals the manifest) | National release dates for January–June 2026 only | — |
| `backend/data/processed/sws_hunger.parquet` (production, **read only**, rows filtered at read time to 2026-Q1..2026-Q2) | `64701ed6…` | Footer range 2024-Q3..**2026-Q2** (no July–December rows). The rows read are the **March 2026** and **June 2026** SWS surveys (Balance Luzon, repeated across 5 province rows; used once as a regional value). | **No publication date is stored.** Upper bound: `fetched_at` 2026-09-09T03:21Z, so certainly public before 2026-10-13. Exact dates **unverified**. |

**Ruled out:**

- SWS web pages were **not** opened. They can show protected later rounds.
- No July–December 2026 data was opened. Nothing was loaded and then filtered.

## What the evidence supports

| Use | Supported? | Why |
|---|---|---|
| **The 2027-Q1 forecast origin (2026-10-13)** | **Yes** | Every Jan–Jun 2026 value used is proven public before the origin |
| **Backtest origins in 2026** (for example, using the March 2026 round at an earlier origin) | Only through the information-set convention | The convention assumes a quarter's data are known at the next quarter's origin. Exact SWS 2026 and provincial CPI dates are **unverified**. |

## Still pending (not authorized)

July–December 2026 CPI and SWS, 2026 news features, and all mixed files listed in E17 v3's request.
