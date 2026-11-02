# aiPHeed FI5 — final report (Objectives 1–4)

Every figure below comes from files written by `python -m app.fi5.pipeline all` on 2026-11-02 (tables in full:
[RESULTS.md](RESULTS.md), generated from `backend/data/fi5/out`). Method lock `dc8f1023e416c383…` was written
before the evaluation ran; the evaluated code matched the lock. After the run, only the explanation wording
(`explain.py`) and one post-hoc diagnostic function (`evaluate.label_noise_diagnostic`) were changed; neither
changes any prediction or metric.

## A. Executive completion summary

| Objective | Delivered and working | Research outcome |
|---|---|---|
| 1 NLP | XLM-RoBERTa zero-shot (Filipino + English) on 9,628 headlines; BERTopic (11 topics); bias-corrected FSSI per province-quarter and domain; news inside the five domains; features enter LightGBM | News adds **no measurable** forecasting skill (ablation Brier change 0.000–0.004) |
| 2 Forecasting | FIRI v2-independent target, five-domain features with release-date alignment, 1998+ history, one LightGBM per lead, walk-forward 2010–2026, all metrics, overfitting/permutation/geographic audits | **No lead is reliable.** Accuracy 0.53–0.60; the 75 % target is **not met**; furthest reliable lead: **none** |
| 3 Rankings | All 142 LGUs ranked from PSA poverty (SAE 2021; Lucena from PSA HUC table) and POPCEN 2024 density; independently reproduced (max diff 7e-15) | Ranking order is driven by vulnerability, because no province-level outcome exists to validate province forecasts |
| 4 Baselines | Persistence, PSA-only, NLP-only, logistic regression on identical origins | LightGBM does **not** beat persistence (accuracy) or logistic regression (Brier) at Leads 1–2 |

The system is complete as software (end-to-end pipeline, cached NLP, saved models, read-only API, 34 passing
tests). The research claim that LightGBM forecasts above-normal hunger reliably is **not supported** by the data.

## B. Research references and selected methodology

See [RESEARCH_EVIDENCE.md](RESEARCH_EVIDENCE.md): FAO FIES/PoU/dimensions, IPC, WFP HungerMap, FEWS NET, DOST-FNRI,
PSA, BSP, and 9 forecasting studies. 16 DOIs were verified on Crossref (`crossref_verification.json`). Selected
design: the simplest one the data allow, which is a direct experience-based outcome at the level it is measured,
five domains with news inside them, one regularised LightGBM per lead, and rolling-origin evaluation against
persistence.

## C. Food insecurity target and justification

* **Outcome:** SWS involuntary hunger ("experienced hunger and had nothing to eat, past 3 months"), Balance Luzon
  (the SWS area that contains CALABARZON), 1998-Q3 to 2026-Q3. This is the severe end of the FIES experience scale.
  It is not PoU, poverty or prices.
* **Label:** HIGH if the quarter's rate is above the mean of the preceding 20 quarters (≥ 8 readings), following
  the FEWS NET/GIEWS "worse than the five-year average" convention. There are 98 labelled quarters, 51 % of them
  HIGH. Quarters without a round are unlabelled, never LOW.
* **Continuous check:** the hunger level is forecast too (MAE vs persistence).
* **Not used as target:** DOST-FNRI FIES (≤ 3 provincial points), PoU (national, modelled), poverty/CPI/
  unemployment (drivers, not outcomes). No province-quarter food-insecurity observation exists.

## D. Historical data sources and coverage

`backend/data/fi5/raw/MANIFEST.csv` lists 20 files with sha256 hashes and origins. Release rules are in
`app/fi5/sources.py`.

