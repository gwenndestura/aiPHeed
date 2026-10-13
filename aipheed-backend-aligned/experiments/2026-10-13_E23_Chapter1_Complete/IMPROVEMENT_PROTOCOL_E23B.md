# E23-B Improvement Protocol (frozen before any E23-B model was run)

**Why a new protocol.** On 2026-10-13 the user asked for a model with **more than 75% classification accuracy** that **beats the strongest applicable baseline on the same leakage-free test observations**. E23 (frozen protocol e3b60eff…) is left unchanged. This is a separate experiment.

**Not blind.** E23's results were seen before this protocol was written:

- under the primary target, the lead-1 test rows are 37 HIGH and 3 LOW;
- persistence accuracy is 0.875;
- the E23 proposed model scored 0.825.

The candidates below were chosen from that diagnosis (the label is highly persistent and dominated by the regional hunger level). This is **development evidence**. **No untouched authorized holdout exists:**

- 2026-Q1/Q2 outcomes were viewed in E18;
- 2026-Q3 onward is protected and not authorized.

Section 6 gives the prospective holdout procedure.

## 1. Unchanged from E23

- Target: training-window-median threshold. The fixed 14.6 threshold is reported as a sensitivity.
- Timing rules.
- Origins, test rows and minimum training.
- The six baselines. Their **sealed E23 predictions are reused unchanged**, so the comparison rows are identical.
- Metric code.

## 2. Primary metric for E23-B

**Classification accuracy** (Objective 2-I; the user's stated criterion). Reported **separately** alongside:

- ROC-AUC, precision, recall, F1, Brier;
- the confusion matrix and class counts.

Two references are always reported:

- **always-HIGH**;
- **training majority**.

On these test rows, accuracy above 75% is reachable without any skill.

## 3. New features (all published before the origin O(t))

For each province, using only labels **published before O(t)** (the E23 rule):

| Feature | Definition |
|---|---|
| `S1_last` | S1 of the latest published label quarter |
| `margin_last` | `S1_last − τ(O)` |
| `y_last` | 1 if `S1_last > τ(O)` (the persistence signal) |
| `D_last` | D of the latest published label quarter |
| `D_mean4` | Mean D of the last 4 published label quarters |
| `H_last_pub` | H of the latest published label quarter |
| `H_roll4` | Mean H of the last 4 published label quarters |
| `H_trend` | `sws_hunger` (latest published round, E23 feature) − `H_last_pub` |

These are the "lagged features, trends and rolling statistics". None uses an unpublished value.

## 4. Candidate family (LightGBM only, the model named in H3) and nested selection

**Feature sets:**

| Set | Contents |
|---|---|
| **FA** combined | Lag block + 37 government + 9 news |
| **FB** government | Lag block + 37 government (no news) |
| **FC** compact | Lag block + [food_cpi_yoy, cpi_dev, unemployment_rate, rice_price_regular_accel] + [FSSI, FSSI_lag1] |

**Grid, for each set:**

- num_leaves 3, max_depth 2, learning_rate 0.05, colsample_bytree 0.8, balanced class weight, random_state 42;
- min_child_samples ∈ {5, 10};
- n_estimators ∈ {50, 150};
- reg_lambda ∈ {1, 10};

That is 8 configurations per set, **24 in total**, and no others.

**Decision threshold** ∈ {0.3, 0.4, 0.5, 0.6, 0.7}, chosen in the inner folds only.

**Inner validation (training pairs only, E23 rule):**

- validation targets = the last 3 distinct training target quarters;
- inner training = pairs with target quarter ≤ v − k − 1;
- inner predictions are pooled; for each configuration, the best threshold is the one with maximum inner accuracy (ties → the threshold nearest 0.5);
- configurations are scored by inner accuracy, with ties broken by inner log loss, then by grid order;
- if no inner fold is usable: FA, first configuration, threshold 0.5.

**News is retained only if the inner selection picks FA or FC.** The share of origins choosing each set is reported.

## 5. Decision rules

At each lead, the selected model **IMP** is compared with each of the six baselines on identical rows.

**"Exceeds 75%"** = pooled accuracy > 0.75. Always reported **next to always-HIGH**.

**"Beats the strongest baseline"** (strongest = the highest pooled accuracy among the six) requires all of:

1. higher pooled accuracy;
2. a one-sided exact sign-flip test on per-origin accuracy differences with p < 0.05;
3. more origins better than worse.

Also reported:

- exact McNemar on rows (descriptive; rows are clustered);
- the leave-one-origin-out range of the accuracy difference.

**"Robust on unseen quarters":** not assessable until the prospective holdout (Section 6). Development origins are not unseen.

**Hypotheses:**

- H3 is re-assessed with the E23 rule (AUC + Brier vs all six) applied to IMP, **descriptively**. E23's primary decisions stand.
- If no lead is evaluable under E23's rule, the result stays "not testable".

## 6. Prospective holdout (cannot be run now)

1. Freeze the IMP procedure (this file plus the code hashes).
2. Once the user authorizes 2026-Q3 news and government data, and publication of the corresponding labels:
   - produce sealed forecasts for 2026-Q4 (from origin 2026-10-01) and for later targets;
   - score them only after their labels are published.
3. ≥ 8 origins and ≥ 5 LOW rows are required before any robustness claim.
