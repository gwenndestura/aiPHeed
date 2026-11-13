# 09 — Indicator and group contribution assessment; final dashboard contributor structure (deliverables 13, 14)

Scripts:
- `scripts/indicators.py`: re-scores the existing 110 fold fits (withholding, permutation with 10 repeats, TreeSHAP; FINAL only).
- `aiPHeed_final_reliability_20261113/scripts/contrib_final.py`: 105 group retrains and 18 single-input retrains.
- `direction_check.py`.

Evidence:
- `evidence/IND_assessment.csv` (41 inputs);
- `aiPHeed_final_reliability_20261113/evidence/CONTRIB_*.csv`.

**Rule, fixed in the script before scoring:**
- An indicator is **predictive** only if destroying its information (permutation) makes Lead-1 Brier worse with a 95 % CI above 0, **and** it is selected in at least 50 of 110 fits, **and** its direction is plausible.
- A **group** is predictive if retraining without it makes Lead-1 Brier worse with a CI above 0.

## 1. Group level (out-of-sample retraining, Lead 1, 3 rounds × 5 seeds)

| Group (original dashboard group) | ΔBrier without it [95 % CI] | ΔBA | Class flips | Verdict |
|---|---|---|---|---|
| Regional economy: GRDP per person, regional income (not an original group) | **+0.029 [+0.003, +0.054]** | −0.117 | 15 | **Predictive.** Regional resolution only |
| Agriculture and fish production: palay, corn, combined harvest (not an original group; thesis "fish kill" proxy) | **+0.011 [+0.001, +0.020]** | −0.023 | 5 | **Predictive** (small) |
| 1 Market and prices | +0.011 [−0.004, +0.026] | −0.012 | 4 | Contextual: plausible direction, gain not significant |
| 2 Climate stress | −0.002 [−0.012, +0.006] | −0.020 | 1 | Contextual: no out-of-sample gain |
| 3 Employment | 0.000 | 0 | 0 | Contextual / requires data: national series only, never moves a forecast |
| 4 OFW remittances | — (no input) | — | — | **Requires additional data:** no provincial series; removed from the model by design |
| 5 Poverty and social vulnerability | −0.002 [−0.012, +0.008] | −0.031 | 2 | Contextual for forecasting. Kept for the thesis Objective 3 LGU weighting. Not a trigger bar: the thesis names poverty as the Objective 3 vulnerability weight, not a trigger |
| News / NLP signals | +0.002 [−0.001, +0.005] | −0.011 | 1 | Contextual. Shown inside groups |

## 2. Individual indicators (ranked by mean |TreeSHAP| across 110 fits)

| Rank | Indicator | Group | Public source / resolution | Selected (of 110) | Permutation ΔBrier L1 [CI] | Rounds worse | HIGH recall change when scrambled | Direction | Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `hh_grdp_rel` | Regional economy | PSA regional accounts; **regional**, annual | 100 | +0.021 [−0.008, +0.050] | 2/3 | **−3 HIGH detections** | yes (−) | **Retain; show** (group-level significant, largest single effect; borderline alone) |
| 2 | `cpi_food_rel_nat` | Market | PSA CPI; provincial, monthly | 110 | −0.000 [−0.009, +0.008] | 1/3 | −1 | yes (+) | Retain as input; contextual display |
| 3 | `p_density` | Poverty | PSA census; provincial | 80 | +0.001 [−0.008, +0.010] | 2/3 | 0 | denser → lower risk | Contextual (LGU weighting) |
| 4 | `a_e_market` | News | News corpus; area level | 10 | +0.005 [−0.001, +0.011] | 1/3 | 0 | no prior | Contextual |
| 5 | `vu_rain12` | Climate | NASA POWER; province centroid | 20 | not perturbed in L1 fits | — | — | no prior | Contextual |
| 6 | `p_subsistence` | Poverty | PSA; provincial, triennial | 100 | −0.000 [−0.007, +0.007] | 1/3 | 0 | yes (+) | Contextual |
| 7 | `p_poverty` | Poverty | PSA; provincial, triennial | 100 | +0.001 [−0.002, +0.005] | 1/3 | 0 | yes (+) | Contextual |
| 8 | `cpi_rice_yoy` | Market | PSA CPI | 30 | −0.000 [−0.003, +0.002] | 0/3 | 0 | yes (+) | Contextual |
| 9 | `ag_palay_yoy` | Agriculture | PSA palay/corn, quarterly (**refreshed 11-13**, see §4) | 80 | +0.001 [−0.002, +0.004] | 1/3 | 0 | yes (−) | **Retain; show within Harvests** (group significant) |
| 10 | `c_agri_yoy` | Agriculture | PSA palay/corn, quarterly | 80 | +0.001 [−0.002, +0.004] | 1/3 | 0 | yes (−) | **Retain; show within Harvests** |
| 11 | `l_fg_rel`, `l_fg_yoy` | Market (local prices) | PSA/BAS farmgate prices | 80 / 32 | +0.001 / +0.002 (CI includes 0) | 2/3 | 0 | higher farmgate price → lower risk (producer income; no fixed prior) | Contextual |
| … | `oni`, `vu_tc_*`, `c_tc_4q`, `tc_rate_since` | Climate | NOAA ONI (global); IBTrACS | 20–110 | ≈ 0 | 0 | 0 | no prior | Contextual |
| … | `unemp_rate` | Employment | PSA LFS; national/regional only before 2022 | < 20 | 0 | 0 | 0 | — | Requires provincial data (PSA provincial LFS from 2022 can be used prospectively only) |
| — | 7 missing-value flags and `r_e_net` | various | — | — | — | — | — | — | Not recommended (never used) |

