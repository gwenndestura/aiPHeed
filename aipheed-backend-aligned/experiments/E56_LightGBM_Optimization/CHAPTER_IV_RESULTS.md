# Chapter IV results (final model, E56)

*Thesis-ready text based on the generated outputs in `runs/20261018T132444Z` and `tables/`. It supersedes the E55 draft where the two differ.*

## 4.x Forecast Target and Horizon

In accordance with Section 1.7, food insecurity risk was determined from SWS quarterly hunger data and PSA food price data. A province was classified as HIGH risk in a quarter when the Balance Luzon hunger rate exceeded 11.3 percent, the 60th percentile of the 2021 to 2022 reference rounds, and the province also experienced food-price pressure. Food-price pressure meant that its food inflation, or its food inflation minus headline inflation, exceeded its own 2021 to 2022 60th percentile. The classification is a risk indicator arising from elevated regional hunger and a provincial shock to food access, and not a measured prevalence of household food insecurity.

Forecasts were produced two quarters ahead of the latest predictor quarter. Each forecast was issued on the first day of a quarter using only information published before that date, and it targets the quarter after the issue quarter. The dashboard forecast for the first quarter of 2027 was therefore issued on 1 October 2026 from predictors through the third quarter of 2026. At that date, observed food insecurity risk was available only through the second quarter of 2026, since the third-quarter SWS round and the September 2026 CPI were released after the issue date. The direct household food insecurity measures, namely the FNRI FIES and the PSA subsistence incidence, end in 2023 and were used only as reference figures.

## 4.x Model Optimization

The proposed LightGBM model forecasts provincial food-price pressure and multiplies this by the probability that regional hunger remains elevated.

The LightGBM component starts from the base-effect projection of provincial food inflation computed from PSA CPI. Its trees then adjust that projection using the five trigger groups, news-derived signals, and rice-policy orders. The trees were constrained so that they could redistribute risk across provinces and quarters but could not carry forward the general price level of an earlier regime.

A single bounded optimization cycle evaluated 72 configurations of tree size, learning rate, number of boosting rounds, minimum leaf size, feature and row subsampling, L1 and L2 regularization, class weighting, recency weighting, and the inclusion of poverty. At each forecast origin, the configuration was selected by nested chronological validation using earlier quarters only. The evaluation protocol was frozen before any result was computed, and the full run was repeated with identical outputs.

## 4.x Forecasting Performance

Table 4.x reports two-quarter-ahead performance on 45 province-quarters from 2024-Q3 to 2026-Q3 (14 HIGH and 31 LOW), which all models share.

| Model | Accuracy (95% CI) | Balanced accuracy | Recall HIGH | Precision HIGH | Recall LOW | Precision LOW | F1 | Brier | AUC |
|---|---|---|---|---|---|---|---|---|---|
| Proposed LightGBM | 0.778 (0.69–0.87) | 0.760 | 0.714 | 0.625 | 0.806 | 0.862 | 0.667 | 0.178 | 0.763 |
| Naive persistence | 0.600 | 0.592 | 0.571 | 0.400 | 0.613 | 0.760 | 0.471 | 0.400 | 0.592 |
| Majority class (LOW) | 0.689 | 0.500 | 0.000 | – | 1.000 | 0.689 | – | 0.311 | – |
| PSA-only (logistic) | 0.378 | 0.333 | 0.214 | 0.150 | 0.452 | 0.560 | 0.176 | 0.598 | 0.295 |
| PSA-only (LightGBM) | 0.400 | 0.290 | 0.000 | 0.000 | 0.581 | 0.562 | – | 0.424 | 0.221 |
| NLP-only (logistic) | 0.667 | 0.523 | 0.143 | 0.400 | 0.903 | 0.700 | 0.211 | 0.235 | 0.488 |
| NLP-only (LightGBM) | 0.644 | 0.546 | 0.286 | 0.400 | 0.806 | 0.714 | 0.333 | 0.267 | 0.450 |
| Logistic regression (combined) | 0.333 | 0.301 | 0.214 | 0.136 | 0.387 | 0.522 | 0.167 | 0.646 | 0.247 |

The proposed model reached 77.8 percent accuracy and a balanced accuracy of 0.760. It correctly identified 10 of the 14 HIGH-risk and 25 of the 31 LOW-risk province-quarters, and it obtained the lowest Brier score of all models. It met the development goal of 75 percent accuracy with both class recalls above 0.60. Its minimum accuracy when any single quarter was left out was 0.75.

The model also distinguished between provinces within the same quarter: the within-quarter AUC was 0.767, and the five provincial decisions differed in six of the nine quarters. Accuracy was highest for Rizal (1.00) and Quezon (0.89), and lowest for Cavite (0.44), where the model tended to overstate risk.

These results are development evidence and not independent validation, for four reasons.

First, all evaluated quarters had been examined during earlier model development.

Second, the accuracy interval spans 0.69 to 0.87. The gain over the previous LightGBM version (0.733) amounts to two province-quarters and is not statistically distinguishable.

Third, the improvement in Brier score was significant against naive persistence but not against the majority-class rule.

Fourth, the forecasts were on average about 10 percentage points too high (calibration-in-the-large −0.10, calibration slope 0.81).

Because hunger remained above the threshold in every evaluated quarter, the results reflect the model's ability to anticipate provincial food-price shocks under elevated regional hunger. In the single earlier case where hunger rose sharply (2024-Q2), the model did not anticipate the increase. Establishing a 75 percent lower bound with statistical confidence would require considerably more quarters than the nine available. The forecasts for the first quarter of 2027 were therefore frozen before their outcomes exist and constitute the independent test.

## 4.x Contribution of Predictors

SHAP values computed with the TreeSHAP algorithm show that Market and Prices, which includes the projected food inflation from PSA CPI, was the leading factor in nearly every forecast. Employment, OFW remittances, and climate made smaller contributions, while fish-kill and news-derived inputs had little or no measurable effect.

Poverty was evaluated as a candidate predictor using the 2021 PSA Small Area Estimates. The optimization selected it at four of the twelve forecast origins, but earlier controlled comparisons showed that it did not improve out-of-sample performance. Poverty was therefore retained in its intended role as a vulnerability weight for the relative prioritization of the 142 cities and municipalities, and not as a demonstrated predictor of quarterly change.

These attributions describe the model's reasoning, are indicative, and are not definitive determinations of cause.

## 4.x Forecast for the First Quarter of 2027

All five provinces were forecast at LOW food insecurity risk for the first quarter of 2027:

| Province | Probability |
|---|---|
| Quezon | 14.6 percent |
| Cavite | 10.9 percent |
| Laguna | 7.0 percent |
| Rizal | 5.0 percent |
| Batangas | 4.3 percent |

The model estimated a 96 percent probability that regional hunger would remain above the threshold. However, provincial food-price pressure was projected to be low, mainly because Market and Prices and Employment lowered the estimated risk. The forecast used CPI through August 2026 and SWS hunger through the second quarter of 2026. OFW remittance data were not yet available for 2026, so the dashboard reports the data status as limited.
