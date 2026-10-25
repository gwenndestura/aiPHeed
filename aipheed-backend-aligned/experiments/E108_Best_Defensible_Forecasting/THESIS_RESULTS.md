# E108 Deliverable F: thesis-ready results

**Evidence status.**
- Retrospective rolling-origin evaluation, 2021–2026.
- **Development evidence:** every evaluated quarter had been examined by earlier experiments, and E108's design responded to E107's diagnosis on the same quarters.
- Rules were frozen before scoring.
- **No result here has been confirmed on unseen quarters.** The sealed forecasts (`out/sealed_prospective.csv`, sha `fbc8bf91…`) are that test.

## 1. Plain summary for the panel

1. **What is forecast.** The Chapter I food-insecurity risk condition for each CALABARZON province: regional hunger above 11.3% **and** provincial food-price pressure.
   - It is a composite risk proxy.
   - No measured provincial food-insecurity outcome exists in the project.
   - The only directly observed measure, SWS hunger, is regional and was analysed separately.
2. **How.** Risk probability = (regional hunger outlook from the latest SWS round) × (LightGBM probability of provincial food-price pressure from all 12 aiPHeed indicators). This follows the target's own AND rule and stops the model being taught that price pressure means low risk.
3. **Lead time.** One-quarter-ahead forecasts are strong: accuracy 0.89, balanced accuracy 0.87, 13 of 16 high-risk cases detected, AUC 0.92, over 13 quarters.
   - They miss one pre-registered check: the most recent four quarters, where "always low" did better.
   - So **no lead time is established as reliable**, and Lead 1 is the only horizon with supporting evidence.
   - **Two to four quarters ahead the forecasts are not reliable.**
4. **What drives it.** Almost entirely food-price information (the CPI projection), plus the regional hunger reading. Climate, vulnerability and news indicators are included but add no measurable predictive value with the data available.
5. **Regional hunger** cannot be forecast better than its latest published SWS reading.

## 2. Objective-by-objective assessment (Chapter I §1.5.2)

| Objective | Status | Evidence |
|---|---|---|
| 1. NLP pipeline (FSSI, BERTopic) | **Achieved as a pipeline. Its forecasting contribution is not demonstrated.** | FSSI-v3 is in the model (N1) but has values for only 17% of province-quarters and never enters a fitted tree (`INDICATOR_AUDIT.md` §3–4) |
| 2 I–IV. Accuracy, precision/recall, F1, AUC of LightGBM | **Achieved (reported)** | Lead 1: accuracy 0.892, precision HIGH 0.76, recall HIGH 0.81, F1 0.79, AUC 0.917 (`MODEL_COMPARISON.md`) |
| 2 V. Furthest reliable horizon by walk-forward expanding-window evaluation | **Inconclusive at Lead 1; not reliable at Leads 2–4. No reliable horizon established.** | `MAX_LEAD_DECISION.md` |
| 3. Municipal rankings from **validated** province forecasts | **Not achieved as worded.** The province forecasts are not validated on unseen data; rankings remain a weighting of unvalidated forecasts. | — |
| 4. Comparison with the four baselines | **Achieved.** At Lead 1, F1 beats persistence (p = 0.006), NLP-only (p = 0.008) and logistic-12 (p = 0.027). It ties PSA-only (p = 0.24). The PSA-only logistic itself meets the reliability rule at Lead 1 (post hoc). | `MODEL_COMPARISON.md` §1 |
| 5. Dashboard, ISO 25010, FNRI face validity | **Not in E108 scope.** The dashboard is unchanged, and E108 is exposed only through read-only API routes. | — |
| Brief: all 12 indicators in LightGBM | **Achieved and verified** | 13 columns in the fitted booster; per-family future-perturbation tests at feature and prediction level |
| Brief: ≥ 75% accuracy | **Met at Lead 1 only** (0.892; cluster 95% CI 0.79–0.99). Not met at Leads 2–4 (0.60–0.69). | — |
| Brief: food insecurity not confused with price pressure | **Achieved in wording and design.** The target is labelled a composite proxy; the LightGBM part is labelled price pressure; SWS hunger is analysed separately. | `METHODOLOGY.md` §2 |

## 3. Suggested wording (Chapter IV results / discussion)

> **Objective 2-V.** The forecasting model combined the regional SWS hunger outlook with a LightGBM classifier of provincial food-price pressure that used all twelve aiPHeed indicators. It was evaluated by walk-forward expanding-window validation at one to four quarters ahead, under a reliability rule fixed before scoring.
>
> One quarter ahead, the model correctly classified 89% of 65 province-quarters (95% CI 79–99%, by quarter), detected 13 of 16 high-risk cases and outperformed naive persistence. It did not outperform a constant "low-risk" forecast during the four most recent quarters, which contained one high-risk case. One-quarter-ahead forecasting is therefore supported by the evidence but not established as reliable.
>
> Two to four quarters ahead, accuracy (60–69%) fell below that of a constant "low-risk" forecast. The furthest reliable forecasting horizon therefore could not be established with the 2021–2026 data.

> **Indicator contribution.** Predictive skill came almost entirely from food-price information. Removing it reduced one-quarter accuracy from 89% to 68%. Climate, vulnerability and news indicators, although included, did not measurably improve the forecasts. The likely reasons are limited variation and coverage: the news index was available for only 17% of province-quarters.

> **Target.** The forecast target is a composite risk condition. It combines a regional hunger survey with provincial food prices, and it is not a direct measurement of provincial food insecurity.

## 4. Limitations and implications for DA

1. **No provincial food-insecurity ground truth.** Provincial differences in the forecast come from price inputs only.
2. **Small sample.** 19 SWS outcome quarters and 7–13 evaluable quarters per lead.
3. **No untouched historical test.** The verdicts become confirmatory only when the sealed forecasts are scored against 2026-Q4 and later outcomes.
4. **Hunger surges are not anticipated.** The hunger factor carries the latest SWS round forward, so a surge before it appears in a published round (as in 2023-Q4) is missed.
5. **For DA use:** treat a HIGH forecast as a one-quarter early signal of price-driven risk during elevated hunger, to be checked against official PSA, DA and DSWD information. It is not an assessment of food insecurity, and it is not a substitute for field verification.
6. **Data needed for stronger claims:**
   - more SWS quarters (each year adds 4);
   - a provincial outcome (CBMS food-shortage items, provincial FIES);
   - publication-dated real-time data vintages;
   - leading price information beyond the latest CPI index.
