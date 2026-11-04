# AIPHEED: Review of Related Literature and Verified Philippine Evidence

**Study:** AIPHEED: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using NLP and Machine Learning
**Prepared:** 4 November 2026

**How to read this review.**
* Every claim carries a source, listed in section 10.
* Claims taken from the study brief are marked **Verified**, **Partly verified** or **Not verified** in section 8.
* AIPHEED's own experimental evidence is cited by experiment ID (for example FI9-N and E143) so that the literature can be read against what the system has already shown.

---

## 1. The problem in the literature

Food-security information in low- and middle-income settings arrives late, infrequently, and at coarse geographic levels. The forecasting literature treats this as two linked problems.

**Publication lag.**
* Official statistics describe a reference period that has already ended and are released weeks or months later.
* The macroeconomic nowcasting literature calls the resulting unbalanced end of the data set the "jagged" or "ragged" edge (Giannone, Reichlin and Small, 2008; Bańbura, Giannone and Reichlin, 2010).

**Sparse outcome labels.**
* Direct measurements of household food insecurity come from periodic surveys.
* A forecasting model can only learn from, and be validated against, the periods and places in which the outcome was actually measured.

Food-security studies respond in two ways:
1. They borrow **high-frequency proxies**: news, satellite imagery, prices, and phone surveys.
2. They **pool many labelled units**: districts, livelihood zones, and countries.

The pooling gives a model enough examples to learn from even when each unit is measured rarely.

## 2. Studies combining official statistics with news, text, remote sensing, or other high-frequency data

| Study | Outcome forecast | Unit and label frequency | Data combined | Horizon | Main finding |
|---|---|---|---|---|---|
| Balashankar, Subramanian and Fraiberger (2023), *Science Advances* | IPC food-crisis phase (FEWS NET) | District; several IPC rounds per year | NLP indicators from about 11.2 million news articles, plus traditional risk factors | Up to 12 months | News indicators improved district-level predictions over traditional models up to 12 months ahead. The World Bank reports that adding news to 3-month-ahead forecasts would have reduced prediction errors by more than 40%. Hybrid news-plus-traditional models performed best. |
| Ahn, Yan, Lin and Wang (2023), *HungerGist*, arXiv:2311.10953 | Food-insecurity risk | Nine African countries, four years | More than 53,000 news articles; sentence-level "gists" | — | A model trained only on news outperformed a baseline that used traditional risk factors and human-curated keywords. It also returned interpretable text evidence. |
| Martini et al. (2022), *Nature Food* | Prevalence of insufficient food consumption and crisis-level food-based coping (WFP) | Subnational areas where WFP surveys exist | Conflict, weather extremes, economic shocks | Nowcast | Trained where primary survey data exist and used to estimate where they do not. The preprint reports up to 78% of variation explained. It underpins HungerMap LIVE. |
| Foini, Tizzoni, Martini, Paolotti and Omodei (2023), *Scientific Reports* | Insufficient food consumption | Six countries; near-daily phone-survey observations | Food-consumption history, conflict, weather, economic shocks | Up to 30 days | Gradient-boosted trees beat the naive last-value forecast. Performance depended strongly on the number of historical observations. |
| Westerveld et al. (2021), *Science of the Total Environment* | Monthly transitions in IPC phase | Ethiopian livelihood zones | 130 open variables in 19 categories (climate, land, markets, conflict, infrastructure, demographics) | 1 to 12 months | XGBoost F1 (macro) of 0.51 at 3 months and 0.61 at 7 months. Food-security history and surface soil moisture were the most influential predictors. |
| IFPRI, *Predicting Food Crisis* | IPC phase | More than 13,000 subnational observations, 38 countries | Prices, weather, conflict, high-frequency data | Up to 12 months | Reported to identify 94.1% of IPC Phase 3+ cases; not peer-reviewed at the time of reporting. |
| Penson et al. (2024), World Bank WPS 10768 (Yemen) | Food-security deterioration | Yemen | A few indicators: inflation, conflict, agricultural productivity shocks; data-driven thresholds | Most accurate at 5 months | Simple, transparent indicator thresholds generated reliable warnings before sharp deterioration. |
| Lentz, Michelson, Baylis and Zhou (2019), *World Development* | Village-cluster food-security status | Malawi; trained on 2010–2011, tested on 2013 | Market prices, satellite rainfall, geographic and demographic data | About two years | Correctly identified 83–99% of the most food-insecure clusters, against 0–10% for the prevailing approach. |

