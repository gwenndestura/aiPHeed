# 142 LGU priority rankings

File: `backend/data/e150/out/issue/lgu_priority_2027-Q1.csv`. Checks: `issue/lgu_validation.json`.

**These rank LGUs by vulnerability within a province-level forecast. They are not municipal food-insecurity measurements or forecasts.**

## Method

Priority = province P(HIGH ≥ 50) × vulnerability, where vulnerability = 0.6 × poverty percentile + 0.4 × density percentile across the 142 LGUs (PSA SAE 2021; POPCEN 2024).

* **Percentile normalization** limits the effect of extreme density in dense cities.
* **0.6/0.4 weights** are the ones this project already uses. **Please confirm they match the thesis.**

## Province differences in the ranking

Median rank in the region: Quezon 21, Cavite 53, Rizal 70, Batangas 102.5, Laguna 109.5.

Within-province score range, showing LGUs are separated by their own vulnerability: Quezon 0.125, Cavite 0.076, Rizal 0.061, Laguna 0.047, Batangas 0.039. There are 135 unique scores among 142 LGUs.

## Top LGUs

| Rank | LGU | Province | Score | 90 % rank range | P(top 20) |
|---|---|---|---|---|---|
| 1 | Plaridel | Quezon | 0.130 | 1 to 52 | 0.68 |
| 2 | Pagbilao | Quezon | 0.129 | 2 to 54 | 0.65 |
| 3 | Candelaria | Quezon | 0.128 | 3 to 56 | 0.63 |
| 4 | Agdangan | Quezon | 0.128 | 4 to 57 | 0.62 |
| 5 | Lucena | Quezon | 0.127 | 5 to 58 | 0.59 |
| 6 | Tiaong | Quezon | 0.125 | 6 to 61 | 0.55 |

## Effect of provincial uncertainty

5,000 draws of each province's forecast, re-ranking every LGU.

| Check | Result |
|---|---|
| Mean width of the 90 % rank range | **72 places of 142** |
| LGUs with P(top 20) above 0.9 | **0** |
| LGUs with P(top 20) between 0.1 and 0.9 | 51 |

**Provincial uncertainty dominates the ranking. No LGU is a firm top-20 priority.** The rank order within a province is much firmer than the order between provinces. So DA can use it most safely to compare LGUs within one province.

## Sensitivity to weights

| Poverty/density | Spearman with 0.6/0.4 | Top-20 overlap |
|---|---|---|
| 0.5/0.5 | 0.99 | 19 |
| 0.7/0.3 | 0.99 | 18 |
| 1.0/0.0 | 0.90 | 14 |
| 0.0/1.0 | 0.11 | 2 |

Stable around the chosen weights, but it shifts substantially if either component is removed. Density alone gives a very different list.

## Validation limits

* **No municipal food-insecurity measurement is held,** so the ranking cannot be validated against a municipal outcome. Operation Timbang LGU rows measure child nutrition, not food insecurity, so they are not used as validation, and CBMS 2024 is not held.
* **Province-level check only:** population-weighted LGU poverty against latest measured food insecurity gives Spearman 0.70, n = 5. Too few to rely on, and measurement years differ.
* **Is the poverty link defensible?** Yes for concept: E150's poverty inputs are the main structural predictor. **Is density's link defensible?** It's an exposure measure, not evidence of hunger, and density's role is the weaker part of this index.

**What would validate it:** CBMS 2024 LGU-level FIES, which gives a direct cross-sectional test of rank agreement.
