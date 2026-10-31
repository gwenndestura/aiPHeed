# E125 issuance readiness: origin 2026-Q4, planned issue 2027-01-01

**Decision on 2026-10-31: BLOCKED.** Two conditions fail:
- the issue date has not arrived;
- the September 2026 LFS month is not yet published.

**No forecast was issued.** The E124 store is unchanged: no forecast, one blocked attempt recorded.

## Conditions

| Condition | Result |
|---|---|
| Current date on or after 2027-01-01 | **No** (2026-10-31) |
| All required source periods complete | **No.** National unemployment for 2026-Q3 has 2 of 3 months. |
| Required datasets refreshed | NASA POWER **yes** (2026-01..09). IBTrACS **yes** (file modified 2026-10-30, last fix 2026-10-29). LFS re-queried, but September is absent. |
| All features satisfy the frozen eligibility rules | 33 of 34. EHS_unemployment_change_R is BLOCKED. |
| Forecast reproducible | **Yes.** Shuffled identical inputs give identical results; the pre-refresh run equals E123 exactly. |
| Snapshot store operational | **Yes.** Empty; duplicate and early issuance refused (tested on a copy). |
| Protocol hash matches the frozen configuration | **Yes** |
| No unresolved critical data-integrity failure | **Yes for issuance.** One processing defect (D-E125-2) is open and awaits approval; it does not affect the 2026-Q4 issue. |

## Features (`E125_FEATURE_ELIGIBILITY_AUDIT.csv`)

| Decision | Count | Features |
|---|---|---|
| **READY** | 4 | CEC_cyclones_100km, CEC_cyclones_R, FIS_fssi, FIS_shortage_news_R (dated sources) |
| **READY WITH WARNING** | 29 | **Provisional publication dates:** all FMA, AFP and CEC rainfall/heat features (provincial and regional), and EHS_remittance_decline_R. **Unverified dates:** EHS_unemployment_prov and EHS_underemployment_prov (2024 used: 2025 incomplete in the source) and PSV_poverty (static, assumed date). |
| **BLOCKED** | 1 | EHS_unemployment_change_R (September 2026 not published) |
| NOT APPLICABLE | 0 | — |

## Refresh results

**NASA POWER** (`E125_NASA_POWER_REFRESH_AUDIT.csv`):
- Monthly rainfall and temperature for 2026-01..2026-09 at all five centroids; 2026-10 not yet in the source (fill value).
- **0 revisions** to 2021–2025 values.
- 2026-Q1..Q3 complete.
- The E119 aggregation reproduces the existing series exactly before the refresh is applied.

**Cyclones** (`E125_CYCLONE_REFRESH_AUDIT.csv`):
- **Within 100 km, 2026-Q3:** 0 for every province. The nearest storm (PEILOU) passed 263 km from the Rizal centroid.
- **PAR, 2026-Q3:** 7 storms (BAVI, MAYSAK, NOUL, PEILOU, SAUDEL, KROVANH, SURIGAE). All 2026 tracks are IBTrACS **PROVISIONAL**.
- **Double count found and avoided:** SAUDEL appears under two IBTrACS IDs that share JTWC id WP172026, so it is counted once. This splitting occurs nowhere else in 2021–2026, so history is unchanged.
- **History check:** 98.1% of quarters match. The one mismatch is D-E125-2.

**LFS:** see `E125_LFS_SEPTEMBER_2026_AUDIT.md`.

**Other sources** (review of every E124 registry row):
- CPI (provincial and Region IV-A), retail and farmgate prices, wholesale rice, production, remittances, FSSI and GDELT already hold the periods their rules make available before 2027-01-01. Nothing else needs refreshing for this issue.
- **Before the issue,** re-check CPI, prices, production and remittances for revisions, and extend the news corpus beyond 2026-10-14 for the next quarter.

## CPI publication dates (E124 finding)

**Ledger evidence.** 13 of 32 archived provincial CPI releases came after the day-10 rule, by up to 12 days. But every quarter FIRI3 scores has at least **71 days** between the rule date of its last month and the issue date.

**Check.** All 160 scored uses were checked against every dated piece of evidence (archives, owner-reported dates). **0** uses have evidence on or after their issue.

**Conclusion.** The rule's optimism cannot make any FIRI3 quarter-start score ineligible. Undated months stay provisional.

## Open defect (not applied)

**D-E125-2.** The E114 PAR series omits quarters in which no storm entered PAR (2023-Q1, 2024-Q1, 2025-Q1). The as-of rule then uses an older quarter's count instead of 0.

**Effect, as a sensitivity.** With explicit zeros, 9 regional scores change (max 0.042) and 1 band changes (2025-Q2: above usual → usual or below).

**No effect on 2026-Q4:** 2026-Q3 has 7 storms.

**Proposed:** record zero-storm quarters as 0. These are true counts, not imputation. Approval is needed because historical regional scores change.

## Path to issuance

1. **On or after 2026-12-01:** re-query LFS; confirm September; recompute E1 for 2026-Q3.
2. **On or after 2027-01-01:**
   - re-check every source for revisions and log the hashes;
   - rerun `run_e125.py --today <date>`, expecting all conditions to pass;
   - **with the owner's authorization,** call `Store.issue("2026-Q4", …)`;
   - write `E124_2026Q4_FORECAST_SNAPSHOT.json`, `E124_2026Q4_FEATURE_TRACE.csv` and `E124_2026Q4_FORECAST_REPORT.md` from the stored snapshot.
