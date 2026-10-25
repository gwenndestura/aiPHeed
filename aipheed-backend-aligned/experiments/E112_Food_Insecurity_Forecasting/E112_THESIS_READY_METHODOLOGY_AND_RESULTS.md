# E112 Thesis-ready text (Chapter III methodology and Chapter IV results)

*Draft wording for the researchers to adapt. The numbers are from `out/results.json` and `out/objective4_baselines.json`.*

## Chapter III: Methodology (summary)

**Outcome.**
- Food insecurity was measured by the Social Weather Stations (SWS) Total Hunger rate for Balance Luzon, the survey area that contains CALABARZON.
- It is the only directly observed food-insecurity series available quarterly for 2021–2026.
- Non-commissioned rounds from 2021-Q2 to 2026-Q3 were used (20 quarters).
- The other three SWS areas were used to test whether results generalize.
- No provincial or municipal food-insecurity outcome exists for the study period. Forecasts are therefore regional, and municipal outputs are presented as vulnerability rankings rather than forecasts.

**Forecast timing.**
- A forecast for quarter t+k was issued on the first day of quarter t+1, using only information published before that date.
- Because SWS publishes each quarter's result after the quarter ends, the newest available reading is usually one quarter old. A one-quarter-ahead forecast is therefore two quarters beyond the newest observation. Every forecast reports this true horizon.

**Predictors.**
- The twelve FIRI indicator families: food-price projection, inflation, rice prices, vulnerability, El Niño, typhoons, crop and fisheries production, unemployment, remittances, news sentiment, and the regional hunger outlook. Provincial values were averaged to the region.
- **News indicators.** Headlines from the project news corpus were de-duplicated and assigned to six event categories (price, shortage, disaster, agricultural supply, jobs and income, assistance) with a fixed English–Filipino keyword list. For each quarter the share of headlines in each category was computed, and its change from the same quarter a year earlier. A quarter's news was used only when every counted headline had been published before the issue date. GDELT documents located in CALABARZON served as an independent second source.

**Models.**
- **Proposed model:** a LightGBM regression predicting the change from the latest published reading, from the twelve families with and without the news indicators. The configuration was fixed (depth-one trees, 25 or 75 trees chosen on past data) and trained in an expanding walk-forward window.
- **Baselines** (Objective 4): naive persistence (latest reading), a PSA-only model, an NLP-only (news) model and a linear regression. Simple smoothing rules were also included.

**Evaluation.**
- Forecasts were scored by mean absolute error against the published SWS value.
- Methods were compared with the Diebold–Mariano test (Newey–West variance, small-sample correction) and corrected for multiple comparisons with Holm's method.
- A method counted as **reliable** at a lead time only if it met all of the following, specified before scoring:
  - significantly beat persistence over at least eight quarters;
  - kept Balance Luzon error within the ±4-point survey margin;
  - improved in every third of the period, when hunger rose and when it fell, and after the 2025 survey change;
  - survived leaving out any single quarter;
  - did not worsen in the last four quarters;
  - did not underpredict hunger surges more than persistence;
  - achieved at least 70% coverage of its 80% interval;
  - was confirmed on quarters not yet observed.

## Chapter IV: Results (summary)

**News.**
- The news indicators were available for every quarter.
- Disaster coverage tracked the typhoon record closely (ρ = 0.81) and, in the project corpus, coincided with year-over-year changes in hunger (ρ = 0.76).
- Price headlines did not track measured inflation.
- Agricultural-supply news was associated with the following quarter's change in hunger in the project corpus (ρ = 0.65, Holm-adjusted p = .074), but not in the independent GDELT source.
- Adding the news indicators did not improve forecasts:
  - the LightGBM with news performed the same as the LightGBM without them (one quarter ahead, MAE 4.05 vs 4.04);
  - a news-only model was slightly, but not significantly, more accurate than persistence (3.52 vs 3.72, p = .36).

**Proposed model and baselines.**
- One quarter ahead, persistence had a mean absolute error of 3.72 points. The proposed LightGBM had 4.04, the PSA-only model 3.73 and the linear regression 4.49.
- The proposed model did not outperform persistence at any lead time.
- No indicator family or news category significantly improved the forecasts.

**Generalization.**
- The models improved on persistence only during the 2024 increase in hunger.
- They did worse after the 2025 change in the survey's respondent base and when hunger fell.
- Every method missed at least one of the two sharp increases one quarter ahead.

**Horizon.**
- No method met the reliability criteria at any lead time. Beyond one quarter ahead, fewer than eight quarters could be evaluated.
- A reliable forecasting horizon was therefore not established with 2021–2026 data.

**Adopted method.**
- The decision rule set before scoring selects the latest published SWS reading as the operational outlook. It is reported with its true horizon and its typical error, about 3.7 points.
- The LightGBM and news-only forecasts were issued as of 1 October 2026 and sealed on 25 October 2026 (before any of their target quarters was published) for prospective evaluation as new SWS results are published.

**Limitations.**
- Twenty regional quarters, survey noise of about ±4 points, a change in survey design, and the absence of provincial or municipal outcomes limit what can be demonstrated.
- Validation of municipal rankings requires local food-security data such as the 2024 CBMS food-security items.
