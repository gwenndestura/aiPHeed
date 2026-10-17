# E54 audit: is poverty used to forecast food-insecurity risk in aiPHeed?

**Written:** 2026-10-17 on branch `e46-lead2-policy` at d215bf8 (E53), before any E54 score.
**Question:** is PSA poverty (2021 municipal/provincial Small Area Estimates, poverty incidence, subsistence incidence, or a proxy) in the training data, the feature matrix or the inference of E38, E46-I7, E52 and E53? Or is it used only for the municipal vulnerability ranking and the dashboard?
**Method:** every model's input files were opened and their columns listed; every feature list was read from the code that builds the matrix and, where one exists, from the frozen model artifact. A column existing in some dataset was not taken as model use.

## 1. Answer

**Poverty is not used to forecast food-insecurity risk in any of the four models.** No poverty statistic is in any of their raw inputs, feature matrices or inference paths. PSA poverty enters aiPHeed in exactly one place: the **Objective 3 municipal vulnerability ranking** (and the dashboard's display of poverty rates). That ranking multiplies the already-computed province probability by a vulnerability weight; it does not feed back into any forecast.

The only poverty-related signal inside a model is indirect: the Filipino word *kahirapan* ("poverty") and the phrase "economic hardship" are among the keywords of the news **employment** trigger, so they can move `news_employment`, a share of news titles. That is a news-text proxy, not a poverty estimate (section 4).

## 2. Per-model table

| Model (status) | Poverty in the raw dataset? | Poverty in the training feature matrix? | Poverty used at inference? | Poverty used for rankings / display? |
|---|---|---|---|---|
| **E38** (aiPHeed-E38-LGBM-NQ, lead 2; **production default**, served from `backend/data/e36/e36_record.json` when `AIPHEED_LEAD2_MODEL` is unset) | **No.** Inputs: `backend/data/inputs/{sws_rounds, s1_labels, d_quarterly_panel, dnow_panel}.csv`, the E32 provincial rice CPI, the news store `articles.jsonl`, `fssi_v2_panel.csv`. No poverty column (section 3). | **No.** Served model: 6 features `H_margin, H_trend, D_last, Dnow, news_reg, fssi_v2` (`E38_Lead2_Diagnosis_Tuning/models/E38-LGBM-NQ_O2026-10-01_lead2.txt`, line 8 `feature_names=`; same list in the `.json`). Selection pool: COMPACT (6), COMB (13: `H_last, H_gap, H_trend, H_margin, D_last, Dnow, rice_rel, news_n, news_reg, news_direct_share, fssi_v2, fssi_missing, y_last`), COMB_T5 (COMB + 5 `trig_*` news shares). No poverty column (`E36…/runner/e36_lib.py:28-31`, `E38…/runner/e38_lib.py:23`). | **No.** | **Yes.** `e36_record.json` carries `lgu_ranking`: `risk_index = province p_high × (0.6·poverty_norm + 0.4·density_norm)`, 142 rows (`poverty_lgu_estimate` non-missing for 141; Lucena = province substitute 16.8, unverified). The ranking is built by `backend/scripts/build_record_e36.py:277-283` → `app/quarterly/lgu_audit.build_ranking`, and recomputed for the dashboard by `app/ml/inference/e31_engine.py:172-187` (`E31Disaggregator`). The dashboard also displays a province poverty rate (POPCEN-weighted SAE mean, `app/services/dashboard.py:469-482`) and per-LGU SAE values (`dashboard.py:721-726`). |
| **E46-I7** (served only with `AIPHEED_LEAD2_MODEL=e46`; target T43 = SWS hunger > 11.3 **and** provincial price signal) | **No.** Inputs (`e41_lib.load`, `e43_lib.load_extra`, `e46_lib.load_events`): PSA CPI index and YoY, SWS rounds, palay/corn and fisheries production, national LFS, news composition, PAGASA climate, BSP remittances/FX, PSA rice prices, FSSI v2, rice-policy events. No poverty column. | **No.** Price residual inputs (30): `F_hat_M1, F_now, D_now, gap_now, rice_whsl_yoy, tc_count, tc_count_l1, enso, enso_l2, palay_yoy, corn_yoy, enso_x_mom, tcl1_x_palay, fish_yoy, aqua_yoy, ur_yoy, under_yoy, remit_usd_yoy, remit_php_yoy, fx_yoy, news_market, news_climate, news_fish_kill, news_employment, news_ofw_remittance, news_n, tariff_yoy_regime, import_suspension_share, price_ceiling_share, food_emergency_share`. Hunger ridge inputs (12): `F_now, enso, enso_l2, tc_count, tc_count_l1, palay_yoy, fish_yoy, ur_yoy, under_yoy, remit_php_yoy, fx_yoy, news_n`. Both lists are stored in `E46_Rice_Policy/frozen/E46_I7_PROSPECTIVE_2027Q1.json` (`selection_at_origin`) and built in `E44…/runner/e44_components.py:25-34` + `E46…/runner/e46_lib.py:20`. | **No.** | **No** in the model or its record: `backend/data/e46/e46_record.json` has 0 occurrences of "poverty" and no `lgu_ranking`. The dashboard's municipal view under this mode is still the separate Objective 3 ranking (`dashboard.py:713-717`), which uses poverty. |
| **E52** (PS = provincial food-price pressure; E46 I7 price component; served only with `AIPHEED_LEAD2_MODEL=e52`) | **No** (same inputs as E46-I7). | **No.** Same 30 price residual inputs (`E53…/runner/e53_lib.py` `pcols()` = `PRICE_GROUPS` + `POLICY`). | **No.** | **No** in the record (`backend/data/e52/e52_record.json`: 0 "poverty"); the record text says "LGU rankings are relative prioritization" (`build_record_e52.py:231`). |
| **E53** (R0 = E52 kept; no calibrator or LightGBM arm adopted; served only with `AIPHEED_LEAD2_MODEL=e53`, E52 probabilities with D-1 attribution) | **No** (same inputs). | **No.** R0, C1/C2, LGB-R/RL/C and every ablation draw from the same 30 inputs; LGB-C adds base projections and distance-to-threshold features only (`e53_lib.py:204-205`). | **No.** | **No** in the record (`backend/data/e53/e53_record.json`: 0 "poverty"). |

**Non-missing observations of poverty in the four feature matrices: 0** (no poverty column exists in them).

## 3. Where poverty data exist in the repository

| Variable | File | Geographic level | Reference year | Non-missing values | Used by |
|---|---|---|---|---|---|
| `poverty_incidence_2021` (+ `cv_2021`, 90% CI) | `backend/data/reference/sae2021_calabarzon_municipal.csv` (sha256 `bb77e4c2…`; copied to `E54/data/`) | city/municipality | 2021 | 141 of 142 LGUs (Lucena, a highly urbanized city, is not in the PSA no-HUC table); 25 with CV > 20% | builds `lgu_vulnerability.csv` (`scripts/build_lgu_psa_2021_2024.py`) |
| `poverty_lgu_estimate`, `poverty_value_used` | `backend/data/inputs/lgu_vulnerability.csv` (sha256 `82f21a9f…`) | city/municipality | 2021 | 141 estimates; 142 values used (Lucena substitute 16.8 = "PSA 2021 province poverty incidence", source workbook not in the repo, unverified) | Objective 3 ranking (0.6 weight); dashboard |
| `subsistence_incidence_pct` (among population) | `backend/data/inputs/psa_subsistence_population_2021_2023.csv` (sha256 `7656e5e7…`) | province | 2021, 2023 | 10 (5 provinces × 2 years); CV 17.4–62.3% | **nothing served**; earlier E27 acquisition only |
| subsistence among families (+ food threshold) | `E27_Resolve_Forecasting_Failures/acquisition/validated/psa_subsistence_families_2021_2023.csv` | province + region | 2021, 2023 | 12 | nothing served |
| `poverty_incidence_pct` | `backend/data/processed/lgu_poverty.parquet` | city/municipality (mostly **province-mean fallbacks**) | 2021 | 142 | legacy dashboard fallback only (`dashboard.py:42`) |
| `subsistence_pct` | `backend/data/processed/psa_subsistence.parquet` | province | **2018** + later | 18 | nothing; **contains pre-2021 rows: must not be loaded** (study-window rule) |

**Province summaries of the 2021 municipal SAE** (computed for this audit from the 141 estimates):

| Province | LGUs | Unweighted mean, % | POPCEN-2024-weighted mean, % (dashboard definition) | Subsistence 2021 / 2023, % |
|---|---|---|---|---|
| Batangas | 34 | 8.55 | 8.79 | 1.0 / 1.4 |
| Cavite | 23 | 11.13 | 9.91 | 2.4 / 0.8 |
| Laguna | 30 | 7.89 | 6.04 | 2.4 / 1.3 |
| Quezon | 40 | 20.30 | 19.65 | 6.6 / 0.9 |
| Rizal | 14 | 6.89 | 7.06 | 0.9 / 2.6 |

**Legacy code, not served:** the pre-E25 pipeline (`backend/app/ml/features/feature_matrix.py:15,171`, `app/ml/training/datadriven_trainer.py:34`) listed `poverty_incidence` as a feature. No served model (E36/E38 or the lead-2 records) is built by that code.

## 4. Indirect proxies

- **News employment trigger:** `backend/app/ml/nlp/trigger_classifier.py:69-72` includes "economic hardship" and "kahirapan" among the employment keywords. E42 already flagged this (`E42…/runner/e42_audit.py:171`).
  - The keywords feed `news_employment` (the share of a province's titles in that group) in the E46-I7/E52/E53 price residual inputs.
  - They also feed `trig_employment` in E38's COMB_T5 pool, which the served E38 configuration (COMPACT) does not use.
- **What this proxy is, and is not:** it counts news titles that use a poverty word. It is not a poverty statistic, and E53's ablations found no reliable predictive value for the news group (`A-news` dBrier CI includes 0).
- **Other inputs:** labour-force unemployment and underemployment, and OFW remittances, relate to household income. They are not poverty measures.

## 5. Why poverty is not in training

These reasons are design facts; the E54 comparison tests whether they matter in practice.

1. **No time variation.**
   - SAE 2021 is one value per area.
   - Subsistence has two reference years, 2021 and 2023, and both appear in the same PSA release (publication date recorded as 2024-08-15).
   - So at any forecast origin at most one vintage is known.
   - A static provincial value is a fixed province attribute. It cannot explain why a province's risk changes from one quarter to the next, which is what the lead-2 targets measure.
2. **Geographic mismatch.**
   - The hunger part of T43 (and of the E38 label) is the **regional** SWS series: one value per quarter for all five provinces. A provincial poverty value averages to one constant across the region, so it cannot enter the regional hunger component.
   - The PS price signal is provincial, so provincial poverty can enter only the price part.
   - The municipal SAE has no municipal target to forecast. Using it in a provincial model requires aggregation (mean of 141 estimates), and the result is not an official PSA provincial figure.
3. **Thresholds are already provincial.** The PS and T43 price thresholds are each province's own 2021–2022 60th percentile, so a persistent difference in a province's level is already absorbed by its threshold.
4. **Publication timing.**
   - The SAE 2021 municipal estimates were released in 2024. The month is not verified in the repository, and the 2024 POPCEN weights later still.
   - The subsistence table carries 2024-08-15.
   - Under the as-of rule (a value enters a forecast issued at O(t) only if it was published before O(t)), poverty is unknown at every origin before mid- or late 2024. The model's training rows from 2021–2024 could not have used it.
5. **Conceptual role.**
   - Poverty measures how badly a price or hunger shock hurts households (vulnerability). It does not measure whether a shock will occur (hazard).
   - Chapter I Objective 3 assigns poverty exactly that role: "using PSA published poverty incidence and population density as vulnerability weights".

Whether poverty nevertheless adds predictive information is tested, pre-registered, in `PROTOCOL.md`.
