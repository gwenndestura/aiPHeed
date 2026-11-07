# E174 provenance (2026-11-07)

## Protected state (verified before and after)
Branch `aiPHeed/e166-drift-average`, HEAD `a980ccc`. E168 seal `28f2c918`, E173 seal `55c1bd37`, SIMPLE config
`ad38a0f17f51b8917ce93840150818bd037bd20f86ece08b588f08029136424e`. E166-E173 and the four modified service files untouched.
E168 and SIMPLE were not refitted, recalibrated or re-scored.

## Sources
- Repository: see `source_inventory.csv` (11 sources). No household microdata (.dta/.sav/PUF) is held.
- FNRI Heat Map API (live, 2026-11-07): 124 areas; latest provincial rounds 2021 (Batangas, Cavite), 2019 (Quezon, Rizal), 2018 (Laguna).
- FNRI eNutrition (eNutrition home, 2015 PUF, ENNS 2018-2021 PUF, 2023 and 2025 presentation pages): **HTTP 500 on every page on
  2026-11-07**; not readable. Earlier project notes (E129) record HTTP 503 on 2026-10-27/28. Availability of post-2021 provincial
  data there is unverified, not disproved.
- Known but not held: 2022 ENNS (FIES, about 20 provinces/HUCs, Jul-Dec 2022; coverage unverified; FNRI request drafted in E87,
  not sent); 2024 POPCEN-CBMS SDG 2.1.2 (FIES, by LGU; PSA request drafted, not sent).

## Findings
- 404 observations: 223 previously used (E151-E173 training/anchor or test), 177 excluded, **4 eligible independent**.
- Eligible: ENNS 2019 HFIAS for Camarines Sur, Davao Oriental, Pampanga, Zamboanga del Sur. The repository's ENNS 2019 table
  carried only their headline share, so they were never targets; the Heat Map publishes their full HFIAS categories and matches
  the ENNS headline exactly (0.0 points). **No standard error is published** for them. None is in CALABARZON.
- Excluded with reasons in `excluded_rows.csv`: 2011 round (different instrument), 39 city/HUC rows (no city inputs; no earlier
  own survey), 16 areas outside the panel, Heat Map duplicate category rows (164 raw rows, mostly 2015; the models use the FNRI 2015
  report file instead), FIES rows (ENNS 2021 provincial decks: same households as HFIAS rows already tested; 2023/2025 regional),
  and Cebu 2019 (Heat Map and ENNS publication disagree by 9.9 points).
- Effective sample size of the 4 rows by the existing method (PER_CELL 1.8, SHARED 0.726): **2.5**. C6 needs 40 rows:
  **C1-C6 cannot be evaluated on independent data.**

## What is required
A DOST-FNRI provincial HFIAS round after 2021 with standard errors for >= 40 provinces (any later ENNS/NNS provincial release, or
the 2023 NNS provincial estimates if FNRI publishes or releases them on request). FIES rounds (2022 ENNS, 2024 CBMS) can only
support a separately declared FIES sensitivity analysis; they cannot replace the HFIAS target.