**What these studies share:**
1. Each forecasts an outcome that is **measured regularly somewhere**: IPC phases several times a year, or WFP survey prevalence near-daily.
2. Each **pools thousands of labelled place-periods** across districts or countries.
3. **The outcome's own history is consistently among the strongest predictors.** News and secondary data add to it rather than replace it.
4. Validation is **always against measured outcomes** held out in time or space.

None of them forecasts a food-insecurity outcome that has never been measured. They forecast or nowcast measured outcomes for periods and places where the measurement has not yet arrived.

## 3. Philippine and CALABARZON work on delayed, sparse, or infrequent food-security data

| Work or system | What it addresses | Relevance to AIPHEED |
|---|---|---|
| **PhilFSIS** (PSA/BAS with FAO, TCP/PHI/3401; implemented 2012) | A web-based "one-stop shop" for relevant, timely, comprehensive, user-friendly, and accessible food-security data. It covers crops, livestock and poultry, and fisheries, and publishes food-security indicators on PSA OpenSTAT. | Establishes the policy need for timely, integrated food-security information. It organizes and disseminates data but does not forecast. |
| **FAO Data in Emergencies (DIEM) monitoring**, Philippines | Periodic household surveys, roughly every four months, representative at regional level. Round 1: 13 August–1 October 2021, 2,087 households, seven regions including CALABARZON. Round 2: 26 January–2 March 2022, 1,904 households. | Shows that periodic household monitoring exists in CALABARZON, but with gaps between rounds and restricted microdata. |
| **2023 National Nutrition Survey** (DOST-FNRI; 36,703 households; 81 provinces, 33 HUCs and 3 other areas; fieldwork 2023–2024) | Moderate-to-severe household food insecurity measured with **FIES**: 31.4% nationally. **CALABARZON 19.1% (CI 17.0–21.1)**, the lowest region, published through PSA's SDG 2.1.2 indicator. | A credible regional outcome and validation benchmark. It is infrequent and uses FIES, not the HFIAS of the 2013–2021 FNRI rounds. |
| **FNRI NNS 2013, 2015 and ENNS 2018/2019/2021** | Household food insecurity measured with **HFIAS**, with provincial estimates in the published rounds (2013, 2015, 2018, 2019). | The only provincial food-insecurity measurements available for CALABARZON's five provinces. They anchor AIPHEED's provincial risk model (E141–E143). |
| **Transformer-based quarterly crop-production forecasting** | A global time-series transformer forecasts the quarterly production volume of 325 crops in 83 provinces from the PSA Crops Production Survey. It significantly outperforms local statistical models. | Demonstrates quarterly ML forecasting at provincial scale in the Philippines for the **availability** dimension. |
| **PhilRice/IRRI PRISM** | Satellite (SAR) rice monitoring since 2014: seasonal rice area and yield, plus crop damage from typhoons, floods, and drought, validated with field surveys. Operated by PhilRice since 2018. | A national precedent for geospatial, high-frequency availability monitoring that is not delayed by survey cycles. |
| **World Bank Real-Time Food Prices** | Weekly prices for 108 Philippine markets (2007–2025), built from WFP and FAO price data with machine-learning imputation of missing prices. | A model for handling missing price observations, for the **access** dimension. |
| **Rice price studies** (Duyapat, 2025; Antonio et al., 2025) | Random Forest forecasting of wholesale rice prices. Panel VAR evidence that world rice prices, fuel prices and ENSO drive regional rice inflation. | Support price signals as leading indicators of food-access pressure. |
| **BSP news-based nowcasting** (BSP working paper, 2026; BIS IFC papers) | Text analytics and machine learning to nowcast regional and national inflation from news. Online job postings to nowcast unemployment. A BSP news-sentiment index. | The closest Philippine evidence that news text carries timely economic signal at regional level. |
| **ADB, Mapping Poverty through Data Integration and AI** (2020; guidebook 2021, with PSA) | Daytime satellite imagery plus computer vision, integrated with surveys and censuses, to produce more granular poverty estimates. Used for the Bayan Bayanihan COVID-19 food programme. | A Philippine precedent for geospatial ML that fills gaps in official poverty statistics (the **vulnerability** component). |
| **510 / Philippine Red Cross typhoon impact model** | Machine learning on ECMWF ensemble typhoon tracks with about 40 hazard, exposure and vulnerability predictors. Predicts the percentage of completely damaged houses per municipality; used since 2019. | A municipal-level geospatial ML model operating ahead of impact, for the **stability** dimension. |
| **DA AMIA Climate Risk Vulnerability Assessment** | CRVA maps for Cavite, Laguna, Batangas, and Rizal (2024 terminal report) and a Quezon terminal report. Hazard, sensitivity, adaptive capacity, and climate suitability layers. | Geospatial foundation for DA Region IV-A hazard exposure. |
| **NNC EWS-FNS** and **WFP–DSWD EWS-HFI** | Early-warning systems for food and nutrition security. EWS-HFI gathers and monitors data quarterly with LGU take-over. | Existing Philippine early-warning practice; quarterly monitoring rather than ML forecasting. |
| **PIDS DP 2022-21** (Galang) | Assesses the four FAO dimensions and finds the food-security goal not yet met. Recommends data-driven action plans and a modern monitoring and evaluation system backed by a reliable information system. | Policy support for evidence-informed monitoring; see the note on the brief's PIDS claim in section 8. |

