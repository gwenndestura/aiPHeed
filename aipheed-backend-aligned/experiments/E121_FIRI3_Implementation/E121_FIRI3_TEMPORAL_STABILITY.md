# E121 FIRI3 temporal stability

**Source.** `out/temporal_changes.csv`: every consecutive pair of computed quarters for the same unit.

Each change is split into two parts:
- **common-indicator change:** the change in the mean of the indicators present in both quarters;
- **composition effect:** the rest, from indicators joining or leaving.

Each change also records which features joined or left, and whether an unchanged observation was rescored because its normalization history grew.

## 1. Summary

| | Provincial | Regional |
|---|---|---|
| Consecutive pairs | 70 | 9 |
| Mean \|change\| | 0.063 | 0.080 |
| SD of change | 0.084 | 0.113 |
| Changes > 0.15 | 5 | 2 |
| Pairs with a change of indicator set | 18 | 1 |
| Mean \|composition effect\| | 0.011 | 0.004 |
| Pairs where an unchanged observation was rescored | 0% | 11% |
| Band changes | 20 of 70 | 4 of 9 |
| Lag-1 autocorrelation of FIRI3 | 0.28–0.57 by province (E120) | 0.38 |

**Comparison with FIRI v2.** On the 75 matched rows, FIRI v2's mean quarterly change is 0.072 against FIRI3's 0.063.

## 2. Abrupt changes (> 0.15)

| Unit | Origin | Change | Composition effect | Cause |
|---|---|---|---|---|
| Cavite | 2023-Q2 | −0.281 | 0 | Common indicators fell (the 2023-Q1 quarter was "high"); no data-structure change |
| Laguna | 2023-Q2 | −0.268 | 0 | Same quarter; wholesale rice joined inside FMA |
| Batangas | 2024-Q4 | −0.176 | 0 | Conditions |
| Laguna | 2025-Q3 | −0.157 | −0.042 | Mostly common indicators (−0.115); PSV joined (Laguna PSV = 0.1) |
| Rizal | 2025-Q3 | −0.167 | −0.018 | Mostly common indicators; PSV joined |
| Regional | 2025-Q3 | −0.185 | 0 | Conditions |
| Regional | 2026-Q3 | +0.219 | 0 | Conditions |

## 3. Causes checked

| Cause | Finding |
|---|---|
| Dataset publication updates | Each quarter brings new observation periods. No observation was revised inside the inputs: E119 is a single vintage. NASA POWER revisions are a disclosed limitation (current vintage). |
| Missing features | Features joining or leaving are recorded per pair. They explain one of the five provincial jumps (Laguna 2023-Q2: wholesale rice joined). |
| Normalization history | Rescoring an *unchanged* observation happened in 0 provincial pairs and 1 regional pair. Percentile drift is not a source of jumps. |
| New indicator availability | PSV at 2025-Q3 (DI-2); FIS sporadic; EHS lost at 2026-Q2 (DI-3) |
| Number of contributing indicators | The composition effect is small on average (0.011) but up to ±0.10 for a single province |

## 4. Conclusion

- **FIRI3 changes mainly because its inputs change.** The 7 jumps above 0.15 have composition effects of 0.04 or less.
- **It is somewhat smoother than FIRI v2** (0.063 vs 0.072 mean quarterly change).
- **Band changes are frequent** (20 of 70 provincial pairs), because many scores sit near 0.5. Users should read the band together with the leave-one-out range.
