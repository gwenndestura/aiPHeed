# v9 Stage 2: How organizations define and monitor food insecurity

**Verification levels (fetched 2026-11-02 unless noted):**
- **FULL**: full text read (HTML or extracted PDF text).
- **PARTIAL**: abstract or search-result excerpt of the named source only. Facts stated are limited to that excerpt.
- **UNVERIFIED-CITATION**: not confirmed. **Gate 2: nothing later may rely on it.**

**Standing constraint:** no `sws.org.ph` access, and no "latest" queries on PSA series, to protect the sealed quarters.

## Definitions matrix

| Organization / instrument | Definition, indicator | Data, geography, frequency | Uncertainty | Lag | Forecasting? | AIPHEED may claim | May not claim | Level |
|---|---|---|---|---|---|---|---|---|
| FAO, SDG 2.1.2 / FIES | Prevalence of moderate or severe food insecurity on the FIES global reference scale, using Rasch modelling; universal thresholds are converted to local scales by equating, which needs at least 4 of 8 items in common | Representative samples; national surveys or Gallup World Poll | Rasch reliability and item-fit checks reported | Annual reporting | No | That FIES is the reference construct | That SWS or CPI values are SDG 2.1.2 values | FULL ([UN metadata](https://unstats.un.org/sdgs/metadata/files/Metadata-02-01-02.pdf)) |
| DOST-FNRI ENNS/NNS | Household FIES prevalence (added in 2019 ENNS). National: **44.2 % (2019), 33.4 % (2021), 31.4 % (2023; 95 % CI 30.7–32.1)**; severe 2.7 % in 2023. HFIAS also reported (2018–19: 44.0 % food secure) | 2023: 36,703 households; regional | CIs published | About 1 year | No | National trend; regional anchor once obtained | Provincial or quarterly values | FULL for national ([2024 Summit](https://enutrition.fnri.dost.gov.ph/uploads/2024%20National%20Nutrition%20Summit_Part%201.pdf), [2018-19 Facts](https://enutrition.fnri.dost.gov.ph/uploads/2018-2019%20ENNS%20FACTS%20AND%20FIGURES_JULY182023.pdf)). **CALABARZON 2019 and 2023: NOT OBTAINED** |
| FNRI 2023, regional | BARMM highest 48.2 %, Calabarzon lowest (no number); Davao 37.8 % | | | | | | | PARTIAL ([Mindanao Times](https://www.mindanaotimes.com.ph/davao-region-records-37-8-moderate-to-severe-household-food-insecurity-in-2023-dost-fnri/), secondary) |
| FNRI 2025 | Repo holds CALABARZON 22.6 %, national 32.6 % from press | | | | | Context only, flagged secondary | Primary-source figure | NOT re-verified this session (`enns_fetcher.py`) |
| PSA poverty | Subsistence incidence: families below the provincial food threshold. National 2023: 2.7 % of families, 4.3 % of population | FIES-based, province, triennial; CV warnings above 20 % for Region IV-A in the preliminary 2023 table | CVs published | Months | No | Vulnerability weight (O3) | Food-insecurity measure | PARTIAL ([press release](https://psa.gov.ph/system/files/phdsd/Press%20Release_2023%20Full%20Year%20Poverty%20Statistics.pdf), [technical notes](https://psa.gov.ph/statistics/poverty/technical-notes)) |
| PSA CPI (provincial), LFS, palay | Methods | | | | | Data values only, as audited in v6 | Any statement about method detail | **UNVERIFIED-CITATION** |
| SWS hunger | Repo: families reporting involuntary hunger, past 3 months; 4 areas | 300–1,080 per area; quarterly | Published margins | Median 32 days | No | "Balance Luzon hunger" | Provincial or CALABARZON value | Wording **UNVERIFIED-CITATION** (protected). Sampling facts from `sws_area_rounds.csv` |
| IPC | Area in a phase when at least 20 % of population is in that phase or worse | Analyst consensus, sub-national | Confidence levels | Periodic | Projections | Used as literature target only | IPC-compatible results | PARTIAL ([IPC Q&A](https://www.ipcinfo.org/fileadmin/user_upload/ipcinfo/docs/IPC_Q_A.pdf), [Manual 3.1](https://www.ipcinfo.org/fileadmin/user_upload/ipcinfo/manual/IPC_Technical_Manual_3_Final.pdf) located, not read) |
| FEWS NET | IPC-compatible outlooks; expert benchmark in literature. Thesis: no Philippine coverage | 37 countries | | | Yes, near and medium term | Benchmark concept | Coverage of the Philippines | PARTIAL ([FEWS NET](https://fews.net/about/integrated-phase-classification)) |
| WFP HungerMap LIVE | Near-real-time monitoring plus ML nowcasts labelled separately from observed values | Over 90 countries; models trained on 63 countries, 14 years | | Daily | Nowcast | Practice of separating modeled from measured | | PARTIAL ([WFP](https://www.wfp.org/stories/wfp-launches-hungermap-live), [methods slides](https://www.nutritioncluster.net/sites/nutritioncluster.com/files/2021-02/Session%204)%20HungerMap%20LIVE%20-%20Predictive%20model.pdf)) |
| WFP CARI; GEOGLAM; FAO GIEWS; FAO SOFI | | | | | | | | **UNVERIFIED-CITATION**, not relied on |

## ML forecasting of food insecurity

| Source | Target | Horizon | Features | Model | Validation | Result and own limits | Level |
|---|---|---|---|---|---|---|---|
| Andrée, Chamorro, Kraay, Spencer, Wang 2020, [WB PRWP 9412](https://documents1.worldbank.org/curated/en/304451600783424495/pdf/Predicting-Food-Crises.pdf) | IPC ≥ 3, binary; 1,162 districts, 21 countries | Up to 12 months | Remote sensing, conflict, food prices | Random forest with a loss weighting false negatives against false positives | Cross-validation plus temporal holdout; compared with binarized FEWS NET | At 4- and 8-month horizons FNR falls below 20 % (FEWS NET 74 %, 79 %) with FPR about 7 %. Warns single holdouts depend on composition | FULL |
| Foini et al. 2023, [Sci Rep](https://pmc.ncbi.nlm.nih.gov/articles/PMC10038988/) | Daily insufficient food consumption | ≤ 30 days | Coping, conflict, prices, rain, NDVI | XGBoost per horizon | Time-ordered splits vs last value | Beats last value only in Yemen and Syria at long horizons (30 days R² 72 vs 65, 47 vs 31); **worse in 4 other countries with fewer than half the data; history length is the key factor** | FULL |
| Balashankar et al. 2023 | See `../v10/NEWS_LITERATURE.md` | | | | | | FULL |
| Lentz et al. 2019, [World Dev.](https://www.sciencedirect.com/science/article/abs/pii/S0305750X19301603) | 3 food security measures, Malawi village clusters | Next survey (2010 fit, 2013 test) | Open data | | Out-of-sample year | Transferable approach claimed | PARTIAL |
| Westerveld et al. 2021, [Sci. Total Environ. 786](https://research.vu.nl/en/publications/forecasting-transitions-in-the-state-of-food-security-with-machin/) | IPC transitions, Ethiopia | 3 months reasonable | Transferable | ML | | Not *Science Advances* as sometimes cited | PARTIAL |
| Busker et al. 2024, [Earth's Future](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023EF004211) | IPC, Horn of Africa | Up to 12 months | | XGBoost | | | PARTIAL |
| Carneiro et al. 2025, [Sci Rep](https://pmc.ncbi.nlm.nih.gov/articles/PMC12540806/) | Whether a FEWS NET report mentions food insecurity | **None: not a forecast** | Hazard topics in the same report | RF best, AUC 0.79 | 70/30 split | Associations only. **Chapter I's "strongest predictor" should be read as association in report text** | FULL |
| Wang et al. (WFP) | | | | | | Lead not found | **UNVERIFIED-CITATION** |

## Alignment: where AIPHEED matches or departs from practice

| Choice | Practice | AIPHEED | Verdict |
|---|---|---|---|
| Target | IPC phases or survey-based indicators with many area-time rows | SWS area hunger plus provincial CPI | **Departs**; no IPC exists here (thesis's reason). Composite has no precedent found |
| Threshold | IPC ≥ 3 is externally defined | Whole-period median (legacy) | **Contradicts practice**; externally fixed rule required (Stage 1 e) |
| Sample | Thousands to tens of thousands of area-periods | 10 effective target quarters | **Contradicts**: Foini shows ML fails to beat last value even with far more data than this |
| Baseline | Last value or expert outlook | Persistence | **Matches** |
| Imbalance | Loss or weighted recall and precision | Balanced accuracy, PR-AUC, MCC beside accuracy | **Matches** |
| Validation | Temporal folds, temporal holdout | Walk-forward plus sealed future | **Matches, stricter** |
| Modeled vs measured | WFP labels nowcasts separately | `evidence_status` per value | **Matches** |

**Plain conclusion.** Published gains come from panels orders of magnitude larger than CALABARZON's. Where a peer-reviewed study had less data, the naive baseline won. The AIPHEED development result is what that literature would predict (INFERRED).

## Gate 2

**PASSED with restriction:** later stages may cite only FULL or PARTIAL sources for the specific fact stated. UNVERIFIED-CITATION items are excluded.
