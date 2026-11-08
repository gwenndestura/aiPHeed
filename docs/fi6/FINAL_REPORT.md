# aiPHeed FI6 — final report (Objectives 1–4)

* **Where the numbers come from:** every number below comes from `python -m app.fi6.pipeline all`, run on
  2026-11-02. The full tables are in [RESULTS.md](RESULTS.md), generated from `backend/data/fi6/out`.
* **What was fixed in advance:** the target, the features, their expected directions, the models and the
  reliability rules were fixed in [DECISION_RECORD.md](DECISION_RECORD.md). They were locked
  (`ccdfda3d6e625c79…`) before the evaluation ran, and the evaluated code matched the lock.
* **What changed after the run:** only the issue/report steps changed. They now apply the same rule to every
  model, add the plain persistence sentence and add the report generator. No prediction or metric changed.

## Summary

| Question | Answer |
|---|---|
| What does the system predict? | The probability that SWS hunger in Balance Luzon (the SWS area that contains all of CALABARZON) is **significantly above its five-year normal**, i.e. higher than the average of the previous 20 quarters by more than the survey's published 95 % margin of error. |
| Is the target better than FI5's? | Yes. Sampling error alone would flip 6.7 % of labels, against 14.2 % for FI5. Unreliable labels (flip probability > 0.2) fall from 34 % to 11 %. |
| Does LightGBM work? | It runs and no longer overfits (in-sample 0.87 vs out-of-sample 0.84 at lead 1; FI5 had 0.91 vs 0.53). But it is **not reliable at any lead**: lead 1 accuracy 0.839, recall 0.27, AUC 0.69. |
| Does it beat the baselines? | It beats PSA-only, NLP-only and logistic regression. It does **not** beat naive persistence at lead 1, and at leads 2–4 the differences are not significant. |
| Furthest reliable lead | **LightGBM: none. Naive persistence: lead 1** (the only method and lead that passes every pre-declared rule). |
| 75 % accuracy? | **Reached at lead 1 (0.871), by persistence, together with recall 0.55 and precision 0.67.** LightGBM's 0.84 is not counted as success, because "always LOW" scores 0.82 and LightGBM catches only 3 of 11 HIGH quarters. |
| Does news help? | No. Removing all news, or any single news domain, changes Brier by ≤ 0.003. |
| Do the five domains help? | Removing any one domain changes Brier by −0.006 to +0.005; none gives a repeatable gain. The forecast is carried by the latest survey reading. |
| Province / LGU | No province-quarter outcome exists, so there are no province forecasts to validate. The 142-LGU ranking uses the validated regional lead-1 forecast (persistence) × PSA poverty and density vulnerability. It is a priority ranking, not a measurement. |

## 1. What the system predicts and why it represents food insecurity

* **The question:** SWS asks families whether they "experienced hunger and did not have anything to eat" in the
  past three months. That is a direct experience of the severe end of the FAO Food Insecurity Experience Scale
  (Cafiero et al. 2018), not a driver such as prices or poverty.
* **What counts as HIGH:** a quarter where hunger rose above its own five-year normal by more than the survey
  could produce by chance. This keeps the FEWS NET "worse than normal" logic and removes the sampling noise that
  defeated FI5.
* **Excluded:** quarters with no SWS round, and the first quarters, which have fewer than 8 earlier readings. They
  are left unlabelled, not set to LOW.
* **How alternatives were chosen between:** six definitions were compared on label reliability alone, before any
  model was fitted. The table is in the decision record.
* **What this target is not:** not province or municipal hunger, not undernourishment (PoU), not poverty.

## 2. Research evidence (concise comparison)

The full review is in [docs/fi5/RESEARCH_EVIDENCE.md](../fi5/RESEARCH_EVIDENCE.md). All DOIs below were verified on
Crossref (`crossref_verification*.json`). Two DOIs tried for this round resolved to unrelated papers and were
dropped.

