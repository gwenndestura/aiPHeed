# E7 Protocol: Evidence-Based Indicator Influence

| Item | Value |
|---|---|
| Date | 2026-10-12 |
| Status | Frozen before any E7 code ran or any test-period outcome was examined |
| Scope | Isolated development backend. Approved window 2021–2025. No 2026 outcome. |

**This is the seventh analysis on the 7 reused test quarters, and it is run once.** All results are exploratory, and the effective sample is about 7 quarters.

## 1. What can and cannot be learned

**Equation 3 is the outcome definition:** stress = SWS + 2 × provincial food-inflation gap; the event is stress > τ.

- Its component weights **cannot be learned from data.** No independent food-insecurity outcome exists to fit them against, so learning α from a target defined by α would be circular.
- Equation 3 therefore stays the target definition, with α = 2 documented as unvalidated (E6). τ is frozen point-in-time: 10.843 retrospectively, 14.345 prospectively.

**What can be learned from evidence is how much each predictor contributes** to forecasting that outcome:

- LightGBM learns the (nonlinear) contributions.
- A **training-only** procedure decides which indicator groups enter.
- Outer-test ablation and permutation importance then **report** (not select) whether each group adds value on unseen quarters.

**Alternatives considered and rejected before running:**

| Alternative | Why rejected |
|---|---|
| A data-driven composite with estimated α | Circular, as above |
| Unsupervised weights (PCA or variance) | Measure variance, not food-insecurity relevance |
| Equal-weight z-composite | Evaluated in E5 (S2): 35/35 HIGH |

## 2. Indicator groups (development frame; all inputs as published before the origin; NaN kept)

| Group | Features | Scope |
|---|---|---|
| **R**: regional hunger and persistence | `sws_hunger`, `sws_change`, `last_published_stress` | Regional / lagged outcome |
| **GP**: provincial government | `cpi_rel`, `cpi_rel_lag1`, `cpi_dev`, `food_cpi` (level), `food_cpi_yoy`, `food_cpi_yoy_lag1`, `food_cpi_yoy_accel`, `rice_price_regular`, `rice_price_regular_lag1`, `rice_price_regular_accel`, `poverty_incidence` | Provincial |
| **GN**: national/regional government | `unemployment_rate` (+lag1, +accel), `ofw_remit_yoy_pct` (+lag1, +accel), `diesel_php_per_l` (+lag1, +accel), `gasoline_php_per_l`, `fx_usd_php_avg`, `brent_usd_per_bbl`, `headline_cpi`, `food_minus_headline_yoy` (+lag1, +accel), `enso_numeric`, `drought_alert`, `tc_count`, `tc_severe_flag`, `rainfall_anomaly_pct` (+lag1, +accel) | Shared by all provinces in a quarter |
| **N**: news | `FSSI`, `FSSI_lag1`, `FSSI_lag2`, `FSSI_accel`, `fssi_article_count`, `news_ph_fssi`, `news_ph_count`, `trigger_market`, `trigger_climate`, `trigger_fish_kill`, `trigger_employment`, `trigger_ofw_remittance` | Mixed |

**Training-only feature filter (applied inside every fold, before fitting):** drop a feature if, **in that fold's training rows**, it is missing in more than 50% of rows or has zero variance.

## 3. Configurations (LightGBM classifier unless stated)

**Common settings:**

- `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42;
- no class weighting;
- monotone +1 on `sws_hunger` and `last_published_stress` where present, 0 elsewhere.

| ID | Inputs |
|---|---|
| M0 | Existing configuration: the 12 Equation 5 inputs, with the served model's Optuna parameters and `class_weight="balanced"`, refitted per fold on time-valid inputs. *Its parameters were tuned on data that include the test quarters (disclosed).* |
| M1 | R (core) |
| M2 | GP + GN (government only) |
| M3 | N (news only) |
| M4 | GP + GN + N (government + news) |
| M5 | R + GP + GN + N (full) |
| **M6** | **Training-only selection** (§4). **This is the model implemented and served, whatever its outer-test result.** |

**Simple baselines:**

- carry-forward (last published stress > τ);
- Equation 3 rule (SWS input + 2·`cpi_rel` > τ);
- regional-only rule (SWS input > τ);
- always-HIGH and always-LOW.

## 4. Training-only selection for M6

**Candidates:** the eight sets R + every subset of {GP, GN, N}. R is always included, because the target is defined by SWS and lagged stress.

**Inner validation, within each outer fold:**

1. **Inner folds:** inner walk-forward over the outer training quarters only. For inner target quarter q, inner training = the outer training quarters < q whose labels were published before q's origin. At least 6 inner training quarters are required.
2. **Score and choice:** each candidate is scored by mean inner out-of-fold **log loss**. The lowest wins; ties (≤ 0.005) go to fewer groups.
3. **Fallback:** if fewer than 3 inner out-of-fold quarters exist, use R alone.

**The selected groups are recorded for every fold.**

## 5. Outcomes and metrics

| Outcome | Labels |
|---|---|
| **Primary** | Binary S1 event at τ0 = 10.843 (served; leakage-free). Test: 7 quarters, 35 rows. |
| Secondary | Binary at 14.345 (leakage-affected) |
| Tertiary (the most informative for indicator value) | Continuous next-quarter stress. A LightGBM regressor with the same groups and parameters (objective `regression`), for M1–M6. Compared with carry-forward stress, the Equation 3 origin estimate, and the SWS input. |

**Metrics for the binary outcomes:**

- reference HIGH/LOW counts; predicted HIGH/LOW/INSUFFICIENT counts;
- accuracy and balanced accuracy;
- HIGH precision, HIGH recall and LOW recall;
- false HIGH and false LOW counts;
- ROC-AUC and PR-AUC;
- Brier score and log loss;
- per-quarter results;
- quarter-cluster bootstrap balanced-accuracy differences against carry-forward.

**Metrics for the continuous outcome:**

- RMSE and MAE;
- within-quarter Spearman ρ (province differentiation);
- a quarter-bootstrap CI of the RMSE difference against carry-forward.

**Permutation importance on unseen data** (M5 classifier, primary and secondary; M5 regressor):

- permute one group's columns jointly across the 35 test rows, 200 times (seed 42);
- report the mean increase in log loss or RMSE.

Correlated groups share or distort importance, so this is **not** causal influence.

## 6. Decision reporting

| Question | How it is answered |
|---|---|
| Does a group add value? | Compare the configurations with and without it (M1 vs M5 and M2–M4), plus permutation importance. A group "adds value" only if both point the same way **and** the continuous-outcome RMSE bootstrap CI excludes 0. Otherwise it is "not demonstrated". |
| Is M6 better than E6 and the baselines? | Same decision labels as E6 (improvement / non-inferiority / no demonstrated improvement) |
| Changes after results | None. M6 is served as pre-specified; any later change needs a new protocol. |
