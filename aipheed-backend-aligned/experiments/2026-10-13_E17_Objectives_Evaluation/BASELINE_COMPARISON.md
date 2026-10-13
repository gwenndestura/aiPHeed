# Baseline Comparison (Objective 4)

**Setup.** Identical folds and test rows for every arm. Target: S1 > 14.6. Timing-valid training. Sources: `BASELINE_COMPARISON.csv`, `HORIZON_ARM_METRICS.csv`, `CONFUSION_MATRICES.csv`.

**The four baselines**, as named in Chapter I Objective 4:

| ID | Baseline | Definition |
|---|---|---|
| I | Naive persistence | The province's latest published label |
| II | PSA-only indicator | Logistic regression on 20 PSA inputs |
| III | NLP-only sentiment | Logistic regression on the 4 FSSI inputs |
| IV | Logistic regression | Logistic regression on all 46 inputs |

**REF:** the training-majority reference, which is not a Chapter I baseline.

## 1. k = 1 (7 test quarters, 35 rows: 30 HIGH, 5 LOW)

| Arm | Accuracy | Precision (HIGH) | Recall (HIGH) | F1 (HIGH) | Balanced accuracy | Recall (LOW) | ROC-AUC | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|
| **Proposed LightGBM** | **0.629** | 0.905 | 0.633 | 0.745 | 0.617 | 0.60 | 0.667 | 19/2/11/3 |
| I. Naive persistence | 0.686 | 0.913 | 0.700 | 0.792 | 0.650 | 0.60 | (hard 0/1) | 21/2/9/3 |
| II. PSA-only indicator (LR) | **0.714** | 0.917 | 0.733 | 0.815 | 0.667 | 0.60 | 0.680 | 22/2/8/3 |
| III. NLP-only sentiment (LR) | 0.229 | 1.000 | 0.100 | 0.182 | 0.550 | 1.00 | 0.627 | 3/0/27/5 |
| IV. Logistic regression (all inputs) | 0.686 | 0.952 | 0.667 | 0.784 | **0.733** | 0.80 | **0.733** | 20/1/10/4 |
| REF: training majority (LOW) | 0.143 | — | 0.000 | — | 0.500 | 1.00 | (hard) | 0/0/30/5 |

**Accuracy difference, LightGBM minus baseline** (quarter-cluster bootstrap, 95% interval):

| Baseline | Difference (95% interval) | Quarters LightGBM better / tied |
|---|---|---|
| Persistence | **−0.057** (−0.114 to 0.000) | 0 / 5 |
| PSA-only | **−0.086** (−0.229 to +0.057) | 1 / 3 |
| NLP-only | +0.400 (+0.200 to +0.629) | 6 / 1 |
| LR (all inputs) | −0.057 (−0.286 to +0.200) | 1 / 3 |

## 2. k = 2 (5 test quarters, 25 rows: 23 HIGH, 2 LOW)

| Arm | Accuracy | F1 (HIGH) | Balanced accuracy | ROC-AUC | TP/FP/FN/TN |
|---|---|---|---|---|---|
| **Proposed LightGBM** | **0.680** | 0.800 | 0.598 | 0.522 | 16/1/7/1 |
| I. Naive persistence | **0.720** | 0.829 | **0.620** | (hard) | 17/1/6/1 |
| II. PSA-only (LR) | 0.560 | 0.718 | 0.304 | 0.391 | 14/2/9/0 |
| III. NLP-only (LR) | 0.200 | 0.231 | 0.565 | 0.413 | 3/0/20/2 |
| IV. LR (all inputs) | **0.720** | 0.837 | 0.391 | 0.717 | 18/2/5/0 |

**Against persistence:** −0.040 (−0.160 to +0.080).

## 3. k ≥ 3

| k | Test quarters | Result |
|---|---|---|
| 3 | 3 | LightGBM 0.333 against persistence 0.733 and LR (all inputs) 0.800 |
| 4 | 1 | — |
| 5 | 1 | — |
| 6–8 | none | — |

**Insufficient evidence at every k ≥ 3** (fewer than 5 test quarters).

## 4. Answer for Objective 4

**The proposed LightGBM model did not outperform the Chapter I baselines at any evaluable lead time:**

- **Naive persistence** was as good or better at k = 1 and k = 2.
- **The PSA-only baseline** had the highest accuracy at k = 1.
- **Logistic regression on all inputs** had the highest balanced accuracy and AUC at k = 1.
- **The model beat only the NLP-only sentiment baseline** (and the majority reference). That baseline predicted LOW almost everywhere.

**The sensitivity analyses do not change this:**

- **Rule-L label (S-T0):** the model is below persistence (0.886) and "always HIGH" (0.943).
- **The implementation's own training rule with poverty included (R0):** the model scores 0.700, against 0.800 for the PSA-only baseline.

**These comparisons use only 7 and 5 test quarters, with 5 and 2 LOW cases.** Most intervals are wide and include 0, so no ordering among the better arms is established either.