| Reference | FS concept | Outcome measured | Predictors | Method | Validation | Relevance to aiPHeed |
|---|---|---|---|---|---|---|
| Cafiero, Viviani & Nord 2018, *Measurement* 116:146–152, doi:10.1016/j.measurement.2017.10.065 | experience-based FI (FIES) | FIES scale | — | Rasch measurement | cross-country equating | SWS hunger ≈ severe end of FIES |
| FEWS NET — Funk et al. 2019, *BAMS* 100:1011–1027, doi:10.1175/BAMS-D-17-0233.1; Backer & Billing 2021, *Glob. Food Sec.* 29:100510, doi:10.1016/j.gfs.2021.100510 | acute FI outlooks | IPC-compatible phases | rainfall, prices, livelihoods | scenario-based projection | projections scored against later outcomes | "compared with normal"; score forecasts against later releases |
| Westerveld et al. 2021, *Sci. Total Environ.* 786:147366, doi:10.1016/j.scitotenv.2021.147366 | IPC phase transitions | FEWS NET phases | prices, climate, conflict | random forest etc. | temporal hold-out | skill falls with lead; transitions are hard; persistence is strong |
| Andrée et al. 2020, WB PRWP 9412, doi:10.1596/1813-9450-9412 | crisis onset | IPC ≥ 3 | prices, weather, conflict, NDVI | random forest, logit | out-of-sample | gains concentrated at short leads |
| Foini et al. 2023, *Sci. Rep.* 13:2793, doi:10.1038/s41598-023-29700-y | insufficient food consumption | WFP FCS / rCSI prevalence (mVAM) | the series' own history + covariates | time-series ML | rolling forecast | short-horizon forecastability is limited; history dominates |
| Krishnamurthy et al. 2022, *Nat. Sustain.* 5:956–964, doi:10.1038/s41893-022-00962-0 | drought-related FI change | FEWS NET outcomes | climate, prices | ML | out-of-sample | climate signals help mainly in drought-driven systems |
| Balashankar et al. 2023, *Sci. Adv.* 9:eabm3449, doi:10.1126/sciadv.abm3449 | food crises | IPC phase | news-derived driver signals + traditional data | ML | out-of-sample, 3–12 months | news as driver signals inside domains (the FI6 design); it needed millions of articles |
| Maxwell, Vaitla & Coates 2014, *Food Policy* 47:107–116, doi:10.1016/j.foodpol.2014.04.003 | comparison of household FI indicators | FCS, rCSI, HFIAS, HHS, … | — | correlation, classification agreement | household survey | indicators measure different things; do not mix scales casually |
| Lentz et al. 2019, *World Dev.* 122:399–409, doi:10.1016/j.worlddev.2019.06.008 | household FI | survey consumption/coping | public secondary data | ML | out-of-sample | judge recall of crisis cases, not accuracy |
| Tashman 2000, *IJF* 16:437–450, doi:10.1016/S0169-2070(00)00065-0 | method | — | — | rolling origin | — | walk-forward design |
| Lundberg et al. 2020, *Nat. Mach. Intell.* 2:56–67, doi:10.1038/s42256-019-0138-9 | method | — | — | TreeSHAP | — | plain-language explanations |

## 3. Five domains and indicators

18 features were chosen a priori, each with an expected direction enforced as a LightGBM monotone constraint.
The table, with source, level, frequency, start year, release lag and the reason for each include/exclude
decision, is in the decision record.
* Market and prices: food CPI, rice CPI, palay production, market news.
* Climate stress: rainfall anomaly, storms near CALABARZON, ONI, climate news.
* Employment: unemployment rate and its change (national), employment news.
* OFW remittances: remittance growth (national), remittance news.
* Poverty and social vulnerability: poverty incidence (regional, constrained to raise risk), hardship/aid news.

Employment and remittances are separate domains, and there is no news group.

## 4. NLP and FSSI (Objective 1)

The FI5 tier was reused from cache; nothing was re-scored.
* **Corpus and classifier:** 9,628 unique Filipino/English headlines (2021-01 to 2026-10). XLM-RoBERTa-large-XNLI
  zero-shot labels 1,147 of them relevant, by domain: market 513, climate 435, poverty 166, employment 114,
  remittance 83.
* **Evidence types:** risk factor 626, background 291, government response 202, actual hunger report 28.
* **Topics:** BERTopic finds 11 interpretable topics (frozen 2021–22 fit).
* **FSSI:** event-level and source-weighted. It is a share of coverage, not a count, and thin province cells are
  shrunk toward the region.
* **Validation:** a 200-headline stratified annotation kit is in `backend/data/fi6/nlp_validation/`. The sheet
  shows no model labels; the key is kept separately. Score it with `python -m app.fi6.nlp_validation score`, which
  reports precision, recall and kappa. **It has not been annotated by a person, so the zero-shot labels remain
  unverified.**

