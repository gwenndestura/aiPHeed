# aiPHeed E148: quarterly survey-anchored forecasting system. Evidence report

**Date:** 2026-11-04. **Branch:** `pfi/e147-fnri-heatmap`, worktree `C:\Users\admin\aipheed_e145`, local only. **Production and dashboard:** not changed.

## Verdict

**E148 is implemented and is the strongest result this project has produced. It does not yet pass all release gates, so promotion is not requested.**

On the sealed 2021 round, which no model had seen, Lead 1 reached **accuracy 0.76** across 25 provinces, against 0.56 for persistence and 0.60 for always-LOW. It narrowly fails the locked reliability rule, news adds nothing, and the between-survey movement has no independent support yet.

| Objective | Status | Evidence |
|---|---|---|
| 1. News pipeline with demonstrable value | **Pipeline built; value not shown** | Q-GNB − Q-G +0.0025 Brier; Holm fails at every lead |
| 2. LightGBM forecast, Lead 1, 75 %, maximum lead | **75 % met on the untouched round; reliable lead 0** | 0.76 [0.57, 0.89], n = 25; misses R4 |
| 3. 142 LGU rankings | **Built on the candidate forecast** | Not promotable until Objective 2 passes |
| 4. Four baselines | **Done** | Section 6 |
| 5. Dashboard, ISO/IEC 25010, face validity | **Face validity done; rest not done** | Dashboard held back by this rule; the 50 DA evaluators' responses must be real |

**The sealed labels are now spent.** They were scored once. Any further model built after this point cannot call 2021 untouched.

## 1. Root causes of E145 and E146, and what changed

| Failure | Cause found | Correction | Result in E148 |
|---|---|---|---|
| Four provinces identical | The hierarchical anchor gave provinces zero own weight, and the level was flat within the region | Learn change from each province's own published survey | Forecasts 32.6 to 51.8 % |
| No HIGH in CALABARZON | Above-national class | FNRI's published cut-off, High ≥ 60 % | Quezon High in 2013 and 2019 |
| Nothing beat persistence | Predicted geography, not change | Target is change since the last survey | Brier −0.050; interval just includes 0 |
| No untouched test | All labels had been seen | 2021 HFIAS found on FNRI's Heat Map | First sealed test |
| Quarterly evaluation under 75 % | SWS is regional and noisy; a different target | Measured provincial outcomes as anchors; SWS as signal and check | 0.76 at surveyed quarters |
| News not significant | Thin attribution, one outlet | Added 3 outlets and 2 more years | **Not solved** (section 7) |

**My own errors, corrected:** I said the 2021 ENNS used only FIES and that HFIAS ended in 2019. FNRI's methodology shows HFIAS ran through 2021. E144's end-to-end "pass" used look-ahead 2013 estimates, and it does not stand as a clean result.

## 2. Labelled data

Full inventory and provenance: `docs/e147/DATA_INVENTORY.md`. The new source is DOST-FNRI's **Hunger and Malnutrition Heat Map**, with provincial any-level HFIAS for 2013, 2015, 2018, 2019 and 2021, Radimer/Cornell 2011, and official cut-offs. It matches earlier sources on all but 2 of 230 matched rows.

Your workbook's 2018 and 2019 "moderate-to-severe" column is HFIAS moderate only, so it cannot be used as printed.

## 3. Target

Food-insecure households (any-level HFIAS), learned as a continuous value. Class HIGH = **≥ 60 %, FNRI's "High" public-health significance**. Comparison of six candidates: `docs/e147/DATA_INVENTORY.md`, section 4.

**This needs your adviser's confirmation:** any-level includes mild insecurity, and 40 to 83 % of provinces are HIGH depending on the round.

## 4. How the quarterly system works

1. **Surveys train it.** Each measured outcome becomes rows for leads 1 to 8, with inputs as public at each issue date.
2. **LightGBM learns change** from the province's latest *published* survey, using the inputs now and accumulated since that survey (mixed-frequency aggregation).
3. **It runs every quarter,** because the inputs exist every quarter. No intermediate label is created.
4. **A new survey resets the anchor.**

