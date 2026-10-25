# E111 Quarterly generalization

**Measure.** Quarter differential vs the latest reading (RW): the mean over the 4 SWS areas of |error| − |error of RW|. Negative means better. Development evidence.

## Lead 1 (true horizon mostly 2 quarters)

| Target quarter | ASYM | LLR | BRK | Context (Balance Luzon) |
|---|---|---|---|---|
| 2023-Q2 | −0.63 | −1.24 | −1.24 | stable, low |
| 2023-Q3 | −0.75 | −0.89 | −0.89 | stable |
| 2023-Q4 | −1.34 | −1.45 | −1.45 | rise begins |
| 2024-Q1 | −0.53 | −0.06 | −0.06 | rising |
| 2024-Q2 | −0.56 | +0.37 | +0.37 | **surge** |
| 2024-Q3 | −0.58 | +2.23 | +2.23 | **surge** |
| 2024-Q4 | 0.00 | +4.02 | +4.02 | **surge to 25%** |
| 2025-Q2 | 0.00 | −1.91 | −1.91 | fall (survey change) |
| 2025-Q3 | −0.17 | −0.17 | 0.00 | rise |
| 2025-Q4 | −0.29 | −0.29 | 0.00 | fall |
| 2026-Q1 | −0.45 | −1.22 | −0.82 | rise |
| 2026-Q2 | **+0.33** | −0.18 | −0.10 | fall |
| 2026-Q3 | −0.22 | −0.84 | −0.80 | rise |

## By segment

| Segment | ASYM, Lead 1 | LLR, Lead 2 |
|---|---|---|
| Early / middle / recent thirds | −0.81 / −0.29 / −0.16 | −0.63 / −0.50 / −0.97 |
| Rising area-quarters | **−0.78** | −0.23 |
| Falling area-quarters | **+0.27** (fails) | −1.57 |
| Sharp increases (mean underprediction vs RW) | 8.71 vs 10.18 | 9.91 vs 10.60 |
| Sharp decreases (MAE vs RW) | 9.57 vs 9.29 | 5.31 vs 9.13 |
| Stable (MAE vs RW) | 2.42 vs 2.59 | 2.64 vs 2.94 |
| From 2025-Q2 (survey change) | −0.13 | −1.42 |
| Last four quarters (2025-Q4..2026-Q3) | −0.16 | −0.97 |
| Leave-one-quarter-out, worst case | −0.32 (still better) | −0.47 (still better) |
| Without the inferred 2021 cells (S-NOINF) | MAE 4.51 vs RW 4.84 | 4.85 vs 5.53 |

## Answers

**Consistent across early, middle and recent periods?**
- ASYM (Lead 1) and LLR (Lead 2): yes. Both are better than RW in every third and in the last four quarters.
- Plain smoothing (LLR) at Lead 1: no. It loses in the 2024 surge.

**Rising and falling hunger?** No method helps in both directions.
- **ASYM** helps when hunger rises and, by construction, cannot help when it falls (+0.27).
- **LLR at Lead 2** helps in both directions, but stays outside the ±4-point Balance Luzon accuracy bound.

**Sharp increases?** **No method detects them.**
- The miss rate is 0.8–1.0 for every method.
- ASYM reduces underprediction by about 1.5 points at Lead 1, the only consistent surge improvement.
- The 2024 surge (14% → 25%) was not anticipated by any method or indicator.

**Driven by a few quarters?** No. The ASYM and LLR gains survive removing any single quarter.

**The 2025 survey change?**
- Gains persist after 2025-Q2.
- Restarting the filter at the change (BRK) adds nothing over LLR.

**Generalizes beyond these quarters?** Unknown.
- ASYM was designed after E110 had shown the surge pattern on these quarters.
- Its consistency here is therefore not independent confirmation; only the sealed prospective forecasts can provide that.
