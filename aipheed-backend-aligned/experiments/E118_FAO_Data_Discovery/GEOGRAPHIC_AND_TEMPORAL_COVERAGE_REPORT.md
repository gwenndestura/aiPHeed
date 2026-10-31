# E118 geographic and temporal coverage (measured on acquired data; `out/acquired_coverage.csv`)

**Geography.** Province names were standardized to Cavite, Laguna, Batangas, Rizal and Quezon:
- Quezon City (NCR) is excluded;
- Lucena City (HUC) is kept separate;
- "Quezon" in poverty and FIES tables excludes Lucena.

Nothing was interpolated, and no annual value was spread into months or quarters.

## Provincial monthly and quarterly datasets (all five provinces verified)

| Dataset | Frequency | All 5 provinces | First | Latest (all provinces) | Key-item completeness | New vs aiPHeed |
|---|---|---|---|---|---|---|
| Retail prices: rice (regular-milled), chicken, pork, tilapia, tomato and others | monthly | yes | 2018-01 | 2026-09 | every published month present for rice, chicken, pork and tilapia; tomato 75%; pechay from 2022-12 only | **new** (commodity level). Retail rice YoY correlates 0.86 with A3. |
| Farmgate prices: palay, corn, livestock (household) | monthly | yes | 2010-01 | 2026-09 (livestock 2026-06) | palay 97-99% | **new** (producer side) |
| Wholesale prices: rice, fish | monthly | rice yes; fish 3 provinces | 2010-01 | 2026-09 | well-milled rice 98% | overlaps A3 |
| CPI, bottom 30% income households | monthly | yes | 2018-01 (YoY 2019-01) | 2026-09 | food group complete | **largely redundant**: food YoY r = 0.94 with all-income food CPI; mean difference 1.0 pp |
| Vegetables and root crops production (142 crops) | quarterly | yes | 2010-Q1 | 2026-Q2 | 100% of listed cells | **new** |
| Aquaculture production by species | quarterly | yes | 1996-Q1 | 2026-Q2 | 13% of species cells (most species not farmed in a province) | subsector of C4 |
| Palay / corn production | quarterly | yes | 1987-Q1 | 2026-Q3 | 100% | existing C3 |
| Fisheries production | quarterly | yes | 1993-Q1 | 2026-Q2 | 86% | existing C4 |
| Chicken and livestock production | quarterly | yes | **2023-Q1** | 2026-Q2 | 100% | new but only 14 quarters |
| NASA POWER climate (rainfall, temperature) | monthly | yes (centroid points) | 1981-01 | 2025-12 | 100% | **new**: replaces the empty rainfall column. Between-province rainfall correlation 0.78 (genuine provincial variation). |

## Provincial outcome-type measures (not monthly or quarterly)

| Measure | Years | Points per province | Precision |
|---|---|---|---|
| Subsistence incidence (families) | 1991, 2006, 2009, 2012, 2015, 2018, 2021, 2023 | 8 | CV 14-88% (Cavite 44-88%) |
| FIES food share of expenditure | 2018, 2021, 2023 | 3 | survey-based |
| FNRI FIES | 2018-19 (selected), 2021 (Batangas, Cavite, Lucena), 2023 (region only) | 0-2 | CI ± 2-5 pp |
| OPT Plus child undernutrition | annual (request) | about 10-15 | LGU completeness varies |
| CBMS FIES | 2023-24 | 1 | census-like (barangay) |

## Answers to the coverage questions

1. **All five provinces?**
   - Yes for every PSA price, production and CPI table above, and for NASA POWER.
   - No for labour-force data (national only on OpenSTAT) and remittances (national).
2. **Genuinely provincial?** Yes for prices, production, CPI and poverty. Climate points are province centroids, not provincial averages.
3. **Monthly or quarterly?** Yes for prices, production and climate. No direct food-insecurity measure is monthly or quarterly at province level.
4. **2021-2026?** Yes for all monthly and quarterly sets above.
5. **Before 2021?** Yes for most. Chicken and livestock production only from 2023.
6. **Publication dates?** Not per period; see the timing report.
