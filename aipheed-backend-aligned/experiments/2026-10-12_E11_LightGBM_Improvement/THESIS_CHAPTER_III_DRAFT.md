# DRAFT: Suggested Chapter III Text (E11). Not inserted into the approved chapter.

## Forecasting Target

The forecasting target is the corrected composite stress indicator (S1). For each province and quarter, S1 adds the Balance-Luzon involuntary hunger estimate of the Social Weather Stations (SWS) to two times the difference between the province's food inflation rate and the mean food inflation rate of the five CALABARZON provinces. Missing inputs remain missing and are never replaced with zero. The five-province mean is computed only when all five provinces have a value. A quarter is labelled HIGH when its stress value is strictly greater than 10.843, the median stress of the labelled quarters published before 1 October 2023. The indicator is constructed from public data and is not an independent measurement of provincial food insecurity.

## Data and Timing

The study used PSA provincial food price indices, SWS hunger estimates, and selected regional indicators from the first quarter of 2021 to the fourth quarter of 2025. Every input file was verified against a recorded cryptographic hash, and a data-access guard excluded any record after the fourth quarter of 2025. Each input was aligned to the information available on the first day of the target quarter, in accordance with the release dates of its source. Provincial price release dates were estimated from national release dates and were treated as indicative and not verified. News-derived indicators were excluded, because their coverage, geographic attribution, and source files could not be established as eligible.

## Models Compared

Four simple baselines were evaluated:

1. carrying forward the latest published stress value;
2. the latest regional hunger value alone;
3. the S1 formula applied to the newly released inputs;
4. predicting the most frequent training class.

LightGBM was examined in three structures:

1. a direct structure that predicts the stress value itself;
2. a decomposed structure that predicts only the province's relative food-price deviation and adds it to the latest regional hunger value;
3. a residual structure that predicts a correction to the S1 formula forecast.

The feature sets ranged from three regional and persistence features to thirteen features that added provincial food-price, poverty, regional inflation, and employment indicators. Four configurations were prespecified, from single-split trees with strong regularization to moderately deep trees. No class weighting was applied.

## Validation Design

The models were evaluated through chronological walk-forward validation on seven test quarters, from the fourth quarter of 2023 to the fourth quarter of 2025. For each test quarter, models were trained only on quarters whose data had been published before that quarter began, and all provinces of a quarter were kept together. The LightGBM configuration was selected within each training set through an inner walk-forward validation, so that the test quarter never influenced the choice. Predictions were saved and sealed before the test outcomes were revealed. Because the five provinces share one regional hunger value, each quarter, and not each province, was treated as the independent unit. Uncertainty was summarized using a bootstrap that resamples whole quarters.

## Decision Rule

The decision rule was fixed before the experiment. A LightGBM model would be recommended over the S1 formula only if it met all four conditions:

1. it reduced the stress error in at least five of the seven quarters;
2. its average improvement had a bootstrap interval entirely below zero;
3. it ranked provinces at least as well as the S1 formula;
4. it improved in the same direction under a shorter, rolling training window.
