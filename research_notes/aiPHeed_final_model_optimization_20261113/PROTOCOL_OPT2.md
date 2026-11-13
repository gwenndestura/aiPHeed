# PROTOCOL_OPT2 — survey-gap-aware training with genuine long-gap pairs (written 2026-11-13 BEFORE the arm is built, fitted or scored)

## Evidence that motivates it (already on file; no new scoring)
- PROTOCOL_OPT (sha bb05c253) scored 16 protocol arms plus 11 supplementary ones: every arm gives 2021 1/4 or 2/4 HIGH; DELTA/TRAJ/DELTA_TRAJ leave 2021 at 1/0/3/21.
- DELTA's change inputs were mostly missing (47-50 missing test values per fold), so it was a weak test; recorded as a construction defect, not rerun here.
- The documented 2021 cause is gap extrapolation: the 2021 test gap is 24 quarters; 2021-fold training gaps are 8 (2015 targets), 14 (2018), 16 (2019).
  The RATE term is fitted only on gaps <= 16, then multiplied by 24/g0.

## The one new arm
 LG (long-gap pairs). The 2021 fold's training table gets extra rows: every ENNS2018 and ENNS2019 province-lead row (leads 1-8, exactly as the
 Pipeline builds them) re-built with the FNRI2015 round withheld from the anchor, so the anchor is that province's NNS2013 round
 (gap about 22-26 quarters). Labels are the genuine 2018/2019 outcomes; inputs are the genuine panel values at each row's issue quarter.
 The hierarchical base for each pair row is fitted on the rounds released before that row's issue quarter, minus FNRI2015.
 All rounds used (NNS2013, FNRI2015, ENNS2018, ENNS2019) were released before the 2021 Lead-1 origin (6-quarter lag rule).
 Everything else is FINAL: engine_final.fit_predict(rate='lin', miss='mind', cw='balanced'), same input sets, grid, seeds 168/1/2/3/4, cut-off 0.50.
 2018 and 2019 folds: no long-gap pair is released before those origins (checked and logged), so LG = FINAL there by construction.

## Checks before scoring
 R1 Rebuilding the 2021 Lead-1 table WITHOUT pairs through the same script must reproduce the cached FINAL table (same rows, max abs diff of
    shared numeric columns <= 1e-9) and FINAL's seed-168 probabilities (<= 1e-6). Otherwise the arm is not scored.
 R2 Every pair row: anchor round = NNS2013, target round released before the 2021 origin, no 2021 outcome present.

## Decision rule (fixed now)
 LG replaces nothing unless it meets all 8 targets in each of 2018, 2019 and 2021 for the 5-seed mean AND for every single seed, and its pooled
 Brier beats persistence. Even then it is a retrospective pass on rounds already used ~30 times: it is sealed as a prospective challenger,
 not declared validated, and not put in the dashboard. If it fails, FINAL is kept and the failure is recorded.
 No other arm, weight or threshold is added after LG is scored.
