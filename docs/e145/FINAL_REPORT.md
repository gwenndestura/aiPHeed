# aiPHeed: research-driven methodology redesign. Final report

**Date:** 2026-11-04. **Branch:** `pfi/e145-provincial-news-panel`, worktree `C:\Users\admin\aipheed_e145`, local only. **Production and dashboard:** unchanged.

## Verdict

**The methodology does not pass all 20 gates. It is not a validated forecasting system.** 11 gates pass, 7 pass only in part and 2 fail (G2, G7).

| Objective | Result |
|---|---|
| 1. News improves the model | **Not achieved.** The full pipeline was built and tested on 78 provinces. News did not measurably improve the forecast at any of leads 1 to 4 |
| 2. Actual food-insecurity target, per province | **Partly.** The target is measured HFIAS. But the five CALABARZON forecasts are nearly identical |
| 3. At least one quarter ahead | **Timing met, skill not shown.** Lead 1 is genuine, but it does not beat persistence |
| 4. Maximum reliable lead | **Determined: 0 quarters** under the locked rule. Lead 1 fails because it does not beat persistence |
| 5. LightGBM at 75 % or higher | **Met only on measured survey rows** (0.903, n = 62). Quarterly SWS hunger reaches 0.633 |

Three findings matter most:

1. **Accuracy clears 75 %, but persistence does too.** Repeating the previous survey scores 0.806 on the same rows.
2. **The class "above national" has never been measured in CALABARZON.** That is 0 of 13 HFIAS rows and 0 of 4 FIES rows, so high-risk recall cannot be tested in the study area.
3. **The quarterly forecast is almost flat and cannot separate provinces.** For 2027-Q1, four provinces receive 40.4 % and Quezon 40.5 %, with a 90 % interval of about 22 to 62 %.

All HFIAS rows were seen by earlier experiments, so everything below is **development evidence**. No result here is an untouched test.

---

## 1. International literature review

The evidence database lists 36 sources, 22 of them directly on food-insecurity forecasting or monitoring. **How far each was read:** two in full text (Balashankar, Bertetti), and the rest from abstracts, summaries or metadata, as marked in the `evidence_read` column. Papers marked "metadata" support a citation, not a detailed claim, and should be read in full before being cited in the thesis.

**A. Sparse labels.** The reviewed studies mostly do not have exact, frequent labels either:

* *Consensus labels.* IPC and FEWS NET phases are analyst classifications, not direct measurements (Balashankar 2023, Westerveld 2021, Busker 2024). Evaluation is often against the same system's later assessment (Bertetti 2024).
* *Borrowing across places.* HungerMap trains where surveys exist and estimates where they do not (Martini 2022).
* *Round to round.* Models predict the next survey round (Lentz 2019, Zhou 2021).
* *Gap filling.* Gaussian processes fill spatio-temporal survey gaps (Kopp 2026), which still needs repeated rounds.
* *Validation.* None of these proves accuracy where no measurement exists. They validate where the outcome was measured or classified, which is the standard adopted here.

**B. News.** Balashankar 2023 is the strongest evidence: 3-month RMSE of 0.149 traditional, 0.099 news and 0.082 hybrid, on about 1,160 districts. It reports no persistence baseline, works less well where coverage is thin, and its headline gain varies between versions (32 %, 40 %, 46 %). HungerGist reports news-only gains. Mueller and Rauh (2018, 2022) separate persistent risk from new risk.

**C. Hybrid systems.** Hybrids beat either part alone in the district-scale setting. No reviewed study shows a gain at a scale close to aiPHeed's.

**D. Early warning.** Yemen rules work best at 5 months (Penson 2024). Soil-moisture signals looked strong in retrospective cases, but the paper states it did not test out-of-sample accuracy (Krishnamurthy 2022).

**E. Horizon.** Skill often concentrates in short leads (Busker 2024, about 3 months). A no-change rule reaches about 76 % against FEWS NET's 78 % (Bertetti 2024). Backer and Billing (2021) report about 84 % but sharply lower accuracy at high severity. Comparing accuracy alone is therefore not enough.

## 2. Research evidence database

`docs/e145/LITERATURE_EVIDENCE.csv`, with every requested field. Where a field could not be verified it says `n/r`. Earlier review: `docs/research/AIPHEED_RELATED_LITERATURE_REVIEW.md`.

