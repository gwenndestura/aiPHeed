# v9 Stage 1(c): label circularity audit protocol

**Status.** Written and hashed before any v9 label or model is scored. **DEVELOPMENT only.** All rows were seen by earlier work. No result here can support an objective being met, and no label rule is adopted by this document.

## Labels audited (existing rules, reproduced as documented, not adopted)

Rows: the 5 provinces x every quarter 2022-Q2 ... 2026-Q3 with a published SWS round (17 quarters, 85 rows; 2022-Q1 and 2025-Q1 have no round and get no label, never imputed). YoY before 2022 is excluded (lock C3, no pre-2021 base).

| Id | Rule | Source |
|---|---|---|
| L-COMP | stress = SWS_BL(q) + 2 x (food_yoy(p,q) - mean over provinces of food_yoy(q)); HIGH if stress > median of stress over all 85 rows | `label_generator._build_stress_labels` |
| L-SWS | HIGH if SWS_BL(q) > median of SWS_BL over all 85 rows | SWS component of L-COMP |
| L-CPI | flag(p,q) = food_cpi(p,q) > rolling mean + 1 SD (24-quarter window, at least 4, computed from 2021-Q1 only); HIGH if flag(q) and flag(q-1) | `label_generator._build_cpi_labels`, with the 2020 base removed (standing 2021+ rule) |

The whole-period median in L-COMP and L-SWS uses future rows. It is audited as written; it fails requirement (e) and is not proposed.

## Issue and availability (lock E1, C4)

Issue = 00:00 on the first day of dashboard quarter D; Lead k targets D - 1 + k. SWS: `published` date per round through `as_of`. Provincial CPI and rice: quarter end + 10 days (lock C4), so at issue the latest complete quarter is D - 2. Unemployment (national series): D - 2. News: quarter D - 1, complete at issue.

## Predictors (at issue)

- **CPI-derived (ablated group):** latest `food_yoy`, latest `food_yoy` minus provincial mean, `cpi_z` (food_cpi minus rolling mean, over rolling SD), latest flag, rice price QoQ change.
- **Other:** FSSI, FSSI_lag1, FSSI_accel, 5 trigger shares, unemployment, latest SWS_BL value, lead h.

F-ALL = both groups. F-NOCPI = other group only.

## Model (fixed; no tuning)

LightGBM binary classifier with the v6 regularisation (`app.forecasting.v6.lgbm.PARAMS`, objective binary), up to 200 rounds, early stopping 20 on the chronologically last 25 % of training issues, refit at the best iteration. Fewer than 30 training rows or one training class or best iteration 0: predict the training base rate. Probability cut 0.5 (fixed).

Training rows at issue I: earlier issues whose target label was final strictly before I (all SWS rounds of the target quarter published, CPI available).

## Evaluation

Target quarters 2024-Q1 ... 2026-Q3 with a label (10 quarters, 50 rows; lock E2 set S-U). Leads 1 and 2. Grid: 3 labels x 2 feature sets x 2 leads = **12 ledger trials**.

Reported per cell: n, base rate, accuracy, balanced accuracy, precision, recall, F1, AUC-ROC, PR-AUC, MCC, Brier; always-HIGH, always-LOW, persistence (latest known label at issue, per province). 95 % CI by moving-block bootstrap over target quarters (block 3, 2000 draws, seed 2026) for AUC and balanced accuracy, and for the paired difference F-ALL minus F-NOCPI in AUC.

## Mechanical predictability (no fitting)

1. Share of variance of stress between quarters (SWS, one value shared by all provinces) and within quarters (CPI deviation).
2. Share of quarters in which all 5 provinces get the same label, per label.
3. L-CPI: P(HIGH at q | flag at q-1 = 0), which the rule forces to 0; P(HIGH at q | flag at q-1 = 1).
4. Agreement of each label with its value at the latest known quarter at Leads 1 and 2 (the PERSIST rows).
5. Pairwise agreement and phi between L-SWS and L-CPI.
6. `data/thesis/panel.parquet`: whether `label_stress` equals the CPI rule as built by `build_thesis_panel.py`.

## Reading (fixed in advance)

If skill on L-CPI exceeds skill on L-SWS and ablating CPI predictors removes it, the reading is "price pressure, not hunger" (decision tree 1), at DEVELOPMENT strength only. No threshold or feature changes after seeing results; any follow-up is labelled exploratory and added to the ledger.
