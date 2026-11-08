# Deliverable 6. Feature contribution report (12 FIRI v2 families, five trigger groups)

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

**Design limit.** With five provinces per year and at most three waves, a feature-ablation experiment on provincial
outcomes has no statistical power: removing a feature from a model trained on five rows changes nothing that could be
distinguished from noise. FI12 therefore measures each feature's **rank association** with each outcome (within-year
Spearman, pooled over waves, exact p, Holm correction within outcome). This is descriptive and not causal.

## The 12 FIRI v2 families (`backend/app/ml/inference/firi.py`)
| FIRI v2 family | column tested | association with provincial outcomes [R] |
|---|---|---|
| A1 food-price-pressure forecast | FI10 forecasts; P0H4 pi_price; A1_food, A1_gap | negative on 2018/2021 food poverty; 2023 pi_price ρ 0.82 (p 0.07, one year) |
| A2 headline inflation | head_m | strongest positive: pooled ρ 0.47 (one-sided p 0.05, Holm 1.0) |
| A3 rice price | rice_m; val_A3 | negative (pooled −0.23; 2023 −0.82) |
| V1 poverty + density | poverty_inc; val_V1 | pooled +0.12; 2023 val_V1 −0.56 |
| C1 El Niño | oni / val_C1 | no provincial variation |
| C2 typhoons | tc_365d / val_C2 | no variation in PSA years; 2015 ρ 0.58; 2023 ρ 0.16 |
| C3 palay/corn | palay_yoy; val_C3 | pooled +0.29; 2023 −0.67 |
| C4 fisheries | val_C4 | 2023 only: +0.10 |
| E1 unemployment | unemp_rate / val_E1 | national: no provincial variation |
| E2 remittances | remit_yoy / val_E2 | national: no provincial variation |
| N1 FSSI / news | news_prov_z; val_N1 | pooled +0.24; val_N1 has no provincial variation |
| H1 regional hunger | val_H1 | regional: identical for all provinces |

**Five of the twelve families (C1, E1, E2, H1 and, in served rows, N1) have no provincial variation.** They are national
or regional series copied to every province. They can move all provinces together but cannot tell provinces apart.

## Five trigger groups (FI10 as-of features, annual means of Lead-1 issue rows)
| outcome | group | feature | n_years | mean_spearman | p_one_sided_positive | p_two_sided | holm_two_sided |
|---|---|---|---|---|---|---|---|
| FNRI15_SEV | market | f_m | 1.00 | -0.40 | 0.78 | 0.45 | 1.00 |
| FNRI15_SEV | market | z_food | 1.00 | -0.10 | 0.61 | 0.78 | 1.00 |
| FNRI15_SEV | market | gap_known | 1.00 | -0.20 | 0.66 | 0.68 | 1.00 |
| FNRI15_SEV | market | head_m | 1.00 | 0.40 | 0.26 | 0.52 | 1.00 |
| FNRI15_SEV | market | rice_m | 1.00 | -0.30 | 0.74 | 0.52 | 1.00 |
| FNRI15_SEV | climate | rain_anom_3m | 1.00 | 0.67 | 0.13 | 0.27 | 1.00 |
| FNRI15_SEV | climate | tc_365d | 1.00 | 0.58 | 0.20 | 0.40 | 1.00 |
| FNRI15_SEV | climate | palay_yoy | 1.00 | 0.30 | 0.34 | 0.68 | 1.00 |
| FNRI15_SEV | poverty | poverty_inc | 1.00 | 0.70 | 0.12 | 0.23 | 1.00 |
| FNRI15_SEV | news | news_prov_z | 1.00 | -0.70 | 0.93 | 0.13 | 1.00 |
| FNRI15_SEV | construct check | price_excess | 1.00 | -0.70 | 0.93 | 0.13 | 1.00 |
| FNRI15_INSEC | market | f_m | 1.00 | -0.70 | 0.93 | 0.13 | 1.00 |
| FNRI15_INSEC | market | z_food | 1.00 | -0.30 | 0.74 | 0.52 | 1.00 |
| FNRI15_INSEC | market | gap_known | 1.00 | -0.10 | 0.61 | 0.78 | 1.00 |
| FNRI15_INSEC | market | head_m | 1.00 | 0.70 | 0.12 | 0.23 | 1.00 |
| FNRI15_INSEC | market | rice_m | 1.00 | -0.40 | 0.78 | 0.45 | 1.00 |
| FNRI15_INSEC | climate | rain_anom_3m | 1.00 | 0.46 | 0.22 | 0.43 | 1.00 |
| FNRI15_INSEC | climate | tc_365d | 1.00 | -0.29 | 0.80 | 0.40 | 1.00 |
| FNRI15_INSEC | climate | palay_yoy | 1.00 | 0.40 | 0.26 | 0.52 | 1.00 |
| FNRI15_INSEC | poverty | poverty_inc | 1.00 | 0.60 | 0.17 | 0.35 | 1.00 |
| FNRI15_INSEC | news | news_prov_z | 1.00 | -0.60 | 0.88 | 0.23 | 1.00 |
| FNRI15_INSEC | construct check | price_excess | 1.00 | -0.10 | 0.61 | 0.78 | 1.00 |
| PSA_SUB_FAM | market | f_m | 3.00 | 0.20 | 0.25 | 0.50 | 1.00 |
| PSA_SUB_FAM | market | z_food | 3.00 | -0.18 | 0.72 | 0.55 | 1.00 |
| PSA_SUB_FAM | market | gap_known | 3.00 | -0.17 | 0.72 | 0.56 | 1.00 |
| PSA_SUB_FAM | market | head_m | 3.00 | 0.47 | 0.05 | 0.10 | 1.00 |
| PSA_SUB_FAM | market | rice_m | 3.00 | -0.23 | 0.77 | 0.45 | 1.00 |
| PSA_SUB_FAM | climate | rain_anom_3m | 3.00 | -0.18 | 0.72 | 0.56 | 1.00 |
| PSA_SUB_FAM | climate | palay_yoy | 3.00 | 0.29 | 0.16 | 0.33 | 1.00 |
| PSA_SUB_FAM | poverty | poverty_inc | 3.00 | 0.11 | 0.35 | 0.70 | 1.00 |
| PSA_SUB_FAM | news | news_prov_z | 3.00 | 0.24 | 0.21 | 0.42 | 1.00 |
| PSA_SUB_FAM | construct check | price_excess | 3.00 | -0.45 | 0.94 | 0.12 | 1.00 |
| PSA_SUB_POP | market | f_m | 3.00 | 0.16 | 0.29 | 0.59 | 1.00 |
| PSA_SUB_POP | market | z_food | 3.00 | -0.19 | 0.74 | 0.52 | 1.00 |
| PSA_SUB_POP | market | gap_known | 3.00 | -0.19 | 0.74 | 0.52 | 1.00 |
| PSA_SUB_POP | market | head_m | 3.00 | 0.48 | 0.05 | 0.10 | 1.00 |
| PSA_SUB_POP | market | rice_m | 3.00 | -0.21 | 0.76 | 0.49 | 1.00 |
| PSA_SUB_POP | climate | rain_anom_3m | 3.00 | -0.23 | 0.78 | 0.43 | 1.00 |
| PSA_SUB_POP | climate | palay_yoy | 3.00 | 0.27 | 0.18 | 0.37 | 1.00 |
| PSA_SUB_POP | poverty | poverty_inc | 3.00 | 0.14 | 0.32 | 0.65 | 1.00 |
| PSA_SUB_POP | news | news_prov_z | 3.00 | 0.25 | 0.20 | 0.40 | 1.00 |
| PSA_SUB_POP | construct check | price_excess | 3.00 | -0.41 | 0.92 | 0.16 | 1.00 |

