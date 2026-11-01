# Lead 2 issued after the SWS release: thesis-ready text

Because the two-quarter-ahead (Lead 2) forecast is limited by the age of the newest hunger survey, its issue date was moved, under a protocol frozen before scoring (SHA-256 `1328f059…`), from the first day of the following quarter to the day after the SWS round for the origin quarter is published. The issue date was capped at 67 days after the quarter ends, the 90th percentile of verified publication lags. The target quarter, the model, the threshold and the seven reliability criteria were unchanged. The always-LOW, climatology and persistence baselines were recomputed at the new issue date, so they also received the fresher survey.

This shortened the hunger information gap from three quarters to two, at the cost of about one month of warning (median lead time 152 days instead of 182). It made the 2023-Q4 hunger surge, published on 22 January 2024, available for the 2024-Q2 target.

On the same 65 province-quarters (13 quarters), the served model issued after the SWS release reached:

- accuracy 0.800 (95% CI 0.69–0.89), balanced accuracy 0.732 and ROC-AUC 0.760;
- a Brier score of 0.167, against 0.194 at the original issue date;
- 4 of 10 province onsets anticipated, compared with none before.

It met six of the seven criteria. It beat persistence (0.754) and climatology on accuracy, and on Brier score (p = 0.052 and 0.067).

It failed the recall criterion: 10 of 17 high-risk province-quarters (0.588, against 0.60 required). All seven remaining misses came from the food-price component, which by design still used CPI only up to the original issue date. Its accuracy and balanced-accuracy passes also depended on a single borderline survey quarter (Balance Luzon 2023-Q2, exactly 11.3%), and across simulated SWS sampling error all classification criteria passed together in only 6% of draws.

A Kalman hunger variant failed two criteria. On independent 2002–2020 data its advantage over persistence held only under the main assumption about pre-2021 release dates.

**Lead 2 therefore remains experimental, but post-SWS issuance is the first change that removes the hunger-information limit.** The remaining limit is the food-price forecast. Confirming either this result or a version with a refreshed price component requires a separately pre-registered price variant and forecasts sealed after each SWS release from 2027, with about ten resolved quarters (around late 2029).
