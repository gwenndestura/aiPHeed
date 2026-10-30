# Data issues and recommendations

The fix column marks whether existing data can resolve the issue:
- **Yes**: it can be fixed with data already in the repository.
- **No**: it needs new collection or official records.

| # | Dataset / indicator | Evidence | Effect on forecasting | Recommended correction | Fix |
|---|---|---|---|---|---|
| 1 | CPI refresh months (A1, A2 in CR/CR-ANC) | 61 owner-reported, 79 unresolved release dates (`psa_cpi_availability_ledger_20261029.csv`) | Lead-2 refresh gains are provisional | dated PSA release pages for each province-month | **No** (owner) |
| 2 | CPI final vintage (A1, A2, price label) | 3 of 29 archived headline rates differ (≤ 0.4 pp) | small leakage of revisions | use archived as-released values where they exist | partly |
| 3 | CPI 2018=100 before public (A1, A2) | 375 training rows issued before 2022-06-07 | training uses a series not then public | obtain 2012=100 values for 2021 origins, or drop those rows (sensitivity shown) | partly |
| 4 | Price thresholds (label, A1, A2) | 600 training rows issued before the 2021-22 P60 was computable | training labels use a future-derived constant | expanding-window thresholds for a development-only target. The official labels are unchanged. | **Yes** |
| 5 | Lags of A3, C3, C4, E1, E2 | no dated releases saved; shifting one quarter changes Lead-2 development Brier 0.177 → 0.189 | B0's development result is fragile | collect PSA/BSP release calendars; until then report both lags | **No** |
| 6 | V1 poverty | SAE 2021 / POPCEN 2024 published 2024-25, used at all origins; 5 distinct values | cannot be a time-varying signal; acts as a province identifier | use as a vulnerability profile only; label it so | **Yes** (relabel) |
| 7 | C2 climate panel | rainfall anomaly column 100% empty; typhoon counts identical across provinces in 61% of quarters | climate domain lacks rainfall; little provincial signal | add PAGASA station or CHIRPS rainfall with dates | **No** |
| 8 | E1 employment | national only on OpenSTAT; owner provincial file is annual 2021-25 with gaps | cannot distinguish provinces; national time marker | regional quarterly LFS (Region IV-A) with release dates | **No** |
| 9 | E2 OFW remittances | national; model panel stops at 2025-Q4, though the audit copy runs to 2026-Q2; BSP blocks automated download | stale and national; no long history | refresh the panel from the audit copy (2026-Q1/Q2); obtain BSP 1989+ series manually | partly **Yes** |
| 10 | N1 news | FSSI missing in 83% of Lead-2 rows; coverage follows the collection calendar (0% in 2021, ~35% in 2024-26) | not usable as a consistent predictor | keep as context; do not impute | **No** |
| 11 | H1 / T43c hunger part | one Balance Luzon value copied to 5 provinces | 13-14 independent observations, not 65-70 | treat hunger as regional; separate regional forecast from provincial profile | **Yes** (design) |
| 12 | T43c price part | computed from the same CPI as A1/A2 | partly circular target | do not use T43c to claim market contribution | **Yes** (design) |
| 13 | 11.3% threshold | P60 of 6 quarters (2021-22) | unstable, regime-specific event definition | report levels; use "above usual" from known history for events | **Yes** |
| 14 | Provincial food-insecurity outcome | none over time (FIES 2021/2023 snapshots, subsistence 2021/2023, CBMS one window) | provincial forecasting cannot be validated | send the E87 data requests (CBMS, FNRI); use snapshots for cross-sectional validation | **No** |
| 15 | Pre-2021 SWS release dates | rule (month end + 60 days), 9 spot checks | timing of long-history training uncertain | lag-100 sensitivity (E114: conclusions held); collect release dates | partly |
| 16 | Typhoon quarter 2026-Q3 | incomplete when fetched | missing latest climate input | refetch IBTrACS after quarter end | **Yes** |

## Priority order

1. **Items 1, 5, 9 and 14.** These need official records or a download by you.
2. **Items 4, 6, 11, 12 and 13.** These are design corrections possible now. None of them changes production.
3. **Items 7, 8 and 10.** These need new data sources.
