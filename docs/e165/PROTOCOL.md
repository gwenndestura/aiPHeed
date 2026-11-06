# E165 protocol: AUTO + shrink-only score calibration (one locked run)

- **Written:** 2026-11-06, before the E165 code was written and before any E165 result existed.
- **Lock:** this file and `backend/app/e165/calib.py` are committed to git before the run. `eval` refuses to run if either has uncommitted changes, and refuses a second run.

## Why
- E164 AUTO is correct on 57 of 72 Lead-1 rows (79.2 %) and fails only E156 criterion **C4**.
- C4 is measured on the **score**: `y_true` regressed on `mu_AUTO`, logit scale, region bootstrap (`Pv.scale_test`). It requires the 95 % slope interval to include 1. AUTO's slope is 0.73 [0.51, 0.88]: the scores are too spread.
- Recalibrating P(HIGH) alone cannot change C4. The score itself must be shrunk.

## Disclosed before the run
1. **This design was chosen after seeing AUTO's slope and reliability table** (E164 report). The 72 rows have been read by E151 to E164. The result is retrospective.
2. **The shrink-only form is chosen because it cannot change any HIGH/LOW class.** `mu' = b·mu` with `b > 0` keeps every sign, so the HIGH line, every class, accuracy, precision, recall, F1, AUC and C1, C3, C5 and C6 are unchanged by construction. Only the score, P(HIGH), the 90 % range, Brier (C2) and C4 can change.
3. **Expected weakness:** at the 2018 and 2019 issues, training holds one round (FNRI2015), so `b` can only come from region folds, which cannot see drift between rounds. `b` may stay near 1 there, and C4 may still fail.
4. The calibration intercept (overall upward bias, about +2.8 points) is **not** corrected, because an intercept would move the HIGH line. It is reported.

## Method (fixed)
AUTO is run exactly as in E164 (`app.e164.auto`: same menu, inner region GroupKFold, selection and probability rule). Then, for each outer issue (survey × lead), using **training rows only**:

1. **Temporal estimate**, if training holds two or more survey rounds. For each training round r after the earliest:
   - run the whole AUTO procedure on the training rows of earlier rounds only;
   - forecast the rows of round r.

   Pool these out-of-time forecasts. `b_raw` is the slope of `y_true` on the forecast score (weighted least squares with intercept, weights `1/(se² + 0.05)`).
2. **Otherwise**, `b_raw` is the same slope fitted on the inner out-of-fold scores of AUTO's selected configuration.
3. `b = clip(b_raw, 0.25, 1.0)`.
   - Never stretched (b ≤ 1).
   - Never below 0.25.
   - If `b_raw` cannot be computed, b = 1.
4. `mu_CAL = b · mu_AUTO`.
5. sd and the 90 % range come from `app.e164.auto.scale` on the training errors `y − b · oof`. Then `P(HIGH) = Φ(mu_CAL / sd)`.

The same rule is used for the live 2027-Q1 forecast, with all released rounds as training.

## Checks, reported whatever the result
- **Reproduction:** E165's recomputed `mu_AUTO` must equal E164's committed `mu_AUTO` (max abs difference < 1e-6). Otherwise the run is **void**.
- **Class identity:** `(mu_CAL ≥ 0) == (mu_AUTO ≥ 0)` on every row.
- **Reported:** b and its source for every issue.

## Decision rule (fixed now)
- **Reliability:** E156 criteria C1–C6, computed with the unchanged code (`app.e156.leads.evaluate`) on Leads 1–4.
- **If CAL's maximum reliable lead ≥ 1:** AUTO-CAL replaces AUTO as the **release candidate**, and its 2027-Q1 forecast is sealed. It is not deployed until the sealed forecast is scored, as for E164.
- **Otherwise:** AUTO stays as the release candidate, E158 stays as the thesis model, and the thesis reports that shrink-only calibration was tested once and did not pass C4.

## Always reported
- All Lead 1–4 metrics and C1–C6 for CAL and for AUTO.
- Brier of CAL minus AUTO, E158 and persistence, with 95 % intervals.
- Calibration slope and mean error.
- The Lead-1 reliability table.
- 90 % range coverage.

## Not allowed after the lock
Changing the b rule, the clip bounds or the procedure; adding an intercept; dropping rows, rounds or leads; re-running.
