# Provincial food-insecurity outcomes: what exists, what is held, what would be needed (E99, documentation only)

No data were requested or collected in E99 (deadline rule, 2026-10-22). "Held" means present in this repository.

| Source | Construct | Geography and period | Held? | Could it validate provincial forecasts? |
|---|---|---|---|---|
| SWS Social Weather Survey, involuntary hunger | Household hunger, 3-month recall | Balance Luzon (region) quarterly; no provincial figure is published | Yes (`sws_rounds.csv`) | No: regional only. Used as the regional outcome and inside Eq. 3. |
| DOST-FNRI ENNS 2021 provincial dissemination | FIES moderate/severe food insecurity, 12-month recall | Batangas, Cavite, Lucena City (2021 only) | Yes (E87) | No: 2 provinces, 1 year, overlapping CIs. Descriptive only. |
| DOST-FNRI NNS 2023 regional dissemination | FIES | CALABARZON (2023) | Yes | No: regional, one year. |
| DOST-FNRI Updating Survey 2025 | FIES (population basis) | CALABARZON (2025) | Yes | No: regional, one year, different basis. |
| DOST-FNRI NNS 2019, CALABARZON regional FIES | — | **Not published** (the 2019 ENNS covered 2 provinces) | — | — |
| PSA Community-Based Monitoring System (CBMS) 2024 | Household items including food shortage/hunger questions | Household → barangay/LGU, one round (2024) | **No** | Partly: one cross-section could check the LGU ranking (H4-like) and the 2024 provincial ordering. It cannot validate quarterly forecasts. Requires a PSA data request (microdata or LGU tables). |
| DOST-FNRI ENNS/NNS provincial microdata | FIES | Provinces covered by each rolling round | **No** | Partly: a few province-years. Requires a FNRI data request. |
| PSA FIES (Family Income and Expenditure Survey) | Food expenditure share (not food insecurity) | Province, 2021 and 2023 | **No** | Contextual only: affordability, not a food-insecurity outcome. |

**Consequence for the claims.**
- Every quarterly evaluation in E83–E99 is either regional (SWS) or against a constructed proxy (Eq. 3 composite, T43).
- The thesis must state that **no provincial food-insecurity outcome was available to validate the provincial
  forecasts**, and that provincial values are proxy-based estimates.
- The strongest additional evidence that could still be obtained is **CBMS 2024 LGU-level food-shortage tables**. They
  would allow one cross-sectional check of the provincial and LGU orderings. This requires a formal PSA request, which
  is outside the current deadline rule.
