# E129 provincial target construction options

**Evidence.** `E129_PROVINCIAL_TARGET_INVENTORY.csv` (15 candidates), `E129_PROVINCIAL_PANEL_FEASIBILITY.csv`, the OUTCOME_GAP_RESOLUTION register (10-28) and the E118 discovery (1,245 PSA OpenSTAT tables).

**Searches this session**
- FNRI 2022 ENNS province list: not found.
- 2024 CBMS FIES provincial results: PSA RSSO IV-A reports Batangas provincial CBMS briefings (Aug–Sep 2025). The page returned 403, which was not bypassed. No FIES values are public.

**Each option is kept separate.** Measured food insecurity, proxies, constructed indices and price conditions answer different questions.

## A. Direct provincial food-insecurity labels: **not available as a series**

| Source | Status |
|---|---|
| FNRI ENNS 2021 provincial FIES | **Held:** Batangas 29.7 %, Cavite 31.7 % (and Lucena). One round, 2 of 5 provinces. |
| FNRI 2022 ENNS | 20 domains; Laguna, Quezon and Rizal coverage unverified; not held |
| CBMS 2024 FIES (SDG 2.1.2) | Every participating LGU, but one 12-month window (Jul 2023–Jun 2024); not held |

**Verdict.** At best 1–2 provincial cross-sections. **No within-province change can be observed, so no Lead 1–4 forecast can be scored.** Valuable for cross-sectional validation of province or LGU ranking.

## B. Provincial survey-based estimates: **not available; precision doubtful**

| Source | Assessment |
|---|---|
| SWS microdata by province | About 20–75 respondents per province-round (estimated). Quarterly labels would be mostly sampling noise; an annual pooled panel (about 25 province-years) is possible. Requires access, design weights and an estimation protocol. |
| PSA APIS hunger item | Regional design |
| PSA FIES | No food-insecurity items |
| FNRI ENNS microdata | Rolling provincial design; too few rounds |

## C. Alternative official proxies: **none suitable as a quarterly food-insecurity label**

| Proxy | What it measures | Why not a label |
|---|---|---|
| Subsistence incidence | Income below the food threshold (food poverty) | Triennial (2021, 2023); CV up to 88 % |
| FIES food share / bottom-30 % | Economic access, vulnerability | Triennial; structural |
| NNC OPT Plus underweight / stunting | Child nutrition (utilization) | Annual; not held (403; FOI needed); a downstream nutrition outcome |
| DSWD programme data | Programme exposure | Driven by targeting and budget, not by measured need |

## D. Continuous target: **available only as a food-price condition**

**No continuous provincial food-insecurity series exists.**

The only continuous, official, repeated, genuinely provincial series is **provincial food CPI** (YoY, or the food-headline gap): 5 × 23 quarters.
- It is a legitimate forecasting target for **provincial food-price pressure**: regression of the YoY rate or its change, with no imposed threshold.
- It must be named as such. Forecasting it does not demonstrate food-insecurity forecasting accuracy.
- **Leakage warning:** price features (A1/A2/A3) would then be lagged values of the target itself, so persistence must be the main comparator.

## E. Constructed provincial risk index: **possible, but validates only itself**

**If owner-approved, a declared "Provincial Food Insecurity Risk Index" (PFIRI) could combine dimensions:**

| Dimension | Indicator | Why it is a food-insecurity dimension |
|---|---|---|
| Access: prices | Provincial food CPI YoY vs own 2021+ distribution | Food affordability |
| Access: staple | Retail regular rice YoY | Staple affordability |
| Availability | Palay/corn and fisheries production drop | Local supply |
| Stability | Local typhoon exposure (100/300 km); rainfall anomaly (NASA centroid) | Supply and income shocks |
| Vulnerability (weight, not driver) | Subsistence incidence 2023 / V1 | Sensitivity of households to shocks |

**Consequences that must be stated**
- It is **computed from the predictors**. "Forecasting" it with the same predictors is partly forecasting their own lags, so skill is mechanically inflated.
- **Its accuracy is index-forecast accuracy, not household food-insecurity accuracy.**
- It overlaps FIRI3 (E121–E127), which already covers six indicators by province. A second index needs a formal justification (FIRI3 is frozen and must not change). The cleaner option is to treat **FIRI3 as the declared risk index** and not build a parallel one.
- It can only be validated externally, cross-sectionally, against CBMS 2024 / ENNS FIES by province or LGU.

## Combination consequences

Mixing these (for example, regional SWS × provincial CPI, as in T43c) produces a label whose provincial variation comes entirely from prices. Its regional variation is copied. It is not admissible as a provincial food-insecurity label.
