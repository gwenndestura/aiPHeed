# E56 protocol: one bounded optimization and selection cycle for the two-quarter LightGBM food-insecurity model (frozen before any E56 score)

**Written:** 2026-10-18 on branch `e46-lead2-policy`, after E55 (a9c717b).
**Freeze:** the SHA-256 of this file (LF line endings) is in `runner/PROTOCOL_SHA256.txt` and is committed before the evaluation run. There is one run and one byte-identical repeat. Deviations go to `DEVIATIONS.md`. **No further optimization cycle follows** unless a reproducible defect is found.

## 0. Evidence status

- The evaluation quarters (2024-Q3..2026-Q3) were examined in E43–E55, including E55's scores of 24 LightGBM configurations and 11 diagnostics.
- Inner (nested) selection never uses an outer row. The analyst-level choice between E55 and E56 does use the outer rows (section 5). So E56 results are **development evidence**.
- The untouched test is prospective (2027-Q1 onward).

**Run before freezing (no score computed):**
- the score-free data-freshness audit (`tables/data_freshness.csv`, `tables/horizon.json`);
- a smoke test at origins 2023-Q4 and 2026-Q3.

## 1. Horizon and target (unchanged from E55)

**Horizon: two quarters.**
- Predictor quarter t: the latest completed calendar quarter.
- Issue date O(t): 00:00 on day 1 of quarter t+1. Only data published before O(t) are used.
- Target: t+2.
- Example: t = 2026-Q3, intermediate 2026-Q4, target 2027-Q1, issued 2026-10-01. At that date the latest T43 label known is 2026-Q2. The CPI used runs through August 2026, and SWS through 2026-Q2.

**Target: T43** (E55 PROTOCOL section 2): Balance Luzon SWS hunger > 11.3% **and** provincial PSA food-price pressure.
- On every evaluation row hunger is above 11.3%, so the evaluated skill is the provincial price-shock part under elevated hunger.
- It is a food-insecurity **risk** indicator, not measured prevalence.
- The direct surveys (FNRI FIES, PSA subsistence incidence) end in 2023, are regional or annual, and are not targets.

## 2. Candidate E56-TUNED

The structure is E55-LGBM's: P = P_hunger (I7 regional component) × P_price, where P_price is LightGBM with the structural CPI-projection offset and intercept-free boosting.

**Search space:** 72 configurations, `runner/e56_lib.search_space()`:
- the 24 E55 configurations;
- plus 48 drawn once with numpy seed 56 from this product:

| Setting | Values |
|---|---|
| num_leaves (capped at 2^depth) | 2, 3, 4, 6 |
| max_depth | 1, 2, 3 |
| learning_rate | 0.02, 0.05, 0.1 |
| boosting rounds | 10, 25, 50, 100 |
| min_child_samples | 5, 10, 20 |
| feature fraction | 0.6, 0.8, 1.0 |
| bagging fraction (freq 1 when < 1) | 0.7, 1.0 |
| L1 | 0, 1 |
| L2 | 1, 10, 30 |
| class weighting | none, balanced |
| drift multiplier m | 1.0, 0.5, 0.0 |
| recency half-life | none, 6 quarters |
| features | Market + policy, or all groups |
| poverty | none, or POV-AS (E54/E55 as-of SAE province mean) |

LightGBM seed 55, deterministic, single thread.

**Selection:**
- At each origin, the configuration with the lowest embargoed forward-chaining log-loss on training targets only (I7 `folds`: last 6 inner targets, ≥ 4 earlier, embargo 3).
- Tie-break: simplicity (fewer trees × splits, Market only, no poverty, no recency, no class weight, m order, id).
- Every learned quantity (offset scale, trees, tree-mean constant, recency and class weights) is fitted on the fitting rows only. Missing values stay missing.

**Probability calibration is not in the search.**
- E53 (C1–C4) and E55 (F8) showed that calibrators fitted on earlier regimes worsened calibration-in-the-large and discrimination.
- Nested calibration would need a third level of folds with ≤ 6 inner targets.
- This is documented as "not supported by sufficient historical data".

**Decision:** p ≥ 0.5, fixed.

## 3. Rows and comparators

**Primary rows:** E55's 45 rows (targets 2024-Q3..2026-Q3, 14 HIGH / 31 LOW) where every model and baseline exists. The supplementary block is all 50 rows including 2024-Q2.

**Compared on identical rows:**

| Model | Source |
|---|---|
| E55-LGBM | committed E55 predictions, `runs/20261017T153947Z` |
| E46-I7, I7-BASE, E52 | committed predictions |
| Objective 4 baselines B1–B7 | E55 baseline run `baselines_20261017T153459Z` |
| climatology | as in E55 |
| majority class | always LOW: the training majority at every origin |
| always HIGH | |

## 4. Metrics

**Per model:**
- accuracy (quarter-cluster bootstrap CI);
- balanced accuracy;
- HIGH precision and recall; LOW precision and recall;
- F1 (HIGH); Brier; AUC;
- confusion matrix;
- calibration-in-the-large, calibration slope and reliability;
- per-quarter and per-province results;
- leave-one-quarter-out accuracy;
- n and distinct quarters.

**Province discrimination:**
- within-quarter AUC (pairs in the same quarter);
- mean within-quarter SD of probabilities;
- the number of quarters whose five decisions are not all equal.

**Paired Brier** E56-TUNED − E55-LGBM: quarter bootstrap, 1000 draws, seed 56.

**Acceptance A1–A5** (E52/E55 criteria) is reported for both models.

## 5. Final selection rule (one cycle)

**E56-TUNED becomes the final model** only if, on the 45 primary rows, both hold:
- (a) its Brier score is lower than E55-LGBM's;
- (b) its balanced accuracy is ≥ E55-LGBM's − 0.02.

**Otherwise E55-LGBM is the final model.** No other model, row set or metric is used to choose.

Whether the final model meets A1 (≥ 0.75 accuracy) is reported as found.

## 6. Final artifacts and serving

**For the final model at the 2027-Q1 origin**, `backend/data/e56/model/` saves:
- the LightGBM booster text;
- the feature schema (ordered columns, groups, sources);
- the configuration;
- the offset parameters (m, scale, correlation, thresholds) and the tree-mean constant;
- the hunger component parameters (standardized test row, coefficients, intercept, base, RMSE);
- the 2027-Q1 feature rows;
- a SHA-256 manifest.

**Checks:**
- A test reproduces the served 2027-Q1 probabilities from these files alone (LightGBM `Booster(model_file)`, the bivariate normal and the normal CDF), within 1e-9.
- If E56-TUNED is selected, its 2027-Q1 forecast is frozen once in `frozen/`. The E55 frozen file is never edited.

**Serving:** the `e56` record (exact TreeSHAP, as in E55) adds data-freshness fields:
- the latest target quarter known at issue and the latest in the data;
- the latest predictor period per source.

It is served only with `AIPHEED_LEAD2_MODEL=e56`. E38 stays the production default and the rollback until the user authorizes a switch.

## 7. Not allowed

- Changing labels, rows, the search space, the seed, the selection rule or the decision threshold after freezing.
- A second tuning cycle chosen from E56 scores.
- Data beyond the authorized limit (2026-10-14).
- Pre-2021 data; web searches for PSA, SWS or BSP values.
