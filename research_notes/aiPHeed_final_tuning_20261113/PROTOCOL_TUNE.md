# PROTOCOL_TUNE — training-only optimisation of FINAL-LG (written 2026-11-13 BEFORE any arm below is fitted or scored)

## Rules
- Base = FINAL-LG (FINAL engine + genuine long-gap pairs; 2018/2019 folds identical to FINAL). Lead 1. FINAL's folds and cached tables.
- Every tuning choice (hyperparameters, anchor, class weighting, calibration, decision threshold) is made INSIDE each fold's training data by the
  engine's region-grouped inner cross-validation. No 2018/2019/2021 test outcome enters any choice within a fold.
- Across arms, the only outcome-based choice is rolling-origin SELECT: for the 2021 fold, the arm with the lowest log loss on the 2018 + 2019
  out-of-sample forecasts (released before the 2021 origin); 2018/2019 folds use FINAL-LG. 2021 never selects anything.
- Seeds 168/1/2/3/4. No synthetic data. FINAL, FINAL-LG and their artifacts are not modified. Nothing is deployed.

## Arms
 A1 LG-WIDE    + 40-configuration randomized search (engine_opt.wide_grid, seed 20261112): num_leaves {3,5,7,15}, max_depth {-1,2,3,4},
               learning_rate {.01,.02,.05,.1}, n_estimators {100..700}, min_child_samples {5..40}, feature/bagging fraction, bagging_freq,
               L1 {0,.1,1,5}, L2 {1,5,20,50}, min_split_gain; chosen by inner-CV weighted SSE after the base grid (hpw=True).
 A2 LG-CW      class weighting none / sqrt / balanced: three fits; the one with the lowest INNER out-of-fold Brier is used (training only).
 A3 LG-THR     FINAL-LG with the engine's inner-OOF decision threshold (`thr`) instead of 0.50 (the cw=balanced fit of A2).
 A4 LG-SANC    + a structural-attractor anchor in the anchor menu: ATTR (PROTOCOL_ATTR, unchanged inputs) converted to the absolute scale
               (z_hat + logit(national value of the latest round released at the row's issue quarter)); training-row anchors cross-fitted
               (5-fold GroupKFold by region; ATTR trained on the other regions' Lead-1 non-pair rows); test rows from ATTR on all training rows.
               LightGBM still learns the residual; the inner CV chooses among H / OH / RSS / SANC.
 A5 LG-OPT     A4 + A1 search + A2 class-weight choice + A3 threshold: the fully training-optimised LightGBM.
 A6 LG-OPT-D   A5 + DROMIC features, ONLY if PROTOCOL_DRM confirms at least one (decided by that protocol, not here).
 Comparators: FINAL, FINAL-LG, ATTR-ABS/HYB (PROTOCOL_ATTR), persistence.

## Evaluation
 Absolute label (HFIAS mod+sev >= 50 %), every round + pooled: confusion matrix, HIGH recall/precision/F1, LOW recall/precision, BA, accuracy,
 Brier, ROC-AUC, PR-AUC, false positives, missed HIGH; at 0.50 and at each arm's own (training-chosen) threshold; per seed; 2021-fold
 training-round drops (FNRI2015 / ENNS2018 / ENNS2019) for A5 and FINAL-LG (seed 168); paired bootstrap vs FINAL-LG; chosen settings logged.

## Decision rule (fixed now)
 An arm is "better than FINAL-LG" only if ALL: (1) all 8 targets in 2018, 2019 and pooled, for the seed mean and every seed; (2) pooled Brier
 <= FINAL-LG + 0.005; (3) 2021: more HIGH found than FINAL-LG with no more than 2 false alarms, and F1 above FINAL-LG's; (4) SELECT picks it.
 Reported against the owner's 8 targets in every round. Results on 2018/2019/2021 are HISTORICAL TEST results (retrospective; the outcomes
 have been viewed many times) — not independent validation. A passing arm may be sealed for prospective validation only.
