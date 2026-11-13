# PROTOCOL_INPUTS — official-indicator and feature-set study for FINAL (written 2026-11-13 BEFORE any arm below is fitted or scored)

## Question
Do PSA official poverty statistics, PSA population/density, PSA regional accounts (GRDP) and NOAA ONI add predictive information to
FINAL, alone or together, and does any defensible change to FINAL's input set improve it under FINAL's own evaluation protocol?

## Fixed elements (unchanged from FINAL, FINAL_FROZEN_CONFIG.json)
- Engine: research `engine_final.fit_predict(tr, te, AN, seed, rate="lin", miss="mind", cw="balanced")` (= app.hcw.final_engine).
- Folds: `run_qs.load(survey, lead)` for ENNS2018, ENNS2019, ENNS2021 (forward-chained; training rounds released before the origin only).
- Leads 1 and 2 (the served leads). Seeds 168, 1, 2, 3, 4; seed aggregation = mean probability. Threshold 0.50. Target, labels and
  evaluation rows unchanged (HFIAS moderate+severe >= 50 %, provincial). No synthetic data. No hard-coded rounds, provinces or labels.
- Every choice inside a fold (anchor, input set, hyper-parameters, calibration, input selection) is made on that fold's training rows only.

## Arms
 B0      FINAL reproduction (must match the stored FINAL fold predictions, ETMIX_rows_all_leads.csv column FINAL, |dp| <= 1e-6).
 D-ALL   B0 without the seven official columns (p_poverty, p_subsistence, p_poverty_gap, p_density, hh_grdp_g, hh_grdp_rel, oni) and their
         missing flags.
 D-POV   B0 without p_poverty, p_subsistence, p_poverty_gap (+ flags).
 D-DEN   B0 without p_density (+ flag).
 D-GRDP  B0 without hh_grdp_g, hh_grdp_rel (+ flags).
 D-ONI   B0 without oni.
 F-ALL   B0 with the seven official columns always kept (they bypass the 25-input rank filter; pruning and monotone signs unchanged).
 N-OFF   B0 + corrected / extended official inputs added to the candidate pool (selected or not by the unchanged rank filter):
           p_density_c  log(population / land area) from the latest census RELEASED at the issue date (2010, 2015, 2020, 2024; census C
                        usable from 1 January of C+2, the E137 rule). Replaces p_density, which reads 2010/2015 only.
           p_popgrowth  annual population growth between the two latest released censuses (PSA published growth rates).
           oni_12m      mean of the 12 latest ONI seasons available at the issue date (season end + 10 days).
           oni_max12    maximum of those 12 seasons (El Nino peak).
           nino_m12     number of those 12 seasons with ONI >= +0.5 (El Nino duration).
           nina_m12     number of those 12 seasons with ONI <= -0.5 (La Nina duration).
           oni_lag2q    latest ONI available 6 months before the issue date (lagged ENSO exposure).
         Monotone signs: oni_12m, oni_max12, nino_m12, oni_lag2q +1 (El Nino -> drought -> lower harvest / higher prices); nina_m12 0;
         p_density_c 0 (as p_density); p_popgrowth 0.
 N-OFF-F N-OFF with all official columns (poverty x3, p_density_c, p_popgrowth, hh_grdp_g, hh_grdp_rel, the five ONI columns) forced in.

## Evaluation (every arm, each lead; seed mean and each seed)
 Per round and pooled: confusion matrix (TP/FP/FN/TN), accuracy, HIGH precision/recall/F1, LOW precision/recall, ROC-AUC, Brier, log loss,
 prediction distribution (share predicted HIGH). Incremental value of each official group = paired difference vs B0 (Brier, log loss) with
 a 3000-draw paired bootstrap 95 % CI over province-rounds.

## Decision rule (fixed now)
 An arm REPLACES FINAL only if ALL hold at Lead 1 and Lead 2 for the 5-seed mean:
  (1) pooled owner metrics pass: accuracy, precision, recall, F1 >= 0.75 and AUC >= 0.75;
  (2) pooled Brier <= B0 + 0.005;
  (3) in no round is HIGH recall below B0's, and in at least one round HIGH F1 is higher than B0's;
  (4) among arms meeting (1)-(3), it has the lowest log loss on the 2018 + 2019 folds (released before the 2021 origin); 2021 selects nothing.
 Otherwise FINAL's input set is kept unchanged. An official group is reported as "predictive" only if dropping it (D-*) worsens pooled
 Lead-1 Brier with a bootstrap 95 % CI entirely above 0; "contextual" if it is selected but its removal has no significant effect.
 Results on 2018/2019/2021 are retrospective historical tests (outcomes viewed before), not independent validation.
 Owner rule (all five metrics in EVERY round) is reported for every arm; FINAL itself does not meet it (2021).
