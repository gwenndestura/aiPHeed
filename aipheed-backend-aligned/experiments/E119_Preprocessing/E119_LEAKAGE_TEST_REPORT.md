# E119 leakage test report

**When the checks run.** `runner/preprocess.py` runs them after building the datasets and **stops before writing** if any fails. Results are in `out/manifest.json`. The same checks run independently in `backend/tests/integration/test_e119_preprocessing.py`, which reads the written CSVs.

**Point-in-time rows checked.** `E119_POINT_IN_TIME_VALIDATION.csv` holds one row per (dataset, origin, lead, feature) value. Each row gives the observation period, availability date, issue date, target quarter and status.

| # | Check | How | Result |
|---|---|---|---|
| 1 | Every feature's observation period is before the target quarter | obs quarter < target quarter for every regional PIT row | **PASS** |
| 2 | Every feature was available before the issue date | avail_date < issue_date for every regional and provincial PIT row | **PASS** |
| 3 | No target-quarter hunger among predictors | H1 latest-reading quarter < target quarter for every row | **PASS** |
| 3b | SWS history uses only rounds published before the issue | published date < issue date for every H1 PIT row | **PASS** |
| 4 | Derived statistics use only 2021+ data available at the issue | YoY needs the 2021+ value 4 quarters earlier; its availability is the later of the two dates. Anomalies use earlier same-quarter 2021+ values. A1/A2 thresholds are as-of (corrected pipeline). | **PASS** (by construction; test re-checks the first YoY quarter is 2022) |
| 5 | No observation before 2021-01 in any modeling file | minimum period of all 256 series ≥ 2021-Q1; all PIT obs periods ≥ 2021 | **PASS** |
| 6 | No imputation or zero fill | Missing stays NaN; quarters need all 3 months. The test checks that every provincial dataset value equals a cleaned observation of the same unit and period (over 1,000 values). | **PASS** |
| 7 | Raw inputs unchanged | SHA-256 of every input before and after the run | **PASS** |
| 8 | No duplication of coarse values across provinces | No national or regional feature column in the provincial dataset | **PASS** |
| 9 | Computed changes (YoY, drops, pp changes, declines) start 2022-Q1 or later | Every derived change series checked at run time (PSA-published CPI YoY excepted) | **PASS** |

## Known limits (not leakage, but disclosed)

- **Release dates are mostly rules, not archived releases.** Prices, production, LFS, ONI and NASA POWER use documented release rules (`rule_unverified`). CPI months with an archived PSA release are `verified`. But a quarter is `verified` only if all 3 months are, which no quarter achieves, so CPI quarters are `rule_unverified`.
- **Strict (verified-only) view.**
  - Regional: 10 features (H1 ×4, C1, PAR typhoons, GDELT ×4).
  - Provincial: 4 features (C2, local typhoons, N1 FSSI, N1 article count).
- **NASA POWER values may be revised after first release.** The values used are the current vintage, not real-time.
- **The provincial A1/A2 thresholds** come from the corrected pipeline and are as-of. They equal the frozen thresholds at the 2021–22 window.
