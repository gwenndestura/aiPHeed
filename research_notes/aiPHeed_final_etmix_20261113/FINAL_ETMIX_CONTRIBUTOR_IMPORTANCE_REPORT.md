# FINAL-ETMIX: which forecasting contributors genuinely matter (Part 4)

## Method (`scripts/contrib_jobs.py`, `scripts/contrib_eval.py`)
- **Fits.** Every walk-forward fit of ETMIX was redone: 22 fold-leads × 5 seeds = 110 fits.
  - The model is unchanged. All 110 reproduce the stored fits: the same selected inputs in 110/110, and the ETMIX probabilities within 2e-16.
  - Each fit predicts under both elapsed-time hypotheses. All measures use the ETMIX probability ½(p_g + p_s), 5-seed mean, on **held-out test rows**.
- **Groups.** Inputs are grouped by what they measure (`group()`, identical in research and backend; tested). This is not the old dashboard design.

**The nine methods:**

| # | Method | What it measures |
|---|---|---|
| 1 | LightGBM gain / split / selection frequency | How much the fitted trees use an input (not predictive value) |
| 2 | Exact TreeSHAP (`pred_contrib` × elapsed time) | Additive attribution of each forecast; adds up exactly to (forecast logit − survey anchor) |
| 3 | Permutation within the test round (10 repeats) | Change in Brier / balanced accuracy / AUC when an input or group is shuffled across provinces |
| 4 | Individual input withholding | The input set to missing (MIND: training median + flag), fitted model unchanged |
| 5 | Group withholding | All inputs of a group missing at once |
| 6 | Retraining without the group | 3 rounds × 7 groups × 5 seeds = 105 refits at Lead 1; selection is redone, so correlated inputs can take over |
| 7 | Retraining without one input | 6 leading inputs × 3 rounds, seed 168 |
| 8 | Probability change and HIGH/LOW flips | Size of the change, separately from whether it helps |
| 9 | Consistency | By lead, by survey round, by province (`C4`), and correlation among inputs (`C8`) |

**Caveats.**
- Performance changes use the 72 reused province-rounds: descriptive evidence, not independent.
- No feature was selected for the model from these results.
- Attribution is **not** causation.

## 1. Group results (Lead 1 unless stated)

| Group | Lead-1 attribution share (TreeSHAP) | Gain share | Withhold: flips of 532 | Permute: ΔBrier L1 [CI] (rounds up) | Retrain without: ΔBA / ΔBrier [CI] | Classification |
|---|---|---|---|---|---|---|
| **Regional economy** (GRDP pc relative to national; household income) | **41.7 %** (2018 42 %, 2019 42 %, **2021 0 %**) | 0.46 | **85** | **+0.019** [−0.005, +0.039] (2/3) | **−0.117 / +0.029 [+0.003, +0.054]**; 15 flips | **Core** |
| **Food prices and inflation** (CPI food relative to national, food/rice inflation, farmgate) | 27.8 % (2021: 41 %) | 0.19 | 28 | +0.002 (1/3) | −0.032 / +0.011 [−0.003, +0.026]; 7 flips | Supporting |
| **Poverty and social vulnerability** (poverty incidence, subsistence incidence, density) | 26.0 % (2021: 0 %) | 0.23 | 31 | +0.003 (1/3) | −0.031 / −0.002 [−0.013, +0.008]; 2 flips | Supporting |
| **Agriculture and fish production** (palay, agri output growth, fish prices) | 10.5 % | 0.07 | 17 | +0.001 (1/3) | −0.032 / **+0.011 [+0.003, +0.020]**; 3 flips | Supporting |
| Climate and typhoon exposure | 0.1 % | 0.01 | 2 | −0.000 (0/3) | −0.020 / −0.002; 1 flip | Supporting by rule (weak); **context on the dashboard** |
| News signals (NLP / FSSI) | 17.4 % overall, but 0.4 % in 2018–19 and **49 % in 2021** | 0.05 | 2 | +0.001 [+0.0004, +0.0018] (2/3) | **0.000 / +0.002**; 0 flips | **Redundant** |
| Employment | 0 % | 0 | 0 | 0 | 0 / 0; 0 flips | **Contextual** (never selected) |

Sources: `evidence/C1_group_withhold_permute.csv`, `C3_shap_group_shares.csv`, `C6_retrain_without_group_L1.csv`, `contributor_registry.json`.