## 4. Handling publication lag, missing values, quarterly updating, and reference period versus release date

**Ragged edge and release dates.**
* The nowcasting literature models each series with its own publication lag. A forecast uses only the values released before the issue date (Giannone, Reichlin and Small, 2008; Bańbura, Giannone and Reichlin, 2010).
* Mixed-frequency methods such as MIDAS (Marcellino and Schumacher) combine monthly indicators with quarterly targets without waiting for the slowest series.

**Missing values.**
* Gradient-boosted trees (XGBoost, LightGBM) accept missing inputs directly. This is why Foini et al. (2023) and Westerveld et al. (2021) could operate when some drivers arrive late.
* The World Bank Real-Time Food Prices dataset imputes missing market prices with machine learning, with accuracy reported as similar to direct measurement.

**Practice for AIPHEED, in accordance with this literature:**
1. Every indicator carries two dates: its **reference period** and its **release date**. A forecast issued on date *d* uses only values released before *d*. AIPHEED's quarterly clock (`app/quarterly/target.py`) issues at the start of each quarter for the next quarter.
2. Missing or late indicators enter as missing values with availability flags, not as interpolated values.
3. Evaluation replays each historical issue date with the values available at that date (pseudo-real-time). Random splits are not used.
4. News is collected continuously and dated by publication time. It is the only input with no release lag. This is the property the news literature exploits.

## 5. Food-insecurity outcomes used in prior studies

| Outcome | Used by | Frequency and geography in the Philippines |
|---|---|---|
| IPC acute phase | Balashankar et al.; Westerveld et al.; IFPRI | No IPC acute series for CALABARZON |
| Food Consumption Score / insufficient food consumption; reduced Coping Strategies Index | Martini et al.; Foini et al. (WFP) | WFP/FAO DIEM rounds, regional and periodic |
| FIES (SDG 2.1.2) | FAO; PSA; 2023 NNS | 2023 NNS regional (CALABARZON 19.1%); PSA SDG releases |
| HFIAS (Coates, Swindale and Bilinsky, 2007) | FNRI NNS 2013, 2015; ENNS 2018/2019/2021 | Provincial in published rounds; every 2–4 years |
| Self-rated involuntary hunger | SWS | Quarterly; four areas (NCR, Balance Luzon, Visayas, Mindanao) |
| Prevalence of undernourishment (SDG 2.1.1) | FAO | National, annual |
| Food prices and crop production | Price and production forecasting studies | PSA monthly CPI and prices; quarterly production by province |

**The trade-off for CALABARZON:**
* The only quarterly food-insecurity-type outcome is SWS hunger, which is regional (Balance Luzon contains CALABARZON).
* The only provincial outcome is HFIAS, which is measured every few years.
* FIES 2023 is regional and is used only as an agreement benchmark, never pooled with HFIAS.

## 6. Evidence on whether news-derived indicators improve forecasts at 3, 6, 9, and 12 months

**Food-crisis forecasting:**
* Balashankar et al. (2023) report gains up to 12 months ahead and more than 40% lower error at 3 months when news is added to existing forecasts. This is the strongest horizon evidence.
* HungerGist shows news-only models outperforming traditional-factor baselines.

**Food and commodity prices:**
* News-based sentiment improved Indian food (vegetable) inflation forecasts (RBI Occasional Paper, 2021).
* News-mined events reduced food price forecast error by 22% across four Indian crops (NYU, KDD 2016).
* Gains depend on the horizon and the text representation: embedding-based text helps at monthly horizons, while sentiment scores are too compressed for long horizons (Kent doctoral thesis, 2026).

