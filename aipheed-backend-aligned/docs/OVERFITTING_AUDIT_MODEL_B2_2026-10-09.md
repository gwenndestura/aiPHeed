# Overfitting and Reliability Audit: 45-Feature MODEL-B2 (2026-10-09)

**Scope:** a supplementary audit. MODEL-B2 was not tuned, re-selected or re-thresholded on the outer test quarters.

**What was not touched:**

- the 55-row outer evaluation, its timing rules and its criteria;
- Chapter III;
- production MODEL-A (`models/lgbm_best.pkl` and `training_results.json` are unchanged since 2026-10-08 20:32);
- the earlier evidence files.

Nothing was committed or deployed.

**Files:**

- **Script:** `scripts/supplementary/overfitting_audit_b2.py`
- **Evidence:** `evidence/2026-10-09_overfitting_audit/`
- **Reproduce:** `python -m scripts.supplementary.overfitting_audit_b2`
- **Governing configuration:** `config/governing_model.json`, checked by `scripts/evaluate_governing_model.py` and `tests/unit/test_governing_model.py`.

---

## 1. Executive summary

**Classification: INCONCLUSIVE, because the available evidence is insufficient.** Within 2022-Q4 to 2025-Q4, the audit found **no classic overfitting**. It also could not show that the 81.8% reflects a food-insecurity signal that generalizes beyond the evaluated period.

**What was verified:**

- **The reported numbers reproduce exactly.** 45/55 correct, with identical predictions and probabilities (difference ≤ 1.1e-16), and the input-frame hash matches the frozen configuration. Timing-valid persistence (76.4%), naive persistence (80.0%), the clock-only model (78.2%) and the 12-feature model (74.5%) also reproduce.
- **No classic overfitting.**
  - **Accuracy:** mean training accuracy is 0.926, inner-validation accuracy is 0.816 (training data only) and outer accuracy is 0.818. The inner walk-forward correctly predicted the outer level.
  - **Stability:** dropping any one test quarter gives 0.80–0.86. Changing the evaluation start gives 0.80–0.82.

**What weakens the result:**

- **Selection exposure.** The 55 outer rows are not untouched. The 45-feature set and the class-weighting rule were both chosen after results on these same rows had been seen. To approximate the selection procedure honestly, five configurations (the 12-feature and 45-feature sets, with and without class weighting) were chosen by inner validation inside each fold. That nested procedure scores **78.2% (43/55)**. **The 81.8% is therefore an optimistic figure; the nested 78.2% is the less biased estimate.**
- **The model mostly predicts the quarter's regime, not which provinces differ.**
  - In 7 of the 11 quarters it gave all five provinces the same class.
  - Predicting the best single class for each quarter would score 85.5%.
  - Of the 8 rows that belong to the minority class within their quarter, the model got 4 right. Mean within-quarter AUC is 0.63.
  - From 2024 on, overall AUC is 0.52.
- **It is not distinguishable from simple references.** Clock-only scores 78.2% (p = 0.73) and has a *better* Brier score (0.153 vs 0.167). Timing-valid persistence scores 76.4% (p = 0.51). Quarter-cluster 95% intervals for every difference include 0.
- **It is sensitive to feature choice.**
  - **Price levels:** removing them gives 56–60%.
  - **Constructed commodity series:** removing them costs 5 rows (72.7%). These series are an exact transformation of food CPI from 2022-Q1, confirmed on all 992 rows.
  - **Selection inside folds:** the Section 3.3.2.7-style selection run inside each fold gives 69.1%.
- **It is sensitive to the label threshold.** The approved global-median threshold (14.6) is computed over all 95 labelled rows, test quarters included. Using a training-only median instead changes 8 test labels and gives 70.9%.
- **No untouched future period exists.** There is no label after 2025-Q4, so performance on future quarters is **unverified**.

**What can be claimed:**

