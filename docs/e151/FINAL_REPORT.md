# E151 final report: news, quarterly forecasting and validation

**Verdict: the release gates fail, so nothing goes to production or the dashboard.** E147 to E150 are unchanged. This is research output on branch `pfi/e151-news-quarterly`.

**Three findings:**

1. **The quarterly forecast has real skill at SWS area level.** One quarter ahead on 2021 to 2026, it clearly beats repeating the last reading.
2. **The provincial forecast clearly beats an old survey, most of all when that survey is old,** but accuracy is 0.72 against the 0.75 target and all of this is retrospective.
3. **Corrected news did not add measurable information** one quarter ahead, at area or province level.

Evidence labels: **R** retrospective, rows read by earlier work. **C** confirmation, settings fixed on earlier data, but not strictly blind. **S** sealed, not scored yet. **E** exploratory.

## Release gates (required model GNT, Lead 1)

Target: HFIAS moderate plus severe. Both the pool and the 2021 round must pass (deviation D2).

| Gate | Pool (n = 72, 25 HIGH) | 2021 round (n = 25, 4 HIGH) |
|---|---|---|
| R1 accuracy at least 0.75 | **0.722 FAIL** | 0.84 pass |
| R2 AUC at least 0.70 | 0.855 pass | 0.929 pass |
| R3 both recalls at least 0.50 | HIGH 0.76, LOW 0.70 pass | HIGH 0.50, LOW 0.90 pass (HIGH is 2 of 4) |
| R4 Brier below persistence | -0.075 [-0.135, -0.024] pass | -0.163 [-0.241, -0.089] pass |
| R5 above majority rule | 0.722 vs 0.653 pass | **0.84 vs 0.84 FAIL (tie)** |
| R6 coverage 0.80 to 0.98 | 0.958 pass | 0.96 pass |
| R7 slope interval includes 1 | **[0.51, 0.98] FAIL** | [0.27, 1.04] pass |
| R8 a province pair separated | **0 of 10 FAIL** (live forecast) | |
| R9 news passes Q1 | **FAIL** | |

**Maximum reliable lead under these gates: 0 quarters,** because Lead 1 fails. This is the gates' result, not a statement that quarterly updating has no value; see sections 8 and 9.

## 1. Dataset audit

| Data | Geography | Period | Frequency | Role | Reliability |
|---|---|---|---|---|---|
| HFIAS (FNRI) | Province | 2013, 2015, 2018, 2019, 2021 | Rounds | Direct measure, target | 2015 checked against the report for 76 provinces, no differences. Margins imputed for 2013, approximated at 3 points for 2021. **Each province appears in one ENNS round only** |
| SWS hunger | 4 areas | Quarterly | Quarterly | Direct measure, one item. Never a provincial label | 80 confirmation rows |
| FIES (PSA) | National, regional | 2019, 2021, 2023 | Rounds | Context only, never pooled | No provincial values held |
| Market | Province | Monthly CPI | Monthly | Determinant | Province level |
| Climate | Province; ONI national | Quarterly | Quarterly | Determinant | The 10-30 audit recorded rainfall as absent; a rainfall anomaly input is in use, and **this was not re-audited here** |
| Employment | **National**; regional annual from 2021 | Quarterly | Quarterly | Determinant | Cannot separate provinces |
| OFW remittances | **National** | Quarterly | Quarterly | Determinant | Cannot separate provinces |
| Poverty, density | Province | PSA rounds | Rounds | Vulnerability | Made relative to the all-province mean, removing E150's double count |
| News | Mixed levels, section 2 | 2013 to 2026 | Daily | Proxy | Rappler is 60.9 % of eligible stories |

**Discarded earlier and now used:** about 10,000 national-query articles and 10,000 multi-publisher titles. **Survey weights:** microdata are not held, so survey-weight-aware estimation was not possible.

## 2. News failure analysis and corrected pipeline

