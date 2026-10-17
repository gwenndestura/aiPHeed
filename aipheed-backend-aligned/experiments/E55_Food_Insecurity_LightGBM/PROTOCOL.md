# E55 protocol: the food-insecurity target and the final LightGBM model (frozen before any E55 score)

**Written:** 2026-10-17 on branch `e46-lead2-policy`, after E54 (poverty audit).
**Freeze:** the SHA-256 of this file (LF line endings) is in `runner/PROTOCOL_SHA256.txt` and is committed before any evaluation run. Each script runs once, then a byte-identical repeat. Changes after freezing go to `DEVIATIONS.md`.

## 0. Evidence status (read first)

**What has already been seen:**
- Every evaluation quarter used here (2024-Q2..2026-Q3) was examined in E43–E54, on T43, PS and the thesis label.
- So every E55 historical figure is **development evidence**. It is not independent validation.

**What was run before freezing:**
- A smoke test of the E55-LGBM code at the operational origin 2026-Q3. Its target, 2027-Q1, has no outcome yet.
- A score-free label audit (counts of HIGH labels per quarter, no model output compared with any label).

**The only independent test:** the frozen 2027-Q1..Q4 forecasts (section 9).

## 1. Horizon

"One quarter ahead" in the user's brief is the project's **Lead 2**:
- The forecast is issued at 00:00 on day 1 of quarter t+1 (origin O(t)).
- It uses only data published before O(t).
- It targets quarter t+2, the quarter after the issue quarter. Example: issued 2026-10-01, for 2027-Q1.

This is the same convention as E46, E52 and E53 (E47 cutoff audit).

## 2. Target: food-insecurity risk T43 (primary)

### 2.1 Definition

Chapter I section 1.7: *"SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk."*

A province-quarter q is **HIGH** if both hold:
- **(a) Regional hunger is elevated:** Balance Luzon SWS involuntary hunger H_q > 11.3%.
- **(b) The province faces food-price pressure (PS):** its PSA food CPI YoY (quarter mean) is above its 2021–2022 60th percentile, **or** its food-minus-headline YoY is above its 2021–2022 60th percentile.

Otherwise it is **LOW**.

**Thresholds:**
- All are the frozen E40 `label_spec.json` values: P60 of 2021-Q1..2022-Q4, in-window data, never recomputed.
- The hunger threshold 11.3 is P60 of the 2021–2022 Balance Luzon rounds.
- The definition is single-quarter (E43's T43, without E40's sustain-2).

**SWS rounds:**
- The production file `backend/data/inputs/sws_rounds.csv` is used, all rounds, quarter mean.
- 2025-Q2 and 2025-Q3 have only supplementary rounds (`definition_A` False). Their H values are 16.15 and 23.8. Both are far above 11.3, so condition (a) does not depend on the wording.
- **Sensitivity:** approved rounds only (`T43_approved`).

### 2.2 What the label is, and is not

- **It is a food-insecurity risk classification.** It needs the directly measured hunger indicator to be elevated **and** a provincial price shock to household food access.
- **It is not** a household food-insecurity prevalence, and not an official classification.

**Measurement limits** (from the score-free audit, to be disclosed with every result):
- SWS hunger is one **regional** value per quarter.
  - There is no quarterly provincial or municipal measure of hunger or food insecurity in the public data.
  - Provincial differences in T43 therefore come only from (b).
- From 2023-Q4 onward the hunger condition (a) is met in every quarter: H is between 14.3 and 25.3.
  - So on every evaluation row (2024-Q2..2026-Q3) T43 = PS. This is checked and reported.
  - Forecasting skill for the hunger condition therefore **cannot be evaluated** in 2021–2026. Condition (a) last changed state at 2023-Q4, before any evaluable origin.
  - The evaluation measures the price-shock part under elevated hunger.
- PSA subsistence incidence (2021, 2023; provincial) and the FIES regional food-insecurity figures are direct measures. They are annual or triennial, so they cannot be a quarterly target.

### 2.3 Compared targets (preserved, not the primary)

- **Thesis Eq. 3 label (S1 = H + 2D):**
  - EQ3-T: E38's trailing median.
  - EQ3-G: the global median. It uses future quarters, so it fails as-of computability.
  - Both are reported on their own rows from E51/E38.
  - Saturated: 40/45 HIGH rows in 2024–2026.
  - Not comparable with T43 accuracies.
- **PS:** E52's target. Identical to T43 on the evaluation rows, but defined without hunger.

## 3. Rows

**Evaluation rows:** targets 2024-Q2..2026-Q3 (origins 2023-Q4..2026-Q1), 5 provinces each, where every arm and baseline has a prediction.
- Expected: 10 quarters, 50 rows, identical to the E52/E53 rows.
- The run stops if the T43 labels on these rows differ from the E52 `rows.csv` labels.

**Also reported:**
- The approved-rounds subset (no 2025-Q2/Q3; 40 rows).
- Sample size and HIGH/LOW counts for every block.