**Why news does not help:**
* Coverage starts in 2021, so 2010–2020 training rows have no corpus news.
* Headlines only.
* The corpus was collected retrospectively in Oct 2026.
* 67 % of headlines have no province.
* Many headlines restate official releases that are already in the government features.
* The remittance domain has only 83 relevant headlines.

## 5. LightGBM performance (62 evaluated quarters per lead, 11 HIGH)

| Lead | Accuracy | Balanced acc. | Precision | Recall | F1 | AUC | Brier | Brier skill | Reliable |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.839 | 0.617 | 0.600 | 0.273 | 0.375 | 0.686 | 0.129 | +0.135 | no (recall, AUC) |
| 2 | 0.806 | 0.490 | 0.000 | 0.000 | 0.000 | 0.469 | 0.163 | −0.086 | no |
| 3 | 0.790 | 0.516 | 0.250 | 0.091 | 0.133 | 0.524 | 0.155 | −0.031 | no |
| 4 | 0.790 | 0.552 | 0.333 | 0.182 | 0.235 | 0.597 | 0.160 | −0.058 | no |

* **Calibration at lead 1 is good:** predicted 0.10 vs observed 0.11, 0.29 vs 0.23, and 0.66 vs 0.60 across the
  three populated bins.
* **Hunger level:** MAE skill vs persistence is −0.08, +0.16, +0.07 and +0.03 at leads 1–4. None is significant;
  every bootstrap interval includes 0.

## 6. Baseline comparison (Objective 4, same origins)

| Lead | LightGBM | Persistence | PSA-only | NLP-only | Logistic | Always-LOW |
|---|---|---|---|---|---|---|
| acc / recall / AUC, lead 1 | 0.839 / 0.27 / 0.69 | **0.871 / 0.55 / 0.74** | 0.742 / 0.18 / 0.57 | 0.806 / 0.27 / 0.53 | 0.742 / 0.36 / 0.67 | 0.823 / 0 / — |
| lead 2 | 0.806 / 0 / 0.47 | 0.710 / 0.09 / 0.58 | 0.677 / 0 / 0.39 | 0.790 / 0.27 / 0.56 | 0.629 / 0.27 / 0.44 | 0.823 / 0 / — |
| lead 3 | 0.790 / 0.09 / 0.52 | 0.790 / 0.36 / 0.66 | 0.694 / 0.09 / 0.44 | 0.774 / 0.27 / 0.57 | 0.677 / 0.36 / 0.54 | 0.823 / 0 / — |
| lead 4 | 0.790 / 0.18 / 0.60 | 0.774 / 0.27 / 0.72 | 0.710 / 0.18 / 0.38 | 0.790 / 0.18 / 0.56 | 0.500 / 0.18 / 0.44 | 0.823 / 0 / — |

* **Lead 1:** LightGBM vs persistence: Brier difference +0.012 (95 % CI −0.023 to +0.059), McNemar p = 0.63.
  Persistence is better and the difference is not significant.
* **Lead 2:** LightGBM vs persistence: Brier −0.035 (CI −0.088 to +0.020), McNemar p = 0.07.
* **Why persistence wins:**
  * Elevated hunger comes in multi-quarter episodes (2020–21, 2024–26), and persistence follows them.
  * LightGBM's strongest learned pattern is mean reversion: high readings fall back. That cut its HIGH forecasts
    and its recall.
  * With shuffled training targets, LightGBM's AUC rises to 0.77, above its real 0.69. The feature-based
    adjustments subtract information.

## 7. Reliability across periods

| Lead 1 | 2010–15 (4 HIGH) | 2016–20 (1 HIGH) | 2021–26 (6 HIGH) |
|---|---|---|---|
| Persistence accuracy / recall | 0.83 / 0.50 | 0.94 / 0 | 0.85 / 0.67 |
| LightGBM accuracy / recall | 0.83 / 0.25 | 0.94 / 0 | 0.75 / 0.33 |

There are very few HIGH quarters per era. Persistence's lead-1 recall 95 % interval is 0.28–0.79, so even the
passing result is imprecise. The sealed forecasts are the real test.

## 8. SHAP explanations in plain words