**Philippines:** BSP is nowcasting regional and national inflation from news text (2026).

**Conditions under which news helps.** Across these studies, news helps most:
* where news coverage is dense;
* where many labelled units exist;
* when combined with traditional indicators rather than used alone.

**AIPHEED's own evidence (FI9-N, locked protocol)** uses SWS Balance Luzon hunger, 62 target quarters, 2010–2026.

| Issue timing | Government indicators only | Government + news | Persistence | Finding |
|---|---|---|---|---|
| End of quarter *t*, for quarter *t*+1 (news of quarter *t* complete) | Brier 0.129, AUC 0.70 | **Brier 0.119, AUC 0.77** | 0.116 | News significantly improved probability quality (Bonferroni-robust) but did not beat the latest reading |
| Start of the viewing quarter, for the next quarter (AIPHEED's dashboard horizon) | Brier 0.166, AUC 0.44 | Brier 0.161, AUC 0.47 | 0.198 | News reduced error slightly; no configuration discriminated HIGH from LOW |

* Adding news to the E36 LightGBM did not raise one-quarter-ahead accuracy: 0.815 with news, against 0.846 for government indicators only.
* For the provincial HFIAS target, news could not be tested as an input. FSSI covers only the five CALABARZON provinces, while the HFIAS model learns from 78 provinces (E143).

**The literature therefore supports news as a high-frequency complement**, and AIPHEED reproduces that effect for the next quarter when the quarter's news is complete. The 3-, 6-, 9- and 12-month gains reported abroad were obtained with thousands of IPC-labelled district-periods. AIPHEED has 62 regional quarters and 203 provincial survey rows.

## 7. Geospatial machine learning for food security, crop yield, disaster impact and hunger risk

* **Poverty and vulnerability:**
  * Jean et al. (2016, *Science*) used nighttime lights as a proxy label to train a CNN on daytime imagery. Image features explain up to 75% of variation in consumption and assets.
  * ADB (2020, 2021) applied the approach in the Philippines with PSA.
* **Crop yield:** You et al. (2017, AAAI) combined CNN/LSTM representations of remote-sensing data with a Gaussian process for spatio-temporal structure. RMSE was 30% lower than traditional remote-sensing methods. PRISM provides the Philippine SAR-based equivalent for rice.
* **Disaster impact:** the 510 typhoon impact model predicts municipal house damage before landfall from forecast tracks and vulnerability layers.
* **Food security:**
  * Lentz et al. (2019) combined satellite rainfall, prices, and geography at village-cluster level.
  * Martini et al. (2022) and Westerveld et al. (2021) model subnational units with spatial predictors.
  * A common design is to pool spatial units to compensate for sparse labels, and to use hazard and exposure layers as predictors.

## 8. Verification of the Philippine evidence in the study brief

| Claim in the brief | Status | Accurate wording | Source |
|---|---|---|---|
| PhilFSIS is designed as a one-stop source of relevant, timely, comprehensive, and accessible food-security data | **Verified** | "Envisioned as a one-stop shop containing relevant, timely, comprehensive, user-friendly, and accessible data affecting food security" (PSA OpenSTAT); established under FAO TCP/PHI/3401 at BAS | PSA OpenSTAT PhilFSIS page |
| FAO DIEM collected household data in CALABARZON roughly every four months | **Verified, with limits** | FAO describes collection "roughly every four months, depending on seasonality". Two Philippine rounds were found (2021, 2022), representative at regional level, with CALABARZON among the seven regions. Microdata are restricted. | FAO Microdata Catalogue 2086, 2321; IHSN 11185 |
| 2023 NNS gives CALABARZON moderate-to-severe household food insecurity of 19.1% | **Verified, with instrument note** | 19.1% (CI 17.0–21.1), measured with **FIES**, via PSA SDG 2.1.2. National 31.4%; CALABARZON lowest region. Not comparable with HFIAS. | PSA SDG 2.1.2; FNRI 2024 Nutrition Summit; earlier AIPHEED verification (`docs/fi9/LABEL_COMPARABILITY_REPORT.md`) |
| Transformer-based quarterly forecasting of 325 crops across 83 provinces, addressing short, sparse, intermittent series | **Partly verified** | The 325 crops, 83 provinces, quarterly horizon, global time-series transformer, and PSA CrPS data are confirmed. The "sparse and intermittent" framing was not confirmed from the abstract; check the full text before citing it. | "A Global Forecasting Approach to Large-Scale Crop Production Prediction with Time Series Transformers" |
| Philippine food-price forecasting studies using WFP data apply ML to forecast prices and price spikes | **Not verified as stated** | No Philippine study combining WFP data, ML and price spikes was found. Cite instead: the World Bank RTP dataset (WFP/FAO prices, ML imputation, 108 Philippine markets); Duyapat (2025), Random Forest on PSA wholesale rice prices; Antonio et al. (2025), drivers of rice inflation. | World Bank Microdata 6172; al-kindipublisher; FAO AGRIS |
| PIDS recommends a national early-warning system with quick or real-time data fetching, processing, and dissemination | **Not verified** | PIDS DP 2022-21 (Galang) recommends data-driven action plans and a modern M&E system backed by a reliable information system. Existing early-warning systems are NNC EWS-FNS and WFP–DSWD EWS-HFI. Locate the exact PIDS source before keeping the "real-time" wording. | PIDS DP 2022-21; Rappler (EWS-FNS) |
| DA CALABARZON publishes production and food-sufficiency information; DA AMIA includes hazard maps and climate-risk information for the region | **Partly verified** | AMIA CRVA maps cover Cavite, Laguna, Batangas, Rizal (2024 terminal report) and Quezon (terminal report). The DA CALABARZON production and food-sufficiency pages were not checked in this review. | amia.da.gov.ph CRVA maps |

## 9. How AIPHEED extends Philippine research, and how to state the contribution

**What is new.** No identified Philippine study integrates all three of the following in one quarterly system for DA Region IV-A:
1. FAO-dimensional government indicators: availability, access, utilization, and stability;
2. NLP-derived news signals, through zero-shot XLM-RoBERTa sentiment and BERTopic topics combined into a bias-corrected Food Stress Sentiment Index (FSSI v2; volume dependence reduced from 0.44 to 0.05);
3. geospatial modelling, with province and LGU disaggregation weighted by PSA poverty and population density.

PhilFSIS organizes data, FAO DIEM monitors households periodically, PRISM and the crop transformer forecast availability, BSP nowcasts inflation from news, and ADB maps poverty. Each covers one part of this chain.

**Wording supported by the evidence.** Two statements in the brief go beyond what AIPHEED's results currently support. Revising them now avoids a gap between the manuscript and the evaluation chapter.

| Brief | Evidence-informed revision |
|---|---|
| "It will forecast food insecurity up to 12 months ahead" | "It will update quarterly and determine empirically, through walk-forward evaluation, the furthest horizon at which forecasts remain reliable" (Specific Objective 2.V). The 12-month results in the literature rest on thousands of IPC-labelled district-periods that do not exist for CALABARZON. |
| "AIPHEED should show that NLP-derived news indicators can make government information more timely" | "AIPHEED tests whether NLP-derived news indicators make government information more timely. News improved the probability quality of next-quarter forecasts once the quarter's news was complete (FI9-N), but did not improve discrimination at the two-quarter dashboard horizon." |

**Suggested gap statement.**

> Existing Philippine systems provide valuable but incomplete support for timely food-security decision-making. PhilFSIS organizes food-security information, FAO conducts periodic household monitoring, PRISM and recent machine-learning studies forecast crop production, and the BSP nowcasts inflation from news. However, no identified study integrates FAO-dimensional government indicators, NLP-derived news signals, and geospatial machine learning into a quarterly food-insecurity forecasting and early-warning system for DA Region IV-A. AIPHEED addresses this gap by using news as a high-frequency complement to delayed official statistics, with its forecasting horizon determined empirically against the food-insecurity measurements that exist for the region: SWS hunger quarterly at the regional level, and FNRI HFIAS at the provincial level.

## 10. References

1. Ahn, Y., Yan, M., Lin, Y.-R., and Wang, Z. (2023). HungerGist: An interpretable predictive model for food insecurity. arXiv:2311.10953. https://arxiv.org/abs/2311.10953
2. Antonio, et al. (2025). Rice price inflation dynamics in the Philippines. FAO AGRIS record. https://agris.fao.org/search/fr/records/682f3beb9d0aa4165340bfa0
3. Asian Development Bank (2020). Mapping poverty through data integration and artificial intelligence. https://www.adb.org/publications/mapping-poverty-data-integration-ai ; Guidebook (2021): https://www.adb.org/publications/guidebook-mapping-poverty-data-integration-ai
4. Balashankar, A., Subramanian, L., and Fraiberger, S. P. (2023). Predicting food crises using news streams. *Science Advances*, 9(9), eabm3449. https://doi.org/10.1126/sciadv.abm3449 ; World Bank blog: https://blogs.worldbank.org/en/opendata/predicting-food-crisis-outbreaks-using-natural-language-processing-news-streams
5. Bańbura, M., Giannone, D., and Reichlin, L. (2010). Nowcasting. ECB Working Paper 1275. https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1275.pdf
6. Bangko Sentral ng Pilipinas (2026). News-based inflation nowcasting, BIS IFC Bulletin 67. https://www.bis.org/2026-07/ifcb67_15.pdf ; unemployment nowcasting, IFC Bulletin 66: https://www.bis.org/ifc/publ/ifcb66_26.pdf
7. DA AMIA. Climate Risk Vulnerability Assessment maps and CALABARZON terminal report. https://amia.da.gov.ph/climate-risk-vulnerability-assessment-crva-maps/
8. DOST-FNRI (2024). 2023 National Nutrition Survey, National Nutrition Summit. https://enutrition.fnri.dost.gov.ph/uploads/2024%20National%20Nutrition%20Summit_Part%201.pdf
9. Duyapat (2025). Rice wholesale price forecasting in the Philippines. https://www.al-kindipublisher.com/index.php/jmss/article/view/11681
10. FAO. Data in Emergencies Monitoring, Philippines Round 1 (catalog 2086) and Round 2 (catalog 2321). https://microdata.fao.org/index.php/catalog/2086 ; https://microdata.fao.org/index.php/catalog/2321
11. Foini, P., Tizzoni, M., Martini, G., Paolotti, D., and Omodei, E. (2023). On the forecastability of food insecurity. *Scientific Reports*, 13, 2793. https://www.nature.com/articles/s41598-023-29700-y
12. Galang (2022). Is food supply accessible, affordable, and stable? PIDS DP 2022-21. https://pidswebs.pids.gov.ph/CDN/document/pidsdps2221.pdf
13. Giannone, D., Reichlin, L., and Small, D. (2008). Nowcasting: The real-time informational content of macroeconomic data. *Journal of Monetary Economics*, 55(4), 665–676.
14. Global time-series transformer for Philippine crop production (2023). https://www.researchgate.net/publication/372893304
15. IFPRI. Predicting Food Crisis. https://www.foodsecurityportal.org/fr/node/3619
16. Jean, N., Burke, M., Xie, M., Davis, W. M., Lobell, D. B., and Ermon, S. (2016). Combining satellite imagery and machine learning to predict poverty. *Science*, 353(6301), 790–794.
17. Lentz, E., Michelson, H., Baylis, K., and Zhou, Y. (2019). A data-driven approach improves food insecurity crisis prediction. *World Development*, 122, 399–409.
18. Martini, G., et al. (2022). Machine learning can guide food security efforts when primary data are not available. *Nature Food*, 3, 716–728.
19. Penson, S., et al. (2024). A data-driven approach for early detection of food insecurity in Yemen's humanitarian crisis. World Bank Policy Research Working Paper 10768.
20. PhilRice / IRRI. Philippine Rice Information System (PRISM). https://prism.philrice.gov.ph/
21. PSA OpenSTAT. Philippine Food Security Information System (PhilFSIS). https://openstat.psa.gov.ph/Featured/PhilFSIS
22. Reserve Bank of India (2021). Forecasting food inflation using news-based sentiment indicators. https://rbi.org.in/Scripts/bs_viewcontent.aspx?Id=4198
23. 510 / Netherlands Red Cross. Typhoon impact model, Philippines. https://www.anticipation-hub.org/Documents/Briefing_Sheets_and_Fact_Sheets/510-philippines-typhoon-model-report.pdf
24. Westerveld, et al. (2021). Forecasting transitions in the state of food security with machine learning using transferable features. *Science of the Total Environment*. https://research-portal.uu.nl/en/publications/forecasting-transitions-in-the-state-of-food-security-with-machin/
25. World Bank. Real Time Food Prices, Philippines. https://microdata.worldbank.org/catalog/6172
26. You, J., Li, X., Low, M., Lobell, D., and Ermon, S. (2017). Deep Gaussian process for crop yield prediction based on remote sensing data. *AAAI-17*. https://doi.org/10.1609/aaai.v31i1.11172
