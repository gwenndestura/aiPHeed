# E113 CPI validation

## 1. Data source and alignment

| Item | Detail |
|---|---|
| Series | PSA Consumer Price Index (2018 = 100), food and all-items, year-on-year %, monthly, Region IV-A (CALABARZON), inherited to the five provinces (identical values) |
| Source | PSA OpenStat table 0012M4ACP22 (`E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv`; YoY in `E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv`). Already in the repository, so no new collection (no-new-data rule). |
| Coverage | 2021-01 to 2026-09 (study window 2021+) |
| Release dates and lag | PSA publishes each month's CPI in the first week of the following month. E113 uses a conservative **day-10 rule**: month *m* counts as available from day 10 of month *m*+1. At a quarter-start issue date, months 1–2 of the just-ended quarter are available and month 3 is not. Release dates are a rule, not a recorded calendar; replacing the rule with PSA's actual release calendar is listed as missing evidence. |
| Rice | PSA wholesale regular-milled rice prices (quarterly YoY, E107 family A3). Quarter *t*−1 is treated as available at O(*t*). |
| **Not available** | National CPI; the rice/cereals CPI sub-index; CPI of NCR, Visayas and Mindanao regions. For those areas the Calabarzon series is a proxy. |
| Look-ahead check | The leakage audit raised unreleased CPI months by +50; no forecast changed (`out/leakage_audit.json`). |

## 2. Role 1: does price news track CPI? (validation of the news signal)

**Test.** Spearman ρ between quarterly Calabarzon food CPI YoY (3-month mean) and the price-news measures. A negative lag means news leads CPI. Holm correction over 40 tests (§7.5).

| News measure vs CPI | Lag −2 (news 2Q earlier) | Lag −1 | Lag 0 | Lag +1 | Lag +2 |
|---|---|---|---|---|---|
| Corpus price share vs food YoY level | 0.04 | 0.02 | −0.28 | −0.59 | −0.46 |
| Corpus price YoY vs change in food YoY | **0.47** (raw p .028, Holm .54) | 0.35 (.076) | 0.11 | −0.49 | −0.33 |
| GDELT price share vs food YoY level | 0.16 | −0.02 | −0.15 | −0.25 | −0.24 |
| GDELT price YoY vs change in food YoY | **0.70 (raw p .001, Holm .016)** | 0.18 | 0.00 | −0.11 | −0.21 |

**Result.** By the pre-registered rule, price news is **validated as a leading signal of food-inflation acceleration**:
- the **direction** of price coverage, its year-over-year change, rises about two quarters before food inflation accelerates;
- this is significant in GDELT, with the same sign in the project corpus.

**What price news does not do: track the inflation *level* at the same time.** Concurrent and lagging correlations are negative. Price stories cluster around policy events (rice tariff cut, price ceilings) that come *after* inflation peaks.

**Severity check (disaster news).** Plain disaster share vs typhoon count: ρ = 0.81. With severe headlines double-weighted: ρ = 0.80. Severe share alone: ρ = 0.73. Severity weighting adds nothing.

## 3. Role 2: does lagged CPI improve hunger forecasts? (candidate covariate)

**Test.** Same folds and rows as every other model. One-sided DM (HLN, Newey–West); Holm over the 18 CPI-family tests.

| Comparison (scaled-loss difference; negative = CPI helps) | Lead 1 | Lead 2 | Lead 3 | Lead 4 | Lead 5 | Lead 6 |
|---|---|---|---|---|---|---|
| SH-MRP vs SH-MR (CPI added to mean reversion) | +0.15 | +0.67 | +0.27 | −0.35 | −0.56 | −0.44 |
| SH-FULL vs SH-MRN (CPI added to MR + news) | +0.22 | +0.42 | +0.67 | +1.17 | +2.55 | −0.13 |
| SH-P (PSA-only) vs RW | +0.09 | +0.47 | +0.35 | +0.27 | +0.19 | +0.22 |
| Holm p (all 18) | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

**Placebo.** Shuffling the CPI and rice features across quarters gives *better* forecasts than the real values (permutation p = .97).

**Result.** **Lagged CPI does not improve hunger forecasts at any lead; it usually makes them worse.**

## 4. Role 3: are forecast errors larger in high-inflation quarters? (regime check)

**Definition.** High inflation = target quarter's Calabarzon food YoY in the top tercile of 2021–2026 (≥ 5.29%). Among evaluated targets these are 2023-Q1 to 2023-Q3; they enter only the Lead-1 and Lead-2 evaluations.

| Lead | High-inflation rows | Persistence scaled error, high | Other | Mann–Whitney p |
|---|---|---|---|---|
| 1 | 12 | 0.96 | 1.31 | .50 |
| 2 | 4 | 1.20 | 1.46 | 1.0 |
| 3–6 | 0 | — | — | — |

**Result.** Errors are **not** larger in high-inflation quarters. The largest errors came in 2024–2026, when Calabarzon food inflation was moderate to low (0.9–5.1%). This is consistent with E108–E112: hunger and food inflation moved apart after 2023.

## 5. Conclusion

| Role | Answer |
|---|---|
| Validation of price news | **Partly validated.** The direction of price coverage leads food-inflation changes by about two quarters (GDELT, Holm p = .016). Concurrent levels do not agree. |
| Forecast covariate | **No value.** No gain at any lead (Holm p = 1); worse than shuffled values. |
| Regime check | No high-inflation error regime |

CPI stays out of the adopted forecast and is **not** used as the outcome (E112 decision kept). It can be shown to DA IV-A as **context**: the food-price environment, labelled as separate from hunger.