- "Under strict-timing walk-forward evaluation of 11 quarters, the governing 45-feature configuration classified 45 of 55 province-quarters correctly (81.8%; 95% CI about 70–91%). A nested procedure that also accounts for the configuration choice gives 78.2%."

**What cannot be claimed:**

- that it outperforms persistence or a time-trend reference (H3);
- that it identifies which provinces are at risk within a quarter;
- that it will reach 75% on future quarters;
- that the thesis meets its requirement because 81.8% exceeds 75%.

## 2. Audit methodology

| Item | Setting |
|---|---|
| Outer protocol (fixed) | Strict-timing frame (`frame_t2`); k = 1; expanding window; at least 8 target quarters; outer test quarters 2022-Q4 to 2025-Q4 (11 quarters, 55 rows); seed 42; cut-off 0.50 |
| Model | LightGBM defaults (`objective=binary`, `random_state=42`) plus `scale_pos_weight = (1−p)/p` from the fold's training rows |
| Inner validation | Walk-forward inside each outer training set; at least 5 inner target quarters; training rows only |
| Nested choice | 5 configurations, scored on inner validation. Exact ties were broken by a declared order with the Chapter III 12-feature reading first; outer results never decided anything. |
| Uncertainty | 10,000-draw bootstrap that resamples the 11 test quarters (rows in a quarter share inputs). Exact McNemar test on row discordance. Sign test on quarter-level differences. |
| Hashes | Config, input frame, five data files, the 55-row file and the script (`audit_results.json → provenance`) |

## 3. Verification of the 45-feature configuration

### 3.1 Count and composition

| Check | Result |
|---|---|
| 45 candidates = `features_fused.parquet` columns (excluding keys and `cpi_dev`) | PASS (45) |
| Model inputs = 45 candidates + `cpi_dev` + `sws_hunger` | PASS (**47 inputs**) |
| No explicit time-index feature among the inputs | PASS (none) |
| No label column among the inputs | PASS |
| Input-frame hash matches frozen MODEL-B2 (`118c3297…`) | PASS |
| 55 rows reproduced: identical predictions and probabilities; 45/55; acc 0.8182; F1 0.820; AUC 0.8278; predictions hash `25f2ea5e…` | PASS (14/14 checks in `evidence/2026-10-09_governing_45/`) |

**Discrepancy: "45 features" means 47 model inputs.** The governing model uses the 45 Section 3.3.2.6 candidates, plus `cpi_dev` (the Equation 5 term) and `sws_hunger` (the most recent SWS round released before the forecast quarter).

- A model with **only the literal 45** gives the **same 45/55** (AUC 0.822 vs 0.828), so the two extra inputs do not change accuracy.
- The configuration was **not** switched to the literal 45. How to describe the count is a wording decision (see Section 12).

### 3.2 Trace from source to prediction

The per-feature audit (`evidence/2026-10-08_optimization/feature_audit.csv`) covers all 47 inputs. Summary by family:

| Family (count) | Source | Built in | Strict-timing step (`frame_t2`) | Reaches the model as |
|---|---|---|---|---|
| FSSI and lags/accel (4) | News corpus, Algorithm 1 (Eq. 1–2) | `fssi_builder.py` → `feature_matrix.py` | News of t (not shifted) | Quarter t |
| Trigger proportions (5) | News corpus, Algorithm 2 | `trigger_classifier.py` | Not shifted | t |
| CPI, rice, unemployment, OFW, FX, fuel, Brent, climate, commodity levels, and their lags/accel (35) | PSA, BSP, DOE, EIA, NOAA, PAGASA, PSA NRP | `feature_matrix.py` loaders; forward fill within province, then zero fill | Shifted to t−1 | t−1 |
| Poverty incidence (1) | PSA official poverty statistics | `feature_matrix.py`; vintage set in `reliability_diagnostics.load` | Latest survey published | Release vintage |
| `cpi_dev` (1) | PSA CPI | `feature_matrix.py` (prior 4 quarters of the same province) | Shifted to t−1 | t−1 |
| `sws_hunger` (1) | SWS | `algorithm4_timing_valid.frame_t2` (release dates in `timing_audit.py`) | Latest round released before t+1 | As released |

