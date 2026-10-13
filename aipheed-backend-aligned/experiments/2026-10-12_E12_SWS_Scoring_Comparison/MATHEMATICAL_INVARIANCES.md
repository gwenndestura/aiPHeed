# Mathematical Invariances (documented before the grid; verified on synthetic data and on 2021–2025 data)

**Definitions:**

- D[p, t] = F[p, t] − mean of the five provinces' F[t], defined only when all five provinces have F.
- Option A: Score[p, t] = α·H[t] + β·D[p, t].

| # | Property | Why | Verified |
|---|---|---|---|
| 1 | Σ_p D[p, t] = 0 for complete quarters | D is a deviation from the five-province mean | Synthetic test 1 |
| 2 | **α shifts all five provincial scores in a quarter equally** (by α·H[t]) | H[t] is one regional value shared by all five provinces | Synthetic test 2 |
| 3 | For β > 0, **the within-quarter ranking equals the ranking of D**, for every α | Adding a constant and scaling by β > 0 preserve order | Synthetic test 2; all 36 historical combinations |
| 4 | **Within-quarter spread = β × spread(D)** | The α·H term cancels in max − min | Synthetic test 4; all 36 combinations |
| 5 | **Changing α alone cannot improve ranking or spread** | Follows from 3 and 4 | Synthetic tests 2–3 |
| 6 | Combinations with the same α/β are scale-equivalent: Score = β·(r·H + D) with r = α/β | Factor out β | 36 combinations → **22 distinct ratios** |
| 7 | With consistently transformed thresholds, equal-ratio scores classify identically. For r = 1/2, Score = (β/2)·S1, so threshold (β/2)·τ0 reproduces S1 exactly. | Scaling both sides by β/2 > 0 | Synthetic test 5; all 5 S1-equivalent combinations give 56 HIGH out of 80, identical to S1 |
| 8 | **Option C (D alone) = Option A with α = 0.** It is not an independent model. | Definition | Synthetic test; group "0/1" has 6 combinations |
| 9 | Option B with wH = 0 is a rescaled D (same ranking as D). With wH = 1 it is a rescaled H: constant within a quarter, no ranking. | Z is affine with a positive scale | Synthetic test; E12 data |
| 10 | Option B with 0 < wH < 1 equals Option A with a **fold-dependent** effective ratio (wH/σH)/(wF/σD), plus a constant shift | Expand the Z terms | E12: at wH = 0.5 the effective ratio ranged 0.35–0.90 across folds |
| 11 | Under D alone, every complete quarter has at least one province above the mean and one below. A threshold at 0 always labels some provinces HIGH and some LOW. | Σ D = 0 | E12: 1–3 above and 2–4 below in every quarter |

**Consequence:**

- Within a quarter, **every** combined score (any α ≥ 0 with β > 0, or 0 ≤ wH < 1) produces **the same provincial ranking as D**.
- The weight on regional hunger changes only the **level all five provinces share**. It can therefore change HIGH/LOW only through a level threshold, and it moves all five provinces together.
