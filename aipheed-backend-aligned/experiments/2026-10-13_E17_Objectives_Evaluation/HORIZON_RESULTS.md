# Forecasting Accuracy by Lead Time (Objective 2)

**What was evaluated:**

| Item | Value |
|---|---|
| Model | The current implementation's LightGBM classifier (governing configuration MODEL-B2), with the timing departures D1–D5 in `DATA_TIMING_AUDIT.md` |
| Target | The implemented label: HIGH if S1 > 14.6 |
| Data | Eligible 2021–2025 data |
| Validation | Walk-forward, expanding window; origin at the start of quarter t+1; lead time k |

**Sources:**

- `HORIZON_RESULTS.csv` (one row per lead time)
- `HORIZON_ARM_METRICS.csv` (every arm)
- `PER_QUARTER_RESULTS.csv`
- `CONFUSION_MATRICES.csv`
- Run `runs/20261013T034704Z/`; replicate `runs/20261013T034910Z/` (byte-identical)

## 1. Results for the proposed model, one row per lead time

| k (quarters ahead) | Test quarters | Province-quarter rows | HIGH / LOW in test | Training labelled quarters | Accuracy (= mean fold accuracy) | Precision (HIGH) | Recall (HIGH) | F1 (HIGH) | Balanced accuracy | Recall (LOW) | ROC-AUC | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **7** (2023-Q4..2025-Q1, 2025-Q4) | 35 | 30 / 5 | 8–15 | **0.629** | 0.905 | 0.633 | 0.745 | 0.617 | 0.60 | 0.667 | Evaluated |
| **2** | **5** (2024-Q2..2025-Q1, 2025-Q4) | 25 | 23 / 2 | 8–14 | **0.680** | 0.941 | 0.696 | 0.800 | 0.598 | 0.50 | 0.522 | Evaluated (only 2 LOW cases) |
| 3 | 3 | 15 | 14 / 1 | — | 0.333 | 0.833 | 0.357 | 0.500 | 0.179 | 0.00 | 0.143 | **Insufficient evidence** |
| 4 | 1 | 5 | 4 / 1 | — | 0.600 | 0.750 | 0.750 | 0.750 | 0.375 | 0.00 | 0.000 | **Insufficient evidence** |
| 5 | 1 | 5 | 4 / 1 | — | 0.800 | 0.800 | 1.000 | 0.889 | 0.500 | 0.00 | 0.500 | **Insufficient evidence** |
| 6–8 | **0** | — | — | — | — | — | — | — | — | — | — | **Not evaluable.** No target quarter has 8 earlier labelled quarters published in time. |

**Why the horizons run out:**

- Labels exist for 16 quarters, 2021-Q2..2025-Q4. There is no SWS round in 2021-Q1 or 2022-Q1, and no production round in 2025-Q2 or 2025-Q3.
- At least 8 labelled training quarters must be published before each origin.
- The longer the lead time, the fewer test quarters remain.

**Per-quarter accuracy, proposed model** (correct out of 5):

| k | 2023-Q4 | 2024-Q1 | 2024-Q2 | 2024-Q3 | 2024-Q4 | 2025-Q1 | 2025-Q4 |
|---|---|---|---|---|---|---|---|
| 1 | 2 | 2 | 2 | 3 | 5 | 4 | 4 |
| 2 | — | — | 0 | 3 | 5 | 5 | 4 |

**Confusion matrices, proposed model:**

| k | TP | FP | FN | TN |
|---|---|---|---|---|
| 1 | 19 | 2 | **11** | 3 |
| 2 | 16 | 1 | **7** | 1 |

The model misses many HIGH cases. Its training quarters (2021–2023) are mostly LOW (HIGH share 3/15, 4/15 and 5/20 by year), while the test quarters are mostly HIGH.

## 2. Class imbalance and dependence

- **Imbalance.** The test rows are 86% HIGH at k = 1 and 92% at k = 2. Accuracy alone is therefore misleading. A rule that always says HIGH would score 0.857 at k = 1 and 0.92 at k = 2.
  - That "always HIGH" rule is **not** what the training-majority reference does: the training majority is LOW, so that reference scores 0.143 and 0.08.
  - Balanced accuracy and LOW recall are reported for this reason. **They rest on only 5 and 2 LOW cases.**
- **Dependence.**
  - The five provinces in a quarter share the same regional hunger value, which is the dominant part of the label.
  - The effective sample is the **number of test quarters (7 and 5)**, not the rows.
  - Intervals were bootstrapped by quarter.

## 3. Sensitivity analyses (not used to choose)

| Setting | k = 1 accuracy (M) | Note |
|---|---|---|
| **S-T0**: Rule-L label, HIGH if S1 > 10.84335 (33 HIGH / 2 LOW) | 0.657 (balanced 0.818, AUC 0.894) | "Always HIGH" would score 0.943, and persistence 0.886. The model is worse than both. |
| **R0**: the implementation's own recorded training rule (labels not yet published allowed) + `poverty_incidence` | 0.700 (balanced 0.728, AUC 0.763; 8 test quarters) | Still below the PSA-only baseline (0.800). The recorded 0.818 used 2020 data and a different window, and was not reproduced on 2021+ data. |
