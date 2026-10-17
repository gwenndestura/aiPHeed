# E46 addendum: iteration I9, I8 with the prevalence decision rule (frozen before any I9 decision is computed)

**Written:** 2026-10-17, after the single I8 run (`runs/i8_20261017T001227Z`, addendum commit 77ef9dc).
**Freeze:** SHA-256 of this file (LF) in `runner/ADDENDUM_I9_SHA256.txt`, committed with the code before I9 is computed.

## 0. Evidence status

I8 result (S44): accuracy 0.771, balanced 0.665, HIGH recall 0.44, Brier 0.132, AUC 0.902. A2 fails, and EXT accuracy is 0.700.

I looked at those aggregate numbers only. I did not look at I8's row-level probabilities before writing this.

**I9 is hindsight-informed** (the eleventh look at S44 across E44–E46). Acceptance stays prospective.

## 1. Diagnosis: D5, a decision cut that ignores the event's prevalence

**Why 0.5 under-calls HIGH:**
- I8 ranks well: AUC 0.90 on S44, 0.77 on EXT.
- Its probabilities are reliable: Brier 0.132, and calibration-in-the-large passes A4.
- But T43 is a rare AND-event, with training prevalence π between 0.04 and 0.23. With calibrated probabilities of a rare event, p ≥ 0.5 selects only the most certain cases. HIGH recall is therefore low by construction, whatever the ranking.

**Why π is the right cut:**
- For a calibrated p, the cut that maximises expected balanced accuracy is p ≥ π. Balanced accuracy is Youden's J + 1, with equal weight on each class.
- Balanced discrimination is what gate A2 and the user's requirement ask for ("meaningful HIGH/LOW discrimination, not accuracy by the majority class").
- The rule uses no fitting. It differs from the D2 defect, which refitted Platt scaling plus a threshold grid on a few out-of-fold labels.

## 2. I9 (everything not listed is I8 exactly)

**Probabilities:** I8's p, unchanged, so Brier, AUC and calibration are I8's.

**Decision:** HIGH iff p ≥ π_t, where π_t is the share of HIGH among the T43 labels available at O'(t) (`K.available_labels` under the I8 timing: SWS rounds posted before O'(t), targets ≤ t−1).

**Computation:** from the committed `runs/i8_20261017T001227Z/predictions_i8.csv`, with no refit. `runner/e46_evaluate_i9.py` recomputes π_t at every origin from the data.

## 3. Final-candidate rule

The ADDENDUM_I8 rule applies, with I9 in place of I8:
1. A0–A4 on S44;
2. EXT accuracy ≥ 0.75;
3. minimum leave-one-quarter-out S44 accuracy ≥ 0.70;
4. Brier no worse than B-persist-O'.

**If I9 passes all four:**
- it is E46's final candidate, served behind `AIPHEED_LEAD2_MODEL=e46`;
- production stays E38 until the user decides;
- its status is "historical development criteria met (hindsight-informed); forecasting acceptance pending prospective validation".

**If it fails:**
- nothing new is served;
- I2 stays the `e44` candidate;
- the blocker is reported.

## 4. Prospective freeze

- **What:** I9's 2027-Q1 decisions, with π at O' = 2026-10-15, go to `frozen/E46_I9_PROSPECTIVE_2027Q1.json` (sha256).
- **Probabilities:** I8's frozen probabilities.
- **Acceptance:** the PROTOCOL section 5 prospective rule, unchanged.
