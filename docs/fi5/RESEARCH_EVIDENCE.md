# FI5 research evidence and methodology justification

Every journal reference below was checked against Crossref on 2026-11-02 (`crossref_verification.json` in this
folder holds the returned title, authors, year, journal, volume and pages). Institutional sources are cited by
their official pages. Nothing here is quoted from memory without that check.

## 1. What "food insecurity" means here (measurement frameworks)

| Source | What it defines | What FI5 takes from it |
|---|---|---|
| FAO, *Measuring hunger* and the Food Insecurity Experience Scale (FIES), https://www.fao.org/measuring-hunger/en ; Cafiero, Viviani & Nord (2018), *Measurement* 116, 146–152, doi:10.1016/j.measurement.2017.10.065 | Food insecurity is an **experience** of limited access to food, measured on a scale from worry, to reduced quality, to reduced quantity, to going without eating. Moderate and severe food insecurity are thresholds on that scale. | The SWS question ("experienced hunger and had nothing to eat in the past three months") asks about the **severe end** of the same experience scale. FI5 therefore treats SWS involuntary hunger as a direct food-insecurity observation, not a proxy. |
| FAO Prevalence of Undernourishment (PoU), FAOSTAT, https://www.fao.org/faostat/ | Undernourishment = habitual calorie intake below requirement, **modelled** from national food supply and consumption distributions; national and three-year averaged. | Not usable as a quarterly provincial target (national, modelled, annual). Kept apart from hunger: the two are not interchangeable. |
| FAO food security dimensions (availability, access, utilization, stability); SOFI reports, https://www.fao.org/publications/sofi | Organising frame for drivers. | Used to check indicator coverage: market/prices and production = availability + access; employment, remittances and poverty = access; climate and typhoons = stability (and availability). **Utilization is not covered** by any quarterly series for CALABARZON (FNRI nutrition surveys are infrequent) and is reported as a gap. |
| IPC Technical Manual 3.1, https://www.ipcinfo.org/ | Acute vs chronic food insecurity; area classification by **convergence of evidence**; evidence-quality rules; IPC phases are not produced for the Philippines' provinces quarterly. | No IPC labels were created. The idea that several weak evidence streams are combined, with their quality stated, shapes FI5's two-layer output (validated area forecast + clearly labelled LGU priority). |
| WFP HungerMap LIVE, https://hungermap.wfp.org/ ; Martini et al. (2022), *Nature Food* 3, 716–728, doi:10.1038/s43016-022-00587-8 | Where surveys are missing, WFP **nowcasts** food consumption from secondary data (prices, conflict, climate, macro). Estimates are modelled, not ground truth. | Confirms the driver families FI5 uses (prices, climate, macro/income). FI5 does **not** use HungerMap estimates as Philippine ground truth. |
| FEWS NET — Funk et al. (2019), *BAMS* 100(6), 1011–1027, doi:10.1175/BAMS-D-17-0233.1; Backer & Billing (2021), *Global Food Security* 29, 100510, doi:10.1016/j.gfs.2021.100510 | Early warning compares current conditions with what is **normal** (e.g. the five-year average) and validates projections against later outcomes. | FI5's HIGH label = hunger above its own five-year average; forecasts are scored against later SWS releases only. |
| DOST-FNRI ENNS / FIES / HFIAS, https://enutrition.fnri.dost.gov.ph | Household food insecurity prevalence, provincial in only a few rounds (2018–19 pooled, 2021, 2023 regional). | At most three points per province: not enough for a quarterly target. Reported as a validation reference and a gap. |
| PSA official poverty statistics, SAE 2021, POPCEN 2024, LFS, CPI, crop statistics (https://openstat.psa.gov.ph) | Poverty (income below the poverty line) is a vulnerability, not food insecurity itself. | Poverty, population density, prices, production and employment enter as **explanatory** variables or LGU weights, never as the outcome. |
| BSP OF remittances (via World Bank WDI BX.TRF.PWKR.CD.DT, BSP data) | National personal remittances. | National level kept national; no provincial remittance values are invented. BSP's own site refused automated download (HTTP 403), so the WDI mirror of BSP data is used. |
| PAGASA / NASA POWER / IBTrACS / NOAA ONI | Weather, typhoon tracks, ENSO. | PAGASA station data require a formal request; NASA POWER (gridded, province centroids), IBTrACS tracks (which include PAGASA/JMA/JTWC best tracks) and ONI are the public substitutes. |

## 2. Forecasting literature (what was predicted, how it was validated, what transfers)

| Study | Predicted (ground truth) | Inputs | Geography / period | Horizon and validation | Result | Limits | Used in FI5 |
|---|---|---|---|---|---|---|---|
| Lentz, Michelson, Baylis & Zhou (2019), *World Development* 122, 399–409, doi:10.1016/j.worlddev.2019.06.008 | Household food consumption / coping (LSMS-type survey outcomes), classified by thresholds | Prices, rainfall, remote sensing, demographics | Malawi, villages; 2010–2013 | Out-of-sample by period; classification | Data-driven models beat the existing early-warning classification for the outcome | Survey-period outcomes; short history | Use public, routinely published predictors; judge recall of crisis cases, not only accuracy |
| Westerveld et al. (2021), *Sci. Total Environ.* 786, 147366, doi:10.1016/j.scitotenv.2021.147366 | Transitions in IPC phase (FEWS NET) | Market prices, climate, conflict, land cover | Ethiopia, livelihood zones; 2009–2020 | Forecast 4–12 months ahead; temporal hold-out | Accuracy falls with horizon; transitions are much harder than persistence | IPC phases are themselves expert-judged; class imbalance | Report every lead with the same rule; compare with persistence |
| Andrée, Chamorro, Kraay, Spencer & Wang (2020), World Bank PRWP 9412, doi:10.1596/1813-9450-9412 | IPC phase ≥3 onset (FEWS NET) | Prices, weather, conflict, macro, NDVI | 21 countries, districts; 2009–2020 | Random forest / logit; out-of-sample; lead up to 12 months | Gains over naive models are concentrated at short leads; persistence is a strong benchmark | Expert-judged target | Logistic regression and naive persistence are mandatory baselines |
| Balashankar, Subramanian & Fraiberger (2023), *Science Advances* 9(9), eabm3449, doi:10.1126/sciadv.abm3449 | IPC phase (food crises) | News-derived indicators from 11 million articles + traditional covariates | 21 countries, districts; 1980–2020 news | Out-of-sample; 3–12 months | News features improved crisis prediction over traditional indicators at several horizons | Very large corpus (millions of articles) | Motivates news **inside** driver domains and a test of whether news adds information; FI5's corpus is ~9.6 k headlines, a far smaller signal |
| Deléglise et al. (2022), *Expert Syst. Appl.* 190, 116189, doi:10.1016/j.eswa.2021.116189 | Food consumption scores (survey) | Heterogeneous: climate, prices, remote sensing | Burkina Faso; 2009–2018 | Spatial/temporal splits | Gradient boosting competitive; spatial transfer weaker | Survey-based outcome | Gradient boosting with strong regularisation on small samples |
| Martini et al. (2022), *Nature Food* 3, 716–728, doi:10.1038/s43016-022-00587-8 | Prevalence of insufficient food consumption (WFP mobile surveys) | Prices, rainfall, NDVI, conflict, macro | 40+ countries, admin-1 | Nowcast; spatial cross-validation | Useful nowcasts where survey data are missing | Nowcast, not long-lead forecast | Driver families; caution that modelled estimates are not ground truth |
| Zhou, Lentz, Michelson, Kim & Baylis (2022), *AEPP* 44(2), 893–910, doi:10.1002/aepp.13214 | Principles paper | — | — | — | Transparency, usability, careful validation for food-security ML | — | Plain-language explanations; disclose what the score is and is not |
| Tashman (2000), *Int. J. Forecasting* 16, 437–450, doi:10.1016/S0169-2070(00)00065-0 | Method | — | — | Rolling-origin (walk-forward) evaluation | Fixed-origin hold-outs overstate accuracy | — | Expanding-window walk-forward with refit at every origin |
| Brier (1950), *Monthly Weather Review* 78, 1–3, doi:10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2 | Method | — | — | Probability scoring | — | — | Brier score and Brier skill vs climatology |

## 3. NLP and modelling methods

| Method | Reference | Why it is used |
|---|---|---|
| XLM-RoBERTa (multilingual encoder, 100 languages incl. Tagalog) | Conneau et al. (2020), ACL, 8440–8451, doi:10.18653/v1/2020.acl-main.747 | Filipino and English headlines in one model |
| Zero-shot classification by entailment (NLI) | Yin, Hay & Roth (2019), EMNLP-IJCNLP, 3912–3921, doi:10.18653/v1/D19-1404 | No labelled Philippine food-insecurity news corpus exists; hypotheses state the domain, the evidence type and the direction |
| Multilingual sentence embeddings (paraphrase-multilingual-MiniLM-L12-v2) | Reimers & Gurevych (2020), EMNLP, 4512–4525, doi:10.18653/v1/2020.emnlp-main.365 | Embeddings for BERTopic and near-duplicate (same event) detection |
| BERTopic | Grootendorst (2022), arXiv:2203.05794 (preprint) | Unsupervised topics; number of topics not fixed in advance |
| LightGBM | Ke et al. (2017), *Advances in NeurIPS* 30, https://papers.nips.cc/paper/6907 | Tree boosting that handles missing values natively (news exists only from 2017/2021) |
| TreeSHAP | Lundberg et al. (2020), *Nature Machine Intelligence* 2, 56–67, doi:10.1038/s42256-019-0138-9 | Exact per-forecast contributions, summed per domain for plain sentences |
| Composite-indicator weighting | OECD/JRC (2008), *Handbook on Constructing Composite Indicators* | Equal weights for the two LGU vulnerability components when no outcome exists to estimate weights |

## 4. Research decision (the simplest reliable design for the data that exist)

1. **Target.** SWS involuntary hunger, Balance Luzon, quarterly 1998-Q3 to 2026-Q3 (98 labelled quarters). It is
   the only direct, repeated food-insecurity observation covering CALABARZON. HIGH = above its own five-year
   average (FEWS NET/GIEWS "worse than normal" convention). No quarter without a survey round is labelled.
2. **Level.** The model forecasts at the level the outcome is measured (Balance Luzon, which contains all five
   provinces). Province-quarter food-insecurity observations do not exist, so a *validated province-level forecast*
   is not possible from public data; provinces and LGUs receive the validated area forecast plus a transparent
   vulnerability adjustment, labelled as a priority ranking.
3. **History.** Pre-2021 data are used wherever the series is consistent: SWS 1998+, CPI 1994+, palay 1987+,
   NASA POWER 1981+, IBTrACS, ONI, remittances 1990+, LFS 2005+ (the 2005 unemployment definition; earlier rounds
   use a different definition and are not joined), poverty 2006–2025 (methodology break 2015→2018 disclosed).
4. **Five domains with news inside them**; one regularised LightGBM per lead with the same features; four
   baselines on identical walk-forward origins; reliability rules fixed before scoring (METHOD_LOCK.json).
