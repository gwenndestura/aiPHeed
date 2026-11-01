# Model selection rule (pre-declared)

This file was written and committed **before** `backend/scripts/model_report.py` was first run. The rule is applied mechanically by that script; its output is `docs/aipheed/results/`.

## Candidates

| Order (simplest first) | Candidate | Estimated parameters | Feature or prior choices made before seeing outer-test results? | Eligible for selection |
|---|---|---|---|---|
| 1 | PERSIST: latest published SWS value | 0 | Yes | Yes |
| 2 | TREND-D: latest + 0.5 × last change (fixed) | 0 | Yes (E136 protocol, before computation) | Yes |
| 3 | SEAS-LLM: measurement-aware seasonal local level | 3 | Yes. Its quarter-effect hypothesis was data-prompted (E132 V3), but its parameters are re-estimated at each origin from training data only. | Yes |
| 4 | HFM-X: pooled level + 5 theory-signed drivers | 10 | Yes (E133 protocol, before results) | Yes |
| — | RIDGE-ALL: ridge, α = 10 fixed | ≈ 23 | Yes | **Not on the primary set.** It needs ≥ 20 training rows, so it has no forecasts on most S-U rows. It is reported on S-E132 for information. |
| — | X-RED: HFM-X with prior 0.5 | 10 | **No:** the prior was chosen after seeing outer-test results (E135) | **No.** Reported only. |
| — | SIMPLE (the one new simplified model): pooled level + rice, unemployment, news | 8 | **No:** features chosen from E133–E135 ablations on outer-test rows | **No.** Reported only. |

**Excluded models.** LightGBM is not a candidate, because the directive's list omits it. E131 and E132 already showed it overfits.

## Validation

**Chronological, expanding window.** At each quarter-start issue (P-DASH):
- every model is re-estimated from SWS rounds published before the issue (state-space parameters by maximum likelihood; ridge coefficients);
- it then forecasts Leads 1–4.

**No hyperparameter is tuned**: priors, α and grids are fixed in the source protocols. With no tuning, there are no inner folds to use. The outer test rows are scored once.

## Metrics

Each is reported per model and lead, on S-U (primary; n_obs ≥ 8) and S-E132:
- n eligible, n within tolerance, and the % within with a 95 % CI (block bootstrap over target quarters, 10 000 draws, seed 2026);
- MAE, RMSE, bias;
- high-hunger under-prediction: mean error in the top observed tercile;
- sharp-increase detection: rows within tolerance among rows with y − y_latest > 2·SE;
- prediction variance ÷ target variance;
- Pearson correlation;
- train-versus-test gap, where a training error is recorded (ridge); otherwise "n/a".

## Primary metric and tie-break

- **Primary metric:** share within the frozen tolerance at **Lead 2** on **S-U** (protocol lock E1, E2, T1).
- **Procedure:**
  1. Start with the incumbent = PERSIST.
  2. Take the eligible candidates in the order above.
  3. A candidate replaces the incumbent **only if the 95 % block-bootstrap CI of its paired within-share difference against the incumbent** (same target-quarter resamples) **lies entirely above 0**.
  4. Otherwise, the simpler incumbent stays.
- **Selected model:** the final incumbent.
- **Reliability:** N1–N7 are then applied mechanically at Leads 1–4 (protocol lock R1–R2). Nothing in this rule changes the tolerance, the eligible rows or the reliability criteria.
