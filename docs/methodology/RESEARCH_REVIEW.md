# Research review: measuring and forecasting food insecurity at small geographic scales

The DOIs below were checked on Crossref on 2026-11-02/03 (`crossref_verification_methodology.json`,
`docs/fi5/crossref_verification.json`, `docs/fi6/crossref_verification_fi6.json`). Institutional sources are cited by
their official pages. APA 7th edition.

## 1. Experience-based measurement

* FIES measures food insecurity as an experience on a calibrated scale (Rasch model). Moderate and severe
  thresholds are set on that scale, and prevalence estimates carry sampling and measurement error (Cafiero et al.,
  2018).
* SWS's single question about hunger with nothing to eat, asked over a 3-month reference period, corresponds to the
  severe end of that construct. It is not FIES itself, so the two scales are not interchangeable.
* Different household food-security indicators capture different dimensions and are not substitutes (Maxwell et
  al., 2014).
* **For aiPHeed:** SWS hunger is a valid outcome for the area it samples. FIES rounds are benchmarks, not quarterly
  labels.

## 2. Geography: aggregation and ecological inference

* Relationships observed for aggregates do not transfer to sub-units (Robinson, 1950).
* An outcome measured for Balance Luzon cannot validate CALABARZON or provincial predictions. Two thirds of Balance
  Luzon lies outside CALABARZON.

## 3. Small-area estimation (SAE)

* **What PSA does for poverty.** PSA's city and municipal poverty estimates follow the census-based small-area
  approach.
  * A household model of welfare is fitted on survey data and applied to census auxiliaries (Elbers et al., 2003).
  * Empirical best/Bayes refinements are used (Molina & Rao, 2010).
  * Area-level Fay–Herriot models are the alternative when only area aggregates exist (Fay & Herriot, 1979).
* **What food insecurity would need:**
  1. household outcome data with geographic identifiers (FNRI FIES or PSA APIS microdata);
  2. auxiliaries shared with the census (CPH 2020);
  3. a model validated against direct estimates where the sample supports them;
  4. reported mean squared errors or intervals.
* **What is held:** none of the outcome microdata. Poverty SAE cannot be reused as food-insecurity SAE, because the
  outcome differs.

## 4. Indicator-based early warning (risk vs measurement)

* Operational systems keep outcome indicators separate from contributing drivers, and judge forecasts against later
  outcomes.
  * FEWS NET uses scenario-based projections (Funk et al., 2019).
  * FEWS NET projections are validated against later outcomes (Backer & Billing, 2021).
  * IPC uses a convergence-of-evidence protocol (IPC Global Partners, 2021).
  * WFP CARI keeps food consumption outcomes separate from coping capacity (WFP, 2021).
* Data-driven crisis prediction improves on expert classifications when it is scored on observed outcomes (Lentz et
  al., 2019; Westerveld et al., 2021; Andrée et al., 2020).
* News helps when it is read as signals of specific drivers (Balashankar et al., 2023).
* Where survey data are missing, nowcasts are model estimates, not ground truth (Martini et al., 2022).
* **For aiPHeed:** prices, poverty, employment, remittances, climate and news are drivers or risk signals. They are
  never outcomes.

## 5. Forecast evaluation

* Rolling-origin (walk-forward) evaluation (Tashman, 2000).
* Probabilistic forecasts scored with the Brier score (Brier, 1950).
* Persistence as the reference forecast to beat (Andrée et al., 2020; Westerveld et al., 2021).
* Short-horizon forecastability of food-insecurity indicators is limited by their own history (Foini et al., 2023).

## References

Andrée, B. P. J., Chamorro, A., Kraay, A., Spencer, P., & Wang, D. (2020). *Predicting food crises* (Policy Research Working Paper No. 9412). World Bank. https://doi.org/10.1596/1813-9450-9412

Backer, D., & Billing, T. (2021). Validating Famine Early Warning Systems Network projections of food security in Africa, 2009–2020. *Global Food Security, 29*, 100510. https://doi.org/10.1016/j.gfs.2021.100510

Balashankar, A., Subramanian, L., & Fraiberger, S. P. (2023). Predicting food crises using news streams. *Science Advances, 9*(9), eabm3449. https://doi.org/10.1126/sciadv.abm3449

Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review, 78*(1), 1–3. https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2

