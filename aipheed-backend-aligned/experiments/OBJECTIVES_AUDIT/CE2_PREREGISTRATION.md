# C-E2 pre-registration: C-E with the 8-setting grid averaged instead of selected (fixed before any fit, 2026-11-03)

**Development evidence;** the 18th historical attempt. C-b stays the main model unless C-E2 passes the adoption rule
and the team and adviser approve.

## Hypothesis

C-E (C-b + national unemployment change + OFW remittance decline) selects one of the 8 fixed LightGBM settings at
each origin. At recent origins it chose one-split trees, which use only one or two input groups.

Averaging the forecasts of **all 8 settings** (`hr_lib.GRID`: depth 1/2 × 50/150 trees × class weights none/balanced),
instead of selecting one:
- (a) removes the selection step's noise;
- (b) lets every input the deeper trees use contribute to each quarter's forecast.

## Definition

- **Inputs:** C-E's 23 (`ce_model.CE`), the same table, the same E2 feature (`out/ce_features.csv`), the same
  walk-forward from 1998-Q3, the same training rows and labels known at O(t).
- **At each origin:** fit all 8 settings (`hr_lib.LGBM`, seed unchanged).
- **Forecast:** p = mean of the 8 predicted probabilities. Fallback as C-b when training is not eligible.
- **SHAP:** the mean over the 8 models of TreeSHAP (log-odds), per input.
- **Dashboard driver bars:** each quarter's own SHAP of the forecast issued for it, grouped into the five groups.
- **Nothing is selected or tuned on outcomes.**

## Evaluation and gates (as C-E)

**Reported:**
- 62 quarters, all metrics, R1–R7, Algorithm 3;
- a 14-test Holm family (C-E2 × 7 baselines × 2 leads);
- paired Brier vs C-b and vs C-E;
- for every evaluated forecast, the share of each of the five groups and how many forecasts have every group above
  zero.

**Gates:**

| Gate | Condition |
|---|---|
| G1 | All 14 comparisons significant |
| G2 | Brier < C-b at both leads (p < 0.10) and accuracy not lower |
| G3 | R1–R7 |
| G4 | MRLT ≥ 2 |
| G5 | R7 fixed |

**Adoption:** G2 and G4, plus team and adviser approval.

**Reported whatever the result.**
PLAN-SHA256: a1b469da7f325c2e7582af57c1a5f4a1b62db308624ae1ce842049e4274bd1aa
