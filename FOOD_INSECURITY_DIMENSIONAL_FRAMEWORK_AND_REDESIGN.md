# aiPHeed: food-insecurity dimensional framework and redesign (E71)

**Date:** 2026-10-20 · **Branch:** `e71-food-insecurity-dimensions` (from `e70-objectives-completion` @ ce338e7) · **Experiment:** `aipheed-backend-aligned/experiments/E71_Food_Insecurity_Dimensions/`

**Rules fixed before computation.** The framework, indicators, normalisation, threshold, validation tests and forecast rules were frozen in `PROTOCOL.md` (sha `52cd8a12…`, commit 08ab805) before any E71 label, score or forecast was computed. Forecasts were sealed (commit c3daa19) before any evaluation label was read.

---

## Summary

| Question | Answer |
|---|---|
| Does T43 measure food insecurity? | **No.** It equals provincial food-price pressure on all 155 evaluated rows (E70). It measures one access mechanism, not food insecurity. |
| Was a food-insecurity target that does not collapse into prices built? | **Yes.** FIR71 has three observed dimensions (access, availability, stability). Utilization is explicitly *not observed*. Vulnerability is a separate layer, and the outcome is kept out of the index. FIR71 equals the price condition on only 48 of 90 rows; most HIGH rows are driven by availability (26) or stability (17), not access (6). |
| Does FIR71 correspond to measured food insecurity? | **No evidence that it does.** Against SWS regional hunger: ρ = −0.21 [−0.68, +0.35] over 17 quarters. Against PSA provincial subsistence incidence: ρ = −0.40 (2023) and −0.87 (2022 vs 2021). The contributing factors that can be measured do not track the outcomes that are measured. |
| 80% Lead-2? | **Not reached.** Best: DIMFUSE 29/45 = 0.644 (balanced 0.649; HIGH recall 0.864). The Objective 2 LightGBM gets 22/45 = 0.489. Even a higher figure would be proxy-prediction accuracy on reused quarters, not food-insecurity accuracy. |
| Can genuine food-insecurity accuracy be established with the available data? | **No.** No provincial or municipal food-insecurity outcome exists in repeated observations. The one repeated outcome (SWS) is regional, and in 2025–26 it moved against every observable contributing factor. |
| Production | Unchanged. No backend or frontend change in E71, and no served value changed. Nothing merged, pushed or deployed. |

---

## 1. Conceptual framework

### 1.1 Definitions

- **Food security.** "Food security exists when all people, at all times, have physical and economic access to sufficient, safe and nutritious food that meets their dietary needs and food preferences for an active and healthy life" (World Food Summit, FAO 1996).
- **The four dimensions** (FAO 2006):
  - **availability:** supply through production, stocks and trade;
  - **access:** economic and physical means to obtain food;
  - **utilization:** diet, nutrition, water, sanitation and health that turn food into nutritional well-being;
  - **stability:** the other three must hold at all times, against shocks and cycles.
- **HLPE (2020)** adds *agency* and *sustainability*. Neither has an indicator in these data; they are noted but not modelled.

### 1.2 Related concepts aiPHeed must not conflate

| Concept | What it is | Relation to food insecurity |
|---|---|---|
| Food-price pressure | Food inflation relative to a norm | **A driver of economic access**, not an outcome. High prices with rising incomes need not reduce access. |
| Hunger (SWS) | Self-reported involuntary hunger at least once in 3 months | **A severe outcome** of food insecurity (experience-based) |
| Food insecurity (FIES, SDG 2.1.2) | Experience scale of access constraints, moderate or severe | **The outcome** aiPHeed should estimate (FAO Voices of the Hungry; Ballard et al. 2013) |
| Malnutrition | Anthropometric or micronutrient status | Utilization outcome; slow-moving; caused by more than food |
| Poverty / subsistence incidence | Income below the poverty or food line | **Vulnerability**, and a structural access constraint. Annual or triennial. |
| Food stress (news) | Media reporting of adverse food events | **Signal of possible shocks**, not a measurement of conditions |

### 1.3 Outcome vs contributing factors (the design principle adopted)