| Failure found | Evidence | Fix | Result |
|---|---|---|---|
| Wrong scorer sign (my bug) | Hunger hypothesis ranked fact-checks highest | Scores negated once (D1) | Fixed |
| One article credited to many provinces | E150: 4.13 provinces per article | One geographic level; national news stays national | Fixed |
| Weak filter | 17,747 of 140,737 articles pass the gate; 18 of 80 sampled were off-topic | Filter added | **Only partly fixed: 7 of 23 caught on fresh data** |
| Raw NLI not comparable across questions | Displacement took 34 % of top events, climate 0.9 % | Each reader standardised on pre-2015 stories | Fixed |
| Zero-shot unreliable alone | 20 % agreement, 35 % after standardising | Mean of XLM-RoBERTa, embedding similarity and seed phrases | 69 % on fresh data |
| Saturated sentiment | Problem mean 0.72, plan 0.83 | Standardised | 80 % problem agreement |
| Duplicates | 696 exact, 0.9 % near-duplicates | Removed | Not the main problem |
| Time alignment and leakage | E150 12-month windows | 3-month windows before the issue date; topics fitted on earlier stories only | Unit tested |
| One publisher | Rappler 60.9 % | Outlet centring | **Remains; removing it raises MSE to 0.183 from 0.178** |
| Filipino-English | Filipino-dominant 1.5 % of gated articles | Multilingual models | Not separately measured |
| Province sparsity | Median 2 to 4 stories per quarter in CALABARZON; Rizal covered in 28 of 56 quarters | Province, area, regional and national streams; shrinkage | **Remains** |

**Label check, fresh sample, rule fixed first (n = 80):** top event 69 % (55 of 80, Wilson 58 to 78 %), 84 % on relevant stories (48 of 57), current-problem 80 %. Files: `docs/e151/label_check_reader*.csv`, `backend/data/e151/out/label_check*`. **The reader is the system's author, not an independent annotator.**

**Pipeline counts:** 141,513 loaded; 127 survey reports removed; 140,737 kept; 43 sites; 17,121 unique texts scored; 16,974 stories; 13,347 eligible after filters.

**Against the two papers.** Balashankar et al. 2023 (read in full through PMC): monthly relative frequency, training-only Granger-type screen and temporal evaluation are followed. Frame-semantic parsing is not; seed phrases are simpler, and they had about 11.2M articles and about 1,160 districts. van Wanrooij et al. 2024: **only the abstract and search excerpts could be read,** because it is paywalled, so its detail here follows the mission brief.

## 3. BERTopic interpretation and features

* 14 fits, each on stories published before its origin; later stories are only assigned.
* Latest fit: 29 topics, 30.4 % outliers, 16,852 stories. Readable themes include typhoons, inflation and fuel, OFWs, rice and NFA, floods and evacuees, hunger and malnutrition, African swine fever, 4Ps, El Nino.
* **Removed by keyword rule at every fit: 42 of 257 topic rows,** for example flood-control corruption, Filipino cuisine, police killings of farmers, fact-checks, presidential politics. The rule was written from the last fit's keyword list and uses no outcome.
* Features: event scores, topic shares against a 36-month base, net stress and its change, hunger, intensity, outlet diversity, emerging topics, and monthly series with 3-month rolling means (`news_monthly.csv`). Lags 0, 3 and 6 months.
* Development chose national events, lag 0, with screening. **Topic features were not selected,** and dropping them did not change the result.

**Geography (mission section 2C):** on development rows, province-level attribution was not tested against SWS, because SWS is area level. Median MSE by level was close (area 0.242, national 0.242, pooled 0.242, area + national 0.238).

## 4. News-only, government-only and combined (SWS, Lead 1, C)

80 rows, 20 quarters, 4 areas, 2021-Q1 to 2026-Q3. Settings fixed on rows through 2020.

| Model | MSE | Direction right | AUC of a rise |
|---|---|---|---|
| Persistence | 0.266 | 0.49 | |
| History only | 0.247 | 0.70 | 0.83 |
| Ridge, all inputs | 0.518 | 0.59 | 0.56 |
| News + history | 0.268 | 0.70 | 0.83 |
| **Government + history** | **0.173** | **0.75** | **0.84** |
| Government + overall news | 0.171 | 0.76 | 0.84 |
| GNT, required | 0.179 | 0.73 | 0.84 |

* **Primary test:** GNT - GOV +0.0055 [-0.007, +0.019], Diebold-Mariano p = 0.41. 66 % of 200 placebos did as well. **News fails.**
* **GNT - persistence** -0.087 [-0.148, -0.032]. **GOV - history** -0.074 [-0.115, -0.037].
* **Development rows differed:** GNT - GOV -0.019 [-0.046, -0.002]. The gain did not hold on later rows.
* **Much of the rise detection is mean reversion:** history alone reaches AUC 0.83.
* **Deterioration (16 events):** recall and precision GNT 0.50, 0.50; GOV 0.44, 0.47; history 0.38, 0.50. Too few events to separate them.

**E, cannot overturn the result:** news lagged 3 months MSE 0.168 against 0.173 with no news. At Lead 4, GNT - GOV -0.015 [-0.031, -0.001]. Overall news at Leads 3 and 4 is below GOV with intervals under 0. Many comparisons were made, so some may be chance. **These are hypotheses for the sealed forecasts, not findings.**