## 3 and 4. Failure analysis and why earlier experiments failed

`docs/e145/FAILURE_ANALYSIS.md`. Root causes in brief:

| Cause | Evidence |
|---|---|
| No province-quarter measurement exists | 13 of 275 possible CALABARZON province-quarters measured with HFIAS (4.7 %) |
| HIGH never measured in CALABARZON | 0 of 13 HFIAS, 0 of 4 FIES |
| Few independent time points | 4 rounds, 3 origins, 12 area-round cells |
| Far less data than the literature | 203 rows against thousands of district-periods |
| "Where" mistaken for "when" | E140 AUC 0.96 falls to 0.70 within Luzon |
| News tested where it could not work | Provincial news had never met a provincial outcome until E145 |
| Lead defined inconsistently | CH1 "Lead 1" was the issue quarter |
| Test data reused | About 29 attempts on the same 62 SWS quarters |
| Proxy targets | CH1 and FIRI learn price pressure or a constructed index |

**Correction to E144.** Its end-to-end check fed 2013 provincial estimates trained on later rounds into the link, which is look-ahead. Its locked result stands on record but is not treated as clean. See E146 below.

## 5 and 6. Proposed methodology and its justification

**Survey-anchored, mixed-frequency LightGBM forecast:**

    logit(prevalence, province p, quarter T) = alpha + gamma x logit(SWS area hunger, T) + delta x province position + province shock

| Part | Source | Literature basis |
|---|---|---|
| Area forecast | LightGBM on four SWS areas | Pooling units; Martini, Foini |
| Province position | E143 C4: cross-fitted LightGBM + hierarchical anchor | Round to round (Lentz, Zhou); area-level shrinkage (Fay and Herriot) |
| Province shock | LightGBM on real survey rows, may choose no shock | Keeps unmeasured quarters out of training |
| News | XLM-RoBERTa, BERTopic, bias-corrected FSSI, within-province change | Balashankar; Mueller and Rauh; Laurer |
| Timing | Only values published before the issue date | Giannone et al. |

**Why this differs from what failed.** It targets measured food insecurity, not prices. It separates shared time movement from lasting province position. It tests news on provinces for the first time. It never trains on estimated labels, because an estimated label has no province-specific movement to learn.

**What the data then decided.** The shock model chose "no shock" in every fit, so soil moisture and news had no effect in E146.

## 7. Target and label construction

| Measure | Role | Coverage |
|---|---|---|
| HFIAS moderate-or-severe (FNRI 2013, 2015, ENNS 2018, 2019) | **Training and test target** | 78 provinces at most per round; 203 rows; 30-day recall |
| SWS involuntary hunger | Quarterly time signal, tested separately | 4 areas, regional |
| FIES (ENNS 2019, 2021; NNS 2023) | Agreement only, never pooled | 12-month recall |
| PSA Family Income and Expenditure Survey 2023 | Vulnerability context only | No food-insecurity item |
| IPC, Food Consumption Score, rCSI, HHS | Not available for these provinces in the sources reviewed | |

**Instrument facts verified from the decks.** The 2021 ENNS uses FIES (pages 51 to 53), which corrects earlier records. The HFIAS series appears to end in 2019, so a future HFIAS confirmation round may never come. The owner workbook's 2018 and 2019 "moderate-to-severe" column is HFIAS moderate only.

**Classes.** E145 uses above the same round's national reference (owner decision D-1). E146 uses above 42.8 %, the pooled national ENNS value, because a future national level is unknown.

## 8. Data and feature architecture

| Group | Features | Update |
|---|---|---|
| Poverty, density | `p_poverty`, `p_subsistence`, `p_poverty_gap`, `p_density` | Survey and census years |
| Prices | `m_food_cpi_yoy`, `m_rice_cpi_yoy`, threshold | Annual in the provincial file, to 2018 |
| Climate, production | Rain, typhoons, palay and corn, fisheries, soil moisture (new) | Quarterly or monthly |
| News (new) | `nb_fssi`, `nb_attention`, `nb_fssi_delta`, 6 topic shares, raw arm | Trailing 4 quarters |
| Survey history | Province and region anchors | Survey rounds |
| Area | Latest SWS, anomaly, age, nowcast, ONI, unemployment, remittances | Quarterly |

