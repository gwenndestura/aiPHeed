# E119-R2 framework comparison

**Compared frameworks.**

| Framework | Description |
|---|---|
| **A** | The served 12 FIRI v2 indicators. In code they are grouped into six letter domains (A, V, C, E, N, H) with `MIN_DOMAINS = 4`. |
| **B6** | The six groupings suggested in the task. |
| **B7** | Seven indicators (recommended). |
| **C** | Four FAO-pillar indicators. |

**Basis.** Measured facts from `E119R2_COMPLETE_DATASET_INVENTORY.csv` and `E119R2_REDUNDANCY_AND_CORRELATION_REPORT.md`.

## 1. The frameworks

| | A: FIRI v2 (12) | B6: six suggested groupings | **B7: seven indicators (recommended)** | C: four FAO pillars |
|---|---|---|---|---|
| Units | A1 A2 A3 V1 C1 C2 C3 C4 E1 E2 N1 H1 (code domains: Affordability, Household vulnerability, Climate and food production, Household economy, News, Regional hunger) | Market accessibility; Agricultural and fisheries production; Climate and environment; Employment and household economy; Poverty and social vulnerability; Food insecurity signals and external shocks | **FP** Food Prices and Affordability; **PS** Local Food Production and Supply; **CH** Climate and Weather Hazards; **HI** Household Income and Employment; **SV** Structural Poverty and Vulnerability; **NS** Food Stress News Signals; **EH** Experienced Hunger | Availability; Access; Utilization; Stability |
| How B7 differs from B6 | — | — | B6's sixth group mixes the outcome (SWS hunger), media signals and an economic shock (remittances). B7 moves remittances to HI and splits the rest into NS (signals) and EH (outcome). | — |

## 2. Criteria

| Criterion | A | B6 | **B7** | C |
|---|---|---|---|---|
| Conceptual completeness | Prices, hazards, production, income, poverty, news, hunger present. No vegetables, root crops, livestock, rainfall, temperature or food budget share. | Complete | Complete; every acquired dataset has a place | Complete in name, but each pillar is very broad |
| Alignment with food insecurity | Mixes a model output (A1) and the outcome (H1) with the drivers | The sixth group mixes the outcome with predictors | Drivers (FP, PS, CH, HI), conditions (SV), signals (NS) and the outcome (EH) kept apart | Good conceptually; operationally weak (see below) |
| Acquired datasets accommodated | 32 of 48 have a FIRI v2 indicator. 16 have none; 3 of those are out of scope anyway (pre-2021 CPI, SWS in other regions, FNRI validation set). **13 relevant 2021+ CALABARZON datasets have no indicator:** retail vegetables, root crops, farmgate livestock, other cereals, wholesale fish, vegetable and root-crop production, chicken, livestock, rainfall, rainfall anomaly, temperature, FIES food share. | 48 of 48 | **48 of 48**, each with a role | 48 of 48, but many datasets belong to 2–3 pillars, so assignment is ambiguous |
| Redundancy | A1 is a LightGBM forecast built from CPI inputs that overlap A2/A3. C2 is identical across provinces in 64% of quarters and listed as national in `firi.NATIONAL`. C4 is grouped under climate. | Groups fine; the sixth group mixes unrelated evidence | Measured: FP 14 series ≈ 4.6 signals, PS 6 ≈ 5.0, CH 5 ≈ 3.2. Duplicates fixed by primary/alternative rules (r ≥ 0.79 rice; 0.94 bottom-30% CPI; 0.93 GDELT). | Hard to control: a price shock from a typhoon could count in Access, Availability and Stability at once |
| Missingness | N1 82.6% missing per province-quarter. V1 static. | As B7 | Missingness reported per component. Sparse series (FSSI, chicken/livestock 2023+) assigned to profiling, not forecasting. | Pillar values would be built from very unequal parts |
| Geographic suitability | C1, C2, E1, E2, H1 identical for all provinces; H1 regional value shown per province | As B7 | Each component keeps its resolution. National/regional components labelled "regional context" in the provincial profile, never province values. | Mixed resolutions inside every pillar |
| Temporal suitability | Annual/static V1 used every quarter (timing deviation disclosed) | As B7 | Monthly, quarterly and annual stay at their own frequency. SV is a profile only. | Mixed |
| Forecasting eligibility | 12 inputs regardless of quality | Not stated | Each dataset classified: 12 forecasting predictors (regional/national series), 15 provincial profiling, 11 supporting, 3 regional context, 2 validation, 10 excluded | Not separable |
| Interpretability (DA personnel) | Code letters; "A1 forecast" is opaque | Clear | Clear plain-language names that match how DA and LGUs talk (prices, harvest and catch, weather, jobs, poverty, news, hunger) | Abstract; "Utilization" has no CALABARZON data |
| Academic defensibility | Implementation-driven; weights for V1 and the 0.5 threshold are not derived from data | Reasonable, but the sixth group is not one concept | Each indicator is one causal role in the FAO / early-warning chain (hazard → production and prices → household access → outcome), plus structural vulnerability and signals. FAO dimensions are a secondary label. | Faithful to FAO, but the FAO dimensions are meant for classification, not measurement; Utilization would be empty |

## 3. Why not fewer, why not more

- **Why not 4 (C).**
  - Utilization has no province-quarter data in 2021–26. OPT Plus is unavailable (403 / FOI) and NDHS is a regional one-off.
  - Access would hold prices, income, poverty and hunger together, which are causes and outcome at once.
- **Why not 6 (B6).** Merging SWS hunger with news and remittances puts the target and two unrelated predictors in one indicator. Any "signal" score built from it would contain the outcome.
- **Why not more than 7.** Splitting FP into rice, protein and vegetables, or PS into crops and fish, would turn components into indicators. Components already stay separate as predictors, so extra indicators would only add labels.
- **Why not keep 12 (A).**
  - Three of the twelve are not datasets: A1 is a forecast, H1 is the outcome, and V1 is a weighted composite.
  - Two are near-duplicates at province level (C2 equals the national count in most quarters; E1 and E2 are national).
  - 13 relevant acquired datasets have no place.

## 4. Recommendation

**Framework B7: seven indicators**, with named components and one primary series per component. See `E119R2_FINAL_RECOMMENDATION.md`.
