# E159 result: ranking test

The criteria are in `RANKING_TEST_CRITERIA.md`, committed in fde622cb before any result was computed. The code is `backend/app/e159/ranking.py` and the output is in `backend/data/e159/out/`.

## Lead 1
| Measure | E158 | Latest survey (PERS) | E158 − PERS |
|---|---|---|---|
| Within-region concordance, 40 pairs | **0.60** [0.44, 0.73] | **0.70** [0.55, 0.84] | −0.10 [−0.28, +0.07] |
| Same, gaps ≥ 5 points, 15 pairs | 0.60 [0.33, 0.82] | 0.80 [0.60, 1.00] | −0.20 [−0.46, 0.00] |
| Spearman, 2018 / 2019 / 2021 | 0.72 / 0.54 / 0.65 | 0.59 / 0.62 / 0.67 | |
| Spearman, mean | 0.635 | 0.627 | |

- **R1, ranks provinces within a region: FAIL.** The interval's lower bound is 0.44, below 0.5.
- **R2, ranks provinces nationally: PASS.** Spearman is positive in all three rounds.
- **R3, adds to the latest survey: FAIL.** E158 is no better than the latest survey and points worse. The latest survey alone passes R1.

Leads 2 to 4 give the same picture. On large-gap pairs E158 is significantly worse than the latest survey at Lead 3 (−0.33 [−0.54, −0.14]) and Lead 4 (−0.27 [−0.50, −0.06]).

## Meaning
- E158 orders provinces nationally about as well as the latest survey (Spearman 0.63 for both). This ordering comes mostly from differences between regions.
- Within one region, E158's ordering is not reliable. It is less reliable than simply keeping each province's latest survey order. The shared regional level, which drives E158's accuracy on the 50 line, also flattens the differences between provinces in the same region.

## CALABARZON, row by row (no claim)
| Round | Province | Latest survey | E158 | Survey result |
|---|---|---|---|---|
| 2018 | Laguna | 41.4 | 35.5 | 26.2 |
| 2019 | Quezon | 48.8 | 48.0 | 44.0 |
| 2019 | Rizal | 41.3 | 42.7 | 39.1 |
| 2021 | Batangas | 43.5 | 26.2 | 39.9 |
| 2021 | Cavite | 41.8 | 29.3 | 35.5 |

- In 2019, both arms put Quezon above Rizal. Both were right.
- In 2021, E158 put Cavite above Batangas and was wrong; the latest survey was right. E158 also cut Batangas by 17 points, and the result fell only 4 points. This is the same pattern as the 2027-Q1 forecast.

## Consequence (per the fixed rule)
- E158's order within a region is not evidence. **The 2027-Q1 order Rizal > Cavite > Quezon > Laguna > Batangas must not be presented as a ranking.**
- The current LGU priority list must not be used as validated, because it multiplies LGU poverty by each province's chance of HIGH, which depends on that order.
- E158's HIGH/LOW class and its Lead 1 results are unaffected.
- The model is not changed.
