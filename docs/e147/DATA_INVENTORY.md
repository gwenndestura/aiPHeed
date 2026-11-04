# Labelled food-insecurity data: inventory, provenance and allowed use

Audit date 2026-11-04. Values for the 2021 HFIAS round are sealed and were not read for this document.

## 1. Direct food-insecurity measurements

| Source | Instrument, recall | Years | Geography | Rows held | Allowed use |
|---|---|---|---|---|---|
| **DOST-FNRI Hunger and Malnutrition Heat Map** (`heatmap.fnri.dost.gov.ph`, public) | HFIAS, 30 days | 2013, 2015, 2018, 2019, **2021** | Province, HUC | 86, 86, 40, 38, **37** any-level | **Train (2013 to 2019) and sealed test (2021)** |
| Same | Radimer/Cornell, 3 months | 2011 | Province, HUC | 85 | **Predictor only.** Not comparable with HFIAS. 2008 is shown at regional level on the map |
| FNRI NNS 2013 Appendix, FNRI 2015, ENNS provincial decks | HFIAS | 2013 to 2019 | Province | 203 in the E141 panel | Same rows, with standard errors |
| ENNS 2019 and 2021 provincial decks | FIES, 12 months | 2019 (20 areas); 2021 (Batangas, Cavite, Lucena held locally) | Province, HUC | 23 | Agreement only. Never pooled |
| NNS 2023 regional deck, PSA SDG 2.1.2 | FIES | 2023 | Region | 17 | Face validity only |
| 2025 Updating Survey | FIES, population basis | 2025 | Region | 1 for CALABARZON | Context; the basis differs |
| SWS | One-item involuntary hunger, 3 months | Quarterly, 1998 onward | 4 areas | About 100 per area | Quarterly time signal; regional, never a provincial label |
| CBMS 2024 | FIES | Jul 2023 to Jun 2024 | Barangay, city | **Not held** | Would be the strongest spatial evidence |

**2021 provinces with model inputs (25):** Agusan del Sur, Albay, Apayao, Aurora, Bataan, Batangas, Bohol, Catanduanes, Cavite, Cotabato, Davao de Oro, Davao del Sur, Ifugao, Ilocos Sur, La Union, Leyte, Masbate, Negros Occidental, Negros Oriental, Occidental Mindoro, Romblon, Sarangani, Surigao del Norte, Tarlac, Tawi-Tawi. **Cities not scored (12):** no provincial inputs.

## 2. Your workbook `aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx`

The workbook's own notes say these are not quarterly labels. That is correct, and it should stay.

| Sheet content | Finding | Action |
|---|---|---|
| FNRI 2015 food secure and severe | Matches the panel for all five provinces | Usable; already in the panel |
| ENNS 2018, 2019 "moderate-to-severe" | **Mislabelled in the source matrix. These are HFIAS moderate only.** Laguna 18.3, Rizal 27.5, Quezon 30.3; true moderate-or-severe 26.2, 39.1, 44.0 | Do not use as printed |
| ENNS 2018, 2019 severe | Correct HFIAS severe | Usable |
| ENNS 2021 values | FIES: Batangas 29.7, Cavite 31.7. Not HFIAS | Agreement only |
| PSA subsistence incidence | Income-based food poverty, not experience of food insecurity. Province ranks unstable | Predictor only |
| Regional benchmarks | 51.5 % is pooled 2018, 2019 and 2021 HFIAS, confirmed on the Heat Map. 19.1 % is FIES 2023 | Face validity |

## 3. Reconciliation of the Heat Map against the panel

Any-level values for rounds already read.

| Round | Heat Map rows | Matched | Exact | Mismatch |
|---|---|---|---|---|
| 2013 | 86 | 78 | 77 | Basilan 80.5 vs 78.87 |
| 2015 | 86 | 81 | 81 | None |
| 2018 | 40 | 36 | 36 | None |
| 2019 | 38 | 35 | 34 | Cebu 54.9 vs headline 64.8 |

**Omitted observations.** 2013: 8 areas, 2015: 5, 2018: 4, 2019: 3 are Heat Map rows the panel cannot match, mostly cities. The panel uses 22 of 38 ENNS 2018 rows and 25 of 38 ENNS 2019 rows because of missing provincial inputs or missing values. They are excluded from training because their inputs do not exist, not because the labels are wrong.

**Quality problem found.** The Heat Map's 2015 export has mislabelled duplicate moderate and severe rows in 82 province-category cells (for Abra, "13.0" appears under both labels). Moderate-or-severe from the Heat Map is therefore not used for 2015. The any-level series is clean and is what E147 uses.

**Corrected claim.** Earlier work said the 2021 ENNS used only FIES and that HFIAS ended in 2019. FNRI's methodology shows HFIAS continued through 2021.

## 4. Candidate targets, on development rows only

| Candidate | Nationwide positive share by round (2013, 2015, 2018, 2019) | CALABARZON positive rows of 13 | Assessment |
|---|---|---|---|
| A. Above national, moderate-or-severe | 0.36, 0.19, 0.50, 0.56 | **0** | Cannot produce a high-risk case in the study area |
| B. Moderate-or-severe ≥ 42.8 % | 0.83, 0.90, 0.59, 0.68 | 5 | The threshold is a pooled national mean, not a severity standard |
| **C. Food-insecure households ≥ 60 %, FNRI "High"** | 0.83, 0.82, 0.64, 0.68 | **2 (Quezon 2013, 2019)** | **Selected.** Published cut-off, not set by this study |
| D. FNRI five bands | All rows: Very High 22, High 138, Medium 42, Low 1. CALABARZON: High 2, Medium 10, Low 1 | | Reported with C; too few rows in outer bands to model |
| E. Above own region's mean | 0.47, 0.58, 0.36, 0.40 | 5 | Relative, and incomplete rounds change the comparison set. Rejected as primary |
| F. Continuous any-level | Between-province SD 8 to 13 points; survey SE 2 to 5 | | **Used as the learning target**; C is its reported class |

**Why C.** The brief requires a threshold justified by established measurement practice. FNRI's Heat Map publishes this one as "cut-off values for public health significance (Food Insecure Households)". It separates Quezon from the region as measured.

**Weaknesses of C, stated plainly.**
* Nationally, 64 to 83 % of provinces are HIGH, so accuracy must be read beside always-HIGH.
* Within 1.645 SE of 60 %, the class is uncertain, and Quezon 2015 at 59.7 % is one such case.
* Any-level includes mild insecurity, a broader concept than moderate-or-severe.
* The thesis should cite FNRI's Heat Map for it, and your adviser should confirm it.

## 5. What can train, validate and test

| Use | Rows |
|---|---|
| Train (change from last survey) | 2015 (78), 2018 (22), 2019 (25) |
| Development test | 2018, 2019: already seen by earlier experiments, on other targets |
| **Final untouched test** | **2021: 25 provinces, sealed** |
| Face validity | FIES 2019, 2021, 2023 |
| Quarterly province-level validation | **None exists.** No survey measures provinces quarterly |

## 6. Provincial coverage of CALABARZON, HFIAS

| Province | 2013 | 2015 | 2018 | 2019 | 2021 |
|---|---|---|---|---|---|
| Batangas | 58.1 Medium | 56.3 Medium | | | Sealed |
| Cavite | 53.1 Medium | 56.0 Medium | | | Sealed |
| Laguna | 55.9 Medium | 53.2 Medium | 39.3 Low | | |
| Quezon | 71.4 High | 59.7 Medium | | 61.9 High | Lucena City only, sealed |
| Rizal | 56.3 Medium | 53.7 Medium | | 56.6 Medium | |
