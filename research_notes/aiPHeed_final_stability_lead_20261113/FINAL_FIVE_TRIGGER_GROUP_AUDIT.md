# FINAL: five dashboard trigger groups vs model inputs (audited 2026-11-13)

## Sources and method
- **Fitted models:** the 110 FINAL fits of this study, from the walk-forward study (3 rounds × Leads 1–8 where supported × 5 seeds). Each fit records:
  - its **selected inputs**, chosen inside the fit from training rows only;
  - their **LightGBM gain** (`features_lead/*.json`).
- **Scripts and outputs:**
  - `scripts/trigger_audit.py` produces `evidence/TRIG_group_audit.csv` and `evidence/TRIG_gain_share_per_fit.csv`.
  - The input → group mapping is `group_of()` in `../aiPHeed_final_standalone_20261113/scripts/rerun_final.py`. News indices are counted inside their topic's group; cross-topic news indices, agriculture and timing are listed separately and are **not** a sixth dashboard group.
  - Missing-flag inputs (`mi_<input>`) count with their input. A "times selected" count can therefore exceed the number of fits.
- **Effect when removed:** each group set to missing (as if unpublished) with the same fitted model, Lead 1, seed 168 (`../aiPHeed_final_standalone_20261113/evidence/R7e_*`).

## The three things kept separate

| Dashboard group (your five) | What the served dashboard (E196) displays | FINAL candidate inputs (77) | Selected by FINAL (of 110 fits) | FINAL gain share, Lead 1 / all leads | Effect on FINAL Lead 1 forecasts when removed |
|---|---|---|---|---|---|
| **1 Market and prices** | "Market / Prices" bar: provincial food and rice CPI | 15: food/rice CPI yoy, 3-month, acceleration, relative-to-national, since-anchor; local food-group and rice prices and relatives; terms of trade; market news (3) | 10: `cpi_food_3m`, `cpi_food_yoy` (all fits), `l_rice_rel`, `cpi_food_rel_nat` (110/110), `l_fg_rel` (90), `l_fg_yoy` (42), `cpi_rice_yoy`, `cpi_since` (30), `a_e_market`, `l_terms` (10) | **0.28 / 0.20** | 2 class flips; balanced accuracy −0.02 |
| **2 Climate stress** | "Climate Stress" bar: rainfall, soil moisture, typhoons, ENSO | 16: rain and soil anomalies, typhoons in 4 quarters, rain/soil/typhoon since anchor, ONI, 5 structural exposure measures (`vu_*`), climate news (3) | 7: `vu_tc_strong`, `vu_tc_wind` (110/110: **static** typhoon exposure); `vu_tc_clim` (30); `oni`, `tc_rate_since`, `c_tc_4q`, `vu_rain12` (20) | **0.001 / 0.014** | **0 flips** (probability change ≤ 0.001) |
| **3 Employment** | "Employment (national)" bar: PSA LFS unemployment (national) | 10: unemployment rate, yoy, change since anchor, regional unemployment; household income growth; regional GRDP growth; employment news (4) | **1**: `a_e_employment` (area employment-news index; 16/110). **No official employment series is ever selected.** | **0.002 / 0.002** | **0 flips** |
| **4 OFW remittances** | "OFW Remittance (national)" bar: BSP remittances (an E196 input) | **0: no remittance input among FINAL's 77** | 0 | **0** | Not applicable |
| **5 Poverty and social vulnerability** | Not a bar; shown as "Other model inputs". The dashboard's fifth bar is **Fish Production** | 14: poverty incidence, subsistence, poverty gap, density, relative income, regional GRDP level, hunger proxy `h2`, poverty and hunger news (7) | 6: `p_poverty` (all), `p_subsistence` (all), `hh_grdp_rel`, `p_density` (100), `income_rel` (32), `a_e_hunger` (26) | **0.56 / 0.70** | **13 flips; balanced accuracy −0.08** (largest) |
| *Not a group:* agriculture and fish production | Fish Production bar (E196) | 7 | 6: `ag_palay_yoy`, `c_agri_yoy` (80), `agri_since` (64), `ag_dev3y` (30), `l_fish_yoy`, `ag_corn_yoy` (10) | 0.07 / 0.07 | 5 flips |
| *Not a group:* cross-topic news | Counted inside the groups on the dashboard | 13 | 3 (10/110 each) | 0.09 / 0.03 | 0 flips |

**Gain share by lead:**

| Lead | Market | Climate | Employment | Remittance | Poverty | Agriculture/fish | News |
|---|---|---|---|---|---|---|---|
| 1–2 | 0.28 | 0.001 | 0.002 | 0 | 0.56 | 0.07 | 0.09 |
| 3–6 | 0.17 | 0.024 | 0.002 | 0 | 0.74 | 0.06 | 0 |
| 7–8 | 0.15 | 0.001 | 0.003 | 0 | 0.77 | 0.07 | 0 |

## Findings
1. **FINAL genuinely uses two of the five groups:**
   - market and prices;
   - poverty and social vulnerability (dominant).
2. **Climate stress is selected but inert.** The selected climate inputs are static exposure measures, and the time-varying climate inputs are rarely chosen. Removing the group changes no forecast.
3. **Employment is effectively absent.** Only an employment-news index is ever selected, in 16 of 110 fits. Official employment inputs:
   - are national or regional;
   - have one value for every province in the 2018 and 2019 training rows;
   - sit 5.6–7.9 SD outside training in 2021 (COVID).
4. **OFW remittances are not a FINAL input at all.**
5. **Group mismatch.** The dashboard's five bars belong to **E196**, not FINAL. E196 shows Fish Production as the fifth bar and poverty under "Other". Your five groups put poverty and social vulnerability fifth. Nothing on the dashboard was changed.

## Can genuine provincial indicators fill the gaps? (checked 2026-11-13)

| Group | Genuine provincial source | Historical release date vs evaluation origins (latest: 2021-Q2) | Verdict |
|---|---|---|---|
| Employment | PSA "Annual Provincial Labor Market Statistics" (2018–2020, 117 provinces and HUCs), first released **27 January 2022**; later annual provincial releases | After every evaluation origin | Usable for **future** forecasts and prospective validation only; cannot be back-filled into these folds without leakage |
| OFW remittances | PSA Survey on Overseas Filipinos: by **region** and OFW characteristics; BSP: national | No provincial series found | **No genuine provincial remittance series.** Copying regional values to provinces would not be a provincial observation; not done |
| Climate | NASA POWER, IBTrACS, ONI (already provincial or point-based, as-of) | Already available | Data exist; the model does not use them. The likely reason: anomalies explain little of the residual change on training transitions (12 November evidence: all change inputs \|ρ\| < 0.15) |

Sources:
- [PSA Annual Provincial Labor Market Statistics](https://psa.gov.ph/statistics/labor-force-survey/node/165789)
- [PSA release PDF (2022-03)](https://psa.gov.ph/sites/default/files/iesd/2022-12/Provincial%2520Annual%2520Labor%2520and%2520Employment%2520Statistics.pdf)
- [PSA 2020 Survey on Overseas Filipinos](https://psa.gov.ph/sites/default/files/iesd/2022-12/2020%2520SOF%2520Special%2520Release.pdf)

## Conclusion
**FINAL does not genuinely use all five dashboard groups.** It uses two: poverty and social vulnerability, then market and prices. Climate and employment are present only nominally, and remittances are absent. Showing five equally important groups for FINAL would misrepresent the model.