**Implementation discrepancy: the governing model's timing exists only in supplementary scripts.** The strict-timing shift, the SWS release logic and the poverty vintage are applied by `scripts/supplementary/` code, not by the production training path.

- `app/ml/training/trainer.py` trains MODEL-A on the 12-feature selection without these steps.
- The governing configuration therefore has **no production training path yet**. Building one is a production change that needs separate authorization.

### 3.3 Git history

- The `aipheed-backend-aligned/` tree, including every MODEL-B and MODEL-B2 script and all evidence, is **untracked by git**. Its provenance rests on the file hashes recorded in the evidence, not on commit history.
- The predecessor `backend/` history shows result-driven iterations on the same 2020–2025 data:
  - `559c003` "push ROC-AUC over target";
  - `9ed80c0` per-quarter labelling;
  - `bd28fc8` "restore global stress threshold … best result was F1=0.84";
  - `747ffb1` "reduce feature set 45->15".

  The label definition and feature-count decisions were therefore made earlier with results in view (Section 10).

## 4. Training vs validation (`train_inner_outer_by_fold.csv`)

| Outer test quarter | Train rows | Train acc | Train AUC | Inner-val acc | Inner-val AUC | Outer acc | Trees / splits |
|---|---:|---:|---:|---:|---:|---:|---|
| 2022-Q4 | 40 | 0.650 | 0.72 | 0.800 | 0.22 | 0.8 | 3 / 3 |
| 2023-Q1 | 45 | 0.911 | 0.96 | 0.800 | 0.45 | 1.0 | 100 / 100 |
| 2023-Q2 | 50 | 0.920 | 0.96 | 0.840 | 0.46 | 0.8 | 100 / 100 |
| 2023-Q3 | 55 | 0.909 | 0.98 | 0.833 | 0.45 | 1.0 | 100 / 105 |
| 2023-Q4 | 60 | 0.917 | 0.99 | 0.857 | 0.56 | 0.8 | 100 / 131 |
| 2024-Q1 | 65 | 0.954 | 1.00 | 0.850 | 0.62 | 0.6 | 100 / 126 |
| 2024-Q2 | 70 | 0.971 | 1.00 | 0.822 | 0.63 | 0.4 | 100 / 175 |
| 2024-Q3 | 75 | 0.987 | 1.00 | 0.780 | 0.67 | 0.8 | 100 / 199 |
| 2024-Q4 | 80 | 0.988 | 1.00 | 0.782 | 0.71 | 1.0 | 100 / 205 |
| 2025-Q1 | 85 | 0.988 | 1.00 | 0.800 | 0.76 | 1.0 | 100 / 210 |
| 2025-Q4 | 90 | 0.989 | 1.00 | 0.815 | 0.80 | 0.8 | 100 / 233 |
| **Mean** | | **0.926** | **0.965** | **0.816** | | **0.818** | |

What the evidence supports:

- **A training-to-test gap of 0.11**, which grows to about 0.17–0.19 in late folds. The model memorizes its training quarters: training AUC is about 1.0.
- **Inner validation matched outer accuracy** (0.816 vs 0.818). This is not the signature of a model whose test accuracy collapses.
- **Low inner AUC** (0.22–0.63 through 2024-Q2) means the probability ranking inside training periods was poor. Accuracy there came mostly from predicting the dominant class.
- **The first fold is degenerate.** With 40 rows and `min_child_samples=20`, the model grows only 3 one-split trees.
- **Conclusion:** the high training fit is expected for boosted trees and is not by itself evidence of overfitting. Validation and test accuracy agree. The weak inner AUC is evidence of limited discriminative signal, not of overfitting.

## 5. Temporal validation

### 5.1 How the governing model's choices were made

