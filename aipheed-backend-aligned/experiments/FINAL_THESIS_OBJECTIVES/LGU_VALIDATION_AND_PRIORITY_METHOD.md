# LGU priority method and what validates it (Objective 3)

## Method (served)

For each of the 142 cities and municipalities (`backend/app/quarterly/lgu_poverty.py`, `lgu_audit.py`):

```
vulnerability = 0.6 × poverty_norm + 0.4 × density_norm      (min-max normalised)
priority     = P(HIGH) of the LGU's province × vulnerability  (clamped to [0, 1], 4 dp)
```

- Poverty: PSA 2021 municipal Small Area Estimates (141 LGUs). Lucena City has no own estimate; the Quezon value is
  used and labelled as a substitute.
- Density: POPCEN 2024 population ÷ land area.
- P(HIGH): the CH1-LGBM province forecast, validated at Lead 1.
- Ranks are given within province and region.

## What validates it, and what does not

| Claim | Status |
|---|---|
| The province probability it starts from is validated | **Yes**, at Lead 1 (accuracy 0.914) |
| The poverty and density inputs are the official figures | **Yes**: 141/142 SAE, 142/142 POPCEN reconciled against the PSA workbooks |
| The LGU priority equals a measured municipal food-insecurity rate | **No.** No municipal outcome exists openly (CBMS 2024 LGU data not published) |
| The ranking is useful to planners | **Not yet tested.** Chapter I's Hypothesis 4 judges this by DA evaluators' assessments; that survey has not been held |

Within a province the order is fixed by vulnerability, because every LGU shares the province probability. The
forecast changes how high the whole province sits, not the order inside it. The dashboard says so on every LGU row
("Relative position within the province … Not a measured or official municipal food-insecurity rate").

FNRI face validity (Objective 5, not a validation of the ranking): ENNS/NNS show food insecurity is about twice as
common among poor households as non-poor ones, which supports weighting poverty most.
