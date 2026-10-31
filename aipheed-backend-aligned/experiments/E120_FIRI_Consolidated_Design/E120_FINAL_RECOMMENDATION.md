# E120 final recommendation

**Status.** A design for review. FIRI v2 stays served and unchanged until the owner approves a replacement. No model was trained, and production, the API and the dashboard were not modified. Local commit only.

## 1. Recommendation

**Six consolidated indicators.** The proposed structure is kept, with Indicator 6 redefined:
- SWS hunger leaves the index;
- remittances move to Indicator 4.

| # | Indicator | Definition (short) |
|---|---|---|
| 1 | Food Market Accessibility and Affordability (FMA) | Year-on-year price pressure on food and household necessities |
| 2 | Agricultural and Fisheries Production (AFP) | Fall in local food output by commodity group |
| 3 | Climate and Environmental Conditions (CEC) | Weather exposure: rainfall departures, heat, nearby cyclones |
| 4 | Employment and Household Economic Stability (EHS) | Unemployment and underemployment; nationally, job and remittance shocks |
| 5 | Household Poverty and Social Vulnerability (PSV) | Structural poverty (with food poverty, food share and density as profile) |
| 6 | Food Insecurity Early-Warning Signals (FIS) | News-reported food stress (FSSI-v3, GDELT shortage share) |

## 2. Features under each indicator

| Indicator | Provincial FIRI (scored) | Regional FIRI (scored) | Profile, context or alternative (not scored) |
|---|---|---|---|
| FMA | CPI food YoY; CPI headline YoY; wholesale rice YoY; retail chicken, pork, tilapia YoY | Region IV-A CPI food and headline YoY; farmgate palay YoY (Region IV-A) | Bottom-30% CPI; retail rice; farmgate palay (provincial); vegetable and root-crop prices; farmgate hog |
| AFP | Palay, corn, vegetables, root crops, fisheries, chicken, livestock production drop | Same groups, Region IV-A rows (except chicken and livestock) | Aquaculture (part of fisheries) |
| CEC | Absolute rainfall departure; temperature anomaly; cyclones within 100 km | Same for the CALABARZON proxy; cyclones in PAR | Rainfall total; cyclones within 300 km; ONI and PAGASA El Niño advisory |
| EHS | Annual provincial unemployment and underemployment (latest published year) | National unemployment change; national remittance decline | Unemployment level |
| PSV | Poverty incidence (SAE 2021, population-weighted; from 2025-07-01) | — (no regional series) | Subsistence incidence (CV > 20%); FIES 2023 food share (undated); density |
| FIS | FSSI-v3 (≥ 5 articles) | GDELT shortage share | Agri-supply, jobs-income and assistance shares; article counts |
| Outside the FIRI | — | — | SWS Balance Luzon hunger (target); FIRI v2 A1 (model output) |

**Datasets per feature** are in `E120_FEATURE_DICTIONARY.csv` (dataset_id and source). **The mapping of all 54 datasets** is in `E120_DATASET_TO_INDICATOR_MAPPING.csv`.

## 3. Method

1. **Feature (Level 1).**
   - Take the as-of value at the issue date from 2021+ observations; it must be at most 3 quarters old.
   - Align the direction (production and remittances reversed; rainfall as the absolute departure).
   - **Dynamic features:** expanding-window mid-rank percentile against the feature's earlier available observations (≥ 8).
   - **Annual and structural features:** mid-rank among the five provinces for the latest published year.
2. **Indicator (Level 2).**
   - Average the features into components (each component counts once), then the components into the indicator.
   - Requires at least half of the components.
3. **FIRI (Level 3).**
   - Equal-weighted mean of the available indicators.
   - Requires at least 4 of 6 provincial, or 4 of 5 regional, indicators.
   - 0.5 = the usual level.
   - Reported with completeness, chance bands (usual / above usual / elevated / high), verification share and the leave-one-out range.
4. **Never:** zero-fill, impute, use pre-2021 bases, copy national values to provinces, or learn weights from SWS.

## 4. Provincial and regional handling

**Provincial FIRI:**
- six indicators from provincial observations only;
- computable for 75 of 115 province-quarters;
- usually from four indicators, because PSV has existed only since 2025-07 and FSSI rarely has 5 articles.

**Regional FIRI:**
- five indicators from Region IV-A, CALABARZON or national series;
- computable for 10 of 23 quarters (from 2024-Q2).

**National series** (remittances, ENSO, GDELT, unemployment) appear in the provincial view only as labelled context.

## 5. Machine-learning eligibility

| Group | Use |
|---|---|
| Regional SWS model: regional features | **Eligible (candidates):** Region IV-A CPI food and headline; farmgate palay; the Region IV-A production groups; CALABARZON rainfall and heat; cyclones in PAR; national unemployment change; remittance decline; GDELT shortage share |
| Regional SWS model: summaries | The regional indicator scores, **or** the regional FIRI as one summary predictor (not both with their own components) |
| Regional SWS model: target history | Lagged SWS readings (model input only, never a FIRI input) |
| Small sample | 39 labelled rows: a pre-registered short list is needed |
| Profiling only | All provincial features, provincial indicator scores and the provincial FIRI (no provincial label) |
| Context only | ENSO, GDELT jobs-income and assistance shares, density |
| Excluded | FIRI v2 (contains H1 and SWS-derived weights); the A1 model output; the commissioned SWS round |

## 6. More defensible than FIRI v2?

**Yes, on construction.** See `E120_FIRI_COMPARISON.md`.
- It uses all relevant data.
- It separates evidence from the outcome, and the index from the model.
- It keeps provincial data provincial.
- It removes measured duplicates.
- It uses equal weights whose robustness is shown, with interpretable bands.

**Neither version is validated against a provincial food-insecurity outcome**, because none exists. The two disagree strongly: ρ −0.30, and 39% agreement on the side of 0.5. That is expected, because v2 is weighted toward regional hunger.

## 7. Implementation plan (each step needs approval)

1. **E121: freeze an `E121_FIRI3_PROTOCOL.md`** from this design, including the sensitivity variants named here (for example, CPI food and headline merged into one component).
2. **Build a separate module** (for example `firi3.py`) and leave `firi.py` untouched. Reproduce `out/level3_firi_equal.csv` exactly, with tests.
3. **Prospective check:** score FIRI3 alongside FIRI v2 for new quarters before any switch.
4. **Regional check:** a pre-registered comparison of the regional FIRI with later SWS readings. Descriptive only, never used to set weights.
5. **Data that would strengthen it** (owner signatures needed):
   - PSA release calendars, to turn rule dates into verified dates;
   - the FIES 2023 publication date (adds the food-share feature);
   - CBMS 2024 FIES (the first provincial outcome for validation);
   - OPT Plus (utilization);
   - CHIRPS rainfall (area averages instead of centroid points).
6. **Dashboard:** any change of the served index is a separate owner decision. The approved design and colours stay.
