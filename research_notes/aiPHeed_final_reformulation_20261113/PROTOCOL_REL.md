# PROTOCOL_REL — national-relative reformulation of the FINAL forecasting task (written 2026-11-13 BEFORE any relative-target model is fitted or scored)

## Why (evidence already on file; no relative-target model has been fitted)
1. The FINAL label is absolute: HIGH = HFIAS moderate+severe >= 50 %. The 50 % cut is a project choice. FNRI's published scale applies to ANY-level
   insecurity (High = 60-79.9 %), and FNRI's provincial factsheets report each province against the national value (`*_sig_vs_ph`).
2. National HFIAS moderate+severe moves between rounds: 2015 53.8 (FNRI 2015 report), 2018 41.6, 2019 46.9 (ENNS factsheets, `ph_*`), 2021 41.0 (ENNS 2021 Table F.2).
   The absolute label therefore = (national level of the target round) + (province position relative to national). The national component is common to
   all provinces of a round, there are only 3-4 draws of it, and at the 2021 origin the latest released national (2019, 46.9) is 5.9 points above
   the 2021 value. The HIGH share swings 36 % / 52 % / 16 % (2018/2019/2021) with it.
3. FINAL's elapsed-time term learns the national decline; LG showed fixing it does not fix ranking; oracle thresholds fail. With 4 HIGH in 2021, the
   per-round targets pass by chance 27 % of the time for a FINAL-skill model.
4. Chapter I (as restated in the manuscript) does not define the target; the 50 % definition appears only in the implementation text.

## Reformulated target (evaluated ALONGSIDE the absolute target; not adopted without owner/adviser approval)
 HIGH_rel = province HFIAS mod+sev in the target round > national HFIAS mod+sev in the same round (published values above).
 Continuous form: z = logit(p_prov) - logit(p_nat). Label sensitivity: rows with |p_prov - p_nat| <= 1.96 x SE_prov reported separately.
 NNS 2013 national mod+sev is not published: estimated as 56.05 % (78 common provinces; 2013 mean logit shifted by the 2015 province-mean minus national
 offset). It enters only training anchors. Sensitivity: 2013 national := 53.8 %.

## Candidates (Lead 1, same folds and cached tables as FINAL, origin rules unchanged)
 REL-P    relative persistence: z_hat = z_anchor; P = Phi(z_hat / s), s from training residuals by gap (A4.scale, as the engine).
 REL-HB   measurement-error-aware empirical-Bayes regression (non-ML): z_EB = region mean + lambda (z_anchor - region mean),
          lambda = tau2 / (tau2 + se_anchor^2), tau2 from the anchor round; z_T = a + b z_EB by weighted least squares on training rows; P as REL-P.
 REL-LGBM FINAL's engine unchanged (engine_final.fit_predict rate='lin', miss='mind', cw='balanced', 5 seeds) with y_true := y_true - logit(nat_T),
          q_true := Phi(y_rel / se_true) and anchors H := z_anchor, OH := z_EB, RSS := region mean z (inner CV picks one, training rows only).
          Hybrid: statistical relative anchor + LightGBM residual.
 Comparators: FINAL-as-REL (stored FINAL mu, sd = mu / Phi^-1(p); P_rel = Phi((mu - logit(nat_latest_released)) / sd)); REL-P; persistence; always-LOW.
 Absolute-label view: FINAL (as is) and REL-LGBM converted with P_abs = Phi((mu_rel + logit(nat_latest_released)) / sd).
 Anchors use only rounds released by the origin (2013, 2015) and their published (or estimated 2013) national values.

## Evaluation
 Every round separately + pooled: recall, precision, F1 (HIGH), BA, Brier, accuracy, ROC-AUC, PR-AUC; confusion matrices; 5 seeds; 2021-fold
 training-round drops (REL-LGBM seed 168, REL-HB); 2013-national sensitivity; paired province-cluster bootstrap (2000) of pooled Brier vs FINAL-as-REL
 and REL-P; Monte Carlo pass probability at the relative class counts.
 Evaluability rule (fixed now, from the absolute-target Monte Carlo): per-round count targets are binding only in rounds with >= 8 HIGH and >= 8 LOW;
 other rounds are reported with Clopper-Pearson CIs and are "not evaluable", never "passed".

## Decision rule (fixed now)
 REL-LGBM is the recommended reformulated candidate iff (a) all 8 targets pooled; (b) all 8 targets in every evaluable round for the 5-seed mean AND every
 seed; (c) pooled Brier <= FINAL-as-REL and <= REL-P; (d) 2018 and 2019 F1/BA not below FINAL-as-REL by more than 0.05.
 If REL-HB is within 0.005 pooled Brier of REL-LGBM and meets (a)-(b), the report must say LightGBM adds no measurable value over the statistical model.
 Any pass is retrospective (the province values were inspected many times; only the relative labels are new) and is NOT independent validation.
 Nothing enters the dashboard or production; no target change without owner/adviser approval. No arm, weight or threshold is added after scoring.
