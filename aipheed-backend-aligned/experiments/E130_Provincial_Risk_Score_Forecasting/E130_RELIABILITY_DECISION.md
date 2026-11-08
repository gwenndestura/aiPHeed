# E130 reliability decision

## Classification: **BLOCKED**

All three BLOCKED conditions in the brief (Part 19) hold:

| BLOCKED condition | Evidence |
|---|---|
| No defensible provincial reference score can be established *for quarterly forecasting* | Gate G1–G8: no candidate passes (`out/gate.json`; re-checked after the search, `out/gate_recheck.json`). The only valid provincial reference, PFDR v1 (PSA subsistence incidence), is observed every two years. |
| The independent observations are insufficient | 10 provincial reference values (5 changes) are held, and 0 are quarterly. N1 needs ≥ 10 target quarters and ≥ 40 rows. |
| Data limits prevent a valid out-of-sample evaluation | No quarterly provincial target exists for any lead. No provincial subsistence round after 2023 is published (owner, 2026-10-31), so even the survey-year seal cannot be scored yet. |

**Why not PARTIAL SUCCESS or INCONCLUSIVE.**
- PARTIAL SUCCESS needs "defensible numerical forecasts". No provincial model could be trained or scored.
- INCONCLUSIVE needs "some evidence that supports the approach" from model results. There are none; the survey-year seal is not yet scored.

## Success criteria (brief Part 19)

| Criterion | Result |
|---|---|
| Valid provincial reference risk score | Partly. PFDR v1 is valid at survey-year resolution only. |
| Numerical risk-score forecasting demonstrated | **No** |
| ≥ 75 % of predictions within the pre-established tolerance | **Not evaluable** (tolerance fixed: 1.645 × reference SE) |
| ≥ 75 % classification accuracy where valid | **Not valid** (no approved PFDR thresholds) |
| LightGBM outperforms every baseline | **Not established** |
| Lead 2 meets the operational requirement | **No:** Lead 2 status **failed** (not evaluable) |
| Generalization, overfitting, leakage and bias audits | No model to audit. The predictor panel passes E119's 9 leakage checks. |
| Reliability criteria (N1–N7, R1–R7) | N1 / R1 fail; the rest are not evaluable |

## Maximum reliable lead

| Model | Maximum reliable lead |
|---|---|
| LightGBM | none |
| Persistence | none |
| PSA-only | none |
| NLP-only | none |
| Linear / logistic regression | none |

**The first unreliable lead is Lead 1.**

## What was achieved

1. **A frozen, execution-ready provincial protocol:**
   - the target gate;
   - the reference definition;
   - a measurement-based tolerance;
   - N1–N7;
   - the walk-forward design;
   - the models and ablation;
   - SHAP.

   It runs unchanged once a valid quarterly provincial target exists.
2. **The issue-date mismatch, resolved.** The dashboard Lead 2 is the next quarter after the dashboard quarter. E128's Lead k equals the dashboard's Lead k. Only the information horizon differs (SWS: k + 1 at the quarter-start issue, k after the mid-quarter release).
3. **The first sealed provincial numerical forecast.** It targets the next PSA provincial subsistence round after 2023 and was frozen before any search (`sealed/E130_SURVEY_YEAR_SEAL.csv`). It stays unscored until PSA publishes that round.
4. **Quantified causes and data requirements:**
   - 75 % within tolerance needs forecast error ≤ 1.022 × the reference SE;
   - a reliable pass needs 20–40 quarters and predictors explaining ≥ 50 % of the true change.
5. **A provincial affordability signal (descriptive).** Food-price rise ranked the 2021→2023 PFDR changes (Spearman 0.90, N = 5, partly mechanical); unemployment did not (0.00).

**Nothing in production, FIRI v2, FIRI3, E128 or E129 was changed.**
