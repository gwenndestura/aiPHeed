# E102: market/price and economic-access indicators for food-insecurity forecasting. Pre-registered protocol

**Date:** 2026-10-23. **Branch inspected:** `main` @ `0239273` (served: `AIPHEED_LEAD2_MODEL=thesis`). **Production is not changed**; outputs go to `out/` only. E100 and E101 files are not modified.
**Freezing:** this file is hashed (`runner/PROTOCOL_SHA256.txt`, LF-normalised) before any arm below is scored.

**Already examined (disclosed):** served FIRI v2 evaluation; E100 (affordability domain negatively related to regional hunger at Lead 2; cumulative level L and REL descriptive correlations at Lead 2); E101 (T1, T1-REL, by lead). No new indicator other than L and REL, and no arm below, has been scored. All 2021–2026-Q3 outcomes were seen before: every result is **development evidence**; the unseen test is the sealed one (section 9).

## 1. Outcome (the food-insecurity target)

y_L(t) = 1 if the mean of all SWS Balance Luzon involuntary-hunger rounds of target quarter t + L exceeds 11.3%; L ∈ {1, 2}. Regional: one value per quarter. This is the only quarterly direct food-insecurity observation. The LightGBM price label PS / T43 is **not** used as a target here; any result on it would be a price-pressure result.

## 2. Information set at origin t (issue = 00:00 PHT, day 1 of quarter t + 1)

- CPI (`backend/data/processed/cpi_full.parquet`, read with `year >= 2021`): **quarters ≤ t − 1 only** (month 3 of quarter t is released after the issue date; the quarterly file has no partial quarters). Revisions after release cannot be reconstructed: the file's vintage is used and this is disclosed.
- Existing FIRI indicators (`firi2_history.csv`), A1 by lead (stored / E63 sealed, hash-checked), H1 by lead (`thesis_system.regional_hunger`): their own as-of rules.
- SWS: only rounds posted before the issue date (`thesis_system._posted`).
- Training labels: a pair (t', y_L(t')) enters training at origin t only if t' < t and every round of quarter t' + L was posted before issue(t).

## 3. New indicators (province p, origin t; regional value = mean of the five provinces)

| Code | Formula (CPI quarters ≤ t − 1) | Concept |
|---|---|---|
| LVL | 100 × (food index(t−1) / food index(2021-Q1) − 1) | cumulative food price level (base 2021-Q1) |
| REL | 100 × ((food / all-items)(t−1) / (food / all-items)(2021-Q1) − 1) | food-specific burden relative to general prices (**proxy**, not food cost / income) |
| PERS | share of quarters t−4..t−1 with food YoY > 4.0% (the BSP inflation-target ceiling; fixed, not fitted) | persistence of high food inflation |
| ACC | food YoY(t−1) − food YoY(t−3) | acceleration / deceleration |
| VOL | standard deviation of quarter-on-quarter food index % changes over t−4..t−1 | volatility |
| LAG | food YoY(t−3) | delayed price effect |
| RELxE | REL × E1raw (national unemployment-rate change, points) | burden combined with weakening jobs |

Index arms use each indicator's mid-rank percentile among all provinces' values at strictly earlier origins (≥ 8, else missing), as FIRI v2. Poverty (V1) is constant over time, so at the regional level it cannot interact with time-varying burdens; provincial poverty interactions are not testable against a regional outcome (disclosed).

## 4. Arms

**A. Index arms (no training; evaluated on every quarter where SERVED is computable).** Weights for FB arms: C3 walk-forward evidence weights recomputed per lead exactly as E101 `served_equal`.

| Arm | Definition |
|---|---|
| SERVED | Served FIRI v2 (C3), reproduced per lead (E101 gate) |
| T1, T1-REL | E101 arms, reproduced |
| FB1 | SERVED with domain A = mean(A1, A2, A3, pct REL, pct PERS) (supplement) |
| FB2 | SERVED with domain A = mean(A1, pct REL, pct PERS) (replace the change indicators A2, A3) |
| FB2-noH | FB2 without domain H (no SWS input): independent of the outcome |
| T1-B | T1 with A = mean(A1, pct REL, pct PERS) |