Protocol: `docs/e148/PROTOCOL.md`. Lead 1 in Q4 2026 targets Q1 2027, using only values published before the issue date. Research basis: `docs/e145/LITERATURE_EVIDENCE.csv`; closest precedents are Martini 2022, Lentz 2019, Kopp 2026 and Ghysels-style mixed-frequency aggregation.

## 5. Lead-time results, sealed 2021 test

Q-G (selected on development rows). 25 provinces, 10 HIGH. Persistence: accuracy 0.56, Brier 0.27. Always-LOW 0.60.

| Lead | Target | Trained on | Accuracy | Precision | Recall | F1 | AUC | Brier | Failed checks |
|---|---|---|---|---|---|---|---|---|---|
| **1** | 2021-Q3 | 2015, 2018, 2019 | **0.76** | 0.625 | 1.00 | 0.769 | 0.740 | 0.217 | **R4 only** |
| 2 | 2021-Q3 | Same | 0.76 | 0.625 | 1.00 | 0.769 | 0.740 | 0.217 | R4 only |
| 3 | 2021-Q3 | 2015, 2018 | 0.68 | 0.583 | 0.70 | 0.636 | 0.773 | 0.186 | R1, R6 |
| 4 | 2021-Q3 | Same | 0.64 | 0.538 | 0.70 | 0.609 | 0.747 | 0.188 | R1 |
| 5 | 2021-Q3 | Same | 0.64 | 0.538 | 0.70 | 0.609 | 0.747 | 0.187 | R1 |
| 6 | 2021-Q3 | Same | 0.68 | 0.583 | 0.70 | 0.636 | 0.740 | 0.190 | R1, R6 |
| 7 | 2021-Q3 | 2015 | 0.56 | 0.476 | 1.00 | 0.645 | 0.733 | 0.273 | R1, R3, R4, R5, R6 |
| 8 | 2021-Q3 | 2015 | 0.56 | 0.476 | 1.00 | 0.645 | 0.747 | 0.272 | R1, R3, R4, R5, R6 |

**Lead 1 confusion:** TP 10, FP 6, TN 9, FN 0. False-negative rate 0, false-alarm rate 0.40. Accuracy interval [0.57, 0.89].

**Maximum reliable lead under the locked rule: 0 quarters.** Lead 1 misses only one check: Brier − persistence = −0.050 [−0.116, +0.005].

**Where accuracy falls.** Accuracy stays at or above 75 % to lead 2, then drops below it. The drop coincides with the model losing the latest survey round from training, not only with horizon. So lead 2 is the **furthest lead meeting 75 %**, but it is not a "reliable lead" under the rule.

**Development rows (2018, 2019, n = 47, already seen):** Lead 1 accuracy 0.745 against always-HIGH 0.66. Beats persistence on Brier, −0.025 [−0.039, −0.011].

## 6. Baselines, Lead 1 on 2021

| Model | Accuracy | Recall | AUC | Brier |
|---|---|---|---|---|
| **Q-G, LightGBM** | **0.76** | 1.00 | 0.740 | 0.217 |
| Drift (anchor + mean change) | 0.76 | 0.70 | 0.793 | **0.185** |
| Q-noSWS | 0.72 | 1.00 | 0.733 | 0.223 |
| Q-GNB (with corrected news) | 0.72 | 0.90 | 0.747 | 0.219 |
| Q-GN (with raw news) | 0.72 | 0.90 | 0.740 | 0.222 |
| Q-frozen (no quarterly updating) | 0.68 | 1.00 | 0.660 | 0.254 |
| B2 PSA-only logistic | 0.68 | 0.90 | 0.660 | 0.242 |
| B4 Logistic, all inputs | 0.60 | 0.20 | 0.733 | 0.273 |
| News-only LightGBM | 0.60 | 0.90 | 0.720 | 0.322 |
| B1 Naive persistence | 0.56 | 1.00 | 0.793 | 0.267 |
| B3 NLP-only logistic | 0.52 | 0.90 | 0.693 | 0.337 |
| E147 (survey-to-survey) | 0.68 | 1.00 | 0.773 | 0.239 |

