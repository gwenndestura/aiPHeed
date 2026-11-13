# FINAL model completion: official indicators, feature set and integration (2026-11-13)

Branch `aiPHeed/final-model-completion-20261113`. Study folder `research_notes/aiPHeed_final_inputs_20261113/`.
Protocol `PROTOCOL_INPUTS.md` (sha `4cb830c6`) and addendum 1 (sha `56e6c928`) were locked before any arm was fitted.

**Verdict.**
- No input change beats FINAL under the locked rule, so FINAL's procedure and input set stay unchanged.
- Of the four official groups, only PSA regional accounts (GRDP) carry measurable predictive information.
  - Poverty and density are context only.
  - ONI has no effect.
  - The new agriculture-sector GRDP series makes forecasts significantly worse.
- FINAL is **not** switched into production. It still fails the owner's rule in 2018 and 2021, and the user's brief forbids deploying an unvalidated model.
- The landing page no longer shows any model inputs.

---

## 1. Initial FINAL architecture and actual inputs

**Procedure** (`app/hcw/final_engine.py`; `FINAL_FROZEN_CONFIG.json`, seal `80b20aed`):
- The forecast starts from a survey anchor. The candidates are H, OH and RSS; inner CV picks one.
- LightGBM forecasts the change per quarter of gap (RATE).
- MIND fills missing values with the training median and adds a 0/1 flag for each gappy input.
- Each fit keeps the **25 inputs with the largest |Spearman ρ| with the training residual**, then prunes near-duplicates (ρ > 0.95).
- Other settings:
  - Monotone signs on inputs.
  - Inner GroupKFold by region over 16 hyper-parameter settings.
  - Balanced class weights.
  - Five seeds, averaged.
  - Threshold 0.50.

**Candidate pool.** 102 valid columns, from the GOV/FULL/+cons sets of `app/e168/lgbm_only.py` plus `app/hcw/engine.py` NEW_GROUPS. The seven official columns are all in it:
- `p_poverty`, `p_subsistence`, `p_poverty_gap`, `p_density` (`app/e150/model.py` GROUPS["poverty"])
- `hh_grdp_g`, `hh_grdp_rel` (NEW_GROUPS["rp_hhecon"])
- `oni` (GROUPS["climate"])

**Inputs FINAL actually uses for the current 2027-Q1/Q2 forecasts.**
- Logged from the live refit, `build_corrected._one` with `AIPHEED_LIVE_ASOF=2026-11-01`.
- The 7 fits logged so far, Lead 1 (5 seeds) and Lead 2 (2 seeds), all select the same 23 inputs (`evidence/live_selected_inputs.json`).

`a_e_hunger, a_net_since, ag_dev3y, ag_palay_yoy, cpi_food_3m, cpi_food_rel_nat, cpi_food_yoy, cpi_since, gap_q, l_fish_yoy, l_rice_rel,
mi_ag_pc, mi_cpi_food_accel, mi_l_fg_rel, mi_l_fg_yoy, mi_r_e_net, n_e_hunger, n_e_market, n_e_net, n_net_since, soil_since, unemp_rate, vu_tc_clim`

None of the seven official columns is in that set.

## 2. Why poverty, density, GRDP and ONI were not used

Each of the brief's ten possible causes, checked against the repository:

| # | Possible cause | Finding (evidence) |
|---|---|---|
| 1 | Never collected | **No.** Poverty, subsistence and poverty gap: `backend/data/hfias/raw/psa/poverty_1991_2015.csv` and `subsistence_1991_2015.csv` (2012, 2015), plus `data/e137/raw/y2023/psa/*` and `data/e138/raw/psa/*` (2018, 2021, 2023). Census: `data/e137/raw/psa/population_2010_2024.csv`. GRDP: `data/e154/raw/regional_income_long.csv`. ONI: `data/fi5/raw/noaa/noaa_oni.txt` plus the live file. |
| 2 | Not connected to the model | **No.** All seven are in FINAL's candidate pool (above). |
| 3 | Removed in preprocessing | **No.** Coverage in the training folds is 92–100 % (GRDP 92 %, density 96 %, poverty 99 %, ONI 100 %). |
| 4 | Excluded by feature selection | **YES, this is the cause for the live forecasts.** The 25-input rank screen (`engine.py` `Model._select`) places them 36th (`hh_grdp_rel`, \|ρ\| 0.079), 44th (`oni`, 0.066), 55th–57th (poverty gap, poverty), 63rd (`hh_grdp_g`), 76th (`p_density`) and 90th (`p_subsistence`, 0.009) of 102. This is a single-variable screen, not a performance test. |
| 5 | Removed by missing-value handling | **No.** MIND keeps them and adds flags. The flags also rank low (`mi_p_density` 99th). |
| 6 | Resolution prevents alignment | **Partly, for ONI.** ONI is one global value per quarter. In the 2018 and 2019 training folds it takes **2 distinct values** (one round, two issue quarters), so it cannot explain differences between provinces or rounds. GRDP is regional: 16 distinct values per round, one per region. Poverty and density are provincial (60–121 distinct values). |
| 7 | Poor performance in earlier validation | **Mixed.** In the 110 earlier fold fits (`aiPHeed_final_official_20261113/evidence/IND_assessment.csv`), `hh_grdp_rel` was selected 100/110 times and was the largest contributor. Poverty and subsistence were selected 100/110, density 80/110, ONI 20/110. Permutation 95 % CIs all include 0. That study classed every one of them as "contextual". |
| 8 | Training and inference use different feature definitions | **No.** Both paths call the same `final_engine.fit_predict` with the same `H.feature_sets()` and column builders. The fold refit here reproduces FINAL's stored fold predictions to 1.1e-16. The live refit reproduces the sealed parts to ≤ 1e-6 (`build_official_shap.py` asserts this). The difference between the folds (they use GRDP) and live (it does not) is purely the screen. Live trains on 732 rows pooled over 2015–2021, where province-level *change* matters more than static levels. |
| 9 | Outdated feature schema | **Yes, for density.** `app/e137/features.py` `_census()` reads only the 2010 and 2015 censuses, although the file also holds the 2020 census and POPCEN 2024. Live forecasts therefore used 2015 density. The corrected version (`p_density_c`) correlates 0.999 with the old one, so the effect is negligible (arm N-OFF, §4). |
| 10 | Dashboard and backend on different model versions | **Yes.** The branch's `backend/data/registry/registry.json` sets production = **E168**. `final_engine.py` is marked `experimental … not approved for serving`. Production (aipheed.vercel.app) serves **E196**. FINAL appears only in the local preview dashboard. The branch landing page described E168's inputs (OFW remittances, fish production), which FINAL does not use. |

**Also found: data not reachable from version control.**
- `backend/data/e154/.gitignore` ignores `raw/`, so the GRDP-per-person series was not on the branch.
- The 2024–2025 GRDP files in `data/hcw/raw/` were untracked and existed only in the `aipheed_hcw` checkout.
- A clean checkout (for example, Render) could not rebuild FINAL's GRDP inputs. **Fixed:** these files are now committed (§15).
- The 2024–2025 GRDP-per-person values are **estimates** (`app/hcw/grdp_extend.py`), made from PSA total-GRDP growth and population trend. They are not PSA-published per-person figures.

## 3. Official datasets incorporated in this work

- **PSA regional accounts by industry, Agriculture, forestry and fishing (AFF), all 17 regions, 2000–2025.**
  - Fetched from PSA OpenSTAT (`DB/2B/GP/IN/<region>[_OS]`) by `backend/app/hcw/grdp_industry.py`.
  - Saved to `backend/data/hcw_official/raw/psa_grdp_aff_by_region.csv`, with provenance JSON (table ids and PSA update dates).
  - Two columns: real growth at constant 2018 prices, and share of GRDP at current prices.
  - Years up to 2023 come from the 2000–2023 series, the same series the model's GRDP-per-person input uses. 2024–2025 come from the current release.