**Dataset versions (SHA-256, first 16 characters):** articles `98391479c50f920f`; news features `d53ca88deb41a49d`; soil `925273c490d575fd`; E145 predictions `b3e682aae9249933`; E146 predictions `8014345c4cce67b7`; E144 Stage A `2a71c5384b7c2ea6`.

## 9. News integration and incremental contribution

**Corpus.** Rappler public archive, 2012 to April 2019 for the test, with the same exact phrases for every province. 47,117 unique articles on 78 provinces, 155 survey reports removed, and 4,478 unique food-security texts scored.

**Bias correction.** Correlation of the index with article volume, against the raw count:

| Round | Corrected FSSI | Raw count |
|---|---|---|
| 2013 | −0.05 | 0.28 |
| 2015 | 0.17 | 0.65 |
| 2018 | −0.19 | 0.13 |
| 2019 | 0.09 | 0.67 |

The first version of the index had a volume artefact, found and fixed before any outcome was read. See the protocol.

**E145, 125 rows, region-cluster intervals. Negative means news helps.**

| Comparison | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| FULL − C4 (Brier) | −0.0074 [−0.022, +0.009] | +0.0022 [−0.011, +0.015] | −0.0003 [−0.015, +0.015] | +0.0047 [−0.009, +0.018] |
| GNB − G | −0.0034 [−0.012, +0.005] | +0.0035 [−0.007, +0.013] | +0.0083 [−0.022, +0.040] | +0.0040 [−0.002, +0.010] |
| GN − G (raw) | +0.0031 [−0.005, +0.011] | +0.0027 [−0.005, +0.011] | +0.0037 [−0.021, +0.029] | −0.0094 [−0.029, +0.008] |

* **Holm test across leads 1 to 4:** no lead passes.
* **Placebo:** wrong-province news matched or beat real news in 23 % of draws. The rule required 5 % or less.
* **By coverage, lead 1:** low +0.016, mid −0.029, high −0.009. Not significance-tested, and this does not support a claim.
* **Accuracy and recall at lead 1:** FULL and C4 have the same confusion matrix, so news changed no decisive call there.
* **Longer leads:** FULL was significantly *worse* at lead 5.

**Wording, as pre-registered:** "News was tested on measured provincial food insecurity and did not measurably improve the forecast."

**Is this a data limit or a true absence?** It cannot be told apart yet. The L1 point estimate favours news, but detecting a gain that size needs about 8.8 times the evidence.

**E144 at area level:** no gain at any horizon (Holm p from 0.20 to 0.55).

**Unmeasured.** Sentiment accuracy on Filipino-English news has no local check, because no labelled sample is permitted. One outlet supplies the news. Attribution is a body mention, which is weak. Rizal (93 articles) and Quezon (208) have thin coverage because of their anchored phrases.

## 10. Model and baseline comparison

**E145, lead 1. Class: above the round's national reference. 125 rows, 62 decisive (40 HIGH).**

| Arm | Accuracy | Precision | Recall | F1 | AUC | Brier | ECE |
|---|---|---|---|---|---|---|---|
| FULL (gov + news + surveys) | 0.903 | 0.947 | 0.900 | 0.923 | 0.959 | **0.183** | 0.043 |
| C4 (gov + surveys) | 0.903 | 0.947 | 0.900 | 0.923 | 0.984 | 0.190 | 0.098 |
| GNB (gov + corrected news) | 0.903 | 0.947 | 0.900 | 0.923 | 0.963 | 0.189 | 0.046 |
| G (gov only) | 0.887 | 0.946 | 0.875 | 0.909 | 0.958 | 0.192 | 0.057 |
| GN (gov + raw news) | 0.855 | 0.897 | 0.875 | 0.886 | 0.950 | 0.195 | 0.062 |
| N (news only, LightGBM) | 0.565 | 0.623 | 0.825 | 0.710 | 0.573 | 0.244 | 0.050 |
| B1 Persistence | 0.806 | 0.850 | 0.850 | 0.850 | 0.856 | 0.207 | 0.131 |
| Region's previous level | 0.806 | 0.868 | 0.825 | 0.846 | 0.926 | 0.190 | 0.063 |
| B2 PSA-only logistic | 0.790 | 0.865 | 0.800 | 0.831 | 0.908 | 0.206 | 0.066 |
| B3 NLP-only logistic | 0.597 | 0.703 | 0.650 | 0.675 | 0.649 | 0.339 | 0.284 |
| B4 Logistic, all | 0.790 | 0.886 | 0.775 | 0.827 | 0.885 | 0.248 | 0.189 |
| Always HIGH | 0.645 | 0.645 | 1.000 | 0.784 | n/a | 0.250 | 0.069 |