Each forecast gets one or two sentences built from TreeSHAP contributions summed per domain. Only contributions of
at least 0.3 percentage points are mentioned. For 2026-Q4, issued 2026-09-30, the forecast reads:

> Food prices and household hardship pushed the hunger forecast for 2026-Q4 up, while the latest hunger survey
> reading pulled it down. These are the factors the model leaned on, not proven causes.

The validated persistence forecast carries its own sentence:

> The latest survey reading (17.3%) is below the significantly-above-normal line (21.4%), so the simple forecast is
> LOW.

Average contribution sizes, in percentage points of the forecast change, at lead 1:

| Block | Average contribution (pp) |
|---|---|
| Latest reading | 2.6 |
| Employment | 0.87 |
| Climate | 0.67 |
| Market | 0.66 |
| Poverty | 0.16 |
| Remittances | 0.03 |

**The latest survey reading is by far the largest input; the other domains move the forecast little.**

## 9. LGU rankings (Objective 3)

* **Coverage:** all 142 LGUs (Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14). Poverty comes from PSA SAE
  2021, with Lucena taking PSA's 2021 HUC value of 10 %. Density comes from POPCEN 2024. No values are missing.
* **Score:** priority = 100 × P(HIGH, lead 1, persistence) × (½ poverty rank + ½ density rank).
* **Interpretation:** every LGU shares the regional probability, so the order is the vulnerability order. Cavite
  City, Trece Martires, Tanza, General Trias and Taytay lead.
* **Sensitivity:** 11–24 of the top-third LGUs change with other weightings, so the ½/½ weights are a policy
  choice for DA.
* **Missing input:** only Lucena, which uses a published city-level estimate, not a provincial substitute.

## 10. Backend

* **Package:** `backend/app/fi6/` — `target`, `features`, `models`, `evaluate`, `nlp_validation`, `pipeline`,
  `report`. It reuses FI5's verified `sources`, `nlp`, `rankings` and `explain`.
* **API:** `backend/app/api/v1/fi6.py`, mounted in `router.py`. Read-only routes under `/api/v1/fi6/`: `status`,
  `target`, `forecast`, `evaluation`, `baselines`, `provinces`, `lgus`, `nlp/validation`.
* **Outputs:** saved LightGBM models in `backend/data/fi6/models/`. The seal (2026-Q4 to 2027-Q3, sha256
  `d6b99d8c…`) is in `backend/data/fi6/out/SEAL_fi6.csv`.
* **Tests:** `tests/unit/test_fi6.py`; 42 tests pass together with the FI5 and health tests.
* **Untouched:** the approved frontend, the served dashboard model and FIRI v2. There is no FIRI import (verified).
* **Next issue:** forecasts are issued at quarter end, so the 2026-Q3 reading (23.6 %, published 14 Oct) enters at
  the next issue, on 2026-12-31.

## 11. Reproduction (from `backend/`)

FI5 raw data and NLP caches come first (cached; no re-scoring):

```bash
python -m app.fi5.pipeline acquire
```

```bash
python -m app.fi6.pipeline all
```

```bash
python -m app.fi6.report
```

```bash
python -m pytest tests/unit/test_fi6.py tests/unit/test_fi5.py -q
```

The FI6 evaluation takes about 2 minutes on 20 worker processes.

## 12. Remaining limitations and the data that would resolve them

1. **LightGBM does not add skill beyond the latest survey reading.**
   * Cause: about 98 labelled quarters with 16 HIGH, and drivers measured nationally or regionally.
   * What would resolve it: more outcome observations. Options are the PSA APIS hunger item by region/year, FNRI
     FIES rounds, or SWS area microdata (which would allow the other areas to be pooled with matched regional
     drivers).
2. **Province-level validation is impossible.**
   * Cause: no province-quarter food-insecurity observations exist.
   * What would resolve it: provincial FIES/HFIAS from DOST-FNRI or PSA, repeated at least yearly.
3. **News adds nothing.**
   * What would resolve it: a prospective, real-time collector with article bodies, and a larger, pre-2021 corpus.
4. **The zero-shot NLP labels are unverified until the annotation kit is filled.** Two annotators are recommended.
5. **The LGU vulnerability weights need DA sign-off.**
6. **Everything here is development evidence.** All 1998–2026 quarters had been seen by earlier work. The sealed
   2026-Q4+ forecasts are the first clean test of the reliability claim, for both LightGBM and persistence.
