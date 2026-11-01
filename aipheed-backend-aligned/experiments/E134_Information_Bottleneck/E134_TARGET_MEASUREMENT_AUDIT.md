# E134 target measurement audit

## 1. Measurements and their relation to food insecurity

| Measurement | Construct | Type | Frequency, 2021+ | CALABARZON / provincial | Role in AIPHEED |
|---|---|---|---|---|---|
| **SWS involuntary hunger** | Experienced hunger (families, past 3 months) | Survey observation, published margins | Quarterly; 20 quarters, 23 rounds (2022-Q1 and 2025-Q1 missing) | Balance Luzon only (CALABARZON is 1 of 7 regions) | **Primary quarterly target** |
| PSA subsistence incidence | Income below the food threshold | Survey estimate (FIES), with CI | 2021, 2023 provincial | Provinces | Independent periodic reference (provincial layer) |
| DOST-FNRI FIES (moderate + severe) | Experienced food insecurity (FAO FIES scale) | Survey estimate | 2021 (Batangas, Cavite), 2023 and 2025 regional | Partial | Complementary validation evidence |
| FIES 2023 expenditure, income and savings | Economic access / stress | Survey estimate | 2023 | Provinces | Supporting evidence (provincial layer) |
| OCTA hunger | Experienced hunger, different instrument | Survey (news-reported) | 7 BL readings | Balance Luzon | Cross-check only |

**Not food-insecurity measurements:** CPI, poverty incidence, FIRI v2/FIRI3 and model scores. None of them is used as a target.

**Multi-source combination: rejected.**
- The instruments differ in construct (experienced hunger vs income-based food deprivation vs the FIES scale), unit (families vs population), reference period and geography.
- SWS and OCTA, which measure the same construct, still differ by MAE 5.2 (E132).
- So the tracks are kept **separate**:
  - SWS: quarterly forecasting target;
  - PFDR / FIES: provincial survey-year reference;
  - FNRI: construct validation.

## 2. How much forecast error the target's own uncertainty explains

**Sampling variance against forecast MSE**, Lead 2, P-DASH, S-U (40 rows; `out/t1_target_uncertainty.csv`):

| Model | MSE | Mean SE² | Sampling share | Excess RMSE beyond sampling |
|---|---|---|---|---|
| PERSIST | 59.4 | 4.9 | 8 % | 7.4 |
| SEAS-LLM | 57.4 | 4.9 | 9 % | 7.2 |
| **HFM-X** | 41.2 | 4.9 | **12 %** | **6.0** |
| E134-ONI | 32.5 | 4.9 | 15 % | 5.3 |
| ORACLE-NOW (true current level known) | 52.1 | 4.9 | 9 % | 6.9 |

**Conclusion.** Sampling error explains only **8–15 %** of the forecast error. The rest is genuine change in hunger that the models do not foresee. Survey noise is not the reason 75 % fails, and it is **not** used to widen the tolerance.

**Other components:**
- **Non-sampling variance within SWS:** τ² is estimated at its lower bound (0.01) at every issue (E133). SWS rounds are consistent with their published margins.
- **Design change:** in 2025 SWS changed the respondent base (household heads → adults) and alternated sample sizes (600 / 300 per area). This is handled by the break variance and the design effect (HFM-NS-DES). It explains part of the post-2025 quarter-to-quarter pattern; SEAS-LLM is 0.71 within on post-break targets.
- **Temporal gaps:** 2022-Q1 and 2025-Q1 have no round. They are treated as missing and never interpolated into targets.
- **Publication delay:** 3–10 weeks after fieldwork. At a P-DASH issue the newest SWS quarter is usually two quarters old, so Lead 2 is h = 3 quarters past the last observation (E130/E133).
- **Coverage:** the four areas are national strata. Balance Luzon's estimate covers 7 regions; CALABARZON's share of it is not published.

## 3. Consequence

The target is defensible as measured food insecurity. Its uncertainty is small relative to the errors: about 88 % of HFM-X's Lead-2 squared error is true change in hunger, which the models fail to forecast.
