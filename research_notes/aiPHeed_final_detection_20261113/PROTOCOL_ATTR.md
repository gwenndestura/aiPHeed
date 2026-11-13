# PROTOCOL_ATTR — structural-attractor ranking + FINAL-LG level (written 2026-11-13 BEFORE the 2021 province profiles are examined and BEFORE any ATTR model is fitted or scored)

## Evidence that defines the design (no 2021 information used for any choice)
- `evidence/TRANS_partial_correlations.csv`: per-transition partial Spearman correlations between each input and the change in
  national-relative position (dz), controlling for the starting relative position, meta-analysed over the three transitions that do not involve
  2021 (T1 2013->2015, n 78; T2 2015->2018, n 22; T3 2015->2019, n 25). Holm-significant and sign-consistent in T1-T3: income_rel (-),
  p_poverty (+), p_poverty_gap (+), hh_grdp_rel (-), a_e_employment (+), p_subsistence (+).
- Starting relative position regresses partway to the national value over a survey gap (slope 0.54 / 1.11 / 0.67 in T1-T3).
- Earlier evidence: FINAL and FINAL-LG rank 2021 no better than persistence (Spearman 0.67); FINAL-LG is the best LEVEL forecaster (bias -3.2 pp in 2021).
- Interpretation fixed now: provinces revert toward a STRUCTURAL level set by poverty/income, not toward a common mean; the absolute label =
  national level (best estimated by FINAL-LG) + relative position (to be estimated by the structural model).

## Structural set S (fixed now)
 S = {income_rel, p_poverty, p_poverty_gap, hh_grdp_rel, p_subsistence}: the Holm-confirmed inputs that measure economic condition.
 a_e_employment is excluded a priori: it is a news-coverage index, not a structural condition. Typhoon inputs are excluded: not confirmed in T1-T3.
 Values are as published at each row's issue quarter (as-of panels already in the fold tables). Missing values: training median of that fold.

## Arms (Lead 1; FINAL's folds and cached tables)
 ATTR     Bayesian linear regression (sklearn BayesianRidge, default hyper-priors, evidence-maximised) of z_T on [z_anchor, S] on the fold's
          released Lead-1 transitions only (2018 and 2019 folds: T1; 2021 fold: T1+T2+T3), weights 1/(se_T^2 + 0.05). Gives z_hat and predictive sd.
          Relative label: P = Phi(z_hat / sd). Equivalent to an error-correction model z_T - z_a = a + (b-1) z_a + c'S.
 HYB      (selected design) level from FINAL-LG, ranking from ATTR: mu_i = mean_j(mu_LG,j) + (z_hat_i - mean_j z_hat_j) over the provinces forecast
          at that origin; P_i = Phi(mu_i / sd_LG,i), sd_LG = mu_LG / Phi^-1(p_LG). Per FINAL-LG seed (5 seeds) and 5-seed mean.
 HYB-F    same with FINAL instead of FINAL-LG (checks the result is not LG-specific).
 ATTR-ABS diagnostic: P = Phi((z_hat + logit(latest released national)) / sd).
 Comparators: FINAL, FINAL-LG, persistence. Diagnostic only: HYB with the exact target-round national (oracle level) to separate ranking from level.

## Evaluation
 Absolute label (HIGH >= 50 %, unchanged) per round and pooled: recall, precision, F1, BA, Brier, accuracy, ROC-AUC, PR-AUC, confusion matrices;
 relative label for ATTR; seeds; 2021-fold training-transition drops (T1, T2, T3) for ATTR and HYB; within the seven 2021 provinces with 2015
 level >= 64 % the AUC (descriptive only); coefficient signs vs T1-T3; paired bootstrap of HYB - FINAL-LG (Brier, prevalence error).
 Leakage: S as-of the origin; training transitions released by the origin; test outcomes never read by the fit.

## Decision rule (fixed now)
 HYB is the recommended detection candidate iff ALL hold: (1) 2018 and 2019 all 8 targets and F1/BA not below FINAL-LG by more than 0.05;
 (2) pooled all 8 targets; (3) pooled Brier <= FINAL-LG + 0.005; (4) 2021 ROC-AUC > FINAL-LG's and 2021 F1 >= FINAL-LG's;
 (5) every LG seed gives the same 2021 TP/FP as the mean or better; (6) coefficient signs match T1-T3.
 2021 "4/4 with precision >= 0.70" is reported against the owner's targets but is not, by itself, evidence (4 positives; 2021 viewed ~40 times).
 Any pass is retrospective and is NOT independent validation; nothing enters the dashboard; FINAL and FINAL-LG are not modified.
 No arm, input or weight is added after scoring.