- **Corrected census density and growth.**
  - Density now uses the latest census *released* at the issue date: 2010, 2015, 2020 or 2024, each usable from 1 January of census year + 2.
  - Population growth is the annual change between the two latest released censuses.
- **ONI exposures.**
  - 12-season mean, 12-season maximum, El Niño and La Niña duration (seasons at or beyond ±0.5), and a 6-month lag.
  - Each uses only seasons available at the issue date: season end + 10 days.

These were tested as candidates (§4). None was adopted, so production inputs are unchanged.

## 4. Indicators evaluated: evidence

**Setup.**
- FINAL's own folds: `run_qs.load` for ENNS2018, ENNS2019, ENNS2021, forward-chained.
- Leads 1 and 2, 5 seeds, 72 province-rounds per lead.
- 360 fits, 0 failures. Every choice inside a fold uses training rows only.
- Evidence: `evidence/INPUTS_metrics.csv`, `INPUTS_incremental_vs_B0.csv`, `INPUTS_selection_counts.csv`, `INPUTS_decision.csv`.

**Incremental value against FINAL (B0)**, measured as the pooled change in Brier when the group is removed (D-) or added (N-). Positive means worse than FINAL. Paired bootstrap 95 % CI, 3000 draws.

| Group | Arm | ΔBrier L1 [95 % CI] | ΔBrier L2 [95 % CI] | Effect on classification | Classification |
|---|---|---|---|---|---|
| All seven official columns | D-ALL | +0.003 [−0.017, 0.022] | +0.007 [−0.012, 0.024] | L1 pooled F1 80.0 → 76.9 %, fails owner metrics | jointly helpful, not significant |
| **PSA GRDP (regional)** | D-GRDP | **+0.029 [+0.004, +0.054]** | **+0.031 [+0.005, +0.057]** | False alarms 5 → 16; 2018 accuracy 86 → 50 % | **predictive: keep** |
| PSA poverty, subsistence, gap | D-POV | −0.003 [−0.013, 0.008] | +0.005 [−0.005, 0.015] | L1 slightly better without it, L2 slightly worse | contextual |
| PSA population density | D-DEN | −0.004 [−0.015, 0.008] | −0.005 [−0.016, 0.006] | No HIGH F1 gain at L1 | contextual |
| NOAA ONI | D-ONI | 0.000 [0.000, 0.000] | 0.000 | Never selected in any fold fit (0/30) | no effect |
| Seven columns forced in | F-ALL | +0.000 [−0.004, 0.004] | −0.001 [−0.007, 0.005] | L2: 2021 gains a false alarm, pooled precision 74 % | no gain |
| Corrected density, growth, ONI exposures | N-OFF | +0.001 [−0.002, 0.005] | −0.000 [−0.002, 0.002] | ONI features never pass the screen | no gain |
| Same, forced in | N-OFF-F | +0.001 [−0.004, 0.006] | +0.000 [−0.006, 0.006] | L2 pooled precision 74 % | no gain |
| **PSA AFF (regional)** | N-AFF | **+0.007 [+0.001, +0.012]** | **+0.006 [+0.001, +0.011]** | 2018 false alarms 3 → 6 | **harmful: excluded** |
| All new inputs | N-ALL | **+0.006 [+0.002, +0.011]** | **+0.005 [+0.002, +0.009]** | — | harmful |
| All new inputs, forced in | N-ALL-F | **+0.007 [+0.001, +0.014]** | +0.004 [−0.003, 0.010] | L1: 2021 HIGH found **2/4** (FINAL 1/4), but 2018 false alarms 3 → 6, pooled precision 72.4 % | rejected (precision, Brier) |