| Element | How it is determined | Training-only? |
|---|---|---|
| Feature set | Fixed by configuration; not selected per fold | n/a, but chosen after results on the 55 rows were seen (Section 10) |
| Hyperparameters | LightGBM defaults; none tuned | Yes |
| Class weight | Training HIGH share of each fold | Yes. The rule itself was picked from 8 variants evaluated on the same folds. |
| Threshold | Fixed at 0.50 | Yes |
| Imputation | Forward fill within province (past only), then zero fill | Yes (no statistics fitted across rows) |
| `cpi_dev` | Prior 4 quarters of the same province | Yes |
| **Label threshold** | **Global median of all 95 labelled stress scores (14.6), test quarters included** | **No.** This is part of the approved target definition (Eq. 3), so it is reported, not changed. |

### 5.2 Supplementary nested experiments (training data only)

| Procedure | Correct | Acc | F1 | ROC-AUC | PR-AUC | 2022 / 2023 / 2024 / 2025 |
|---|---:|---:|---:|---:|---:|---|
| Governing MODEL-B2 (fixed configuration) | 45 | 0.818 | 0.820 | 0.828 | 0.866 | 0.80 / 0.90 / 0.70 / 0.90 |
| **Nested choice among 5 configurations** | **43** | **0.782** | 0.784 | 0.832 | 0.866 | 0.80 / 0.80 / 0.70 / 0.90 |
| In-fold feature selection (correlation filter > 0.85, then top 12 by training gain; Section 3.3.2.7 analogue) | 38 | 0.691 | 0.693 | 0.718 | 0.768 | 0.20 / 0.85 / 0.55 / 0.90 |

The five configurations were: 12-feature default, 12-feature weighted, 47 default, 47 weighted, and literal 45 weighted.

**Nested choices per fold:**

- From 2023-Q4 onward, inner validation chose the 47-feature weighted configuration in every fold (7 of 11 folds overall).
- In the early folds, all five configurations tied, and the declared order picked the 12-feature default.

So training data alone would have moved toward the 45-feature, weighted configuration. The honest estimate of "choose a configuration, then forecast" is 78.2%, not 81.8%.

### 5.3 Label-threshold sensitivity (diagnostic; the target is unchanged)

Each fold's training-row median was used as the threshold instead of the global median. The resulting thresholds were 12.1–14.3, against 14.6.

- 8 of the 55 test labels change.
- Accuracy is **0.709 (39/55)**, AUC 0.761.

Part of the measured accuracy therefore depends on a class boundary that was set using the test period.

## 6. Quarter-level stability (`quarter_level.csv`)

| Quarter | HIGH / 5 | Correct | Predicted HIGH | Model predicted one class for all 5 | Best single-class score for the quarter |
|---|---:|---:|---:|---|---:|
| 2022-Q4 | 1 | 4 | 0 | yes | 0.8 |
| 2023-Q1 | 0 | 5 | 0 | yes | 1.0 |
| 2023-Q2 | 1 | 4 | 0 | yes | 0.8 |
| 2023-Q3 | 1 | 5 | 1 | no | 0.8 |
| 2023-Q4 | 3 | 4 | 2 | no | 0.6 |
| 2024-Q1 | 4 | 3 | 2 | no | 0.8 |
| 2024-Q2 | 5 | 2 | 2 | no | 1.0 |
| 2024-Q3 | 4 | 4 | 5 | yes | 0.8 |
| 2024-Q4 | 5 | 5 | 5 | yes | 1.0 |
| 2025-Q1 | 5 | 5 | 5 | yes | 1.0 |
| 2025-Q4 | 4 | 4 | 5 | yes | 0.8 |

