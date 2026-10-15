# E43 protocol: five-trigger food-insecurity-risk forecast at Lead 2 (frozen before any E43 model is fitted)

**Written:** 2026-10-15 on branch `e43-five-trigger-risk` (from `e42-lead2-improvement` @ bd4038f).
**Freeze:** the SHA-256 of this file (LF) is in `runner/PROTOCOL_SHA256.txt`, committed before any E43 model is fitted. The runner refuses to run if the file changed.
**Run rule:** run once, then a byte-identical repeat. Deviations go to `DEVIATIONS.md`.

## 0. Scope correction and what is known before any model

- **Chapter I §1.7:** "SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk."
  - E41/E42 forecast **food price pressure only**. They are audit evidence, not the system definition.
- **Chapter I** names "trigger composition scores" and data "from PSA, DOST-FNRI, SWS, PAGASA, PhilRice, BSP and DOE" (§1.7). It does not list the five triggers.
- **The five triggers are defined in the repository:**
  - `backend/app/ml/nlp/trigger_classifier.py`: news keyword taxonomy (HungerGist 8+2), groups `market`, `climate`, `employment`, `ofw_remittance`, `fish_kill`.
  - `backend/app/ml/inference/e20_forecast.py` `DRIVER_GROUP_FEATURES`: groups government features with them (market: CPI and rice; employment: unemployment).
- **Correction to E41/E42.** They said climate and OFW data were not obtainable in-window. In fact the repository holds in-window files whose metadata show 2021-Q1..2026-Q3 only:
  - `aipheed-backend-aligned/data/processed/pagasa_climate.parquet`. Despite its name, it holds NOAA IBTrACS typhoon tracks within 300 km of each province centroid, plus NOAA CPC ONI ENSO.
  - `bsp_macro.parquet`: national OFW cash remittances curated from BSP releases, 2021–2025, plus the USD/PHP rate.
  - `psa_rice_prices.parquet`: PSA provincial wholesale rice price.
  - `province_rainfall.parquet` starts in 1991 and is **never loaded** (study-window rule).
- **Label diagnostics** (`runs/labels/label_diagnostics.json`; no model fitted):

| Label | HIGH share | HIGH quarters | Provinces differ | Note |
|---|---|---|---|---|
| E40 as frozen (sustain-2) | 5% (5/95) | 3 (2024-Q3..2025-Q1) | – | none usable for training before 2024 |
| Hunger only | 63% | – | never | identical for all provinces |
| **L3** (E40 signals, single quarter) | 19% | 7 | in 7 of 19 quarters | |
| **L4** (H > 11.3 and food YoY > 4%) | 23% | 9 | in 9 of 19 quarters | |

- **v1 (served) root causes** were established in E41/E42 audits: a relative trailing median, drift of the regional H, and HIGH even with food inflation below 4% in 50% of HIGH rows.
- **Evidence status:** every quarter from 2021 to 2026-Q3 has been examined by earlier experiments, and the E40 holdout is exposed (E41 C-1). E43 results are development evidence. Independent confirmation is prospective (§8).

## 1. Target (chosen for meaning, before any model)

**Primary T43 = L3, "concurrent elevated reported hunger and food-price pressure".**
- **Rule:** a province-quarter is HIGH if `sws_hi AND (cpi_hi OR gap_hi)` in that quarter. The signals and their frozen 2021–22 P60 thresholds are exactly E40's (`E40_SWS_CPI_Tiers/label_spec.json`):
  - `sws_hi`: H > 11.3;
  - `cpi_hi`: food YoY above the province's own window P60;
  - `gap_hi`: food minus headline above the province's own window P60.
- **The only change from E40:** the sustain-2 rule is dropped. It gives 5 HIGH rows in 3 quarters and none usable before 2024, and a Lead-2 forecast of a two-quarter conjunction is a different event. **This change needs adviser approval.**
- **Missing data:** quarters with no approved SWS round have no label; they are never zero-filled.
- **What it measures:** an exploratory food-stress outcome built from SWS hunger (regional) and PSA food prices (provincial), the two sources §1.7 names. **It is not independently verified household food insecurity**, and SWS is never presented as provincial.