| Series | Source | Level | Coverage used | Release rule |
|---|---|---|---|---|
| Hunger | SWS releases | Balance Luzon | 1998-Q3–2026-Q3 | published date |
| Food / rice / all-items CPI | PSA OpenSTAT | Region IV-A | 1994-01–2026-09 | +10 days after month |
| Palay production | PSA | Region IV-A | 1987–2026-Q3 | quarter + 45 d |
| Rainfall, Tmax | NASA POWER | 5 province centroids | 1981-01–2026-09 | month + 30 d |
| Typhoon tracks (≤ 200 km) | NOAA IBTrACS v04r01 | CALABARZON | 1884–2026-10 | real time |
| ENSO (ONI) | NOAA CPC | Niño 3.4 | 1950–2026-09 | season + 10 d |
| Unemployment | PSA LFS | Philippines | 2005-04–2026-08 (2005 definition only) | month + 45 d |
| Personal remittances | BSP via World Bank WDI | Philippines | 1990–2025 | 15 Feb next year |
| Poverty incidence | PSA | Region IV-A | 2006–2025 (methodology break 2015→2018) | Y+2, or documented date |
| GDELT DOC news volume | GDELT | Philippine sources | 2017-Q1–2026-Q3 | real time |
| Local news corpus | Google News RSS (collected Oct 2026) | geocoded province / region | 2021-01–2026-10 | quarter end |

BSP's own site returned HTTP 403 to automated download, so the WDI mirror of BSP data is used. Local news
before 2021 does not exist, so news features are missing for those quarters (LightGBM handles missing values).

## E. Five-domain feature architecture

32 features (`app/fi5/features.py`, registry in `sources.REGISTRY`):

* **Outcome history:** latest reading, its anomaly, its age.
* **Market:** food/rice CPI YoY, food minus all-items, food acceleration, palay YoY. News: GDELT shortage and
  agri-supply, FSSI-market, market-topic share.
* **Climate:** rainfall z, Tmax anomaly, storms this quarter / last 4 quarters, ONI. News: FSSI-climate,
  climate-topic share.
* **Employment:** unemployment rate and change. News: GDELT jobs, FSSI-employment, employment-topic share.
* **Remittances:** remittance YoY. News: FSSI-remittance, remittance-topic share.
* **Poverty:** poverty incidence. News: GDELT assistance, FSSI-poverty, poverty-topic share, hunger-report share.

There is no separate news group (tested in `test_five_domains_and_no_news_group`). Domain contribution was
measured by walk-forward ablation rather than fixed weights. Removing any one domain changed Brier by −0.031 to
+0.024 with no consistent sign. No domain gives a stable gain.

## F. NLP processing and FSSI results

* **Corpus:** 9,643 articles, 9,628 unique headlines, 2021-01-01 to 2026-10-14. 3,794 passed the EN/FIL relevance
  gate and were scored by `joeddav/xlm-roberta-large-xnli` (fp32, CPU, 20 threads). The hypothesis set hash is
  `aa356c2831ac`.
* **Relevance:** 1,147 headlines carry at least one domain, 143 of them multi-domain. By domain: market 513,
  climate 435, poverty 166, employment 114, remittance 83.
* **Evidence types:** risk factor 626, background 291, government response 202, actual hunger report 28. The
  hunger-report cut is 0.9, because lower bands were mostly programme news.
* **BERTopic:** fitted on 2021–22 headlines only and then frozen; 11 topics. Examples: typhoon, flooding,
  rice/farmers, inflation/prices, typhoon damage to agriculture, fishing livelihoods, ayuda/DSWD.
  Representative headlines for each topic are in `bertopic_topics.csv`.
* **FSSI bias correction:** each event is counted once, outlets are down-weighted by 1/√n, the score is a share of
  all collected events, and thin province cells are shrunk toward the region (k = 10). The model sees z-scores
  computed from earlier quarters only. Province cells average 20–38 events per quarter, with shrink weights
  0.60–0.76.
* **Thresholds:** 0.3 for domain relevance and 0.9 for hunger reports. Both were set by reading sampled headlines
  before any forecast result was seen.
* **Known limits:**
  * Headlines only (no article bodies).
  * The corpus was collected retrospectively, and its volume rose from 193 to 882 articles per quarter.
  * Zero-shot labels were not checked against a human-labelled set, because none exists.

## G. LightGBM performance (walk-forward, 62 evaluated quarters per lead, 28 HIGH / 34 LOW)

| Lead | Acc | Prec | Rec | F1 | AUC | Brier | BSS vs clim. |
|---|---|---|---|---|---|---|---|
| 1 | 0.532 | 0.483 | 0.500 | 0.491 | 0.483 | 0.309 | −0.170 |
| 2 | 0.548 | 0.500 | 0.357 | 0.417 | 0.540 | 0.287 | −0.078 |
| 3 | 0.597 | 0.571 | 0.429 | 0.490 | 0.579 | 0.264 | +0.015 |
| 4 | 0.565 | 0.514 | 0.679 | 0.585 | 0.529 | 0.292 | −0.079 |