**Classification rules,** fixed in `contrib_eval.py` before it was first run:
- **Core:** retraining loss (ΔBA ≤ −0.03 or ΔBrier ≥ +0.005), AND the permutation worsens Brier in ≥ 2 of 3 rounds, AND withholding flips ≥ 2 % of forecasts.
- **Redundant:** withholding or permuting matters, but retraining without the group changes nothing.
- **Contextual:** no measurable effect at all.
- **Supporting:** everything in between.

## 2. Individual inputs

| Input | Group | Geography (empirical) | Selected (of 110 fits) | Gain share | Withhold flips / permute ΔBrier L1 | Retrain without it (L1) | Verdict |
|---|---|---|---|---|---|---|---|
| `hh_grdp_rel`: log regional GRDP per capita relative to the national mean | Regional economy | **REGIONAL** | 100 | **0.43** | 83 / +0.024 | **ΔBA −0.106, ΔBrier +0.025, 14 flips** | **Core.** The single most important input |
| `income_rel`: regional household income relative | Regional economy | REGIONAL | 32 | 0.02 | 4 / +0.002 | 0.000 / 0.000 | Redundant with `hh_grdp_rel` |
| `cpi_food_rel_nat`: provincial food CPI relative to national | Food prices | provincial | 110 | 0.10 | 18 / +0.000 | ΔBA −0.031, ΔBrier −0.003 | Supporting (unconstrained sign) |
| `cpi_food_yoy`, `cpi_food_3m`, `cpi_rice_yoy`, `cpi_since` | Food prices | provincial | 30–174 | ≤ 0.02 each | ≤ 3 / ≈ 0 | — | Supporting as a group; individually minor |
| `l_fg_rel`, `l_fg_yoy` (farmgate palay) | Food prices | provincial (20 % missing) | 90 / 42 | 0.02 / 0.01 | ≤ 5 / +0.001–0.002 | — | Minor |
| `l_rice_rel`, `l_terms` | Food prices | provincial (35–43 % missing) | 110 / 10 | ≈ 0 | 0 | 0 (`l_rice_rel`) | Unsupported |
| `p_poverty`, `p_subsistence` (ρ = 0.94 with each other) | Poverty | provincial | 164 / 116 | 0.08 / 0.07 | 7–17 / ≈ 0 | ΔBA −0.020 (`p_poverty`) | Supporting; the two share importance |
| `p_density` | Poverty | provincial | 100 | 0.08 | 11 / +0.001 | — | Supporting |
| `c_agri_yoy`, `ag_palay_yoy`, `agri_since`, `ag_dev3y` | Agriculture | provincial | 30–80 | 0.01–0.02 | 2–9 / ≈ +0.001 | 0.000 (`c_agri_yoy`: others substitute) | Supporting as a group; no single input essential |
| `l_fish_yoy` | Agriculture/fish | provincial (79 % missing) | 10 | ≈ 0 | 0 / +0.0006 | — | Unsupported |
| `a_e_market`, `a_e_hunger`, `a_e_employment`, `a_net_since`, `n_net_since` | News | REGIONAL / NATIONAL | 10–26 | ≤ 0.02 | up to 32 flips (2021 folds) | Group: 0.000 | Redundant: the model substitutes market and agriculture inputs |
| `vu_tc_wind`, `vu_tc_strong`, `vu_tc_clim`, `c_tc_4q`, `vu_rain12`, `oni` | Climate | provincial (`oni` national) | 20–110 | ≤ 0.01 | ≤ 1 / 0 | — | Unsupported as predictors |
| `unemp_rate`, `unemp_yoy`, `unemp_chg_since` | Employment | NATIONAL | 0 | 0 | — | — | Unsupported; never selected |
| `unemp_region` | Employment | absent in training rows | — | — | — | — | Excluded (not available) |
| `c_fish_yoy`, OFW remittances | — | — | dropped by design | — | — | — | Excluded |

Sources: `evidence/C2_input_withhold_permute.csv`, `C5_input_importance.csv`, `C7_retrain_without_input_L1_seed168.csv`, `C9_input_inventory_etmix.csv`.

## 3. Answers to the brief's questions (groups)

