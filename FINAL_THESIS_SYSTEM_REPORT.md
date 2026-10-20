# aiPHeed: final thesis system report

**Date:** 2026-10-20
**Branch:** `final-thesis-system`, from `e69-food-insecurity-risk-framework` @ `feb9d4d` (the E69 head, verified equal to origin). The pushed commit SHA is recorded in §14 and in `aipheed-backend-aligned/experiments/FINAL_Thesis_System/out/commit_record.txt`.
**Thesis-demo configuration:** `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1` (`backend/config/thesis_demo.env`).
**Requirement basis:** Chapter I §1.5.2 and §1.7, verbatim from `THESIS 2 (11).pdf` (sha256 `88dd0b62…`; extract in `aipheed-backend-aligned/experiments/E25_Reliable_Forecasts_2021_2026/thesis_source/CHAPTER_I_verbatim.txt`).
**Final methodology decision (user, 2026-10-20):** no direct provincial or LGU food-insecurity outcome exists, so the system estimates local food-insecurity risk from the closest available indicators with a documented composite. The composite is frozen before evaluation, keeps the LightGBM food-price-pressure forecast as a distinct component, never treats regional hunger as provincial, and keeps missing distinct from zero. It is presented as an estimated risk assessment, never as a validated probability.

---

## 1. What can be claimed, and what cannot

**Can be claimed (measured, reproducible):**

- **Working system.** aiPHeed is a complete, working geospatial system for CALABARZON:
  - Filipino-English news pipeline: XLM-RoBERTa food-stress intensity, FSSI-v3, BERTopic topics;
  - LightGBM Lead-2 food-price-pressure forecasting, with expanding-window walk-forward evaluation at leads 1–3;
  - comparison with the four Chapter I baselines;
  - an **estimated food-insecurity risk index (FIRI v1)** per province, built from six indicator domains under a methodology frozen before evaluation;
  - priority rankings for all 142 cities and municipalities;
  - PDF reports;
  - a dashboard whose map, panels, rankings and API values agree.
- **What every province estimate shows.** Each estimate says why it is classified: domain scores, each indicator's value, 0–1 score and status, freshness (issue date, data periods) and coverage (domains available).
- **LightGBM Lead-2 metrics on development back-tests** (50 province-quarters, 10 quarters): accuracy 0.72, precision 0.63, recall 0.56, F1 0.59, AUC-ROC 0.65.
- **LightGBM against the Chapter I baselines:**
  - Lower Brier than all four on the same 45 rows.
  - The advantage is statistically established only against the PSA-only and the combined logistic regressions.
- **FIRI evaluation (§7).** Reported in full with the same protocol and the same rows. FIRI ranks rows reasonably (Lead-2 AUC 0.72; 0.81 on the 45 Objective 4 rows), but classifies almost everything HIGH (88% of Lead-2 rows), so its accuracy is low (0.44).

**Cannot be claimed:**

- **FIRI is not validated as a measure of food insecurity.**
  - No provincial or municipal food-insecurity outcome exists.
  - The T43 label shares its price sources with FIRI's affordability indicators, and the regional hunger outcome shares SWS with FIRI's hunger indicator.
  - FIRI is a proxy composite on a 0–1 scale, not a probability.
- **No reliable horizon.** No lead meets the pre-registered reliability criterion, for the LightGBM or for FIRI, so the "furthest reliable horizon" of Objective 2 V is **"none established"**.
- **The > 75% Lead-2 accuracy goal is not demonstrated:**
  - LightGBM: 0.72 on 50 rows; 0.78 on the 45 Objective 4 rows, not distinguishable from always-LOW at the quarter level;
  - FIRI: 0.44;
  - every scored row was examined during development; no unseen quarter has been scored.
- **Not municipal forecasts.** The LGU rankings are relative prioritizations.
- **No measured effect for news and climate.** News sentiment, BERTopic topics and El Niño information have no measured effect on forecast accuracy, and the news domain could not enter FIRI (§6.4).

---

## 2. Final acceptance matrix: Objectives 1–4 (exact Chapter I wording)

