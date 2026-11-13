# FINAL-ETMIX: complete input inventory (Part 4A)

**Four different things are kept apart below:**
1. **available** candidate inputs (77);
2. inputs **selected** in each fit (top 25 by training-residual correlation, after pruning: 17–20 per fit, including missing-flags);
3. inputs that **contribute predictive information** (`FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md`);
4. inputs **suitable for the dashboard** (`FINAL_ETMIX_DASHBOARD_TRIGGER_GROUP_REPORT.md`).

**Full table:** `evidence/C9_input_inventory_etmix.csv`. It lists every candidate with:
- its group;
- the feature sets it belongs to;
- its empirical geography, computed from the 2021 Lead-1 training rows (does the value vary within a region in a quarter?);
- its missing share in training;
- how often it was selected in the 110 fits;
- its gain share and mean |TreeSHAP|.

## 1. Inventory by group

| Group | Candidate inputs (exact names) | Source datasets | Geography (empirical) | Transformations | Selected (sum over 110 fits) | Gain share |
|---|---|---|---|---|---|---|
| Regional economy | `hh_grdp_rel`, `hh_grdp_g`, `income_rel`, `income_growth` | PSA Regional Accounts (GRDP per capita, constant 2018 prices; latest year published by the origin; 2024–25 extension in the H_cw branch); PSA FIES regional income | **REGIONAL** (all four) | Log ratio to the national mean; annual growth | 132 (`hh_grdp_rel` 100) | 0.455 |
| Food prices and inflation | `cpi_food_rel_nat`, `cpi_food_yoy`, `cpi_food_3m`, `cpi_food_accel`, `cpi_rice_yoy`, `cpi_since`, `l_fg_rel`, `l_fg_yoy`, `l_rice_rel`, `l_rice_yoy`, `l_terms` | PSA provincial CPI (food, rice); PSA farmgate palay and wholesale rice prices | Provincial | Year-on-year / 3-month change; level relative to national; change since the anchor survey; price centring **as of each origin** (fix 2026-11-11) | 622 | 0.186 |
| Poverty and social vulnerability | `p_poverty`, `p_subsistence`, `p_poverty_gap`, `p_density` | PSA official poverty statistics (latest release by the origin); PSA POPCEN / land area | Provincial | Logit / level; carried forward between releases | 280 | 0.229 |
| Agriculture and fish production | `c_agri_yoy`, `agri_since`, `ag_palay_yoy`, `ag_corn_yoy`, `ag_dev3y`, `ag_pc`, `l_fish_yoy` | PSA OpenSTAT palay, corn and agricultural output; fish prices | Provincial (`l_fish_yoy` 79 % missing) | Four-quarter growth; deviation from the 3-year mean; per capita | 234 | 0.067 |
| Climate and typhoon exposure | `c_rain_anom_6m`, `c_soil_anom_3m`, `c_tc_4q`, `rain_since`, `soil_since`, `tc_rate_since`, `vu_dry6`, `vu_rain12`, `vu_tc_wind`, `vu_tc_strong`, `vu_tc_clim`, `oni` | NASA POWER; NOAA IBTrACS; NOAA ONI | Provincial (`oni` national) | Anomalies; past-6/12-month counts; **`vu_tc_*` = past-365-day exposure** (not static) | 330 | 0.014 |
| Employment | `unemp_rate`, `unemp_yoy`, `unemp_chg_since`, `unemp_region` | PSA LFS | **NATIONAL**; `unemp_region` absent in the training rows | Rate, change | **0** | 0 |
| News / NLP | 33 inputs: `p_e_*`, `p_tp_*`, `p_tg_*`, `p_intensity`, `p_net_since` (province); `a_e_*`, `a_net_since` (area); `n_e_*`, `n_net_since`, `r_e_net` (national); `h2` | aiPHeed corpus: XLM-RoBERTa zero-shot events, BERTopic topics, FSSI | Province (with area/national fallback 63 %); area = REGIONAL; national | Shares and net stress per quarter; change since the anchor | 82 | 0.049 |
| Timing (structural) | `gap_q`, `lead` | — | — | Elapsed quarters | 20 | 0.001 |
| Survey anchor (structural) | H / OH / RSS | FNRI HFIAS rounds released by the origin | Province | Shrunk provincial deviation + national level of the latest released round | Every fit | Not an input; the starting point |

**Dropped by design** (`app.hcw.engine.DROP`):
- fish-production growth `c_fish_yoy`;
- OFW remittances (no provincial series exists).

Missing-value flags (`mi_*`, MIND) are added automatically for inputs with training gaps. They are counted with their base input.

## 2. What each fit actually uses
- **Always selected (110/110):** `cpi_food_rel_nat`, `l_rice_rel`, `vu_tc_wind`, `vu_tc_strong`.
  - Being selected is not contributing: `l_rice_rel` and `vu_tc_strong` have ≈ 0 gain and ≈ 0 attribution.
  - They pass the correlation screen, but the monotone, regularized trees rarely split on them.
- **`hh_grdp_rel`:** selected in 100/110 fits, but **in none of the 2021 Lead-1 and Lead-2 fits**. There, the regional economy contributes nothing, and news + market inputs carry the attribution.
- **Employment inputs:** never selected.

## 3. Documentation versus code (checked)
| Earlier statement | Status |
|---|---|
| "`vu_tc_wind` / `vu_tc_strong` are static exposure" (earlier dashboard text) | **Wrong.** They are past-365-day counts (corrected in the 7-of-7 study; confirmed) |
| 7-of-7 inventory: geography blank for the 17 added inputs | **Filled here.** The regional-economy inputs are REGIONAL; agriculture and typhoon inputs are provincial |
| "Climate is a forecast trigger" (thesis five triggers) | **Not supported** for ETMIX (0.1 % of attribution; no retraining loss) |
| "Remittance trigger" | Not a model input (dropped; no provincial data) |
| "Fish kill trigger" (E196 dashboard key `fish_kill`) | Not a FINAL/ETMIX input |