**Operational origins (not scored):**
- 2026-Q2: target 2026-Q4, an earlier forecast.
- 2026-Q3: target 2027-Q1, the prospective forecast.

## 4. The E55-LGBM model (primary candidate, fixed here)

### 4.1 Structure

P(T43 HIGH at t+2) = P_hunger × P_price.

**P_hunger:** E46-I7's regional hunger component, unchanged.
- Ridge on regional signals, applied to the latest H posted before O(t).
- P(H(t+2) > 11.3) uses an out-of-fold RMSE scale.
- It is not LightGBM: 15–19 regional observations are too few for a tree model.

**P_price:** a LightGBM classifier for PS(t+2), trained on as-of PS labels of training targets ≤ t−1 with vintage `d.cut(t)` (the E53 `frame`):

1. **Offset (`init_score`):** the logit of the structural probability.
   - The base-effect CPI projections of food YoY and food-minus-headline YoY (drift multiplier m) are converted with the bivariate normal of E44 `p_price_biv`.
   - The scale is the projections' RMSE and error correlation on the fitting rows.
2. **Trees:** depth-1 trees (2 leaves) with learning rate 0.05, min_child_samples 10, reg_lambda 10.
   - The objective is an **intercept-free logistic loss**: the gradients are centred to sum to zero at each iteration.
   - The trees' (weighted) mean output on the fitting rows is subtracted after fitting.
   - So the trees redistribute risk between province-quarters but cannot carry an earlier regime's level shift. This is the I7 D3 fix, applied to trees.
3. **Inputs:**
   - Market: `F_hat_M1, F_now, D_now, gap_now, rice_whsl_yoy` + the rice-policy block;
   - Climate: 8 inputs;
   - Fish kill: 2;
   - Employment: 2;
   - OFW: 3;
   - News: 5 group shares + `news_n` (E44 `PRICE_GROUPS`, E46 `POLICY`).
   - Missing values stay missing; LightGBM routes them.

### 4.2 Configuration

The configuration is selected per origin by **embargoed forward-chaining log-loss on training targets only** (I7 `folds`: last 6 inner targets, ≥ 4 earlier targets, embargo 3).

**Grid (24 configurations):**

| Setting | Values |
|---|---|
| m | 1.0, 0.5, 0.0 |
| trees | 10, 40 |
| features | Market + policy only, or all groups |
| recency half-life (sample weights 0.5^((q_max − q)/h)) | none, 6 quarters |

**Tie-break:** fewer trees, Market only, no recency, then m in the order 1.0, 0.5, 0.0.

**Decision:** p ≥ 0.5, fixed. There is no threshold refit and no calibrator. E46 D2 and E53 showed that both hurt on these data.

### 4.3 Why this design (from E46/E53, not from any E55 score)

E53's LightGBM arms lost to the ridge model for these reasons:
- 30–60 training rows;
- an over-prediction carried from the 2022–2023 inflation regime into 2025–2026;
- trees cannot extrapolate a base effect.

E55-LGBM keeps the structural projection as an offset and forbids the trees from learning a level. The trees are always used: at least 10 trees at every origin, with no "no-tree" option. LightGBM is therefore a genuine part of every forecast.

## 5. Variants (same grid, selection, rows and decision)

| Arm | Change | Role |
|---|---|---|
| **POV-AS** | + `pov`: E54 POV, the unweighted province mean of the 2021 municipal SAE, centred across provinces. Known only at origins O(t) ≥ 2025-01-01, else missing. | poverty, as-of (primary poverty test) |
| POV-LA | + `pov` known at every origin | look-ahead sensitivity |
| FE | + five province indicators | is a poverty effect more than province identity? |
| D-climate, D-fish_kill, D-employment, D-ofw_remittance, D-news, D-policy | that group removed from the inputs | trigger ablation |
| MKT-ONLY | features fixed to Market + policy | all non-market triggers removed |

## 6. LightGBM factor diagnostics (Section 6 of the brief; development diagnostics, never selection)

Each diagnostic is one fixed configuration with no selection: m = 1.0, all inputs, gate = P_hunger, decision 0.5 unless stated.

| ID | Configuration | Factor it isolates |
|---|---|---|
| F0 | plain LightGBM classifier on PS (4 leaves, 100 trees); no projection | the naive approach |
| F1 | F0 + base projections and distance-to-threshold features | structural knowledge as features |
| F2 | offset, standard logistic loss (intercept learnable), 40 stumps | offset without regime protection |
| F3 | offset + intercept-free (the E55-LGBM learner without selection) | regime protection |
| F4 | F3 + recency half-life 6 | regime change by weighting |
| F5 | F3 with 8 leaves, 300 trees, min_child 5 | complexity |
| F6 | F3 + class weighting | class imbalance |
| F7 | F3 + threshold tuned on inner out-of-fold balanced accuracy | threshold selection |
| F8 | F3 + inner Platt calibration | calibration |
| F9 | F3 without the OFW group (remittances missing after 2025-Q4) | inconsistently available features |
| F10 | F3 trained on the last 8 target quarters only | sample size |

## 7. Comparators and baselines (identical rows)