**Read this honestly:**
* A simple drift rule ties on accuracy, has a **better Brier** (Q-G − drift +0.031, interval includes 0), and persistence has a higher AUC. LightGBM's advantage on 2021 is high-risk recall (1.00 against 0.70), not overall probability quality.
* **Quarterly updating helped on this test:** Q-G − Q-frozen −0.037 [−0.067, −0.010]. On development rows it was slightly the other way (+0.007 [+0.001, +0.015]), so this finding is not stable yet.
* **The SWS signal helped slightly:** Q-G − Q-noSWS −0.006 [−0.014, −0.0002].

## 7. News ablation

| Comparison on 2021 (Brier) | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| Q-GNB − Q-G | +0.0025 [−0.019, +0.022] | +0.0107 [−0.003, +0.024] | +0.0086 [−0.008, +0.022] | +0.0047 [−0.009, +0.016] |
| Q-GN − Q-G | +0.0059 [−0.010, +0.022] | +0.0156 [+0.001, +0.031] | +0.0048 [−0.001, +0.011] | +0.0044 [−0.001, +0.010] |

Holm: no lead passes. **News did not improve the forecast.** On development rows it was also worse. The placebo gave no support either: the real news gain is positive, so there is no gain to defend.

**Corpus.** 55,047 articles: Rappler 53,335, VERA Files 1,019, NewsBytes 503, PCIJ 190. So adding outlets barely diversified it.

**Why it failed, in order of evidence:**
1. **Attribution is weak.** Only **9.1 %** of gated province-article links name the province in the title or excerpt, since the rest match somewhere in the article body. Stress rates barely differ: 5.1 % named, 4.6 % not.
2. **Single-outlet dependence:** 97 %.
3. **Sentiment accuracy is unmeasured** on Filipino-English news, because no labelled sample is allowed.
4. **Sample size.** Even a real effect of this size would need several times more rows.

Bias correction itself worked: volume correlation fell from up to 0.67 (raw) to at most 0.23.

## 8. Five provincial forecasts

Issued from Q4 2026. Food-insecure households, HFIAS scale.

| Province | Last survey | Measured | Q1 2027 forecast | 90 % interval | P(High) | Band |
|---|---|---|---|---|---|---|
| Quezon | 2019 | 61.9 | **51.8** | 33.7 to 69.4 | 0.23 | Medium |
| Rizal | 2019 | 56.6 | **50.2** | 32.3 to 68.1 | 0.19 | Medium |
| Batangas | 2021 | 56.9 | **48.3** | 30.7 to 66.4 | 0.15 | Medium |
| Cavite | 2021 | 50.2 | **43.6** | 26.8 to 62.1 | 0.07 | Medium |
| Laguna | 2018 | 39.3 | **32.6** | 18.6 to 50.5 | 0.01 | Low |

* **They are distinct and evidence-based,** and each traces to the province's own survey.
* **Only Laguna is clearly separate.** Quezon, Rizal and Batangas overlap heavily.
* **On 2021:** forecasts tracked measured values within Luzon (Spearman 0.74, n = 14), but persistence's was 0.64.
* **By province measured on 2021:** Batangas 56.9 (P 0.11, correct) and Cavite 50.2 (P 0.11, correct). Laguna, Quezon and Rizal had no 2021 provincial row. Five-province performance cannot be established from this.
* **Weak point:** in the same test, Batangas and Cavite got nearly identical estimates (46.5 and 46.7) while they measured 6.7 points apart.

## 9. Quarterly behaviour, the central question

The system now produces a number per province per quarter (`data/e148/out/issue/calabarzon_quarterly_table.csv`, 2017-Q2 to 2026-Q4). **That movement is not yet supported:**

| Check | Result | Pass? |
|---|---|---|
| Independent SWS check: Q-noSWS change vs measured SWS change, 87 area-quarters | ρ −0.004 [−0.23, +0.21] | **No** |
| With SWS inputs (not independent) | ρ +0.10 [−0.15, +0.34] | No |
| Size of quarter-to-quarter movement | 0.5 to 1.2 points on average | Very small |
| 2027 forecast Q1 to Q4 | Same value in each province to 0.1 point | Essentially flat |
| Provinces moving together | Mean pair correlation 0.86 | Mostly shared |

**Fixed wording from the protocol:** "the quarterly movement between surveys has no independent support yet."