| Obj | Approved objective (verbatim) | Required outcome | Implemented components | Tests / reproducible evidence | Measured results | Known limitations | Status |
|---|---|---|---|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | FSSI and latent patterns per province-quarter, used by the system | `backend/app/news/pipeline_v3.py`: corpus of 9,667 titles (2021-01-01..2026-10-14), classifier v2, province attribution, syndication de-duplication, publication-date cutoff at each issue date, XLM-RoBERTa intensities. `fssi_v3()` with the bias weight. BERTopic outputs in `data/news_v3/` (152 topics). Served: v3 news feed, FSSI-v3 and the top topics per province. FSSI-v3 is FIRI's news indicator N1 (SUFFICIENT only). | `test_news_evidence_from_the_objective1_pipeline`; `test_e64_news_pipeline.py` | 695 admitted articles. FSSI-v3 for 2026-Q3: Cavite 0.40 (n 10), Laguna 0.28 (12), Rizal 0.28 (13), Batangas 0.19 (13); Quezon has 1 article, so it is withheld. Classifier v2: precision 0.92 / recall 0.75 on **AI-annotated** titles. | Titles only; collected retrospectively; annotation not human-validated. The bias correction is not validated. Only 3 SUFFICIENT province-quarters in the FIRI reference window, so **the news domain is excluded from FIRI by its frozen rule** (§6.4). No measured forecasting gain. | **Implemented but not validated** |
| 2 I–IV | "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC" | The four metric families for the proposed LightGBM | E56-TUNED LightGBM (FIRI's affordability indicator A1), walk-forward with issue-date cutoffs. `final_evaluation.py` and `firi_evaluate.py` compute from sealed predictions. Served by `/api/v1/config` `modelPerformance` and the PDF. | `test_final_evaluation_reproduces_sealed_predictions`; `test_firi_evaluation_reported_honestly` | LightGBM Lead 2: accuracy 0.72, precision 0.63, recall 0.56, F1 0.59, AUC 0.65, Brier 0.214. FIRI Lead 2: accuracy 0.44, precision 0.39, recall 0.94, F1 0.55, AUC 0.72, Brier 0.264 (§7) | Development evidence; T43 is price pressure | **Implemented; metrics reported; performance not validated** |
| 2 V | "Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | Multi-lead evaluation and a furthest reliable lead under a stated criterion | Leads 1–3 (lead 4 not computable under the CPI cutoff). Criterion pre-registered 2026-10-19 (E63 §8, sha `5b3ee7e9`), applied unchanged to the LightGBM and to FIRI. | same tests; `furthestReliableLead = None` | No lead qualifies for either. LightGBM lead 1 is closest (CI below 0 vs both baselines, 9 of 12 quarter wins). | 9–12 quarters per lead | **Implemented; outcome: no reliable horizon established** |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | 142 LGU rankings from province estimates with poverty and density weights | LGU index = province FIRI × the approved LGU vulnerability (0.6 poverty, PSA SAE 2021; 0.4 density, POPCEN 2024), with exact ranks. Every LGU is labelled "relative prioritization, not a municipal forecast". | `test_142_lgus_finite_mapped_and_coloured` (also checks LGU = FIRI × vulnerability); browser: all 142 dashboard values equal the API (§13) | 142 unique LGUs, finite, mapped (34/23/30/41/14), coloured | The province estimates are **not validated** (the objective's premise). Inside a province the order is the vulnerability order. Lucena's poverty value is a substitute. | **Implemented; premise ("validated province-level forecasts") unmet → partially met** |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | A fair comparison on the same rows, issue dates and target | 45 identical rows (targets 2024-Q3..2026-Q3), the same T43 labels and issue dates, plus the majority class; paired Brier tests and McNemar. The same comparison for FIRI. | `test_final_evaluation_reproduces_sealed_predictions`; `test_firi_evaluation_reported_honestly` | LightGBM Brier 0.178 vs 0.400 (I), 0.598 (II), 0.235 (III), 0.646 (IV), 0.311 (majority); established only vs II and IV. FIRI (0.268) beats no baseline by the rule and is worse than the LightGBM (§7.2). | Development rows only | **Implemented; partial superiority of the LightGBM on examined rows; not validated on unseen quarters** |

**Discrepancy recorded, not changed:** the run brief names DEPDev IV-A among the users. Chapter I §1.7 names "50 DA Region IV-A evaluators" only, and the user removed DEPDev on 2026-10-10.

---

## 3. What the system estimates

| Output | What it is | What it is not |
|---|---|---|
| **Province estimate (the map colour, the "risk level score")** | FIRI v1: the estimated relative risk that households in the province face food insecurity two quarters after the issue date (Lead-2), on a 0–1 scale; HIGH at 0.50 | A probability, a measured food-insecurity rate, or a validated classification |
| **Food-price-pressure forecast** | E56-TUNED LightGBM, Lead-2, label T43. FIRI indicator A1, shown separately in every panel and the PDF as "exploratory food-price-pressure score" | A food-insecurity forecast (T43 equals provincial price pressure on every evaluated row) |
| **Regional hunger outlook** | P(SWS involuntary hunger, Balance Luzon, above 11.3% two quarters ahead), from the latest approved round posted before the issue date (E69 R0). FIRI indicator H1, **the same value for all five provinces** | A provincial hunger estimate |
| **LGU prioritization** | Province FIRI × LGU vulnerability (0.6 poverty + 0.4 density), ranked within the province and the region | A municipal forecast or an official classification |

**Province estimates and LGU prioritization are kept distinct:**
- the province panel shows FIRI with its domain and indicator breakdown;
- the LGU list is headed "Relative prioritization derived from the province forecast with PSA poverty and population density; not validated municipal forecasts";
- every LGU row carries `riskLevelBasis` and `disaggregationLabel` saying the same.

---

## 4. Data support (2021-Q1..2026-10-14 only)

| Indicator role | Data | Geography | Coverage and freshness at the 2026-10-01 issue |
|---|---|---|---|
| Affordability | PSA provincial CPI (food, headline), PSA wholesale rice prices; E56-TUNED LightGBM | province | CPI to 2026-08; rice to 2026-Q2 |
| Vulnerability | PSA 2021 municipal SAE poverty; POPCEN 2024 population and land area | province (from 142 LGUs) | static; published after the earliest origins (timing deviation, §6.3) |
| Climate and production | PAGASA El Niño Alert / Advisory / Climate Advisory (dated); IBTrACS typhoons within 300 km; PSA palay, corn and fisheries production | national (PAGASA); province | PAGASA Climate Advisory 2026-09-23 in force; production 2026-Q2; typhoons for 2026-Q3 incomplete (fetched 2026-09-09), so treated as missing |
| Household economy | PSA LFS unemployment; BSP cash remittances (USD) | **national** | LFS 2026-Q2; remittances end 2025-Q4, so missing from 2026 issues |
| News | Pipeline v3 FSSI-v3 (titles, Google News) | province | used only when SUFFICIENT (≥ 5 articles); domain excluded (§6.4) |
| Regional hunger | SWS involuntary hunger, Balance Luzon, approved rounds | **region** | latest round posted before the issue: 17.3% |

No pre-2021 data is used anywhere (user rule).

---

## 5. How the indicators are combined: FIRI v1 (frozen)

**Protocol files:**
- protocol `aipheed-backend-aligned/experiments/FINAL_Thesis_System/FIRI_PROTOCOL.md` (sha256 `82038f6d…` in `runner/FIRI_PROTOCOL_SHA256.txt`), frozen before anchors were computed or any FIRI value was scored;
- Amendment 1, `FIRI_PROTOCOL_AMENDMENT_1.md` (sha256 `1007d2c4…`), frozen after the anchor feasibility check and **before any FIRI value was scored** (§6.3);
- anchors `backend/data/thesis/firi_anchors.json` (content sha256 `56223d76…`), written once by `runner/firi_anchors.py`, which refuses to overwrite.

**Shared code:** `backend/app/ml/inference/firi.py` is used by both the evaluation runner and the served dashboard (training/serving parity, checked by `test_runtime_firi_equals_the_evaluated_history`).

### 5.1 Indicators and direction (higher score = more risk)

| Domain | Indicator | Raw value x | Score |
|---|---|---|---|
| A Affordability | A1 Lead-2 food-price-pressure forecast | LightGBM price part P_price | x (0–1) |
| A | A2 headline inflation above the province's usual level | headline (latest two CPI months before issue) − the province's 2021–22 headline P60 | anchored |
| A | A3 wholesale rice price change | rice YoY, quarter t−1 | anchored |
| V Vulnerability | V1 structural vulnerability | 0.6 × poverty_norm + 0.4 × density_norm, min-max across the five provinces (the approved LGU weighting at province level) | x (0–1) |
| C Climate and production | C1 PAGASA El Niño Alert/Advisory/Climate Advisory in force before the issue | 1 / 0 | x |
| C | C2 typhoons within 300 km in quarter t | count | anchored |
| C | C3 crop production drop | −min(palay YoY, corn YoY), quarter t−1 | anchored |
| C | C4 fisheries production drop (production, not fish-kill events) | −fisheries YoY, quarter t−1 | anchored |
| E Household economy (national) | E1 unemployment change | ur YoY, quarter t−1 | anchored |
| E | E2 remittance decline | −remittances YoY, quarter t−1 | anchored |
| N News | N1 FSSI-v3, SUFFICIENT only | FSSI-v3 | anchored (unusable, §6.4) |
| H Regional hunger | H1 P(SWS hunger at t+2 > 11.3%) | probability | x (0–1) |

Not used, with reasons:
- subsistence incidence (CV 17–62%);
- bottom-30% CPI (redundant with the general CPI, r 0.78–0.98; ends 2026-06);
- BERTopic topics (no direction);
- news trigger shares (zero in 46–100% of rows).

### 5.2 Normalization, weights, threshold

| Rule | Value |
|---|---|
| Continuous indicators | s = clip((x − P10) / (P90 − P10), 0, 1). P10/P90 come from origins 2021-Q3..2023-Q4 (Amendment 1), province rows; national series contribute one value per quarter. No label is read. |
| Indicators already on 0–1 | used as they are (A1, V1, C1, H1) |
| Degenerate anchor | fewer than 5 window values or P90 = P10 → the indicator is excluded |
| Domain score | mean of its available indicator scores |
| Weights | equal across domains (OECD/JRC *Handbook on Constructing Composite Indicators*, 2008: the default when no outcome exists to estimate weights); nothing is estimated from data |
| FIRI | mean of the available domain scores; at least 4 of 6 domains, otherwise INSUFFICIENT DATA |
| Class | HIGH if FIRI ≥ 0.50 (the scale midpoint, not tuned), on the unrounded index |
| Explanation | each domain's exact share of FIRI; each indicator's value, score and status |

**Anchors** (`firi_anchors.json`):

| Indicator | Window values | P10 | P90 |
|---|---|---|---|
| A2 headline above usual | 50 | −2.31 | +3.06 points |
| A3 rice YoY | 33 | −4.45 | +16.44% |
| C2 typhoons | 50 | 0 | 2 |
| C3 crop drop | 35 | −8.54 | +44.92 |
| C4 fisheries drop | 35 | −40.74 | +39.11 |
| E1 unemployment change | 7 | −2.65 | −1.07 points |
| E2 remittance decline | 7 | −5.95 | −1.27 |
| N1 FSSI-v3 | **3** | — | — (unusable) |

### 5.3 Missing, stale, unavailable (never zero)

| Case | Rule |
|---|---|
| Missing indicator (NaN, not published by the issue date, FSSI below SUFFICIENT) | dropped from its domain; its status is reported (`missing`, `incomplete`, `too_few_articles`) |
| Domain with no indicator | dropped; FIRI is renormalised over the remaining domains; the domain count is shown |
| Typhoon count of a quarter in progress when fetched (2026-Q3) | `incomplete` → missing |
| Dashboard card of a group whose every indicator is missing | status `insufficient_data` ("Missing data is not a sign of low risk"), never "no effect" |

### 5.4 Timing

Every indicator uses only data published before the issue date O(t):
- CPI months before the issue;
- production, LFS and remittances of quarter t−1;
- PAGASA items dated before the issue;
- SWS rounds posted before the issue;
- news published before the issue.

The LightGBM part comes from sealed walk-forward predictions (E57 for Lead 2, E63 for leads 1–3). The served 2027-Q1 value uses the 2026-10-01 record.

---

## 6. Amendment, deviations and exclusions (disclosed)

### 6.1 The LightGBM forecast stays a distinct component

A1 is one of three affordability indicators, about 1/15 of the index on average. Its value is shown separately everywhere:
- `price_pressure_score` in the province rows;
- "The exploratory food-price-pressure score … is …" in the summary text;
- the "Market / Prices" card;
- the PDF.

### 6.2 Regional hunger is never provincial

H1 is the same number for every province and is labelled "Regional hunger (Balance Luzon)" in the domain list and the cards. The indicator definition and the `/config` caveat say so.

### 6.3 Amendment 1 (frozen before scoring)

With the original 2021-Q3..2022-Q4 anchor window:
- E1/E2 had too few values and N1 had 3;
- V1 was withheld before 2025-07-01;
- 6 of 10 Lead-2 origins had fewer than 4 domains, so FIRI could not be evaluated.

Amendment 1 made two changes:
- it widened the window to 2021-Q3..2023-Q4;
- it made V1 a static structural profile at every origin, a publication-timing deviation because PSA SAE 2021 and POPCEN 2024 appeared after the earliest origins.

The original strict-V rule is reported as a sensitivity. The pre-amendment anchors are kept in `out/firi_anchors_v0_original_window.json`. The amendment was written and hashed before any FIRI value or label was read.

### 6.4 News domain excluded by the frozen rule

FSSI-v3 has only 3 SUFFICIENT province-quarters in the anchor window, below the 5-value minimum. N1 therefore has no usable anchor, and FIRI uses five domains: A, V, C, E, H. FSSI-v3 is still served as news evidence (SUFFICIENT only).

### 6.5 Household-economy anchors are saturated (limitation found after scoring; method unchanged)

- The 2021–2023 reference years were the post-lockdown recovery. Unemployment fell 1.1–2.7 points a year (E1 P90 = −1.07), so any smaller fall or a rise scores 1.
- Remittance growth was 1.3–6.0%, so slower growth scores near 1.
- Domain E averages 0.90 on the Lead-2 rows and is 1.0 in every province at the 2027-Q1 issue.
- Each employment card states this.

**Post-hoc diagnostic** (`runner/firi_posthoc_diagnostic.py` → `out/firi_posthoc_diagnostic.txt`). It is not pre-registered and was not used to change FIRI. Recomputing Lead-2 FIRI without E gives:
- accuracy 0.60 (frozen: 0.44);
- HIGH share 0.56 (frozen: 0.88);
- AUC 0.72 (frozen: 0.72);
- HIGH recall 0.72, LOW recall 0.53.

The 2027-Q1 classes do not depend on E: without E all five provinces stay ≥ 0.50, with Batangas lowest at 0.53.

### 6.6 Display at the threshold

The approved UI prints scores with two decimals and reads ≥ "0.50" as HIGH. A LOW FIRI in [0.495, 0.5) is therefore served for display truncated to 0.49, so the number shown never contradicts the frozen class. The one evaluated case is Laguna 2026-Q1, FIRI 0.49975, LOW. The exact value stays in the text ("risk index 0.4998"), the LGU index, the regional mean and the evaluation (`test_class_follows_the_frozen_rule_near_the_threshold`).

---

## 7. How it is evaluated: results

**Protocol:**
- the existing expanding-window walk-forward predictions (sealed E57 / E63 / E55);
- the label T43;
- the same rows and issue dates as the LightGBM;
- the E63 §8 reliability rule;
- Wilson 95% CIs for accuracy.

**Outputs:** `out/firi_rows_all_leads.csv`, `out/firi_regional_outcome.csv`, `backend/data/thesis/firi_evaluation.json` (from `runner/firi_evaluate.py`). FIRI is used as a score for AUC and Brier; it is not a calibrated probability.

### 7.1 Leads 1–3

| Lead | Rows / quarters | Model | Acc [Wilson 95%] | Prec HIGH | Rec HIGH | Rec LOW | F1 | AUC | Brier | TP / FP / FN / TN | % rows HIGH |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 60 / 12 | **FIRI v1** | 0.400 [0.286, 0.526] | 0.364 | 0.952 | 0.103 | 0.526 | 0.636 | 0.278 | 20 / 35 / 1 / 4 | 92% |
| 1 | | LightGBM | 0.850 | 0.833 | 0.714 | 0.923 | 0.769 | 0.901 | 0.130 | 15 / 3 / 6 / 36 | |
| 2 | 50 / 10 | **FIRI v1** | 0.440 [0.312, 0.577] | 0.386 | 0.944 | 0.156 | 0.548 | 0.717 | 0.264 | 17 / 27 / 1 / 5 | 88% |
| 2 | | LightGBM | 0.720 | 0.625 | 0.556 | 0.813 | 0.588 | 0.649 | 0.214 | 10 / 6 / 8 / 26 | |
| 2 | | Persistence | 0.560 | 0.400 | 0.444 | 0.625 | 0.421 | 0.535 | 0.440 | 8 / 12 / 10 / 20 | |
| 2 | | Majority (LOW) | 0.640 | — | 0 | 1 | 0 | 0.500 | 0.360 | 0 / 0 / 18 / 32 | |
| 3 | 45 / 9 | **FIRI v1** | 0.378 [0.251, 0.524] | 0.333 | 1.000 | 0.097 | 0.500 | 0.698 | 0.281 | 14 / 28 / 0 / 3 | 93% |
| 3 | | LightGBM | 0.622 | 0.400 | 0.429 | 0.710 | 0.414 | 0.620 | 0.251 | 6 / 9 / 8 / 22 | |

**FIRI reliability rule** (Brier FIRI − baseline [quarter-cluster 95% CI], quarter wins / losses, sign p):

| Lead | vs persistence | vs climatology | Reliable? |
|---|---|---|---|
| 1 | −0.038 [−0.174, +0.099], 7/5, p 0.77 | −0.006 [−0.168, +0.151], 6/6, p 1.0 | no |
| 2 | −0.176 [−0.342, −0.0004], 7/3, p 0.34 | −0.041 [−0.219, +0.121], 5/5, p 1.0 | no |
| 3 | −0.208 [−0.388, −0.044], 6/3, p 0.51 | +0.015 [−0.167, +0.175], 3/6, p 0.51 | no |

**Sensitivities (descriptive; never used to change the method):**

| Lead | Strict V (V missing before 2025-07-01): acc / AUC / Brier | Without H: acc / AUC / Brier / Rec HIGH |
|---|---|---|
| 1 | 0.383 / 0.728 / 0.284 | 0.533 / 0.635 / 0.250 / 0.762 |
| 2 | 0.460 / 0.778 / 0.271 | 0.660 / 0.809 / 0.218 / 0.833 |
| 3 | 0.356 / 0.714 / 0.298 | 0.622 / 0.682 / 0.243 / 0.929 |

### 7.2 Objective 4 rows (45 identical rows, targets 2024-Q3..2026-Q3)

FIRI on these rows: accuracy 0.422, precision 0.350, HIGH recall 1.000, LOW recall 0.161, F1 0.519, AUC 0.809, Brier 0.268 (TP 14 / FP 26 / FN 0 / TN 5).

| Compared with | Baseline Brier | Δ Brier (FIRI − baseline) [95% CI] | Quarter wins / losses (sign p) | FIRI better by the rule? | McNemar (FIRI right only / baseline right only, p) |
|---|---|---|---|---|---|
| I. Naive persistence | 0.400 | −0.132 [−0.292, +0.032] | 6/3 (0.25) | no | 9/17, p 0.17 |
| II. PSA-only indicator (LR) | 0.598 | −0.331 [−0.521, −0.113] | 7/2 (0.09) | no (sign test) | 14/12, p 0.85 |
| III. NLP-only sentiment (LR) | 0.235 | +0.032 [−0.079, +0.127] | 4/5 (0.75) | no | 12/23, p 0.09 |
| IV. Logistic regression (combined) | 0.646 | −0.378 [−0.540, −0.185] | 7/2 (0.09) | no (sign test) | 15/11, p 0.56 |
| Majority class (always LOW) | 0.311 | −0.044 [−0.250, +0.152] | 4/5 (0.75) | no | 14/26, p 0.08 |
| LightGBM E56-TUNED | 0.178 | **+0.089 [+0.027, +0.143]** (FIRI worse) | 2/7 | no | 4/20, p 0.002 |

### 7.3 Regional food-insecurity outcome (the only direct observation; regional)

The regional mean FIRI was scored against observed SWS hunger above 11.3% at t+2:
- 18 quarters: 16/18 correct (0.89), against always-elevated 13/18 (0.72); AUC 0.94.
- H1 shares the SWS source, so this is not independent.
- Without H (16 quarters): accuracy 0.75, equal to always-elevated (0.75); AUC 0.96.

### 7.4 Reading of the evaluation

1. FIRI ranks rows better than the LightGBM: Lead-2 AUC 0.72 vs 0.65, and 0.81 vs 0.76 on the Objective 4 rows.
2. FIRI's absolute level is high, so at the fixed 0.50 threshold it says HIGH almost everywhere. The main sources are domain E (§6.5) and regional hunger (above 11.3% in every evaluated quarter).
3. FIRI is worse than the LightGBM on T43 Brier and accuracy. This is expected, because T43 is a price-pressure label and FIRI deliberately adds non-price evidence. T43 is therefore not a fair test of a food-insecurity index, and no fair test exists for CALABARZON provinces.
4. **FIRI is reported as an estimated food-insecurity risk assessment for planning, not as a validated classification.** The threshold and weights were not changed after these results.

---

## 8. Dashboard behaviour (thesis mode)

| Element | What it shows |
|---|---|
| Map colour, province "risk level score", regional "forecast index" | FIRI v1 (region = mean of the five provinces); class on the unrounded index (§6.6). Approved palette unchanged. |
| Province note and indicator definition (`/config`, `/provinces`) | "Estimated food-insecurity risk index (FIRI v1)": definition, unit "index 0–1 (HIGH at 0.5)", horizon, sources, caveat (not validated, regional hunger shared, national economy) |
| Trigger composition and "Why is this province at risk?" bars | each factor group's exact additive share of FIRI. Market / Prices = A1–A3; Climate Stress = C1–C3; Fish Kill = C4 (fisheries production, not fish-kill events); Employment = E1; OFW Remittance = E2. V and H go to the "other" share and are named in the summary text. |
| Factor cards (right panel) | status from FIRI (`contributes`, `no_effect`, `insufficient_data`) and an evidence line listing each indicator's value, 0–1 score and status, e.g. "Typhoons within 300 km: quarter still in progress when the data were fetched, not counted" |
| Summary sentence | "ESTIMATED FOOD-INSECURITY RISK for ⟨province⟩, ⟨quarter⟩: ⟨class⟩ (risk index …; HIGH at 0.50). Domain scores: …. Mainly raised by …. Not in the index: …" and then the separate food-price-pressure score sentence, without FIRI reasons attached to it |
| LGU list and map | FIRI × vulnerability; "relative prioritization, not validated municipal forecasts" |
| Past quarters | FIRI from `backend/data/thesis/firi_history.csv`, with "backtest estimate … development evidence"; observed T43 outcome shown |
| PDF | eyebrow "ESTIMATED FOOD-INSECURITY RISK INDEX (FIRI, LEAD-2)", FIRI text, exact-share driver section, the Objective 2/4 tables with FIRI rows |

**Served 2027-Q1** (issue 2026-10-01; five domains each; E2 missing, C2 incomplete, N excluded):

| Province | FIRI | Class | A | V | C | E | H |
|---|---|---|---|---|---|---|---|
| Laguna | 0.736 | HIGH | 0.64 | 0.29 | 0.87 | 1.00 | 0.88 |
| Quezon | 0.736 | HIGH | 0.59 | 0.60 | 0.61 | 1.00 | 0.88 |
| Cavite | 0.719 | HIGH | 0.49 | 0.59 | 0.64 | 1.00 | 0.88 |
| Rizal | 0.674 | HIGH | 0.53 | 0.38 | 0.58 | 1.00 | 0.88 |
| Batangas | 0.624 | HIGH | 0.33 | 0.18 | 0.73 | 1.00 | 0.88 |
| **Region (mean)** | **0.698** | HIGH | | | | | |

The LightGBM food-price-pressure part for 2027-Q1 is low: P_price 15% in Quezon, and A1 adds at most 0.01 to any index. The HIGH estimates come from regional hunger, national unemployment, the PAGASA El Niño advisory, crop and fisheries drops, and rice prices.

---

## 9. Thesis-demo system: startup and configuration

From a fresh checkout of `final-thesis-system`. On Windows, clone with long paths enabled: one old experiment snapshot path exceeds 260 characters, and a plain clone fails with "Filename too long".

```
git -c core.longpaths=true clone https://github.com/gwenndestura/aiPHeed.git
cd aiPHeed
git config core.longpaths true
git checkout final-thesis-system
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
cd ..\frontend
npm install
cd ..\backend
venv\Scripts\python.exe scripts\start_thesis_demo.py
```

This starts the API on http://localhost:8000 and the dashboard on http://localhost:8080. It runs with `AIPHEED_LEAD2_MODEL=thesis` and `AIPHEED_STRICT_MODEL=1`, migrates a scratch SQLite database if `DATABASE_URL` is unset, and generates a random `SECRET_KEY` if unset.

**Options and checks:**
- `--api-only`, `--api-port`, `--ui-port` adjust the startup.
- `GET /api/v1/config` → `servingModel` reports the mode, model ("aiPHeed thesis system v2: Food-Insecurity Risk Index FIRI v1 … with the E56-TUNED LightGBM food-price-pressure forecast as its affordability component"), issue date, target quarter and lead.

**Exact settings:**

| Setting | Value |
|---|---|
| Mode | `AIPHEED_LEAD2_MODEL=thesis` |
| Strict start | `AIPHEED_STRICT_MODEL=1`: refuses to start unless the mode is `thesis` and every required artifact exists and passes its check (`thesis_system.validate`, including that FIRI is computable for the served target); no silent fallback |
| Score record | `backend/data/e58/e58_record.json` (E56-TUNED, configuration 23 at the 2026-10-01 issue, Lead-2, target 2027-Q1) |
| Model artifacts | `backend/data/e56/model/` (including `features_2027Q1.csv`, the inference features FIRI reads) |
| FIRI | `backend/data/thesis/firi_anchors.json`, `firi_history.csv`, `firi_evaluation.json`; code `backend/app/ml/inference/firi.py` |
| Evaluation | `backend/data/thesis/final_evaluation.json` |
| Hunger | `backend/data/inputs/sws_rounds.csv` |
| News | `backend/data/news_v3` (and `news_e31`, `news_e60`) |
| LGU | `backend/data/inputs/lgu_vulnerability.csv` |
| Climate | `app/ml/inference/climate_watch.py`, `enso_context.py` (PAGASA items with dates) |

**Reproducing the FIRI evaluation** (from `backend/`):

```
venv\Scripts\python.exe -B ..\aipheed-backend-aligned\experiments\FINAL_Thesis_System\runner\firi_evaluate.py
venv\Scripts\python.exe -B ..\aipheed-backend-aligned\experiments\FINAL_Thesis_System\runner\firi_posthoc_diagnostic.py
```

`firi_anchors.py` verifies both protocol hashes and refuses to recompute the frozen anchors.

**Rollback:** remove the two variables (or set `AIPHEED_LEAD2_MODEL=e38`) and restart. The E38 production default is unchanged and untouched by this branch.

**Target quarter:** the target follows the Asia/Manila clock (`app/quarterly/target.py`):
- 2027-Q1 until 2026-12-31;
- from 2027-01-01 the target becomes 2027-Q2, and the frozen record is **not** served for it: the dashboard says no estimate exists, and `servingModel.servesTargetNow = false`.

**Next quarter:**
1. Refresh the data.
2. Run `scripts\build_record_e56.py` and `scripts\build_record_e58.py`.
3. FIRI is computed at runtime from the new record with the frozen anchors.

---

## 10. Objective 1 findings (NLP)

| Item | Finding |
|---|---|
| Corpus | 9,667 Google News titles, 2021-01-01..2026-10-14, Filipino and English. Collected retrospectively: 2,118 of 2,132 E60 articles were first seen after their issue date. |
| Relevance | Classifier v2: precision 0.92 / recall 0.75 against **AI annotations** (no human-validated set) |
| Attribution and timing | Province from title geocoding; quarter from the Philippine publication date; only articles published before the issue date are used (`pipeline_v3.asof`) |
| FSSI-v3 | Mean XLM-RoBERTa intensity × bias weight log(1 + median n) / log(1 + n). The weight is from the approved Equation 2 and **not validated**; with n = 1 it multiplies by up to 3.7, so FSSI is served only with ≥ 5 articles. Missing evidence gives no FSSI, never 0. |
| BERTopic | 152 topics, 39.7% outliers, titles only, mostly geographic; served as the top 3 topics of the province-quarter (descriptive) |
| Forecast value | No measured gain: news-only Brier 0.445–0.507; adding news to the LightGBM changes Brier by ≤ 0.01 (E60/E64/E66–E68). Excluded from FIRI by its anchor rule (§6.4). |

---

## 11. Objective 2: LightGBM lead-time table (sealed E63 walk-forward predictions; `FINAL_Thesis_System/out/lead_time_table.csv`)

| Lead | Rows / quarters | Model | Acc | Prec | Rec | F1 | AUC | Brier | TP / FP / FN / TN |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 60 / 12 | **LightGBM** | 0.850 | 0.833 | 0.714 | 0.769 | 0.901 | 0.130 | 15 / 3 / 6 / 36 |
| 1 | | Persistence | 0.683 | 0.550 | 0.524 | 0.537 | 0.647 | 0.317 | 11 / 9 / 10 / 30 |
| 1 | | Majority (LOW) | 0.650 | — | 0 | 0 | 0.500 | 0.350 | 0 / 0 / 21 / 39 |
| 1 | | Climatology | 0.650 | — | 0 | 0 | 0.344 | 0.284 | 0 / 0 / 21 / 39 |
| 2 | 50 / 10 | **LightGBM** | 0.720 | 0.625 | 0.556 | 0.588 | 0.649 | 0.214 | 10 / 6 / 8 / 26 |
| 2 | | Persistence | 0.560 | 0.400 | 0.444 | 0.421 | 0.535 | 0.440 | 8 / 12 / 10 / 20 |
| 2 | | Majority (LOW) | 0.640 | — | 0 | 0 | 0.500 | 0.360 | 0 / 0 / 18 / 32 |
| 2 | | Climatology | 0.640 | — | 0 | 0 | 0.214 | 0.304 | 0 / 0 / 18 / 32 |
| 3 | 45 / 9 | **LightGBM** | 0.622 | 0.400 | 0.429 | 0.414 | 0.620 | 0.251 | 6 / 9 / 8 / 22 |
| 3 | | Persistence | 0.511 | 0.300 | 0.429 | 0.353 | 0.488 | 0.489 | 6 / 14 / 8 / 17 |
| 3 | | Majority (LOW) | 0.689 | — | 0 | 0 | 0.500 | 0.311 | 0 / 0 / 14 / 31 |
| 4 | — | not computable: the year-earlier CPI base month falls after the issue-date cutoff | | | | | | | |

| Lead | LightGBM vs persistence | LightGBM vs climatology | Reliable? |
|---|---|---|---|
| 1 | −0.187 [−0.287, −0.083], 9/3, p 0.146 | −0.155 [−0.260, −0.056], 9/3, p 0.146 | no (sign test) |
| 2 | −0.226 [−0.388, −0.055], 7/3, p 0.344 | −0.090 [−0.192, +0.0001], 5/5, p 1.0 | no |
| 3 | −0.237 [−0.410, −0.065], 7/2, p 0.180 | −0.015 [−0.112, +0.083], 6/3, p 0.508 | no |

- **Furthest reliable lead:** none, for the LightGBM and for FIRI.
- **The > 75% Lead-2 goal:** not demonstrated.

**Objective 4 for the LightGBM** (45 rows; `out/baseline_table.csv`):

| Model | Brier | Δ Brier (LightGBM − baseline) [95% CI] | Established? |
|---|---|---|---|
| LightGBM | 0.178 | — | — |
| I. Persistence | 0.400 | −0.222 [−0.409, −0.037], 6/3 (p 0.25) | no |
| II. PSA-only LR | 0.598 | −0.420 [−0.656, −0.199], 8/1 (p 0.02) | **yes** |
| III. NLP-only LR | 0.235 | −0.057 [−0.122, +0.008] | no |
| IV. Combined LR | 0.646 | −0.467 [−0.670, −0.276], 9/0 (p 0.002) | **yes** |
| Majority | 0.311 | −0.133 [−0.304, +0.021] | no |

The sealed 2026-Q4 and 2027-Q1 forecasts (E68 `sealed/prospective.csv`, E69 `sealed/outlook_forward.csv`) are the first independent test; the 2027-Q1 FIRI values are recorded in §8.

---

## 12. Limitations that affect the thesis conclusions

1. **No provincial or municipal food-insecurity outcome** (CBMS, provincial FIES, caseloads). FIRI cannot be validated, and provincial food-insecurity accuracy cannot be established.
2. **FIRI is HIGH in 88–93% of evaluated rows.** The fixed 0.50 threshold on a level raised by saturated national-economy scores (§6.5) and by regional hunger above 11.3% in every evaluated quarter gives low LOW recall (0.10–0.16).
3. **The news domain is not in FIRI** (3 SUFFICIENT FSSI values in the reference window).
4. **V1 is static** (publication-timing deviation, Amendment 1); the strict-V sensitivity is reported.
5. **SWS hunger is regional,** with ±4–6 point sampling error; the same H1 for all provinces.
6. **Employment and remittances are national;** BSP remittances end 2025-Q4.
7. **Only 9–12 independent quarters per lead;** about 23 effective observations at Lead 2.
8. **All development rows have been examined.** The independent test (2026-Q4 / 2027-Q1) awaits PSA CPI for Oct 2026–Mar 2027 and the SWS 2026-Q4 and 2027-Q1 rounds.
9. **One El Niño episode in 2021–2026,** confounded with disinflation; no dated rainfall or drought archive. C1 is an official status, not a measured impact.
10. **News:** titles only, collected retrospectively, AI-annotated evaluation, thin per province.
11. **Lucena's poverty value** is an unverified substitute.
12. **The pre-2021 exclusion** (user rule) limits every reference window to 2021–2023.

---

## 13. Integration, tests, build and browser results (2026-10-20)

**Integration completed in this run:**

| Area | Change |
|---|---|
| FIRI core | `backend/app/ml/inference/firi.py`: raw indicators, statuses, anchored scores, domains, FIRI, class, shares |
| Thesis mode | `backend/app/ml/inference/thesis_system.py`: `firi_for` (runtime for the issued target, history table for past quarters), `index_rows` (FIRI is the served score; the price score is kept), `firi_drivers` / `contributions` (exact five-group shares), `group_status` / `group_evidence` (card status and indicator text), `firi_text`, `firi_public`, FIRI evaluation in `model_performance`, `fmt_index` |
| Dashboard / API | `backend/app/services/dashboard.py`: FIRI province rows, indicator definition, summary, bars, card status and evidence, region card note, unrounded class with threshold-safe display. `backend/app/api/v1/insights.py`: FIRI explainability note. |
| PDF | `backend/app/services/report.py`: FIRI labels, cover, outlook block, exact-share driver text |
| Runners | `firi_anchors.py`, `firi_evaluate.py`, `firi_posthoc_diagnostic.py`, and the earlier `final_evaluation.py` |
| Approved design | unchanged: no colours, legends, layout or UI elements changed; all explanations use existing text fields |

**Tests and checks:**

| Check | Result |
|---|---|
| Backend full suite (`pytest -q`) | **526 passed, 18 skipped, 0 failed** (`FINAL_Thesis_System/out/backend_full_suite.txt`); `tests/integration/test_thesis_system.py` has 21 tests |
| Backend, committed tree only (another session's uncommitted E46 D-1 hunks swapped out, then restored byte-identical) | see `FINAL_Thesis_System/out/backend_committed_tree_suite.txt` and the commit record |
| Frontend vitest | 46/46 (`FINAL_Thesis_System/out/frontend_checks.txt`; no frontend source changed in this run) |
| Production build (`vite build`) | passed |
| `tsc --noEmit -p tsconfig.app.json` | 6 errors, **pre-existing**, all in `src/data/mockData.ts`; the mock data is not rendered |
| Pre-existing console errors | "Wrong magic number for PMTiles archive" (basemap tiles only) |

**Browser end-to-end** (demo launch config, strict thesis mode, real clock):
- The regional card shows forecast index 0.70, High risk, 5 high / 0 low.
- The regional factor cards follow FIRI (Employment 46%, Climate 23%, Market 23%, Fish 8%; OFW Remittance "insufficient data").
- All five province panels show their FIRI score (Cavite 0.72, Laguna 0.74, Quezon 0.74, Rizal 0.67, Batangas 0.62), "High risk", FIRI bars, and cards whose evidence lists each indicator's value, score and status.
- Every LGU equals the API to 2 decimals and is in rank order:

  | Province | LGUs matched |
  |---|---|
  | Cavite | 23/23 |
  | Laguna | 30/30 |
  | Rizal | 14/14 |
  | Quezon | 41/41 |
  | Batangas | 34/34 |
  | **Total** | **142/142** |

- Back-test quarter Q1 2026: Laguna shows 0.49, Low risk (yellow), "Observed outcome: LOW"; its 30 LGUs match.
- LGU polygons carry the approved colours (Batangas 2027-Q1: Lipa HIGH at 0.56, the other 33 LOW).

---

## 14. Branch and commit

**Push record:** `aipheed-backend-aligned/experiments/FINAL_Thesis_System/out/commit_record.txt`, written after the push.

**Not done (no authorization):**
- merge;
- public deployment;
- change of the production default.

The branch is a tested, reproducible thesis-demo configuration, **not** a live deployment.

**Preview deployment, if authorized later:**
- set `AIPHEED_LEAD2_MODEL=thesis` and `AIPHEED_STRICT_MODEL=1` on the API service;
- point the frontend's `VITE_API_BASE_URL` at it.
