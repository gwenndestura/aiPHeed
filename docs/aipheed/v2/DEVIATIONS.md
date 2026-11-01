# v2 deviations from the pre-registration

Every change made after fitting began (first run of `backend/scripts/v2_validate.py`) is listed here. Results affected by a substantive deviation are labelled EXPLORATORY.

| # | When | What | Substantive? | Effect |
|---|---|---|---|---|
| 1 | After the first validation run | **RIDGE-ALL context baseline:** it has no forecast on rows with < 20 training rows. The first run scored those missing forecasts as "not within" and reported MAE as NaN. It is now scored only on its own rows, and the row count is stated (`rows_note` column). | No (reporting of a context baseline only) | The selection, V2, the candidates and every N1–N7 result are unchanged. RIDGE-ALL at Lead 2 now reads 39.3 % on 28 rows, equal to MODEL_REPORT's S-E132 value. |
| 2 | Before the seal was written | **Leakage-control wording.** The pre-registration says the shuffle control's within share "collapses to the shuffled-series level". On the shuffled series, LL-K (0.35) beats PERSIST (0.275), because filtering an i.i.d. series towards its mean helps. V2 still selects PERSIST at every issue. | No (interpretation of a control; no rule changed) | Reported as observed in MODEL_REPORT_V2 §6 |