**Why the excluded indicators were excluded:**
- **ONI.** National series; 2 distinct values in the 2018/2019 training folds and up to 14 in the 2021 fold. It never passes the screen. Even forced in, with its rolling, peak, duration and lagged forms, it changes nothing measurable. ONI is used neither as a drought measurement nor as a model input. Provincial soil moisture, rainfall and typhoon inputs are the climate signal that does get selected (`soil_since`, `vu_tc_clim`).
- **Poverty, subsistence, gap and density.** Slow-moving provincial levels. FINAL forecasts the *change* from each province's own survey anchor, and that anchor already carries the province's level. Removing these inputs has no significant effect.
- **Families vs population poverty bases.** Families-based and population-based subsistence incidence have rank correlation **0.997** (83–87 provinces in 2018, 2021 and 2023). FINAL's pruning would drop either as a duplicate of the other. Poverty is "among population" throughout and subsistence "among families" throughout, so each series is consistent across eras.
- **Population growth.** Needs two released censuses, so it is missing for every 2015-round training row. It adds nothing.
- **AFF.** Significantly worse at both leads, mainly through 2018 false alarms. Excluded.

## 5. Final selected feature set

**Unchanged.** FINAL keeps its pool and its 25-input screen. For the current forecasts the screen picks the 23 inputs listed in §1.

GRDP is the one official group with significant out-of-sample value in the folds trained on 1–2 rounds, but the live fit on all rounds does not select it. Forcing GRDP (inside F-ALL) did not help the 2021 fold, which is the fold whose training most resembles live. The locked rule therefore gives no basis to change the live selection.

**This is a known limitation:** the current forecasts do not use the regional-economy input that mattered most in earlier rounds.

## 6. Feature importance and contribution

**Earlier work** (kept, not redone): exact TreeSHAP, permutation and withholding on 110 fold fits (`IND_assessment.csv`), and exact SHAP of the live forecasts (`aiPHeed_final_dashboard_preview_20261113/out_final/shap_official.csv`, additive to 1e-15).

**This study adds:**
- Group-removal and group-addition effects with bootstrap CIs (§4).
- Selection counts per arm (`INPUTS_selection_counts.csv`). In B0, `p_poverty`, `p_subsistence`, `p_density` and `hh_grdp_rel` are selected in 10/15 fold fits (the 2018 and 2019 folds); `oni` in 0/15.
- The live rank of every official column (§2, item 4).

## 7. Temporal and geographic alignment

The issue date is the first day of the issue quarter (quarter index i = 4 × year + quarter − 1). A value is used only if it was public before that date:

| Source | Frequency | Rule | Geography |
|---|---|---|---|
| PSA poverty, subsistence, gap | Rounds 2012, 2015, 2018, 2021, 2023 | Round R from 1 Jan of R+2 (conservative; PSA releases full-year provincial figures earlier). Last released value carried forward | Provincial |
| PSA census population / land area | 2010, 2015, 2020, 2024 | Census C from 1 Jan of C+2 | Provincial |
| PSA GRDP per person, AFF growth and share | Annual | Year Y from Q3 of Y+1 (`app/e154/model.py available_year`) | **Regional**: each province takes its region's value; no provincial GRDP is created |
| NOAA ONI | Monthly 3-month seasons | Season end + 10 days; 12-season window and 6-month lag counted back from the issue date | Global |

- No interpolation is used. Annual and census values are the last released observation, carried forward, which adds no future information.
- Training, validation and live inference all use the same builders and the same engine (§2, item 8).

## 8. LightGBM optimisation performed

- **This study:** input-set optimisation only (12 arms, §4). FINAL's engine, hyper-parameter grid, anchors, class weights, calibration and threshold are unchanged.
- **Already done on 11-13 and not repeated:** randomized hyper-parameter search, class-weight selection, training-chosen threshold, structural anchor and DROMIC displacement inputs (`aiPHeed_final_tuning_20261113`, `aiPHeed_final_dromic_20261113`). None improved FINAL.
- **No hard-coding.** No round, province, label or rule was hard-coded, and no synthetic data was used.

