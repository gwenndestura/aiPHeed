# FINAL-ETMIX: dashboard contributor groups (Part 5)

## Decision
**Four forecast-factor groups, two structural elements, three context indicators.**
- The earlier five-trigger design is **not** kept as given. Climate, employment and remittance are not supported as triggers for this model.
- The groups below come from `FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md`.
- **Display rule:** a group is shown as a forecast factor only if it is *core*, or *supporting* with ≥ 5 % of the Lead-1 attribution. This is a presentation rule, set after the classification was computed; it changes no model output.

| # | Dashboard group | Tier | Exact model inputs | Official sources | Resolution | Latest period at the live issue | Predictive evidence | Ablation | Why DA should see it |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Regional economy (GRDP and household income)** | **Core forecast factor** | `hh_grdp_rel`, `hh_grdp_g`, `income_rel`, `income_growth` | PSA Regional Accounts (GRDP per capita, constant 2018 prices); PSA FIES regional income | **Region:** one value for all CALABARZON provinces; labelled "regional figure" | Latest GRDP year the release rule allows before the issue (the H_cw branch extends GRDP with PSA 2024–25 estimates, `app/hcw/grdp_extend.py`) | 42 % of Lead-1 attribution; 0.46 of gain; HIGH rows +0.11 vs LOW −0.09 logit | Retrain without: BA −0.117, Brier +0.029 (CI excludes 0); withholding flips 85 of 532 forecasts | The largest single input. A weaker regional economy than the national average raises every province's forecast risk. **It cannot rank provinces within CALABARZON** |
| 2 | **Food prices and inflation** | Supporting factor | `cpi_food_rel_nat`, `cpi_food_yoy`, `cpi_food_3m`, `cpi_rice_yoy`, `cpi_since`, `l_fg_rel`, `l_fg_yoy` (and `l_rice_rel`, `l_terms`, used rarely) | PSA provincial CPI (food, rice); PSA farmgate palay prices | Province | Monthly CPI to the last complete month before the issue (3-month windows) | 28 % of Lead-1 attribution (41 % in 2021) | Retrain without: BA −0.032, Brier +0.011 (CI includes 0); 28 withholding flips | Food affordability is the most direct, frequently updated provincial signal, and it differentiates provinces |
| 3 | **Poverty and social vulnerability** | Supporting factor | `p_poverty`, `p_subsistence`, `p_poverty_gap`, `p_density` | PSA official poverty statistics; PSA POPCEN 2024 and land area | Province | Latest official provincial poverty release before the issue (carried forward between releases) | 26 % of attribution; HIGH rows +0.05 vs LOW −0.02 | Retrain without: BA −0.031, Brier −0.002 (mixed); 31 withholding flips | Structural vulnerability. It also weights the municipal priorities (Objective 3), so it links the map to the LGU list |
| 4 | **Agriculture and fish production** | Supporting factor | `c_agri_yoy`, `agri_since`, `ag_palay_yoy`, `ag_dev3y` (and `ag_corn_yoy`, `l_fish_yoy`, used rarely) | PSA OpenSTAT palay, corn and agricultural output; fish prices | Province | Latest four published quarters before the issue | 10.5 % of attribution | Retrain without: Brier +0.011 (CI excludes 0), BA −0.032 | Local production and farm income. It is in the DA's own mandate, so the DA can act on it |
| S1 | **Starting point: latest provincial survey** | Structural | Survey anchor (H / OH / RSS) | DOST-FNRI HFIAS (2013–2021) | Province | The province's own survey round and the latest released round | Every forecast starts here | — | Shows how old the measured information is (for example, Laguna 2018) |
| S2 | **Time since the survey** | Structural | `gap_q` and the two elapsed-time hypotheses (g, s) | — | Province | Quarters | ETMIX averages the two readings | — | Old surveys mean more uncertainty. Flag it (risk flag G) |
| C1 | Climate and typhoon exposure | Context only | `vu_*`, `c_tc_4q`, `c_rain_*`, `oni`, … | NASA POWER; NOAA IBTrACS; NOAA ONI | Province (`oni` global) | Past 6–12 months | 0.1 % of attribution | No retraining loss in Brier; 2 withholding flips | Situational awareness only. **Not a forecast trigger** |
| C2 | News signals (FSSI, topics) | Context only (Objective 1 output) | `p_e_*`, `a_e_*`, `n_*`, topics | aiPHeed news corpus (XLM-R, BERTopic) | Province with area / national fallback | Quarter before the issue | Redundant: retraining without changes nothing | 0 retraining flips | What is being reported. **Not a driver** |
| C3 | Employment | Context only | `unemp_*` | PSA LFS | National (provincial LFS from 2022 only) | Latest LFS | Never selected | 0 | Context; labelled national |

**Not shown:** OFW remittances and fish kills (not model inputs).

## Rules for the explanation text
1. **Show a direction** ("raised / lowered this forecast") only for groups 1–4. It comes from the exact TreeSHAP contribution of the forecast being shown; the sign is guaranteed for monotone-constrained inputs and learned for the others. Never infer it from association with HIGH outcomes.
2. **Group 1** always carries: "This is a regional figure, the same for every CALABARZON province."
3. **Missing inputs:** when an input was unpublished at the issue (MIND flag), say so. Never show a stale value as current.
4. **Context groups C1–C3** show values and sources, never a contribution bar or a direction.

## What the dashboard should answer, and from where

| Question | Answer source |
|---|---|
| What is the forecast risk? | ETMIX probability and class (HIGH ≥ 0.50), per province, with the target quarter and lead |
| Which contributors support it? | Groups 1–4 with their exact contributions (`/api/v1/research/etmix/contributors`) |
| Coverage of the contributors | Resolution, source and latest period per group (above; API `resolution`, `source`, `values`) |
| What raises or lowers the estimate? | The signed contributions of groups 1–4 (plus the anchor and trend); attribution, not causation |
| What should DA consider when prioritizing? | Provincial class → municipal priority (poverty × density) → food-price and agriculture values for the province → survey age |

## Implementation status
- **Backend (experimental, admin-only):** implemented. `app/hcw/etmix.py` (`DISPLAY_GROUPS`), `app/hcw/etmix_serve.py`, `app/api/v1/etmix.py`. The tiers are read from the research registry (`data/etmix/out/contributor_registry.json`); nothing is hardcoded.
- **Public dashboard:** **not changed.**
  - It serves E196, whose own trigger groups differ.
  - Switching it to these groups requires approving ETMIX as the replacement.
  - The approved frontend renders whatever `triggers` the backend supplies (`LeftPanel.tsx`), so the switch needs no new UI elements. The new keys (`regional_economy`, `agri_production`) would fall back to an existing icon.
