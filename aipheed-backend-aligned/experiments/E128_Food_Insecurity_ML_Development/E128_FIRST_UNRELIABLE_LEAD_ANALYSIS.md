# E128 first unreliable lead

**The first unreliable lead is Lead 1 (3 months) for every model, under both targets.** Reliability does not "begin to deteriorate" at a later lead. It is never established.

## Failed criteria by lead, all models (T1)

| Model | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| LightGBM | R1 R2 R4 R5 R6 R7 | R1 R3 R4 R5 | R1 R3 R4 R5 | R1 R2 R3 R4 R5 R6 R7 |
| Persistence | R1 R4 R5 | R1 R3 R4 R5 | R1 R3 R4 R5 | R1 R3 R4 R5 |
| PSA-only | R1 R2 R4 R5 R7 | R1 R3 R4 R5 | all | all |
| NLP-only | R1 R2 R3 R4 R5 R7 | R1 R3 R4 R5 | R1 R3 R4 R5 | R1 R2 R3 R4 R5 R7 |
| Logistic Regression | R1 R2 R4 R5 R7 | R1 R3 R4 R5 | R1 R2 R3 R4 R5 R7 | all |

**Why persistence cannot pass.** R4 and R5 require beating persistence, so persistence fails them by construction. It is the no-skill reference.

## Size of each failure, LightGBM T1

| Criterion | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| R1 rows (need 40) / quarters (need 10) | 13 / 13 | 8 / 8 | 7 / 7 | 6 / 6 |
| R2 accuracy (need 0.75) | 0.615 | 0.875 | 0.857 | **0.000** |
| R3 balanced accuracy (need 0.70) | 0.773 | not evaluable (0 LOW) | not evaluable | not evaluable |
| R4 accuracy vs persistence | 0.615 < 0.846 | 0.875 < 1.000 | 0.857 < 1.000 | 0.000 < 1.000 |
| R5 Brier vs persistence (p) | 0.332 vs 0.154 (0.97) | 0.082 vs 0.000 (1.00) | 0.208 vs 0.000 (1.00) | 0.704 vs 0.000 (1.00) |
| R6 recall (need 0.60) | 0.545 | 0.875 | 0.857 | 0.000 |
| R7 minimum third / leave-one-quarter-out minimum | 0.40 / 0.58 | 0.67 / 0.86 | 0.67 / 0.83 | 0.00 / 0.00 |

## Affected origins, and consistent vs isolated failures

**Lead 1.** All errors are false negatives in the high-hunger regime: targets 2023-Q4, 2024-Q1, 2024-Q2, 2025-Q2 and 2025-Q3. This is **consistent**: the model extrapolates the 2021–23 low-hunger years.

**Lead 4.** All 6 origins, 2024-Q2 .. 2025-Q3, fail. Also consistent: the training targets (2021-Q2 .. 2024-Q3) are mostly LOW.

**The structural failures (R1 at all leads; R3, R4 and R5 at Leads 2–4) are the same at every origin.** No origin set exists that could pass them.

## Associated feature groups and data limitations

| Factor | Evidence |
|---|---|
| Hunger history | The only stable source of correct calls (persistence). Removing it from LightGBM changes Brier by −0.003 to −0.334 (mostly improving it), because the model uses it badly at long leads (Lead 4: hunger mean = 79 % of influence, but trained on low-regime levels). |
| Climate (ONI) | Dominant at T1 Lead 2 (76 %); a period marker (see SHAP) |
| Market | Its removal effect changes sign by lead (T1: +0.005, +0.011, −0.122, −0.048) |
| Employment / OFW, news | Small, inconsistent effects |
| Poverty | No time-varying regional series; not testable |
| Data limitations | 20 quarters; target saturation; ±6-point sampling error; national or lagged predictors; regime shift between the training and evaluation years |

## Deterioration with horizon (descriptive, T4, where both classes exist)

| Measure | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| LightGBM balanced accuracy | 0.81 | 0.37 | 0.60 | 0.50 |
| LightGBM Brier | 0.21 | 0.40 | 0.52 | 0.53 |
| Persistence balanced accuracy | 0.77 | 0.47 | 0.65 | 0.63 |
| Persistence Brier | 0.18 | 0.50 | 0.29 | 0.33 |

Lead 2 is where every T4 model drops to chance. This matches LEAD2-series findings that conditions two quarters ahead are not predictable from current inputs. With 8 rows it is descriptive only.