Era breakdowns, confusion matrices and false-positive rates are in RESULTS.md. In 2021–2026, LightGBM accuracy is
0.35–0.60.

## H. Maximum reliable lead time

The reliability rules were fixed in the lock:
* accuracy ≥ 0.75;
* recall ≥ 0.50 and precision ≥ 0.50;
* AUC ≥ 0.70;
* Brier skill > 0;
* accuracy ≥ 0.60 in every era.

**No lead passes, so the furthest reliable lead is none.** Lead 1 fails 5 of the 6 checks.

## I. Overfitting, bias and generalisation

* **Overfitting:** in-sample accuracy is 0.87–0.93 against out-of-sample 0.53–0.60. The most-chosen
  configuration was the most constrained one (stumps). The model memorises noise.
* **Label permutation (20 shuffles):** out-of-sample AUC is 0.498 (lead 1) and 0.470 (lead 2). The harness does
  not leak, and the real model is no better than shuffled labels.
* **Root cause — label noise (post-hoc diagnostic):** 74 % of evaluated quarters (46/62) differ from the five-year
  average by less than the SWS margin of error (±4–6 pp). The HIGH/LOW label is mostly sampling noise. On the 16
  clear quarters, persistence scores 0.56–0.69 and LightGBM 0.38–0.56.
* **Temporal stability:** the worst era is 2021–2026, a regime shift in which hunger sat far above its history.
* **Geographic transfer** (trained on Balance Luzon, applied to the other SWS areas, lead 1):
  * Metro Manila: LightGBM 0.548 vs that area's persistence 0.661.
  * Visayas: 0.597 vs 0.710.
  * Mindanao: 0.532 vs 0.710.
  * Across leads 1–4, transfer is at best equal to each area's persistence (one exception: Visayas, lead 3, 0.629
    vs 0.581). The dynamics learned on Balance Luzon do not generalise.
* **Spurious association:** in the live forecast, the record-low 2025 poverty rate (4.2 %) pushes risk up. That
  coincidence comes from the high-hunger 2021–26 era and is a further sign that the model is not trustworthy.
* **Level forecast:** LightGBM MAE against persistence gives skill −0.07, +0.16, +0.06, −0.06 at leads 1–4. The
  modest gain at lead 2 is not matched at the other leads.

## J. Municipal and city rankings

* **Coverage:** all 142 LGUs (Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14) are in
  `backend/data/fi5/out/lgu_rankings.csv`.
* **Score:** priority = 100 × P(HIGH, lead 1) × vulnerability, where vulnerability = ½ poverty rank + ½ density
  rank.
* **Missing data:** none. Lucena is missing from SAE 2021 (it is an HUC), so it takes PSA's published 2021 City of
  Lucena value (10 %, rounded).
* **Top of the list:** Cavite City, Trece Martires, Tanza, General Trias, Taytay.
* **Provinces:** Cavite ranks first on population-weighted vulnerability.
* **Sensitivity:**
  * Spearman correlation with the equal-weight order: 0.80 for 0.7/0.3 weights, 0.77 for 0.3/0.7, about 0.5 for
    poverty or density alone.
  * 11–24 of the top-third LGUs change depending on the weights. The weights are a policy choice and should be set
    with DA.
* **Interpretation:** the forecast is regional, so every LGU shares one probability, and the order comes only from
  vulnerability. This is an estimated priority, not a municipal hunger measurement.

## K. Baseline comparison (same 62 origins per lead)

| Lead | LightGBM acc / Brier | Persistence | PSA-only | NLP-only | Logistic |
|---|---|---|---|---|---|
| 1 | 0.532 / 0.309 | **0.677** / 0.323 | 0.532 / 0.300 | 0.516 / 0.262 | 0.597 / **0.254** |
| 2 | 0.548 / 0.287 | 0.629 / 0.371 | 0.581 / 0.286 | 0.500 / 0.260 | **0.661 / 0.230** |
| 3 | 0.597 / 0.264 | **0.613** / 0.387 | 0.565 / 0.280 | 0.452 / 0.272 | 0.597 / 0.274 |
| 4 | 0.565 / 0.292 | 0.565 / 0.435 | 0.516 / 0.297 | 0.419 / 0.268 | 0.484 / 0.350 |

