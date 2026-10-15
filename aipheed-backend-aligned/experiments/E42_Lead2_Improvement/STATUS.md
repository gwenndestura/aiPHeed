# E42 status (2026-10-15): interrupted by the user and superseded by E43

E43 redirects the project from price pressure back to five-trigger food-insecurity-risk forecasting (Chapter I, §1.7). E42 is preserved as audit evidence.

## Completed

**Protocol and audit**
- Protocol frozen before any score (`PROTOCOL.md`, sha `4775e4e4…`).
- Phase 2 audit: `runs/audit/audit.json`.

**Runs**
- E41 reproduced byte-identically.
- One evaluation run (`runs/20261015T131128Z`) and a byte-identical repeat (`runs/20261015T131923Z`): predictions sha `277d724a…`, results sha `63d86a39…`.
- Frozen 2027-Q1 forecast: `frozen/E42_PROSPECTIVE_2027Q1.json`.

**Backend and frontend changes**
- Trigger `status`/`statusNote` on explainability.
- Card text built from status: the "0% Weather is hurting food supply" defect is fixed.
- `indicator_for(quarter)`: the indicator now describes the score actually served; each timeseries point carries `scoreType`.
- E42 record behind `AIPHEED_LEAD2_MODEL=e42`.
- Tests: backend 320 passed / 18 skipped; frontend vitest 34/34.

## Results (development evidence; every quarter seen; E40 holdout exposed)

**Pre-registered primary PS (prequential selection plus Platt)**
- Lead-2 accuracy 0.589, Brier 0.222; worse than E41 M1 (0.632 / 0.203).
- Classification: *Insufficient evidence to support Lead-2 operational use*.
- Cause: Platt recalibration fitted on HIGH-rich 2022–23 history raised probabilities just as 2024–25 became LOW-rich.

**Secondary fixed arms**

| Arm | Accuracy | Brier | Calibration slope |
|---|---|---|---|
| M1h (half drift) | 0.695 | 0.188 | 0.86 |
| M1z (flat prices) | 0.716 | 0.189 | 1.29 |

Neither is adopted post hoc.

**Grid on S-C** (9 quarters, 2024-Q3..2026-Q3)
- Every LR/LightGBM model has ROC-AUC below 0.5. Their accuracy (0.51–0.73) comes from predicting LOW in a LOW-rich period.
- NLP adds nothing over government-only: Brier gain −0.008 (LR) and +0.014 (LightGBM), both not significant.

**Triggers**
- Permutation importance: only the market group is clearly positive.
- Masking a group changes LightGBM probabilities by up to ±0.10, so missing data is not neutral.
- gap = food − headline is exactly collinear with them (infinite VIF).

**E40 label**
- 5 HIGH in 95 rows; 0 HIGH in the exposed holdout.
- E40's sealed holdout forecasts (lead 1) are 18/20 correct, with 2 false alarms.
- The E40 methods note says "all LOW", but 2025-Q4 Laguna and Quezon are HIGH in the sealed file.

## Not done
- `FINAL_REPORT.md` (superseded by the E43 report).
