# C-E5 pre-registration: regime adaptation for R3/R7, and the news ablation (fixed before any fit, 2026-11-04)

**Development evidence;** the 21st historical attempt. C-b stays the main model, and C-E2 the demo model, unless a
candidate passes the adoption rule below and the team and adviser approve.

## Research question

Why does C-E2 fail R3 (balanced accuracy 0.690 / 0.679) and R7 (thirds 0.952 / 0.524 / 0.85), and can a
theoretically justified change, fixed in advance, fix them without losing accuracy elsewhere?

## Evidence that motivates the hypotheses (`out/obj2_diagnostics.json`, read only, before this plan)

- **Regime change:** 95% of the quarters in 2010-Q1..2015-Q1 are HIGH, 48% in 2015-Q2..2020-Q4 and 65% in
  2021-Q2..2026-Q3.
  - C-E2's accuracy in the middle third is 0.524, and its LOW recall there is 0.364.
  - C-b (0.571), LOGIT (0.381) and persistence (0.429) fail the same third.
- **Bias towards HIGH:** C-E2's mean probability on LOW quarters is 0.60 (0.73 on HIGH). Overall LOW recall is 0.474.
  - The training history before 2015 is mostly HIGH, so the model's base rate lags when hunger falls.
- **Survey noise:** 9 of 14 Lead-1 errors are within 2 points of the 11.3% line. This part of the error is
  irreducible by any model.

## Hypotheses

- **H5R (recency weighting, concept drift):** weighting recent training rows more lets the model's base rate follow
  regime changes. This should raise LOW recall in 2015-2020 (R3, R7).
- **H5C (past-only recalibration):** a logistic recalibration fitted on C-E2's own recent past forecasts corrects the
  HIGH bias. It moves probabilities towards the recent observed rate (R3, R7, Brier).
- **H5N (Objective 1 ablation, descriptive):** removing the NLP input `z_N1R` from C-E2 changes the Brier score by
  less than 0.005 at both leads. This measures the NLP contribution directly; nothing is adopted from it.

## Candidates (each value fixed here, none tuned)

All candidates keep, unless stated:
- C-E2's 23 inputs, table, labels known at O(t) (`V.known_labels`), stacked leads and walk-forward from 1998-Q3;
- the mean of the 8 `hr_lib.GRID` settings, seed, fallback, target (SWS Balance Luzon > 11.3%) and decision rule
  (HIGH when p >= 0.50).

1. **C-E5R:** every training row gets the sample weight `0.5 ** ((t - q_row) / 16)`.
   - t = origin, q_row = the row's target quarter.
   - Half-life 16 quarters (4 years), chosen a priori as about one hunger regime in the SWS series.
   - LightGBM receives the weight through `sample_weight`. `class_weight` still follows the grid.
   - `hr_lib.py` is not edited (a subclass in the runner).
2. **C-E5C:** at origin t and lead k, take C-E2's stored forecasts for lead k whose target label is known at O(t)
   (`V.known_labels`), and keep the most recent 24 of them (6 years).
   - With at least 12 such forecasts, both classes present, and the forecast not a fallback: fit the logistic
     regression `y ~ logit(p)` (scikit-learn, L2, C = 1.0, p clipped to [0.001, 0.999]) and apply it to the current
     forecast.
   - Otherwise keep C-E2's p.
   - No information after O(t) is used.
3. **C-E2-NONEWS (ablation):** C-E2 without `z_N1R` (22 inputs).

## Evaluation (as C-E2)

- **Window and sample:** 62 verdict quarters (`R.frame`), Leads 1-2 (Leads 3-8 for Algorithm 3).
- **Metrics:** accuracy, balanced accuracy, precision, recall, F1, AUC, Brier, confusion matrix, thirds, R1-R7.
- **Algorithm 3:** the 75% rule.
- **Per candidate:**
  - the 14-test Holm family (7 baselines x 2 leads; paired Brier, one-sided cluster bootstrap, seed 2036,
    B 5000, as `phase_c._paired`);
  - paired Brier vs C-b and vs C-E2;
  - LOW recall per third.
- **Families are reported separately per candidate.** Whichever candidate is reported first, the reader is told that
  three candidates were tested.

## Adoption rule (as the master directive; all required)

- R3 and R7 pass at Leads 1 and 2.
- Algorithm 3 MRLT >= 2.
- Accuracy >= 0.75 at Leads 1 and 2.
- Brier not worse than C-E2 by more than 0.005 at either lead.
- The leakage checks pass (labels known at O(t) only; the calibration set precedes O(t)).
- **Plus team and adviser approval.**

**Failure:** any of the above not met. The candidate is then kept as experimental evidence. C-E2-NONEWS is never
adopted.

**Reported whatever the result.**
PLAN-SHA256: 2ab41820f61daf1a2107a3a5d5805e7d6101899cf3fbbd77d6fe4ded8ce809e9