- **Effective sample: 11 temporal units, not 55 independent rows.**
- **9 of 11 quarters reach at least 0.75.** The two that don't are 2024-Q1 (0.6) and 2024-Q2 (0.4).
- **Quarter-cluster bootstrap 95% CI** for mean accuracy: **0.709–0.909**.
- **Leave-one-quarter-out:** 0.80–0.86. Dropping one year gives 0.77 (without 2023), 0.80 (without 2025), 0.82 (without 2022) and 0.89 (without 2024). No single quarter carries the result.
- **Changing the evaluation start** (minimum training 6–10 quarters): 0.80–0.82, AUC 0.81–0.83.
- **By period:**

| Period | Rows | Accuracy | AUC |
|---|---:|---:|---:|
| Through 2023 | 25 | 0.88 | 0.74 |
| 2024 onward | 30 | 0.77 | **0.52** |

- **Most correct predictions come from getting the quarter's regime right.**
  - In 7 quarters the model gave one class to all provinces.
  - 4 quarters are single-class in reality.
  - Predicting the best single class for each quarter would score 85.5%.
  - Of the 8 rows that are the minority class in their quarter, 4 were predicted correctly.
  - Within-quarter AUC across the 7 mixed quarters averages 0.63 (range 0.25–1.0).

## 7. Feature ablation and temporal dependence

Every variant uses the same outer protocol and the class-weighting rule; nothing was selected from these results. The commodity check is in `D_commodity_construction`.

| Feature set | n | Correct | Acc | AUC | Brier | 2022 / 2023 / 2024 / 2025 | Default LightGBM (correct) |
|---|---:|---:|---:|---:|---:|---|---:|
| Governing 47 (MODEL-B2) | 47 | 45 | 0.818 | 0.828 | 0.167 | 0.80 / 0.90 / 0.70 / 0.90 | 42 |
| Literal 45 candidates | 45 | 45 | 0.818 | 0.822 | 0.170 | 0.80 / 0.90 / 0.70 / 0.90 | 42 |
| Documented 12 (Eq. 5) | 12 | 41 | 0.745 | 0.789 | 0.181 | 0.80 / 0.80 / 0.65 / 0.80 | 38 |
| 12 selected inside each fold | 12 | 38 | 0.691 | 0.718 | 0.213 | 0.20 / 0.85 / 0.55 / 0.90 | n/a |
| Without food-price levels | 38 | 31 | 0.564 | 0.627 | 0.262 | 0.20 / 0.65 / 0.45 / 0.80 | 37 |
| Without any price level | 33 | 33 | 0.600 | 0.618 | 0.261 | 0.20 / 0.75 / 0.45 / 0.80 | 36 |
| Without all price-related features | 24 | 42 | 0.764 | 0.784 | 0.182 | 0.80 / 0.80 / 0.75 / 0.70 | 40 |
| Without the 5 constructed commodity series | 42 | 40 | 0.727 | 0.782 | 0.185 | 0.80 / 0.80 / 0.55 / 0.90 | 40 |
| Without index levels (`headline_cpi`, `food_cpi`) | 45 | 44 | 0.800 | 0.813 | 0.172 | 0.80 / 0.90 / 0.70 / 0.80 | 40 |
| Governing 47 + explicit time index | 48 | 44 | 0.800 | 0.826 | 0.168 | 0.80 / 0.90 / 0.70 / 0.80 | 42 |
| **Clock only (time index)** | 1 | 43 | 0.782 | **0.886** | **0.153** | 0.80 / 0.75 / 0.75 / 0.90 | 43 |

**Commodity construction confirmed.** All **992 of 992** post-2021 commodity rows are reproduced exactly (maximum difference 0.00) by:

> price(q) = price(2021-Q4, province, item) × (1 + food CPI YoY(q, province)/100)

These series are therefore **derived from food CPI**. From 2022-Q1 on they are not independent observations of commodity prices. The model relies on them:

- they carry 36.5% of MODEL-B2's gain;
- removing them costs 5 correct rows;
- in 2024 they act as a province marker (see the robustness report, Section 10).

Food-price levels as a group carry 74.5% of the gain.

**Temporal dependence.**

