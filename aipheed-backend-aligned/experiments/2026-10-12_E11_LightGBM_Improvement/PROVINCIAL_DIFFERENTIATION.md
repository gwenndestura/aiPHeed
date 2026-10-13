# E11 Provincial Differentiation

## 1. Predicted vs true spread (max − min stress across the five provinces, per quarter; expanding window)

| | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q4 |
|---|---|---|---|---|---|---|---|
| **True** | 8.27 | 6.53 | 9.93 | 12.60 | 12.53 | 14.67 | 6.53 |
| S1 rule | 10.67 | 10.87 | 8.27 | 6.53 | 9.93 | 12.60 | 6.93 |
| Carry-forward | 10.67 | 10.87 | 8.27 | 6.53 | 9.93 | 12.60 | 14.67 |
| Regional | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Direct core | 7.09 | 6.99 | **0.16** | **0.34** | **0.00** | **0.00** | 2.05 |
| Direct compact | 6.99 | 7.23 | 3.03 | 4.60 | 2.77 | 4.54 | 4.02 |
| Direct expanded | 5.73 | 5.91 | 2.01 | 4.11 | 0.91 | 3.59 | 4.26 |
| Decomposed | 5.64 | 6.75 | 7.02 | 7.33 | 3.14 | 4.24 | 5.10 |
| Residual | 10.93 | 10.94 | 8.08 | 3.23 | 8.23 | 10.29 | 6.12 |

## 2. Ranking agreement with the S1 target

Mean concordant share of the 10 province pairs per quarter (0.5 = no information):

| Model | Concordant share |
|---|---|
| **Decomposed** | **0.707** |
| Residual | 0.629 |
| S1 rule / carry-forward | 0.614 |
| Direct core | 0.529 |
| Direct expanded | 0.521 |
| Direct compact | 0.457 |
| Direct core_plus | 0.436 |
| Regional | 0.500 (no ranking) |

## 3. Error by province (MAE over 7 quarters)

| | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|
| S1 rule | 3.49 | 4.59 | 8.76 | 2.95 | 2.96 |
| Carry-forward | 3.64 | 4.94 | 11.15 | 2.68 | 3.70 |
| Regional | 3.01 | 4.30 | 8.33 | 3.12 | 3.58 |
| Direct core | 2.21 | 4.80 | 10.11 | 3.01 | 3.83 |
| Decomposed | 2.83 | 4.49 | 9.42 | 3.18 | 3.06 |
| Residual | **1.12** | **3.47** | 8.32 | **2.25** | 3.55 |

## 4. Why the direct LightGBM models flatten provinces

1. **Regional inputs dominate.**
   - SWS, its change, regional CPI and unemployment are identical for all five provinces (0% within-quarter variance).
   - The direct models put 61–100% of their split gain on these inputs and on last published stress.
   - With 5 rows per quarter and shallow trees, the splits separate quarters, not provinces.
2. **The provincial signal is real but weak and unstable.**
   - `cpi_rel` and `anchor_dev` are purely provincial; they correlate 0.60 and 0.55 with the realized deviation d (in-sample, descriptive).
   - The observed province ordering changes a lot between consecutive test quarters (Kendall τ: 0.8, 0.0, 0.2, 1.0, 0.6, 0.2).
3. **It is not mainly over-regularization.** Direct models flatten under every configuration, from stumps to C3.
4. **The formula carries the provincial variation.** The structures that keep the S1 provincial term preserve spread. Only the **decomposed** model improves ranking agreement (0.707 vs 0.614), and it does so without improving stress error.

## 5. Conclusions

- **Direct LightGBM cannot learn meaningful provincial differences** from the approved data.
- **Learning only the provincial deviation (decomposed) ranks provinces somewhat better** than the S1 rule in these 7 quarters. That evidence is weak: 7 reused quarters with unstable rankings.
- **The S1 rule remains the most defensible method for provincial differentiation.**
- **No city or municipal training observations exist,** so none were created.
