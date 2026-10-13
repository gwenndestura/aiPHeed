# Data Gap Inventory (E15)

**Basis:** records and code only.

**No data was fetched, and no data file was opened for this inventory.** Sources:

- project fetcher docstrings in `app/ml/corpus/*.py`;
- `docs/DATA_AVAILABILITY.md` and `docs/DATA_COMPLETENESS_AUDIT_2026-10-09.md`;
- the E9 data-eligibility document;
- the E13 outcome audit, including its two DOST-FNRI-restricted web searches.

**Nothing here is added to any model in this run.**

**"Collectable without protected values"** means that the historical values (through 2025) can be obtained with a query or request restricted to periods up to 2025, without opening 2026 SWS rounds or provincial food-CPI values. It also requires that no existing project file that may contain 2026 rows is opened.

## 1. Candidate independent provincial outcomes

| Candidate | Source | Geography | Frequency | Publication lag | Eligible history in 2021–2025 | Usable as an outcome? | Periods needed for validation | Collectable without protected values? |
|---|---|---|---|---|---|---|---|---|
| **Provincial FIES or HFIAS** (household food insecurity) | DOST-FNRI ENNS 2018, 2019, 2021 (rolling design; provincial weights in the public-use files) | Province or HUC | **Once per province per cycle** (each province in one of the three years) | About 1–2 years | At most one 2021 value, only for provinces in that year's replicate. Not in the project. | **Not for temporal validation** (one point per province). At most one cross-sectional check. | At least 5 to 8 repeated periods per province. Annual is the minimum useful frequency. | Yes. Microdata request to FNRI. |
| FIES moderate or severe | FNRI NNS 2023, 2025 | **Region** (designed for national and regional estimates) | Biennial | About 6–12 months (2025 released 17 June 2026) | 2025 regional only (22.6%, secondary source). The project file repeats it for 5 provinces. | **No** for provinces | — | Regional value: yes |
| **Subsistence incidence** (income below the food threshold) | PSA Full Year Poverty Statistics | Province, region | Triennial (2018, 2021, 2023) and 2025 | About 8 months | 2021, 2023 (5 provinces each). CV 17–53%; only 3 of 10 below 30%. The 2025 values were released 2026-08-21 and are **not in the project**. | **No** for validation: too few periods, too imprecise, and income-based | At least 5 periods with CV < 30% | 2021 and 2023: in the project. 2025: published after the data cutoff, so it needs an explicit eligibility decision. |
| **CBMS household food-shortage items** | PSA Community-Based Monitoring System (RA 11315) | Barangay or municipality, aggregable to province | Per round (rollout from 2022; schedule not verified) | Not verified | Not in the project. CALABARZON coverage **not verified**. | **Potentially the best provincial outcome**, if rounds repeat and cover all five provinces | At least 5 rounds | Yes, by request (PSA or LGUs) for rounds up to 2025 |
| Child undernutrition (OPT Plus) | National Nutrition Council | Province, municipality | Annual | About 6–12 months | Not in the project | **Supporting only.** It measures nutrition, not food insecurity, and depends on weighing coverage. | At least 5 years | Yes, by request |
| DSWD registries (Listahanan, 4Ps, Walang Gutom) | DSWD | Household, municipality | Irregular or administrative | Varies | Not in the project | **No.** They reflect programme eligibility and reach, not prevalence. | — | — |
| **A DA- or LGU-run FIES module** (8 standard FAO questions) | New collection | Province (or lower) | Quarterly or semi-annual is feasible | Weeks | None yet | **Yes, if designed for it.** This is the cleanest route to an independent provincial outcome. | 8 or more periods for a temporal check | Prospective only (nothing historical) |

## 2. Candidate provincial drivers

