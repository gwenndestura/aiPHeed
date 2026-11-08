# E118: answer, recommended data architecture, and the proposed E119 experiment

## The question

**"Can we build a more reliable provincial food insecurity forecasting model for CALABARZON by using additional datasets aligned with FAO's four dimensions?"**

**Answer: not a provincial food-insecurity forecast, because no repeated monthly, quarterly or annual provincial food-insecurity outcome is publicly available.**

The new data do allow three stronger things:
1. a **regional** hunger forecast with better provincial and area inputs;
2. a much richer **provincial vulnerability and early-warning profile**, covering availability, access and stability monthly or quarterly;
3. a **provincial validation** of that profile against the direct measures that do exist (CBMS 2024 FIES, FNRI FIES, OPT Plus, subsistence incidence).

### Direct food-insecurity measures found

| Measure | Provincial? | Repeated? | Use |
|---|---|---|---|
| SWS hunger | no (regional) | quarterly 1998-2026 | the only trainable target (regional) |
| FNRI FIES | partly (2 provinces + Lucena in 2021; selected provinces 2018-19) | irregular | cross-sectional validation |
| CBMS 2024 FIES | yes (LGU / barangay) | once | **best validation source**; needs a PSA/LGU request |
| OPT Plus undernutrition | yes | annual | candidate annual provincial **utilization** target; needs an NNC request |
| Subsistence incidence | yes | triennial (8 points) | long-run check; imprecise (CV up to 88%) |

**What each alternative permits:**
- **Regional SWS:** forecasting claims, regional.
- **CBMS, FNRI:** "the provincial profile ranks provinces / LGUs consistently with measured food insecurity" (cross-sectional).
- **OPT Plus (if obtained):** an annual provincial nutrition-outcome model, about 10-15 years × 5 provinces = 50-75 observations. It would be a utilization outcome, not food insecurity itself.
- **Subsistence:** long-run consistency only.

## Recommended data architecture (preserves the 12 FIRI indicators and five domains)

| Layer | Existing (kept) | New indicators (genuinely new, not duplicates) | Resolution |
|---|---|---|---|
| **Market and prices** (access) | A1, A2, A3 | Retail prices of staples (rice, chicken, pork, tilapia, vegetables) and farmgate palay/livestock prices, provincial monthly 2018/2010+. The bottom-30% CPI is kept as a robustness input only (r = 0.94 with A1/A2). | province, monthly |
| **Fish production** (availability) | C4 | Aquaculture by species (detail of C4; not counted as new) | province, quarterly |
| **Climate** (stability) | C1, C2, C3 | NASA POWER rainfall and temperature anomalies, provincial monthly 1981+ (fills the empty rainfall column). CHIRPS after raster aggregation. | province point, monthly |
| **Employment** (access) | E1 (national) | provincial annual LFS (owner file); minimum-wage orders (dated step series) for a real-wage index with provincial food prices | national monthly / provincial annual |
| **OFW remittances** (access) | E2 (national) | none at provincial level exists; BSP 1989+ national series via manual download | national |
| **Availability, other** (FAO) | — | vegetables / root crops (2010+); livestock and poultry inventory (2010+); chicken and livestock production (2023+, short) | province, quarterly |
| **Utilization** (FAO) | — | OPT Plus (request); NDHS 2022 (regional context) | province annual / region |
| **Direct measures (validation)** | SWS (regional target) | CBMS 2024 FIES, FNRI FIES, subsistence incidence | LGU / province, irregular |

**Rules:**
- Regional and national values stay in a context table and are never copied to provinces (as in the corrected pipeline).
- No composite score is built until a target supports it.

**Exclusions:**

| Excluded | Reason |
|---|---|
| World Bank RTFP | imputed values |
| HDX WFP prices | duplicate |
| Chicken/livestock production as training inputs before 2023 | do not exist |
| Any new series in **strict** evaluation | until release dates are verified |

**Training period:**
- Regional target: 2003-2026, using area-level aggregates of the new series. NASA rainfall at each SWS area's provinces back to 1981; prices only from 2010 (farmgate/wholesale) or 2018 (retail).
- Provincial profile: monthly from 2018 (retail) or 2010 (farmgate/wholesale).

**Monthly or quarterly forecasting.**
- **Quarterly regional hunger:** feasible. That is SWS's frequency.
- **Monthly or quarterly provincial food insecurity:** not feasible to validate.
- **Monthly provincial price-pressure or availability nowcasts:** feasible, but they are not food-insecurity forecasts.

## Proposed E119 (not run; for approval)

**Primary target:** SWS hunger level by area, Leads 1-2 (as E117), plus the "above usual" event.

**Secondary evaluation:** provincial validation of the profile ranking against CBMS 2024 FIES and FNRI FIES (cross-sectional; Spearman ρ with CIs). OPT Plus as an annual provincial outcome if NNC provides it.

**Features:**
- the 12 indicators and five domains, as in E117;
- **new:** NASA POWER rainfall and temperature anomalies (area-level: means of the provinces in each SWS area, which needs centroids for all Luzon, Visayas and Mindanao provinces); staple retail/farmgate price YoY (area means from 2010/2018); vegetables and livestock production YoY.
- Each new group enters in an additive ablation exactly as in E117.

**Models:**
- unified LightGBM (nested inner-fold selection);
- persistence, climatology, mean reversion, AR(1), ridge.

**Validation:**
- rolling origin; strict vs provisional modes;
- quarter-block bootstrap and Diebold-Mariano;
- Holm across groups;
- overfitting (train vs test);
- calibration;
- class balance of the event (not rebalanced);
- area-held-out generalization;
- stability by period (P1 / P2 / P3).

**Untouched evaluation:** sealed prospective forecasts (continuing E117's seal) plus new quarters only.

**Decision rule:** E117's, unchanged. A group "improves" only with pooled CI below 0, Holm p < 0.10 and a negative change in at least 2 of 3 periods. A prospective confirmation is required before any production claim.

**Before running E119:**
1. Collect PSA release calendars for prices and production (for strict mode).
2. Fetch NASA POWER for every province in the four SWS areas, and CHIRPS if reachable.
3. Send the CBMS, FNRI and NNC requests (owner signatures needed).
