# Deliverable 4. Provincial validation report

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

Metrics: Spearman rank correlation between the model's provincial score and the published value (n = 5 per year), exact
one-sided permutation p over the 120 possible orders (smallest possible p = 0.008), top-1 hit (same worst province),
top-2 overlap. **MAE, RMSE and bias cannot be computed for any model:** every model outputs a probability of a
price-pressure or T43c event, not a percentage of households, so its level cannot be compared with a survey percentage.
Brier, AUC and classification metrics need binary labels, which the data do not support (Deliverable 11).

## Track A: FNRI 2015 severe food insecurity (FI10 only)
| year | key | n | spearman | p (one-sided) | top1_hit | top2_overlap | coverage |
|---|---|---|---|---|---|---|---|
| 2015 | FI10_L1sel · L1 | 5 | -0.20 | 0.66 | 0.00 | 1.00 | full |
| 2015 | FI10_L1sel · L2 | 5 | -0.30 | 0.74 | 0.00 | 1.00 | full |
| 2015 | FI10_L2sel · L1 | 5 | -0.20 | 0.66 | 0.00 | 1.00 | full |
| 2015 | FI10_L2sel · L2 | 5 | -0.10 | 0.61 | 0.00 | 1.00 | full |
| 2015 | FI10_damped · L1 | 5 | -0.20 | 0.66 | 0.00 | 1.00 | full |
| 2015 | FI10_damped · L2 | 5 | -0.20 | 0.66 | 0.00 | 1.00 | full |
| 2015 | FI10_naive · L1 | 5 | -0.20 | 0.66 | 0.00 | 1.00 | full |
| 2015 | FI10_naive · L2 | 5 | -0.10 | 0.61 | 0.00 | 1.00 | full |

## Track A: ENNS (mixed reference years; secondary)
**Severe**
| year | key | n | spearman | p (one-sided) | top1_hit | top2_overlap | coverage |
|---|---|---|---|---|---|---|---|
| mixed | FI10_L1sel · L1 | 5 | -0.90 | 0.99 | 0.00 | 0.00 | full |
| mixed | FI10_L1sel · L2 | 5 | -0.90 | 0.99 | 0.00 | 0.00 | full |
| mixed | FI10_L2sel · L1 | 5 | -0.90 | 0.99 | 0.00 | 0.00 | full |
| mixed | FI10_L2sel · L2 | 5 | -0.50 | 0.82 | 0.00 | 0.00 | full |
| mixed | FI10_damped · L1 | 5 | -0.70 | 0.93 | 0.00 | 0.00 | full |
| mixed | FI10_damped · L2 | 5 | -0.60 | 0.88 | 0.00 | 1.00 | full |
| mixed | FI10_naive · L1 | 5 | -0.70 | 0.93 | 0.00 | 0.00 | full |
| mixed | FI10_naive · L2 | 5 | -0.30 | 0.74 | 0.00 | 1.00 | full |

**Moderate-to-severe**
| year | key | n | spearman | p (one-sided) | top1_hit | top2_overlap | coverage |
|---|---|---|---|---|---|---|---|
| mixed | FI10_L1sel · L1 | 5 | -0.30 | 0.74 | 0.00 | 0.00 | full |
| mixed | FI10_L1sel · L2 | 5 | -0.30 | 0.74 | 0.00 | 0.00 | full |
| mixed | FI10_L2sel · L1 | 5 | -0.30 | 0.74 | 0.00 | 0.00 | full |
| mixed | FI10_L2sel · L2 | 5 | -0.80 | 0.96 | 0.00 | 0.00 | full |
| mixed | FI10_damped · L1 | 5 | -0.60 | 0.88 | 0.00 | 0.00 | full |
| mixed | FI10_damped · L2 | 5 | -0.50 | 0.82 | 0.00 | 0.00 | full |
| mixed | FI10_naive · L1 | 5 | -0.60 | 0.88 | 0.00 | 0.00 | full |
| mixed | FI10_naive · L2 | 5 | -0.60 | 0.88 | 0.00 | 0.00 | full |

## Track B: PSA food poverty (families), served P0H4 family, 2023
| year | key | n | spearman | p (one-sided) | top1_hit | top2_overlap | coverage |
|---|---|---|---|---|---|---|---|
| 2023 | CH1-LGBM · L1 | 5 | -0.36 | 0.75 | 0.00 | 0.00 | full |
| 2023 | CH1-LGBM · L2 | 5 | 0.16 | 0.40 | 0.00 | 1.00 | partial |
| 2023 | CR · L1 | 5 | 0.46 | 0.22 | 0.00 | 1.00 | full |
| 2023 | CR · L2 | 5 | -0.05 | 0.55 | 0.00 | 1.00 | partial |
| 2023 | CR-ANC · L1 | 5 | 0.15 | 0.42 | 0.00 | 1.00 | full |
| 2023 | CR-ANC · L2 | 5 | 0.15 | 0.42 | 0.00 | 1.00 | partial |
| 2023 | E108 · L1 | 5 | -0.21 | 0.67 | 0.00 | 0.00 | full |
| 2023 | P0H4 · L1 | 5 | 0.55 | 0.17 | 0.00 | 1.00 | full |
| 2023 | P0H4 · L2 | 5 | 0.67 | 0.13 | 0.00 | 1.00 | partial |
| 2023 | P0H4-U · L1 | 5 | 0.55 | 0.17 | 0.00 | 1.00 | full |
| 2023 | P0H4-U · L2 | 5 | 0.36 | 0.32 | 0.00 | 1.00 | partial |
| 2023 | P0H4_price · L1 | 5 | 0.82 | 0.07 | 0.00 | 1.00 | full |
| 2023 | P0H4_price · L2 | 5 | 0.36 | 0.32 | 0.00 | 1.00 | partial |
| 2023 | UNI-FINAL · L1 | 5 | 0.55 | 0.17 | 0.00 | 1.00 | full |
| 2023 | UNI-FINAL · L2 | 5 | 0.67 | 0.13 | 0.00 | 1.00 | partial |

