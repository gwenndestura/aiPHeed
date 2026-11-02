# H3 single-source LightGBM comparators (EXPLORATORY), fixed before fitting

**Written:** 2026-11-03, after the user's approval (decision 1), before either model was fitted or scored.

**Why.** Null hypothesis H3 (Chapter I §1.4) names six comparators: naive persistence; three logistic regression
variants (news-only, government data-only, combined); and **two LightGBM variants trained on only one data source at a
time**. IMPROVE_V2 already scored persistence and the three logistic regressions. The two single-source LightGBM
variants were never fitted for the food-insecurity target. They are fitted here **as comparators only**.

**They can never be selected, sealed, or replace the reference.** The forecasting result stays as final in IMPROVE_V2
(the reference arm, sealed, SHA-256 `94c62596…`). Nothing in IMPROVE_V2, HISTORY_RETRAIN or any seal changes.

**Evidence status.** Every quarter 2010–2026 was already examined (HISTORY_RETRAIN, IMPROVE_V2, earlier experiments).
These results are **development evidence**.

## Definitions

Everything not listed is **identical to the IMPROVE_V2 reference** (HISTORY_RETRAIN LightGBM (b) for T2):
- **target:** SWS Balance Luzon hunger > 11.3%;
- **training:** leads 1–15 stacked with `lead` as a column, refitted at each origin;
- **walk-forward:** expanding window, training rows q′ ≤ t − 1 with labels published before O(t);
- **model:** P0 settings (learning rate 0.05, `reg_lambda` 5, `min_child_samples` 15, seed 2027, deterministic);
- **configuration:** the unchanged 8-configuration `GRID`, chosen by the unchanged inner chronological validation (last 4 training origins, log-loss);
- **fallback:** the unchanged eligibility rule (≥ 6 quarters, ≥ 5 HIGH, ≥ 5 LOW), else the training HIGH share;
- **constraints:** none (no monotone constraints);
- **decision rule:** HIGH at P ≥ 0.50.

No tuning and no grid change. Inputs are the stored IMPROVE_V2 table `IMPROVE_V2/out/table_pooled.csv` (Balance Luzon rows), read-only.

| ID | Inputs (plus `lead`) | Training origins | Scored on |
|---|---|---|---|
| **LGBM-GOV** (government data only) | The reference's official-indicator columns **without the SWS hunger columns**: `R_food_yoy`, `R_head_yoy`, `R_rice_yoy`, `R_food_mom` (PSA CPI), `R_C3`, `R_C4` (PSA production), `ONI_last`, `ONI_max12` (NOAA ONI), `tc_mean` (IBTrACS typhoons), and the five World Bank Pink Sheet columns | From 1998-Q3, as the reference | Verdict window, targets 2010-Q1..2026-Q3 (62 quarters) |
| **LGBM-NLP** (news only) | The IMPROVE_V2 news columns: `N1R` (regional FSSI-v3), `G_pri_yoy` (GDELT), and the six E112 category shares | Rows whose origin is ≥ 2021-Q1, as the IMPROVE_V2 NLP-only logistic regression (the news does not exist earlier) | News-era quarters only (20 at Lead 1, 19 at Lead 2) |

**Why SWS is excluded from LGBM-GOV.** Chapter I's independent variables are "news-derived signals and government
socioeconomic indicators", and SWS hunger is the source of the dependent variable. The reference's inputs without the
news are the SWS hunger history **plus** the official indicators. Keeping the SWS columns would make LGBM-GOV
identical to the reference, so the comparison would be empty. NOAA, IBTrACS and the World Bank are official or
intergovernmental indicators, grouped here with the PSA series as in the reference input set.

## H3's "combined" models, as they exist

- **The proposed LightGBM that "combines news signals and government data"** is IMPROVE_V2 arm **REF+news** (already scored).
- **The carried-forward model, REF**, uses SWS hunger plus official indicators and no news.

H3 is reported for both.

- **H3's combined logistic regression:** the closest scored model is IMPROVE_V2 `LOGIT` (SWS + official indicators, no
  news). A news-plus-government logistic regression was not fitted (not approved), and this is stated as a limit.

## Comparisons (reported in `OBJ4_H3_COMPARISON.md`)

For each proposed model (REF, and REF+news) at each lead, the Brier difference against each of the six comparators:
- persistence;
- NLP-only LR, PSA-only LR and LOGIT;
- LGBM-GOV and LGBM-NLP.

Each comparison is on the quarters both models have. The p-value is one-sided, from a paired cluster bootstrap by target quarter (seed 2036, 5000 draws, as in IMPROVE_V2). **Holm correction across the six comparisons**, separately for each proposed model and lead. Full Objective-2 metrics and R1–R7 are also reported for the two new comparators.

NOTE-SHA256: b700cb45782b0cbb86512f36a2b2ee798640f7bec23f34800836a82cc08b0ca5
