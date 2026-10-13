# DRAFT: Suggested Chapter III Text (E9). Not inserted into the approved chapter.

*Suggested wording for review with your adviser. Numbers and sources are in the E9 records listed at the end.*

---

## Forecasting Target: The Corrected Food Insecurity Stress Indicator (S1)

The study used a constructed stress indicator as the forecasting target, in accordance with Equation 3 of the approved methodology. For each province p and quarter t, the stress value was computed as the Social Weather Stations (SWS) Balance-Luzon involuntary hunger prevalence for the quarter, plus two times the difference between the province's food inflation rate and the mean food inflation rate of the five CALABARZON provinces. The hunger component is a regional value shared by all five provinces, while the second component reflects relative provincial food-price pressure arising from the Philippine Statistics Authority (PSA) provincial food consumer price index. The coefficient of two was retained as a documented design parameter. This is because there is no independent provincial food insecurity outcome available against which a different weight could be estimated.

The corrected version of the indicator, referred to as S1, applied four rules to the original computation:

1. A missing input produced a missing value and was never replaced with zero.
2. The five-province mean was computed only when all five provinces had a value for the quarter.
3. Only complete quarters were used as labels.
4. The HIGH or LOW status of a quarter was determined against a frozen reference threshold, defined as the median stress of the labelled quarters whose data had been published before a stated date.

For the historical evaluation, the reference date was set to 1 October 2023, the start of the first test quarter. This produced a threshold of 10.843, computed from eight labelled quarters between 2021 and the second quarter of 2023. A province-quarter was labelled HIGH when its stress value exceeded this threshold. The threshold is empirical and indicative, and not an official government cutoff.

## Data Eligibility and Timing

The study used data from the first quarter of 2021 to the fourth quarter of 2025 only. No value after the fourth quarter of 2025 was read, and no pre-2021 value was used. A data-access guard enforced this boundary in software:

- every input file was verified against a recorded cryptographic hash;
- only the required columns were read;
- rows after the fourth quarter of 2025 were excluded during the read itself, so that later values never entered the analysis.

Files identified as potentially containing protected 2026 outcomes, as well as databases, model files, and news-derived tables, could not be opened by the experiment.

Each input was aligned to the information available at the forecast origin, defined as the first day of the target quarter:

- **Regional hunger:** the latest SWS round published before the origin.
- **Provincial food inflation:** the value two quarters before the target, used only when its release date fell before the origin.
- **Last published stress value:** the latest label whose hunger and price components had both been released before the origin.

Provincial price release dates were estimated as the national release date plus fourteen days, because verified provincial release dates were available for only one quarter. Inputs dated in this way were treated as indicative and not verified.

## Forecasting Models

Seven forecasting approaches were compared under identical conditions.

**Simple baselines (four):**

1. Carrying forward the last published stress value.
2. Using the latest published regional hunger value alone.
3. Applying the S1 formula directly to the latest published inputs.
4. Predicting the most frequent training class.

**LightGBM models (three):**

1. A core model using regional hunger, its change, and the last published stress value.
2. A compact model that added provincial food-price indicators.
3. An expanded model that further added poverty incidence, regional headline inflation, and unemployment.

All LightGBM models used fixed settings selected before evaluation, with no hyperparameter search and no class weighting. Each model was trained twice per fold: once to estimate the probability that stress would exceed the threshold, and once to predict the stress value itself.

## Validation Design

The models were evaluated through chronological walk-forward validation. For each test quarter, a model was trained only on quarters whose labels had been published before that quarter began, and it was required to have at least eight such quarters. All preprocessing, feature filtering, and calibration decisions were made within the training portion of each fold. Predictions were written and sealed before the outcomes of the test quarters were revealed.

**Test quarters:** seven, from the fourth quarter of 2023 to the fourth quarter of 2025.

- **Selection period:** the first five quarters, used for model selection.
- **Final period:** the last two quarters, held out from selection.

**Independence.** Because the five provinces share one regional hunger value per quarter, the evaluation treated each quarter, and not each province, as the independent unit. Uncertainty was summarized using a bootstrap that resampled whole quarters.

**Classification rule.** A probability of 0.50 or higher was classified as HIGH, a probability below 0.50 as LOW, and a forecast with a missing or stale required input as INSUFFICIENT_DATA. Model probabilities were reported as uncalibrated, because the training data never provided enough evidence to calibrate them.

## Model Selection Rule

The selection rule was fixed before the experiment was run. Starting from the simplest approach, a more complex model was adopted only when its mean absolute error in predicting stress was at least ten percent lower than the current model's, and it was more accurate in at least three of the five selection quarters. The classification results were reported but were not used for selection, because the test period was expected to contain very few LOW outcomes.

---

*Sources:*

- `01_S1_FORMULA_AND_TARGETS.md`
- `02_DATA_ELIGIBILITY_AND_FEATURE_AVAILABILITY.md`
- `03_FROZEN_PROTOCOL.md`
