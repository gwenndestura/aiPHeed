# E24 Frozen Evaluation Protocol (written and hashed before any E24 model was fitted)

**Freeze:** `runner/PROTOCOL_SHA256.txt` holds the SHA-256 of this file and of `runner/run_e24.py` (computed by script). The runner refuses to start if either changed.

**Not blind.** All 2021-Q1…2026-Q2 outcomes were examined in E9–E23. The E23 diagnosis was seen before this protocol was written:

- persistence errs exactly on the 5 label-change rows;
- the label is 65% regional hunger.

**Every result here is development evidence.** **No untouched authorized holdout exists** (Section 7).

## 1. Targets

| ID | Target | Status | Threshold | Label known at origin O(t) iff |
|---|---|---|---|---|
| **T1** | Approved composite: S1 = H + 2D (Chapter I §1.2 "composite food stress label combining SWS quarterly hunger data and PSA province-level food CPI deviation") | **PRIMARY, required for Chapter I** | Median S1 over labels published before O(t) (training window only), as in E23 | Quarter ≤ t−1 **and** every production SWS round of that quarter published before O(t) (E23 rule) |
| **T2** | Relative provincial food-price pressure: 1 if D(p,q) > 0 (province's food CPI YoY above the five-province mean) | **EXPLORATORY ONLY.** Never substituted for T1. | 0, fixed by definition (D is mean-zero within every quarter); not tuned | Quarter ≤ t−1 (monthly provincial CPI for t−1 is released before O(t); the December CPI of quarter t is not) |

**Why T2 is justified as exploratory:**

- it is one measured, provincial component of T1;
- it has no SWS gaps (2021-Q1…2026-Q2);
- it is balanced by construction;
- it tests whether any model carries **provincial** information.

It is **not** a food-insecurity outcome.

## 2. Origins, timing and features (identical for all models)

**Origins, leads and minimum training:**

- Origin O(t) = 00:00 PHT on the first day of quarter t+1, for t = 2021-Q1…2025-Q4.
- Leads k = 1…8.
- Minimum: 8 distinct labelled training target quarters.

**Feature groups at O(t):**

| Group | Contents |
|---|---|
| **N** (9) | News of quarter t: FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel, 5 trigger shares |
| **G** (37) | 36 government features of quarter t−1 (governing candidates − news − poverty_incidence + cpi_dev) + SWS hunger of the latest production round published before O(t) |
| **P** (5, target-specific) | From labels published before O(t), per province: last published target value, its margin to the origin threshold, last label, mean of the last 4 published values, last − previous published value |

**Training pairs:** (features at t′, label of t′+k), with the label published before O(t). Constant or all-missing training columns are dropped in-fold.

## 3. Models (every model scored on the same rows)

**Required (Chapter I / H3):**

| ID | Model |
|---|---|
| B1 | Naive persistence (last published label) |
| B2 | Logistic regression on G+N |
| B3 | Logistic regression on G |
| B4 | Logistic regression on N |
| B5 | LightGBM on G (nested) |
| B6 | LightGBM on N (nested) |
| **PROPOSED** | LightGBM on G+N (nested) with SHAP |

**Diagnostic:** MAJ, the training-majority class.

**Ablation (exploratory evidence per feature group):**

- logistic regression on P, G+P, N+P, G+N+P;
- LightGBM (nested) on P, G+P, N+P, G+N+P;
- **LRC** = logistic regression on G+N+P with C chosen in nested validation from {0.01, 0.1, 1, 10}.

**LightGBM nested search:** E23's 16 predeclared configurations; scale_pos_weight from the training rows; inner validation = the last 3 training target quarters, inner training ≤ v − k − 1, mean log loss. **Logistic regression:** median imputation, standardization, C = 1 unless LRC.

**Calibration** is not applied. Training windows hold 40–90 rows and, for T1, as few as 20 LOW. This is stated as a limitation.

**Threshold:** 0.5 for every model. No threshold is tuned on any outer-test outcome.

### FINAL candidate (E24-F): persistence-gated selection, fixed now

- **Pool:** {B1 persistence, PROPOSED, LightGBM G+N+P, LRC G+N+P, LightGBM G+P, logistic regression G+P}.
- **Inner accuracy:** at each outer origin, each pool member's accuracy is computed on the last 3 training target quarters, using only training data:
  - LightGBM members use E23 grid entry 0 (single-lead, 3 leaves, min_child_samples 5, 50 trees) in the inner step;
  - logistic regression uses C = 1;
  - persistence uses the last label known at the inner origin.
- **Choice:** the member with the highest inner accuracy is chosen. **Persistence is kept unless another member is strictly higher.** Remaining ties go in pool order.
- **Outer prediction:** the chosen member's outer prediction (its nested-tuned version, as computed above).
- **News:** retained only when a chosen member uses N. The share of origins choosing each member is reported.

## 4. Metrics and statistics

**Per target and lead, pooled over origins:**

- accuracy, balanced accuracy, precision, recall, F1, ROC-AUC (undefined when the test rows hold one class; reported as such), Brier;
- the confusion matrix;
- per-origin class counts and accuracy.

**Paired tests (FINAL and PROPOSED vs each of B1–B6 and MAJ, identical rows):**

- exact one-sided sign-flip test on per-origin accuracy differences;
- the same test on per-origin Brier differences;
- exact paired AUC permutation (within-origin swaps);
- Holm across B1–B6;
- origins better/worse;
- leave-one-origin-out range of the accuracy difference.

**Independent units = test quarters (origins), not province rows.**

## 5. Acceptance criteria for the forecasting goal (T1, FINAL, lead k = 1 declared primary)

| # | Criterion | Pass iff |
|---|---|---|
| C1 | Accuracy > 75% | Pooled accuracy > 0.75 |
| C2 | Beats the strongest applicable baseline | Strongest = highest pooled accuracy among B1–B6. FINAL accuracy is higher **and** the one-sided sign-flip p on per-origin accuracy < 0.05 **and** the mean Brier is not higher. |
| C3 | Not explained by predicting HIGH | Balanced accuracy ≥ 0.60 **and** greater than the strongest baseline's balanced accuracy |
| C4 | Defensible across folds | More origins better than worse vs the strongest baseline, **and** the leave-one-origin-out accuracy difference is ≥ 0 for every left-out origin |
| C5 | Information beyond persistence | FINAL is correct on more label-change rows (rows whose label differs from the last published label) than it gets wrong on unchanged rows |
| C6 | Reliability rule | E23 rule: ≥ 8 origins, ≥ 5 HIGH and ≥ 5 LOW, AUC origin-cluster bootstrap lower bound > 0.5, Brier better than persistence with Holm p < 0.05. **This rule is researcher-declared; adviser approval is pending.** |
| C7 | No leakage | All automated assertions pass: every training label is published before its origin; no training target ≥ the test target; features of t (news) and t−1 (government) only |
| C8 | Reproducible | A second run gives a byte-identical prediction seal |
| C9 | Generalizes to unseen quarters | **Cannot be met** without an untouched holdout (Section 7). Reported as NOT ASSESSABLE. Development origins never count. |

**The forecasting goal is met only if C1–C9 all pass.** The same criteria are reported for T2 as exploratory evidence; they do not count toward the goal.

## 6. Hypotheses (unchanged from E23)

- H1–H3 use E23's decision rules on T1 PROPOSED.
- H4/H5 use `instruments/DECISION_RULES.md` (E23) and need genuine DA Region IV-A responses.

## 7. Holdout policy

**No untouched authorized holdout exists:**

- 2026-Q1/Q2 outcomes were viewed in E18;
- 2026-Q3 onward and all 2026 features are protected or not authorized.

**The first valid generalization test is prospective:**

1. Freeze E24-F (this file + hashes).
2. Once 2026 features are authorized, generate and seal (SHA-256) forecasts for targets ≥ 2026-Q3 **before** those labels are opened.
3. Score only after publication and authorization.
4. A claim needs ≥ 8 new origins and ≥ 5 LOW rows.

`runner/minimum_data.py` estimates the number of new quarters needed.
