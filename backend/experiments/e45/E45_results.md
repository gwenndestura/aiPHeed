# E45: threshold (τ) definitions on the served model (E48-A1 + E49-C2)

Experiment only; the live system, records, frontend and `backend/data` are untouched.

- **Run:** `20261015T234042Z` (`E45_results.json`, `runner/e45_run.py`).
- **Kept fixed:** S1 = H + 2D; the E48-A1 features (E36's 13 inputs + the 5 trigger proportions); E36's walk-forward, grid, seed 36, nested rule and lead 1; E49-C2 shrinkage fitted only on earlier dates (raw p for the first 4 dates).
- **What τ may use:** only S1 of quarters ≤ t−1 whose SWS rounds were all published before the origin.
- **Inputs that depend on τ:** τ also feeds two E36 inputs, H_margin and the last published label. They are computed with each variant's own τ (per province under T3).

| Variant | τ |
|---|---|
| T0 (current) | median of all pooled S1, 2021-Q2..t−1 |
| T1 | median of pooled S1 over the last 4 published quarters |
| T2 | median of pooled S1 over the last 8 published quarters |
| T3 | median of that province's own S1 over its last 8 published quarters |

**Reproduction.** T0 = E49-C2 exactly: accuracy 0.846, Brier 0.1509, Q4 2026 CALABARZON 0.778 (Batangas 0.335), drivers Market 65 / Climate 33 / Fish Kill 2.

## Labels

| Variant | HIGH, all 85 labelled (2021-Q3..2026-Q3) | HIGH, 65 test rows | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Labels ≠ T0 |
|---|---|---|---|---|---|---|---|---|---|
| T0 | 70.6% | 81.5% | 0% | 47% | 55% | 95% | 90% | 93% | – |
| T1 | 60.0% | 67.7% | 0% | 47% | 65% | 95% | **50%** | **47%** | 15.3% |
| T2 | 68.2% | 78.5% | 0% | 47% | 55% | 100% | 70% | 87% | 4.7% |
| T3 | 70.6% | 81.5% | 0% | 47% | 65% | 100% | 80% | 80% | 14.1% |

**τ at the latest origins** (2026-Q1 → Q4 targets):
- **T0:** 14.1 → 15.0.
- **T1:** 21.0 / 19.9 / 22.2 / 19.7.
- **T2:** 16.7 → 19.0.
- **T3 at Q4:** Cavite 18.4, Laguna 19.1, Quezon 23.6, Rizal 18.6, Batangas 17.5.

## Performance (65 test rows, each variant on its own labels)

| Variant | Accuracy | Bal. acc. | AUC | Brier | Log loss | Max p | p ≥ 0.95 | Persistence: acc / Brier | Always-HIGH: acc / Brier |
|---|---|---|---|---|---|---|---|---|---|
| **T0** | **0.846** | **0.841** | **0.855** | 0.151 | 0.489 | 0.945 | 0 | 0.877 / **0.123** | 0.815 / 0.185 |
| T1 | 0.615 | 0.554 | 0.675 | 0.263 | 0.772 | 0.969 | 8 | 0.785 / 0.215 | 0.677 / 0.323 |
| T2 | 0.785 | 0.733 | 0.707 | 0.197 | 0.629 | 0.945 | 0 | 0.769 / 0.231 | 0.785 / 0.215 |
| T3 | 0.738 | 0.614 | 0.638 | 0.192 | 0.575 | 0.922 | 0 | 0.754 / 0.246 | 0.815 / 0.185 |

## Adoption (rule fixed before results)

| Variant | Base rate 35–70% | Bal. acc. ≥ 0.75 | AUC ≥ 0.80 | Brier ≤ persistence | Acc. ≥ always-HIGH | Result |
|---|---|---|---|---|---|---|
| T0 | ✗ (70.6%) | ✓ | ✓ | ✗ (0.151 > 0.123) | ✓ | not acceptable |
| T1 | ✓ | ✗ | ✗ | ✗ | ✗ | not acceptable |
| T2 | ✓ (68.2%) | ✗ (0.733) | ✗ (0.707) | ✓ | ✓ (tie) | not acceptable |
| T3 | ✗ (70.6%) | ✗ | ✗ | ✓ | ✗ | not acceptable |

**No variant is acceptable**, so the current definition (T0) stays.

## Index per quarter (CALABARZON, calibrated; province values in `E45_results.json`)

| Quarter | T0 | T1 | T2 | T3 |
|---|---|---|---|---|
| 2023-Q1 | 0.400 | 0.400 | 0.400 | 0.594 |
| 2023-Q2 | 0.586 | 0.586 | 0.586 | 0.496 |
| 2023-Q3 | 0.356 | 0.592 | 0.356 | 0.455 |
| 2023-Q4 | 0.534 | 0.595 | 0.534 | 0.610 |
| 2024-Q1 | 0.389 | 0.406 | 0.389 | 0.367 |
| 2024-Q2 | 0.604 | 0.624 | 0.604 | 0.450 |
| 2024-Q3 | 0.559 | 0.565 | 0.531 | 0.731 |
| 2024-Q4 | 0.599 | 0.867 | 0.631 | 0.674 |
| 2025-Q1 | 0.812 | 0.624 | 0.817 | 0.795 |
| 2025-Q4 | 0.907 | 0.863 | 0.884 | 0.921 |
| 2026-Q1 | 0.907 | 0.863 | 0.882 | 0.921 |
| 2026-Q2 | 0.873 | 0.785 | 0.765 | 0.562 |
| 2026-Q3 | 0.912 | 0.731 | 0.834 | 0.868 |
| **2026-Q4** | **0.778** | **0.577** | **0.803** | **0.580** |

## Q4 2026 (origin 2026-10-01)

| Variant | CALABARZON | Cavite | Laguna | Quezon | Rizal | Batangas | Drivers (Market / Climate / Fish Kill / Empl. / OFW) |
|---|---|---|---|---|---|---|---|
| **T0 (served)** | **0.778** | 0.888 | 0.877 | 0.914 | 0.877 | 0.335 | 65 / 33 / 2 / 0 / 0 |
| T1 | 0.577 | 0.591 | 0.571 | 0.591 | 0.586 | 0.549 | 100 / 0 / 0 / 0 / 0 |
| T2 | 0.803 | 0.836 | 0.785 | 0.855 | 0.830 | 0.712 | 68 / 28 / 4 / 0 / 0 |
| T3 | 0.580 | 0.497 | 0.768 | 0.543 | 0.752 | 0.338 | 85 / 6 / 9 / 0 / 0 |

Driver shares use the live panel's method: the live engine code is loaded by file path and integer shares are pooled over the provinces.

## Verdict
**No threshold variant meets the adoption rule; keep T0 (the current trailing median of all pooled S1).**
- **Shorter windows:** they balance the labels better (T1 60%, T2 68% HIGH), but the model then can no longer separate HIGH from LOW. AUC falls to 0.64–0.71 and balanced accuracy to 0.55–0.73.
- **The province's own history (T3):** it does not help either.
- **T0 itself** fails the 70% base-rate cap narrowly (70.6%) and does not beat persistence on Brier (0.151 vs 0.123). It is still the only variant with AUC ≥ 0.80 and balanced accuracy ≥ 0.75.

**Q4 2026 index under the chosen (current) definition: CALABARZON 0.778.** Batangas is 0.335 (LOW); the other four provinces are 0.88–0.91.

**For your adviser** (what "HIGH" means under T0):
> A province-quarter is labelled HIGH when its food-stress score S1 (the regional SWS hunger rate plus twice the province's food inflation above the CALABARZON average) is above the median S1 of all earlier quarters from 2021 whose SWS results had been published before the forecast was made. HIGH therefore means "worse than the typical level seen since 2021", a relative judgement against the region's own recent history, not an absolute hunger cut-off. Because hunger and food prices rose in 2024–2026, most recent province-quarters (about 9 in 10) sit above that historical median, so the HIGH share and the forecast index are high in recent quarters.
