# E131 diagnostic report: why the objectives are not being met

This diagnosis rests on:
- E130 (gate, lead mapping, reference uncertainty), re-checked against the data;
- E109–E114 and E128 (earlier forecasting runs);
- E131's own experiments.

Each cause is classified by what would fix it.

| # | Cause | Evidence | Kind | Fixable by code? |
|---|---|---|---|---|
| 1 | **No quarterly provincial food-insecurity measurement** | PSA subsistence is provincial only in survey years: 2021 and 2023, with no 2025 provincial table (owner-verified). FNRI FIES covers 2 provinces in 1 round. CBMS is one window and not held. | Target / data | No |
| 2 | **Provincial food deprivation is driven by income, which is not measured between survey rounds** | 2021→2023 income effects: Quezon −6.0, Laguna −2.4, Cavite −1.7 points; price effects +0.1 to +1.7 (`out/x3a_price_income_decomposition.csv`) | Data | No |
| 3 | **CPI tracks the official food threshold only loosely** | CPI-updated threshold misses by −16.2 % (Laguna) and −6.4 % (Rizal) | Measurement | No; it is a property of the data |
| 4 | **The measured quarterly target (SWS) moves more than any predictor anticipates** | Lead-2 RMSE 6.5–7.8 points against a needed error SD of about 2.0 points (`out/e131_summary.json`). Every sharp increase is missed: 0 of 7, mean error −9.6. | Predictability (data) | Partly: only with new predictors |
| 5 | **75 % agreement within the measurement tolerance means forecasting as precisely as the survey measures** | Analytic requirement: error SD ≤ 1.022 × SE, and the median SWS SE is 1.95 points. An oracle would score 90 %. | Objective definition | A design choice (§ below) |
| 6 | **Few independent quarters** | 20 SWS quarters × 4 areas. Only 7–9 shared evaluation quarters once learned models have 8 training quarters. | Data | Partly: prospective accumulation |
| 7 | **Regime shifts** | The 2024 surge (Balance Luzon 11 → 25) and the 2025 respondent-base change (household heads → adults). High-level quarters are under-predicted by 7.1 points on average. | Data / measurement | No; it can be monitored |
| 8 | **The learned models overfit** | LGBM-ALL: training MAE 2.1 against 6.1 out of sample; all 100 trees split | Methodology | Yes. Regularization does not help when there is no signal. |
| 9 | **Trigger groups add no stable skill** | Ablation effects of a few points, unstable in sign. In ridge, the market group *hurts* (removing it lowers MAE by 2.25). E114, on untouched 2013–2020 data, found the same. | Data / predictability | Only with better drivers, chiefly income |
| 10 | **Issue timing** | At the quarter-start issue, Lead 2 is 3 quarters past the newest SWS reading. Issuing after the release helps persistence at Lead 2 (MAE 5.04 against 5.98 on the univariate set). | Design | Yes: a dashboard re-issue, needing owner approval |

## What can be solved by code, data, methodology or design

| Kind | Items | Status in E131 |
|---|---|---|
| Code | #8, #10 | Done: measurement-aware model (LLM), operational lead mapping, release-anchored policy evaluated |
| Better data | #1, #2, #4, #6 | Not available today. Needed: quarterly provincial income or FIES measurement, CBMS 2024, and more SWS quarters (prospective). |
| Methodology | #3, #9 | Done: price-versus-income decomposition, ablation, area-level CPI |
| Target measurement | #1, #5 | Done: the measured target is fixed as SWS (areas) and PFDR (provinces, survey years) |
| Research design | #5, #10 | Owner decisions: the agreement tolerance (only prospectively), and the dashboard re-issue timing |
