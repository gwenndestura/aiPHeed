# E131 data-source investigation

"Held" means the data are in the repository or in the owner's Downloads. Window: 2021+.

## Food-insecurity measurements (target candidates)

| Source | What it measures | Geography | Frequency, 2021+ | Held | Validity for E131 |
|---|---|---|---|---|---|
| **SWS involuntary hunger** | Experienced hunger, % of families | 4 areas: Metro Manila, Balance Luzon, Visayas, Mindanao | Quarterly. 20 quarters (2021-Q2 … 2026-Q3; 2022-Q1 and 2025-Q1 missing); 23 rounds with published margins. | Yes (`E110_Hunger_Generalization/data/sws_area_rounds.csv`) | **Selected quarterly target** (measured food insecurity). Not provincial. |
| OCTA "Tugon ng Masa" hunger | Experienced hunger | Balance Luzon | About 10 values, 2023–2026, from news reports | Yes (`FORECAST_RESEARCH_II/data/octa_bl.csv`) | Independent cross-check only (too short) |
| **PSA subsistence incidence (PFDR)** | Food deprivation: income below the food threshold | Province (5) and region | Survey years 2021 and 2023. **No 2025 provincial table** (owner-verified 2026-10-31). | Yes, and re-acquired from OpenSTAT with thresholds (`data/raw/psa_food_threshold_subsistence_2021_2023.csv`) | Survey-year provincial reference |
| PSA official food thresholds | Cost of a minimum food basket per person | Province | 2021, 2023 | Yes (same file) | Price side of PFDR |
| **FIES 2023 public-use file** | Household income and expenditure microdata | Province (W_PROV; Lucena separable) | 2023 | Yes (owner's Downloads, read in place, sha256 in `out/x3_inputs.json`) | Reproduces PFDR 2023 within 0–0.25 points; enables the price-versus-income decomposition |
| FIES 2021 public-use file | As above | Province | 2021 | No (PSA data archive) | Would allow a forward test, 2021 microdata → 2023 official |
| FNRI ENNS 2021 FIES | Experienced household food insecurity | Batangas, Cavite | One round | Values held | Construct cross-check |
| FNRI 2022 ENNS / 2023 NNS / 2025 survey | Experienced food insecurity | Unverified provinces (2022); region (2023, 2025) | Periodic | Regional values held | Regional context |
| CBMS 2024 FIES | Experienced food insecurity | All 142 LGUs | One window (Jul 2023 – Jun 2024) | **No** (requests unsent) | Best cross-sectional LGU check |
| SWS microdata with province codes | Experienced hunger | Province (about 20–75 respondents per round) | Quarterly | No | Too few respondents for provincial estimates |
| NNC Operation Timbang Plus | Child undernutrition | Province | Annual | No (403) | Not food insecurity |

## Predictors (five trigger groups)

| Group | Source | Geography and frequency | Held | Notes |
|---|---|---|---|---|
| A Market | PSA CPI index (`0012M4ACP22`): all items, food, rice; 18 regions; monthly 2021-01 … 2026-09 | Region → area (unweighted mean) | **Newly acquired** (`data/raw/psa_cpi_regional_2021_2026.csv`) | YoY only from 2022-01 |
| A Market | Provincial food CPI, retail and wholesale prices (E119) | Province, monthly | Yes | Used in E130 / E131 X3 |
| C Climate | ONI, El Niño flag, PAR typhoons (E119) | Global / national | Yes | No area-level series 2021+ |
| E Employment and OFW | LFS unemployment, BSP remittances (E119) | Regional / national | Yes | Provincial LFS is annual |
| N News | GDELT topic shares (E119); FSSI v3 (provincial, sparse) | National / province | Yes | — |
| V Poverty | PSA poverty incidence among the population, 2021/2023/2025, all regions and provinces | Region / province, survey years | **Newly read** from the owner's workbook (Table 2) | — |

## What changed relative to E130

- **Newly held:**
  - the official food thresholds;
  - regional CPI for all 18 regions;
  - poverty for 2021, 2023 and 2025;
  - the FIES 2023 microdata route to provincial income.
- **Confirmed absent:**
  - a 2025 provincial subsistence table;
  - any quarterly provincial income or food-insecurity series;
  - CBMS 2024 FIES.