**Objective 4 baselines** (refitted on **T43** labels; E52 baseline code with T43 labels and T43 persistence):

| Baseline | Specification |
|---|---|
| B1 | naive persistence: the latest T43 label available at O(t) |
| B2 / B3 | PSA-only logistic / LightGBM |
| B4 / B5 | NLP-only logistic / LightGBM |
| B6 | combined logistic |
| B7 | the E38 LightGBM procedure on T43 |
| naive | climatology, always HIGH, always LOW |

**Other models** (committed predictions; not baselines; paired comparisons only):

| Model | Note |
|---|---|
| E46-I7 | T43, the same target |
| I7-BASE | structural projection only × P_hunger |
| E52 | P(PS): a different definition, identical labels on these rows |
| E38-served | thesis Eq. 3 label (EQ3-T); **non-equivalent target**, reported for information only |

## 8. Metrics and acceptance

**Per arm:**
- accuracy with its 95% quarter-cluster bootstrap CI;
- balanced accuracy;
- HIGH and LOW recall;
- precision and F1;
- Brier and AUC;
- calibration-in-the-large, calibration slope and reliability table;
- confusion matrix;
- per-quarter accuracy and confusion;
- leave-one-quarter-out accuracy.

**Paired Brier differences:** quarter-cluster bootstrap, 1000 draws, seed 55.

**E55-LGBM is accepted for development** only if all hold on the 50 rows (the E52 criteria):

| ID | Criterion |
|---|---|
| A1 | accuracy ≥ 0.75 |
| A2 | balanced accuracy ≥ 0.70, and HIGH and LOW recall ≥ 0.60 |
| A3 | Brier lower than every Objective 4 baseline and naive rule |
| A4 | balanced accuracy higher than every Objective 4 baseline and naive rule |
| A5 | minimum leave-one-quarter-out accuracy ≥ 0.70 |

Calibration and the comparison with E46-I7 / E52 are reported, not gates.

**Poverty rule** (E54's): an arm **IMPROVES** on E55-LGBM only if all hold:
- its paired Brier CI upper bound is < 0;
- its balanced accuracy ≥ E55-LGBM's;
- both recalls are within 0.05 of E55-LGBM's.

Only an improving **POV-AS** may replace E55-LGBM as the served model. POV-LA and FE are informational.

**Trigger ablations:** informational. A group "adds information" if removing it gives a paired Brier CI lower bound > 0.

## 9. Prospective freeze and serving

**Freeze:**
- The 2027-Q1 forecasts of the served arm (E55-LGBM, or POV-AS if it improves) from origin 2026-Q3 are written **once** to `frozen/E55_LGBM_PROSPECTIVE_2027Q1.json` with a sha256.
- This happens whether or not A1–A5 hold, because it is the independent test of the LightGBM model.
- Later quarters are frozen at their own origins by the same procedure, unchanged.

**Serving:**
- The `e55` record (`backend/scripts/build_record_e55.py`) serves the arm with exact TreeSHAP attributions.
- It is enabled only with `AIPHEED_LEAD2_MODEL=e55`.
- The production default (E38) is not changed without the user's authorization.

**Explanations served** (exact, for the served arm at every issue date):
- The price part's log-odds is decomposed additively: logit P_price = baseline + Market CPI projection (the offset minus its training mean) + Σ_g TreeSHAP_g.
  - TreeSHAP is LightGBM `pred_contrib`.
  - Feature groups follow the E53 D-1 mapping (rice policy → Market, `news_<group>` → that group, `news_n` → other), with poverty as its own group.
  - The reconstruction error must be < 1e-9.
- The regional hunger probability is shown as a separate factor.
- **Group status:**
  - **insufficient_data:** none of the group's observed inputs has a value at the issue date. Its effect, which comes from LightGBM's routing of missing values, is still recorded.
  - **contributes:** |group log-odds effect| ≥ 0.05.
  - **no_effect:** otherwise.
- The dashboard text says "model attributions, not causes" and names the target as food-insecurity risk (elevated regional hunger and provincial food-price pressure), never as measured prevalence.

## 10. Leakage and validity checks (`tests/test_e55.py`)

1. **As-of invariance:** recomputing every input from data truncated at O(t) (CPI, SWS, production, LFS, news, climate, OFW, rice, policy events) reproduces E55-LGBM's forecast exactly.
2. **Study window:** no input row before 2021-Q1.
3. **TreeSHAP:** LightGBM `pred_contrib` equals `shap.TreeExplainer`. Baseline + groups reconstruct the price log-odds (< 1e-9).
4. **Labels:** T43 = PS when H > 11.3 and 0 otherwise. The evaluation rows equal E52's.
5. Protocol hash, and the frozen-file hash.

## 11. Not allowed

- Changing labels, thresholds, rows, grids, the selection rule, the decision rule or the baselines after freezing.
- Selecting among E55 arms by their evaluation scores, beyond the poverty rule above.
- Pre-2021 data; outcomes after 2026-Q3; web searches for PSA, SWS or BSP values.