The full table is in `IND_assessment.csv`.

**What it shows:**
- **No single indicator passes the permutation test alone.** With 72 outcomes in 3 rounds, single-indicator effects are below what the data can resolve.
- Out-of-sample value is established only at **group level**, for regional economy and harvests.
- Relative to the 2026-Q4 issue's information cut-off, every input was published before the origin (release-lag rules in `08_REPRODUCIBILITY` of the reliability study).

## 3. Why regional economy and harvests help while the dashboard groups do not
- **Regional economy:** GRDP per person separates poorer from richer regions (ρ −0.89 with its contribution), and that difference is the largest persistent part of provincial food-insecurity variation. It is regional, so it ranks regions, not provinces within a region; it caused the two 2019 within-region misses (report 06).
- **Harvests:** palay and corn output changes vary across provinces and over time, and they precede the survey reference quarter.
- **Market:** provincial food CPI moves largely together across provinces (national price shocks), so it adds little beyond the anchor and the regional terms.
- **Climate:** exposure indices are nearly constant within a province, so their information is already in the survey anchor.
- **Employment:** national rates are identical for every province, so they cannot separate provinces.
- **Remittances:** no provincial series exists.

## 4. Temporal-alignment defect found and corrected (11-13)
- **Defect:** `ag_palay_yoy` and `ag_corn_yoy` were built from a PSA file ending in 2023-Q4, so the 2026-Q4 forecast compared 2023 with 2022 while the dashboard text said "latest quarters".
- **Fix:** `app/hcw/inputs.py` now adds the PSA live download of the same OpenSTAT table (2E4EVCP0). The two sources are identical on the overlapping 2023 quarters (zero difference).
- **Scope:** only rows from 2024-Q3 onward changed, so no historical training or evaluation row changed.
- **Effect on live forecasts:** up to 0.002 in probability and 1.3 points in share; all remain LOW.

## 5. Final dashboard contributor structure (implemented in the preview; no frontend design change)

| Bar shown | Composition | Status | What the explanation says |
|---|---|---|---|
| **Regional economy (GRDP)** | `hh_grdp_*`, `income_*` | Predictive (group CI > 0) | "…forecasts got measurably worse without this group." Marked as a regional figure |
| **Rice and corn harvests** | palay/corn by crop + combined harvest (moved out of Climate) | Predictive (group CI > 0) | Same sentence. Current PSA quarters |
| **Food prices** | PSA food/rice CPI + local rice/palay/fish prices | Contextual | "…not measurably worse without this group, so read it as context." |
| **Dry spells and typhoons** | rain/soil anomalies, ENSO, typhoon exposure | Contextual | Same |
| **Employment (national)** | national unemployment | Contextual | Same; marked as a national figure |
| Other factors | survey level, time since survey, poverty, density, news not inside a group | — | Shown as "Other factors" |
| OFW remittances | — | Not shown | No input exists. It stays in the About text as unavailable data |

**Display rules:**
- A bar is drawn only when its exact contribution moves *that* forecast's share by at least 1 percentage point.
- Contributions are additive TreeSHAP values, labelled as model influence, not causes.

**Current issue:**
- Batangas shows Food prices only.
- Laguna, Quezon and Rizal show Dry spells and typhoons.
- Cavite shows no bar: its forecast is its survey level plus the time term.
- Regional economy shows on no forecast, because the live fits (trained through ENNS 2021) did not select GRDP.
