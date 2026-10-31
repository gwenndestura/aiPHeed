# E128 frozen experiment protocol

**Freezing.** This file's SHA-256 is written to `runner/PROTOCOL_SHA256.txt`, and the protocol is committed before any model is fitted. `runner/run_e128.py` refuses to run if the hash differs. Changes go in numbered addenda only.

**What was known before freezing**
- **Inspected.** All 2021–2026 SWS quarters and every feature were inspected by earlier experiments (E40–E127).
- **Seen here.** The target class distributions below were computed from the target series alone. No model was fitted.
- **No new data.**

## 1. Target (supervised level: **regional**)

| Item | Definition |
|---|---|
| Source | SWS Balance Luzon involuntary hunger, non-commissioned rounds (`FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv`, verified against SWS releases) |
| Value y(q) | Mean of quarter q's non-commissioned rounds; observed when the last round of q is published |
| Geography | Balance Luzon (Luzon outside Metro Manila). It contains CALABARZON but is not CALABARZON. A regional proxy only. |
| Independent observations | 20 quarters, 2021-Q2 .. 2026-Q3. No round exists for 2021-Q1, 2022-Q1 or 2025-Q1. The commissioned 2025-Q1 round is excluded. |

### T1, primary: the frozen Chapter I hunger condition

**HIGH = y(q) > 11.3.**
- 11.3 is the hunger threshold of T43c / E40 `label_spec.json`, frozen 2026-10-15.
- It is not chosen here, and it is not an SWS-defined category.
- 13 HIGH / 7 LOW. Every quarter from 2023-Q4 to 2026-Q3 is HIGH (11 in a row).

### T4, secondary sensitivity (pre-registered; it cannot establish thesis reliability)

**HIGH = y(q) > the mean of the last up to 4 Balance Luzon quarter means published before the issue date.**
- It asks: will hunger be above its recent usual level?
- It uses no tuned constant, and it is the least saturated source-defined alternative in 2023–2026.
- **Caveat.** The Balance Luzon margin of error is about ±6 points. Many differences from the trailing mean lie inside sampling error.

### Rejected for E128

| Candidate | Reason |
|---|---|
| T43c province-quarter labels | Their hunger condition is the regional SWS value copied to the five provinces. Their province part is the food-price condition, which is itself a market predictor family. |
| FIRI3 / FIRI v2 scores or bands | Not ground truth |
| FIES 2023 | Annual and descriptive |
| Provincial or LGU labels | None exist |

## 2. Time convention

| Item | Rule |
|---|---|
| Issue date | O(t) = 00:00 on the first day of quarter t+1. Origins t = 2021-Q1 .. 2026-Q3. |
| Lead k | Target quarter t+k, k = 1..4. The target quarter ends 3k months after the issue. Leads above 4 are not evaluated (too few quarters). |
| Features | The E119 point-in-time regional dataset (value usable only if available strictly before O(t); 9 leakage checks passed), plus the as-of transforms in §3 |
| SWS information at O(t) | Rounds published before O(t). The true SWS horizon (target quarter minus the newest known quarter) is recorded per row. |
| Training rows for origin t, lead k | Pairs (s, s+k) whose target y(s+k) was **fully published before O(t)** |

## 3. Features (fixed before fitting)

| Group | Features |
|---|---|
| Hunger history (not a trigger) | Latest Balance Luzon reading; change vs previous; mean of last 4 known quarters; staleness |
| 1. Market and food prices (incl. agriculture and fish supply) | Regional food CPI YoY; headline CPI YoY; farmgate palay YoY; food YoY change vs the previous origin; palay/corn drop C3; fisheries drop C4; aquaculture YoY; vegetables/root crops YoY |
| 2. Climate | El Niño advisory; ONI; typhoons entering PAR; rainfall anomaly; temperature anomaly |
| 3. Employment and OFW | Unemployment rate; unemployment YoY change (national LFS); remittance decline (national BSP) |
| 4. News and NLP | Four GDELT food-news shares (national); local news volume, log(1 + admitted aiPHeed articles, five provinces, quarter t−1) |
| 5. Poverty and vulnerability | **No eligible time-varying regional series.** Subsistence incidence is 2021/2023, both published 2024-08-15; V1 is a static 2025 profile. Including either would act as a time dummy. Not testable; reported as such. |

**Excluded features**

| Feature | Reason |
|---|---|
| FSSI-v3 regional | Present in 11 of 23 quarters, so more than 40% missing. Article volume is used instead. |
| XLM-R / BERTopic outputs | No dated regional series beyond FSSI-v3 |
| Rainfall total | Duplicates the rainfall anomaly |
| FIRI3 / FIRI v2 | Composite scores; see §1 |

**Missing values**
- LightGBM uses its native handling.
- Logistic Regression uses training-fold median imputation, then training-fold standardization.
- Nothing is interpolated.

## 4. Models (identical targets, origins and information)

