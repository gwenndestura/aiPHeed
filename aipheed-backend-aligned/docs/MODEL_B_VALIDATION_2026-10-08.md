# MODEL-B Validation: Reproducing the 78.2% Result

Prepared 2026-10-08. **Outcome: the 78.2% result does not survive validation,
and MODEL-B is not ready for production.** MODEL-A (the served 12-feature model)
is unchanged. Nothing is committed and Chapter III is not edited.

Evidence, preserved so later runs cannot overwrite it:
`evidence/2026-10-08_model_b/` (configuration, input SHA-256 hashes, scripts,
per-row walk-forward predictions, Algorithm 4 results, timing audit).

```bash
python -m scripts.supplementary.timing_audit
python -m scripts.supplementary.algorithm4_timing_valid
```

## A. Model specification tested (MODEL-B candidate)

| Item | Specification |
|---|---|
| Algorithm | Algorithm 3: LightGBM with library defaults (objective binary, random_state 42), no class weighting |
| Features | 45 Section 3.3.2.6 candidates + CPI_dev (Eq. 5 legend) + SWS hunger; list in `MODEL_B_CONFIG.json` |
| Horizon | One quarter: features of quarter t paired with the label of t+1, same province |
| Evaluation | Walk-forward expanding window, minimum 8 target quarters, 11 test quarters, 55 rows, cut-off 0.50 |
| Poverty incidence | 2018 survey through 2022-Q3; 2021 survey from 2022-Q4 (released 15 Aug 2022); 2023 survey from 2024-Q4 (released Aug 2024) |
| SWS hunger | Latest round whose release date precedes the start of the forecast quarter (dates from the SWS article timestamps) |

## B. Reproduction against the 78.2% diagnostic

| Version | Accuracy | Precision | Recall | F1 | AUC |
|---|---:|---:|---:|---:|---:|
| 78.2% diagnostic (T0) | 0.782 | 0.819 | 0.782 | 0.784 | 0.815 |
| SWS as published, government data of t (T1) | 0.764 | 0.808 | 0.764 | 0.765 | 0.804 |
| Strict Rule 3, government data of t-1 (T2) | 0.764 | 0.808 | 0.764 | 0.765 | 0.824 |

**Cause of the change: SWS timing.** The diagnostic paired each quarter's SWS
figure with the next quarter's label. SWS publishes most rounds weeks into the
following quarter, so in **all 11 test quarters** that figure was released after
the forecast quarter had begun (for example 2023-Q4's survey on 22 Jan 2024,
used to forecast 2024-Q1). With SWS as actually published, it adds nothing
(0.764 with or without it).

## C. Accuracy by year

| Evaluation period | T0 (invalid) | T1 | T2 strict | Meets 75%? (T1 / T2) |
|---|---:|---:|---:|---|
| 2022 (1 fold) | 0.80 | 0.80 | 0.80 | Yes / Yes |
| 2023 (4 folds) | 0.75 | 0.75 | 0.85 | Yes / Yes |
| 2024 (4 folds) | 0.75 | **0.70** | **0.60** | **No / No** |
| 2025 (2 folds) | 0.90 | 0.90 | 0.90 | Yes / Yes |
| Overall | 0.782 | 0.764 | 0.764 | Yes / Yes |

Across minimum training windows of 6-10 quarters: T1 0.754-0.767; T2
0.733-0.767. Two quarters ahead: 0.70-0.72.

## D. Leakage audit

Per forecast quarter (full table: `results/timing_audit.csv`):

| Forecast quarter | SWS value used (T1/T2) | Released | SWS of quarter t released | In time? | Poverty estimate |
|---|---|---|---|---|---|
| 2022-Q4 | 2022-Q2 | 2022-06-06 | 2022-10-29 | No | 2018 survey |
| 2023-Q1 | 2022-Q3 | 2022-10-29 | 2023-01-19 | No | 2021 survey |
| 2023-Q2 | 2022-Q4 | 2023-01-19 | 2023-05-11 | No | 2021 survey |
| 2023-Q3 | 2023-Q1 | 2023-05-11 | 2023-08-02 | No | 2021 survey |
| 2023-Q4 | 2023-Q2 | 2023-08-02 | 2023-11-20 | No | 2021 survey |
| 2024-Q1 | 2023-Q3 | 2023-11-20 | 2024-01-22 | No | 2021 survey |
| 2024-Q2 | 2023-Q4 | 2024-01-22 | 2024-04-30 | No | 2021 survey |
| 2024-Q3 | 2024-Q1 | 2024-04-30 | 2024-07-23 | No | 2021 survey |
| 2024-Q4 | 2024-Q2 | 2024-07-23 | 2025-01-14 | No | 2021 survey |
| 2025-Q1 | 2024-Q2 | 2024-07-23 | 2025-01-14 | No | 2023 survey |
| 2025-Q4 | 2025-Q1 | 2025-03-29 | no round | - | 2023 survey |

