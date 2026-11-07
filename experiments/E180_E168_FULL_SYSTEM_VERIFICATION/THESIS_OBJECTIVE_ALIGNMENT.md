# Thesis objective alignment (E168)

| Objective | Claims | Implemented | Evidence | Incomplete | Cannot be claimed |
|---|---|---|---|---|---|
| Food-insecurity forecasting | forecast food-insecurity risk for CALABARZON | E168: P(HFIAS mod+sev >= 50 %) per province, Leads 1-3 | lock intact; 56 / 55 / 54 of 72; beats 6 baselines | prospective validation (2027-Q1 sealed; no outcome yet) | validated quarterly provincial food insecurity |
| Regional and provincial forecasting | provincial (and regional) forecasts | provincial model; region = mean of 5 provinces; LGU = Algorithm 5 ranking | 142/142 map join; per-province forecasts | no provincial truth after 2021 | municipal forecasts; quarterly ground truth |
| NLP integration | Filipino-English news drives risk | 36 news inputs; 23.6 % attribution; H1 rank 9 | news_panel to 2026-Q4 | human validation missing (n_annotated 0) | validated NLP classification |
| Five risk drivers | market, climate, fish, employment, remittance | all mapped; market and climate provincial; employment and remittance national; fish = production | FEATURE_DRIVER_VERIFICATION.csv | share method incorrect (F02); fish label (F10) | provincial employment / remittance effects; fish-kill effects |
| ML reliability | reliable forecasts to the maximum reliable lead | Algorithm 3: Lead 3; strict C1-C6: Lead 1 | recalculation matches leads.py | Lead-2 C1; F1 0.742 < 0.75; 72 reused rows | Lead-2 strict reliability; independent validation |
| Geospatial visualization | map of provincial / LGU risk | React map, 81 provinces, 142 LGUs | join verified; colours by riskLevel | back-forecasts labelled "actual" (F11) | observed municipal food insecurity |
| Explainability | SHAP drivers per forecast | exact LightGBM pred_contrib, additivity asserted | shap_results.json; history | displayed shares mis-normalised; otherPct missing | causal driver effects |
| Deployment / decision support | live system for DA Region IV-A | Render + Vercel | render.yaml | production serves the older model (F01); alerts not E168-based | operational E168 decision support today |

A dashboard feature existing is not counted as an objective passing: rows are judged on the evidence column.