## FIRI v2 values in the served P0H4 rows (2023 only)
| outcome | feature | mean_spearman | p_one_sided_positive | p_two_sided | holm_two_sided |
|---|---|---|---|---|---|
| PSA_SUB_FAM | val_A3 | -0.82 | 0.97 | 0.07 | 1.00 |
| PSA_SUB_FAM | val_V1 | -0.56 | 0.85 | 0.30 | 1.00 |
| PSA_SUB_FAM | val_C2 | 0.16 | 0.43 | 0.87 | 1.00 |
| PSA_SUB_FAM | val_C3 | -0.67 | 0.92 | 0.17 | 1.00 |
| PSA_SUB_FAM | val_C4 | 0.10 | 0.45 | 0.90 | 1.00 |
| PSA_SUB_FAM | A1_food | -0.05 | 0.55 | 0.90 | 1.00 |
| PSA_SUB_FAM | A1_gap | -0.41 | 0.78 | 0.43 | 1.00 |
| PSA_SUB_FAM | pi_price | 0.82 | 0.07 | 0.13 | 1.00 |
| PSA_SUB_POP | val_A3 | -0.70 | 0.93 | 0.13 | 1.00 |
| PSA_SUB_POP | val_V1 | -0.60 | 0.88 | 0.23 | 1.00 |
| PSA_SUB_POP | val_C2 | 0.05 | 0.47 | 0.93 | 1.00 |
| PSA_SUB_POP | val_C3 | -0.80 | 0.96 | 0.08 | 1.00 |
| PSA_SUB_POP | val_C4 | -0.10 | 0.61 | 0.78 | 1.00 |
| PSA_SUB_POP | A1_food | 0.00 | 0.53 | 0.95 | 1.00 |
| PSA_SUB_POP | A1_gap | -0.60 | 0.88 | 0.23 | 1.00 |
| PSA_SUB_POP | pi_price | 0.72 | 0.08 | 0.17 | 1.00 |

## Not testable
| feature | status |
|---|---|
| oni | no provincial variation (national or regional series) |
| remit_yoy | no provincial variation (national or regional series) |
| tc_365d | no provincial variation (national or regional series) |
| unemp_rate | no provincial variation (national or regional series) |
| val_C1 | no provincial variation or missing |
| val_E1 | no provincial variation or missing |
| val_E2 | no provincial variation or missing |
| val_H1 | no provincial variation or missing |
| val_N1 | no provincial variation or missing |

## Reading
- **No feature is associated with any provincial outcome after Holm correction** (every Holm p = 1.0).
- **Market features point the wrong way for food poverty:** food inflation excess, rice prices and the price-gap terms
  are negatively associated (realised price excess −0.45). Price pressure is highest in the more urban, less poor
  provinces. The family that drives P0H4's provincial differences is therefore the family least related to measured
  provincial food poverty.
- **Leakage and bias checks:** every feature is the as-of value used by FI10 at its issue date (FI10 as-of tests); the
  served P0H4 values are the served rows. National series copied to provinces are flagged above. SHAP was not used: with
  five observations per year no explanation of a fitted model would be meaningful.
