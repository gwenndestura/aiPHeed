# FORECAST_RESEARCH: sources and the decisions they support

I checked each source on 2026-10-27, by web search or by fetching the page. "Fetched" means I read the page itself. "Record" means I confirmed the bibliographic record and the abstract only. Each source supports only the principle listed beside it. None of these sources evaluated aiPHeed.

## Measurement and target

| # | Source | Checked | Principle used | How it applies to aiPHeed |
|---|---|---|---|---|
| S1 | FAO, *The Food Insecurity Experience Scale (FIES)*. https://www.fao.org/measuring-hunger/access-to-food/about-the-food-insecurity-experience-scale-%28fies%29/ | Fetched | FIES is an experience-based measure of the **access** dimension. "No single tool can account for the multiple dimensions of food security." | SWS involuntary hunger is also experience-based and covers access only. A food-price rise is an access *pressure*, not observed food insecurity. T43c is therefore a composite **proxy**: an experienced-hunger term (regional) AND a provincial price-pressure term. |
| S2 | FAO (2006), *Food Security*, Policy Brief Issue 2. Verified in the BIAS_AUDIT session. | Record (earlier session) | Four dimensions: availability, access, utilization, stability. | aiPHeed covers access (hunger, prices, income) and part of availability (production). Utilization is not measured. |
| S3 | Altman DG, Royston P. The cost of dichotomising continuous variables. *BMJ* 2006;332:1080. doi:10.1136/bmj.332.7549.1080 (PMC1458573) | Record | Splitting a continuous variable into two groups loses information and power, and makes values just either side of a cut point look very different. | The price term is a cut on a continuous food-CPI YoY. FR2 models the continuous projection error and converts it to a probability only at the end. Errors within 0.5 points of a threshold are reported as borderline. |

## Evaluation

| # | Source | Checked | Principle used | How it applies to aiPHeed |
|---|---|---|---|---|
| S4 | Hyndman RJ, Athanasopoulos G. *Forecasting: Principles and Practice* (3rd ed.), §5.10 Time series cross-validation. https://otexts.com/fpp3/tscv.html | Fetched | Evaluation on a rolling forecasting origin: each training set uses only earlier observations. Error is assessed at the horizon of interest, and it grows with the horizon. | Every forecast is made at its own origin from data published before the issue date. Results are reported per lead. |
| S5 | Tashman LJ. Out-of-sample tests of forecasting accuracy: an analysis and review. *Int J Forecasting* 2000;16(4):437-450 | Record | Out-of-sample tests need explicit design choices (origin, horizon, re-fitting) so that they are reproducible. | The protocol fixes the origins, refitting at every origin, the horizons and the blocks before scoring. |
| S6 | Gneiting T, Raftery AE. Strictly proper scoring rules, prediction, and estimation. *JASA* 2007;102(477):359-378. doi:10.1198/016214506000001437 | Record | Brier score and log loss are strictly proper: they reward honest probabilities. | The Brier score is the primary score. Accuracy at 0.50 is a secondary criterion. |
| S7 | scikit-learn User Guide, §1.16 Probability calibration. https://scikit-learn.org/stable/modules/calibration.html | Fetched | Calibration data must be disjoint from training data. Isotonic regression overfits on small data (it needs more than ~1000 samples); sigmoid suits small samples. A lower Brier score does not by itself mean better calibration. | No calibrator is fitted on evaluation outcomes. With fewer than 400 training rows, isotonic regression is not used. Calibration is reported separately: reliability bins, calibration-in-the-large and slope. |
| S8 | Van Calster B et al. Calibration: the Achilles heel of predictive analytics. *BMC Med* 2019;17:230. doi:10.1186/s12916-019-1466-7 | Record | Poorly calibrated risks mislead decisions. Calibration should be assessed, with care for model complexity relative to sample size. | Reliability is reported per lead. The flat-projection bias (FR1) is a calibration-in-the-large defect. |
| S9 | Riley RD et al. Calculating the sample size required for developing a clinical prediction model. *BMJ* 2020;368:m441. doi:10.1136/bmj.m441 | Record | Datasets too small for the number of predictors or events produce inaccurate predictions. | With 17 HIGH rows in 7 quarters per lead, and an effective sample of about 30, the number of free parameters must stay small. That favours a structural base plus a few learned corrections. |

## Forecasting method

