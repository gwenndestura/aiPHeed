# DRAFT: Thesis Results Interpretation (E13, updated). Not inserted into the approved chapters.

## Outcome Data

The study looked for an official, repeated, province-level measure of food insecurity for Cavite, Laguna, Batangas, Rizal and Quezon. None was available for 2021–2025:

- **SWS hunger estimate:** the only repeated hunger measurement. It covers Balance Luzon, an area wider than CALABARZON, with one value per quarter.
- **FNRI Food Insecurity Experience Scale:** available only as a single regional value for 2025.
- **PSA subsistence incidence:** available by province for 2021 and 2023, but most provincial estimates had coefficients of variation above 30 percent.

The accuracy of province-level food-insecurity prediction therefore could not be established. The study evaluated two narrower forecasting tasks instead.

## Forecasting Regional Hunger

At the start of each quarter, using only values published before that date, the study forecast the SWS Balance-Luzon hunger rate for that quarter. Over nine test quarters (2023-Q4 to 2025-Q4):

- **The latest published value had the lowest mean absolute error:** 4.8 percentage points.
- **The alternatives were worse:** a trend-adjusted value (4.9), the historical average (6.7) and a regularized autoregressive model (6.6).
- **Every method under-forecast** the rise in hunger during 2024 and 2025.
- **Uncertainty was underestimated:** intervals based on earlier errors covered the realized value in only two of nine quarters.

## Forecasting Provincial Food-Price Pressure

The study also forecast each province's food inflation and its deviation from the five-province average, over 11 test quarters (2023-Q2 to 2025-Q4).

**Food inflation:** no model was more accurate than the value two quarters earlier (mean absolute error 2.4 percentage points).

**Deviation from the average:** a model that shrank the latest deviation toward zero reduced the error from 1.36 to 1.18 points and met the study's pre-specified criteria. The improvement has three limits:

1. It did not hold against a forecast of no provincial difference from 2023-Q4 onward.
2. It disappeared when older data were used to allow for uncertain release dates.
3. It was observed on quarters examined in earlier analyses.

## Comparison with Official Statistics

Where sampling error allowed a clear comparison, provinces with higher subsistence incidence usually had higher relative food-price pressure in the same year: six of eight comparable pairs. Quezon, however, had the highest subsistence incidence in 2021 and the lowest relative price pressure in 2023. The comparison is descriptive and does not validate the indicator.

## Interpretation

With the available data, aiPHeed provides timely regional hunger context and provincial food-price-pressure information. It does not provide a validated forecast of provincial food insecurity. The more complex models, including LightGBM, did not outperform simple approaches.
