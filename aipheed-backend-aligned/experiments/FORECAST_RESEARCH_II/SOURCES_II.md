# FORECAST_RESEARCH_II: sources added in this phase

I checked each source on 2026-10-27, by web search. **Record** means I confirmed the bibliographic record and a summary of the finding, but did not read the full text. Each source supports only the principle listed beside it.

The FORECAST_RESEARCH sources S1-S18 (`../FORECAST_RESEARCH/SOURCES.md`) still apply. In particular:
- FAO FIES is a measure of the access dimension (S1);
- dichotomising loses information (S3);
- proper scoring rules (S6);
- calibration rules (S7, S8);
- small-sample limits (S9);
- naive inflation forecasts are hard to beat (S10);
- importance is model-specific (S15, S16).

| # | Source | Checked | Principle used | How it applies |
|---|---|---|---|---|
| S19 | Faust J, Wright JH. Forecasting inflation. *Handbook of Economic Forecasting* vol. 2A (2013), ch. 1, pp. 2-56. doi:10.1016/B978-0-444-53683-9.00001-3 | Record (ScienceDirect, RePEc) | A simple "glide path" from the current inflation reading to a long-run anchor is competitive with survey forecasts and beats most model-based forecasts. Simple benchmarks are hard to beat. Models are local approximations. | Motivated arms J2 (drift anchored at the 3% midpoint of BSP's 2-4% target) and J3 (half-way glide path). J2 cut the food-inflation RMSE at Leads 3-4 by about a third. That gain did not carry over to the binary label (§5.2 of the report). |
| S20 | Timmermann A. Forecast combinations. *Handbook of Economic Forecasting* vol. 1 (2006), ch. 4, pp. 135-196. Stock JH, Watson MW (2004), "forecast combination puzzle" | Record | Equal-weight combinations often beat estimated weights, because estimating the weights adds error. | CMB averages Z0 and J3T with fixed weights; no weight is fitted. |
| S21 | Frénay B, Verleysen M. Classification in the presence of label noise: a survey. *IEEE TNNLS* 2014;25(5):845-869. doi:10.1109/TNNLS.2013.2292894 | Record | Mislabelled training and test instances degrade learning and bound the accuracy you can measure. | The SWS sampling error makes the hunger side of T43c uncertain whenever a reading is near 11.3 (§2.3). |
| S22 | DOST-FNRI, 2021 ENNS provincial dissemination decks (Batangas, Cavite, Lucena), 2023 NNS CALABARZON deck, 2025 Updating Survey | Repository record (E87 `fnri_fies_observations.csv`, with page numbers; PDFs held locally) | FIES moderate-or-severe food insecurity, 12-month recall, households (2025: population). | The only direct food-insecurity observations available for the region. They are annual and mostly regional, so they can only be compared descriptively (§2.4). |
| S23 | PSA Family Income and Expenditure Survey 2023, public-use file (`Downloads/PHL-PSA-FIES-2023-V1-PUF`, SHA-256 44f660c8) | Read locally; weighted aggregates only | Food share of family spending; national per-capita income deciles. | A structural vulnerability profile for the five provinces. It contains no food-insecurity items. |
| S24 | OCTA Research *Tugon ng Masa* Balance Luzon hunger, as reported by GMA, Philstar and Canadian Inquirer (E73 `provenance.csv`) | Repository record | An independent survey of self-rated involuntary hunger. | It agrees with SWS on the 11.3 side in 3 of 7 matched rounds, and is not published earlier in any useful way (§2.4). |

Not used: anything that would show a value for a quarter after 2026-Q3. No PSA, BSP or SWS "latest" query was run, and sws.org.ph was not opened.
