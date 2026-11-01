# Step 1: SWS publication-date audit (done before the protocol; no scoring)

**Script:** `runner/audit_dates.py`.

**Output:** `out/sws_rounds_audit.csv` (one row per round, with its date basis) and `out/audit_dates.json`.

**Series:** the same SWS series as every earlier study (`LEAD2_RELIABILITY_RESEARCH/runner/rlib.rounds`):

- Balance Luzon 2021+ from `backend/data/inputs/sws_rounds.csv`;
- all other area-rounds from `FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/sws_area_rounds_full.csv` (`published`, `source_type`).

The served features store the same dates as `sws_newest_published` (`ch1_lib.pi_h` → `fi_lib.known`). No website was accessed.

## How each date is known

| Period | Rounds | Quarters | Date basis |
|---|---|---|---|
| 2002–2020 | 80 | 74 | **Estimated.** The SWS media-release tables give the round's label month only. The date is the stated rule "label month end + 60 days" (`source_type = … (rule)`). |
| 2021–2026 | 21 BL rounds (production series) | 21 | **Verified.** Each is an SWS release or news report date. `date_type`: `verified`, `verified-single`, `verified (SWS release posted date, E31)`. |

**Pre-2021 spot checks** (`sws_release_date_evidence.csv`, 10 rounds 2008–2020) found real releases from 8 days before to 43 days after the label month end. For example:

- Sep 09 → 2009-10-14 (+14);
- Sep 15 → 2015-11-02 (+33);
- Jun 16 → 2016-08-12 (+43);
- Dec 19 → 2020-01-26 (+26);
- Sep 20 → 2020-09-28 (−2).

**So the +60-day rule is conservative** (later than reality), and it remains an estimate.

## Days from quarter end to publication of the quarter's last round

| Basis | Quarters | min | p25 | median | p75 | **p90** | max |
|---|---|---|---|---|---|---|---|
| Verified (2021-Q2 .. 2026-Q3) | 21 | −2 | 19 | 30 | 46 | **67** | 84 |
| Estimated (2002–2020, rule) | 74 | 29 | – | 60 | – | – | 60 |

**Verified values, sorted:**

−2, 14, 14, 14, 17, 19, 22, 23, 28, 29, 30, 33, 36, 41, 42, 46, 51, 55, 67, 72, 84

The −2 is 2025-Q1: the commissioned Stratbase–SWS round was published on 2025-03-29, before its quarter ended.

## Consequences fixed in the protocol

| Item | Rule |
|---|---|
| Cap | 67 days after quarter end: the nearest-rank 90th percentile of the **verified** quarters only. The rule-based pre-2021 dates are not measurements and were not used for the cap. |
| Pre-2021 lag bound | Main = rule dates (label month end + 60). **Sensitivity = rule + 30 days** (label month end + 90; as in Y12, a later bound). Most pre-2021 issues then fall on the cap. |

**Remaining gap:** individual pre-2021 release dates cannot be verified from the project data. psa.gov.ph and sws.org.ph archive pages were not scraped.
