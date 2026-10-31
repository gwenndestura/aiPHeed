# E131 reliability report

## Overfitting

| Model (Lead 2, P-DASH) | Training MAE | Out-of-sample MAE | Notes |
|---|---|---|---|
| LGBM-ALL | 2.12 | 6.13 | All 100 trees split. Seeds 131–135: out-of-sample MAE 6.03–6.21 at Lead 2, 5.84–6.12 at Lead 1. |
| LLM | Two parameters (level-noise variance, plus the fixed observation variances) | 4.70 | Too few parameters to memorise anything |

**LightGBM overfits.** Hyperparameters were fixed in advance (no tuning on outcomes), so the gap is not a tuning artefact. There is simply too little predictive signal for ~40–100 training rows.

## Generalization

| Check | Result |
|---|---|
| Walk-forward, expanding windows, both issue policies | No model passes at any lead |
| Univariate set (Lead 2: 40 rows, 10 quarters) | LLM 0.38 within against PERSIST 0.40 (P-DASH); advantage not significant |
| Province-held-out | Not applicable: there is no quarterly provincial target. The provincial layer is checked at survey rounds (X3). |
| Untouched data | Only the prospective seal (2026-Q4 onward) |

## Bias (LLM, Lead 2)

| Bias type | Finding |
|---|---|
| Geographic | Metro Manila 0.71 within against 0.43 for the other areas; under-prediction in every area (−1.5 to −1.8 points) |
| By level | Over-predicts low quarters (+3.8) and under-predicts high quarters (−7.1): regression toward the mean, so **risk at high levels is understated** |
| Sharp increases | 0 of 7 caught |
| News coverage (E130) | Cavite 4.0 articles per quarter against Rizal 1.1 |
| Missing data | 2022-Q1 and 2025-Q1 have no SWS round; the Kalman filter skips them without imputing |
| From the proxy | Provincial model-based values depend on the deprivation measure (Quezon relative risk 0.76 against 2.86) |

## Leakage

- Every feature is point-in-time: SWS rounds published before the issue date, and CPI from day 10 after the month.
- The E119 covariates were taken as of the quarter start.
- Training targets had to be published before the issue date. Interval calibration used only targets published before the issue date.
- No pre-2021 rows were loaded; CPI YoY starts in 2022.
- Hyperparameters, the tolerance and the selection rule were frozen before any result.
- Seals are write-once.

## Calibration

80 % coverage at Lead 2: LLM 0.86, PERSIST 0.82, LGBM-ALL 0.57.

LLM's Kalman intervals are calibrated at Leads 2–3 and under-cover at Lead 1 on the univariate set (0.61).

## Reproducibility

Deterministic: fixed seeds, grids and inputs, with hashes in `data/acquisition_log.json` and `out/x3_inputs.json`. The scripts are listed in `README.md`, and `backend/tests/unit/test_e131_resolution.py` checks them.