**So what is established:** a province-level risk estimate refreshed each quarter, tested where measured. **What is not:** that the quarter-to-quarter changes carry real information. Quarterly updating improved the 2021 survey-quarter forecast, but the quarter-level track doesn't yet follow measured hunger.

## 10. All five trigger groups: real inputs, unequal use

Exact TreeSHAP on the fitted model. No share was forced.

| Group | Inputs | Share of influence | Used? |
|---|---|---|---|
| Survey history | Anchor, gap, regression to mean, Radimer 2011 | 61.8 % | Yes |
| Poverty and vulnerability | Province | 20.5 % | Yes |
| SWS area signal | Area | 9.3 % | Yes |
| Climate stress | Province | 3.9 % | Yes: cyclones and production since last survey only. Soil moisture, rain, ONI no splits |
| OFW remittances | **National** | 3.3 % | Yes: year-on-year only |
| Market and prices | Province, annual, stale after 2018 | 1.3 % | Yes |
| Employment | **National** | **0.0 %** | **In the model, but no split** |

**Employment is a real input, and the model did not use it.** I won't display a contribution it doesn't have. Remittance and employment history has no provincial variation before 2021, which is the likely cause. The live dashboard must show this honestly.

## 11. LGU prioritisation

`data/e148/out/issue/lgu_priority_2027-Q1.csv`, 142 LGUs. Priority = province P(High) × vulnerability; vulnerability = 0.6 poverty percentile + 0.4 density percentile (PSA SAE 2021, POPCEN 2024). Top: Plaridel, Pagbilao, Candelaria (Quezon).

Province differences now shape the ranking, unlike E146. It is a vulnerability-based prioritisation, not a municipal measurement. **Check the weights:** your brief says "specified" weights, and 0.6/0.4 is the owner decision recorded in the C-B6 work.

## 12. Face validity

| Evidence | Measured | Model | Assessment |
|---|---|---|---|
| ENNS pooled 2018, 2019, 2021, CALABARZON any-level | 51.5 % regional | Five-province mean of measured values 53.0 | Consistent |
| 2021 Batangas, Cavite, HFIAS | 56.9, 50.2 (Medium) | Both LOW class, P 0.11 | Agrees |
| 2019 FIES Quezon, Rizal; 2021 FIES Batangas, Cavite | Below national | Medium or Low | Direction agrees |
| NNS 2023 FIES, CALABARZON | 19.1 % (lowest region) | HFIAS scale, not comparable | Direction only |

HFIAS and FIES are different scales. The 2019 pairs correlate at ρ 0.82 [0.60, 0.92], passing the pre-set rule for a bridge, but no bridged value is used here. These anchors do not validate any province-quarter.

## 13. Generalization and robustness

* **Leave-one-region-out change correlation, lead 1:** 0.42.
* **20 % masked inputs:** Brier 0.209 against 0.203 on development rows.
* **Change skill on 2021:** ρ 0.36 [0.02, 0.64].
* **Anchor lag 8:** not computable on development rows, because 2015 is not yet released at those issue dates. The strict release rule leaves no training data.
* **Rain anomalies run high in 2021,** consistent with La Niña, but with outliers up to 12 SD. Provincial CPI is stale after 2018.

## 14. Reproducibility

| Item | Evidence |
|---|---|
| Locks | `data/e147/out/PROTOCOL_LOCK.json`, `data/e148/out/PROTOCOL_LOCK.json`, before results |
| Sealed labels | SHA-256 `f15a1977…`; never printed before scoring |
| Predictions hashed before labels opened | E147 `a1893c05…`; E148 `2d2c808f…`; committed in `7d78d8e5` before scoring |
| Seeds | 147, 148 |
| Deviations | None for E148 |

**Disclosed:** I saw E148's development results and the failed SWS check before opening 2021, but the lock prevented any change. E147's 2021 result was scored at the same time.

## 15. Objective-by-objective acceptance

