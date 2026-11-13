# FINAL input-feature audit (verified from code and fitted models, 2026-11-13)

## Sources
- **Inventory:** `evidence/G3_input_inventory.csv`, one row per candidate input: group, feature sets, empirical geography, training missing share, selection count over the 110 FINAL fits, and mean gain share.
- **Selection and gain:** `../aiPHeed_final_stability_lead_20261113/features_lead/*.json`, recorded inside each fit from training rows only.
- **Code:** `app/hcw/engine.py` (feature sets, `NEW_GROUPS`, `DROP`), `app/hcw/inputs.py` (agriculture, climate exposure, GRDP), `app/e154/model.py` (regional consumption, release rule), `app/e151/prov.py` (news and SWS inputs), `app/e168/lgbm_only.py` (feature sets).

## How empirical geography was determined
For each input, I counted distinct values across provinces at each forecast origin in training rows: one value means national; one value per region means regional.
- **Market, poverty and agriculture/fish inputs** vary by province.
- **Employment inputs** are national (one value per quarter); `unemp_region` is empty in every training fold.
- **Regional accounts** are regional: `hh_grdp_*` from code, `income_*` empirically.
- **News indices** come in three levels: `n_*` national, `a_*` area (SWS area / region) and `p_*` provincial.

A regional or national value repeated across provinces carries **no within-region provincial information**. This report never counts it as provincial.

## The 77 candidate inputs, by meaning

| Group (by meaning) | Inputs (definition) | Source and level | Release rule in the pipeline | Selected (of 110 fits) | Mean gain share |
|---|---|---|---|---|---|
| **Regional accounts (PSA)** | `hh_grdp_rel`: log regional GRDP per capita (constant 2018 prices) − mean over regions. `hh_grdp_g`: its yearly change. `income_rel`, `income_growth`: the same for regional household final consumption per capita | PSA regional accounts; **regional** | Year Y usable from Q3 of Y+1 (`E154.available_year`, an assumed rule). 2024–25 GRDP values are flagged estimates, used only in live issues, never in evaluation folds | `hh_grdp_rel` 100; `income_rel` 32; growth inputs 0 | **0.43** (`hh_grdp_rel`) + 0.02 |
| **Market and prices** | Provincial food and rice CPI: yoy, 3-month, acceleration, relative to national, since anchor (`cpi_*`); local farm-gate palay and wholesale rice levels relative to the region and yoy (`l_fg_*`, `l_rice_*`); terms of trade (`l_terms`) | PSA CPI and price surveys; **provincial** | As-of price panel, published months only (`test_e152`) | `cpi_food_rel_nat` 110, `cpi_food_3m` 110, `cpi_food_yoy` 110, `l_rice_rel` 110, `l_fg_rel` 80, `l_fg_yoy` 32, `cpi_rice_yoy` 30, `cpi_since` 30, `l_terms` 10 | 0.15–0.24 |
| **Poverty and social vulnerability** | `p_poverty` (poverty incidence), `p_subsistence` (subsistence incidence), `p_poverty_gap`, `p_density` (population density) | PSA official poverty statistics; census; **provincial** | Latest released round before the origin | `p_poverty` 100, `p_subsistence` 100, `p_density` 80 | 0.17–0.26 |
| **Agriculture and fish production** | Palay and corn production yoy and 3-year deviation, per capita (`ag_*`); agricultural production yoy and since anchor (`c_agri_yoy`, `agri_since`); fisheries production yoy (`l_fish_yoy`) | PSA production statistics; **provincial** | 45 days after quarter end | `ag_palay_yoy` 80, `c_agri_yoy` 80, `agri_since` 64, `ag_dev3y` 30, `l_fish_yoy` 10, `ag_corn_yoy` 10 | 0.07 |
| **Climate** | Rain and soil anomalies 3–6 months (`c_rain_anom_6m`, `c_soil_anom_3m`); since-anchor rain, soil and typhoon rate; typhoons in the past 4 quarters (`c_tc_4q`); ONI (national ENSO); dry months in the past 6 and rain anomaly over 12 (`vu_dry6`, `vu_rain12`); **past-365-day** typhoon wind exposure and strong-storm count (`vu_tc_wind`, `vu_tc_strong`); 1990–2010 typhoon climatology (`vu_tc_clim`, **static**) | NASA POWER, IBTrACS (provincial or point); ONI (national) | Months completed before the origin | `vu_tc_strong` 110, `vu_tc_wind` 110, `vu_tc_clim` 30, `oni` 20, `tc_rate_since` 20, `c_tc_4q` 20, `vu_rain12` 20 | 0.001–0.024 |
| **Employment** | `unemp_rate`, `unemp_yoy`, `unemp_chg_since` (national), `unemp_region` (empty) | PSA LFS; **national** | Released before the origin | **0** | **0** |
| **News / NLP** (counted inside topics) | Event indices by topic at national (`n_e_*`), area (`a_e_*`) and provincial (`p_e_*`) level; provincial topic proportions (`p_tp_*`); targeted-news indices (`p_tg_*`); intensity; net since anchor; regional net (`r_e_net`); `h2` = news-model SWS hunger increment | GDELT, newspaper archives, Google News; XLM-R / BERTopic; DA-validated dataset | Stories before the origin (`test_e151`) | `a_e_hunger` 26, `a_e_employment` 16, `a_e_market`, `r_e_net`, `n_net_since`, `a_net_since` 10 | 0.17 at Leads 1–2 (2021 fold only); ≈ 0 at Leads 3–8 |
| **Timing** | `gap_q` (own-survey gap), `lead` | Derived | n/a | `gap_q` 20 | 0.001 |
| **OFW remittances** | **None.** The remittance family is excluded by design (`DROP = ("fish", "remittance")` in `app/hcw/engine.py`) | BSP (national) | n/a | n/a | n/a |

## Corrections to the 13 November trigger audit
1. **`vu_tc_wind` and `vu_tc_strong` are recent (past-365-day) provincial typhoon exposure, not static measures.** Only `vu_tc_clim` is static.
2. **The "poverty" group there included `hh_grdp_rel` and `income_rel`, which are regional accounts.** Separated, regional GRDP per capita is the single largest input (about 43 % of gain). Provincial poverty, subsistence and density together carry 17–26 %.
3. **Remittances are absent by design** (`DROP`), not only for lack of data.

## Redundancy and concealment
- **Regional GRDP and provincial poverty overlap.** Retraining without poverty changes Lead 1 balanced accuracy by only −0.011, because regional GRDP and the remaining inputs compensate. Withholding poverty at prediction time still flips 26 forecasts.
- **Employment and national news indices are repeated across all provinces.** They cannot separate provinces and are never or rarely selected.
- **Regional accounts are repeated across a region's provinces.** Their large weight means much of FINAL's province ranking is actually a **region** ranking.