- The governing set has no explicit time feature.
- Adding one leaves results essentially unchanged (44/55).
- A model with *only* the time index reaches 78.2% with a better AUC and Brier score.

Together this is strong evidence of **potential temporal-trend dependence**: much of what MODEL-B2 gets right is available from "which period is it". It is not leakage. No feature was removed from the governing configuration; any removal needs methodology approval.

## 8. Baseline comparisons (same 55 rows)

| Reference | Correct | Acc | F1 | Precision (w) | Recall (w) | 2022 / 2023 / 2024 / 2025 |
|---|---:|---:|---:|---:|---:|---|
| MODEL-B2 | 45 | 0.818 | 0.820 | 0.841 | 0.818 | 0.80 / 0.90 / 0.70 / 0.90 |
| MODEL-B (default weights) | 42 | 0.764 | 0.765 | 0.808 | 0.764 | 0.80 / 0.85 / 0.60 / 0.90 |
| Persistence, timing-valid | 42 | 0.764 | 0.766 | 0.781 | 0.764 | 0.80 / 0.80 / 0.65 / 0.90 |
| Persistence, naive (**diagnostic only**: uses labels not yet released) | 44 | 0.800 | 0.802 | 0.808 | 0.800 | 0.60 / 0.80 / 0.80 / 0.90 |
| Clock only | 43 | 0.782 | 0.784 | 0.819 | 0.782 | 0.80 / 0.75 / 0.75 / 0.90 |
| Training-majority class | 22 | 0.400 | 0.229 | 0.160 | 0.400 | 0.80 / 0.75 / 0.10 / 0.10 |

Paired comparison of MODEL-B2 against each reference:

| MODEL-B2 vs | B2 right / ref wrong | Ref right / B2 wrong | McNemar p | Quarter-bootstrap 95% CI of the difference | Quarters better / tie / worse | Sign-test p |
|---|---:|---:|---:|---|---|---:|
| MODEL-B | 3 | 0 | 0.25 | [0.000, +0.109] | 3 / 8 / 0 | 0.25 |
| Timing-valid persistence | 6 | 3 | 0.51 | [−0.036, +0.145] | 5 / 4 / 2 | 0.45 |
| Naive persistence (diagnostic) | 4 | 3 | 1.00 | [−0.091, +0.109] | 4 / 5 / 2 | 0.69 |
| Clock only | 5 | 3 | 0.73 | [−0.127, +0.182] | 3 / 7 / 1 | 0.63 |
| Training-majority class | 25 | 2 | < 0.001 | [+0.218, +0.636] | 8 / 3 / 0 | 0.008 |

**How to read this:**

- **The training-majority baseline is not a strong reference.** Because the HIGH share rose over time, the training majority stayed LOW until the end. It is the only reference MODEL-B2 clearly beats.
- **The other differences are not established.** Against persistence, the clock and MODEL-B, the differences are not statistically established. That does **not** show the models are equivalent; the data are too few to separate them.
- **H3 is not supported by this evidence.**

## 9. Probability calibration (`calibration_plot.png`)

| Probabilities | Brier | Brier skill vs training base rate | Log loss | ECE (5 bins) | Mean P / observed rate | PR-AUC (prevalence 0.60) |
|---|---:|---:|---:|---:|---|---:|
| MODEL-B2 | 0.167 (quarter-bootstrap 95% CI 0.123–0.210) | 0.40 | 0.522 | 0.117 | 0.544 / 0.600 | 0.866 |
| MODEL-B (default) | 0.184 | 0.34 | 0.582 | 0.120 | 0.482 / 0.600 | 0.879 |
| Clock only | **0.153** | **0.45** | **0.482** | 0.124 | 0.563 / 0.600 | 0.875 |
| Training base rate | 0.277 | 0 | 0.750 | 0.243 | 0.358 / 0.600 | 0.805 |

**MODEL-B2 reliability bins:**

