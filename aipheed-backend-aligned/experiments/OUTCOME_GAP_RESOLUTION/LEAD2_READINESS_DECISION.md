# Lead-2 readiness decision

**Date:** 2026-10-28. **Branch:** `aiPHeed/forecast-research` (local; not pushed, not deployed).
**Evidence:** `OUTCOME_DATA_FEASIBILITY.md`, `OFFICIAL_OUTCOME_SOURCE_REGISTER.csv`, `LEAD2_VALID_OUTCOME_PROTOCOL.md` (frozen; SHA-256 in `runner/PROTOCOL_SHA256.txt`), and `out/comparators_reproduced.json`.

## Decision

# NOT EVALUABLE — REQUIRED OUTCOME DATA UNAVAILABLE

Lead 2 forecasts a province's risk class for the next quarter (issued on the first day of the current quarter, e.g. 2027-Q1 from 2026-10-01). No measured food-insecurity outcome exists at that unit (province × quarter) for 2021-2026, in the repository or at any agency source found:
- CBMS 2024 is one 12-month window (July 2023 - June 2024), and has not been obtained.
- FNRI FIES is one-off provincial cross-sections (2021: Batangas, Cavite, Lucena) plus regional values for 2023 and 2025.
- APIS is annual and regional.
- SWS, the only quarterly measure, is published for Balance Luzon only.

So whether Lead 2 forecasts actual provincial food insecurity **cannot be evaluated**. It has not failed; it cannot be tested.

## What this decision does not change

- **The proxy evidence still stands as proxy evidence.**
  - P0H4, P0H4-U and Z0-U were reproduced exactly from their saved predictions.
  - Against T43c their Lead-2 accuracy is 0.769, 0.800 and 0.800 (development evidence). Each fails at least one reliability criterion: R3/R5/R6, R6, and R5 respectively.
  - Their status at Lead 2 remains **experimental**.
  - T43c is a price-and-hunger proxy: it tracks food-price pressure, and in 2021-26 that pressure moved against measured hunger (FORECAST_RESEARCH_II §2.4).
- **No threshold, target or rule was changed.** No model was trained or tuned in this phase.

## The closest valid outcome and its schedule

**Track A (regional experienced hunger).**
- The system's Lead-2 hunger forecast for Balance Luzon is sealed for 2027-Q1: a 98% chance that hunger is above 11.3, point value 23.6, issued 2026-10-15.
- It is logged in `out/track_a_log.csv` and will be scored when SWS publishes 2027-Q1.
- Reliability needs 10 such untouched quarters, so the earliest decision is around the third quarter of 2029.
- Even then, it would show regional hunger forecasting, not provincial food insecurity.
- All three comparators share this hunger forecast, so they cannot be told apart on this outcome.

**Track B (provincial validity, one period).** It becomes possible as soon as PSA CBMS 2024 aggregates or FNRI provincial FIES are obtained. It can test whether the province class means food insecurity. It cannot test Lead-2 timing.

## What is required to establish Lead-2 reliability against a valid outcome

1. **A repeated provincial food-insecurity measurement.** Either:
   - a provincial FIES or hunger series with at least quarterly frequency, for example quarter-of-interview FIES from FNRI, or an LGU-administered quarterly FIES module; or
   - CBMS repeated annually, which would support only an annual-horizon forecast, not Lead 2 in quarters.
2. **At least 10 untouched target quarters** of that outcome, with forecasts sealed before each publication.
3. **In the meantime, to give the label meaning:** CBMS 2024 municipal and provincial FIES (request A), plus FNRI's answer on 2022 ENNS coverage of Laguna, Quezon and Rizal (request B).

**Model tuning against the T43c proxy should stop** until item 1 or 3 exists. Further tuning would optimise a label that has not been shown to measure food insecurity.

## Actions for the researchers

- Send requests A and B (drafts in `E87_Outcome_Gap/DATA_REQUESTS.md`, updated wording in `OUTCOME_DATA_FEASIBILITY.md` §4). They need your names, signatures, the adviser's name and ethics documents. I did not send anything.
- Retry the FNRI eNutrition site, which was down on 2026-10-27/28.
- From January 2027, score the sealed forecasts (seals a498b5ef, bd6572e1, b7162a63) and Track A as each SWS quarter is published.
