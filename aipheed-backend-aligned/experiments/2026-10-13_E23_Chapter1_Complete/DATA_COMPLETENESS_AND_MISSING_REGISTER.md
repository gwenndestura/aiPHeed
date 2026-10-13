# Data inventory, completeness and missing-data register

**Machine-readable outputs:**

- `data_inventory/file_inventory.csv`: all 157 data files with size, mtime and SHA-256, and whether their content was read;
- `data_inventory/completeness_report.json`: province × quarter matrices;
- `rankings/ranking_verification.json`.

**Expected coverage:** 5 provinces (Cavite, Laguna, Batangas, Rizal, Quezon) × 2021-Q1…2026-Q4 = 120 province-quarters; 142 LGUs.

**Is the data complete for the claims made?** Only for the back-test claims in 2021–2025, with the gaps below. It is **not complete for a 2027-Q1 forecast.**

## Missing-data register

| # | What is missing | Quarters | Provinces / LGUs | Field(s) | Why | What would resolve it |
|---|---|---|---|---|---|---|
| M1 | Supporting news for the 2027-Q1 forecast | 2026-Q4 (Oct 1 – cutoff) | all 5 | articles, FSSI, triggers | Not authorized. The quarter is also only 13 days old. | Your authorization of a 2026-Q4 news file, collected with verified publication timestamps |
| M2 | News features | 2026-Q1…Q3 | all 5 | FSSI, lags, accel, 5 triggers | 2026 news not authorized | Authorization plus a rebuild under the PHT fix (F1) |
| M3 | Government features (t−1) | 2026-Q1…Q3 | all 5 | 36 government features | Not authorized past 2025-Q4 (in features); July–December 2026 protected | Authorization of the 2026 PSA/BSP/DOE/PAGASA series |
| M4 | Provincial food CPI | 2026-Q3, 2026-Q4 | all 5 | food CPI YoY (monthly) | July–December 2026 protected | Authorization (and publication, for Q4) |
| M5 | SWS hunger | 2026-Q3 (Sept round), 2026-Q4 | region | H | Protected (Q3); not yet fielded or published (Q4) | Authorization after the forecasts are frozen |
| M6 | Labels (no production SWS round) | 2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3 | all 5 | S1, y | No production-definition round. Supplementary 2025-Q2/Q3 rounds exist but use a different respondent base. | Adviser decision (D3) on whether supplementary rounds may define a label |
| M7 | Government t−1 values | 2021-Q1 rows | all 5 | 36 features | 2020-Q4 is outside the approved window | None needed: left missing by design |
| M8 | Provincial unemployment | all | all 5 | unemployment_rate | PSA LFS publishes no provincial quarterly table | None (documented limitation) |
| M9 | LGU-specific poverty | 2021 SAE | **126 of 142 LGUs** | poverty_incidence | PSA SAE table lacks these LGUs; the province mean is used | A PSA SAE release with municipal coverage, or the RSSO IV-A tables (site behind Cloudflare; not bypassed) |
| M10 | Verified provincial CPI release dates | 2021–2026 | all 5 | availability time | RSSO IV-A pages are not machine-readable; the national date + 14 days proxy is used in earlier studies | Manual verification of RSSO IV-A releases |
| M11 | NNS 2019 CALABARZON prevalence | 2019 | region | FIES % | Not located in a primary source; the 2018–2019 ENNS used HFIAS | FNRI regional table, or drop the 2019 anchor |
| M12 | Independent provincial food-insecurity outcome | all | all 5 / all LGUs | FIES by province | Not published by FNRI below region | FNRI microdata, CBMS, or a DA/LGU FIES module |
| M13 | Promoted forecasting model | — | — | model artifact | No lead met the frozen reliability rule | New evaluable quarters (see the final report) |

## Source acquisition checklist (per quarter)

| Source | Series | Expected release | Granularity | Needed for |
|---|---|---|---|---|
| Philippine news (RSS, Google News, GDELT) | Articles with original publication time | Continuous | Article | FSSI and triggers of the reference quarter |
| PSA OpenStat 0012M4ACP23 | Provincial food CPI (monthly) | ~5th of the following month (national); provincial later | Province-month | D, cpi_dev, label |
| PSA OpenStat 0012M4ACP22 | Headline / food CPI | Same | Region-month | Government features |
| SWS | Hunger (Balance Luzon) | 1–3 months after fieldwork | Region-quarter | SWS feature, label |
| PSA LFS | Unemployment | Quarterly | National | Government features |
| BSP | OFW remittances, USD/PHP | Monthly | National | Government features |
| DOE | Diesel, gasoline prices | Weekly | National | Government features |
| PAGASA / NOAA / IBTrACS / POWER | Typhoons, rainfall, ENSO, drought | Monthly | Province or national | Government features |
| PSA SAE / census | LGU poverty, population, land area | Multi-year | LGU | Rankings |

**For every source, record:** the original publication date, the observation period, the retrieval time, the SHA-256 (computed) and the authorization.
