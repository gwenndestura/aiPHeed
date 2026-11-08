# LightGBM optimisation report (E168)

- **Protocol:** `PROTOCOL.md` (b1be8c39), fixed before results.
- **Code:** `backend/app/e168/lgbm_only.py`.
- **Outputs:** `backend/data/e168/out/` (`all_rows.csv`, `results.json`).

## Search, inside training rows only (region GroupKFold(5), weighted logit SSE)
- **Baselines:** {H, OH, RSS}.
- **Feature sets:** {GOV, FULL} × {without, with consumption}, each with or without in-fold correlation pruning (|ρ| > 0.95).
- **LightGBM grid:**
  - `num_leaves` {3, 7};
  - `min_child_samples` {10, 40};
  - `reg_lambda` {5, 20};
  - `n_estimators` {150, 400};
  - fixed: learning rate 0.02, feature and bagging fraction 0.8, monotone constraints.
- **Total:** 384 LightGBM configurations per origin.

## What training-only selection chose
| Origin | Baseline | Features | LightGBM |
|---|---|---|---|
| 2018, 2019 | OH (own survey history) | GOV, pruned to **20** columns | **3 leaves**, min leaf 10, λ 20, **150 trees** |
| 2021 | RSS | FULL, pruned to 62 columns | 3 leaves, min leaf 10, λ 5, 150 trees |

- **The most constrained LightGBM won every time.**
- Class weighting was not used (HIGH ≥ 50 is a definition), and the threshold was fixed at 0.5.

## Result, Lead 1 (n = 72, effective about 46)
| | E158 | E166 | **E168 (LightGBM)** |
|---|---|---|---|
| Accuracy | 73.6 % | 76.4 % | **75.0 %** |
| Balanced accuracy | 0.760 | 0.800 | 0.780 |
| HIGH precision / recall | 0.58 / 0.84 | 0.61 / 0.92 | 0.60 / 0.88 |
| LOW precision / recall | 0.89 / 0.68 | 0.94 / 0.68 | 0.91 / 0.68 |
| F1 (HIGH) / macro F1 | 0.69 / 0.73 | 0.73 / 0.76 | 0.71 / 0.75 |
| AUC | 0.860 | 0.904 | 0.891 |
| Brier | 0.1344 | 0.1247 | **0.1230** |
| Bias (points) | +2.9 | +3.25 | **+2.97** |
| Confusion (TP / FP / FN / TN) | 21 / 15 / 4 / 32 | 23 / 15 / 2 / 32 | 22 / 15 / 3 / 32 |

**Paired comparison with E158:**
- Brier −0.011 [−0.033, +0.011].
- McNemar: 4 rows right only for E168, 3 only for E158, p = 1.0.
- **Not significant.**

## Lead 2
| | E158 | E168 |
|---|---|---|
| Accuracy | 73.6 % | **77.8 %** |
| Brier | 0.1371 | 0.1221 (−0.015 [−0.039, +0.010]) |
| McNemar | | 5 vs 2, p = 0.45 |

## By round, Lead 1 (accuracy / Brier)
| Round | E158 | E168 |
|---|---|---|
| 2018 | 63.6 % / 0.150 | 68.2 % / 0.152 |
| 2019 | 68.0 % / 0.172 | **76.0 % / 0.137** |
| 2021 | 88.0 % / 0.083 | 80.0 % / 0.084 |

## CALABARZON back-test error (points), E158 → E168
| Row | E158 | E168 |
|---|---|---|
| Laguna 2018 | +9.3 | **+3.8** |
| Quezon 2019 | +4.0 | **+0.8** |
| Rizal 2019 | +3.6 | −4.8 |
| Batangas 2021 | −13.7 | −11.3 |
| Cavite 2021 | −6.2 | −6.7 |

All classes remain correct (LOW).
