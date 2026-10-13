# Phase 0: Forecast Origin, Information Gap and Horizon for 2027-Q1

| Item | Value |
|---|---|
| Forecast generation date | **2026-10-13** (actual execution date) |
| Target quarter | **2027-Q1** |
| Authorized information | **Approved eligible data through 2025-Q4 only.** No 2026 observation is authorized (Phase 2), so none is used. |
| Information cutoff | The latest eligible observation of each series, all published by about mid-January 2026. The forecast is generated in October 2026, but its information set is a **January 2026 information set**. |

**Horizon convention, used identically in backtesting and in the 2027-Q1 forecast:** h = the number of quarter steps from the **latest eligible observed quarter of the target series** to the target quarter.

## 1. By target

| Target | Geography | Latest eligible observation | Its publication date | Steps to 2027-Q1 | **h** | Does the publication schedule permit a forecast at h? |
|---|---|---|---|---|---|---|
| **Regional hunger H** (SWS involuntary hunger, % of families) | Balance Luzon | 2025-Q4 (November 2025 SWS survey, production series) | **2026-01-14** (verified-single) | 2025-Q4 → 2027-Q1 | **5** | Yes. Whether **h = 5 is evidenced** is decided in Phase 4. |
| **Provincial food inflation F** (YoY %) | 5 provinces | 2025-Q4 (quarterly mean of Oct–Dec 2025) | **Proxy:** national release + 14 days (third week of January 2026). **Not verified**; the release-date file was not opened. | 2025-Q4 → 2027-Q1 | **5** | Yes, under the proxy |
| **Relative pressure D** (F − unweighted five-province mean) | 5 provinces | 2025-Q4 | As F (proxy) | 2025-Q4 → 2027-Q1 | **5** | Yes, under the proxy. Requires all five provinces (they are complete). |
| **Thesis risk label** (HIGH if S1 > 14.6) | 5 provinces | 2025-Q4 label, known after both SWS (2026-01-14) and CPI (proxy) are published | ≥ 2026-01-14 | 2025-Q4 → 2027-Q1 | **5** (classification lead time k = 5 in the E17 convention) | **No.** The implemented classifier needs news features from 2026 quarters, which exist only in mixed files and are not authorized. E17 also found that k = 5 has **1** test quarter and that the model beats no baseline at any lead time. |

**The targets do not share one cutoff by accident.** Each target's latest eligible observation is 2025-Q4 because of **the authorization limit**, not because their publication schedules coincide.

## 2. If 2026 data were authorized (not done; shown for planning)

This is based on footer row ranges only. No values were read.

| Target | Files that hold 2026 rows | Latest quarter in those files | Horizon if authorized and verified |
|---|---|---|---|
| H | Production `sws_hunger.parquet` (rows to 2026-Q2) | 2026-Q2, if its round was published before the origin | **3** |
| F, D | `cpi_full.parquet` (rows to 2026-Q2); `provincial_food_cpi_yoy_2026H1_raw.csv` | 2026-Q2 (Jul–Sep 2026 provincial CPI is **protected**) | **3** |

**Neither shorter horizon is available without authorization.** The publication dates of those 2026 values would also need verifying first.

## 3. Consequence

**Every 2027-Q1 forecast here is a 5-quarter-ahead forecast.** Under the horizon-matching rule, candidates must be validated **at h = 5**. Shorter horizons are reported only as diagnostics.