FULL minus persistence on Brier: −0.024 [−0.055, +0.006], so not proven better. It beats the region's previous level by only 0.007 on Brier at lead 1, and that comparison was not tested.

**E146, lead 1. Class: above 42.8 %. 125 rows, 95 decisive (80 HIGH).**

| Arm | Accuracy | Recall | False-alarm rate | AUC | Brier |
|---|---|---|---|---|---|
| E2E-clean (selected) | 0.853 | 1.000 | **0.933** | 0.940 | 0.134 |
| QS, QS-nosoil, QS-N | Identical: no shock chosen | | | | |
| C4-link (no time signal) | 0.842 | 0.988 | 0.933 | 0.897 | 0.138 |
| Persistence | 0.863 | 0.963 | 0.667 | 0.770 | 0.148 |
| PSA-only logistic | 0.884 | 0.975 | 0.600 | 0.856 | **0.130** |
| Logistic, all | 0.895 | 0.963 | 0.467 | 0.877 | 0.145 |
| Always HIGH | 0.842 | 1.000 | 1.000 | n/a | n/a |

**E146's 0.853 is not meaningful evidence of skill.** It barely beats always saying HIGH and flags 14 of 15 low rows. PSA-only logistic has the best Brier here, so **LightGBM is not the best learner on this class.**

**Soil moisture:** no effect, since the shock was never selected.

## 11. Walk-forward evaluation

Expanding-window rolling origins, as-of data: O1 (train 2013, test 2015, 78 rows), O2 (train 2013, 2015, test 2018, 22), O3 (train all earlier, test 2019, 25).

| Experiment | Period | n per lead | Note |
|---|---|---|---|
| E145 | 2015, 2018, 2019 rounds | 125 (62 decisive) | Lock: `data/e145/out/PROTOCOL_LOCK.json` |
| E146 | Same | 125 (95 decisive) | Lock: `data/e146/out/PROTOCOL_LOCK.json` |
| E144 Stage A | Issues 2022-Q1 onward; secondary 2014-Q1 onward | 60 at h = 1; 172 secondary | Quarterly, area level |

Each lock has one logged fix-only deviation, made after a crash and before any metric was read. E145 also has a pre-lock revision of the index.

## 12. Accuracy and classification metrics

**Quarterly SWS hunger, the only true quarterly test (E144, h = 1, 2022 onward, n = 60):** accuracy 0.633, precision 0.885, recall 0.548, F1 0.676, AUC 0.718, Brier 0.241, ECE 0.246. Always-HIGH reaches 0.70 and naive last-class 0.70. **This fails 75 %.**

## 13. Maximum reliable lead time

Arm FULL, E145 class. Target quarter is the survey's reference quarter (Q3 of 2015, 2018 or 2019). Persistence stays at accuracy 0.806, Brier 0.207.

| Lead | Accuracy | Precision | Recall | F1 | AUC | Brier | ECE | Reliability |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.903 | 0.947 | 0.900 | 0.923 | 0.959 | 0.183 | 0.043 | Fails R4 |
| 2 | 0.839 | 0.941 | 0.800 | 0.865 | 0.945 | 0.202 | 0.080 | Fails R4 |
| 3 | 0.887 | 0.923 | 0.900 | 0.911 | 0.933 | 0.211 | 0.122 | Fails R4, R5 |
| 4 | 0.871 | 0.944 | 0.850 | 0.895 | 0.938 | 0.201 | 0.062 | Fails R4 |
| 5 | 0.855 | 0.970 | 0.800 | 0.877 | 0.892 | 0.224 | 0.108 | Fails R4, R5 |
| 6 | 0.871 | 0.971 | 0.825 | 0.892 | 0.928 | 0.213 | 0.086 | Fails R4 |
| 7 | 0.887 | 0.971 | 0.850 | 0.907 | 0.948 | 0.192 | 0.058 | Fails R4 |
| 8 | 0.871 | 1.000 | 0.800 | 0.889 | 0.968 | 0.195 | 0.092 | Fails R4 |

