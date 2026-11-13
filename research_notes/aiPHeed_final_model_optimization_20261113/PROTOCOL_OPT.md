# PROTOCOL_OPT — structured model optimization across ENNS 2018/2019/2021 (written 2026-11-13 BEFORE any new arm is fitted or scored)

## Motivation (from evidence already on file, not from new scoring)
FINAL predicts the CHANGE since a province's last survey, yet most of its inputs are LEVELS (current poverty, current regional GRDP).
In 2021 it could not tell high-burden provinces that improved strongly from those that did not. A change target should be explained by
how conditions CHANGED since that survey and by the province's own earlier trajectory. These inputs were never offered to the model.

## New arms (same engine, seeds 168/1/2/3/4, same folds, Lead 1; cut-off 0.50; only the candidate inputs differ)
 N1 DELTA       adds change-since-anchor inputs: for c in {p_poverty, p_subsistence, p_poverty_gap, unemp_region, hh_grdp_rel, hh_grdp_g, ag_pc}
                d_c = (value as published at the forecast origin) - (value as published at the anchor survey's reference quarter).
                Both values come from the as-of panels (gov_panel, cand_panel), so both were public at the origin. No outcome is used.
 N2 TRAJ        adds the province's earlier measured trajectory: x_sv_prov_chg, x_sv_reg_chg, x_sv_nat_chg, x_sv_prov_dev_reg, x_sv_vol
                (changes between previously RELEASED rounds; already in the fold tables, built by the E-series pipeline).
 N3 DELTA+TRAJ  both.
 Inputs are added to all four candidate sets; FINAL's own 25-input selection, grid and RATE/MIND handling are unchanged.

## Architectures already fitted earlier (stored 5-seed predictions, tabulated per round here for the first time; not refitted)
 BASE (no RATE: gap as an ordinary input = H_cw), RATE (no MIND), RATE_SQRT (square-root time effect), IMPUTE, MIND, RIMP, DROPGAP, COMP,
 FINAL-ET, FINAL-SA, FINAL-ETMIX, FINAL-CF.

## Selection without using the evaluated round (rolling-origin model selection)
 SELECT: for the 2021 fold, the arm with the lowest log loss on the 2018 + 2019 Lead-1 out-of-sample forecasts (rounds released before the
 2021 origin) is used; 2018 and 2019 folds have no earlier out-of-sample round and use FINAL. SELECT is the only sequence that may be
 called a model chosen without 2021 outcomes.

## Acceptance (unchanged from the brief)
 All 8 targets in EACH of 2018, 2019, 2021 at Lead 1 (recall, F1, precision, BA >= .70; Brier <= .20; accuracy >= .75; ROC-AUC >= .70;
 PR-AUC > prevalence), pooled Brier better than persistence, every seed's pooled accuracy >= .75.
 Reported for every arm. An arm that passes only when picked AFTER seeing its 2021 result is labelled "retrospective pass, not selected
 blind" and may be sealed as a prospective challenger, but is NOT declared validated and NOT put in the dashboard.
 All arms and failures are recorded.
