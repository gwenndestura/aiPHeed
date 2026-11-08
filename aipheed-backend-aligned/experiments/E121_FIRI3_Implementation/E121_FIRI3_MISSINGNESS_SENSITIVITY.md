# E121 FIRI3 missing-data sensitivity

**Source.** `runner/run_e121.py`: `out/missingness_by_k.csv` and `out/composition_changes.csv`.

## 1. Scores by number of available indicators (provincial, 75 computable rows)

| k | Rows | Indicator sets | Mean FIRI3 | SD | Chance SD | Mean \|FIRI3 − core-4\| | Max | Band differs from core-4 |
|---|---|---|---|---|---|---|---|---|
| 4 | 54 | AFP CEC EHS FMA: 50; AFP CEC FMA PSV: 4 | 0.513 | 0.090 | 0.144 | 0.006 | 0.147 | 3.7% |
| 5 | 13 | +PSV: 7; AFP CEC FIS FMA PSV: 6 | 0.418 | 0.074 | 0.129 | 0.055 | 0.105 | 7.7% |
| 6 | 8 | all six | 0.419 | 0.055 | 0.118 | 0.048 | 0.097 | 0.0% |

**The core-4 score** is the mean of FMA, AFP, CEC and EHS, where available.

**Reading.**
- **Low means for k = 5 and 6 are mostly timing, not missing data.** Those rows all come from 2025-Q3 onward, when the common indicators were also low. Their core-4 means are 0.381 and 0.410.
- **Adding PSV and FIS moves a score by 0.05 on average and at most 0.11.** The band changes in 0–8% of rows.

## 2. When an indicator joins or leaves (same province, consecutive quarters)

**Overall.** 18 composition changes. The mean |composition effect| is **0.011**: across provinces, PSV's mid-ranks average 0.5.

**For individual provinces, the effect is not small:**

| Event | Composition effect by province |
|---|---|
| PSV joins (2025-Q3) | Quezon +0.103, Cavite +0.079, Batangas +0.015, Rizal −0.018, Laguna −0.042 |
| FIS joins / leaves | −0.088 to +0.074 |
| EHS leaves (2026-Q2, DI-3) | −0.058 to +0.049 |

## 3. Conclusion

**Four-indicator and six-indicator scores are not automatically comparable for a given province.**
- The level difference is mostly period, not completeness.
- But when PSV or FIS joins, a province can move by up to ±0.10 for reasons of data availability alone.

**How the frozen method handles it:**
- every score reports its indicator set;
- the geographic comparison uses only origins where all five provinces have the same set.

**The issue is recorded as DI-2.** Proposed: always report the common-core score and flag set changes. It needs approval.
