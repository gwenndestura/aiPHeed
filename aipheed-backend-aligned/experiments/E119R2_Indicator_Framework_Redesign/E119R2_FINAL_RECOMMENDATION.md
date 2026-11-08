# E119-R2 final recommendation: a seven-indicator food insecurity framework

**Status.** A proposal for review. Nothing is implemented: FIRI v2, the served model, the dashboard and the E118/E119 files are unchanged. No model was trained and nothing was pushed.

## 1. Recommendation in brief

**Seven indicators.** Each is a named group of **components**. Each component keeps its own series at its own resolution and frequency, with one **primary** series where several measure the same thing.

**Two uses, kept apart:**

| Use | What it is | Status |
|---|---|---|
| **Regional forecasting** | SWS Balance Luzon hunger, predicted from regional/national series of the indicators | A supervised model is possible |
| **Provincial vulnerability profiling** | The five provinces compared on provincial components | No label exists, so no supervised provincial forecast is claimed |

**The causal order behind the seven:**

| Stage | Indicators |
|---|---|
| Hazard | CH |
| Supply and prices | PS, FP |
| Household access | HI |
| Underlying conditions | SV |
| Early signal | NS |
| Outcome | EH |

Each stage is a different role in the food-insecurity chain. That keeps cause and outcome out of the same indicator, and lets DA staff read the profile as "what happened, where, and to whom".

## 2. The seven indicators

| # | Indicator | Definition | FAO dimension | FIRI v2 represented |
|---|---|---|---|---|
| 1 | **FP · Food Prices and Affordability** | How expensive food and household necessities are, measured by changes in consumer, retail, wholesale and farmgate prices of staple and protein foods | Access (primary); Stability | A1, A2, A3 |
| 2 | **PS · Local Food Production and Supply** | Change in the quantity of food produced in the province: cereals, vegetables, root crops, fisheries, poultry and livestock | Availability (primary); Stability; Access (producer income) | C3, C4 |
| 3 | **CH · Climate and Weather Hazards** | Rainfall and temperature departures, tropical cyclones near the province, and the ENSO state | Stability (primary); Availability | C1, C2 |
| 4 | **HI · Household Income and Employment** | Households' ability to earn income: unemployment, underemployment, participation, OFW remittances | Access (primary); Stability | E1, E2 |
| 5 | **SV · Structural Poverty and Vulnerability** | Slow-moving conditions that make a province more exposed when a shock arrives: poverty, food poverty, food share of spending, density (context) | Access (primary); Utilization (indirect) | V1 |
| 6 | **NS · Food Stress News Signals** | How much local and national news reports shortage, price stress, job loss or assistance | Stability (early warning) | N1 |
| 7 | **EH · Experienced Hunger** | Share of families experiencing involuntary hunger (SWS Balance Luzon); FIES surveys for validation | Access and Utilization (outcome); Stability | H1 |

**What does not carry over from FIRI v2:**
- **A1** is a model forecast, not data. It becomes a possible *forecast of FP*, not an input.
- **V1's fixed 0.6/0.4 weights** are replaced by showing its components side by side.
- **H1** becomes the outcome indicator (EH), not one of the drivers.

**Utilization is the weakest dimension.** No province-quarter nutrition or WASH data exist for 2021–26. OPT Plus needs an FOI request, and NDHS 2022 is regional and one-off. Utilization is represented only through experienced hunger and food poverty. This is a disclosed gap, not a hidden one.

## 3. Datasets per indicator, and their use

Roles: **F** = regional forecasting predictor; **P** = provincial profiling; **R** = regional context; **S** = supporting (alternative or sensitivity, never extra evidence); **V** = validation only; **X** = excluded.

| Indicator | Components and datasets (role) |
|---|---|
| **FP** | **General food inflation:** CPI food provincial (P), Region IV-A CPI food/headline (F), bottom-30% CPI (S, r 0.94). **Cost of living:** CPI headline provincial (P). **Rice price:** wholesale rice (P, primary), retail rice (S, r 0.86), farmgate palay (F, the regional rice series; r 0.79). **Protein prices:** retail chicken, pork, tilapia (P). **Vegetable and root-crop prices:** tomato, cabbage, eggplant, cassava, carrot (S). **Producer prices:** farmgate hog and livestock (S). **Excluded:** corngrits (not a household staple), wholesale fish (2 provinces), A1 forecast (model output), CPI 1994–2018 and other pre-2021 or unacquired price sets. |
| **PS** | **Cereals:** palay (F), corn (F). **Vegetables:** non-root vegetable production (F). **Root crops** (P). **Fisheries:** total (F), aquaculture (S: part of the total). **Poultry and livestock:** chicken, livestock (P; start 2023, YoY only from 2024). **Excluded (not acquired):** fruit crops, inventories, trade, cereal stocks, damage reports. |
| **CH** | **Rainfall:** total (F; regional = mean of 5 centroids; ends 2025-12), anomaly (S). **Temperature** (P). **Cyclones:** within 100 km (P, primary local measure), within 300 km (S; equal across provinces in 64% of quarters), in PAR (F). **ENSO:** ONI (F), PAGASA advisory (R). **Excluded:** CHIRPS, stations, NDVI (not acquired). |
| **HI** | **Employment:** national unemployment (F); provincial annual unemployment, underemployment, employment and participation 2021–25 (P). **Remittances:** national (R; 21.7% missing, 11% verified). **Excluded:** wage orders, 4Ps (not acquired). |
| **SV** | Poverty incidence SAE 2021 (P); subsistence incidence 2021 and 2023 (P, with CVs); FIES 2023 food share, all and bottom 30% (P); density (S, context); V1 composite (S, legacy). |
| **NS** | GDELT shares (F as a *candidate to be tested*; supply and shortage shares r 0.93, so use one); FSSI-v3 (P; only 20 of 115 province-quarters have ≥ 5 articles); article counts (S). |
| **EH** | SWS Balance Luzon (F: target and lagged history); SWS other areas (R: panel methods only); FNRI 2021 and CBMS 2024 FIES (V); commissioned SWS round, OPT Plus, NDHS, FAOSTAT (X). |

