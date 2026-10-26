# Final LightGBM data validation

Checks run on the audited training tables (`out/training_table_lead{1..4}.csv`) and on the model that uses them
(CH1-LGBM, one primary LightGBM price model over all 12 families × the SWS hunger condition).

## 1. Every indicator reaches the model

All 12 families have at least one column in every training table (16 model columns). SHAP share of the price model
(audited inputs, mean |SHAP| by family):

| Family | Lead 1 | Lead 2 |
|---|---|---|
| A1 food-price pressure | 0.665 | 0.454 |
| E1 unemployment | 0.075 | 0.038 |
| H1 hunger outlook | 0.065 | 0.025 |
| E2 remittances | 0.054 | 0.001 |
| C4 fisheries | 0.052 | 0.002 |
| A3 rice | 0.036 | 0.021 |
| C3 palay/corn | 0.026 | 0.134 |
| V1 vulnerability | 0.013 | 0.011 |
| C2 typhoons | 0.009 | 0.000 |
| N1 news | 0.004 | 0.313 |
| A2 headline inflation | 0.001 | 0.000 |
| C1 El Niño | 0.000 | 0.000 |

C1 has zero share because it is a national on/off flag that is constant over most training windows; it is kept, as
the protocol requires all 12 families. At Lead 2 news takes a large share, and the news ablation shows that share
hurts (§4).

## 2. No future information (issue-date checks)

| Check | Result |
|---|---|
| newest SWS round used is published before the issue date | all rows (test `test_training_tables_use_only_information_published_before_issue`) |
| newest news item used is published before the issue date | all rows |
| newest CPI month + 5 days release lag is before the issue date | all rows |
| labels for target quarters 2026-Q4 and later | none present (0 non-null in every table) |
| leakage perturbation audit (10 origins; future data altered → forecasts unchanged) | passed (`FINAL_THESIS_OBJECTIVES/out/leakage_audit.json`); same code used for the audited rerun |

## 3. Independent outcome counts (what the 75% is measured on)

| Quantity | Count |
|---|---|
| SWS rounds 2021+ (regular, non-commissioned) | 23 |
| Quarters with a Balance Luzon reading (the independent hunger values) | 20 |
| T43c-labelled province-quarters | 100 (20 quarters × 5 provinces) |
| HIGH labels | 19 |
| Lead-1 evaluation rows | 70 (14 target quarters × 5), 17 HIGH |
| Mean pairwise correlation of provincial food YoY | 0.70 |

The 70 Lead-1 rows are **not** 70 independent outcomes: the hunger term is one regional value per quarter and
provincial prices move together. All intervals are therefore cluster-bootstrapped by quarter (14 clusters).

## 4. Pooled SWS areas vs Balance Luzon only

Pooling the other SWS areas (NCR, Visayas, Mindanao) can legitimately help only the *noise estimate* σ of the hunger
condition; using another area's reading as CALABARZON's outcome would create artificial labels, so it was not done.

| Variant (Lead 1, audited inputs) | Accuracy | 90% CI |
|---|---|---|
| Primary: σ from Balance Luzon errors | 0.914 | 0.843–0.971 |
| Sensitivity: σ pooled over the 4 areas | 0.929 | 0.857–0.986 |

The difference is one row out of 70. The primary stays as frozen; the sensitivity is reported only.

## 5. Corrections versus result

| | First run (held inputs) | Audited inputs |
|---|---|---|
| Lead 0 accuracy / AUC | 0.850 / 0.792 | 0.850 / 0.804 |
| Lead 1 accuracy / Brier / AUC | 0.914 / 0.089 / 0.923 | 0.914 / 0.087 / 0.923 |
| Lead 2 accuracy | 0.533 | 0.583 |
| Lead 3 accuracy | 0.520 | 0.520 |
| Lead 4 accuracy | 0.575 | 0.575 |
| Max reliable lead | 1 | 1 |

The corrections change E2 (the most-changed column) and C2, which carry small shares; the classification at Lead 1 is
identical, and no verdict changes. Data quality was not what limited the forecasts.
