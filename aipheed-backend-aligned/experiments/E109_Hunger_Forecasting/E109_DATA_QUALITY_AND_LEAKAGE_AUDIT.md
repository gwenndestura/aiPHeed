# E109 Data quality and leakage audit

## 1. Outcome data

| Check | Result |
|---|---|
| Values match SWS releases | 12 of 24 rounds checked in E109, all match (§5 of the source audit). The rest were verified in E31. |
| Publication dates | per round in `sws_rounds.csv`. June 2025 (2025-08-15), September 2025 (2025-11-05) and September 2026 (2026-10-14) re-confirmed. |
| Commissioned rounds | 1 (Stratbase-SWS March 2025), excluded from the primary series |
| Respondent-base change | household heads → registered voters → adults (2025). Disclosed; sensitivity S-HH. |
| Quarter value | mean of the quarter's non-commissioned rounds by fieldwork date (2021-Q2, 2022-Q2 and 2025-Q2 have two rounds) |
| Real-time vintage | **Defect found and fixed before scoring (Addendum 1).** The frozen rule hid a published round when a later round of the same quarter would follow, which uses future knowledge. Inputs and training targets now use the rounds published before the issue date. |
| Dependence | one row per quarter; nothing replicated across provinces. At Leads ≥ 2 consecutive errors overlap, so the Diebold–Mariano test uses Newey–West lag *k* − 1 with the HLN correction, and the MAE intervals use a moving-block bootstrap (block = *k*). |
| Sample size | 20 outcome quarters; 9 evaluable at Lead 1, 7 at Lead 2, 6 at Lead 3, 5 at Lead 4 |

## 2. Predictors: the 12 FIRI families (E107 registry, unchanged)

**Construction.** All 13 columns come from `e107_lib.feature_table(k)` and are averaged over the five provinces per origin, because the outcome is regional. The E107 provenance, publication rules, missingness and future-perturbation tests still apply (E107 `INDICATOR_AUDIT.md`; E108 per-family tests). Regional aggregation changes their meaning:

| Family | At regional level |
|---|---|
| A1, A2, A3, C3, C4 | five-province means of provincial values |
| C1, E1, E2, H1 | national or regional already, unchanged |
| C2 | mean typhoon count |
| **V1** | **constant** (a static provincial profile averaged over provinces), so it cannot inform a regional time series |
| N1 | mean over provinces with ≥ 5 headlines; missing in most quarters |

**Which families the fitted LightGBM actually used** (`results.json` → `family_usage`, mean |SHAP| share):

| Lead | Used (share) | Never split |
|---|---|---|
| 1 | A1 0.36, A2 0.23, H1 0.11, C1 0.09, C4 0.07, E2 0.06, C3 0.05, E1 0.02, A3 0.01 | C2, N1, V1 |
| 2 | E2 0.52, C3 0.12, E1 0.10, C1 0.07, N1 0.06, C2 0.05, A2 0.05, A3 0.03 | A1, C4, H1, V1 |
| 3 | C1 0.64, H1 0.28, E2 0.04, A2 0.03, A3 0.01 | 7 families |
| 4 | E2 0.44, H1 0.36, A3 0.13, C1 0.07 | 8 families |

**Instability.** The set of families used changes from lead to lead and origin to origin. With 8–17 training quarters per fit this is expected, and no family has a stable contribution.

**Ablation at Lead 1** (MAE; full model 4.04):

| Removed | MAE |
|---|---|
| affordability | 4.61 |
| hunger | **3.76** |
| household economy | **3.95** |
| others | about the same |

Removing hunger or household economy *improves* the model, and neither version beats the random walk (3.72).

**Interpretation.** Limited influence reflects the **data** (8–17 training quarters, one regional outcome) more than the model. A V1 or N1 contribution cannot be observed in a regional time series of this length.

## 3. Leakage checks (`backend/tests/unit/test_e109.py`, run 2026-10-25)

| Test | Checks |
|---|---|
| `test_outcome_rounds_match_the_project_sws_file_and_the_commission_rule` | values, commission flag |
| `test_primary_quarter_values_are_round_means_and_cover_20_quarters` | target construction |
| `test_known_at_issue_uses_publication_dates` | real-time vintages (Addendum 1) |
| `test_training_pairs_never_use_an_outcome_unknown_at_the_issue` (4 leads) | no target ≥ the issue date; targets equal the vintage known at the issue |
| `test_future_sws_rounds_do_not_change_any_forecast` | a copy of every round shifted by +30 points and published in 2027 leaves all 7 methods' forecasts and σ̂ unchanged at Leads 1–2 |
| `test_negative_control_a_round_published_before_the_issue_does_change_the_forecast` | the perturbation test is not vacuous |
| `test_local_level_parameters_use_only_known_quarters` | Kalman inputs |
| `test_thresholds_are_the_protocol_values` | B1–B4, margin |
| `test_lightgbm_uses_the_13_columns_of_all_12_families` | feature map |
| `test_regional_rows_are_one_per_origin` | no province replication |
| `test_stored_predictions_reproduce` (4 leads) | determinism |
| `test_scored_under_frozen_protocol_with_clean_runner` | protocol hash, clean runner |
| `test_all_three_seals_unchanged` | E107, E108 and E109 seals |
| `test_api_and_every_lgu_has_a_truthful_status` | API; all 142 LGUs labelled "insufficient local evidence" |

**Result: 20 of 20 passed** (`pytest tests/unit/test_e109.py`).

Feature-level future perturbation for the 12 families is covered by the E107 (51) and E108 (50) suites, which still pass.

## 4. What was already seen (honesty about the evidence)

- Every evaluated quarter (2024-Q2..2026-Q3) was examined in E69–E108, and earlier work had already found that the latest reading is hard to beat.
- E109's rules were frozen before scoring, but the evaluation is **retrospective development evidence**.
- **No E109 result has been confirmed on unseen outcomes.**
