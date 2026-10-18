# Chapter IV material: forecasting results (E55)

*Draft text for the Results and Discussion chapter. Figures come from `FINAL_REPORT.md` and `tables/`. All historical results are development evidence and must be presented as such.*

## 4.x Definition of the Forecast Target

In accordance with Section 1.7, the study determined food insecurity risk from SWS quarterly hunger data and PSA food price data. A province was classified as HIGH risk in a quarter when the Balance Luzon hunger rate exceeded 11.3 percent, the 60th percentile of the 2021 to 2022 reference rounds, and the province simultaneously experienced food-price pressure. Food-price pressure meant that its food inflation, or its food inflation minus headline inflation, exceeded its own 2021 to 2022 60th percentile. The classification therefore represents a food insecurity risk indicator arising from elevated regional hunger and a provincial shock to food access, and not a measured prevalence of household food insecurity.

The composite label described in the methodology (regional hunger plus twice the provincial food-price deviation, compared with a median) was retained for comparison. It was not used as the primary target, for two reasons. First, its global median requires quarters that occur after the forecast is issued. Second, the doubling of regional hunger from 2024 onward placed between 89 and 93 percent of the 2024 to 2026 province-quarters above any single threshold, so that a rule predicting HIGH for every quarter outperformed every model. This is an inherent constraint of the available hunger series rather than a defect of the forecasting code.

Because SWS hunger is published as a single value for Balance Luzon, provincial differences in risk arise only from provincial food prices. Hunger remained above the threshold in every quarter from 2023-Q4 to 2026-Q3, so the evaluation measured the system's ability to anticipate provincial food-price shocks under elevated regional hunger. It could not measure the system's ability to anticipate a change in the hunger condition itself.

## 4.x Forecasting Model and Evaluation Design

The proposed model combined two components.

The first was a LightGBM classifier of provincial food-price pressure. Its starting score was the base-effect projection of provincial food inflation computed from PSA CPI. Its shallow trees used the five trigger groups, news-derived signals, and rice-policy orders. The trees were constrained so that they could redistribute risk across provinces and quarters but could not carry forward a general level shift from an earlier price regime.

The second component estimated the probability that regional hunger would remain above the threshold. The forecast probability is the product of the two.

Each forecast was issued on the first day of a quarter for the following quarter, using only information published before the issue date. For example, the forecast issued on 1 October 2026 targets the first quarter of 2027. Model settings were selected at each issue date using earlier quarters only. The evaluation protocol was frozen before any result was computed, and the full run was repeated with byte-identical outputs.

## 4.x Model Performance and Baseline Comparison

Table 4.x reports performance on 45 province-quarters (nine quarters, 2024-Q3 to 2026-Q3, 14 HIGH and 31 LOW), which all models share.

| Model | Accuracy (95% CI) | Balanced accuracy | Recall (HIGH) | Recall (LOW) | F1 | Brier | AUC |
|---|---|---|---|---|---|---|---|
| Proposed LightGBM (E55) | 0.733 (0.62–0.84) | 0.709 | 0.643 | 0.774 | 0.600 | 0.180 | 0.779 |
| Naive persistence | 0.600 | 0.592 | 0.571 | 0.613 | 0.471 | 0.400 | 0.592 |
| PSA-only (logistic) | 0.378 | 0.333 | 0.214 | 0.452 | 0.176 | 0.598 | 0.295 |
| PSA-only (LightGBM) | 0.400 | 0.290 | 0.000 | 0.581 | – | 0.424 | 0.221 |
| NLP-only (logistic) | 0.667 | 0.523 | 0.143 | 0.903 | 0.211 | 0.235 | 0.488 |
| NLP-only (LightGBM) | 0.644 | 0.546 | 0.286 | 0.806 | 0.333 | 0.267 | 0.450 |
| Logistic regression (combined) | 0.333 | 0.301 | 0.214 | 0.387 | 0.167 | 0.646 | 0.247 |

The proposed model obtained the lowest Brier score and the highest balanced accuracy among all models, and it identified both HIGH and LOW quarters with recall above 0.60. Its accuracy of 0.733 fell one province-quarter short of the 75 percent development goal.

A ridge-based component model evaluated on the same rows reached 0.756. The difference between the two models was not statistically distinguishable (paired Brier difference 0.007, 95% CI −0.016 to 0.025).

These results should be read as development evidence, since every evaluated quarter had been examined in earlier experiments. With nine evaluable quarters, the confidence interval for accuracy spans roughly 0.62 to 0.84. Establishing a lower bound of 75 percent would require about 62 independent quarters if the true accuracy were 0.80, or about 16 if it were 0.85. The forecasts for 2027-Q1 were therefore frozen before their outcomes exist and serve as the independent test.

## 4.x Factors Affecting the LightGBM Model

A series of controlled diagnostics was used to identify why earlier LightGBM versions underperformed.

A conventional LightGBM classifier reached only 0.533 accuracy because it predicted HIGH for most quarters, carrying forward the price relationships of the 2022 to 2023 inflation period into the period after the 2024 rice tariff reduction. Supplying the CPI base-effect projection as the model's starting score raised accuracy to between 0.711 and 0.756. Increasing tree complexity, tuning the decision threshold, and applying post-hoc calibration each reduced performance.

These findings indicate that, with roughly 100 training province-quarters, LightGBM performs best when it refines a structural price projection, and not when it learns price relationships from the data alone.

## 4.x Contribution of Poverty and the Five Triggers

The 2021 PSA Small Area Estimates of city and municipal poverty incidence, aggregated to provincial means, were added to the model under three timing assumptions. In every case the forecasts were identical to those of the model without poverty. Earlier tests on the ridge-based models showed the same result.

A static provincial poverty value cannot explain why risk changes from one quarter to the next. Poverty was therefore retained in its intended role under Objective 3, as a vulnerability weight for the relative prioritization of the 142 cities and municipalities, and not as a forecasting input.

Among the five trigger groups, Market and Prices ranked first in 56 of the 60 SHAP explanations. Employment, OFW remittances, and climate made smaller contributions. Fish-kill, news, and rice-policy inputs were never selected by the trees. Removing any single group did not reliably worsen the forecast. The non-market triggers therefore remain documented model inputs with small or no measurable effect, and not proven predictors.

## 4.x Explanations

Each forecast on the dashboard is accompanied by exact SHAP values computed with the TreeSHAP algorithm. These were verified against an independent SHAP implementation and reconstruct the model's output to within 1e-9. Contributions are grouped into the five trigger groups, with the CPI projection counted under Market and Prices. The regional hunger component is shown separately, and trigger groups with missing data at the issue date are disclosed as limited data.

The dashboard presents two or three leading factors in plain language. For example, food insecurity risk in Quezon for the first quarter of 2027 was forecast LOW (15 percent probability), mainly because Market and Prices and Employment lowered it. These attributions describe the model's reasoning and are indicative, and not definitive determinations of cause.

## 4.x Limitations

Five limitations apply to these results.

First, hunger is measured only at the regional level, and it stayed elevated throughout the evaluation period, so the hunger component of the risk definition could not be validated.

Second, the evaluation rests on nine quarters, which is too few to establish a 75 percent accuracy with statistical confidence.

Third, employment, remittance, ENSO, and policy indicators are national, and 2026 remittance data were not yet in the dataset.

Fourth, the municipal rankings are derived from province forecasts and are not independent municipal forecasts.

Fifth, the ISO/IEC 25010 evaluation by DA Region IV-A personnel and the comparison with DOST-FNRI NNS figures remain to be conducted and are reported separately from model development.
