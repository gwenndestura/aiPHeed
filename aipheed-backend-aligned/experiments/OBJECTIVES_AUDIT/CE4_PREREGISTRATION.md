# C-E4 pre-registration: C-E2 plus the target quarter's season (fixed before any fit, 2026-11-04)

**Development evidence;** the 20th historical attempt. C-b stays the main model unless C-E4 passes the adoption rule
and the team and adviser approve.

## Hypothesis

C-E2's Lead-1 and Lead-2 forecasts issued on the same date were identical at 86 of 113 origins: every input is known
at O(t) and the same for both leads, and the trees do not split on the lead. C-E3 (one model per lead) separated them
but lost accuracy (Lead 1 0.726, Lead 2 0.645), because each model saw one eighth of the rows.

The quarter being forecast has a season (lean months vs harvest months) that is known in advance and differs between
the two leads. Adding it to the stacked model keeps all training rows and lets the two forecasts differ when the
season matters.

## Definition

- **Everything as C-E2** (`ce2_model.py`, CE2_PREREGISTRATION.md): table, labels, walk-forward, stacked leads, the 8
  settings of `hr_lib.GRID` averaged, seed, fallback.
- **Two added inputs:** `qsin` = sin(2*pi*m/4) and `qcos` = cos(2*pi*m/4), where m = quarter of year of the target
  quarter q, minus 1 (calendar; no data).
- **SHAP:** mean TreeSHAP as C-E2. The season inputs are not one of the five dashboard groups.
- **Dashboard driver bars:** as C-E2 (relative view).
- **Nothing is selected or tuned on outcomes.**

## Evaluation and gates (as C-E2)

**Reported:**
- 62 quarters, all metrics, R1-R7, Algorithm 3;
- a 14-test Holm family (C-E4 x 7 baselines x 2 leads);
- paired Brier vs C-b and vs C-E2;
- the number of origins where the Lead-1 and Lead-2 forecasts are identical.

**Gates:** G1-G5 as C-E2. **Adoption:** G2 and G4, plus team and adviser approval.

**Reported whatever the result.**
PLAN-SHA256: 95a9cc6164212da10982f68bb32abd546f903491ac1e325a6c0229c5e338e917