| # | Source | Checked | Principle used | How it applies to aiPHeed |
|---|---|---|---|---|
| S10 | Atkeson A, Ohanian LE. Are Phillips curves useful for forecasting inflation? *FRB Minneapolis Quarterly Review* 2001;25(1). https://minneapolisfed.org/research/quarterly-review/are-phillips-curves-useful-for-forecasting-inflation | Record | A naive inflation forecast is hard to beat with structural predictors, and coefficients are unstable across samples. | Every price-part arm must beat the base-effect (no-change) projection, not only always-LOW. |
| S11 | Ben Taieb S, Bontempi G, Atiya A, Sorjamaa A. A review and comparison of strategies for multi-step ahead time series forecasting. *Expert Syst Appl* 2012;39(8):7067-7083 (arXiv:1108.3259) | Record | Strategies for multiple horizons (recursive, direct, multiple-output) differ in accuracy. Multiple-output strategies performed best on NN5. | The unified (pooled-lead) LightGBM is a shared multi-horizon model. FR compares it with per-lead fits. |
| S12 | Foini P, Tizzoni M, Martini G, Paolotti D, Omodei E. On the forecastability of food insecurity. *Sci Rep* 2023;13:2793. doi:10.1038/s41598-023-29700-y | Record | Gradient-boosted trees forecast a food-consumption indicator against a naive baseline, with accuracy assessed by horizon. | The naive (persistence) baseline is mandatory. Forecastability is measured, not assumed. |
| S13 | Lentz EC, Michelson H, Baylis K, Zhou Y. A data-driven approach improves food insecurity crisis prediction. *World Dev* 2019;122:399-409. doi:10.1016/j.worlddev.2019.06.008 | Record | Market prices and other routinely available data can predict food-security outcomes, compared against the prevailing early-warning method. | This supports using price data as an access predictor. It does not show that prices *are* food insecurity. |
| S14 | LightGBM documentation, Parameters. https://lightgbm.readthedocs.io/en/latest/Parameters.html | Fetched | `max_depth` "is used to deal with over-fitting when #data is small"; `min_data_in_leaf` and `lambda_l2` also control over-fitting. `monotone_constraints` sets the direction. Continued training from initial scores is supported. | FR uses shallow trees (depth 1-2), min_child 10-15 and an L2 penalty. The structural projection enters as the base score, so LightGBM learns only corrections. |

## Explanations

| # | Source | Checked | Principle used | How it applies to aiPHeed |
|---|---|---|---|---|
| S15 | scikit-learn User Guide, §5.2 Permutation feature importance. https://scikit-learn.org/stable/modules/permutation_importance.html | Fetched | With correlated features, permuting one leaves the information in the other, which lowers both importances. Importance shows importance *to a model*, not intrinsic value. Compute it on held-out data. | Family contributions are measured by refit ablation on rolling held-out rows, with permutation as a secondary check. Correlated families (A1/A3/world prices) are also ablated together. |
| S16 | Lundberg SM, Lee S-I. A unified approach to interpreting model predictions. NeurIPS 2017 (arXiv:1705.07874). Verified in the BIAS_AUDIT session. | Record (earlier session) | SHAP values decompose a model's output additively. | SHAP is reported as relative model influence, never as a causal effect. |

## Philippine context

| # | Source | Checked | Principle used | How it applies to aiPHeed |
|---|---|---|---|---|
| S17 | Executive Order No. 62, s. 2024 (rice tariff cut from 35% to 15%, signed 2024-06-20). USDA FAS GAIN report RP2024-0023: https://www.fas.usda.gov/data/philippines-philippines-issued-eo-62-modifying-import-duty-rates; Inquirer: https://business.inquirer.net/464688/marcos-formalizes-rice-tariff-cut-via-eo-62 | Record | A policy decision lowered rice import costs from mid-2024. | It is a price shock that no 2021-26 indicator could forecast before June 2024. It explains part of the 2025 price-term false alarms. |
| S18 | PSA CPI (OpenSTAT 0012M4ACP22), SWS hunger rounds, and the other indicator sources | Repository records (`E107 INVENTORY`, `FINAL_SYSTEM_SELECTION/annotation`) | Publication timing and definitions. | The PSA site refuses automated access (403). sws.org.ph was not searched (blind-boundary rule). Publication dates come from the repository's verified rounds file. |

Not used: anything that would show a value for a quarter after 2026-Q3.