* **Maximum reliable lead: 0 quarters** for FULL, C4, GNB and G, and for E146. **First failure: Lead 1.**
* **Does news extend it?** No.
* **Sensitivity, not the locked rule:** dropping R4 alone, FULL would reach lead 2 and fail lead 3 on calibration.
* **Why performance barely falls with lead:** the signal is lasting provincial differences, not forecasting of change. Performance at lead 8 resembles lead 1 for that reason, so this is not evidence of two-year foresight.
* **Change skill:** predicted and measured change between rounds correlate at ρ 0.55 [0.41, 0.68] at lead 1. That is measured relative to persistence and mixes regression to the mean, so it does not prove time skill.

**Time signal (E146, lead 1).** E2E-clean minus C4-link is −0.0041 on Brier. The interval is [−0.0102, +0.0010] by region and [−0.0083, −0.0003] by cell, and the locked claim needs both below 0. **Not claimed.** The clean link coefficient across origins is 0.23, 0.02 and 0.14: unstable.

## 14. Province-level performance

**E145 lead 1, the 8 CALABARZON test rows:**

| Province | Round | Measured status | C4 P | FULL P | Persistence P |
|---|---|---|---|---|---|
| Batangas | 2015 | LOWER | 0.416 | 0.516 (wrong side) | 0.236 |
| Cavite | 2015 | LOWER | 0.189 | 0.212 | 0.192 |
| Laguna | 2015 | LOWER | 0.140 | 0.268 | 0.218 |
| Quezon | 2015 | Not distinguishable | 0.361 | 0.506 | 0.446 |
| Rizal | 2015 | LOWER | 0.242 | 0.290 | 0.310 |
| Laguna | 2018 | LOWER | 0.080 | 0.059 | 0.066 |
| Quezon | 2019 | Not distinguishable | 0.559 | 0.327 | 0.286 |
| Rizal | 2019 | Not distinguishable | 0.020 | 0.038 | 0.074 |

* **C4 on decisive rows:** 5 of 5 correct, exact 95 % interval [0.48, 1.00]. Always-LOW also gets 5 of 5, and news moved Batangas to the wrong side.
* **Recall in CALABARZON:** undefined, because no HIGH case exists.
* **Degradation by province:** cannot be established with 1 to 3 test rows each.
* **By period, C4 accuracy:** 2015 0.917, 2018 1.000, 2019 0.789. Persistence: 0.917, 0.684, 0.789.

**Five independent forecasts: not achieved.** Live C4 gives P 0.072 for Batangas, Cavite, Laguna and Rizal and 0.074 for Quezon. This is not a bug. C4 attributes all persistent deviation to the region (σ_G² = σ_A²), and the LightGBM level is −0.26 for all five. The older C2 form does differ: Batangas 0.064, Cavite 0.124, Laguna 0.075, Quezon 0.165, Rizal 0.191, but it was not selected by this protocol. Its Rizal above Quezon ordering contradicts their measured ordering, so C2 is not an easy fix.

## 15. Overfitting and generalization

* **Train versus test Brier:** C4 0.176 to 0.199 against 0.190. FULL 0.165 to 0.200 against 0.183. G 0.129 to 0.166 against 0.192, which is a real gap for the pure structural model.
* **Missing data, 20 % of inputs masked:** C4 +0.011, FULL +0.007. Tolerable.
* **Geography:** earlier work found skill mostly separates island groups (E140 AUC 0.96 against 0.70 within Luzon). Not retested here.
* **Sampling ceiling:** even an oracle's expected accuracy over all rows is 0.90, because half of the rows (50.4 %) are not decisive.

## 16. NNS face validity

