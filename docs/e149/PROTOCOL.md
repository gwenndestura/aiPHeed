# E149: quarterly survey-anchored forecast with HIGH at 50 %. Protocol E149-P1

Locked before any E149 metric is computed: `backend/data/e149/out/PROTOCOL_LOCK.json`. E148 and its 60 % results are preserved unchanged; E149 imports them and writes only to `data/e149`.

## 1. Decision being tested

**HIGH = food-insecure households ≥ 50 %; LOW = below 50 %.** This is the threshold agreed with the thesis panelists (owner, 2026-11-04). The whole evaluation uses it: labels, class probabilities, logistic baselines, reliability checks, forecasts and LGU rankings.

**Measure.** Any-level HFIAS, the same as E148. The instruction states a prevalence threshold without naming a measure. Keeping the measure unchanged keeps this experiment comparable with E148. Base rates under moderate-or-severe are reported for the panel's information (section 6).

**Labelling.** This 50 % is the panel's cut-off. It sits inside FNRI's published "Medium" band (40 to 59.9), so an E149 HIGH must not be presented as FNRI "High".

## 2. What changes and what does not

Unchanged from the E148 lock: rows, inputs, release rules, issue dates, leads 1 to 8, LightGBM settings, tree-count selection, arms, seeds and bootstraps.

**Changed:** class threshold; soft class labels; logistic baselines, which train on those labels; arm selection on development rows, under the new class; P(HIGH).

**Expected consequence, stated before running.** LightGBM learns the continuous change, so its forecast percentages should equal E148's. Only P(HIGH), the classes and the logistic baselines should differ. E149 verifies this.

## 3. Evidence status

**The 2021 labels were opened by E148. E149 is not an untouched test, and must not be reported as one.** The rows are out-of-sample in time, because models train only on earlier releases, and no setting is tuned on them. E149 scores them openly, with no seal.

## 4. Class balance, already checked

Any-level ≥ 50 %: 2013 0.99, 2015 0.96, 2018 0.68, 2019 0.92, **2021 0.80 (20 of 25)**. CALABARZON 12 of 13 HFIAS rows; only Laguna 2018 is LOW.

**Always-HIGH therefore scores 0.80 on 2021, above the 75 % target.** High-risk recall is near-automatic. Passing R1 and R3 alone would show no skill, so two gates are added.

## 5. Validation gates

R1 to R6 are E148's, at the new threshold, with E148's definitions. Added, and required:

| Gate | Requirement | Why |
|---|---|---|
| R7 | Accuracy above always-HIGH and always-LOW (no-information rate) | At this base rate, 75 % can be reached with no model |
| R8 | LOW recall ≥ 0.50 | Otherwise the system cannot identify a LOW province |

**Maximum reliable lead** = the largest h with every lead to h passing R1 to R8 on 2021. It is 0 if lead 1 fails. Balanced accuracy, specificity and always-HIGH are reported beside accuracy.

News claim, quarterly value and independent SWS check as in E148. Because forecasts do not depend on the threshold, the SWS check result is inherited if the equality in section 2 holds.

## 6. Outputs and information for the panel

Five provincial forecasts with P(HIGH), class and interval; 142 LGU rankings using the same 0.6/0.4 vulnerability weights. A province is called HIGH or LOW by forecast ≥ 50 %, and **"not distinguishable"** is also shown when the 90 % interval includes 50 %.

For the panel: under moderate-or-severe at 50 %, CALABARZON has 0 of 13 HIGH rows.

## 7. Release rule

Production and the dashboard do not change unless all gates pass and the owner approves.
