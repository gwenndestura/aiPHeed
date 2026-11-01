# Addendum 1, implementation note (written before any Addendum-1 score)

The first run stopped at its own integrity check before computing any metric: 30 rows had no price label for quarter
t−1, because `predictions.csv` holds labels only for quarters with an SWS round (2022-Q3/Q4 and 2025-Q1 have none).
The price label needs CPI only. For the persistence and climatology baselines, price labels are therefore read from
`E68_Resolve_E67_Critical_Failures/tables/r2_labels_all.csv` (column `PS`, the same frozen E40 CPI thresholds). It
agrees with `predictions.csv`'s `price` on all 70 overlapping province-quarters (70/70). The forecast, the target
rows and the rules are unchanged.
