# OPTION_1, Step 3: data check (food poverty and news), before any PLAN or build

**Nothing was filled, interpolated or downloaded.** This lists what the repository holds.

## 1. PSA food poverty (subsistence incidence), province level

**Families basis** (PSA Full Year Official Poverty Statistics, Table 3; OpenStat PXWeb DB__1F__FY):
- `backend/data/processed/psa_subsistence.parquet` (2018, 2021, 2023, with CV, CI and PSA's usable flags);
- `LEAD2_RELIABILITY_RESEARCH/y14_food_insecurity_forecast/data_acquired/subsistence_families_2006_2015.csv` and
  `..._2018_2023.csv`.

Subsistence incidence among families, % (CV %):

| Province | 2006 | 2009 | 2012 | 2015 | 2018 | 2021 | 2023 |
|---|---|---|---|---|---|---|---|
| Batangas | 3.7 (20) | 4.1 (35) | 5.8 (24) | 1.6 (34) | 1.1 (26) | 0.6 (35) | 0.8 (34) |
| Cavite | 0.2 (69) | 0.0 (–) | 0.4 (88) | 0.9 (44) | 0.9 (33) | 1.5 (32) | 0.4 (53) |
| Laguna | 1.1 (38) | 0.8 (48) | 1.2 (40) | 0.8 (47) | 0.2 (59) | 1.5 (24) | 0.8 (35) |
| Quezon | 6.5 (19) | 5.0 (31) | 4.6 (24) | 4.9 (40) | 2.6 (23) | **4.7 (17)** | **0.5 (39)** |
| Rizal | 1.1 (71) | 1.2 (41) | 1.3 (41) | 0.6 (51) | 0.7 (37) | 0.6 (34) | 1.5 (25) |
| CALABARZON | 2.3 | 1.9 | 2.3 | 1.6 | 1.0 | 1.6 | 0.8 |

**Population basis:** `backend/data/inputs/psa_subsistence_population_2021_2023.csv`, published 2024-08-15, acquired in
E54, not re-verified online (E109).

| Province | 2021 | 2023 |
|---|---|---|
| Cavite | 2.4 | 0.8 |
| Laguna | 2.4 | 1.3 |
| Quezon | 6.6 | 0.9 |
| Rizal | 0.9 | 2.6 |
| Batangas | 1.0 | 1.4 |

CVs are 17–62%.

**Gaps and cautions:**
- **Years.** The figures are triennial (latest 2023). There is no annual or quarterly value, and none is interpolated.
- **Precision.** In 2023, 4 of the 5 provinces have a CV above 30%. PSA marks such estimates unfit for ranking
  (`usable_for_validation` = False in the parquet). Only Rizal is usable in 2023.
- **The rank is not stable.**
  - 2021: Quezon is clearly highest (4.7%, CV 17).
  - 2023: Quezon is lowest (0.5%), and Rizal is highest (1.5%).

  A province "food-poverty rank" therefore depends on the year chosen, and most differences are inside the sampling
  error.
- **Two bases.** There are two bases (families and population) with different values. One must be chosen.

## 2. PSA food poverty, the 142 cities and municipalities

**Not available.** No city or municipal **subsistence** (food poverty) incidence exists in the repository.

The only municipal Small Area Estimate is **general poverty incidence, 2021**:
- `backend/data/reference/sae2021_calabarzon_municipal.csv`, PSA 2021 City and Municipal Level SAE (no-HUC table);
- 141 LGUs, with CV and 90% CI;
- **Lucena City is missing** (a highly urbanized city, excluded from that table), so the backend uses the Quezon
  province value for it.

**So the Step 4 LGU ranking "food poverty 60% + density 40%" cannot be built from municipal food-poverty data.** The
choices, which are yours:
- **(a)** Give every LGU its province's subsistence incidence. The order inside a province then comes from density
  alone, and the food-poverty term only shifts whole provinces.
- **(b)** Keep general poverty (SAE 2021) as the LGU term, and report food poverty at province level only.
- **(c)** Obtain a PSA municipal food-poverty source, if one exists. I know of none in the repository and have not
  searched online.

## 3. News outputs per province-quarter

| Output | Geography | Period | Coverage | File |
|---|---|---|---|---|
| **FSSI-v3** (bias-corrected XLM-RoBERTa intensity) | **Province** | 2021-Q1..2026-Q3 (23 quarters, 115 province-quarters) | **SUFFICIENT (≥ 5 articles) in 20 of 115 (17%)**; 42 limited; 53 no usable evidence. SUFFICIENT provinces per quarter: none before 2022-Q4; at most 4 (2025-Q3, 2026-Q3) | `backend/app/news/pipeline_v3`, measured in `../OBJECTIVES_COMPLETION/out/obj1_news_measures.json` |
| **N1R** (regional FSSI-v3) | Region | 2021-Q1..2026-Q3 | 16 of 23 quarters; missing 2021-Q1, Q2, Q4, 2022-Q1, Q2, 2023-Q3, 2025-Q2 | same |
| **E112 event-category shares** | **Region only (no province column)** | 2021-Q1..2026-Q4 (24 quarters, 147–881 headlines each) | **Six** categories, not five: price, shortage, disaster, agricultural supply, jobs and income, assistance. Plus their year-on-year changes. No gaps | `../E112_Food_Insecurity_Forecasting/out/news_quarterly_corpus.csv` |
| E112 GDELT category shares | Region (CALABARZON-located GKG) | 2021-Q1..2026-Q4 | Same six categories; no gaps | `.../news_quarterly_gdelt.csv` |
| **E85 GDELT event features** | **Province** | 2021-Q2..2026-Q3 (22 quarters × 5 provinces = 110) | Complete. Log volume, tone, "affected", and shares and changes for PRICE, FOODSEC, DISASTER, AGRI, LIVELIHOOD, RESPONSE | `../E85_GDELT_Events/runs/20261021T101520Z/gdelt_features_k1.csv` |
| GDELT price-news YoY (`G_pri_yoy`) | Regional / national | 2021+ | Model input of REF+news | IMPROVE_V2 table |
| BERTopic | Province | 120 province-quarters | Descriptive only; not a forecast input | `backend/data/news_v3/` |

**For the planned news explanation sentence and early-warning flag:**
- A **province** sentence from the project's own event categories is not possible: the E112 shares are regional.
- **Province-level news categories exist only from GDELT (E85)**, with complete coverage 2021-Q2..2026-Q3.
- **Provincial FSSI-v3 is too sparse** for a per-province flag (17% sufficient). Regional N1R covers 16 of 23 quarters.

The choice of source, and of the history window and threshold for "rises sharply", goes into PLAN.md after your OK.
