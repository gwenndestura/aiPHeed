# Provincial Differentiation (E12)

## 1. Which formula components create provincial differences?

| Score | Within-quarter ranking | Within-quarter spread |
|---|---|---|
| H only | **None** (constant across provinces) | 0 |
| D only (Option C) | Ranking of D | spread(D) |
| S1 = H + 2D | **Identical to D's ranking** in all 16 labelled quarters | 2 × spread(D) |
| Option A, any α, β > 0 | **Identical to D's ranking** (36/36 combinations) | β × spread(D); α has no effect |
| Option B, 0 ≤ wH < 1 | **Identical to D's ranking** (all folds) | (1 − wH)/σD × spread(D) |
| Option B, wH = 1 | None | 0 |

**Mean within-quarter spread of Option A by β** (independent of α):

| β | 0.5 | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 |
|---|---|---|---|---|---|---|
| Spread | 2.42 | 4.83 | 7.25 | 9.67 (= S1) | 12.08 | 14.50 |

**Finding: all provincial differentiation in S1 and its variants comes from D.** Changing the SWS weight (α) does not change any province's rank or the spread between provinces. β only rescales the spread.

## 2. How strong and stable is the provincial signal?

| Measure | Value | Source |
|---|---|---|
| Quarters with all five provinces' F | **20 / 20** | `QUARTERLY_RESULTS.csv` |
| Range of D within a quarter (max − min, pp) | 1.37 to 7.33 | Same |
| Rank agreement with the previous quarter (Kendall τ) | 0.0 to 1.0; median 0.6. Low at 2021-Q3→Q4 (0.0), 2024-Q1→Q2 (0.0) and 2024-Q2→Q3 (0.2) | Same |
| Typical ordering 2022–2023 | Rizal and Batangas highest; Quezon lowest | Same |
| Typical ordering 2024–2025 Q1 | **Quezon highest**; the lowest varies (Laguna, Cavite, Rizal) | Same |
| Typical ordering 2025-Q4 | Laguna highest; Batangas lowest | Same |
| Own-score persistence of D (latest published vs realized; normalized MAE) | 0.90 SD; concordance 0.614 | `BASELINE_COMPARISON.csv` |

**Interpretation:** relative food-price pressure differs meaningfully between provinces in every quarter. **The ranking shifts substantially over time.** Quezon moved from lowest to highest between 2023 and 2024. The latest published ranking therefore predicts the next one only moderately.

## 3. What this does and does not show

- It shows **where provincial food prices rose faster or slower than the five-province average.**
- It does **not** show which province has more food insecurity: no province-level outcome exists.
- **No city or municipal observations exist,** so none were created.