**Coverage verified.** NNS 2023 is regional: CALABARZON 19.1 % (CI 17.0 to 21.1), lowest region, national 31.4 %. The national 2018-2019 deck has **no** CALABARZON figure. 2019 evidence is provincial. Sources and pages: `backend/data/e145/calabarzon_face_validity_anchors.csv`.

| Check | Measured | Forecast direction | Agreement |
|---|---|---|---|
| FIES 2023, region | Below national | All five LOW | Yes |
| FIES 2021, Batangas 29.7, Cavite 31.7 (national 33.4) | Below; Cavite's interval includes national | LOW | Yes |
| FIES 2019, Quezon 32.2, Rizal 38.4 (national 44.2) | Below | LOW | Yes |
| HFIAS 2019, Quezon 44.0, Rizal 39.1 (national 46.9) | Not distinguishable | LOW | Compatible |

**Direction agrees, but this is weak evidence:** "always LOW" agrees equally. These figures do not establish quarterly provincial truth, and the values were seen before this work. The 2019 HFIAS and FIES pairs across 20 areas correlate at ρ 0.82 [0.60, 0.92], which passes the pre-set bridge rule. FIES was not used to update the forecast.

**PSA 2023 context (not validation).** Share of population in the national bottom 30 % correlates 0.82 [0.53, 0.95] with 2023 regional FIES and 0.72 [0.56, 0.82] with latest HFIAS. Quezon stands out at 52 %, against 14 to 24 % elsewhere. This is the best current evidence that Quezon differs, and the forecast does not reflect it.

## 17. Municipal and city rankings

`backend/app/e145/lgu.py` and `data/e146/out/issue/lgu_priority_2027-Q1.csv` (142 LGUs). Priority = province P × vulnerability, where vulnerability = 0.6 × poverty percentile + 0.4 × density percentile (PSA SAE 2021, POPCEN 2024).

**Limits.** Because province P is nearly identical, the ranking is effectively vulnerability alone. It is a prioritisation, not a municipal measurement. E143 files used 0.5/0.5, while this uses the owner's recorded 0.6/0.4 from the C-B6 work, so the two must not be mixed.

## 18. Reproducibility evidence

| Item | Evidence |
|---|---|
| Protocols locked before results | SHA-256 of protocol, code and thresholds in each `PROTOCOL_LOCK.json` |
| Same rows as E143 | C4 reproduced to 1.1e-16 |
| Independent recomputation | Accuracy, AUC and Brier recomputed from saved predictions with plain numpy and sklearn, without project code: all match |
| Seeds | E145 145, E146 146; topic model 145 |
| Tests | `test_e145.py` 6 of 6 pass. `test_e144.py` 4 of 6: two remaining tests need its issue and registry step, which was deliberately not run |
| Sealed forecast | `data/e146/out/issue/sealed_prediction_2026-10-01.json`, sha256 `dc747ad5883e3641` (first 16) |

"Independently verified" here means recomputed from outputs. No third party has replicated it.

## 19. Remaining limitations, with exact blockers

| Blocker | Measured size | What would change it |
|---|---|---|
| No province-quarter label | 13 of 275 (4.7 %) | A repeated provincial survey |
| No HIGH in CALABARZON | 0 of 17 province-rounds | A different class definition, which is a thesis decision |
| Provinces inseparable within region | C4 P 0.072 to 0.074 | More rounds per province; or microdata |
| News power | SE 0.0078; detectable 0.022; observed 0.0074; 8.8 × evidence needed | More rounds or outlets |
| Beating persistence | Detectable 0.044; observed 0.024; 3.2 × evidence needed | More rounds |
| Time signal | 12 cells; clean γ 0.02 to 0.23 | More rounds with SWS overlap |
| Quarterly 75 % | SWS accuracy 0.633; earlier simulation put the ceiling for one change label near 0.58 to 0.64 | Not resolved by modelling |
| Provincial inputs stale | Provincial CPI to 2018 in this file; poverty rounds to 2015 in this feature set | Update the inputs |
| News current to April 2019 only | Later years not collected, as news did not pass | Collect if news is pursued |

**Other limits.** The quarterly table's "estimated" rows are never scored. Quarter-to-quarter change is shared across Balance Luzon, of which CALABARZON is about a third of the population. Survey reference quarters are approximate.

