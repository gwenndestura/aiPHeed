# 06 — Five dashboard contributor groups: validation for FINAL

Scripts: `scripts/contrib_final.py` and `scripts/direction_check.py`. Both re-score the existing 11-13 fits, keeping only FINAL's own probabilities (hypothesis g):
- 110 fold fits with exact TreeSHAP, withholding and permutation;
- 105 retrains without one group (Lead 1, 3 rounds, 5 seeds);
- 18 single-input retrains.

Every fit reproduces the stored FINAL probabilities to 2.2e-16.

Evidence:
- `evidence/CONTRIB_group_retrain_L1.csv`
- `CONTRIB_shap_group_shares.csv`
- `CONTRIB_input_importance.csv`
- `CONTRIB_single_input_retrain_L1.csv`
- `CONTRIB_direction_check.csv`

**Rule (PROTOCOL_REL):** a group genuinely improves out-of-sample forecasting only if retraining without it raises the pooled Lead-1 Brier score, with a 95 % CI above 0.

## 1. The five dashboard groups

| Dashboard group | FINAL inputs | SHAP share at Lead 1 (2018 / 2019 / 2021) | Retrain without it: ΔBrier at L1 [95 % CI] | ΔBA | Flips | Direction plausible? | Verdict |
|---|---|---|---|---|---|---|---|
| 1 Market and prices | `cpi_food_rel_nat` (110/110 fits), `cpi_food_3m`, `cpi_food_yoy`, `cpi_rice_yoy`, `cpi_since`, `l_fg_*`, `l_terms` | 0.278 (0.20 / 0.22 / 0.41) | +0.011 [−0.004, +0.026] | −0.012 | 4 | Mostly yes: higher food CPI relative to the nation → higher risk (ρ +0.80). The farmgate-price inputs `l_fg_rel` and `l_fg_yoy` run the other way (higher farm prices → lower risk), which has no fixed prior | **Not established.** Large share, and the effect points the right way, but out-of-sample gain is not significant |
| 2 Climate stress | `vu_rain12`, `vu_tc_wind`, `vu_tc_strong`, `vu_tc_clim` (20–32 of 110 fits) | 0.001 | −0.002 [−0.012, +0.006] | −0.020 | 1 | No prior direction is defensible for exposure inputs | **No effect.** Showing climate contributions is unsupported |
| 3 Employment | `unemp_rate` (rarely selected) | ≈ 0 | −0.000 [−0.000, −0.000] | 0.000 | 0 | — | **No effect.** Withholding it never changes a forecast |
| 4 OFW remittances | **none.** Remittance is removed by design (`DROP` in `app/hcw/engine.py`), and no provincial series exists | — | — | — | — | — | **Cannot be tested.** FINAL has no remittance input |
| 5 Poverty and social vulnerability | `p_poverty`, `p_subsistence`, `p_density` | 0.260 (0.27 / 0.25 / **not selected in 2021**) | −0.002 [−0.012, +0.008] | −0.031 | 2 | `p_poverty` and `p_subsistence`: yes (ρ +0.76 / +0.84). `p_density`: denser → lower risk, which is plausible (urbanity) but is not a "vulnerability" direction | **Not established.** Large SHAP share in 2018–19, but no out-of-sample loss when it is removed: its information is carried by regional accounts |

## 2. Groups FINAL actually relies on (not dashboard groups)

| Group | SHAP share at L1 | Retrain ΔBrier [95 % CI] | ΔBA | Flips | Verdict |
|---|---|---|---|---|---|
| Regional economy (`hh_grdp_rel`, `income_rel`; **regional, not provincial**) | 0.417 (absent in 2021) | **+0.029 [+0.003, +0.054]** | −0.117 | 15 | **Genuine improvement.** Higher GRDP → lower risk (ρ −0.89) |
| Agriculture and fish production (`ag_palay_yoy`, `c_agri_yoy`, `agri_since`, `mi_ag_dev3y`) | 0.105 | **+0.011 [+0.001, +0.020]** | −0.023 | 5 | **Genuine improvement** (small). Production growth → lower risk |
| News / NLP signals | 0.174 (0.49 in 2021 only) | +0.002 [−0.001, +0.005] | −0.011 | 1 | Not established |

**Single-input retrains (seed 168):**
- `hh_grdp_rel`: +0.025 [−0.002, +0.052], 14 flips. This is the largest single effect, borderline at one seed.
- `cpi_food_rel_nat`, `p_poverty`, `c_agri_yoy`, `l_rice_rel` and `income_rel` each have a CI that includes 0.

## 3. Findings
1. **Only two of the five dashboard groups carry any FINAL signal:** market and prices, and poverty. Neither passes the out-of-sample test.
2. **Climate and employment have no measurable effect on any FINAL forecast.** Remittance is not a FINAL input at all.
3. **The only groups that genuinely improve out-of-sample forecasting are regional economy and agriculture/fish.** Neither is a dashboard group, and the regional-economy input is the same for every province in a region.
4. **The live fits (trained through 2021) did not select regional economy or poverty**, so their contributions at the current issue are exactly zero (11-13 ETMIX completion report). A dashboard that shows five contributor bars for FINAL would therefore show effects the model does not have.
5. Recommendation (unchanged from 11-13, not implemented):
   - Label the groups by what FINAL uses: regional economy (marked regional), market and prices, poverty and social vulnerability, agriculture and fish.
   - Show climate, employment and remittance as context only, not as model contributors.
   - The brief forbids forcing equal importance, and nothing here does.
