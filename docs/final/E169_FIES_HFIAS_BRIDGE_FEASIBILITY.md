# E169: FIES → HFIAS bridge feasibility (2026-11-06)

**Owner decision (2026-11-06):** allow a documented bridge so the overall level can be refreshed from the 2023 NNS. This is a relaxation of the "keep FIES, HFIAS and SWS distinct" rule.

**Scope:**
- **Feasibility only.** No model was built and no gate was changed.
- **Code:** `backend/app/e169/fies_bridge.py`
- **Output:** `backend/data/e169/out/fies_bridge_feasibility.json`

## Verdict: FEASIBLE at national and regional level; NOT precise enough for provincial labels

### 1. Paired data exists
- **20 provinces and cities in the 2019 ENNS factsheets report both HFIAS and FIES (moderate + severe) for the same households.** Source: `data/hfias/clean/enns_hfias.csv`.
- The pairs include Quezon and Rizal.
- This is the only pairing year in the repo:
  - The 2018 factsheets carry HFIAS only.
  - No 2021 factsheet with both scales was found in the repo or by web search.

### 2. The bridge (logit scale, fitted on the 2019 pairs only)
| Quantity | Value |
|---|---|
| logit HFIAS = a + b · logit FIES | a = 0.158, **b = 0.917 [0.64, 1.22]** |
| Correlation (percent scale) | 0.82 |
| HFIAS − FIES, mean | +4.5 points |
| Residual per province | 0.27 logit (about 6 points) |
| Province HIGH (≥ 50) agreement | 85 % |

- The two scales measure closely related constructs. **HFIAS runs about 4–5 points higher than FIES.**
- **Per province, the bridge error (about 6 points) is as large as the forecast error.** So the bridge must not be used to create provincial HFIAS labels.
- At regional or national level, province noise averages out and the bridge becomes useful.

### 3. Checks on national values
| Year | FIES (PSA SDG 2.1.2) | Bridged HFIAS | HFIAS observed |
|---|---|---|---|
| 2019 (in sample) | 44.2 | 48.6 | 46.9 national, **+1.7 points** |
| **2021 (out of year)** | 33.4 | **38.4 [35.2, 41.4]** | 41.6, an unweighted mean of 25 provinces (rough; no national HFIAS 2021 was printed) |

- **The bridge carries over to 2021 in direction and approximate size**, with an error of a few points.
- It is not yet proven: there is one pairing year, and 2021 has no exact national comparison.

### 4. What it gives for 2023
| | FIES 2023 | Bridged HFIAS 2023 [95 %] |
|---|---|---|
| **CALABARZON** | 19.1 | **23.8 [18.5, 29.6]** |
| Philippines | 31.4 | 36.4 |

- **The region-level anchor moves from 2021 to 2023**, cutting the gap at a 2027 forecast from 6 years to about 3.5.
- It is **regional only.** Provincial differences still come from the 2021 provincial HFIAS plus the LightGBM ranking part.
- **A bridged CALABARZON level of about 24 % is far below the HIGH threshold of 50.** This independently supports the all-LOW reading for the region in 2023.

## 5. Second-year test: 2021 pairs (added 2026-11-06)

**Search results:**
- **No 2021 provincial factsheets exist in the web archive.** The FNRI uploads index has only national 2021 reports.
- The FNRI heat map is HFIAS only.
- The DEPDev 2021 Batangas/Cavite values are HFIAS components.

**Found:**
- The **2021 ENNS Facts and Figures** (DOST-FNRI) prints FIES and HFIAS for the same households: nationally, and for 18 socio-demographic subgroups (household size, residence, wealth quintile, sex, education and occupation of the head).
- 19 pairs in total, transcribed with page numbers to `data/e169/raw/enns2021_fies_hfias_subgroup_pairs.csv`.
- **Exact 2021 national values:** FIES 33.4 (SE 1.4); HFIAS moderate + severe 21.3 + 19.7 = **41.0**.

**Frozen 2019 bridge applied to 2021, with no refitting** (`bridge_2021_test.json`):

| | Result |
|---|---|
| National | bridged 38.3 vs observed 41.0 (**−2.7 points**) |
| 19 pairs, mean error | **−3.0 points** (all negative) |
| Mean absolute error | **3.0 points** (using FIES as if it were HFIAS: 7.6) |
| Largest error | 6.9 (no-grade heads) |
| HIGH (≥ 50) agreement | 89.5 % (misses "poor quintile", 50.1 observed vs 45.1 bridged) |
| 2021's own fit, for comparison | slope 0.994 (2019: 0.917 [0.64, 1.22]); intercept 0.343 (2019: 0.158) |

**Reading:**
- **The shape of the bridge holds across years**, and the slope is stable.
- **The level gap does not hold.** In 2021, HFIAS ran about 3 points higher relative to FIES than in 2019. HFIAS uses a 30-day recall and FIES a 12-month recall, so the gap can move with conditions at fieldwork, such as COVID in 2021.
- **The bridge is usable only with a year-drift uncertainty of about ±3 points** on top of its fitting uncertainty.

**Effect on 2023:**
- With the 2019 intercept, CALABARZON bridged HFIAS is 23.8 %. With the 2021 intercept it is 25.1 %.
- Either way it is **far below the HIGH line of 50**, so the regional conclusion does not depend on which year's gap applies.

## Owner-workbook labelling error (found during this check)
- The DEPDev-sourced rows labelled "Moderate-to-severe food insecurity" (Laguna 2018, Quezon 2019, Rizal 2019, Batangas 2021, Cavite 2021) are **HFIAS moderate only**.
  - **Example:** Quezon 2019, labelled "moderate-to-severe" 30.3 and "severe" 13.7. The FNRI factsheet gives moderate 30.3 and severe 13.7, so moderate-to-severe = **44.0**.
- The true moderate + severe values are the two rows added together. The CSV is unchanged; it is the owner's file.

## What it does not do
- **It does not change the historical C1/C4 result.** No FIES existed before the 2018 and 2019 origins (`E169_NEW_SIGNAL_TESTS.md`).
- It does not create provincial labels.

## Next steps
1. ~~A second pairing year~~ **Done (section 5): no 2021 provincial pairs exist; national and subgroup pairs confirm the slope and show about ±3 points of year drift.** Original plan: If FNRI's 2021 provincial factsheets print FIES next to HFIAS (as the 2019 ones do), the bridge can be fitted on 2019 and **tested on 2021 province by province**. That is the decisive feasibility test. Source: FNRI eNutrition provincial ENNS 2021 PDFs (web archive copies, as for 2018/2019).
2. **E170 protocol, fixed before results:**
   - **Part A:** LightGBM provincial ranking relative to the region.
   - **Part B:** the regional level from the newest official survey, bridged with propagated uncertainty.
   - The frozen bridge is fitted on 2019 only.
3. **Regional 2023 check:**
   - Run the frozen E158/E168 forecasts as of 2023, aggregate them to regions, and compare with the 17 regional 2023 values through the bridge.
   - **Caveat:** the 2023 values are already in the repo and have been read, so this is out of sample but **not blind**. Nothing may be tuned on it.
