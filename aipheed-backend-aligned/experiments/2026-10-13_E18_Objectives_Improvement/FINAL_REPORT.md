# E18 Final Report

## What improved

1. **The evaluation is now honest about timing.** E18 shows that most of the model's apparent skill comes from information that is not available in real time. The same model scores 0.825 with the previous quarter fully known, but 0.629 under strict publication timing (E17).
2. **The root causes are identified with evidence** (`ROOT_CAUSE_ANALYSIS.md`):
   - The label's latest value is the best forecast. The structural rule equals persistence exactly.
   - Regional hunger dominates the label and is unforecastable.
   - There are very few LOW cases.
   - The current model leans on trending price levels.
3. **New, justified candidates were tested under a frozen protocol:** structural rules, structural LR, constrained and tuned LightGBM on stationary features, and two level-shift models for hunger.
4. **Authorized January–June 2026 data were added.** This shortens the 2027-Q1 horizon from 5 to 3 quarters and gives 2026-Q1 and 2026-Q2 as a descriptive check of the E17 v3 frozen candidates, which held.
5. **A development dashboard view shows the actual outputs,** with each target clearly separated and insufficient-data states (local only).

## What did not improve

1. **No model beat the simple baselines under the frozen rules,** at any horizon, for any target.
2. **No horizon meets the reliability working criterion.** The binding limit is the number of LOW test cases, 2–3 at h ≥ 2.
3. **Provincial food-insecurity accuracy still cannot be evaluated.** No independent provincial outcome exists.

## 2027-Q1 research forecast

h = 3, information through 2026-Q2:

| Output | Forecast |
|---|---|
| Regional hunger | **17.3%** |
| Provincial food inflation, % | Cavite 4.73, Laguna 3.97, Quezon 4.87, Rizal 4.33, Batangas 1.43 |
| Constructed label | Batangas LOW; the others HIGH |

**All are research outputs, labelled as not forecasts of provincial food insecurity.**

## What is still needed to satisfy the Chapter I objectives

1. **For you and your adviser:**
   - a reliability criterion for Objective 2-V;
   - a decision on how the constructed label is described;
   - a replacement anchor for NNS 2019 and 2023.
2. **Authorization of July–December 2026 data,** and later quarters, so the classifier can be tested on new quarters with LOW cases.
3. **An independent provincial outcome:** FNRI provincial microdata, CBMS, or a DA- or LGU-run FIES module.
4. **The ISO/IEC 25010 survey** with 50 DA Region IV-A evaluators, and the H4 ranking assessment.
5. **Public deployment,** if you decide to deploy (not done here).