**Totals:**
- 54 datasets; 48 acquired or in the repository.
- By role: 12 forecasting predictors, 15 provincial profiling, 11 supporting, 3 regional context, 2 validation, 10 excluded (`E119R2_FORECASTING_ELIGIBILITY.csv`).

## 4. What can actually be used for forecasting

**The 12 regional forecasting predictors:**
- Region IV-A CPI food/headline;
- farmgate palay (Region IV-A);
- palay, corn, vegetable and fisheries production (Region IV-A rows);
- ONI;
- cyclones in PAR;
- CALABARZON rainfall;
- national unemployment;
- GDELT news shares;
- the lagged SWS reading.

**Strict (verified-only) subset:** SWS history, cyclones in PAR, GDELT. Every other predictor's release date is a documented rule, not an archived release. This is the binding constraint for a strict model.

**Sample size is the real limit.** There are 39 labelled rows and only 19–23 quarters per series. A model must be small:
- a handful of predictors, chosen by a pre-registered rule;
- the latest SWS reading as the baseline.

All earlier phases found nothing beat it at Lead 2.

## 5. What is only for profiling or context

- **Provincial profiling (quarterly):** provincial CPI, rice, protein prices, production by commodity, cyclones within 100 km, temperature, and FSSI.
- **Provincial profiling (annual or static):** poverty, subsistence, FIES food share, annual employment.
- **Regional or national context, never shown as a province value:** the PAGASA advisory, remittances, and SWS in other areas.

## 6. Why this is better than the 12-indicator structure

1. **It uses the data that exist.**
   - All 48 acquired datasets have a place and a role.
   - Under FIRI v2, 13 relevant 2021+ CALABARZON datasets had no indicator: vegetables, root crops, livestock, rainfall, temperature, food budget share and others.
2. **It separates cause, condition, signal and outcome.**
   - FIRI v2 mixed a model forecast (A1) and the outcome (H1) into the drivers.
3. **It counts evidence once.**
   - Measured redundancy: the 14 price series behave like about 4.6 signals, production like 5.0 of 6, and hazards like 3.2 of 5.
   - Near-duplicates are alternatives, not extra votes: rice at three market levels, bottom-30% CPI, GDELT supply and shortage, and the 300 km cyclone count.
4. **It respects geography.**
   - National and regional values are labelled as context.
   - Province values are only genuine provincial observations.
   - The 300 km cyclone count, identical across provinces in most quarters, is replaced by the 100 km count for the profile.
5. **It respects time.**
   - Annual and static data stay annual.
   - No pre-2021 base enters any change.
   - Sparse series are not forced into the model.
6. **It is readable.**
   - The names follow how DA and LGU staff discuss food security: prices, harvest and catch, weather, jobs, poverty, news, hunger.
   - FAO dimensions are a secondary label, as intended.

## 7. Implementation recommendations (each needs approval; none done here)

1. **Freeze a framework protocol** (E120) before any model: the indicators, components, primary series and roles in this folder.
2. **Rebuild the E119 datasets under the new structure** as a new folder, leaving E119 itself unchanged:
   - split vegetables from root crops;
   - add the bottom-30% FIES share;
   - fix the E119 per-indicator `resolution` label for Region IV-A rows (see the validation report).
3. **Regional model.** Use a pre-registered small predictor set, one primary series per component, with the latest SWS reading as the baseline. Evaluate with rolling origins on 2021+ only.
4. **Provincial profile.**
   - Show components with their date, resolution and status.
   - Compare provinces by rank.
   - No composite weights until a defensible method is pre-registered, such as in-sample principal components.
5. **Data to request**, all needing owner signatures:
   - PSA release calendars, to turn rule dates into verified ones;
   - CBMS 2024 FIES;
   - OPT Plus, for the utilization gap;
   - FIES 2021 food shares;
   - NWPC wage orders.
6. **Changing FIRI v2 on the dashboard** is a separate, later decision for the owner. The dashboard design and colours stay as approved.
