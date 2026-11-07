# Target validity (E168)

**What E168 predicts (VERIFIED):** P(a province's share of households with moderate or severe food insecurity on the DOST-FNRI HFIAS is
>= 50 % in the target quarter). Evidence: `app/e147/features.base_rows` (line 124) → values identical to `mod_sev_pct` in
`data/hfias/clean/enns_hfias.csv` (max |diff| 0.0); 26.7 points from "any food insecurity". The argument name `outcomes("insecure")` is
misleading (F15).

| Question | Answer | Status |
|---|---|---|
| Direct food-insecurity measure? | Yes: HFIAS household experience scale | VERIFIED |
| Hunger prevalence or proxy? | Neither: it is food-insecurity prevalence (moderate + severe), thresholded at 50 % | VERIFIED |
| Comparable across periods? | NNS 2013, FNRI 2015, ENNS 2018/2019/2021 all HFIAS; FIES rows excluded | VERIFIED |
| Geographic scope | Province (78 panel provinces nationwide; 5 in CALABARZON); training and evaluation are national | VERIFIED |
| Temporal scope | Survey rounds only; reference quarter Q3 of the survey year (assumed in code) | PARTIALLY VERIFIED |
| Provincial ground truth for dashboard quarters | None after 2021; 2023-Q1..2026-Q4 are back-forecasts; 2027-Q1 sealed | VERIFIED (limitation, F07) |
| SWS Balance Luzon | **Not the E168 target.** Used only in the temperature-shrink step. It covers all of Luzon outside Metro Manila: not a CALABARZON or provincial measure | VERIFIED |
| Thesis title "food insecurity forecasting" | Supported at province-survey-round level | VERIFIED with qualification |
| Dashboard / Landing description | Landing still describes an SWS + price target | INCORRECT (F04) |

**Claim the system supports:** "forecasts one to three quarters ahead whether a province's HFIAS moderate-or-severe food insecurity
will reach 50 %, validated retrospectively on 72 DOST-FNRI province-rounds (2018-2021)."
