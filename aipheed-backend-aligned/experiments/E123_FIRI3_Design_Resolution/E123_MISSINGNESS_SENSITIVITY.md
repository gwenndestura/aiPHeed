# E123 missingness sensitivity

**Source.** `out/missingness_by_k.csv` and `out/change_decomposition.csv`, on FIRI3 v1.2.

## Scores by number of available indicators (provincial)

**Fixed core** = FMA, AFP, CEC, EHS.

| k | Rows | Origins | Indicator sets | Mean FIRI3 | Mean fixed core | Mean FIRI3 − core | Mean \|FIRI3 − core\| | Max | Band differs from core |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 50 | 2023-Q1..2025-Q2 | FMA AFP CEC EHS: 50 | 0.516 | 0.516 | 0 | 0 | 0 | 0% |
| 5 | 11 | 2025-Q3..2026-Q3 | + PSV: 11 | 0.442 | 0.404 | +0.037 | 0.065 | 0.113 | 9.1% |
| 6 | 14 | 2025-Q4..2026-Q3 | all six: 14 | 0.428 | 0.420 | +0.008 | 0.045 | 0.095 | 0% |

**Effect of Amendment 2.** Since 2026-Q2/Q3 regained EHS, every computed provincial score now contains the full fixed core. In E122, 4 rows lacked EHS.

## Availability vs actual change (consecutive quarters, same unit)

| | Provincial | Regional |
|---|---|---|
| Pairs | 70 | 9 |
| Mean \|change\| | 0.061 | 0.080 |
| Mean \|feature-change part\| | 0.063 | 0.078 |
| Mean \|availability part\| | 0.008 | 0.004 |
| Pairs where the indicator set changed | 13 | 1 |
| Share of absolute change due to availability | **12.9%** | 4.5% |

## Reading

- **Level differences by k are mostly period differences.**
  - The 5- and 6-indicator rows are all from 2025-Q3 onward, when the core itself was lower (0.40–0.42 vs 0.52).
  - Adding PSV/FIS moves a province by 0.045–0.065 on average, at most 0.11. That is up to ±0.1 for reasons of data availability, not conditions.
- **About 13% of the provincial quarter-to-quarter movement is availability.** The rest is genuine feature change.

**Comparability rule (unchanged, now supported by outputs):**
- Compare provinces or quarters on the **fixed core** or the **cross-province core**, which is reported beside FIRI3 in `E123_COMMON_CORE_RESULTS.csv`.
- Treat an overall FIRI3 difference between rows with different indicator sets as **not directly comparable**.