Other time-sensitive series: food CPI, prices, labour force and remittances for
quarter t complete their release one to six weeks into quarter t+1. T1 assumes
the forecast is issued after those releases; T2 uses quarter t-1 to be strictly
"before the forecast period". News features (FSSI, triggers) are available at
the end of quarter t under both. SWS release dates for 2024-Q3 to 2025-Q4 come
from the release pages (the fourth-quarter-2024 page shows "Jan 14, 2024" for a
December 2024 survey; 14 January 2025 is used).

## E. 45 versus 12 features

Chapter III supports both readings:

| Reading | Evidence (THESIS 2 (9), Chapter III) |
|---|---|
| 45-feature matrix | Algorithm 3: "Input - 45-feature matrix, 120 rows spanning 5 provinces across 24 quarters" (line 1418). Algorithm 4: "Input - 45-feature matrix with Maximum Reliable Lead Time k as fixed forecast gap" (line 1462). Section 3.5: "a 45-column training matrix" (line 1930) |
| 12 features | Section 3.2: the matrix "is reduced to 12 final features through the selection process described in Section 3.3.2.7" (line 1164). Section 3.4.3: "the 12 features actually used for training and SHAP attribution" (lines 1781-1782); "LightGBM Training ... on the 12-feature, 120-row matrix" (line 1825) |
| SWS in the matrix | Section 3.3.2.6 joins "SWS hunger" (line 1281) |
| Default model | Algorithm 3: "A default LightGBM classifier" (line 1399) |
| Timing | Rule 3: "All features will derive exclusively from data available before the forecast period" |

The 12-feature reading has more explicit statements about training, and
Section 3.3.2.7, which defines the reduction, is missing. Running Algorithms 3
and 4 on the 45-feature matrix is therefore **an interpretation that needs the
adviser's decision**, not a pure implementation correction. Measured
difference: 12 features 0.618, 45-feature matrix 0.764 (T1).

## F. Algorithm 4 (kept separate)

Chapter III: 100-trial TPE on nine hyperparameters, mean weighted F1, gap = k,
best parameters scored once on the last four holdout quarters, targets F1 >=
0.75 and AUC >= 0.80. On T2 inputs: CV weighted F1 0.784; holdout (20 rows,
only 2 LOW) accuracy 0.80, weighted F1 0.80 (met), AUC 0.50 (not met);
always-HIGH 0.90 and persistence 0.85 on the same rows. With two LOW rows the
holdout cannot measure AUC meaningfully. The production Algorithm 4 also still
applies the gap as a train/test gap with a same-quarter holdout (Level 1 fix
pending), which this diagnostic does not change.

## G. Production readiness: NO

| Acceptance criterion | Status |
|---|---|
| Follows Chapter III | Undetermined: 45 vs 12 needs the adviser |
| Only information available at prediction time | Yes under T1/T2; **no** for the 78.2% run |
| Poverty leakage removed | Yes (in diagnostics; production fix pending) |
| SWS timing valid | Yes under T1/T2 |
| Reproduces ~78.2% | **No** (0.764) |
| Overall >= 75% | Yes (0.764) |
| Every year >= 75% | **No** (2024: 0.70 T1, 0.60 T2) |
| Untouched future quarters, no test tuning, no target change | Yes |
| Production predictor uses the same construction | **No**: production builds no timed SWS, no poverty vintage, no t-1 government series, and serves same-quarter (k = 0) outputs |

Components that still assume MODEL-A: `trainer.py` (Eq. 5's twelve, balanced
weights, gap semantics), `features_fused.parquet` (no SWS, same-year poverty),
`predictor.py` and the dashboard timeline (k = 0 labelling), SHAP and municipal
rankings (generic, follow the model), alerts (generic). The priority layer is
already withdrawn and archived.

## H. Adviser decisions required

1. **45 or 12 features for Algorithms 3 and 4** (Section E). This decides
   whether 0.764 or 0.618 is the approved model's accuracy.
2. **When a forecast is issued** (Rule 3): before the forecast quarter starts
   (T2) or once quarter t's official releases are out (T1). Both give 0.764
   overall here, but they differ by year and by robustness.
3. **What 75% means for acceptance**: Algorithm 3's mean fold accuracy (0.764,
   passes) or every evaluation year (2024 fails).
4. Whether SWS hunger, timed by its release dates, belongs in the matrix
   (it does not change accuracy under valid timing).
