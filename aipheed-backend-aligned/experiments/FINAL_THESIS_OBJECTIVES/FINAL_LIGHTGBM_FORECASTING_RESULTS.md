# Final LightGBM forecasting results (CH1-LGBM)

**Target:** T43c, Chapter I province-quarter high/low risk (§1.4, §1.7). **Protocol:** `FINAL_TARGET_AND_EVALUATION_PROTOCOL.md`
(sha `dd9ab815…`, frozen before scoring). **Inputs:** audited (Addendum 1); the first run on held inputs is kept in `out/`.

## Model

P(HIGH) = π_H × π_P; HIGH when P ≥ 0.5.
- π_H = Φ((latest Balance Luzon hunger − 11.3)/σ), σ from earlier same-horizon errors of the latest reading.
- π_P = one LightGBM classifier of the province price condition, trained on all quarters complete before the issue
  date (expanding window), on 16 columns covering all 12 FIRI v2 families. Grid: depth {1, 2} × trees {50, 150} ×
  class weight {none, balanced}, min child 15, chosen by inner chronological log-loss.

## Results (audited inputs)

| Lead | Rows | Accuracy (90% CI) | Balanced | Precision / recall | AUC | Brier | Always-LOW | PERSIST-SI | Reliable |
|---|---|---|---|---|---|---|---|---|---|
| 0 nowcast | 80 | 0.850 (0.763–0.925) | 0.754 | 0.67 / 0.59 | 0.804 | 0.120 | 0.787 | 0.850 | no |
| **1** | **70** | **0.914 (0.843–0.971)** | **0.883** | **0.82 / 0.82** | **0.923** | **0.087** | 0.757 | 0.743 | **yes** |
| 2 | 60 | 0.583 (0.450–0.717) | 0.496 | 0.28 / 0.29 | 0.408 | 0.271 | 0.717 | 0.650 | no |
| 3 | 50 | 0.520 (0.360–0.680) | 0.427 | 0.19 / 0.21 | 0.406 | 0.281 | 0.720 | 0.540 | no |
| 4 | 40 | 0.575 (0.400–0.750) | 0.383 | 0.00 / 0.00 | 0.312 | 0.249 | 0.750 | 0.550 | no |

First run (held inputs): identical at Lead 1 (0.914), Lead 2 0.533; no verdict differs.

## Why Lead 1 works and Lead 2 does not

At Lead 1 the target quarter's food inflation is largely fixed by the base effect: last year's index for those months
is already published, and the latest index is known. A1 carries 0.67 of the price model's SHAP share. Two quarters
ahead, prices move with shocks (rice policy, typhoons) that nothing in the inputs anticipates; the model then does
worse than always-LOW.

## Seals

- First run: `out/sealed_prospective.csv`, sha `e0bc1ec1…`.
- Audited (served): `../FIRI_V2_DATA_AUDIT/out/ch1_audited/sealed_prospective.csv`, sha `be52d5c3…`.
- Issued 2026-10-01. 2026-Q4 (Lead 1): all five provinces LOW, 0.03–0.09. 2027-Q1 to Q3 (Leads 2–4): LOW, but outside
  the reliable horizon and marked indicative.

Details: `../FIRI_V2_DATA_AUDIT/UPDATED_FORECAST_EVALUATION.md`.