**Evidence that would most change these conclusions: CBMS 2024.** It applies FIES at barangay and city level, which would finally test where risk is highest, including within provinces. It is one window, so it cannot test change over time. FNRI household microdata would also help. The owner's rule against data requests excludes both unless the team already holds them.

## 20. Acceptance matrix

| Gate | Requirement | Status | Evidence |
|---|---|---|---|
| G1 | Target is food insecurity | **PASS** | Measured HFIAS; forbidden targets not used |
| G2 | Five independent provincial forecasts | **FAIL** | Four identical, Quezon +0.002 |
| G3 | LightGBM main model | **PASS** | C4, E2E-clean. Logistic has better Brier on E146's class |
| G4 | XLM-RoBERTa and BERTopic | **PARTIAL** | Implemented; accuracy on local news unmeasured; topic quality not assessed |
| G5 | Bias-corrected FSSI, province-quarter features | **PARTIAL** | Volume dependence reduced; 78 provinces; trailing 4 quarters; to April 2019 only |
| G6 | News and government combined | **PASS** | Arms GNB, FULL, QS-N |
| G7 | News adds demonstrable value | **FAIL** | No lead passes Holm; placebo fails |
| G8 | Lead 1 genuinely one quarter ahead | **PASS** | Issue start of Q2 for target Q3; tested |
| G9 | At least 75 % out of sample | **PARTIAL** | 0.903 on seen survey rows (persistence 0.806); quarterly SWS 0.633; no untouched test |
| G10 | Precision, recall, F1, AUC evaluated | **PASS** | Sections 10, 12, 13 |
| G11 | Expanding walk-forward | **PASS** | Three provincial origins, 48 quarterly issues |
| G12 | Maximum reliable lead determined | **PASS (process); result 0** | Section 13. The result misses "at least Lead 1" |
| G13 | Naive persistence baseline | **PASS** | Compared; not beaten with confidence |
| G14 | PSA-only baseline | **PASS** | Compared |
| G15 | NLP-only baseline | **PASS** | Compared |
| G16 | Logistic baseline | **PASS** | Compared |
| G17 | Municipal and city rankings | **PARTIAL** | 142 LGUs; effectively vulnerability alone |
| G18 | NNS face validity | **PARTIAL** | Direction agrees; always-LOW agrees too; no CALABARZON 2019 regional figure exists |
| G19 | Generalization and overfitting | **PARTIAL** | Checked; provinces and island groups not shown to generalize |
| G20 | Reproducible and independently verified | **PARTIAL** | Locks and recomputation; no untouched test; no third-party replication |

**11 pass, 7 partial, 2 fail.** By the mission's own rule, this methodology is **not complete**.

## Recommendations

1. **Do not deploy this as a validated forecast.** Do not change the live system on this evidence.
2. **State in the thesis exactly what was shown:** "On measured survey rounds, a LightGBM model classified provinces against the national level with 0.90 accuracy, not proven better than the previous survey. News was tested at provincial scale and did not measurably improve the forecast. No forecast horizon met the pre-registered reliability rule."
3. **Decide with your adviser whether "HIGH" should mean above national.** That definition cannot produce a positive case in CALABARZON. A within-region definition could, but it would answer a different question and must be fixed before any new test.
4. **If quarterly numbers go on a dashboard, label them.** Measured, estimated and forecast rows must stay distinct, with the 22 to 62 % interval shown.
5. **Score the sealed forecast** when SWS and any later FNRI data appear, and pursue CBMS if access can be obtained.
6. **Stop model searches on these rows.** More models on the same 125 rows only add multiple-testing risk.

## Files

| Item | Path |
|---|---|
| Protocols | `docs/e145/PROTOCOL.md`, `docs/e146/PROTOCOL.md`, `docs/e144/PROTOCOL.md` |
| Failure analysis, literature | `docs/e145/FAILURE_ANALYSIS.md`, `docs/e145/LITERATURE_EVIDENCE.csv` |
| Code | `backend/app/e145/`, `backend/app/e146/` |
| Results | `backend/data/e145/out/results.json`, `backend/data/e146/out/results.json`, `backend/data/e144/out/results.json` |
| Blockers | `backend/data/e146/out/blockers.json` |
| Quarterly table | `backend/data/e146/out/issue/quarterly_table.csv` |