**B. Trained forecast models (walk-forward, refitted at every origin, ≥ 8 training pairs else no forecast).** Features standardised with training mean/SD. Logistic regression L2, C = 1.0, `lbfgs`; if the training labels are all one class, the forecast is that class's training share (no fit).

| Arm | Features (regional, at origin) |
|---|---|
| P0 persistence | p = H1 (latest posted SWS, normal-error rule); class = latest posted SWS > 11.3 |
| M0 | H_last (latest posted SWS level) |
| M1 | H_last, A2raw, A3raw (current price indicators) |
| M2 | H_last, REL, PERS (improved price) |
| M3 | H_last, REL, PERS, E1raw, RELxE (price + economic access) |
| M4 | REL, PERS, E1raw (no SWS input) |
| M5 | H_last, LVL, REL, PERS, ACC, VOL, LAG (all new price; overfitting check) |
| GBM3 | LightGBM on M3 features: 25 trees, num_leaves 2, max_depth 1, learning_rate 0.1, min_child_samples 3, reg_lambda 5, deterministic, seed 102 |
| PROD | the production LightGBM's regional mean E56_p (= P_hunger × P_price) and its hunger part E56_p_hunger, from the sealed predictions (Lead 1 E63; Lead 2 stored A1 rows' E63 / E68 sources), as served |

Baselines on every set: ALWAYS (1.0), CLIM (share of posted rounds > 11.3 before issue), P0.

## 5. Metrics (per lead, per arm, on the stated common set)

Accuracy (Wilson 95% CI), balanced accuracy, precision / recall / F1 for HIGH and for LOW, Brier, calibration-in-the-large (mean score − event rate), confusion matrix, per-target-quarter correctness with rising-stress quarters flagged (y = 1 after a y = 0 quarter, or H rising ≥ 3 points), paired quarter Brier difference vs SERVED (index arms) or vs P0 (model arms) with bootstrap 95% CI (2,000 draws, seed 2026) and two-sided sign test, and the count of quarters an arm changes relative to its reference (dependence on few observations).

## 6. Ablation and explanation

- Index: FB2 minus each domain in turn (≥ 3 domains), and FB2 with A at fixed shares {0.058 (served), 0.10, 0.167, 0.25} of the total, other domains keeping their evidence weights renormalised (sensitivity, reported, never selected).
- Models: M3 minus each feature group (H, price, economic); coefficients per origin; GBM3 TreeSHAP shares.
- Descriptive: Spearman of each new indicator's regional value at origin t with the hunger level at t + L over all origins (not a selection criterion).

## 7. Decision rule (fixed now)

- **Improves (index):** paired Brier vs SERVED with 95% CI below 0 **and** sign p < 0.05, **and** accuracy ≥ SERVED's, on the common index set, at Lead 2 (Lead 1 reported).
- **Improves (model):** the same vs P0 on the common model set, **and** a LOW recall ≥ 0.5 when LOW quarters exist in the set.
- **75% objective:** met for an arm only if Lead-2 accuracy > 0.75, above ALWAYS and P0 on the same set, with both class recalls ≥ 0.5 where both classes exist; otherwise "not demonstrated".
- If no arm improves: report the obstacle; the recommended configuration is the best-Brier arm that is leakage-free and not significantly worse than SERVED, as a **research candidate to seal**, with SERVED kept in production.

## 8. Tests (written before the run is scored)

`tests/test_e102.py`: indicators at origin t do not change when CPI quarters ≥ t are altered; LVL = REL = 0 at the first origin with t−1 = 2021-Q1; percentiles use strictly earlier origins; training pairs contain only outcomes posted before the issue date; SERVED reproduces the stored FIRI (< 1e-6).

## 9. Prospective seal

Lead-2 values of SERVED, FB1, FB2, FB2-noH, T1-B and the model arms for targets 2026-Q4 and 2027-Q1, and Lead-1 values for 2026-Q4, written to `out/sealed_prospective.csv` with a SHA-256 before those SWS rounds are posted.

## 10. Not done

No pre-2021 data, no new data, no tuning on any outcome beyond the walk-forward rules above, no threshold other than 0.5, no change to served files, no LightGBM price-model retraining (its training panel is not in any branch).
