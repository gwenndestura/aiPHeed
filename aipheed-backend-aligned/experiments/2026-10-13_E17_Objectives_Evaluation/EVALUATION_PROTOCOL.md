# E17 Evaluation Protocol (frozen before any model is fitted or compared)

## Status

**Written:** 2026-10-13, after the input inventory (`runs/inspect_*`), which counted structure and classes only.

**Freeze.** The SHA-256 of this file and of `OBJECTIVE_EVIDENCE_MAP.md` and `DATA_TIMING_AUDIT.md` is stored in `runner/PROTOCOL_SHA256.txt`. The runners refuse to start if any of them changed.

**Basis for the requirements:**

| Element | Source |
|---|---|
| Requirements | Chapter I Objectives only (`OBJECTIVES_EXTRACTION.md`) |
| Target, inputs and model | The current implementation (`config/governing_model.json`, MODEL-B2), except where §3 of the timing audit departs from it |

**Not blind.** All 2021–2025 quarters were seen in earlier experiments.

## 1. Task (Objectives 2 and 4)

| Item | Specification |
|---|---|
| Unit | Province × quarter (5 provinces) |
| Target | Label of quarter t+k: **HIGH if S1 > 14.6**, else LOW. S1 = H + 2D, from file 1, full precision. **This is the implemented label: a constructed composite, not a measurement of food insecurity.** |
| Secondary target (reported, never used to choose) | HIGH if S1 > 10.84335, the aligned backend's Rule-L threshold used in E9–E15 |
| Lead time k | 1, 2, …, 8 quarters. Origin O = first day of quarter t+1; target quarter t+k. |
| Inputs at O | News of quarter t (9); government of quarter t−1 (36); `sws_hunger` = latest production round published before O (1). **46 inputs.** `poverty_incidence` is excluded (timing audit D2). |
| Training rows | Pairs (t′, t′+k) with t′ ≥ 2021-Q1 and with label(t′+k) **published before O**: t′+k ≤ t−1, and all production SWS rounds of t′+k published before O |
| Test rows | Pairs (t, t+k) with a label for t+k, where t+k ≤ 2025-Q4 and there are **at least 8 distinct labelled training quarters** (the implementation's `outer_min_target_quarters`). Each test quarter is one fold of 5 province rows. All five provinces are always together. |
| Missing values | No imputation for LightGBM. Logistic regression uses the training-median imputation. **Nothing is set to 0.** |

## 2. Models (fixed; no tuning)

| Arm | Role | Definition |
|---|---|---|
| **M**: proposed LightGBM | Objective 2's model | `LGBMClassifier(objective="binary", verbosity=-1, random_state=42, scale_pos_weight=(1−p)/p)`, where p is the HIGH share of the fold's training rows (implementation). Otherwise library defaults. **All 46 inputs. HIGH if probability ≥ 0.5.** If the training rows hold one class, the model predicts that class and the fold is flagged. |
| **B-I**: naive persistence | Objective 4-I | The province's latest label published before O |
| **B-II**: PSA-only indicator | Objective 4-II | Logistic regression on the 20 PSA-sourced inputs, timing t−1: food CPI level, YoY, lag and accel; rice price, lag and accel; unemployment, lag and accel; food − headline, lag and accel; headline CPI; five commodity prices; cpi_dev |
| **B-III**: NLP-only sentiment | Objective 4-III | Logistic regression on FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel (timing t) |
| **B-IV**: logistic regression | Objective 4-IV | Logistic regression on all 46 inputs |
| **REF**: majority class | Reference for class imbalance (not a Chapter I baseline) | The majority class of the fold's training labels |

**Logistic regression settings:** median imputation and standard scaling fitted on training rows only; `LogisticRegression(C=1.0, max_iter=5000)`; no class weights; HIGH if probability ≥ 0.5.

**Why logistic regression for B-II and B-III:** Chapter I does not say which model type these two baselines use. The SOP calls the comparisons "logistic regression variants", which is used here as context.

## 3. Metrics (Objective 2)

**HIGH is the positive class.** For each k, pooled over the test rows and also per test quarter:

- accuracy, and **mean fold accuracy** (mean of the per-quarter accuracies);
- precision and recall (HIGH);
- F1 (HIGH) and weighted F1;
- balanced accuracy and recall for LOW;
- ROC-AUC and PR-AUC, only when the test rows contain both classes. Persistence and the majority reference give hard 0/1 scores, so their AUC is reported as degenerate.
- the confusion matrix;
- n training rows (per fold), n test quarters, n test rows, and HIGH/LOW counts.

## 4. Comparisons and findings (descriptive; Chapter I sets no criterion)

**Model against baselines.** For each k with at least 5 test quarters:

- the accuracy and balanced-accuracy differences of M against each baseline and the majority reference;
- the quarter-cluster bootstrap 95% interval of the accuracy difference (10,000 draws, seed 20261013);
- the number of quarters in which M is more accurate.

**Findings reported for each k:**

| Finding | Rule |
|---|---|
| **(F1) Accuracy level** | Mean fold accuracy, and whether it reaches 0.75. **0.75 appears in your earlier brief, not in Chapter I, so it is reported for information and is not used as Chapter I's criterion.** |
| **(F2) Outperforms the baselines** | All of: ≥ 5 test quarters; M's accuracy **and** balanced accuracy ≥ every Chapter I baseline and the majority reference; the bootstrap interval of the accuracy difference against the strongest baseline (highest accuracy) lies entirely above 0 |
| **(F3) Reliability** | **Chapter I defines no criterion, so reliability is reported as not determinable.** The report states what a criterion would need: a threshold, both classes evaluated, enough independent quarters, and a target that measures what is claimed. |

**Insufficient evidence:** any k with fewer than 5 test quarters.

## 5. Sensitivity and reference analyses (never used to choose)

| ID | Analysis |
|---|---|
| **R0** | The implementation's own recorded rules for k = 1: training rule "target quarter precedes the test quarter", `poverty_incidence` included, M only. It shows how the earlier 0.818 arose. |
| **S-T0** | All arms with the secondary target (S1 > 10.84335) |

## 6. Supporting continuous horizons (the earlier "forecast horizon" request; regional hunger, F, D)

| Item | Specification |
|---|---|
| Targets | H (regional, one value per quarter); F[p] and D[p] (provincial) |
| Origin | O = start of quarter t+1; target t+k, k = 1…4 |
| Inputs | H: latest production or supplementary round published before O. F and D: quarter t−1. |
| Baseline | Carry-forward of the latest available value |
| Model | Ridge (α = 1, training-standardized) on that latest value. This is E13's compact model. |
| Training | Pairs whose target was published before O; at least 6 training quarters |
| Reported | MAE, RMSE, test quarters, rows, error by quarter, bootstrap interval of the MAE difference, quarters better |
| Status | **"insufficient"** (< 5 test quarters); **"beats baseline"** (interval below 0 and better in ≥ 2/3 of quarters); otherwise **"does not beat baseline"** |
| Operational reliability | **"Not determinable"** in every case. No defensible error tolerance exists in Chapter I or the project records. |

## 7. Other objectives

| Objective | What is done |
|---|---|
| 1 | Coverage counts of FSSI, triggers and topic outputs, 2021–2025. Code inspection. |
| 3 | What drives the within-province vulnerability ranking (poverty fallback against density). The "validated province forecasts" precondition is checked against the Objective 2 results. |
| 5 | A search of the records for deployment and ISO/IEC 25010 results. Whether NNS 2019 and 2023 values exist in the project. |

**SHAP is not evaluated.** It is not an objective.

## 8. Order, seal, reproducibility

1. Verify the hashes.
2. Build every fold's predictions for all arms; run the future-perturbation check.
3. Write `predictions.csv` and hash it (`SEAL.json`).
4. Only then join the labels and compute the metrics.
5. Run twice and confirm byte-identical outputs.