**Ablation:** removing any one news group leaves MSE between 0.173 and 0.178.

## 5. Scoring methodology and what a percentage means

**Formula.** m = shared level + province level + shrunk own deviation + LightGBM adjustment. Score = 100 / (1 + e^-m). **HIGH when score >= 50, LOW below,** as the panel approved. These are system classes, not FAO or FNRI categories.

**What changed.** The target moved from any-level to moderate plus severe by the owner's decision (D4). **Nothing is scaled, shifted or capped.** E150's poverty double count is removed.

**What an aiPHeed percentage means:** a survey-anchored **risk score**, 0 to 100, on the scale of HFIAS moderate-or-severe, built from past surveys and inputs available at the issue date.

**What it does not mean:** that this share of households was measured as food insecure; a FIES or SDG 2.1.2 figure; a causal statement; a measurement between surveys.

**Prevalence test: not passed.** Pool slope interval [0.51, 0.98] excludes 1, mean error interval [+0.02, +0.23] logit excludes 0. So **it may not be called estimated prevalence.**

**Why any-level was not kept:** on any-level the required model says HIGH on 98.6 % of rows, accuracy 0.819, LOW recall 0.07, AUC 0.77. On moderate-or-severe it says HIGH on 45.8 % against 34.7 % actual, LOW recall 0.70, AUC 0.855. Any-level did pass the prevalence test, so this is a real trade-off. **The choice was made before any model result and any-level cannot replace it afterwards.**

**Open:** whether the panel's 50 was meant for this measure. I found no official source for 50 on it. **This needs the adviser.**

## 6. Calibration and validation

**Calibration, nested in time.** The rule chose linear (selection error on 2019: none 0.423, linear 0.379, isotonic 0.438, region pooling 0.386).

| On 2021 | Mean error (logit) | Error (points) | LOW recall | HIGH recall |
|---|---|---|---|---|
| None | -0.01 | 6.5 | 0.90 | 0.50 |
| **Linear (chosen)** | -0.20 | 7.8 | 0.95 | 0.25 |
| Isotonic | -0.26 | 8.8 | 1.00 | 0.00 |
| Region pooling | -0.10 | 7.6 | 0.86 | 0.50 |

**The chosen calibrator did worse on 2021, on one round, so forecasts here stay uncalibrated.** This cannot show that calibration works.

| Form | Evidence | Result |
|---|---|---|
| A direct | Surveys, R | Section 8 |
| B temporal | SWS changes, C | Direction 0.73 to 0.75; beats persistence |
| B temporal, provinces | Change in score vs survey, R | Spearman 0.52, direction 0.74. Partly level, since surveys are years apart |
| C construct | News vs named inputs | Market vs food CPI 0.39; remittance news vs remittances 0.50; employment news vs unemployment 0.26. **Climate news vs cyclones -0.10, none** |
| D contextual | Regional forecast vs FIES 2023 | Spearman 0.42 on 12 matched regions; different instrument and years |
| Instrument compatibility | HFIAS vs SWS changes | n = 9, Spearman 0.27, same direction 56 %. **Weak support for carrying SWS movement to provinces** |
| E predictive | Sealed | **Not scored yet** |
| F uncertainty | Coverage 0.958 | Honest on average but wide. **Does not widen with staleness:** half-width 0.91 at 3 to 4 years, 0.79 at 6 years; fitted growth per quarter is 0 at the live fit |

**Supported:** quarterly skill at SWS area level; better than repeating an old survey, retrospectively.
**Unproven:** provincial quarterly movement; news value; prevalence reading; blind accuracy.

## 7. Leakage-free quarterly implementation

Issue date is the first day of the quarter before the target. Only values published earlier enter. Topics are fitted on earlier stories, standardising on pre-2015 stories, Granger screening on training rows. Survey labels are never interpolated. Tests: `backend/tests/unit/test_e151.py`.

**Disclosed:** `prov.py` had two bugs fixed after its first scored output: a placebo compared two different Brier definitions, and age bins had to match the real survey gaps. Neither changes a model forecast. All rounds were read by earlier work.

## 8. LightGBM and baselines (provinces, Lead 1, R)