## 9. Primary metrics, every round (FINAL = B0; seed mean; threshold 0.50)

| Lead | Round | TP/FP/FN/TN | Accuracy | Precision (HIGH) | Recall (HIGH) | F1 (HIGH) | AUC | Brier | All 5 ≥ 75 %? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ENNS2018 | 8/3/0/11 | 86.4 % | 72.7 % | 100 % | 84.2 % | 0.964 | 0.130 | no (precision) |
| 1 | ENNS2019 | 11/2/2/10 | 84.0 % | 84.6 % | 84.6 % | 84.6 % | 0.853 | 0.151 | yes |
| 1 | ENNS2021 | 1/0/3/21 | 88.0 % | 100 % | 25.0 % | 40.0 % | 0.857 | 0.090 | **no** (recall, F1) |
| 1 | Pooled (72) | 20/5/5/42 | 86.1 % | 80.0 % | 80.0 % | 80.0 % | 0.898 | 0.123 | yes |
| 2 | ENNS2018 | 8/4/0/10 | 81.8 % | 66.7 % | 100 % | 80.0 % | 0.982 | 0.128 | no (precision) |
| 2 | ENNS2019 | 11/2/2/10 | 84.0 % | 84.6 % | 84.6 % | 84.6 % | 0.878 | 0.141 | yes |
| 2 | ENNS2021 | 1/0/3/21 | 88.0 % | 100 % | 25.0 % | 40.0 % | 0.881 | 0.100 | **no** |
| 2 | Pooled (72) | 20/6/5/41 | 84.7 % | 76.9 % | 80.0 % | 78.4 % | 0.899 | 0.123 | yes |

**LOW class, Lead 1 pooled:** precision 42/47 = 89.4 %, recall 42/47 = 89.4 %.

**Prediction distribution:** 25/72 (34.7 %) predicted HIGH at Lead 1; 25/72 rows are observed HIGH. The model does not predict LOW almost exclusively.

**Stability:** the 5 seeds are listed in `INPUTS_metrics.csv` (rows `seed_*`).

These are retrospective tests. The rounds were viewed many times during development, so this is not independent validation.

## 10. HIGH-risk detection

- **2018 and 2019:** 19 of 21 HIGH provinces found at Lead 1.
- **2021:** 1 of 4 found (25 %) by FINAL and by every one of the 12 input arms except N-ALL-F at Lead 1, which found 2 of 4.
  - N-ALL-F paid for it with 3 extra 2018 false alarms and significantly worse Brier, so it is rejected.
- **Earlier root cause** (`aiPHeed_final_official_20261113/06_HIGH_RISK_FALSE_NEGATIVES.md`): long-gap extrapolation from the 2015 anchor. No public input available at those origins identifies the 2021 shift.

## 11. Comparison with the previous FINAL and with production

- **Previous FINAL:** this FINAL is identical to the sealed version (B0 reproduces it to 1.1e-16).
- **Production E196**, same 72 Lead-1 forecasts:

  | Model | Accuracy | Precision | Recall | F1 | AUC | 2021 HIGH found |
  |---|---|---|---|---|---|---|
  | E196 | 81.9 % | 68.8 % | 88.0 % | 77.2 % | 0.901 | 2/4 |
  | FINAL | 86.1 % | 80.0 % | 80.0 % | 80.0 % | 0.898 | 1/4 |

- McNemar p = 0.58; Brier difference −0.023 [−0.052, 0.007]. **There is no significant difference.**
- E196 was chosen among 52 variants on these same rows, and it uses synthetic draws, which the owner now prohibits.

## 12. Training and production use the same feature schema

**Confirmed for FINAL:**
- Folds and live both call `app/hcw/final_engine.fit_predict` with `app/hcw/engine.feature_sets()`.
- The column builders are the same: `app/e147`, `app/e151`, `app/hcw/inputs.py`.
- Reproduction checks:
  - Folds: 1.1e-16 against the stored FINAL predictions.
  - Live: ≤ 1e-6 against the sealed parts.

