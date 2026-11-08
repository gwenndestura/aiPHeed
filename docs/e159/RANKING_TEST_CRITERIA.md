# E159: does E158 rank provinces correctly?

Written 2026-11-06, **before any ranking result was computed.** The data structure was checked first: row counts per round and region only. Nothing here may change after the results are seen.

## Question
E158's 73.6 % Lead 1 accuracy tests only whether a province is above or below 50. The 2027-Q1 output reorders the five CALABARZON provinces against their latest surveys, and the LGU priority list depends on that order. This test asks whether E158 orders provinces correctly, measured against later survey results.

## Data
`backend/data/e158/out/oof.csv`: out-of-fold forecasts made as of the issue date, with no refitting.
- **Primary:** Lead 1, 72 rows over 3 rounds (ENNS2018 22, ENNS2019 25, ENNS2021 25).
- **Outcome:** `y_true`, the logit of the HFIAS moderate-or-severe share.
- **Arms:**
  - **E158:** `mu_E158`.
  - **PERS:** `y_anchor`, the province's latest survey reading, which is the ranking a user could make without the model.

## Measures
1. **Within-region concordance (primary).** Take every pair of provinces in the same region and the same round whose outcomes differ. A pair is concordant when the arm orders it the same way as the outcome; a tie in the arm counts 0.5. Lead 1 gives 40 pairs.
2. **Within-round Spearman (secondary).** The rank correlation between the arm and the outcome across all provinces in one round, reported per round and as a mean.
3. **Large-gap pairs (sensitivity).** Measure 1, restricted to pairs whose outcomes differ by at least 5 percentage points. Survey error is about ±3 points, so smaller gaps are close to ties.
4. **Leads 2 to 4 (secondary).** Measures 1 and 2 repeated. These overlap Lead 1 on the same target outcomes, so they are not independent evidence.

## Uncertainty
Bootstrap with 2,000 draws, seed 159, resampling region-round clusters for measures 1 and 3 and rounds for measure 2. Report 95 % percentile intervals.

## Pass rules (Lead 1)
- **R1, ranks provinces within a region:** E158 concordance has a 95 % interval lower bound above 0.5.
- **R2, ranks provinces nationally:** E158 Spearman is above 0 in all 3 rounds.
- **R3, adds to the latest survey:** E158 minus PERS concordance has an interval lower bound above 0. If the interval includes 0, E158 is "no better than the latest survey".

Outcomes:
- **All three pass:** E158's provincial order may be presented as informative, and the LGU list may use it.
- **R1 or R2 fails:** E158's order within a region is not evidence. The LGU ranking must not depend on differences between provinces in the same region.

## CALABARZON
Only 2 same-round pairs exist: Quezon–Rizal (2019) and Batangas–Cavite (2021). They are reported row by row, with no claim.

## Not allowed
Changing the model, the measures or the 5-point cut after seeing results; dropping rounds; tuning anything to put Quezon first.
