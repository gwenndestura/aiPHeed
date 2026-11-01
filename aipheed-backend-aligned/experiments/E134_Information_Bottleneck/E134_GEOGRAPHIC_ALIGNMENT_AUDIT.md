# E134 geographic alignment audit

**The mismatch.**
- The target is measured for 4 SWS areas.
- Balance Luzon = CAR, Regions I, II, III, IV-A, MIMAROPA and V (7 regions; NCR is separate).
- CALABARZON (IV-A) is one of those 7 regions.
- The five provinces cover IV-A only.

## Approaches evaluated

| # | Approach | Geographic assumption | Source data | Weighting | Measurement error | Validation | Consequence for provinces | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Obtain SWS boundaries and respondent distribution | SWS area = PSA regions as listed in SWS releases | SWS methodology notes; respondent counts per region not published | n/a | n/a | n/a | None | Boundaries are known (regions); **regional respondent counts are not published**. Not obtainable without an SWS request. |
| 2 | Aggregate province news (FSSI) into the SWS area | 5 provinces represent Balance Luzon | FSSI v2 | POPCEN 2024 (CALABARZON only) | Large: IV-A is about 30 % of Balance Luzon's population (estimate; not computed from held data), and the other 6 regions have no FSSI | Correlation with the BL HFM-X residual: ρ = 0.19, p = 0.67 (8 rows) | n/a | **Rejected:** it does not cover the target geography, and no signal was found |
| 3 | Aggregate regional economic and climate indicators into SWS areas | Area = equal-weight mean of its regions | Regional CPI, B30 CPI, palay, NASA POWER (E134) | Equal region weights (no in-window regional population series held, 2021+) | Moderate: unequal region sizes | Walk-forward (E134-AREA-T) | n/a | **Adopted for drivers.** Tested; no Lead-2 gain. |
| 4 | Model the target at its own geography first, then estimate provinces | — | SWS 4 areas | — | — | Walk-forward on SWS | Provinces inherit Balance Luzon dynamics | **Adopted** (unchanged from E131–E133) |
| 5 | Separate regional and provincial stages | Provincial levels from survey-year references (PFDR, FIES, FNRI) | PFDR 2021/2023, FIES 2023 T7/T8, FNRI 2021 | Survey weights inside PSA/FNRI estimates | Survey CIs; measure-dependence | Survey years only | Provincial ordering differs by measure (provincial report) | **Adopted**, with measure-dependence disclosed |
| 6 | Crosswalk without invented observations | Region → area membership only | PSA region codes | — | — | Unit test (each region maps to exactly one area) | — | **Adopted**; no observation is created |

**Distinction preserved.**
- **Measured:** regional (area) hunger.
- **Estimated:** provincial hunger, which is model-based.
- No SWS value is copied to provinces. No province value is called a measurement.
