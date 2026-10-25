# E110 Quarterly generalization report

**Method.**
- **Loss differential:** d_q = mean over the 4 SWS areas of (|error of method| − |error of RW|) in target quarter *q*. Negative means better than the latest reading.
- **Panel rows only;** the same rows for every method.
- **All quarters had been seen before** (development evidence).

## 1. Quarter by quarter (negative = better than RW)

**Lead 1** (issue date = day 1 of the target quarter; the latest reading is usually two quarters old):

| Target | COMB | LLR | MA2 | Hunger direction (Balance Luzon) |
|---|---|---|---|---|
| 2024-Q1 | −0.53 | −0.06 | −0.20 | rising |
| 2024-Q2 | +0.18 | +0.37 | +0.91 | rising (surge) |
| 2024-Q3 | +1.12 | +2.23 | +1.21 | rising (surge) |
| 2024-Q4 | +2.01 | +4.02 | +1.37 | rising (surge to 25%) |
| 2025-Q2 | −0.96 | −1.91 | −0.71 | falling |
| 2025-Q3 | −0.08 | −0.17 | −0.19 | rising |
| 2025-Q4 | −0.28 | −0.29 | −0.06 | falling |
| 2026-Q1 | −0.73 | −1.22 | −0.49 | rising |
| 2026-Q2 | −0.47 | −0.18 | +0.76 | falling |
| 2026-Q3 | −0.42 | −0.84 | −0.41 | rising |

**Lead 2:**

| Target | COMB | LLR | MA2 |
|---|---|---|---|
| 2024-Q3 | +0.18 | +0.37 | +0.91 |
| 2024-Q4 | +1.12 | +2.23 | +1.21 |
| 2025-Q2 | −1.95 | −3.21 | −2.94 |
| 2025-Q3 | −0.75 | −1.40 | +0.46 |
| 2025-Q4 | +0.08 | +0.44 | +1.86 |
| 2026-Q1 | −0.51 | −1.03 | −2.07 |
| 2026-Q2 | −0.73 | −1.46 | −1.71 |
| 2026-Q3 | −0.91 | −1.82 | −2.51 |

## 2. Generalization checks (`results.json` → `decision[...].parts`)

| Check | LLR, Lead 1 | COMB, Lead 1 | LLR, Lead 2 | COMB, Lead 2 |
|---|---|---|---|---|
| Early / middle / recent thirds | +0.85 / +0.65 / −0.63 | +0.26 / +0.32 / −0.48 | +1.30 / −1.39 / −1.44 | +0.65 / −0.87 / −0.72 |
| Falling area-quarters | −1.21 | −0.67 | −1.89 | −1.07 |
| Rising area-quarters | **+0.80** | **+0.26** | +0.06 | −0.00 |
| From 2025-Q2 (after the survey change) | −0.77 | −0.49 | −1.42 | −0.80 |
| Last four quarters (2025-Q4..2026-Q3) | −0.63 | −0.48 | −0.97 | −0.52 |
| Leave-one-quarter-out worst case | +0.43 | +0.09 | −0.38 | −0.22 |
| Areas better than RW | 1 of 4 | 1 of 4 | 3 of 4 (BL equal) | 4 of 4 (BL by only 0.03) |

## 3. Answers

- **Consistent across early, middle and recent periods?** No.
  - Smoothing methods lose in 2024 (the surge) and win from 2025.
  - The latest reading does the opposite.
- **Works when hunger rises and when it falls?** No single method does.
  - Smoothing helps when hunger falls back.
  - It hurts when hunger rises, which is the case that matters most for early warning.
- **Sharp changes:** the 2024-Q2..Q4 surge (14% → 25%) was missed by every method. The smoothers missed it by more.
- **Depends on a few quarters?** Partly.
  - At Lead 2 the LLR gain survives removing any one quarter (worst case −0.38).
  - It does not survive splitting by period or by direction.
- **Survey-design change:**
  - after 2025-Q2 the smoothers look better;
  - adding the registered-voter round (S-VOTERS) changes nothing;
  - the "design effect" is not consistent across areas (root-cause report H5).
- **Better than simple baselines in eligible periods?** On average, only at Lead 2, and not in every period.
- **Stable under reasonable assumptions?** The conclusions hold under S-VOTERS and S-R4.

**Conclusion.** No method generalizes across quarters. The sample (10 and 8 quarters) contains essentially two regimes: a surge (2024) and a noisy, oscillating plateau (2025–26). A method tuned to either fails in the other.