Cafiero, C., Viviani, S., & Nord, M. (2018). Food security measurement in a global context: The food insecurity experience scale. *Measurement, 116*, 146–152. https://doi.org/10.1016/j.measurement.2017.10.065

Elbers, C., Lanjouw, J. O., & Lanjouw, P. (2003). Micro-level estimation of poverty and inequality. *Econometrica, 71*(1), 355–364. https://doi.org/10.1111/1468-0262.00399

Fay, R. E., & Herriot, R. A. (1979). Estimates of income for small places: An application of James-Stein procedures to census data. *Journal of the American Statistical Association, 74*(366a), 269–277. https://doi.org/10.1080/01621459.1979.10482505

Foini, P., Tizzoni, M., Martini, G., Paolotti, D., & Omodei, E. (2023). On the forecastability of food insecurity. *Scientific Reports, 13*, 2793. https://doi.org/10.1038/s41598-023-29700-y

Funk, C., Shukla, S., Thiaw, W. M., Rowland, J., Hoell, A., McNally, A., Husak, G., Novella, N., Budde, M., Peters-Lidard, C., Adoum, A., Galu, G., Korecha, D., Magadzire, T., Rodriguez, M., Robjhon, M., Bekele, E., Arsenault, K., Peterson, P., … Verdin, J. (2019). Recognizing the Famine Early Warning Systems Network: Over 30 years of drought early warning science advances and partnerships promoting global food security. *Bulletin of the American Meteorological Society, 100*(6), 1011–1027. https://doi.org/10.1175/BAMS-D-17-0233.1

IPC Global Partners. (2021). *Integrated Food Security Phase Classification technical manual version 3.1*. https://www.ipcinfo.org/

Lentz, E. C., Michelson, H., Baylis, K., & Zhou, Y. (2019). A data-driven approach improves food insecurity crisis prediction. *World Development, 122*, 399–409. https://doi.org/10.1016/j.worlddev.2019.06.008

Martini, G., Bracci, A., Riches, L., Jaiswal, S., Corea, M., Rivers, J., Husain, A., & Omodei, E. (2022). Machine learning can guide food security efforts when primary data are not available. *Nature Food, 3*, 716–728. https://doi.org/10.1038/s43016-022-00587-8

Maxwell, D., Vaitla, B., & Coates, J. (2014). How do indicators of household food insecurity measure up? An empirical comparison from Ethiopia. *Food Policy, 47*, 107–116. https://doi.org/10.1016/j.foodpol.2014.04.003

Molina, I., & Rao, J. N. K. (2010). Small area estimation of poverty indicators. *Canadian Journal of Statistics, 38*(3), 369–385. https://doi.org/10.1002/cjs.10051

Robinson, W. S. (1950). Ecological correlations and the behavior of individuals. *American Sociological Review, 15*(3), 351–357. https://doi.org/10.2307/2087176

Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International Journal of Forecasting, 16*(4), 437–450. https://doi.org/10.1016/S0169-2070(00)00065-0

Westerveld, J. J. L., van den Homberg, M. J. C., Nobre, G. G., van den Berg, D. L. J., Teklesadik, A. D., & Stuit, S. M. (2021). Forecasting transitions in the state of food security with machine learning using transferable features. *Science of the Total Environment, 786*, 147366. https://doi.org/10.1016/j.scitotenv.2021.147366

World Food Programme. (2021). *Consolidated approach for reporting indicators of food security (CARI) technical guidance* (2nd ed.). https://www.wfp.org/

## Institutional data sources

* Philippine Statistics Authority. (2026). *Official poverty statistics: Food threshold, subsistence incidence, poverty incidence and magnitude of poor population, by region and province, 2018, 2021 and 2023* [Data tables DB/1F/FY]. PSA OpenSTAT. https://openstat.psa.gov.ph/
* Social Weather Stations. (2025, January 14). *Fourth Quarter 2024 Social Weather Survey: Hunger in families* [Media release]. https://sws.org.ph/
* Food and Nutrition Research Institute, DOST. (n.d.). *Expanded National Nutrition Survey / National Nutrition Survey results*. https://enutrition.fnri.dost.gov.ph/
