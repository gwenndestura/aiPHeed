# Lead 2 experiment log

**Earlier experiments.** Entries 1-20 are the earlier frozen experiments, unchanged. Full rows are in `../LEAD2_FIVE_TRIGGER/out/lead2_experiment_log.csv`. Entries 21 onward are from `PROTOCOL_LEAD2_FINAL_SIGNAL.md`, frozen in 6c6ab71 before any fit.

**Fixed settings.** Seed 2027 for LightGBM and 2031 for bootstraps. Base cut-off features only. Development (DEV) = targets ≤ 2024-Q4; confirmation (CONF) = later targets. Input hashes are in `out/study.json` (`input_sha256`).

| # | Experiment | Hypothesis | Change | Selection data | Result | Status |
|---|---|---|---|---|---|---|
| 1-4 | IMPROVE B1-B4 | biased flat projection; regime; trigger dynamics | anchored projection, recency weights, trigger changes | DEV | no DEV gain (0.177-0.192 vs 0.177) | rejected |
| 5-6 | CANDIDATES C2-C5 | price-condition persistence; composition | lagged labels, excess changes | DEV | worse | rejected |
| 7 | TUNING G0, N0-N2 | configuration limits | grid / forms | inner folds | G0 DEV gain, fails adoption | rejected |
| 8-9 | FINAL K1/K2, SUBGROUP | price composition, subgroups | K_core, K_fresh_gap, K_diff | DEV | L1 worse, FA > hits | rejected |
| 10-12 | COMBINATION, CAUSES, POVERTY_V3 | formula restriction; rainfall; poverty | screens | DEV | no candidate / B0 kept | rejected |
| 13-16 | THRESHOLD, CR, CR-CAL, CR-ANC/T/WCAL | decision cut; fresher CPI; calibration | refresh / thresholds / Platt | DEV | CR-ANC passes R1-R7 on unverified timing; adoption fails | rejected (timing unverified) |
| 17 | ASOF_REEVAL | refresh gain depends on timing | verified-ledger cut-offs | DEV | CR-VER passes the DEV rule but reverses in CONF | rejected |
| 18 | ROOTCAUSE_II ceiling | price unpredictable from projection | Gaussian reference | pre-eval | oracle recall 0.47 | diagnostic |
| 19-20 | BIAS_TRACK X1, X1-VER | regime-drifting projection bias | recent projection error | DEV | worse in DEV | rejected |
| 21 | Price-method study M0-M6 | is the price series predictable at Lead 2? | 8 issue-time methods with own-error probabilities | DEV folds; CONF reported | crossing 48%; lag-3 autocorrelation 0.05; best DEV price Brier 0.17-0.19 (M4, M0) vs climatology 0.29; LightGBM 0.273; nothing holds in CONF on T43c | diagnostic |
| 22 | K-A recent margins | binary lags drop magnitude | B0 + LM_f, LM_g, SM_f, SM_g | gate: M1 or M3 < M0 on DEV price Brier | 0.251 / 0.387 vs 0.188 | **not fitted** (gate failed) |
| 23 | K-B ridge forecast as input | continuous forecast summarizes prices | B0 + RF_f, RF_g | gate: M5 < M0 and M6 | M5 has no DEV forecasts (first fit 2023-Q3; σ needs 6 errors) | **not fitted** (gate failed) |
| 24 | K-E news availability | N1 missingness informative | B0 + N1_articles | gate: DEV coverage ≥ 30% and not calendar-driven | N1 is NaN exactly when < 5 admitted headlines (100%). DEV coverage 5.7%; coverage by origin year 0 / 5 / 10 / 35 / 20 / 40%. Calendar-driven collection, not processing failure. | **not fitted** (gate failed) |
| 25 | S-EARLY on B0 | 600 training rows use thresholds not yet computable, and 375 use the pre-public 2018=100 series | drop training rows issued before 2023-01-06 | DEV / CONF | **No DEV origin remains eligible: DEV cannot be evaluated without those rows.** CONF L2 Brier 0.169 vs 0.156; L1 0.124 vs 0.123 | sensitivity: B0's DEV result depends on point-in-time-compromised training rows |
| 26 | S-LAG on B0 | the lags of A3, C3, C4, E1, E2 are assumed | shift them one more quarter | DEV / CONF | L2 DEV 0.189 vs 0.177, recall 0.09 vs 0.45 (1 vs 5 of 11 DEV HIGH rows); L2 CONF 0.161 vs 0.156; L1 DEV 0.138 vs 0.139 | sensitivity: B0's Lead-2 DEV result is sensitive to the unverified lags |
| 27 | Five-group ablation on B0 (no candidate selected) | which groups add out-of-sample value | refit without each group | DEV / CONF with Holm | Market adds value in CONF (L2 +0.074 [+0.040, +0.107]) but not in DEV (+0.005 [−0.025, +0.033]). News is possible noise in L2 DEV (−0.011). Others not established. | contribution report |

**No candidate was selected.** The post-selection audit on the 65 rows (§6) was therefore not run, and nothing was fitted or compared on those rows to choose a model.
