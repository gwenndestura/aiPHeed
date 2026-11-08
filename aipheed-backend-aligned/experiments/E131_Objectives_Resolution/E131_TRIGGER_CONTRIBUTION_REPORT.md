# E131 trigger-group contribution report

**Method.** Ablation on the shared rows (P-DASH, Leads 1–2), removing one group at a time from LGBM-ALL and RIDGE-ALL (`out/x1_ablation.csv`). A positive ΔMAE means the model got worse without the group, so the group helped. No group was forced to contribute.

| Group | FIRI v2 families | Features | LGBM-ALL ΔMAE (L1 / L2) | RIDGE-ALL ΔMAE (L1 / L2) | Verdict |
|---|---|---|---|---|---|
| A Market and food prices | A1, A2, A3 | Area food-CPI YoY, rice-CPI YoY, relative food price (level and 4-quarter change) | −0.03 / +0.17 | −0.45 / **−2.25** | **No stable contribution.** In ridge it hurts at Lead 2. |
| C Climate | C1, C2 (C3, C4 are provincial only) | ONI, El Niño flag, PAR typhoons | +0.11 / **+0.83** | +0.07 / **+1.02** | Small help at Lead 2 in both models (28 rows; not tested for significance) |
| E Employment and OFW | E1, E2 | Unemployment rate and change, remittance decline | −0.17 / −0.14 | +0.12 / +0.11 | None |
| N News and NLP | N1 (GDELT; FSSI is provincial and sparse) | GDELT topic shares | −0.19 / −0.05 | −0.03 / +0.75 | None in LightGBM; small in ridge at Lead 2 |
| V Poverty and vulnerability | V1 | Area poverty incidence (latest PSA round) | −0.01 / +0.03 | −0.20 / −0.09 | None |
| H Hunger history | H1 | Latest reading, filtered level, area mean, horizon | — | — | **The only consistent signal**. LLM uses it alone and beats every learned model. |

## Why each group contributes so little (investigated, not assumed)

| Group | Data quality and coverage | Timing | Geography | Representation |
|---|---|---|---|---|
| A | Complete; YoY only from 2022 | Available about 10 days after each month | Area = mean of regions (Balance Luzon has 7) | The price *level* relative to all items was added for the affordability idea; no gain. In the provinces, prices explain only the price half of food deprivation, and income dominated (X3a). |
| C | Complete | — | ONI and PAR are national or global, so they work as period markers (E128 SHAP) | No area-level rainfall or typhoon series from 2021 is held |
| E | Unemployment is regional or national; remittances are national | Quarterly | **No provincial or area income series exists.** This is the binding gap (X3a: income effects up to −6 points). | — |
| N | GDELT is national; FSSI v3 is provincial but missing in 56.5 % of cases (E130) | Dated | Uneven coverage: Cavite 4.0 articles per quarter against Rizal 1.1 | E112–E113: no gain; placebo p 0.63 |
| V | Survey years only (2021 / 2023 / 2025) | Published about 8 months after the year | Region | Nearly constant across quarters, so it can only shift levels |

## Conclusion

- **All five groups were investigated with point-in-time data.** None adds stable predictive information about *measured* hunger beyond its own history.
- **The income dimension is the missing driver.** It moves provincial food deprivation most, and nothing measures it between survey rounds.
- Claiming that the five groups "drive" the forecast would be unsupported.
