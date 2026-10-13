# DRAFT: Suggested Chapter IV Text (E9). Not inserted into the approved chapter.

*Suggested wording for review with your adviser. All values are from run `20261012T140816Z`.*

---

## Distribution of the Stress Indicator

Under the frozen threshold of 10.843, the share of province-quarters labelled HIGH rose from eight of fifteen in 2021 and 2022 to nineteen of twenty in 2024 and ten of ten in 2025. This concentration arises from the regional component of the indicator. Balance-Luzon hunger in 2024 and 2025 placed every quarter's regional level above the 2021 to 2023 reference median, and the regional hunger value alone agreed with the S1 classification in 76.2 percent of province-quarters.

Changing the provincial weight did not alter this pattern. With weights of zero, one, two, 2.74, and four, the number of HIGH test rows out of 35 was 35, 35, 33, 33, and 31, respectively. The high share of HIGH classifications is therefore a property of the target in this period, and not an error of the forecasting models.

## Forecasting Performance

Across the seven test quarters, 33 of the 35 province-quarters were HIGH. The only two LOW cases were in Quezon, in the fourth quarter of 2023 and the first quarter of 2024.

**Accuracy is not an informative measure under this imbalance.** A rule that always predicts HIGH achieved an accuracy of 0.943, and every approach exceeded the 75 percent accuracy figure. The core LightGBM model reached an accuracy of 0.971 and a balanced accuracy of 0.985. However, the carrying-forward baseline also classified both LOW cases correctly, with a balanced accuracy of 0.939. These figures rest on two cases in one province, and they are indicative and not definitive determinations of forecasting skill.

The continuous stress forecasts provided the more informative comparison.

| Approach | Mean absolute error, all quarters | Mean absolute error, final period |
|---|---|---|
| Carrying forward the last published value | 5.22 | 6.60 |
| Regional hunger alone | 4.47 | 4.10 |
| S1 rule on the latest published inputs | 4.55 | 4.25 |
| Core LightGBM | 4.54 | 5.87 |
| Compact LightGBM | 5.23 | 6.51 |
| Expanded LightGBM | 4.87 | 6.97 |

**Core LightGBM vs carrying forward.** The core model reduced the error of carrying forward by 0.68 stress points on average, with a bootstrap interval of −1.11 to −0.20 over seven quarters. It was more accurate in six of the seven quarters.

**Core LightGBM vs the simple rules.** It did not improve on the regional hunger rule or on the direct S1 rule, whose differences from the core model were 0.07 and −0.01 points, with intervals spanning zero. In the final period, the simple rules were more accurate than every LightGBM model.

**Additional indicators.** Adding provincial food-price, poverty, inflation, and employment indicators did not reduce the error. Instead, it widened the gap between training error, 1.3 to 1.5 points, and test error, 4.9 to 5.2 points, which indicates overfitting given the small number of quarters.

## Differences Among Provinces

The provinces differed considerably within each quarter, with the observed stress range between the highest and lowest province reaching 6.5 to 14.7 points. Quezon showed the largest movement. Its provincial component shifted from the lowest in 2023 to the highest in 2024 and 2025, and it accounted for the largest forecast error under every approach.

The core LightGBM model predicted nearly identical stress for all five provinces from the second quarter of 2024 onward, with a spread of zero to two points. The approaches that carried forward the latest published provincial price gap preserved more of the provincial ordering:

- **Carrying forward and the S1 rule:** 61.4 percent concordant pairs.
- **Core LightGBM:** 53.6 percent.

The provincial differences reported by the system are therefore better represented by the observed provincial food-price component of the indicator than by the machine learning forecast. Because no city or municipal measurement of hunger or food prices exists, the study did not estimate differences below the provincial level.

## Model Selection

In accordance with the pre-specified rule, the core LightGBM model was selected over carrying forward, because it reduced the stress error by more than ten percent in four of the five selection quarters. The evidence supports a limited conclusion. The model forecasts the regional stress level better than carrying forward, but it does not outperform the transparent S1 rule applied to the newly released inputs, and it does not preserve differences among provinces.

**Not demonstrated:**

1. Incremental value from the additional indicators.
2. A calibrated probability of food insecurity.
3. Performance on a blind future quarter.

These findings are based on seven reused test quarters with estimated provincial release dates. They should be regarded as exploratory.

---

*Sources:*

- `04_RESULTS.md`
- `05_ERROR_ANALYSIS_AND_INFLATION.md`
- `06_MODEL_SELECTION.md`
- `07_LIMITATIONS_DEVIATIONS_REPRODUCIBILITY.md`