The IPC Technical Manual 3.1 (IPC Global Partners 2021) and WFP's CARI (WFP 2021) separate two kinds of evidence:
- **food-insecurity outcomes:** food consumption, livelihood coping, nutrition, mortality;
- **contributing factors:** hazards and vulnerability, and the availability, access, utilization and stability conditions.

Both reach a classification by convergence of evidence, with outcomes taking precedence. Barrett (2010) and Upton, Cissé and Barrett (2016) argue that the measurement must be explicit about which dimension and which time scale it captures.

**Consequences for aiPHeed:**
1. A composite of contributing factors is a **risk index**, not a measurement of food insecurity.
2. Vulnerability (poverty, coping capacity) and **shock exposure** are cross-cutting risk factors. They modify how a hazard translates into food insecurity, so they are not interchangeable with the four dimensions.
3. **Outcomes must stay outside the index** and be used for validation at the level they are measured. Otherwise the index validates itself, as FIRI v2 partly does (§3.2).
4. Composite construction follows the OECD/JRC Handbook (2008):
   - normalisation against a fixed reference;
   - equal weights unless weights can be justified empirically;
   - mandatory sensitivity analysis;
   - an "exploratory" label until validated.

### 1.4 Fit to CALABARZON

- CALABARZON is a peri-urban, net-food-importing region (Cavite, Laguna, Rizal) with agricultural and fishing provinces (Quezon, Batangas). Access through incomes and prices dominates for most households.
- Availability shocks (crops, fisheries) matter locally, especially in Quezon and Batangas.
- Typhoons and El Niño are the main stability hazards.
- Utilization data (water, sanitation, child nutrition) exist only annually or below the quarterly scale.

