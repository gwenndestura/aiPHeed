# E127 2026-Q4 regional PAR feature: recalculation

**What this is.** A feature-level dry run for origin 2026-Q4 (issue 2027-01-01).

**What this is not.** **No forecast was issued, and no forecast score was stored.**

| | v1.2 (before) | v1.3 (Amendment 3) |
|---|---|---|
| PAR quarter used (latest available before 2027-01-01) | 2026-Q3 | 2026-Q3 |
| Count | **7** storms (BAVI, MAYSAK, NOUL, PEILOU, SAUDEL, KROVANH, SURIGAE) | **7** |
| Availability | 2026-10-01 | 2026-10-01 |
| Reference values (2021+ quarters before 2026-Q3, available before the issue) | 19 | **22** (+ the three zeros) |
| Below 7 / equal to 7 | 13 / 1 | 16 / 1 |
| Mid-rank percentile (#below + ½ #equal) / n | 13.5 / 19 = **0.7105** | 16.5 / 22 = **0.7500** |
| Independent recomputation | 0.710526 (matches) | 0.750000 (matches) |
| Future values in the reference set | 0 | 0 |

**Reference values (v1.3, sorted):** 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 4, 4, 4, 4, 6, 6, 7, 8, 9, 10, 10, 15. v1.2 is the same set without the three zeros.

## Verified

- **The current count is unchanged** (7 in 2026-Q3).
- **The change comes only from the reference set,** which now includes the three verified zero quarters.
- **No future observation is used.** The reference set is quarters 2021-Q1..2026-Q2 available before the issue. 2026-Q4 is not covered and not recorded.
- **No other feature changes** at 2026-Q4, and no provincial feature changes.
- **No indicator, aggregation or band rule changes.**

## Interpretation

0.75 means the 2026-Q3 count of storms entering PAR (7) is higher than about three quarters of the quarterly counts seen since 2021. Within FIRI3 it is the regional cyclone component's position relative to the usual level of 2021+.

**It is not a probability of household food insecurity or of a storm impact.** It is one input to the relative composite index.
