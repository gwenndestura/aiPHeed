# Deliverable 5. Baseline comparison report

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

Baselines are formed only from values available by 1 January of the reference year (rule: a survey value is usable from
1 January of reference year + 2, which is later than every actual PSA release).

## Ranking baselines
| outcome | year | key | n | spearman | p_one_sided | top1_hit | years_positive | n_years |
|---|---|---|---|---|---|---|---|---|
| FNRI15_SEV | 2015 | BASE:poverty_prior | 5 | 0.70 | 0.12 | 1.00 | – | – |
| ENNS_SEV | mixed | BASE:poverty_prior | 5 | 0.30 | 0.34 | 1.00 | – | – |
| ENNS_SEV | mixed | BASE:fnri2015_severe | 5 | 0.70 | 0.12 | 1.00 | – | – |
| ENNS_MODSEV | mixed | BASE:poverty_prior | 5 | -0.10 | 0.61 | 0.00 | – | – |
| ENNS_MODSEV | mixed | BASE:fnri2015_severe | 5 | -0.10 | 0.61 | 0.00 | – | – |
| PSA_SUB_FAM | 2018 | BASE:poverty_prior | 5 | 0.90 | 0.04 | 1.00 | – | – |
| PSA_SUB_FAM | 2021 | BASE:poverty_prior | 5 | 0.32 | 0.30 | 1.00 | – | – |
| PSA_SUB_FAM | 2023 | BASE:poverty_prior | 5 | -0.72 | 0.93 | 0.00 | – | – |
| PSA_SUB_FAM | pooled | BASE:poverty_prior | 15 | 0.17 | 0.29 | – | 2.00 | 3.00 |
| PSA_SUB_FAM | 2018 | BASE:fnri2015_severe | 5 | 0.50 | 0.23 | 1.00 | – | – |
| PSA_SUB_FAM | 2021 | BASE:fnri2015_severe | 5 | 0.11 | 0.43 | 1.00 | – | – |
| PSA_SUB_FAM | 2023 | BASE:fnri2015_severe | 5 | 0.36 | 0.32 | 0.00 | – | – |
| PSA_SUB_FAM | pooled | BASE:fnri2015_severe | 15 | 0.32 | 0.14 | – | 3.00 | 3.00 |
| PSA_SUB_FAM | 2021 | BASE:prior_wave_PSA_SUB_FAM | 5 | 0.32 | 0.30 | 1.00 | – | – |
| PSA_SUB_FAM | 2023 | BASE:prior_wave_PSA_SUB_FAM | 5 | -0.70 | 0.93 | 0.00 | – | – |
| PSA_SUB_FAM | pooled | BASE:prior_wave_PSA_SUB_FAM | 10 | -0.19 | 0.70 | – | 1.00 | 2.00 |
| PSA_SUB_FAM | 2021 | BASE:prior_wave_PSA_SUB_POP | 5 | 0.32 | 0.30 | 1.00 | – | – |
| PSA_SUB_FAM | 2023 | BASE:prior_wave_PSA_SUB_POP | 5 | -0.76 | 0.97 | 0.00 | – | – |
| PSA_SUB_FAM | pooled | BASE:prior_wave_PSA_SUB_POP | 10 | -0.22 | 0.72 | – | 1.00 | 2.00 |

## Level accuracy, PSA food poverty (temporal validation: 2018 → 2021, 2018 + 2021 → 2023)
| outcome | test_year | candidate | n | mae | rmse | bias | spearman | noise_floor_mae |
|---|---|---|---|---|---|---|---|---|
| PSA_SUB_FAM | 2021 | L0 | 5 | 0.92 | 1.16 | -0.68 | 0.32 | 0.33 |
| PSA_SUB_FAM | 2021 | L1 | 5 | 1.10 | 1.70 | -0.78 | – | 0.33 |
| PSA_SUB_FAM | 2021 | L2 | 5 | 0.92 | 1.16 | -0.68 | 0.32 | 0.33 |
| PSA_SUB_FAM | 2021 | L3 | 5 | 1.03 | 1.36 | -0.78 | 0.32 | 0.33 |
| PSA_SUB_FAM | 2023 | L0 | 5 | 1.42 | 2.01 | 0.98 | -0.70 | 0.21 |
| PSA_SUB_FAM | 2023 | L1 | 5 | 0.80 | 0.89 | 0.80 | – | 0.21 |
| PSA_SUB_FAM | 2023 | L2 | 5 | 0.98 | 1.50 | 0.64 | -0.87 | 0.21 |
| PSA_SUB_FAM | 2023 | L3 | 5 | 1.29 | 1.75 | 0.86 | -0.87 | 0.21 |
| PSA_SUB_FAM | 2023 | L4 | 5 | 1.94 | 2.65 | 0.32 | -0.36 | 0.21 |
| PSA_SUB_POP | 2021 | L0 | 5 | 1.28 | 1.56 | -1.00 | 0.41 | 0.49 |
| PSA_SUB_POP | 2021 | L1 | 5 | 1.60 | 2.38 | -1.16 | – | 0.49 |
| PSA_SUB_POP | 2021 | L2 | 5 | 1.28 | 1.56 | -1.00 | 0.41 | 0.49 |
| PSA_SUB_POP | 2021 | L3 | 5 | 1.44 | 1.83 | -1.15 | 0.41 | 0.49 |
| PSA_SUB_POP | 2023 | L0 | 5 | 2.10 | 2.80 | 1.26 | -0.82 | 0.39 |
| PSA_SUB_POP | 2023 | L1 | 5 | 1.08 | 1.19 | 1.00 | – | 0.39 |
| PSA_SUB_POP | 2023 | L2 | 5 | 1.46 | 2.17 | 0.76 | -0.90 | 0.39 |
| PSA_SUB_POP | 2023 | L3 | 5 | 1.91 | 2.44 | 1.09 | -0.82 | 0.39 |
| PSA_SUB_POP | 2023 | L4 | 5 | 2.60 | 3.45 | 0.25 | -0.40 | 0.39 |

Candidates (fixed in the protocol): L0 = prior wave (persistence); L1 = CALABARZON prior-wave value for every province; L2 = mean of the province's prior waves; L3 = prior wave shrunk to the regional prior wave by w = tau2/(tau2+se2), tau2 = max(0, var(prior) - mean(se2)); L4 = ridge alpha=1 on standardized [prior subsistence, prior poverty, FI10 Lead-2 mean price-pressure p] trained on the 2018->2021 transition; 2023 only.
The noise floor is the MAE a perfect predictor of the true value would still have against the published estimate.

## Reading
- **The best ranking baseline for food poverty is the 2015 FNRI severe ranking** (pooled ρ = 0.32, positive in 3 of 3 waves,
  p = 0.14). Prior poverty is the only cell below p = 0.05 (2018, ρ 0.90) but reverses in 2023 (−0.72).
- **The provincial ordering of food poverty is not stable:** 2018 vs 2021 ρ = 0.32, 2021 vs 2023 ρ = −0.70. Quezon fell
  from 4.7 % to 0.5 % of families. A persistence forecast of the ranking fails in 2023.
- **No level candidate wins both waves.** Persistence is best for 2021 (MAE 0.92 pp); the regional prior-wave value is best
  for 2023 (0.80 pp); the ridge with price pressure and poverty (trained on five rows) is worst (1.94 pp). The best candidate's
  error is 2.8–3.8× the noise floor because the whole region moved (COVID-19 rise in 2021, fall in 2023).
- **No model beats these baselines.** The only models that can be compared on the same rows (FI10, pooled) are below
  every positive baseline.
