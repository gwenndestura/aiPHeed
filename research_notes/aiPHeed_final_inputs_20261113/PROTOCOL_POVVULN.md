# PROTOCOL_POVVULN — poverty and social vulnerability as FINAL inputs (written 2026-11-13 BEFORE any arm below is fitted or scored)

Owner requirement (2026-11-13): poverty and social vulnerability must be tested as actual LightGBM inputs (selection and training),
not dashboard-only information. Engine, folds, leads, seeds, threshold, target and labels are those of PROTOCOL_INPUTS (sha 4cb830c6).

## Data (official, provincial, no interpolation, no regional-to-provincial conversion)
- PSA Full Year Official Poverty Statistics, all four bases, rounds 2006, 2009, 2012, 2015, 2018, 2021, 2023
  (PSA OpenSTAT DB/3D 0013/0023/0033/0043C3DP*, DB/1F/FY 0011/0031/0051/0071F3DF*; backend/app/hcw/poverty_official.py ->
  backend/data/hcw_official/raw/psa_poverty_by_province.csv). The 2006-2015 families tables are published rounded to whole percents.
- PSA census population 2010, 2015, 2020, 2024 and land area (backend/data/e137/raw/psa/population_2010_2024.csv, land_area_density_2024.csv).

## Availability rules (forecast origin = first day of the issue quarter)
- Poverty round R usable from 1 January of R+2 (the existing E137 rule); the latest usable round is carried forward (last released value).
- Census C usable from 1 January of C+2.

## Features
POVERTY (provincial):
  pv_fam, pv_pop, sb_fam, sb_pop  logit of the latest usable round's incidence (families / population; poverty / subsistence);
                                  monotone sign +1
  d_pv_pop, d_pv_fam              change in logit between the latest and the previous usable round (+1)
  p_poverty_gap                   existing FINAL input (latest round), +1
VULNERABILITY (provincial):
  p_density_c                     log(population / land area), latest released census (sign 0)
  p_popgrowth                     annual % growth between the two latest released censuses (sign 0)

## Arms (Leads 1 and 2; 5 seeds; folds ENNS2018, ENNS2019, ENNS2021)
  P0    FINAL without its poverty/vulnerability columns (p_poverty, p_subsistence, p_poverty_gap, p_density and their flags).
  P1    P0 + POVERTY in the candidate pool (FINAL's 25-input selection decides).
  P2    P0 + VULNERABILITY in the pool.
  P3    P0 + POVERTY + VULNERABILITY in the pool.
  P1F, P2F, P3F  as P1-P3 with those indicators always kept (forced past the selection; pruning and signs unchanged).
  Reference: B0 = FINAL as sealed (PROTOCOL_INPUTS parts).

## Evaluation
Per round and pooled, seed mean and per seed: confusion matrix, accuracy, HIGH precision, recall, F1, AUC, Brier, log loss,
share predicted HIGH. Paired bootstrap (3000) of Brier/log-loss differences vs P0 (contribution of the added group) and vs B0.
Redundancy: Spearman correlations among all poverty/vulnerability features on training rows. Selection counts per arm.

## Decision rule (fixed now; same as PROTOCOL_INPUTS)
An arm replaces FINAL (B0) only if, at Leads 1 and 2 for the 5-seed mean: (1) pooled accuracy, precision, recall, F1 >= 0.75 and
AUC >= 0.75; (2) pooled Brier <= B0 + 0.005; (3) no round loses HIGH recall vs B0 and at least one round gains HIGH F1;
(4) among qualifying arms, lowest 2018+2019 log loss. A group is "predictive" if adding it to P0 lowers pooled Lead-1 Brier with a
bootstrap 95 % CI entirely below 0 (or removing it raises it, CI above 0); otherwise "contextual" or "no effect", with the numbers.
