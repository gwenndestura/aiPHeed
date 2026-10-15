# E44 protocol: resolving the Lead-2 failures with a mandatory five-trigger model (frozen before any E44 score)

**Written:** 2026-10-15 on branch `e43-five-trigger-risk`, after E43 (`708fc61`). It folds in the second E43 brief (nested tuning; five triggers mandatory) and the E44 directive.

**Freeze:** SHA-256 of this file (LF) in `runner/PROTOCOL_SHA256.txt`, committed before any E44 model is fitted. Every iteration below is pre-registered **now**, before any of them is scored, so the choice of iterations is not driven by their outer results. Each is run once, then a byte-identical repeat. All iterations are reported, including failures.

## 0. Root causes established before E44 (from E41–E43 evidence; no E44 score)

| # | Root cause | Evidence |
|---|---|---|
| R1 | **The served v1 label is relative.** It drifts with regional hunger and is HIGH 90–95% of the time in 2024–26. | E41/E42 audits |
| R2 | **The Chapter I target T43 is rare at the province-quarter level:** 19% HIGH, 16 HIGH rows over 2023-Q2..2026-Q3. A direct classifier has 3–16 HIGH training rows at each origin. | E43 labels; E43 train counts |
| R3 | **In the evaluation window T43 is almost a price event.** Approved SWS hunger has been above 11.3 in every labelled quarter since 2023-Q4. A province is HIGH when its food prices are above its 2021–22 reference, so the forecastable part is mostly the provincial price path. That path has a continuous history with about 5 times as many training observations as the binary label. | `sws_rounds.csv`; T43 definition |
| R4 | **Class weighting** inflated E43's LightGBM probabilities (calibration-in-the-large −0.40). | E43 |
| R5 | **National employment levels act as a time proxy:** masking them moves p by −0.54. National OFW levels behave the same way. | E43 |
| R6 | **Climate** is the only non-price trigger with consistent out-of-sample signal. The others are weak or national. | E43 |
| R7 | **Few independent outer quarters (5–12).** Every 2021–2026 quarter has been examined, and the E40 holdout is exposed (E41 C-1). E44 is development evidence; independent confirmation is prospective. | – |

**These root causes are why the iterations below were designed as they are.** That is disclosed: they were informed by E43's outer results on the same quarters.

## 1. Target and timing

