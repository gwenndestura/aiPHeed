# DRAFT: Suggested Chapter IV Text (E11). Not inserted into the approved chapter.

## Forecasting Accuracy

The test period contained 33 HIGH and 2 LOW province-quarters, and both LOW cases were in Quezon. Under this imbalance, a rule that always predicts HIGH reaches an accuracy of 94.3 percent while being unable to recognize a LOW quarter, so accuracy was not used to choose a model. Every approach exceeded the 75 percent accuracy figure. This result is indicative and not a definitive determination of forecasting skill, because the trivial rule also exceeds it.

The error of the predicted stress values provided the more informative comparison.

| Approach | Mean absolute error | Root mean square error |
|---|---|---|
| Carrying forward the last value | 5.22 | 6.76 |
| Regional hunger alone | 4.47 | 5.87 |
| S1 formula forecast | 4.55 | 5.92 |
| LightGBM, direct (core features) | 4.79 | 6.24 |
| LightGBM, decomposed | 4.60 | 6.32 |
| LightGBM, residual correction | 3.74 | 5.42 |

**Against carrying the last value forward,** the residual LightGBM reduced the error by 1.48 points on average, with a bootstrap interval of −2.79 to −0.17. The direct core model reduced it by 0.43 points in six of seven quarters.

**Against the S1 formula,** no LightGBM model established an improvement. The residual model reduced the average error by 0.80 points, but it was more accurate in only four of the seven quarters, and its interval of −2.20 to 0.29 includes zero. Its gain arose mainly from the two quarters with the highest stress, the fourth quarter of 2024 and the first quarter of 2025, and it was less accurate than the formula when stress fell in the fourth quarter of 2025. Adding provincial, poverty, inflation, and employment indicators to the direct model increased the gap between training and test error, which indicates overfitting given the small number of quarters.

## Differences Among Provinces

The direct LightGBM models predicted nearly identical stress for all five provinces from the second quarter of 2024 onward, while the observed difference between the highest and lowest province reached 6.5 to 14.7 points. This is because the regional hunger and inflation inputs, which are identical for every province, accounted for most of the model's splits, and the province ordering itself changed considerably from one quarter to the next.

The structures that kept the provincial term of the S1 formula preserved these differences:

- **Decomposed model:** the highest ranking agreement, 70.7 percent of province pairs, against 61.4 percent for the S1 formula. It did not reduce the stress error.

## Model Selection

No LightGBM model met the prespecified decision rule. The study therefore retains the S1 formula as the primary forecasting method and reports LightGBM as an experimental comparison. The residual design, which adds a LightGBM correction to the formula, is the most promising variant, and it will be evaluated on newly released quarters before any claim of improvement is made. These findings rest on seven test quarters that were examined in earlier exploratory analyses, so they are treated as exploratory.