## Track B: PSA food poverty (families), FI10, every wave and pooled
| year | key | n | spearman | p (one-sided) | top1_hit | top2_overlap | coverage |
|---|---|---|---|---|---|---|---|
| 2018 | FI10_L1sel · L1 | 5 | -0.50 | 0.82 | 0.00 | 0.00 | full |
| 2021 | FI10_L1sel · L1 | 5 | -0.58 | 0.87 | 0.00 | 0.00 | full |
| 2023 | FI10_L1sel · L1 | 5 | -0.21 | 0.67 | 0.00 | 1.00 | full |
| pooled | FI10_L1sel · L1 | 15 | -0.43 | 0.93 | – | – | full |
| 2018 | FI10_L1sel · L2 | 5 | -0.70 | 0.93 | 0.00 | 0.00 | full |
| 2021 | FI10_L1sel · L2 | 5 | -0.58 | 0.87 | 0.00 | 0.00 | full |
| 2023 | FI10_L1sel · L2 | 5 | 0.36 | 0.32 | 1.00 | 1.00 | full |
| pooled | FI10_L1sel · L2 | 15 | -0.31 | 0.85 | – | – | full |
| 2018 | FI10_L2sel · L1 | 5 | -0.70 | 0.93 | 0.00 | 0.00 | full |
| 2021 | FI10_L2sel · L1 | 5 | -0.58 | 0.87 | 0.00 | 0.00 | full |
| 2023 | FI10_L2sel · L1 | 5 | -0.05 | 0.55 | 0.00 | 1.00 | full |
| pooled | FI10_L2sel · L1 | 15 | -0.44 | 0.94 | – | – | full |
| 2018 | FI10_L2sel · L2 | 5 | -0.70 | 0.93 | 0.00 | 0.00 | full |
| 2021 | FI10_L2sel · L2 | 5 | -0.58 | 0.87 | 0.00 | 0.00 | full |
| 2023 | FI10_L2sel · L2 | 5 | 0.36 | 0.32 | 1.00 | 1.00 | full |
| pooled | FI10_L2sel · L2 | 15 | -0.31 | 0.85 | – | – | full |
| 2018 | FI10_damped · L1 | 5 | -0.30 | 0.74 | 0.00 | 0.00 | full |
| 2021 | FI10_damped · L1 | 5 | -0.79 | 0.97 | 0.00 | 0.00 | full |
| 2023 | FI10_damped · L1 | 5 | -0.05 | 0.55 | 0.00 | 1.00 | full |
| pooled | FI10_damped · L1 | 15 | -0.38 | 0.90 | – | – | full |
| 2018 | FI10_damped · L2 | 5 | -0.30 | 0.74 | 0.00 | 0.00 | full |
| 2021 | FI10_damped · L2 | 5 | -0.58 | 0.87 | 0.00 | 0.00 | full |
| 2023 | FI10_damped · L2 | 5 | 0.36 | 0.32 | 1.00 | 1.00 | full |
| pooled | FI10_damped · L2 | 15 | -0.17 | 0.72 | – | – | full |
| 2018 | FI10_naive · L1 | 5 | -0.30 | 0.74 | 0.00 | 0.00 | full |
| 2021 | FI10_naive · L1 | 5 | -0.79 | 0.97 | 0.00 | 0.00 | full |
| 2023 | FI10_naive · L1 | 5 | -0.05 | 0.55 | 0.00 | 1.00 | full |
| pooled | FI10_naive · L1 | 15 | -0.38 | 0.90 | – | – | full |
| 2018 | FI10_naive · L2 | 5 | 0.10 | 0.47 | 0.00 | 1.00 | full |
| 2021 | FI10_naive · L2 | 5 | -0.58 | 0.87 | 0.00 | 0.00 | full |
| 2023 | FI10_naive · L2 | 5 | 0.46 | 0.22 | 0.00 | 2.00 | full |
| pooled | FI10_naive · L2 | 15 | -0.01 | 0.51 | – | – | full |

Population-based results (`ranking_agreement.csv`, outcome `PSA_SUB_POP`) are within 0.1 of the family results.

## Reading
- **FI10 price-pressure forecasts rank provinces in the opposite order to food poverty.** Pooled ρ is between −0.44 and
  −0.01 at Leads 1–2, with no positive year at Lead 1. The realised price excess itself has ρ = -0.45:
  provinces with more food-price pressure had *less* food poverty. Against FNRI 2015 and ENNS the signs are also negative.
- **Served P0H4, 2023 food poverty:** ρ = 0.55 at Lead 1, p = 0.17; Lead 2 (three quarters) ρ = 0.67.
  Not significant; one year, five provinces; the 2023 provinces are themselves not distinguishable (Q p = 0.09);
  about 40 model × lead cells were scored on these five values, so a p near 0.07–0.17 is expected by chance; and its
  top score is a Laguna–Rizal tie that the tie-break gives to Laguna, so it misses the worst province (Rizal). Lead 4 is ρ = −0.76.
- **No model reaches the locked rank-skill rule** (exact p < 0.05 and above the best baseline) on any outcome.
