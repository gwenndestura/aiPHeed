# E128 model comparison (five models, identical rows)

**Rows.** At each lead, all five models are scored on the same outer origins (`E128_WALK_FORWARD_SPLITS.csv`). No model has a missing prediction on those origins.

**Sources.** `E128_LEAD_1_TO_4_COMPARISON.csv`, `out/pairwise_vs_baselines.csv`.

## What the metrics mean here

| Metric | Meaning |
|---|---|
| Accuracy | Share of quarters correctly called high or low hunger |
| Balanced accuracy | The mean of the HIGH and LOW hit rates. It is not inflated when nearly every quarter is HIGH. |
| Precision (HIGH) | When the model warns of high hunger, how often it is right (false-alarm cost) |
| Recall (HIGH) | Share of high-hunger quarters that were warned of (missed-warning cost). This is the most important figure for early warning. |
| F1 | Combines precision and recall |
| ROC-AUC / PR-AUC | Ranking quality across thresholds. Needs both classes. |
| Brier | Probability accuracy (see `E128_CALIBRATION_ANALYSIS.md`) |

## T1, all outer rows

| Lead (n) | Model | Accuracy | Balanced acc. | Precision | Recall | F1 | ROC-AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| 1 (13; 11 H / 2 L) | **LightGBM** | 0.615 | 0.773 | 1.00 | 0.545 | 0.71 | 0.59 | 0.332 |
| | Persistence | **0.846** | **0.909** | 1.00 | **0.818** | 0.90 | **0.91** | **0.154** |
| | PSA-only | 0.692 | 0.818 | 1.00 | 0.636 | 0.78 | 0.64 | 0.305 |
| | NLP-only | 0.692 | 0.614 | 0.89 | 0.727 | 0.80 | 0.64 | 0.235 |
| | Log. Regression | 0.692 | 0.818 | 1.00 | 0.636 | 0.78 | 0.64 | 0.311 |
| 2 (8; all H) | **LightGBM** | 0.875 | n/e | 1.00 | 0.875 | 0.93 | n/e | 0.082 |
| | Persistence | **1.000** | n/e | 1.00 | **1.000** | 1.00 | n/e | **0.000** |
| | PSA-only / NLP-only / LR | 0.875 / 0.875 / 0.875 | n/e | 1.00 | 0.875 | 0.93 | n/e | 0.077 / 0.097 / 0.039 |
| 3 (7; all H) | **LightGBM** | 0.857 | n/e | 1.00 | 0.857 | 0.92 | n/e | 0.208 |
| | Persistence | **1.000** | | | | | | **0.000** |
| | PSA-only / NLP-only / LR | 0.286 / 0.857 / 0.714 | | | | | | 0.478 / 0.116 / 0.219 |
| 4 (6; all H) | **LightGBM** | **0.000** | n/e | n/e | 0.000 | n/e | n/e | 0.704 |
| | Persistence | **1.000** | | | | | | **0.000** |
| | PSA-only / NLP-only / LR | 0.333 / 0.667 / 0.000 | | | | | | 0.571 / 0.249 / 0.904 |

n/e = not evaluable (only one class among the rows).

## T4 (sensitivity), all outer rows

| Lead (n) | LightGBM acc / BA / Brier | Persistence | PSA-only | NLP-only | LR |
|---|---|---|---|---|---|
| 1 (11) | 0.727 / 0.812 / 0.207 | 0.818 / 0.771 / 0.182 | **0.909 / 0.938 / 0.156** | 0.727 / 0.708 / 0.220 | 0.727 / 0.812 / 0.276 |
| 2 (8) | 0.375 / 0.367 / 0.395 | 0.500 / 0.467 / 0.500 | 0.500 / 0.400 / 0.378 | 0.375 / 0.300 / 0.415 | 0.500 / 0.533 / 0.379 |
| 3 (7) | 0.429 / 0.600 / 0.521 | 0.714 / 0.650 / 0.286 | 0.286 / 0.500 / 0.548 | 0.714 / 0.650 / **0.241** | 0.571 / 0.700 / 0.352 |
| 4 (6) | 0.333 / 0.500 / 0.526 | 0.667 / 0.625 / 0.333 | 0.333 / 0.500 / 0.561 | 0.667 / 0.625 / **0.250** | 0.167 / 0.250 / 0.609 |

## Does LightGBM outperform each baseline?

**Test.** Paired bootstrap Brier difference, one-sided, Holm-corrected across the 4 baselines; McNemar exact on correct calls.

| Baseline | T1 L1 | T1 L2 | T1 L3 | T1 L4 | T4 L1 | T4 L2 | T4 L3 | T4 L4 |
|---|---|---|---|---|---|---|---|---|
| Persistence | No (worse) | No (worse) | No (worse) | No (worse) | No | No | No (worse) | No (worse) |
| PSA-only | No | No | No (Holm p 0.052) | No | No (worse) | No | No | No |
| NLP-only | No (worse) | No | No (worse) | No (worse) | No | No | No (worse) | No (worse) |
| Logistic Regression | No | No | No | Holm p 0.048, but both are 0 % accurate | No | No | No | No |

**H3 (LightGBM better than all baselines) is not supported at any lead.**

## Summary

| Question | Answer |
|---|---|
| Highest observed accuracy (learned model) | 0.909, PSA-only, T4 Lead 1 (n = 11) |
| Best average walk-forward accuracy | Persistence (T1 mean 0.96 over Leads 1–4) |
| Best balanced accuracy | PSA-only, T4 Lead 1, 0.938 |
| Best HIGH recall | Persistence (T1 1.00 at Leads 2–4) |
| Best calibrated | Persistence (T1), NLP-only (T4 Leads 3–4), CLIM (T4 Lead 2) |
| Best at Lead 1 | Persistence (T1); PSA-only (T4) |
| Best at Lead 2 | Persistence (T1); CLIM / PSA-only (T4, all near chance) |
| Best overall under the frozen rule | **None qualifies** |
| LightGBM vs the four baselines | Not better than any, at any lead |