* **Does LightGBM offer a real improvement?** No.
* **Brier:** LightGBM beats persistence on Brier at leads 3–4, with intervals excluding 0. That happens only
  because persistence gives 0/1 forecasts that are heavily punished when wrong. Its accuracy at those leads is
  equal or lower.
* **Statistical tests:** no McNemar test favours LightGBM.

## L. Backend integration and modified files

* **New package:** `backend/app/fi5/`.
  * Modules: `sources`, `target`, `nlp`, `features`, `models`, `evaluate`, `rankings`, `explain`, `pipeline`,
    `report`.
* **New API:** `backend/app/api/v1/fi5.py`. Read-only routes under `/api/v1/fi5/`: `status`, `forecast`,
  `evaluation`, `baselines`, `provinces`, `lgus`, `nlp/fssi`, `nlp/topics`, `features`.
* **Modified:** `backend/app/api/router.py`, one router mount.
* **Data:** `backend/data/fi5/`.
  * `raw` + MANIFEST.
  * `nlp`: cached XLM-R scores, articles, topics, FSSI.
  * `models`: LightGBM text models.
  * `out`: lock, evaluation, predictions, forecasts, seal, rankings, verification.
* **Tests:** `backend/tests/unit/test_fi5.py`, 27 tests: target rule, as-of no-future-data checks, five-domain
  structure, metrics, FSSI bias properties, 142 LGUs, plain sentences, no FIRI imports, API.
* **Not changed:** the approved frontend, FIRI v2 and the served dashboard model. FI5 is not wired into the map.
* **Seal:** the forecasts for 2026-Q4 to 2027-Q3 (sha256 `350ffe4f…`) are the first untouched test, once SWS
  publishes those quarters.

## M. Reproduction commands (from `backend/`)

```bash
python -m app.fi5.pipeline all
```

```bash
python -m app.fi5.report
```

```bash
python -m pytest tests/unit/test_fi5.py -q
```

`all` runs acquire → nlp → lock → evaluate → issue → verify.

* **Cache:** XLM-R scoring is cached in `data/fi5/nlp/xlmr_scores.parquet`. A rerun reuses it; scoring from
  scratch takes about 1.5 h on 20 CPU threads.
* **Recomputed embeddings:** `embeddings.npy` is not committed and is recomputed in about 1 minute.
* **Live forecast:** `python -m app.fi5.pipeline issue --issue-quarter 2026-Q3` reproduces it, and the seal hash is
  identical across reruns.
* **GPU:** the Intel Arc iGPU was tried through PyTorch XPU in a separate venv (`C:\Users\admin\aipheed_fi5_xpu`).
  XLM-R large failed on real batches with Level Zero `OUT_OF_RESOURCES`, so all scoring ran on the CPU.

## N. Remaining unresolved requirements

1. **The 75 % accuracy target and a reliable lead are not met** under the locked rules. The data-backed cause is
   that the five-year-average HIGH/LOW label sits inside SWS sampling error in 74 % of quarters. Fixing that needs
   a different target or more data, for example a larger-sample or provincial survey, or a threshold above the
   margin of error defined with the adviser. It cannot be fixed by tuning against these windows.
2. **Validated province-level forecasts are impossible** with public data, because no province-quarter
   food-insecurity outcome exists. Provinces and LGUs get vulnerability-adjusted priority only.
3. **News adds no skill.** The corpus is headlines-only, 2021+, and retrospectively collected. A real-time
   collector and article bodies would be needed for a fair test.
4. **There is no human-labelled validation set** for the zero-shot classifier.
5. **The FAO "utilization" dimension is not covered** by any quarterly series.
6. **Development evidence only.** Pre-2021 and 2021–26 SWS quarters were used by earlier aiPHeed experiments. Only
   the sealed 2026-Q4+ forecasts are a clean test.
7. **The LGU weights** (½/½) need DA sign-off; the sensitivity analysis shows they matter.
