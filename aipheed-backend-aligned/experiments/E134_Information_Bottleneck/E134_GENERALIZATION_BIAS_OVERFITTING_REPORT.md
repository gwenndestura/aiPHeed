# E134 generalization, bias and overfitting report

## Generalization by regime (Lead 2, P-DASH)

**Within tolerance by target period** (`out/e134_metrics.csv`, sets `period:*`):
- pre-surge ≤ 2023: 28 rows / 7 quarters;
- surge 2024: 16 rows / 4 quarters;
- post-break 2025+: 24 rows / 6 quarters.

| Model | Pre-surge | Surge 2024 | Post-break 2025+ |
|---|---|---|---|
| PERSIST | 0.54 | 0.25 | 0.50 |
| SEAS-LLM | 0.64 | 0.06 | **0.71** |
| HFM-NS-DES | 0.71 | 0.00 | 0.67 |
| HFM-X | 0.50 | **0.56** | 0.46 |
| E134-AREA-T | 0.50 | 0.56 | 0.46 |
| E134-ONI | 0.61 | 0.56 | 0.46 |
| E134-ENS | 0.71 | 0.31 | 0.58 |
| CLIM | 0.75 | 0.06 | 0.21 |

**MAE by period:**

| Model | Pre-surge | Surge | Post-break |
|---|---|---|---|
| HFM-X | 3.48 | 5.84 | 4.22 |
| SEAS-LLM | 2.71 | 9.00 | 3.54 |
| E134-ONI | 3.11 | 4.76 | 3.94 |

**Finding: no model generalizes across regimes.**
- Driver models (HFM-X family) are the only ones that work in the surge. They lose 0.2–0.25 of agreement after the 2025 break, where design structure dominates.
- Level and design models are the reverse.
- The equal ensemble (E134-ENS) averages the two and is best in neither.

**By area** (S-U, Lead 2, HFM-X): Metro Manila 0.80, Balance Luzon 0.60, Visayas 0.40, Mindanao 0.20. **Not demonstrated across areas.**

**Unseen periods:** none exist in the window. Only the prospective seals can supply them.

## Bias (Lead 2, S-U)

| Model | Overall | Low tercile | Mid tercile | High tercile |
|---|---|---|---|---|
| SEAS-LLM | −3.19 | −0.85 | −1.23 | −7.64 |
| HFM-X | −2.53 | +1.62 | −2.10 | −7.14 |
| E134-AREA-T | −3.36 | +1.20 | −2.82 | −8.49 |
| E134-ONI | −2.10 | +1.97 | −1.26 | −7.07 |

- **High-hunger under-prediction persists.** About 2 points of it is irreducible: ORACLE-LEVEL, which knows the true target level, still shows −2.0 (E133 D4). The rest is lag behind true change.
- No E134 change reduces it materially without raising low-tercile over-prediction.
- **By area:** errors are largest in Mindanao and Visayas, which have the smaller samples (SE about 2.4 against 1.6 for Balance Luzon) and the largest 2024 jumps.

## Overfitting

| Check | Result |
|---|---|
| Parameters / observations | HFM-X 10 / 80. E134-AREA-T 12 / 80. |
| In-sample one-step vs out-of-sample Lead-1 MAE | HFM-X 3.10 vs 4.70 (E133) |
| Regularization sensitivity | β prior SD 0.5 / 1 / 2 gives Lead-2 within 0.475 / 0.50 / 0.40 (E133). A looser prior overfits. |
| Adding data-rich drivers | +aR +aP worsens Lead-2 MAE 4.87 → 5.39 (p = 0.97 that the extra drivers help). More inputs fit noise. |
| Perturbation | Delaying the area drivers one quarter: Lead-2 MAE 5.39 → 5.53 (stable, small) |
| Feature stability | The market β rises 0.41 → 1.04 between the 2023-Q4 and 2025-Q4 issues (E133). It is learned largely from one episode, so it is **not stable**. |
| Selection on development data | Every comparison uses values seen in E110–E133. The candidate is prospective only. |