**Secondary T43b = L4** (H > 11.3 and food YoY > 4.0%): the same models, reported as sensitivity.

**DA display:** an ordinal version (HIGH = both signals, WATCH = one, LOW = none), observed only.

## 2. Timing (Lead 2)

| Element | Rule |
|---|---|
| Origin | O(t) = first day of quarter t+1 |
| Target | quarter t+2 |
| CPI | months up to month 2 of t |
| SWS | rounds posted before O(t) |
| PSA production, rice wholesale, LFS, OFW remittances, USD/PHP | quarters ≤ t−1 |
| Typhoon tracks | quarter ≤ t (event record observed in real time through PAGASA bulletins; IBTrACS is the archive) |
| ONI ENSO | quarters ≤ t−1 (published about a week after the season ends) |
| News and FSSI-v2 | quarter ≤ t |

**Training pairs:** `(X(t'), T43(t'+2))`, used only if every approved SWS round of t'+2 was posted before O(t) and all three CPI months of t'+2 were published before O(t).

**Study window:** no value before 2021-01 is read. This is asserted, and parquet metadata are checked before loading.

## 3. Features by trigger (as of O(t); missing values stay NaN)

| Trigger | Government features | News (NLP) features |
|---|---|---|
| Market / Prices | F_last, F_now, gap_now, mom3, F_hat_M1, D_now, rice_whsl_yoy (PSA wholesale rice, t−1 vs t−5) | news_market |
| Climate Stress | tc_count, tc_max_signal, tc_severe (quarter t, province); enso (ONI phase t−1: El Niño +1, neutral 0, La Niña −1); palay_yoy, corn_yoy (t−1) | news_climate |
| Fish Kill | fish_yoy, aqua_yoy (PSA, t−1) | news_fish_kill |
| Employment | ur_last, ur_yoy, under_last (PSA LFS, **national**) | news_employment |
| OFW Remittance | remit_usd_yoy (BSP, **national**, curated, t−1); fx_yoy (USD/PHP, t−1) | news_ofw_remittance |
| Hunger history (not a trigger; the target's own component) | H_last, H_chg, H_age | – |
| News totals | – | news_n, fssi_v2, fssi_admitted |

- **GOV** = government columns of the five triggers + hunger history.
- **NLP** = all news columns.
- **COMB** = GOV + NLP.
- `gap_now` is kept, but `HL_now` is dropped: E42 found exact collinearity of the gap with food and headline.

## 4. Models for T43 at Lead 2 (fixed now)

**Baselines:**
- **B-maj:** training majority class; p = training HIGH rate with a Laplace correction.
- **B-persist:** the latest T43 label available at O(t) for the province.
- **B-clim:** the province's training HIGH rate (Laplace).

**Structural (interpretable):**
- **SIM-0:** the E41 component simulation applied to the single-quarter rule at t+2.
  - Price: E41 M1 random walk with drift, bivariate food and headline.
  - Hunger: H random walk from the last approved round.
  - 20,000 paths; seed 43.
- **SIM-5T:** SIM-0, except the hunger path's mean change is a ridge regression (α = 1.0, standardized) of the per-quarter H change on the as-of trigger signals [tc_count (regional mean), enso, ur_yoy, remit_usd_yoy, fx_yoy, F_now (regional mean), news_n].
  - It is fitted on earlier origins whose H change was posted before O(t) (at least 8 pairs; otherwise zero mean change, which equals SIM-0).

**Machine learning (Chapter I's proposed LightGBM and its logistic baselines):**
- **LR-GOV, LR-NLP, LR-COMB:**
  - L2, C = 0.5, `class_weight='balanced'`, standardized;
  - median imputation plus missing indicators.
- **LGBM-GOV, LGBM-NLP, LGBM-COMB:**
  - num_leaves 4, max_depth 2, min_child_samples 5, n_estimators 100, learning_rate 0.05, reg_lambda 5.0;
  - `scale_pos_weight = (1−p)/p`, seed 42, deterministic;
  - NaN passed through.
- **Withholding:** fewer than 6 distinct training target quarters, or fewer than 5 HIGH training rows → no forecast.

**PRIMARY = LGBM-COMB**, the five-trigger LightGBM combining government data and news (Chapter I's proposed model).

**Comparison arms scored on T43 rows:**
- **E38-served:** the served v1 LightGBM's lead-2 probability, from E38's outer predictions.
- **E41-M1:** P(food YoY > 4%), price-only.

These are scored as forecasts of T43 for comparison only.

**Trigger tests** (common set S-C, secondary, nothing chosen from them):
- single-group and leave-one-group-out models (LR and LGBM);
- grouped permutation importance (200 draws);
- grouped SHAP;
- missing-group sensitivity (Δp when a group is set to missing);
- redundancy (|r| ≥ 0.8).

## 5. Evaluation sets

- **S-C:** targets where every §4 arm forecasts. All headline comparisons and gates use S-C.
- **S-SIM:** every target where SIM-0 forecasts (longer history), for the structural arms and baselines.

**Metrics:**
- accuracy, balanced accuracy, precision, recall (HIGH and LOW), F1, confusion matrix;
- ROC-AUC and PR-AUC (with prevalence) when both classes are present;
- Brier, log loss;
- calibration-in-the-large and slope;
- per province and per year.

**Uncertainty:** date-cluster bootstrap (B = 2000, seed 43); paired per-date sign-flip tests with Holm correction.

## 6. Gates for the primary (LGBM-COMB) on S-C

| Gate | Rule |
|---|---|
| G0 | leakage, alignment, window and label tests pass |
| G1 | accuracy ≥ 0.75 |
| G2 | balanced accuracy ≥ 0.70, and HIGH and LOW recall ≥ 0.60 |
| G3 | per-date Brier better than B-maj and B-persist (point estimates), and the gain over B-persist has Holm p < 0.05 |
| G4 | the 95% CI of calibration-in-the-large contains 0 |

**Classification:**
- all gates pass → "suitable for exploratory decision-support testing";
- G0 and G3 pass → "ready for a controlled demonstration; Lead-2 operational use remains experimental";
- otherwise → "insufficient evidence for Lead-2 operational use".

**Serving rule** (fixed now, disclosed as a post-evaluation choice):
- The E43 candidate served behind `AIPHEED_LEAD2_MODEL=e43` is the primary if its S-C per-date Brier is below both B-maj and B-persist.
- Otherwise it is whichever of SIM-5T or SIM-0 has the lower S-SIM Brier, with status "experimental".
- Baselines are never served as the model.
- The default stays E38.

## 7. Outputs (documented, not tuned)

- **Forecast:** P(T43 HIGH in the target quarter). The band is Low (< 0.33), Watch, or High (≥ 0.67).
- **Observed evidence**, each with source, level, reference period and age:
  - SWS H vs 11.3;
  - provincial food inflation vs the province's P60 and vs 4%;
  - typhoons, ENSO, palay/corn and fisheries changes;
  - national unemployment;
  - national OFW remittances and USD/PHP;
  - news shares.
- **Trigger status:**
  - `contributes`: the group has model input and non-zero attribution;
  - `no_effect`;
  - `data_not_in_model`;
  - `no_model_input`;
  - `no_data`;
  - `stale`: the latest observation is more than 2 quarters old at the origin.
- **No municipal probabilities.** LGU rankings stay relative prioritization (Objective 3).

## 8. Prospective freeze

From O = 2026-10-01: every §4 arm's 2027-Q1 forecast, plus the served candidate, written to `frozen/E43_PROSPECTIVE_2027Q1.json` with a sha256.
