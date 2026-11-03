# Research evidence register (2026-11-03)

Verification column:
- **Crossref**: DOI resolved at doi.org and title, authors and year were read from the Crossref API on 2026-11-03.
- **Repo**: the URL is recorded in this repository's data manifests; it was not re-fetched today.
- **Not re-checked**: cited from the reviewer's knowledge; it must be checked before it is quoted in the thesis.

A tenth DOI was checked and turned out to be an unrelated paper (fertilizer valuation, Food Policy 2020). It was removed.

## A. Measurement of food insecurity

| # | Source | Year | DOI / URL | Finding used | Relevance and limitation | How it shaped the system | Verification |
|---|---|---|---|---|---|---|---|
| 1 | Cafiero, Viviani, Nord, "Food security measurement in a global context: The food insecurity experience scale", *Measurement* | 2018 | 10.1016/j.measurement.2017.10.065 | FIES is an experience-based scale with a Rasch measurement model; moderate-or-severe prevalence is comparable across countries after calibration to a global standard | Defines the SDG 2.1.2 outcome. Comparability across survey vintages depends on the same instrument and calibration | FIES moderate-or-severe chosen as the primary outcome. FIES and HFIAS are never pooled | Crossref |
| 2 | Coates, Swindale, Bilinsky, *Household Food Insecurity Access Scale (HFIAS) for Measurement of Food Access: Indicator Guide (v3)*, FANTA | 2007 | fantaproject.org (HFIAS guide) | HFIAS uses 9 items with a 30-day recall and defines its own categories | FNRI 2015 used HFIAS, so its categories are not FIES categories | FNRI 2015 used only as provincial relative position (offset from CALABARZON), with an added drift allowance | Not re-checked |
| 3 | PSA OpenSTAT, SDG 2.1.2 (FIES, FNRI ENNS/NNS) | 2019–2023 | openstat.psa.gov.ph DB/3I/G02/0023I3B2121.px | National 44.2 / 33.4 / 31.4%; 17 regions 2023; Region IV-A 19.1% (CI 17.0–21.1) | Only regional detail in 2023; no provincial series | Outcome for the level model, the benchmark and the bridge | Repo (`published_fies_psa_sdg212.csv`) |
| 4 | DOST-FNRI, 2015 Food Security Survey (Appendices 1–4) | 2015 | enutrition.fnri.dost.gov.ph/uploads/2015_FOOD_SECURITY_SURVEY.pdf | Provincial HFIAS shares with SEs (n 735–1,076 households per province) | Only verified provincial food-security measurement; 2015 and HFIAS | Direct component of the provincial composite | Repo (owner workbook) |
| 5 | PSA, Official Poverty Statistics (full-year 2021 and 2023) | 2022, 2024 | psa.gov.ph | Poverty and subsistence incidence with CVs by region and province | Provincial subsistence CVs are 25–53% (low reliability) | Structural covariates; CVs used to shrink provincial values | Repo (`psa_*_2018_2023.csv`) |

## B. Small-area estimation

| # | Source | Year | DOI | Finding used | How it shaped the system | Verification |
|---|---|---|---|---|---|---|
| 6 | Fay and Herriot, "Estimates of Income for Small Places: An Application of James-Stein Procedures to Census Data", *JASA* | 1979 | 10.1080/01621459.1979.10482505 | Area-level model that combines a direct estimate and a regression estimate weighted by their variances | Provincial composite (direct FNRI 2015 offset + regression offset) | Crossref |
| 7 | Ybarra and Lohr, "Small area estimation when auxiliary information is measured with error", *Biometrika* | 2008 | 10.1093/biomet/asn048 | Covariates estimated from surveys add error that must be accounted for | Provincial covariates shrunk by their published CVs; error propagated | Crossref |
| 8 | Rao and Molina, *Small Area Estimation* (2nd ed.), Wiley | 2015 | 10.1002/9781118735855 | Benchmarking small-area estimates to reliable direct totals; mean squared error of composites | Provincial values benchmarked to the direct CALABARZON FIES estimate | Crossref |

## C. Forecasting, early warning and evaluation

| # | Source | Year | DOI | Finding used | How it shaped the system | Verification |
|---|---|---|---|---|---|---|
| 9 | Lentz, Michelson, Baylis, Zhou, "A data-driven approach improves food insecurity crisis prediction", *World Development* | 2019 | 10.1016/j.worlddev.2019.06.008 | Prices, weather, demographics and past outcomes predict survey-measured food security in Malawi; the outcome is a repeated household survey | Shows the data a learned forecaster needs: a repeated measured outcome. aiPHeed lacks one for provinces, hence gate B6 | Crossref |
| 10 | Balashankar, Subramanian, Fraiberger, "Predicting food crises using news streams", *Science Advances* | 2023 | 10.1126/sciadv.abm3449 | News-derived features improved IPC food-crisis forecasts | Basis for an improved N1. It needs a repeated outcome to learn against; IPC phases are not available for CALABARZON | Crossref |
| 11 | World Bank Policy Research Working Paper 9412, "Predicting Food Crises" (Crossref lists Spencer, Kraay, Wang, Andrée) | 2020 | 10.1596/1813-9450-9412 | Machine-learning forecasts of IPC phases need long panels and are evaluated out of sample against persistence | Persistence and no-change baselines are required in gate B8 | Crossref |
| 12 | Tashman, "Out-of-sample tests of forecasting accuracy: an analysis and review", *Int. J. Forecasting* | 2000 | 10.1016/S0169-2070(00)00065-0 | Rolling-origin out-of-sample evaluation; avoid tuning on the test period | Chronological evaluation is a gate requirement (B6), with minimum sample sizes | Crossref |
| 13 | Gneiting and Raftery, "Strictly Proper Scoring Rules, Prediction, and Estimation", *JASA* | 2007 | 10.1198/016214506000001437 | Brier score is a proper scoring rule; probabilities should be judged by proper scores and calibration | Brier and calibration error in gates B8 and B10 | Crossref |

## D. Established, adapted, new, assumed

| Element | Category |
|---|---|
| FIES moderate-or-severe as the outcome; Fay-Herriot composite; benchmarking; error-in-covariates shrinkage; rolling-origin evaluation; proper scores | Established method (A1, B6–8, C12–13) |
| Using FNRI 2015 HFIAS only as provincial relative position for a FIES estimate | Adaptation for CALABARZON |
| SWS-to-FIES bridge (Δlogit FIES = λ Δlogit SWS12) | New engineering decision; tested on one held-out wave |
| Drift allowance 0.10 logit; 2025 SE = 1.5 × 2023 SE; release dates at month-end | Assumptions needing validation |
| Release-gate thresholds (accuracy ≥ 0.75, balanced ≥ 0.70, HIGH recall ≥ 0.60, ECE ≤ 0.10, ≥ 20 targets with ≥ 10 HIGH) | Project rule (FI9-Z locked class rule plus this directive) |
