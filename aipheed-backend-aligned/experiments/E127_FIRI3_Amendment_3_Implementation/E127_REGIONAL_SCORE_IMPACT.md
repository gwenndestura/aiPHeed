# E127 regional score impact (independently recomputed)

**Comparison.** v1.2 = the E125 refreshed inputs; v1.3 = the same plus Amendment 3. Both were rebuilt from source here.

**Full table.** `E127_HISTORICAL_SCORE_RECONCILIATION.csv`: 138 unit-origins, unchanged rows included.

## Regional CALABARZON: origins with a computable FIRI3

PAR is the regional feature `CEC_cyclones_R`, as of the issue.

| Origin | PAR used, v1.2 | PAR used, v1.3 | Reference values (v1.2 → v1.3) | PAR score (v1.2 → v1.3) | FIRI3 v1.2 | FIRI3 v1.3 | \|Δ\| | Band v1.2 | Band v1.3 |
|---|---|---|---|---|---|---|---|---|---|
| 2024-Q2 | 2023-Q4 = 2 | **2024-Q1 = 0** | 10 → 12 | 0.200 → 0.042 | 0.5479 | 0.5347 | 0.0132 | above usual | above usual |
| 2024-Q3 | 2024-Q2 = 2 | 2024-Q2 = 2 | 11 → 13 | 0.227 → 0.346 | 0.5729 | 0.5808 | 0.0079 | above usual | above usual |
| 2024-Q4 | 2024-Q3 = 10 | same | 12 → 14 | 0.958 → 0.964 | 0.4973 | 0.4977 | 0.0004 | usual or below | usual or below |
| 2025-Q1 | 2024-Q4 = 7 | same | 13 → 15 | 0.692 → 0.733 | 0.4522 | 0.4549 | 0.0027 | usual or below | usual or below |
| **2025-Q2** | 2024-Q4 = 7 | **2025-Q1 = 0** | 13 → 16 | 0.692 → 0.063 | 0.5282 | 0.4862 | **0.0420** | **above usual** | **usual or below** |
| 2025-Q3 | 2025-Q2 = 1 | same | 14 → 17 | 0.071 → 0.235 | 0.3431 | 0.3541 | 0.0109 | usual or below | usual or below |
| 2025-Q4 | 2025-Q3 = 15 | same | 15 → 18 | 1.000 → 1.000 | 0.3450 | 0.3450 | 0 | usual or below | usual or below |
| 2026-Q1 | 2025-Q4 = 6 | same | 16 → 19 | 0.594 → 0.658 | 0.3305 | 0.3348 | 0.0043 | usual or below | usual or below |
| 2026-Q2 | 2026-Q1 = 2 | same | 17 → 20 | 0.235 → 0.350 | 0.3624 | 0.3700 | 0.0076 | usual or below | usual or below |
| 2026-Q3 | 2026-Q2 = 4 | same | 18 → 21 | 0.472 → 0.548 | 0.6826 | 0.6876 | 0.0050 | elevated | elevated |

## How the changes arise

- **In 2024-Q2 and 2025-Q2,** the as-of rule used to fall back to an older count. In v1.2 there was no 2024-Q1 or 2025-Q1 row, so it took 2023-Q4 = 2 and 2024-Q4 = 7. It now uses the true 0.
- **In every later origin,** the reference history gains the zeros, so each count's percentile rank shifts.
- **2025-Q4 is unchanged:** 15 storms is the maximum either way.
- **2023-Q2 to 2024-Q1** have regional FIRI3 *not computable* in both versions: fewer than 4 of 5 indicators. Their PAR feature changes, but no score.

## Summary (matches E126)

| Measure | Result |
|---|---|
| Regional FIRI3 scores changed | **9** (2024-Q2, Q3, Q4; 2025-Q1, Q2, Q3; 2026-Q1, Q2, Q3) |
| Max \|Δ\| | **0.041987** (2025-Q2) |
| Band changes | **1**: 2025-Q2, above usual → usual or below |
| Provincial scores changed | **0**: PAR enters only the regional score |
| Other features or indicators changed | 0 / 0 (only `CEC_cyclones_R` and, through it, regional CEC) |
| CCS changed | the same 9 regional rows |
| Computable scores | unchanged: 75 provincial, 10 regional |
| FIRI3 vs FIRI v2 comparison | unchanged (provincial only; FIRI v2 has no regional index) |
