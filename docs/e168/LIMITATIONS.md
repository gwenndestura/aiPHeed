# E168: known limitations and design facts (for the thesis and the dashboard)

| # | Item | Effect | Where stated |
|---|---|---|---|
| 1 | Validation uses 72 DOST-FNRI province results per lead (ENNS 2018, 2019, 2021), about 45.5 effective | Lead-2 strict C1 is one row short; F1 0.742 < 0.75 | Landing "How accurate it is"; About |
| 2 | No DOST-FNRI provincial HFIAS after 2021 | 2023-2026 dashboard quarters are back-forecasts that cannot be scored | Landing, About, history chart (isForecast) |
| 3 | Employment and OFW remittance inputs are national series | Same for every province | Driver labels "(national)"; Landing disclaimer |
| 4 | Fish production has zero SHAP contribution | Shown as 0 %, labelled "Fish Production" | Driver panel |
| 5 | Inputs are today's data releases | Later revisions of CPI, production and labour data were not available at historical issue dates | Landing disclaimer |
| 6 | Survey reference quarter is set to Q3 of the survey year | Lead arithmetic assumes mid-year fieldwork | This file |
| 7 | LGU ranking uses PSA 2021 poverty and the 2020 census for every quarter | Rankings do not track later poverty changes | About, Landing |
| 8 | News tone is 0.0 when a province has no articles | "No news" looks neutral to the model | Landing disclaimer |
| 9 | No serialized model file | E168 is reproduced exactly by deterministic refit (seed 151); served values are precomputed history files | This file; docs/e168/PROTOCOL.md |
| 10 | `app/e147/features.base_rows` calls `outcomes("insecure")` | The values are moderate + severe HFIAS (verified identical to `mod_sev_pct`); only the argument name is misleading | This file |
| 11 | NLP classifier labels are zero-shot and not yet scored against the 300 human-annotated headlines | Classification quality unverified until the annotations are added | Landing disclaimer |