| Question | Regional economy | Food prices | Poverty | Agri/fish | Climate | News | Employment |
|---|---|---|---|---|---|---|---|
| Improves forecasting (retraining loss)? | **Yes**: Brier CI excludes 0 | Probably (BA −0.03; Brier CI includes 0) | Mixed (BA −0.03; Brier unchanged) | **Yes**: Brier CI excludes 0 | No | No | No |
| Improves HIGH identification? | Precision −0.23 without it; recall unchanged | Precision −0.08 | Recall −0.04 | Precision −0.08 | Recall −0.04 (1 row) | No | No |
| Consistent across rounds? | 2018 and 2019 (ΔBA −0.29, −0.13); **not selected in 2021 Lead-1 fits** | 2018 and 2021 | 2019 only | 2018 only | No | Only 2021 attribution | — |
| Province-specific? | Between-region only (identical within a region) | Province-varying | Province-varying | Province-varying | — | — | — |
| Redundant? | `income_rel` redundant with `hh_grdp_rel` | Partly substitutable | `p_poverty` ~ `p_subsistence` | Inputs substitute for each other | — | **Yes** | — |
| Available at the origin? | Yes (latest published year by the origin; release lag applied) | Yes | Yes (latest PSA release) | Yes | Yes | Yes | Yes (national) |
| Geographic resolution appropriate? | **No: regional, not provincial.** Must be labelled | Yes | Yes | Yes | Yes | Mostly regional / national fallback | National: no |
| Explainable to DA evaluators? | Yes, as "the regional economy is weaker or stronger than the national average" | Yes | Yes | Yes | Yes | Yes | Yes |

## 4. Regional versus provincial contributors
- **`hh_grdp_rel`, `income_rel`, `hh_grdp_g`, `income_growth` are REGIONAL.** They hold the same value for all five CALABARZON provinces.
  - They help the forecast by separating **regions**: poorer regions' provinces were HIGH more often.
  - They do **not** separate provinces within a region. In CALABARZON, the regional-economy contribution is identical for Batangas, Cavite, Laguna, Quezon and Rizal.
  - It must never be presented as a provincial measurement.
- **Area-level news (`a_e_*`) is regional; national news (`n_*`), `oni` and unemployment are national.**
- **Provincial differentiation within CALABARZON** comes from food prices (provincial CPI), poverty / subsistence / density, and agriculture inputs, plus the survey anchor itself.

## 5. Directions: when "raises / lowers risk" is supported
- **Inputs with a fixed monotone constraint:** the sign of their contribution is guaranteed by construction. For these, "raises" or "lowers" the forecast is a faithful description of the model.
  - Lowering risk when higher: regional GRDP (−); agriculture output growth (−).
  - Raising risk when higher: poverty / subsistence (+); food inflation (+).
- **`cpi_food_rel_nat`, `p_density`, `l_fg_*`, `income_rel` are unconstrained.** Their direction is learned and can vary across fits. Shown as "the model estimated it raised / lowered this forecast", not as a rule.
- **Across Lead-1 rows:** regional economy contributes on average +0.108 logit in HIGH rows and −0.090 in LOW rows; poverty +0.046 versus −0.018. Food prices and agriculture do not separate HIGH from LOW on average. Their value is in the within-round adjustments the ablations detect.
- **None of this is causal.**

## 6. Stability across training periods (important caveat)
- `hh_grdp_rel` and the poverty inputs are selected in every fit of the 2018 and 2019 folds and in the 2021 Lead-3–8 fits. They are selected in **none** of the 2021 Lead-1/2 fits, and in none of the live 2026-Q4 fits (both trained with the 2019 and 2021 transitions).
- In those fits, food prices, agriculture and, for attribution only, news carry the forecast.
- The "core" status of the regional economy is therefore real in the walk-forward evidence, but not guaranteed for every future fit.
- The dashboard must show each forecast's **own** contributions and say when a group was not used. The backend does this (`used_by_this_issue`).

## 7. Summary
- **Genuinely contributing individual input:** `hh_grdp_rel` (regional). Food CPI relative to national, poverty / subsistence incidence, density and agricultural output growth contribute as groups.
- **Groups with meaningful predictive information:**
  - Regional economy (core);
  - Food prices, Agriculture & fish, Poverty & social vulnerability (supporting).
- **Redundant:** news / NLP; `income_rel`; individual agriculture inputs.
- **Contextual / unsupported:** climate, employment.
- **Excluded:** fish-production growth and remittances (dropped by design); `unemp_region` (not available).
