# Updated forecast evaluation (audited inputs)

**Target:** T43c, Chapter I province-quarter high/low food-insecurity risk (frozen protocol sha `dd9ab815…`).
**Model:** CH1-LGBM, P(HIGH) = π_H (SWS Balance Luzon hunger above 11.3%) × π_P (one LightGBM over all 12 families).
**Inputs:** audited (Addendum 1, sha `a5d108e3…`). **Issue date:** first day of the quarter after the origin.
Source: `out/rerun_results.json`; served copy: `out/ch1_audited/results.json` → `backend/data/ch1_engine/`.

## Results by lead

| Lead | Rows (quarters) | HIGH share | Accuracy (90% CI) | Balanced acc. | Precision / recall | AUC | Brier | ALWAYS-LOW acc. | PERSIST-SI acc. | Reliable (R1–R7) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 (nowcast) | 80 (16) | 0.21 | 0.850 (0.763–0.925) | 0.754 | 0.67 / 0.59 | 0.804 | 0.120 | 0.787 | 0.850 | no (R4–R6 fail) |
| **1** | **70 (14)** | **0.24** | **0.914 (0.843–0.971)** | **0.883** | **0.82 / 0.82** | **0.923** | **0.087** | **0.757** | **0.743** | **yes** |
| 2 | 60 (12) | 0.28 | 0.583 (0.450–0.717) | 0.496 | 0.28 / 0.29 | 0.408 | 0.271 | 0.717 | 0.650 | no |
| 3 | 50 (10) | 0.28 | 0.520 (0.360–0.680) | 0.427 | 0.19 / 0.21 | 0.406 | 0.281 | 0.720 | 0.540 | no |
| 4 | 40 (8) | 0.25 | 0.575 (0.400–0.750) | 0.383 | 0.00 / 0.00 | 0.312 | 0.249 | 0.750 | 0.550 | no |

Lead 1 = the quarter that starts on the issue date (forecast made before any of its data exist, up to 3 months
ahead). Lead 1 confusion matrix: TP 14, FP 3, TN 50, FN 3.

## Lead 1 robustness

| Check | Value |
|---|---|
| Accuracy by third of the target quarters | 0.88 / 0.96 / 0.90 |
| Leave-one-quarter-out accuracy | 0.908 – 0.954 |
| Onsets caught (HIGH after LOW) | 7 of 10 |
| Brier vs PERSIST-SI | −0.170, p < 0.001 |
| Brier vs climatology | −0.114, p = 0.008 |
| Rows never used in any earlier scoring (2025-Q2/Q3) | 9 of 10 correct (persistence 7 of 10) |
| Pooled-area σ sensitivity | 0.929 |
| Calibration | mean forecast 0.30 vs observed 0.24 (slightly over-warns) |

## Objective 4 / H3 at Lead 1 (Brier, Holm-corrected)

| Comparator | Accuracy | Brier difference | Holm p |
|---|---|---|---|
| PERSIST-SI | 0.743 | −0.170 | < 0.001 |
| LR-COMB | 0.771 | −0.105 | < 0.001 |
| LR-GOV | 0.800 | −0.092 | < 0.001 |
| LR-NLP | 0.686 | −0.125 | < 0.001 |
| LGBM-GOV | 0.914 | +0.0004 | 0.83 |
| LGBM-NLP | 0.700 | −0.127 | < 0.001 |

CH1-LGBM beats five of six comparators and ties LGBM-GOV (the same model without news). H3 ("no difference") is
therefore **not** rejected under the frozen all-six rule.

## News (Objective 1 predictive value)

| Lead | With news | Without news | Brier difference (with − without) | Holm p |
|---|---|---|---|---|
| 0 | 0.850 | 0.850 | −0.0001 | 0.38 |
| 1 | 0.914 | 0.914 | +0.0004 | 0.38 |
| 2 | 0.583 | 0.700 | +0.035 (worse) | 0.032 |
| 3 | 0.520 | 0.640 | +0.072 (worse) | < 0.001 |
| 4 | 0.575 | 0.675 | +0.018 (worse) | 0.14 |

Regional FSSI (N1R, Addendum 2): coverage rises to 16 of 16 evaluation quarters, but no lead gains (Lead 2 Brier
−0.008, Holm p = 0.055; others ≥ 0.44). News stays in the model because the protocol requires all 12 families; it adds
nothing measurable at Lead 1 and harms Leads 2–3.

## Answer

- **75% accuracy:** reached at Lead 1 (0.914; lower 90% bound 0.843), and not at Leads 2–4.
- **Maximum reliable lead:** 1 quarter (up to 3 months). Under the stricter variant (balanced accuracy above every
  baseline) no lead qualifies, because LGBM-GOV ties.
- **Change from the audit:** none to any verdict; Lead 2 rose from 0.533 to 0.583, still failing.
- **Prospective seal (audited):** `out/ch1_audited/sealed_prospective.csv`, sha `be52d5c3…`; 2026-Q4 (Lead 1): all
  five provinces LOW (0.03–0.09). The first-run seal `e0bc1ec1…` is kept unchanged.