| Predicted P(HIGH) | Rows | Mean predicted | Observed HIGH |
|---|---:|---:|---:|
| 0.0–0.2 | 9 | 0.10 | 0.22 |
| 0.2–0.4 | 10 | 0.30 | 0.40 |
| 0.4–0.6 | 11 | 0.46 | 0.36 |
| 0.6–0.8 | 8 | 0.67 | 1.00 |
| 0.8–1.0 | 17 | 0.92 | 0.88 |

**Findings:**

- The probabilities are informative: Brier skill is 0.40 over the training base rate.
- They are roughly but not reliably calibrated. HIGH is under-predicted at low and middle probabilities, and the 0.6–0.8 bin was HIGH every time.
- The class weighting shifts probabilities upward by design. Calibration is a different property from accuracy.
- With 55 rows (8–17 per bin) and 11 temporal units, the calibration estimates are very noisy.
- No calibration method was fitted, and none could be fitted without the outer labels.

## 10. Overfitting assessment

**The 45-feature selection decision:**

- **The comparison was fair.** The 12-feature and 45-feature configurations used the same frame, timing, folds, seed, threshold, class-weighting rule and metrics (`evidence/2026-10-09_governing_45/governing_evaluation.json`).
- **It was not fixed in advance.** The 45-feature reading was adopted after comparing 12 vs 45 on these same 55 rows. The class-weighting rule was picked from 8 variants on the same rows. The global-median label and earlier feature-count changes were also made with results in view (Section 3.3).
- **The 55 rows are not an independent confirmation of the selection.** The 81.8% carries selection bias. The nested estimate (78.2%) partly corrects for the configuration choice, but not for the earlier history.
- **Training data alone point the same way.** Inner validation preferred the 45-feature weighted configuration in every fold from 2023-Q4 on. The choice is consistent with training data, though not proven superior: 45-feature vs 12-feature gives McNemar p = 0.39.

**Assessment:**

| Question | Evidence | Verdict |
|---|---|---|
| Is there classic overfitting (test accuracy collapsing relative to validation)? | Inner 0.816 vs outer 0.818; LOQO 0.80–0.86; window sensitivity 0.80–0.82 | **Not detected** |
| Does the model memorize training quarters? | Training accuracy up to 0.99 and training AUC about 1.0 vs outer 0.82 | Yes, as expected for boosting; it does not translate into worse validation |
| Is the 81.8% stable to reasonable analysis choices? | Nested choice 0.782; training-median labels 0.709; in-fold selection 0.691; price ablations 0.56–0.76 | **No.** It is sensitive to the selection procedure, the label threshold and the feature set. |
| Is there a generalizable food-insecurity signal beyond the time trend? | Clock 0.782 with better AUC and Brier; within-quarter AUC 0.63; 2024+ AUC 0.52; no significant edge over persistence | **Not demonstrated** |
| Has generalization to future quarters been verified? | No labels after 2025-Q4 | **Unverified** |

**Classification: INCONCLUSIVE.** The evidence does not show substantial overfitting in the usual sense: validation and test agree, and the result holds across quarters and windows. It does show that:

- the reported figure is selection-optimistic;
- the figure is sensitive to the label threshold and feature choices;
- the predictive content cannot be separated from a temporal trend with 11 test quarters.

Even acceptable results within 2022–2025 would not guarantee performance on future quarters.

## 11. Remaining limitations

1. **Effective sample:** 11 temporal units. Every interval is wide.
2. **Selection exposure:** the outer rows have been inspected repeatedly (MODEL-A, the T0/T1/T2 timing variants, E0–E7, the robustness variants, this audit). No untouched evaluation data remain within 2020–2025.
3. **Label threshold:** the global-median threshold uses test-period stress scores. The approved Equation 3 says so explicitly; it is reported, not changed.
4. **Constructed commodity series** (exact food-CPI transformation from 2022-Q1), and rice switching from retail to wholesale in 2021.
5. **Potential temporal-trend dependence:** clock-only gets 78.2% and price levels carry most of the gain.
6. **Weak within-quarter discrimination:** mean AUC 0.63; 2024+ AUC 0.52.
7. **Calibration** is roughly right but noisy and under-confident in the middle range.
8. **Algorithm 4's AUC failure is unresolved** (the robustness report covers it). It is not addressed by this audit.
9. **The governing model has no production training path.** Its timing logic lives in supplementary scripts, and MODEL-A (12 features) is what is served.
10. **The governing code is untracked by git.** Its provenance rests on recorded hashes.

