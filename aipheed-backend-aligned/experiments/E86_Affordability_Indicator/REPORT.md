# E86 — should S-COMP replace the served affordability indicator (A1)?

**Question.** Is the E84 S-COMP price-condition probability a better Lead-2 forecast of the provincial food-price
condition than the served E56-TUNED LightGBM price component (FIRI indicator A1)?

**Rows.** The 50 rows where both exist: targets 2024-Q2 .. 2026-Q3, 10 quarters, from the E57 sealed predictions.
18 are positive.

| Indicator | Accuracy | Balanced accuracy | HIGH recall | Brier | AUC |
|---|---|---|---|---|---|
| E56 LightGBM (served A1) | 0.78 | 0.78 | 0.78 | 0.182 | 0.79 |
| **S-COMP** | **0.80** | 0.78 | 0.72 | **0.159** | **0.84** |
| E83 S-SIM | 0.74 | 0.75 | 0.78 | 0.201 | 0.77 |

**Paired per-quarter Brier, S-COMP vs E56.** Gain +0.023, one-sided sign-flip p = 0.126 (10 quarters).

**Decision.**
- The gain is not significant at the project's p < 0.10 rule, so A1 is **not** replaced. The served model is
  unchanged.
- S-COMP is retained as the candidate and sealed (E84 seal ad402660…).
- It is the first two-quarter-ahead price forecast to reach 0.80 accuracy on these rows. That is price pressure,
  not food insecurity.