| Driver | Project source (code) | Geography | Frequency | Lag | Known coverage and gaps (records) | Periods needed to test added value | Collectable without protected values? |
|---|---|---|---|---|---|---|---|
| **Rice price** (regular milled, wholesale) | `psa_rice_fetcher.py`: PSA OpenStat `0052M4AWB01`, 2010 to present | Province | Monthly → quarterly | About 1 month | **No value** for Laguna 2022-Q3, Quezon 2024-Q1 and 2024-Q2 (suppressed). Wholesale runs about PHP 3–6/kg below retail. | Training of at least 6 quarters (have 20), plus **12 new quarters** prospectively (as for H1) | Yes, with a query restricted to ≤ 2025-12. **The existing `psa_rice_prices.parquet` was not opened** (it may hold 2026 rows). |
| Other staples (corn, fish, vegetables, pork, chicken) | `commodity_prices_fetcher.py`: PSA NRP retail tables | Province | Monthly | About 1 month | **The NRP series ends in 2021.** No 2022–2025 values in the project. A wholesale successor table is not verified. | As above | Yes, if a current PSA table exists (not verified) |
| **Typhoon exposure** | `pagasa_climate_fetcher.py`: NOAA IBTrACS storm tracks matched to provinces (`tc_count`, `tc_max_signal`) | Province | Event → quarterly | Days | Continuous archive. The E9 records note a zero-fill issue in the fused feature table. | Event-driven, so it needs **several typhoon quarters**: at least 12 new quarters | Yes, with a query restricted to ≤ 2025 |
| Rainfall anomaly | NASA POWER, interior points per province (`build_province_rainfall.py`) | Province | Monthly → quarterly | Days | Measured. Same zero-fill caveat. | At least 12 new quarters | Yes |
| ENSO (ONI) | NOAA CPC | Global index | Monthly | About 1 month | Continuous | Regional effect only. Not a provincial differentiator. | Yes |
| **Crop or agricultural damage** | **No fetcher in the code** | Province or municipality (DA DRRM / NDRRMC reports) | Event-based | Days to weeks | **Not in the project** | At least 12 new quarters, including damage events | Yes, from historical reports up to 2025 |
| Unemployment | `openstat_fetcher.py`: LFS `0021B3GKEI2` | **National**, interpolated to the provinces | Quarterly | About 6 weeks | Not provincial, so it gives **no provincial differentiation** | — | Yes |
| Provincial labour-force estimates | Not in the code (PSA provincial LFS; availability **not verified**) | Province | Annual (if published) | Not verified | Not in the project | At least 5 years | To be checked |
| OFW remittances; USD/PHP | `bsp_macro_fetcher.py` (remittances curated to 2025-Q4; FX live) | National | Quarterly | About 6 weeks | National only | — | Yes |
| Fuel prices | `oil_price_fetcher.py` (Brent live; DOE pump prices curated to 2025-Q4, with NCR as a proxy) | National (NCR) | Quarterly | Days | National only | — | Yes |
| Poverty incidence | `openstat_fetcher.py`: `0011E3DF010` | Province | Triennial | About 8 months | 2018, 2021, 2023 | Too few periods for a quarterly driver | Yes, up to 2023 |
| Population and density | `lgu_census_fetcher.py`: CPH 2020 | LGU | Census | — | Static | Static weight only, for example a population-weighted mean in place of the unweighted one | Yes |

## 3. Most feasible

1. **Independent outcome:**
   - **Short term:** obtain the **FNRI provincial FIES/HFIAS microdata** (2018, 2019, 2021) and **CBMS food-shortage rounds**. They give a cross-sectional check and possibly a few repeated points.
   - **Durable:** a **DA- or LGU-run FIES module**, collected at least twice a year in all five provinces. It is the only option that would allow a temporal validation within a few years.
   - **Provincial subsistence incidence** remains a descriptive comparison only.
2. **Driver:** **provincial rice prices** come first. The fetcher exists, the data are province-level and monthly, and the three suppressed quarters are documented. **Typhoon exposure** comes second. Both can be collected for 2021–2025 with period-restricted queries, without opening any file that may contain 2026 values.
3. **Every driver needs prospective testing** of at least 12 new quarters (the H1 minimum) before any claim of added value. The 2021–2025 quarters have all been examined.