| Model | Accuracy | Balanced | HIGH recall | LOW recall | AUC | Brier | Error (pts) | Slope | Coverage |
|---|---|---|---|---|---|---|---|---|---|
| **GNT, required** | **0.722** | 0.731 | 0.76 | 0.70 | 0.855 | 0.172 | 8.05 | 0.79 | 0.96 |
| GOV | 0.736 | 0.742 | 0.76 | 0.72 | 0.857 | 0.172 | 8.00 | 0.78 | 0.96 |
| GN | 0.722 | 0.731 | 0.76 | 0.70 | 0.859 | 0.171 | 7.99 | 0.77 | 0.96 |
| NEWS | 0.667 | 0.689 | 0.76 | 0.62 | 0.831 | 0.184 | 9.28 | 0.75 | 0.92 |
| ANCHOR | 0.639 | 0.714 | 0.96 | 0.47 | 0.855 | 0.208 | 9.36 | 0.94 | |
| MIDAS | 0.681 | 0.755 | 1.00 | 0.51 | 0.799 | 0.254 | 11.43 | 0.52 | 0.68 |
| Persistence | 0.625 | 0.703 | 0.96 | 0.45 | 0.827 | 0.247 | 11.16 | 0.71 | 0.82 |
| LR | 0.611 | 0.665 | 0.84 | 0.49 | 0.803 | 0.342 | | | |
| State-space | 0.569 | 0.670 | 1.00 | 0.34 | 0.842 | 0.243 | 11.17 | 0.84 | 0.85 |
| PSA only | 0.556 | 0.650 | 0.96 | 0.34 | 0.762 | 0.263 | | | |
| Fay-Herriot | 0.542 | 0.649 | 1.00 | 0.30 | 0.851 | 0.324 | 11.44 | 0.93 | 0.35 |

Always-LOW accuracy is 0.653. **GNT confusion matrix:** TP 19, FP 14, TN 33, FN 6.

* **GNT - persistence** -0.075 [-0.135, -0.024]. **GNT - ANCHOR** -0.035 [-0.069, -0.008].
* **GNT - GOV** +0.0005 [-0.002, +0.003]. Real news Brier (soft) 0.1375, shuffled mean 0.1367; 87 % of 30 placebos did as well. **News adds nothing here.**
* **Province-sentence upgrade:** with minus without +0.0003 [-0.001, +0.002]. Accuracy 0.722 vs 0.708. No measurable gain.
* **Delayed-label models** did not beat LightGBM on Brier. Fay-Herriot's intervals are far too narrow (coverage 0.35).

**By round, GNT:** 2018 0.636, 2019 0.68, 2021 0.84. In 2019 persistence is better (0.76). **In 2021 the 0.84 equals always-LOW.**

**By survey age (the purpose of this study):**

| Age of last survey | n | Error GNT | Error old survey | Accuracy GNT | Accuracy old survey | Brier GNT | Brier old survey |
|---|---|---|---|---|---|---|---|
| 3 to 4 years | 47 | 8.9 | 9.9 | 0.66 | 0.68 | 0.163 | 0.191 |
| 6 years | 25 | **6.5** | **13.6** | **0.84** | **0.52** | **0.090** | **0.253** |

**This is the strongest support for the thesis purpose, with limits:** the 6-year row is one round, it includes the COVID period, and that round has been read before.

**Longer leads:** L2 0.722, L4 0.75, L8 0.56 (below persistence 0.64). **L4's 0.75 is not a pass,** because those rows share the Lead 1 weaknesses and the anchor drives most of it.

**SHAP, share of mean absolute adjustment:** news 32 %, market 29 %, climate 21 %, poverty 17 %, remittance 0.3 %, h2 0.3 %, employment 0.0 %. **Employment and remittances are inputs but contribute nearly nothing,** and the quarterly SWS signal barely reaches the province model. News's 32 % shows use, not value: the placebo shows no gain.

## 9. Provincial forecast and uncertainty (issue 2026-10-01, target 2027-Q1, S)

| Province | Latest survey | Score | 90 % range | Class |
|---|---|---|---|---|
| Batangas | 39.9 (2021) | 25.8 | 15.1 to 40.5 | LOW |
| Cavite | 35.5 (2021) | 32.8 | 19.9 to 48.9 | LOW |
| Laguna | 26.2 (2018) | 28.7 | 17.1 to 44.1 | LOW |
| Quezon | 44.0 (2019) | 30.8 | 18.5 to 46.6 | LOW |
| Rizal | 39.1 (2019) | 35.4 | 21.8 to 51.7 | LOW |

Sealed: `backend/data/e151/out/issue/sealed_forecast_2027-Q1.json`, sha256 `b397c40f...`. SWS areas: `backend/data/e151/out/sealed_sws_2026-Q4.json`, sha256 `1a1c34bf...`.

**Weaknesses:**

