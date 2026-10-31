# Generalization and bias (E117)

## Overfitting

**Training error is about half of test error for every variant.**

| Variant | Mean training MSE (change target) | Pooled test MSE |
|---|---|---|
| Base | 19.2 | 30-35 |
| All domains (H) | 15.5 | 30-35 |

- The domains lower training error by about 4 points.
- Pooled test error does not fall, and rises with news.
- This is overfitting to features that do not generalize.

## Temporal generalization and contribution stability

The sign of each Δ MSE (vs base) by period is in `INDIVIDUAL_INDICATOR_RESULTS.csv` and `DOMAIN_CONTRIBUTION_RESULTS.csv`.

| Indicator / domain | Lead 1 (P1 / P2 / P3) | Lead 2 (P1 / P2 / P3) | Stability |
|---|---|---|---|
| C3 palay/corn drop | −1.03 / −1.01 / −0.15 | −1.27 / −0.25 / +1.25 | **stable at Lead 1**; not at Lead 2 |
| C4 fish production | −0.77 / −0.16 / −0.64 | −0.40 / −0.22 / +0.76 | consistent sign at Lead 1, small; significant only in P1 |
| Market (group) | +1.41 / +2.20 / **−6.73** | −0.27 / +1.15 / **−5.88** | **only 2021-26** (the inflation/rice-price regime) |
| A3 rice | +2.50 / +0.99 / **−8.24** | +0.75 / +2.60 / **−7.36** | only 2021-26 |
| News N1 | n/a / +2.87 / +2.66 | n/a / +3.10 / +8.73 | consistently worse |
| Climate group, employment, ONI, typhoons | mixed signs | mixed signs | not established |

**Reading.**
- **Market prices:** the relationship appears only in the most recent regime. It may be real, but it cannot be distinguished from a regime-specific pattern until new quarters arrive.
- **Production (palay):** the Lead-1 signal holds in all three periods.

## Areas (pooled MAE, Lead 2)

| Model | NCR | Balance Luzon | Visayas | Mindanao |
|---|---|---|---|---|
| LightGBM base | 4.11 | 4.23 | 4.45 | 5.58 |
| Full (I) | 4.36 | 4.22 | 4.48 | 5.73 |
| Mean reversion | 4.94 | 4.03 | 4.35 | 5.40 |
| Persistence | 4.44 | 4.71 | 4.46 | 6.17 |

- **Mindanao** is the hardest area for every model; it has the most volatile series.
- **Balance Luzon** is the area that covers CALABARZON.
  - At Lead 2, mean reversion is best there (4.03), and the LightGBM variants are about 4.2.
  - At Lead 1, mean reversion is also best there (3.76).

## Bias and representativeness

**Dependence.**
- The four areas share the national inputs (rice CPI, ENSO, typhoons, unemployment, news) and the same quarters.
- All tests average by quarter, so 90 quarters, not 360 rows, is the effective sample.

**Periods.**
- **Back-cast CPI before 2018.** Market features for P1-P2 use PSA's 2018=100 back-cast, not the published vintage.
- **2025 respondent-base change.** In P3, SWS switched from household heads to adults, which raised the level.

These are structural changes the models may partly learn as regime effects.

**Class balance.** The "above usual" event is defined from history known at each issue (41-59% positive by period). It was not rebalanced.

**Geography.** No provincial outcome exists, so no provincial generalization can be measured. Provincial vulnerability is a profile, not a forecast.