**Target T43**, unchanged:
- **Rule:** SWS H > 11.3 (regional) AND (provincial food YoY > its frozen 2021–22 P60 OR food minus headline > its P60), in the target quarter.
- **Status:** experimental. It needs adviser approval (it drops E40's sustain-2 rule) and is not verified household food insecurity.
- **Why it is kept:**
  - it follows Chapter I §1.7 (SWS + PSA food prices);
  - it uses frozen references, so it does not drift;
  - its meaning was fixed before any E43 model was fitted.
- **Alternatives** (v1, E40 sustain-2, hunger only, L4) are documented in E43 §3 and not re-selected.

**Timing:**
- **Lead 2:** O(t) = first day of t+1, where t is the latest completed quarter; the target is t+2.
- **Dashboard:** viewing quarter q gives latest completed q−1 and target q+1 (`backend/app/quarterly/target.py`).
- **Information availability:** as in E43 PROTOCOL §2.

## 2. Five-trigger features (mandatory in every E44 candidate)

E43's features plus four new ones; every value is as of O(t).

| Group | Features |
|---|---|
| Market | F_hat_M1, F_now, D_now, gap_now, rice_whsl_yoy |
| Climate | tc_count (t), tc_count_l1 (t−1), enso (t−1), enso_l2 (t−2, delayed effect), palay_yoy, corn_yoy |
| Fish Kill | fish_yoy, aqua_yoy |
| Employment | ur_yoy, under_yoy (**national**, year-on-year change; levels excluded per R5) |
| OFW Remittance | remit_usd_yoy, remit_php_yoy (USD × USD/PHP, YoY), fx_yoy (**national**) |
| Hunger history | H_last, H_age |
| News | five trigger shares, news_n |

**Interactions (I2 only, price model):**
- `enso_x_mom` = enso × mom3: climate followed by rising prices;
- `tcl1_x_palay` = tc_count_l1 × palay_yoy: typhoon followed by a supply drop.

**Feature sets:**
- **F5:** all of the above except interactions.
- **F5-GOV:** F5 without news.
- **F5-COMPACT:** F_hat_M1, enso, fish_yoy, ur_yoy, remit_php_yoy, H_last, news_climate.

Every set must contain at least one feature of each of the five trigger groups. This is asserted.

## 3. Iterations (all pre-registered now)

### I1: nested-tuned five-trigger classifiers (addresses R4 and R5; tests direct classification)

**Grid** (132 configurations):
- **LightGBM:**
  - num_leaves {2, 4};
  - min_child_samples {3, 8};
  - n_estimators {50, 150};
  - learning_rate 0.05;
  - reg_lambda {1, 10};
  - class weight {none, balanced};
  - set {F5, F5-GOV, F5-COMPACT};
  - window {expanding, last 8 target quarters}.
- **LR:**
  - L2, C {0.05, 0.3, 1};
  - class weight {none, balanced};
  - the same sets and windows.

**Nested selection at each origin t**, using training pairs available before O(t):
1. Blocked leave-one-target-quarter-out inside the training window.
2. Cross-fitted Platt recalibration of the out-of-fold predictions.
3. **Criterion:** mean recalibrated out-of-fold Brier. Ties go to the simpler configuration.
4. Refit on all training pairs, then apply the Platt map from the out-of-fold predictions.
5. **Threshold:** from {0.2, 0.3, 0.4, 0.5}, maximizing out-of-fold balanced accuracy.

**Eligibility:** at least 6 training target quarters, at least 3 HIGH rows, and both classes.

**Code:** `runner/e44_classifiers.py`.

### I2: five-trigger component model (addresses R2 and R3; the substantive change)

**P(T43) = P(H(t+2) > 11.3) × P(price signal of province p at t+2).** Independence of the two components is assumed and stated.

**Price component** (province; trained on every quarter with complete published CPI, not only SWS-labelled quarters):
- **Base:** the E41/E42 base-effect projection of food YoY at t+2 with drift multiplier m ∈ {1, 0.5, 0}, plus the analogous headline projection (same m).
- **Residual model:** residual = F(t+2) − base, regressed on the five-trigger features (F5-GOV + news + the two interactions).
  - **ridge** α ∈ {1, 10, 100} (standardized; median imputation + missing indicators);
  - **LightGBM regressor:** num_leaves {2, 4}, n_estimators {50, 150}, learning_rate 0.05, reg_lambda 10, min_child_samples 5.
  - A zero-residual model is **not** in the grid: the five triggers are mandatory, and ridge α = 100 lets the data shrink their effect.
- **Selection:** of the 21 configurations, the one with the lowest blocked leave-one-target-quarter-out RMSE over training pairs (targets ≤ t−1).
- **Predictive SD:** the selected configuration's out-of-fold RMSE.
- **Signal probability:** P(F > P60_food,p or F − HL̂ > P60_gap,p) with F ~ Normal(F̂, s). HL̂ is the headline projection, treated as known.

**Hunger component** (region; trained on approved quarters posted before O(t)):
- **Regression:** H(t+2) = H_last + ridge(α ∈ {1, 10, 100}) on regional means of [enso, enso_l2, tc_count, tc_count_l1, ur_yoy, under_yoy, remit_php_yoy, fx_yoy, F_now, fish_yoy, palay_yoy, news_n].
- **Selection** by leave-one-target-quarter-out RMSE, which is also the predictive SD. At least 6 training pairs are needed; otherwise no forecast.
- P(H > 11.3) under the normal predictive distribution.

**Joint probability and threshold:**
- The joint p is computed for training targets out of fold, so the threshold ({0.2, 0.3, 0.4, 0.5}, maximizing out-of-fold balanced accuracy) uses training information only.
- **Platt** is applied to the joint p only if the out-of-fold training set has at least 3 HIGH rows.

**Code:** `runner/e44_components.py`.

### I3: more valid observations (contingency; pre-registered now, run regardless)

I2 unchanged, except that the hunger component also trains on the SWS **supplementary** rounds (2025-Q2, 2025-Q3; definition_A = False), which are official SWS releases.

The label T43 is **not** changed. The supplementary rounds enter only as hunger observations, never as labels.

### Comparators (on identical outer rows)

- B-maj (always LOW);
- B-persist;
- B-clim;
- SIM-0, SIM-5T, E43 LGBM-COMB;
- E38-served (scored on T43);
- E41-M1 (price-only, comparison);
- **I2-MKT:** I2 with only market features in the residual model and a random-walk hunger component. This is the market-price-only model.
- **I2 add-one:** market + one group.
- **I2 drop-one:** I2 without one group.
- **I2-GOV / I2-NLP:** I2 without news, and I2 with news only (plus the base).

## 4. Evaluation and acceptance gates (defined now)

- **Outer set S44:** every T43-labelled target quarter where I1, I2, I3, the I2 variants, B-maj, B-persist, B-clim, SIM-0, SIM-5T, E38-served and E41-M1 all forecast. E43 LGBM-COMB starts later (2025-Q1), so it is reported on its own subset. Gates are judged on S44.
- **Also reported:** I2 and I3 on every target they forecast (a longer history), with the baselines on the same rows.

**Metrics:**
- accuracy (date-cluster bootstrap CI), balanced accuracy, recall per class, precision, F1, confusion matrix;
- ROC-AUC, PR-AUC (with prevalence), Brier, log loss, calibration-in-the-large and slope;
- per quarter and per province;
- paired per-date sign-flip tests (Holm).

**Acceptance gates for a candidate:**

| Gate | Rule |
|---|---|
| A0 | E44 tests pass: leakage, five-trigger presence in training **and** inference, alignment |
| A1 | accuracy ≥ 0.75 |
| A2 | balanced accuracy ≥ 0.70, and HIGH and LOW recall ≥ 0.60 (it passes on discrimination, not on the majority class) |
| A3 | per-date Brier lower than B-maj and B-persist (point estimates). Paired p-values are reported; with ≤ 9 outer quarters, significance is not required, and this is stated as a limitation. |
| A4 | calibration-in-the-large CI contains 0 |

**Final candidate rule (fixed now):**
1. The first of [I1, I2, I3] that passes A0–A4 on S44.
2. If none passes: I2 is served, as the pre-declared five-trigger design, with status **"forecasting acceptance NOT met"**.
3. **The task is not marked complete unless a candidate passes.**

**Multiplicity:** up to three looks at S44 (I1, I2, I3). This is disclosed, and a pass on S44 is development evidence only.

## 5. Freeze, serving, outputs

- **Freeze:** every iteration's and comparator's 2027-Q1 forecast from O = 2026-10-01, plus the final candidate's feature list, selected configurations and threshold, to `frozen/E44_PROSPECTIVE_2027Q1.json` with a sha256.
- **Serving:** the final candidate behind `AIPHEED_LEAD2_MODEL=e44`. The production default stays E38 unless the candidate passes and the user decides.

**Per province:**
- the probability and its components;
- the band (Low < 0.33 ≤ Watch < 0.67 ≤ High);
- the five trigger contributions:
  - I2: ridge coefficient × standardized value, or TreeSHAP, in percentage points of food YoY for the price component and in H points for the hunger component;
  - trigger status `contributes` if |contribution| ≥ 0.1 points, otherwise `no_effect`, `stale` if the data are more than 2 quarters old;
- observed evidence;
- the backtest against outcomes.

No municipal probabilities.

**Lead and target fields** in the API: originQuarter (latest completed), currentQuarter, targetQuarter, and leadFromOrigin = 2.