| # | Model | Inputs |
|---|---|---|
| M1 | **LightGBM** (proposed) | All features |
| M2 | Naive persistence | T1: newest Balance Luzon reading at O(t) > 11.3. T4: newest reading > the mean of up to 4 known quarters before it. 0/1 probability. |
| M3 | PSA-only (official statistics) | LightGBM on market + employment/OFW. PSA CPI, farmgate, production and LFS, plus BSP remittances. No news, climate or SWS history. |
| M4 | NLP-only | LightGBM on news features only |
| M5 | Logistic Regression | All features; L2, standardized |

**References for the criteria:** CLIM (the training base rate) and MAJ (the training majority class).

### Training and tuning (inside each walk-forward fold only)

**Direct strategy.** One model per lead.

**Fold eligibility**
- A fold needs at least 6 training rows with at least 2 HIGH and 2 LOW.
- This is lower than CH1's 5/5 because only 7 LOW quarters exist. The origin set is then identical for every model at that lead.

**Inner validation**
- The last 3 training rows in target-publication order, each predicted by a model fitted on the rows published before it.
- Score: mean log-loss. A grid point is skipped if an inner training set has one class.
- If no grid point is scorable, use the default (first) grid point. Ties go to the earlier grid point.

**LightGBM grid**
- num_leaves {2, 4} × n_estimators {25, 75} × min_child_samples {2, 4} × class_weight {None, balanced}.
- Fixed: learning_rate 0.1, feature_fraction 0.8, bagging_fraction 0.8, bagging_freq 1, reg_lambda 1, min_data_in_bin 1, seed 128, deterministic.

**LR grid**
- C {0.1, 1.0} × class_weight {None, balanced}; lbfgs, max_iter 2000.

**Classification threshold:** 0.50, fixed. No threshold is selected.

## 5. Evaluation

**Outer rows.** Every eligible origin with a labelled target. Identical for all models at a lead. Each row is one independent target quarter.

**Blocks**
- DEV = targets ≤ 2024-Q4.
- LATER = targets ≥ 2025-Q2.
- All rows were previously inspected, so the evaluation is **retrospective**. No untouched holdout exists.

**Metrics:** accuracy, balanced accuracy, HIGH precision / recall / F1, ROC-AUC, PR-AUC, Brier, confusion matrix, class supports. A metric that needs both classes is reported as not evaluable (NaN).

### Reliability rule (frozen R1–R7 of `FINAL_THESIS_OBJECTIVES/FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7, unchanged)

| # | Criterion |
|---|---|
| R1 | At least 10 target quarters **and** at least 40 rows |
| R2 | Accuracy ≥ 0.75 |
| R3 | Balanced accuracy ≥ 0.70 |
| R4 | Accuracy > MAJ accuracy and > persistence accuracy |
| R5 | Brier < persistence and < CLIM, each with a one-sided paired bootstrap p < 0.10 (2,000 draws over target quarters, seed 2026) |
| R6 | HIGH precision ≥ 0.60 and recall ≥ 0.60 |
| R7 | Accuracy ≥ 0.60 in each third of the target quarters, and leave-one-quarter-out minimum accuracy ≥ 0.70 |

**Rules for applying it**
- A criterion that cannot be evaluated (for example, balanced accuracy with one class) is **not passed**.
- **Maximum reliable lead** = the largest K with Leads 1..K all passing. If Lead 1 fails: none.
- **Status:** confirmed only on unseen rows. Every row here was inspected, so a pass would be **provisional** at most.
- **Also reported as a sensitivity, not the verdict:** the R1 row count with the 40-row part removed. That part was written for province-quarter rows and is unattainable for one regional series.

**LightGBM vs each baseline**
- Paired bootstrap Brier difference (one-sided) and McNemar exact test.
- Holm correction across the 4 baselines per lead.

## 6. Robustness (on M1, target T1, plus T4 where stated)

| Analysis | Method |
|---|---|
| Overfitting | Training (in-sample), inner and outer accuracy, Brier and AUC; seeds {128, 1, 2, 3, 4}; tree size |
| Temporal | By block and by target-quarter condition: food CPI YoY ≥ 5 %, PAR ≥ 8 storms, unemployment rising, hunger ≥ 15 % |
| Geographic | Not performed. There is no valid provincial or LGU target. |
| Class | Supports, majority-class baseline, confusion matrices, HIGH and LOW recall |
| Ablation | Remove each group (market, climate, employment/OFW, news, poverty), plus production and hunger history, on identical rows; ΔBrier and Δaccuracy |
| Calibration | Reliability table (5 bins), mean predicted vs observed, Brier |
| SHAP | TreeExplainer per fold; mean \|SHAP\| per feature and per group by lead. **Model influence, not causation.** |

## 7. Not allowed

- Changing the targets, threshold, origins, criteria or grids after fitting.
- Using outer outcomes for any choice.
- Pre-2021 data, or new data collection.
- Using FIRI3 or FIRI v2 as labels.
- Production, dashboard or API changes, or modifying served artifacts.
- Pushing, merging or deploying.