**References** (standard published editions, cited from the documents' established content; not re-fetched in this session):
- FAO (1996) *Rome Declaration on World Food Security and World Food Summit Plan of Action*.
- FAO (2006) *Food Security*, Policy Brief Issue 2.
- HLPE (2020) *Food security and nutrition: building a global narrative towards 2030*, Report 15, CFS.
- IPC Global Partners (2021) *IPC Technical Manual Version 3.1*.
- WFP (2021) *Consolidated Approach to Reporting Indicators of Food Security (CARI)*, 2nd ed.
- Ballard, Kepple and Cafiero (2013) *The Food Insecurity Experience Scale: development of a global standard for monitoring hunger worldwide*, FAO technical paper.
- Barrett (2010) "Measuring food insecurity", *Science* 327: 825–828.
- Upton, Cissé and Barrett (2016) "Food security as resilience", *Agricultural Economics* 47: 135–147.
- OECD/JRC (2008) *Handbook on Constructing Composite Indicators*.
- SWS hunger methodology (SWS survey releases).
- DOST-FNRI NNS/ENNS reports.

---

## 2. Dimension-to-evidence matrix (actual availability verified in the project files)

Publication delays are typical lags (PSA/BSP release calendars); only SWS dates are verified per release in `sws_rounds.csv`.

**Type** codes: D = direct outcome, P = indirect proxy, C = context, M = model-derived.

| Dimension / layer | Mechanism | Indicator used | Type | Source, level, coverage | Delay | Two-quarter use | Limitations / overlap | Validation needed |
|---|---|---|---|---|---|---|---|---|
| **Outcome** | Experienced hunger | SWS hunger, total | **D** | SWS, **Balance Luzon only**, 2021-Q2 … 2026-Q3 (no 2021-Q1/2022-Q1; 2025-Q2/Q3 non-approved rounds) | 1–15 weeks after fieldwork | Validation target (regional) | 300–600 respondents, ±4–6 pts; regional | — |
| **Outcome** | Moderate or severe food insecurity | FNRI FIES (NNS 2025) | **D** | Region IV-A, **one value** (22.6%, press-sourced) | ~1 year | None | 1 observation | Primary FNRI table |
| **Outcome** | Food poverty | PSA subsistence incidence | D/C | Province, 2021 and 2023 | ~8 months to 3 years | Face validity only | CV 17–62%; income-based | — |
| **Outcome (missing)** | Local FIES | CBMS FIES by LGU | D | **Not in project.** CBMS 2022/2024, held by LGUs and PSA RSSO IV-A | — | Local validation | Needs acquisition and consent | E26 O1 specification |
| Access, economic | Food purchasing power | a1 food CPI YoY | P | PSA, province, 2021-01 … 2026-09 | ~1 week after the month | Projected by base-effect drift (the one indicator with demonstrated 1–2-quarter skill) | **Food-minus-headline excluded:** r = 0.91 with a1 in 2021–22 (double counting) | Against FIES/SWS |
| Access, income | Livelihood / jobs | a2 unemployment + underemployment | P | PSA LFS, **national**, 2021-01 … 2026-08 | ~5–6 weeks | Last known value | Same for all provinces | Provincial LFS |
| Access, household support | Remittance income | a3 OFW remittances YoY | P | BSP, **national**, 2021 … 2025-Q4 (**2026 missing**) | ~6–7 weeks | Last known value | National; missing 2026 → dimension uses a1, a2 only | — |
| Availability | Local food production | v1 palay + corn YoY | P | PSA, province, 2021 … 2026-Q2 (YoY from 2022-Q1 under the window rule) | ~6–8 weeks | Last known value | Local production ≠ local supply (net importers) | — |
| Availability | Fish supply / fish kills | v2 fish + aquaculture YoY | P | PSA, province, same coverage | ~6–8 weeks | Last known value | **Fish-kill events are not a dated series**; only volumes | — |
| Stability | Typhoon shocks | s1 tropical cyclones | P | PAGASA, province, 2021 … 2026-Q3 (2026-Q3 incomplete) | Near real time | Seasonal climatology for the target quarter | Count, not damage | — |
| Stability | Drought / El Niño | s2 drought alert | P | PAGASA, province, 20 alert quarters | Near real time | Last known value | Binary; no rainfall series | — |
| Stability | Policy supply shocks | rice-policy events | C | National announcements | Same day | Feature (market group) | Not in the index | — |
| **Utilization** | Diet, nutrition, WASH | — | **NOT OBSERVED** | OPT Plus (annual), ENNS (irregular): not in project | — | — | **Missing dimension, not imputed** | Data acquisition |
| Vulnerability | Structural poverty | 2021 SAE poverty (province mean) | C | PSA, LGU, one year, released ~2024–25 | — | **Separate layer**; LGU prioritization weight (Obj 3) | Static; Lucena substitute unverified | — |
| Vulnerability | Density / exposure | POPCEN 2024 density | C | PSA, LGU | — | LGU weight | Static | — |
| Signal | Food-stress news | FSSI-v3, trigger counts | M | 695 admitted headlines; 20/115 SUFFICIENT province-quarters | Real time (collected later) | Feature (ablation) | Titles only; English national media; AI-annotated | Human sample (§7) |

**The five evidence groups in this framework.**
- Markets/prices → access. Climate → stability. Fisheries → availability (fish kills not dated). Employment → access. Remittances → access/household support.
- Together they cover parts of **three** of the four dimensions.
- They contain **no outcome** and **no utilization** evidence, so they cannot define food insecurity by themselves.

---

## 3. Audit of T43 and FIRI v2

### 3.1 T43

- **Rule:** HIGH iff SWS hunger > 11.3 AND (food YoY > P60 OR food-minus-headline YoY > P60).
- **In practice:** hunger exceeded 11.3 in every evaluated quarter, and also exceeded every threshold anchored on 2021–22 (P25 to P90). So T43 = the price condition on 155/155 rows.
- **HIGH came mostly from the gap term** (13 of 18 Lead-2 HIGH cases), i.e. food prices outrunning headline inflation.
- **Verdict:** T43 is a **price-pressure label** (one access mechanism). It is not food insecurity. Its regional-hunger gate is inactive, and it double-counts the price movement (food YoY and gap, r = 0.91).

### 3.2 FIRI v2 (the served map value)

FIRI v2 is a six-domain proxy composite: affordability, vulnerability, climate/production, household economy, news, regional hunger.
- Regional SWS hunger is an **input domain** (25–29% weight, same for all provinces).
- Its domain weights were **fitted walk-forward to the same SWS outcome**.
- Its reported agreement with SWS (16/17) is therefore not independent validation.

E71 tested the contributing factors *without* the outcome (V1): they do not track SWS. This indicates that FIRI v2's apparent agreement comes mainly from its hunger domain. FIRI v2 also mixes vulnerability (a static layer) with dimensions, and classifies 94% of province-quarters HIGH.

**Verdict:** FIRI v2 stays exploratory. It must not be described as validated. Removing the outcome from its inputs is recommended before any validation claim; this is a serving change that needs your and your adviser's decision.

---

## 4. Implemented architecture (E71)

| Layer | Implemented as | Code |
|---|---|---|
| L1 Outcome | SWS (regional), subsistence (provincial), FIES 2025 (regional, one value). **Validation only.** | `e71_score.py` V1/V2 |
| L2 Dimensions | Indicator percentiles vs the 2021–22 reference, in the adverse direction; dimension = mean of its observed indicators; UTILIZATION not observed | `e71_index.py` |
| L3 Vulnerability | 2021 SAE poverty, separate; not in the class rule (static, released after most origins) | unchanged Obj 3 weights |
| L4 Integrated | FIR71 = mean of ACCESS, AVAILABILITY, STABILITY (equal weights, OECD default). HIGH iff FIR71 > the P60 of the 2022 reference composite (E40 convention; 0.381). Profile = three scores + stressed dimensions (> 0.75). | `e71_index.py` |
| L5 Forecast | DIMFUSE: project each indicator to t + h (CPI base effect; seasonal typhoon climatology; last known values), combine, logistic calibration on as-of labels. LightGBM (fixed configuration). LR, PSA-only, NLP-only, persistence, climatology. | `e71_lib.py`, `e71_predict.py` |
| L6 Validation | V1 regional outcome, V2 provincial cross-section, V3 collapse and sensitivity, V4 synthetic scenarios | `e71_score.py`, `tests/test_e71.py` |

**Why not a single supervised classifier on a food-insecurity outcome?**
- There is no provincial outcome with repeated observations. A supervised provincial classifier would have to be trained on a proxy, and the proxy would become its own ground truth.
- The defensible architecture is therefore an explicit, transparent contributing-factor index forecast at Lead 2 and validated against outcomes at their own level.
- A hierarchical model of regional SWS on regional dimension means is possible in principle, but 17 quarters do not support it. The exploratory in-sample OLS gives a *negative* access coefficient.

### 4.1 Scenario tests (V4; synthetic inputs, clearly marked)

`tests/test_e71.py` uses an invented reference distribution. All pass.

| Situation | Framework output |
|---|---|
| High food inflation, otherwise stable | ACCESS raised but not stressed; FIR71 moves at most 1/9 |
| Low inflation with falling income and remittances | ACCESS is the top dimension while the price percentile is low |
| Reduced crop and fish production, stable prices | AVAILABILITY top; ACCESS not stressed |
| Typhoon and drought shock | STABILITY stressed |
| High poverty, no price shock | No change to FIR71; vulnerability is reported separately (by design) |
| Multiple simultaneous shocks | All 3 dimensions stressed; highest FIR71; above threshold |
| Missing indicators | Dimension or index is INSUFFICIENT, never zero |

---

## 5. Missing dimensions and correlated indicators

- **Utilization:** not observed. It is never imputed, and every output says the index covers 3 of 4 dimensions.
- **Remittances 2026:** missing. ACCESS uses the observed indicators only. Missing ≠ no risk.
- **2026-Q3:** has no FIR71 label until PSA publishes Q3 production. These rows were excluded, not filled.
- **Double counting:**
  - food-minus-headline is removed from the index (r = 0.91 with food YoY in the reference period; 0.77 overall);
  - national indicators (a2, a3) are one value per quarter, so they shift all provinces together and add no provincial information.

**Sensitivity of the class:**

| Variant | Agreement with the main class | HIGH prevalence |
|---|---|---|
| Threshold P50 | 86/90 | 0.59 |
| Threshold P75 | 79/90 | 0.42 |
| Gap instead of food YoY | 85/90 | 0.58 |
| Without ACCESS | 78/90 | — |
| Without AVAILABILITY | 69/90 | — |
| Without STABILITY | 68/90 | — |

No single dimension determines the class.

**A disclosed weakness of the frozen threshold.** The reference composite is low: 2022 had few typhoons and La Niña without drought alerts. The P60 cut (0.381) is therefore reached by 42 of 49 HIGH rows without any single dimension above 0.75. "HIGH" means *moderately above the 2021–22 reference on average*, not convergent multi-dimension stress.

---

## 6. Validation and forecasting results

### 6.1 Does FIR71 correspond to food insecurity? (V1, V2)

| Test | Result | Verdict |
|---|---|---|
| V1: mean FIR71 vs SWS hunger, 17 quarters | ρ = −0.21 [−0.68, +0.35]. ACCESS −0.34, AVAILABILITY +0.01, STABILITY −0.04. Change direction 8/16. | **Not supported** |
| V2: FIR71 2023 vs subsistence 2023 (5 provinces) | ρ = −0.40 | Fails face validity |
| V2: FIR71 2022 vs subsistence 2021 | ρ = −0.87. Quezon, the highest subsistence (6.6%), has the lowest FIR71. | Fails face validity |

**Interpretation.**
- Regional hunger rose from 9–12% (2022–23) to 16–25% (2024–26).
- In 2025–26, food inflation fell (rice tariff), production was not unusually low, and few shocks were recorded. All measured contributing factors eased while hunger stayed high.
- The drivers of hunger in this period are not in the data: household incomes beyond national LFS rates, debt, local livelihoods, and possibly survey-sample effects.
- Quezon's structural poverty is the vulnerability layer, which the class rule deliberately excludes. That is why V2 fails for Quezon. Adding poverty would change the cross-section, but it is static and was released after most origins, so it cannot carry the quarterly signal.

**Conclusion.** With the indicators that can be measured, **no tested construction of contributing factors corresponds to the measured outcomes.** FIR71 is a non-collapsed, transparent **exploratory risk index**. It is not a food-insecurity measure.

### 6.2 Lead-1/2/3 forecasts of the FIR71 class

All rows: expanding window, as-of labels q ≤ t − 1, identical rows across arms, threshold 0.5.

**Lead 2:** 45 rows, 9 quarters (2024-Q2 … 2026-Q2), 22 HIGH, ICC 0.63, effective n ≈ 13.

| Arm | Correct | Acc [Wilson] | Prec H | Rec H | F1 H | Bal | AUC | Brier | Slope |
|---|---|---|---|---|---|---|---|---|---|
| **DIMFUSE (selected by rule)** | 29/45 | **0.644** [0.498, 0.768] | 0.594 | 0.864 | 0.704 | 0.649 | 0.852 | **0.225** | 1.01 |
| LightGBM (Objective 2 model) | 22/45 | 0.489 [0.350, 0.630] | 0.488 | 0.909 | 0.635 | 0.498 | 0.519 | 0.284 | 0.24 |
| LightGBM without news | 22/45 | 0.489 | 0.488 | 0.909 | 0.635 | 0.498 | 0.521 | 0.286 | 0.20 |
| IV. LR | 29/45 | 0.644 | 0.600 | 0.818 | 0.692 | 0.648 | 0.761 | 0.247 | 0.44 |
| II. PSA-only LR | 29/45 | 0.644 | 0.594 | 0.864 | 0.704 | 0.649 | 0.674 | 0.314 | 0.22 |
| III. NLP-only LR | 20/45 | 0.444 | 0.465 | 0.909 | 0.615 | 0.455 | 0.512 | 0.337 | −0.18 |
| I. Persistence | 26/45 | 0.578 | 0.545 | 0.818 | 0.655 | 0.583 | 0.583 | 0.422 | — |
| Province climatology | 18/45 | 0.400 | 0.439 | 0.818 | 0.571 | 0.409 | 0.464 | 0.283 | — |
| Majority | 22/45 | 0.489 | — | 1.0 | 0.657 | 0.500 | 0.500 | 0.511 | — |

**Paired comparisons (Lead 2):**

| Comparison | Δ Brier [95% CI] | Quarter sign test |
|---|---|---|
| DIMFUSE vs LightGBM | −0.058 [−0.104, −0.007] | 7/2 (p 0.18) |
| DIMFUSE vs persistence | −0.197 [−0.337, −0.074] | 7/2 (p 0.18) |
| LightGBM vs persistence | −0.139 [−0.289, +0.004] | — |
| LightGBM vs LR | +0.037 [−0.052, +0.128] | — |
| LightGBM vs PSA-only | −0.030 [−0.150, +0.086] | — |
| LightGBM vs NLP-only | −0.054 [−0.128, +0.016] | — |

After Holm adjustment, the LightGBM has no credible advantage over any Objective 4 baseline.

**DIMFUSE errors.** Its LOW recall is 0.435. False alarms concentrate in 2025-Q1/Q2 and 2026-Q1/Q2, when composites fell faster than the projections expected.

**Lead 1** (55 rows, 11 quarters):

| Arm | Accuracy | Brier |
|---|---|---|
| PSA-only LR | 0.691 | 0.233 |
| DIMFUSE | 0.582 | 0.251 |
| Persistence | 0.545 | — |
| LightGBM | 0.491 | 0.278 |

**Lead 3** (40 rows, 8 quarters):

| Arm | Accuracy | Brier |
|---|---|---|
| Persistence | 0.650 | — |
| LightGBM | 0.350 | 0.356 |
| DIMFUSE | 0.425 | 0.408 |

**Furthest reliable horizon** (pre-set criterion: beat persistence and climatology, each with CI < 0 and sign p < 0.05): **none.**

**NLP contribution:** removing news changes Lead-2 Brier by +0.002 [−0.000, +0.006]. **No measurable incremental value.**

### 6.3 The 80% statement

**80% Lead-2 accuracy was not demonstrated.**
- **Best result:** 29 of 45 = 0.644 (DIMFUSE), Wilson [0.498, 0.768]; LightGBM 0.489.
- **Pre-registered criteria:**
  - accuracy ≥ 0.80: **fails**;
  - HIGH recall ≥ 0.50: passes;
  - balanced accuracy ≥ 0.70: **fails**;
  - beats persistence: passes.
- **Not unseen:** every quarter was examined in earlier experiments.
- **Even had it passed,** it would be **proxy-prediction accuracy**, because V1 is not supported.
- **Earlier results:** on the price-pressure label T43, the best Lead-2 result was 0.72 (E70). It is not food-insecurity accuracy.

**Why 80% cannot be established now:**
1. There is no provincial outcome series.
2. The regional outcome decoupled from every measured contributing factor in 2025–26.
3. There are 9–10 Lead-2 quarters with an effective n of about 13–23, so the 95% intervals span ±0.13 or more.
4. All quarters are reused.

**Sealed for genuinely unseen evaluation** (`sealed/prospective.csv` sha `1e729585…`): 2026-Q4 (Lead 2 from 2026-Q2; Lead 1 from 2026-Q3) and 2027-Q1 (Lead 2). DIMFUSE puts 2027-Q1 at 0.11–0.33 (all LOW). FIR71 outcomes become scorable after PSA publishes Q4 2026 and Q1 2027 production.

---

## 7. Objectives 1–4 (approved wording in Chapter I §1.5, quoted in the E70 report §1)

| Objective | Status | Evidence | What is still required |
|---|---|---|---|
| 1 NLP pipeline (XLM-RoBERTa sentiment, BERTopic, bias-corrected FSSI per province-quarter) | **PARTIALLY MET** | Pipeline implemented and served. **Human validation workflow complete:** 300 blind stratified headlines, a second blank annotator file, and a scorer for weighted precision/recall/F1, Cohen's κ, consensus reference, trigger and province agreement, and Filipino-stratum agreement (synthetic-label unit test). News adds no measurable forecast value (Lead-2 Δ Brier +0.002). | **Researcher:** label `E70/annotation/HUMAN_ANNOTATION_SAMPLE.csv`, and the annotator-2 copy in `E71/annotation/`. Bias correction (log weight) has no reference to validate against, so it stays an unvalidated limitation. Filipino coverage is 7/695 headlines. |
| 2 LightGBM metrics and furthest reliable horizon | **PARTIALLY MET** | Full metrics for Leads 1–3 on T43 (E70) and on FIR71 (E71). Expanding window, as-of labels, sealed, reproducible. | No valid food-insecurity outcome; LightGBM is worse than DIMFUSE and LR on FIR71; no reliable horizon; 80% not reached; no unseen outcomes yet |
| 3 LGU rankings from validated province forecasts, poverty + density weights | **PARTIALLY MET** | 142/142 LGUs complete, finite, mapped and consistent across API, map, PDF (34/34 Batangas values at 4 dp) and rankings (E70 `obj3.py`; no serving change since). Weights recomputed exactly. Labelled "relative prioritization". | **Validated province-level forecasts do not exist.** A CBMS LGU FIES outcome is needed to validate any local ranking. |
| 4 Comparison with persistence, PSA-only, NLP-only, LR | **NOT MET for the LightGBM on FIR71; PARTIAL overall** | On identical FIR71 rows with Holm: no credible LightGBM advantage over any of the four. On T43 (E70): credible only over IV. DIMFUSE beats persistence on Brier (CI < 0), but the sign test is not significant. | A model that beats all four baselines on a valid outcome, ideally on unseen quarters |

**Fully met:** none. Each objective's software exists, and none is marked met on that basis.

---

## 8. Implementation, tests, reproduction, data requirements

**Commits** (branch `e71-food-insecurity-dimensions`, not pushed):
- `08ab805`: protocol frozen;
- `c3daa19`: index library and sealed forecasts;
- `df652b6`: scoring, validation, annotation workflow, tests;
- the report commit, given in the reply.

**Files** (all new; no backend or frontend file changed in E71):
- `E71/PROTOCOL.md`
- `runner/e71_index.py` (pure index), `e71_lib.py`, `e71_predict.py`, `e71_score.py`, `e71_annotation.py`
- `sealed/*`, `out/labels.csv`, `out/score.json`, `tables/E71_TABLES.md`
- `annotation/HUMAN_ANNOTATION_SAMPLE_annotator2.csv`
- `tests/test_e71.py`
- this document, and `FINAL_OBJECTIVES_COMPLETION_AND_MODEL_VALIDATION_REPORT_E71.md`

**Tests:**

| Suite | Result |
|---|---|
| E71 + E70 experiment tests | 17/17, incl. synthetic scenarios, missing-not-zero, seals, as-of timing, decision rule, annotation scorer |
| Backend | 546 passed, 18 skipped, 0 failed |
| Frontend | vitest 49/49; `vite build` passed |
| Clean-checkout re-run of `e71_predict.py` | byte-identical `predictions.csv` (80a04455…) and `prospective.csv` (1e729585…) |

**Reproduction:**

```
git archive 089bdf2 aipheed-backend-aligned/experiments backend/data backend/config | tar -x -C LIB
cp -r E70_Objectives_Completion/inputs/aipheed-backend-aligned/data LIB/aipheed-backend-aligned/
export AIPHEED_EXP=LIB/aipheed-backend-aligned/experiments
python -B runner/e71_predict.py --out OUT     # compare with sealed/*.sha256
python -B runner/e71_score.py                  # about 10 min (bootstraps)
python -m pytest -q aipheed-backend-aligned/experiments/E71_Food_Insecurity_Dimensions/tests
```

**Outstanding data requirements** (in priority order; formats in E26 `MISSING_OBSERVATIONS_SPEC.md`):
1. **CBMS 2022/2024 FIES by LGU** (all 142, or at least about 75), from the LGUs or PSA RSSO IV-A. This is the only route to local validation.
2. **FNRI NNS 2023 provincial FIES** and the primary 2025 regional table: provincial and regional outcome anchors.
3. **Provincial income or livelihood series** (provincial LFS, DOLE displacement, DSWD DROMIC affected families): the access drivers missing in 2025–26.
4. **Utilization:** OPT Plus municipal undernutrition, WASH coverage (annual context).
5. **Dated fish-kill events** (BFAR advisories) for the fisheries group.
6. **Prospective outcomes:** score the E68/E69/E70/E71 seals once PSA Q4 2026–Q1 2027 data and SWS 2026-Q4/2027-Q1 are published.

**Decision for you and your adviser.** Whether to remove the SWS hunger domain from the served FIRI v2, so that SWS can serve as an independent validation outcome, or to serve FIR71's dimension profile instead. Either is a serving change. Neither was made, because no index has passed outcome validation.