The model *served* by the branch's registry is E168, not FINAL (§13).

## 13. Production integration status

**FINAL is NOT switched into production.**
- Production on the branch is E168; the deployed site serves E196.
- FINAL fails the owner's rule (all five metrics ≥ 75 % in every round) in 2018 and 2021.
- The brief says not to deploy an unvalidated model.
- The switch also needs owner and adviser sign-off, which is recorded as pending in `aiPHeed_final_official_20261113/01_MODEL_SELECTION_AND_RECOMMENDATION.md`.

**Done for integration readiness:**
- GRDP source data is committed, so a clean checkout can rebuild FINAL's inputs.
- The AFF fetcher and data are committed.
- The landing page is cleaned.

## 14. Landing page does not expose FINAL's inputs

**Confirmed.** Commit `bd9a128d` removed the following from `frontend/src/pages/Landing.tsx`:
- the Data sources table;
- the input list in "Forecast change";
- the trigger-group and news-model wording;
- the national-inputs and fish-production disclaimers.

**Guard test.** A new test in `frontend/src/test/landing.test.tsx` fails if a source table or any input name (remittance, fisheries, ONI, GRDP, CPI, LFS, NASA POWER, IBTrACS, XLM-RoBERTa, BERTopic, "Used now") appears. 21/21 landing tests pass; the type check is clean.

**Preview copy.** The same cleanup was applied to the untracked FINAL preview landing page (`C:\Users\admin\aipheed_final\research_notes\aiPHeed_final_dashboard_preview_20261113\frontend`) and checked in the browser.

## 15. Remaining limitations

- **No independent validation.** All results are retrospective; the next eligible FNRI provincial HFIAS round is the first true test.
- **2021 HIGH detection stays at 1 of 4.** No public input tested fixes it.
- **GRDP not used live.** The live selection does not use GRDP, even though GRDP is the only official group with significant out-of-sample value in earlier folds (§5).
- **Estimated GRDP years.** The 2024–2025 GRDP-per-person values are estimates; the 2024–2025 AFF values are PSA-published.
- **Partial live log.** 7 of 10 live fits were logged when this report was written; all 7 selected the same 23 inputs.

## 16. Files, branch, commits, artifacts

**Branch:** `aiPHeed/final-model-completion-20261113`. Commits `bd9a128d` (landing page) and `5e349aee` (AFF fetcher and protocol), plus the commit that adds this report and the evidence.

**Files:**
- `frontend/src/pages/Landing.tsx`, `frontend/src/test/landing.test.tsx`
- `backend/app/hcw/grdp_industry.py`; `backend/data/hcw_official/raw/psa_grdp_aff_by_region.csv` (+ provenance)
- `backend/data/e154/raw/regional_income_long.csv` (force-added; the folder is git-ignored); `backend/data/hcw/raw/psa/psa_grdp_by_region_2000_2023.csv`, `psa_grdp_by_region_2018_2025.csv`, `grdp_pc_2024_2025_estimated.csv` (+ provenance)
- `research_notes/aiPHeed_final_inputs_20261113/`: protocol and addendum (with hashes), `scripts/inputs_run.py`, `inputs_run2.py`, `inputs_eval.py`, `parts/` (360 fit outputs), `evidence/`, this report

**Model artifact:** unchanged FINAL. Engine `backend/app/hcw/final_engine.py`; config and seal in `research_notes/aiPHeed_final_official_20261113/evidence/FINAL_FROZEN_CONFIG.json` and `SEALED_FINAL_2027Q1_2028Q1.json` (seal `80b20aed`).

**Run:** from `aipheed_hcw/backend` (its `app/hcw` is byte-identical to the branch), with `PYTHONPATH=.`:
- `python inputs_run.py 18 1,2`
- `python inputs_run2.py 18 1,2`
- `python -I inputs_eval.py`
