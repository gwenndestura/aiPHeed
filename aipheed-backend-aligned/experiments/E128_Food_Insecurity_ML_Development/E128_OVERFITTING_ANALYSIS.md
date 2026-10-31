# E128 overfitting analysis

**Method.** Mean over walk-forward folds.
- **Training:** each fold model scored on its own training rows (in-sample).
- **Inner:** the selected grid point's inner chronological log-loss.
- **Outer:** the unseen target quarter.

**Source.** `E128_MODEL_TRAINING_RESULTS.csv`.

## T1 (primary)

| Model | Lead | Train acc | Outer acc | Train Brier | Outer Brier | Inner log-loss | Outer log-loss | Train AUC |
|---|---|---|---|---|---|---|---|---|
| LightGBM | 1 | 0.92 | 0.62 | 0.078 | 0.332 | 0.54 | 0.99 | 0.92 |
| LightGBM | 2 | 1.00 | 0.88 | 0.010 | 0.082 | 0.32 | 0.26 | 1.00 |
| LightGBM | 3 | 0.96 | 0.86 | 0.042 | 0.208 | 0.36 | 0.61 | 1.00 |
| LightGBM | 4 | 1.00 | **0.00** | 0.024 | **0.704** | 0.34 | **2.13** | 1.00 |
| PSA-only | 1 / 2 / 3 / 4 | 0.91 / 0.95 / 0.91 / 0.91 | 0.69 / 0.88 / 0.29 / 0.33 | | 0.31 / 0.08 / 0.48 / 0.57 | | | |
| NLP-only | 1 / 2 / 3 / 4 | 0.97 / 1.00 / 0.90 / 0.93 | 0.69 / 0.88 / 0.86 / 0.67 | | 0.24 / 0.10 / 0.12 / 0.25 | | | |
| Log. Regression | 1 / 2 / 3 / 4 | 0.88 / 1.00 / 1.00 / 1.00 | 0.69 / 0.88 / 0.71 / **0.00** | | 0.31 / 0.04 / 0.22 / 0.90 | | | |

## T4 (sensitivity)

| Model | Lead | Train acc | Outer acc | Outer Brier |
|---|---|---|---|---|
| LightGBM | 1 / 2 / 3 / 4 | 0.86 / 0.91 / 1.00 / 1.00 | 0.73 / 0.38 / 0.43 / 0.33 | 0.21 / 0.40 / 0.52 / 0.53 |

## Findings

- **Every learned model overfits.**
  - Training accuracy is 0.86–1.00 and training AUC 0.90–1.00.
  - On unseen quarters, accuracy is 0.00–0.88.
  - The outer log-loss is 1.5–6× the inner log-loss at Leads 1, 3 and 4.
- **The Lead-2 T1 numbers (0.88) are not evidence of generalization.**
  - All 8 Lead-2 targets are HIGH.
  - A model that has seen HIGH in recent training rows predicts HIGH.
  - Persistence gets 8 / 8.
- **The Lead-4 collapse is distribution shift, not chance.**
  - At Lead 4 the training targets are 2021–2024 quarters, mostly LOW.
  - The model predicts LOW for 2025–2026, when hunger is 16–24 %.
- **Tree size.** With the smallest grid point (2 leaves), folds still use 29–67 trees with splits on 6–18 rows.
- **Seeds** (5 seeds; `out/seed_sensitivity.csv`):

  | Target | Lead | Outer accuracy across seeds |
  |---|---|---|
  | T1 | 1 | 0.54–0.62 |
  | T1 | 3 | 0.71–0.86 |
  | T4 | 2 | 0.25–0.38 |

  No seed makes any lead reliable.
- **Feature-importance instability.**
  - The top SHAP feature changes between leads: ONI at T1 Leads 1–3, hunger mean at T1 Lead 4, palay or food-CPI change at T4 Leads 1–2.
  - It also changes between folds.

**Conclusion.** The overfitting is fundamental: about 25 features and 6–18 training rows per fold. A smaller grid cannot remove it, because the number of independent quarters is the constraint.