| Requirement | Status |
|---|---|
| Actual food-insecurity target | **PASS** |
| LightGBM principal learner | **PASS** |
| Lead 1 = next calendar quarter, as-of inputs | **PASS** |
| ≥ 75 % on untouched rows | **PASS, with scope:** 0.76, n = 25, surveyed quarter, interval reaches 0.57 |
| Beats persistence | **NOT PROVEN:** −0.050 [−0.116, +0.005] |
| Maximum reliable lead determined | **PASS (process); result 0** |
| All four baselines | **PASS** |
| Five differentiated forecasts | **PARTIAL:** distinct, but only Laguna clearly separate |
| Quarterly estimates between surveys | **PRODUCED; movement unsupported** |
| All five groups as real inputs | **PARTIAL:** employment has no effect |
| XLM-RoBERTa, BERTopic, FSSI pipeline | **BUILT;** accuracy on local news unvalidated |
| News adds value | **FAIL** |
| 142 LGU rankings | **BUILT;** waits on validated forecast |
| Dashboard and ISO/IEC 25010 | **NOT DONE,** correctly held back |
| NNS face validity | **DONE,** direction only |

**Promotion is not requested.**

## 16. Exact remaining blockers

| Blocker | Missing evidence | Source | Minimum needed | Action |
|---|---|---|---|---|
| Beat persistence with confidence | More unseen provincial rows; detectable gap 0.087, observed 0.050 | Next FNRI provincial round | About **3 times the rows**, roughly 50 more provinces | Pre-register now; score when published. 2021's 12 city rows lack inputs |
| Validate quarterly movement | Repeated provincial measurement within a year | Provincial phone or panel survey; FAO DIEM is only regional | At least **2 consecutive quarters** across the five provinces, more for power | Commission or partner; no public source found |
| Independent quarterly support | Series that tracks measured hunger | Better province-quarter inputs | Pass the locked SWS check | Fix the three inputs below |
| News value | Full-text attribution and more outlets | Full article text; Inquirer, Philstar, Manila Bulletin, GMA where terms allow | Attribution far above 9.1 %; no dominant outlet above about 50 % | Confirm source rules, then re-test on new rounds |
| NLP accuracy | Local labelled sample | Hand-labelled Filipino-English articles | About **200 articles** (the kit you ruled out) | **Your decision:** lift that rule, or report it as unvalidated |
| Employment and remittances by province | History before 2021 | PSA LFS microdata; FIES 2015, 2018, 2021 public-use files | At least the 3 FIES rounds | PSA microdata request, against your rule on requests |
| Market prices | Provincial CPI 2019 to 2020 | PSA OpenSTAT | One table | I can acquire this |
| Stronger spatial check | CBMS 2024 FIES | PSA, LGUs | CALABARZON LGUs | Team access or request |
| Dashboard and ISO evaluation | Real DA evaluators | DA Region IV-A | 50 respondents | After gates pass |

## 17. Recommendation

1. **Adopt E148 as the thesis's candidate methodology.** State its results with their limits.
2. **Report in Chapter IV:** "On an untouched FNRI round, the LightGBM system reached 0.76 accuracy at Lead 1 with no missed high-risk province, against 0.56 for persistence. The improvement in probability quality was not statistically conclusive. News did not improve the forecast. The furthest lead meeting 75 % was Lead 2, and no lead met all pre-registered reliability checks."
3. **Do not put the quarterly movement on the dashboard as a validated signal.** Show the province estimate, its interval, and when each province was last surveyed.
4. **Stop model searches now.** The untouched labels are spent, and more models on them would prove nothing.
5. **Seal the Q1 2027 forecast** and score it when new data arrive.

## Files

| Item | Path |
|---|---|
| Protocols | `docs/e147/PROTOCOL.md`, `docs/e148/PROTOCOL.md` |
| Data inventory | `docs/e147/DATA_INVENTORY.md` |
| Failure analysis, literature | `docs/e145/FAILURE_ANALYSIS.md`, `docs/e145/LITERATURE_EVIDENCE.csv` |
| Code | `backend/app/e147/`, `backend/app/e148/` |
| Results | `backend/data/e148/out/results.json`, `dev_results.json`, `explain.json` |
| Predictions | `oof_2021.csv`, `oof_dev.csv`, `quarterly_series_lead1.csv` |
| Forecasts | `issue/five_province_forecasts.csv`, `issue/calabarzon_quarterly_table.csv`, `issue/lgu_priority_2027-Q1.csv` |