* **0 of 10 province pairs are separated.** The ranges overlap heavily.
* **The model does not keep Quezon highest.** Measured order is Quezon, Batangas, Rizal, Cavite, Laguna; forecast order is Rizal, Cavite, Quezon, Laguna, Batangas. Batangas is 14 points below its survey and Quezon 13: about 8 to 9 of those points come from the anchor, which carries the low shared level after 2021 and shrinks own surveys, and the rest from the LightGBM adjustment. **These province differences should not be presented as real.**
* **Scores do not change from L1 to L4 at this issue date,** so the live output has no distinct longer-lead forecast.
* **Movement:** the same target moves 2.7 points on average between consecutive issue quarters (median 1.6). That is a change in the forecast, not a measured change, and it is unvalidated at province level.
* All 5 historical test rows in CALABARZON were correctly LOW, but so would always-LOW be.

## 10. LGU methodology and validation (research only)

**The precondition is not met:** the mission asks for rankings only after the provincial model is valid. These are produced to show the method and **should not be used for allocation.**

Priority = province P(HIGH) x vulnerability; vulnerability is 0.6 poverty percentile + 0.4 density percentile. **Those weights are not validated.** 142 LGUs, 135 distinct scores.

* **Rank uncertainty is large:** mean 90 % rank range 69 places. No LGU is above 90 % likely to be in the top 20; 51 are between 10 % and 90 %.
* **Weights:** Spearman with the base 0.99 at 0.5/0.5 and 0.7/0.3, 0.79 at poverty only, 0.67 at density only. Top-20 overlap 17, 17, 11, 14.
* **Province scores vary little within a province** (range up to 0.045), because P(HIGH) is near zero for all five.
* **No municipal food-insecurity measurement is held,** so it cannot be validated.

## 11. Objective matrix

Objectives are as recorded in the E150 matrix and should be checked against Chapter I's exact wording. **The 75 % is from the current mission; an earlier owner instruction says Chapter I sets no threshold. The adviser should confirm it.**

| Objective | Status | Evidence | Missing |
|---|---|---|---|
| 1. XLM-RoBERTa, BERTopic, news features | **Partial** | Pipeline built and checked, 69 % fresh agreement. XLM-RoBERTa alone was inadequate | News adds no measured value; independent labels |
| 2. LightGBM, Lead 1, 75 %, max lead | **Partial** | Beats persistence (R), 0.722, both recalls above 0.5 | 75 %; slope; blind test; max lead 0 under gates |
| 3. 142 LGU rankings | **Partial, not validated** | Produced with uncertainty and sensitivity | Valid provincial model; municipal outcome |
| 4. Baselines | **Achieved** | Persistence, PSA-only, news-only, logistic, plus always-LOW, Fay-Herriot, state-space, mixed-frequency | None |
| 5. Dashboard, ISO/IEC 25010, evaluators | **Not achieved in E151** | Held back by gates | Passing gates; 50 DA evaluators |

| Mission requirement | Status |
|---|---|
| Five groups as real inputs | **Partial:** all are inputs; employment and remittances contribute nearly nothing and are national |
| News genuinely useful | **Not achieved** |
| Credible one-quarter-ahead provincial forecast | **Partial:** beats old surveys retrospectively; no blind proof; provinces not separated |
| No leakage, no fabrication, no forced results | **Achieved** with disclosed limits; tested by unit tests and the design |
| Survey-equivalent prevalence | **Not supported** |

## 12. Reproducing

Protocol and deviations: `docs/e151/PROTOCOL.md`. Lock: `backend/data/e151/out/PROTOCOL_LOCK.json`. Results: `backend/data/e151/out/{gates.json, prov_results.json, prov_results_insecure.json, sws_results.json, sws_ablation.json, validation.json, label_audit.json}`.

```bash
cd backend
PYTHONPATH=. python -m app.e151.sws confirm
PYTHONPATH=. python -m app.e151.prov run
PYTHONPATH=. python -m app.e151.gates
```

Raw text and scoring outputs under `backend/data/e151/raw/` are not committed.

## What can honestly be said in the thesis

> "A LightGBM forecast using government inputs improved on repeating the last reading at SWS area level, one quarter ahead, on 2021 to 2026. At province level it improved on the last survey in retrospective tests, most clearly when that survey was six years old, with accuracy 0.72 on moderate-or-severe HFIAS at the 50 line, below the 0.75 target. Corrected news features did not add measurable information. The score is a risk score, not a prevalence estimate. Prospective validation of sealed forecasts is under way."

**The next independent evidence** is SWS at area level as it is published, and any new FNRI round. **No further model search on these rows adds evidence.**