## 12. Recommendations and adviser decisions

**Recommendations (no action taken):**

1. **Keep the 45-feature configuration as the governing configuration.** It is defensible on these grounds:
   - the comparison was fair;
   - training-only nested validation prefers it;
   - it matches Chapter III's 45-column matrix, Algorithm 3/4 inputs and Section 3.5.

   It must be reported with:
   - the selection disclosure;
   - the nested 78.2% alongside the 81.8%;
   - the quarter-cluster interval;
   - the clock and persistence references;
   - the commodity construction and threshold sensitivity.
2. **Do not present 81.8% as independent confirmation** of the 45-feature choice, nor as evidence that H3 or the 75% requirement is met.
3. **Pre-register a prospective test now.** Freeze `config/governing_model.json` (SHA-256 recorded in the evidence). Score 2026-Q1 onward once SWS publishes those rounds, under the same rules. Report the result whatever it is. This is the only route to verifying future performance.
4. **Report within-quarter discrimination separately from overall accuracy.** For DA's use (which provinces to prioritize), the within-quarter AUC of about 0.63 is the relevant figure.

**Decisions that need adviser approval** (Chapter III was not edited):

| # | Decision | Proposed wording or option (not applied) |
|---|---|---|
| R1 | Feature count wording | Sec. 3.2 line 1164, Table 3.4.3.1 lines 1781–1782, 1817 and 1825: replace "reduced to 12 final features through Section 3.3.2.7" with "the 45 candidate features from Section 3.3.2.6, plus CPI_dev (Eq. 5) and SWS hunger as released before the forecast quarter (47 model inputs); no feature reduction is applied". Set d = M = 47. |
| R2 | Missing Section 3.3.2.7 | Either remove the references, or add a short section saying the governing configuration applies no reduction and that the correlation/SHAP reduction was evaluated as a comparison (69.1% when run inside folds). |
| R3 | Equation 5 | Present F as a function of the full feature vector X(t), with the listed terms as its NLP and price-signal components; or keep Eq. 5 and state that it lists core terms. |
| R4 | SWS in the matrix | Sec. 3.3.2.6 lists SWS as a joined source. In fact it is excluded from `features_fused` and enters as the latest released round. Wording needs to match. |
| R5 | Commodity data | Sec. 3.3.1.2 says "PSA NRP (vegetable, fish, livestock)" and "Ricelytics 2022–2025". Actual data: NRP observed through 2021, CPI-derived after; rice is PSA wholesale from 2021. |
| R6 | "A default LightGBM classifier" (Algorithm 3) | MODEL-B2 adds `scale_pos_weight`. Either approve the class-weighting rule, or report MODEL-B (default, 76.4%) as the Algorithm 3 result and MODEL-B2 as a supplementary result. |
| R7 | Global-median label threshold | Keep as approved and disclose the 70.9% training-median sensitivity, or adopt a training-only threshold. The latter changes the target and needs explicit approval. |
| R8 | Algorithm 4 / Section 3.4.4 | The AUC failure on a 2-LOW holdout is unresolved. Decide whether the non-publication rule blocks reporting. |
| R9 | H3 | Report as "not supported" (or "inconclusive"): MODEL-B2 vs timing-valid persistence p = 0.51; vs naive p = 1.00. |
| R10 | Production | Whether and when to build a production training path for the governing configuration and replace MODEL-A. |
