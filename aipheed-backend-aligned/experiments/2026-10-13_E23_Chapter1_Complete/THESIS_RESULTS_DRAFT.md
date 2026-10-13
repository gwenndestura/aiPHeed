# Chapter IV draft: Results organized by the Chapter I objectives (E23)

*Draft for the adviser's review. Numbers come from `RESULTS_TABLES.md`, which is generated from sealed runs.*

## A. Supported findings

**Objective 1.** The two-tier NLP pipeline was implemented. It produces the bias-corrected FSSI, its lags and acceleration, five trigger shares and BERTopic topic shares for every province-quarter from 2021 to 2025.

**Objective 2.** The proposed LightGBM model was evaluated with walk-forward expanding-window validation at lead times of one to six quarters. Timing was strict:

- news of the origin quarter;
- government indicators of the previous quarter;
- SWS rounds and training labels only after their verified publication dates.

Accuracy, precision, recall, F1-score, ROC-AUC and the Brier score were computed for every lead.

**Objective 3.** All 142 city and municipal rankings were produced with the poverty-incidence and population-density weights. An independent re-implementation reproduced them exactly.

**Objective 4.** The proposed model was compared with all six H3 baselines on identical test rows. The four Objective 4 baselines map onto them.

**Objective 5.** A development dashboard was built, with:

- forecast-period, supporting-news and cutoff labels;
- data-insufficiency states;
- SHAP-based results;
- the rankings;
- a PDF report generated from the same forecast record.

The regional anchor was verified in the DOST-FNRI 2023 National Nutrition Survey. CALABARZON's moderate-to-severe household food insecurity was 19.1% (95% CI 17.0–21.1), the lowest of the 17 regions, against 31.4% nationally.

**Quarterly operation.** A configuration-driven update cycle was implemented and tested. It:

- uses only news published (Philippine time) in the quarter before the target and before the declared cutoff;
- records every input's hash, availability date and vintage;
- reports "insufficient data" instead of producing a forecast from stale or unauthorized inputs.

## B. Findings that do not support the proposed model

1. **Classification at all lead times.** On the composite label with a training-window median threshold, the test quarters (2023-Q4 to 2026-Q1) contained only three LOW province-quarters at lead 1 and two or fewer at longer leads. This is because regional hunger rose after 2023. No lead time met the predeclared evaluability condition (at least 8 origins and 5 cases of each class). The maximum reliable lead time is therefore **none**, and H1–H3 could not be tested.
2. **Comparison with persistence.** At lead 1, naive persistence was more accurate than the proposed model (0.875 vs 0.825), had a higher ROC-AUC (0.779 vs 0.703) and a lower Brier score (0.125 vs 0.142).
3. **Sensitivity target (fixed threshold of 14.6).** Lead 1 had five LOW cases. The proposed model had the highest ROC-AUC (0.760), but no difference from any baseline was statistically significant after Holm adjustment. The government-only LightGBM was more accurate (0.775 vs 0.750).
4. **Improvement round (E23-B).** A separately pre-registered improvement round added lagged label, trend and rolling features with nested selection. It reached 0.850 accuracy at lead 1. That is above 75%, but still below persistence (0.875) and below a constant "high risk" prediction (0.925). **Accuracy above 75% is therefore not evidence of forecasting skill on these data.**
5. **SHAP attribution.** The largest SHAP contributions came from price levels that trend over time. The FSSI ranked seventh of 44 inputs, and the news features carried about 6% of total attribution.

## C. Results awaiting participants

H4 (ranking consistency) and H5 (ISO/IEC 25010 functional suitability, accuracy and usability) require responses from the 50 DA Region IV-A evaluators. The questionnaire, consent text, facilitator guide and scoring script with predeclared decision rules are ready. **No response has been collected or simulated.**

## D. Limitations to state in the thesis

1. **The label is mostly regional.** About 68% of the label's variance is the regional SWS hunger level, which is shared by all five provinces.
2. **Weak data at two levels:**
   - unemployment is a national series;
   - 126 of the 142 LGUs have only a province-mean poverty value.
3. **No independent provincial outcome.** No independent provincial food-insecurity outcome exists to validate the forecasts below the regional level.
4. **No untouched holdout yet.** The 2021–2026-Q2 quarters were examined during development. The first untouched evaluation will be the sealed 2026-Q4 forecast, once its outcomes are published and authorized.
