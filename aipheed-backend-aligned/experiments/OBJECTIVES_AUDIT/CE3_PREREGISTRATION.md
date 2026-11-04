# C-E3 pre-registration: C-E2 with one model per lead (direct multi-horizon) (fixed before any fit, 2026-11-04)

**Development evidence;** the 19th historical attempt. C-b stays the main model unless C-E3 passes the adoption rule
and the team and adviser approve.

## Hypothesis

C-E2 fits one model on all leads stacked, with the lead as an input. The trees almost never split on the lead, so the
Lead-1 and Lead-2 forecasts issued on the same date were identical at 86 of 113 origins (including 2026-Q4 and
2027-Q1, both 0.896).

Fitting a **separate model for each lead** (trained only on that lead's rows and labels) lets each horizon learn its
own relation between the inputs known at O(t) and hunger k quarters later. The two forecasts then differ whenever the
data say the relation differs.

## Definition

- **Inputs, table, labels, walk-forward, grid, seed:** exactly C-E2's (`ce2_model.py`, CE2_PREREGISTRATION.md).
- **At each origin and each lead k:** training rows are C-E2's training rows with lead == k only; fit all 8 settings
  of `hr_lib.GRID`; p = mean of the 8 probabilities; SHAP = mean TreeSHAP. Fallback as C-b when the lead's training
  rows are not eligible.
- **Dashboard driver bars:** as C-E2 (relative view, each quarter's own SHAP).
- **Nothing is selected or tuned on outcomes.**

## Evaluation and gates (as C-E2)

**Reported:**
- 62 quarters, all metrics, R1-R7, Algorithm 3;
- a 14-test Holm family (C-E3 x 7 baselines x 2 leads);
- paired Brier vs C-b and vs C-E2;
- the number of origins where the Lead-1 and Lead-2 forecasts are identical.

**Gates:** G1-G5 as C-E2. **Adoption:** G2 and G4, plus team and adviser approval.

**Reported whatever the result.**
PLAN-SHA256: 34b1c1f9445234129a26b856fe7c5bb7bf625d816d7ee29680f044abcf6d0e05
