# SHAP / explainability audit (E168)

| Check | Status | Evidence |
|---|---|---|
| Attributions from the served model | VERIFIED | `app/e168/history.py` → `app/e166/history.contributions` uses LightGBM `pred_contrib` of the configuration chosen at that issue |
| Additivity (attributions reproduce the forecast) | VERIFIED | `history.one()` asserts max |base + Σ contributions − mu| < 1e-6 for every quarter (run 2026-11-06 passed for all 17) |
| Correct observation and lead | VERIFIED | contributions computed for each province's Lead-1 test row of that issue quarter |
| Scaling | VERIFIED | contributions multiplied by lambda, consistent with the shrunk score |
| Grouping into five drivers | VERIFIED (mapping) | `e166_serving._contrib`: market, climate, employment, remittance via `C.gmap`; `c_fish_yoy` → fish_kill; all else → other |
| Required share formula (|SHAP| of group ÷ |SHAP| of all features; otherPct remainder; sum 100) | **INCORRECT (F02)** | `dashboard.py` line 1158 normalises |signed group sum| over the five groups only; `ExplainabilityResponse` (`schemas/public.py` 436) has no otherPct |
| Measured gap (2027-Q1) | | Quezon API climate 76 / employment 14 / market 9 / remittance 1 vs required 65.0 / 8.3 / 9.4 / 0.6 + other 16.7; Batangas 46 / 27 / 26 / 1 vs 30.5 / 32.0 / 7.6 / 0.8 + other 29.1; Cavite other 37.5 |
| Signed vs absolute | PARTIALLY VERIFIED | Within a group, positive and negative inputs cancel in the signed sum; the required |SHAP| method avoids this |
| Unavailable vs zero | VERIFIED (behaviour) / qualify | fish_kill is an input with exactly zero attribution, shown as 0 %, which is correct but needs labelling |
| Model-wide SHAP (RQ1/H1) | VERIFIED | `data/e168/out/objectives/shap_results.json`: climate 46.6 %, market 35.4 %, employment 15.5 %, remittance 2.6 %, fish 0 % of the five groups; other = 47 % of total; H1: FSSI rank 9, food-CPI deviation rank 10 |
| Causal language | Qualify | attributions describe the model's adjustment to the survey anchor, not causes; the panel note says so |
| Hard-coded explanations | none found | values come from history JSON |
