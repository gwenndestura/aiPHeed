# PAPER_ALIGNED, Step 0: what the paper requires, where it contradicts itself, and what was tried before

**Source:** `C:\Users\User\Downloads\THESIS 2 (18).pdf` (73 pages), read 2026-11-03. The text was extracted with pypdf
(layout mode). The printed page numbers equal the PDF page numbers, and "p." below means that page. Figures (pseudocode
images) could not be read as text; where a requirement exists only inside a figure, it is marked "(figure)".

## A. Requirements, with pages

### A1. Research questions (§1.3, pp. 10–11)

| ID | Wording (short quote) | p. |
|---|---|---|
| RQ1 | "What variables most significantly predict food insecurity risk across the provinces of CALABARZON, as identified through SHAP feature attribution?" | 10 |
| RQ2 | "What is the furthest lead time at which aiPHeed can reliably forecast province-level food insecurity risk across CALABARZON?" | 10 |
| RQ3 | LightGBM combining NLP news signals and government indicators "compare against **six** baseline approaches": naive persistence; three logistic regressions (combined, government-only, NLP-only); two LightGBM ablations, one per data source | 10 |
| RQ4 | "How effectively do the city- and municipality-level … risk rankings derived from province-level forecasts reflect relative vulnerability across CALABARZON?" | 10 |
| RQ5 | "How do DA Region IV-A personnel, as system evaluators, and **DEPDev Region IV-A personnel, as usability evaluators**, assess aiPHeed under the ISO/IEC 25010 … in terms of functional accuracy and ease of use respectively?" | 11 |

### A2. Null hypotheses (§1.4, pp. 11–12)

The dependent variable is "the binary food insecurity risk classification, either high or low, **of a CALABARZON
province in a given quarter**" (p. 11).

| ID | Null hypothesis (short) | p. |
|---|---|---|
| H1 | FSSI and food CPI deviation will **not** be among the strongest predictors under SHAP | 11 |
| H2 | aiPHeed will **not** reliably classify a province high or low across multiple lead times | 11 |
| H3 | The combined LightGBM will **not** outperform the **six** comparators | 11 |
| H4 | The LGU rankings will **not** be consistent with DA Region IV-A evaluators' assessments (aiPHeed Post-Survey Questionnaire) | 12 |
| H5 | aiPHeed will **not** receive favorable functional suitability, accuracy and usability ratings from **DA Region IV-A** evaluators under ISO/IEC 25010 | 12 |

### A3. Specific objectives (§1.5.2, pp. 12–13)

| Obj | Requirement | p. |
|---|---|---|
| 1 | Two-tier pipeline: zero-shot XLM-RoBERTa Filipino-English sentiment and BERTopic, producing the **bias-corrected FSSI** and **latent risk patterns per province-quarter** | 12 |
| 2 I–IV | Accuracy, precision and recall, F1, AUC-ROC of **province-level** high/low classifications | 12–13 |
| 2 V | Walk-forward expanding-window CV across lead times to find **the furthest reliable horizon** | 13 |
| 3 | Municipal and city rankings from **validated province-level forecasts**, weighted by PSA poverty incidence and population density | 13 |
| 4 | Compare the proposed LightGBM with **four** baselines: naive persistence, PSA-only, NLP-only, logistic regression | 13 |
| 5 | Public geospatial dashboard with **forecast maps and early-warning alerts**; ISO/IEC 25010 evaluation with DA Region IV-A evaluators; validation against **DOST-FNRI NNS 2019 and 2023** CALABARZON prevalence (face validity) | 13 |

### A4. Scope (§1.7, pp. 14–15)

- Covers **142 cities and municipalities** in Region IV-A (Cavite, Laguna, Batangas, Rizal, Quezon): an interactive map
  of risk levels and rankings, plus the factors influencing each forecast (pp. 14–15).
- A **downloadable PDF** for each province and for CALABARZON: forecast scores, SHAP drivers, performance metrics,
  data-sufficiency disclosures (p. 15).
- **News 2021 to 2025.** Data from PSA, DOST-FNRI, SWS, PAGASA, PhilRice, BSP and DOE (p. 15).
- "**SWS quarterly hunger data and PSA food price data will be used to determine food insecurity risk**"; DOST-FNRI as
  regional reference (p. 15).
- LGU estimates "will not represent official food insecurity classifications"; limited-coverage areas are disclosed
  (p. 15).
- "Evaluation will involve **50 DA Region IV-A evaluators** using the ISO/IEC 25010 software quality standard" (p. 15).

### A5. Data and preprocessing (§3.3, pp. 31–37)

| Item | Requirement | p. |
|---|---|---|
| News corpus | RSS, Google News RSS, GDELT DOC 2.0; **Jan 2020–Dec 2025**; "17,791 unique articles" | 31 |
| Indicators | PSA (food CPI, unemployment, rice retail, poverty), BSP (OFW remittances, USD/PHP), DOE (weekly fuel, quarterly), PAGASA (typhoons, rainfall anomaly, ENSO, drought alert), PhilRice Ricelytics (2022–2025), SWS hunger, PSA NRP (vegetable, fish, livestock); "about 2,732" datasets; province-quarter parquet | 32–33 |
| Text | HTML strip, title + summary, truncated to **512** characters | 33 |
| Geocoding | 3-stage PSGC: 92-entry alias table, substring, fuzzy at token_set_ratio 85; unmatched articles excluded | 33–34 |
| Bias weight | Eq. 1: w = log(1 + median articles) / log(1 + articles(p,t)); **LIMITED_SIGNAL** if < 5 articles, propagated to all 142 LGU outputs | 34–35, 49–50 |
| FSSI | Eq. 2: FSSI = w × mean article score; plus FSSI_lag1, FSSI_lag2, FSSI_accel (4 columns) | 35, 50–51 |
| Triggers | Regex, 5 bilingual categories: **market, climate, employment, ofw_remittance, fish_kill**; proportions 0–1 | 35, 39–41 |
| Government features | YoY of food CPI and remittances; food-minus-headline gap; ENSO −1/0/1; drought binary; lag-1 and acceleration for 7 series (14 columns) | 36 |
| Fusion | **120 rows** (5 provinces × 24 quarters, **2020-Q1..2025-Q4**) × **45 columns**; forward-fill within province, **remaining gaps zero-filled** | 36–37 |

### A6. Algorithms (§3.4, pp. 37–47)

| Algorithm | Requirement | p. |
|---|---|---|
| **1** Zero-shot XLM-R | `joeddav/xlm-roberta-large-xnli`; 10 bilingual HungerGist hypotheses; score = max entailment; drop < 0.30; average per province-quarter; bias-correct; lags | 37–39 |
| **2** Regex triggers | 5 categories, multi-label, proportions per province-quarter, feed SHAP narratives | 39–41 |
| **3** Lead-time discovery | k = 1..8; walk-forward expanding window, gap k, **min training 8 quarters**, one quarter per fold; **default LightGBM**; record accuracy, precision, recall, F1, AUC; **reliable if mean fold accuracy ≥ 0.75**; halt at the first failure; output the Maximum Reliable Lead Time | 41–43 |
| **4** Optuna TPE | **100 trials**, 9 hyperparameters (leaves, depth, learning rate, estimators, min child, subsample, colsample, L1, L2); gap = k*; objective **mean weighted F1** of the walk-forward CV; best set evaluated **once on the last 4 quarters, never seen by Optuna**; target **F1 ≥ 0.75, AUC-ROC ≥ 0.80**; retrain on all data → `lgbm_best.pkl` | 43–45 |
| **5** Disaggregation | 142 LGUs; vulnerability = 0.6 poverty_norm (PSA 2021 SAE) + 0.4 density_norm (**2020 census**), min-max within province; risk = province probability × vulnerability, clamped [0, 1]; rank all 142; **data_sufficiency_flag** and **disaggregation_label** on every row; input = "**validated** province-level LightGBM forecast probabilities" | 45–47 |

### A7. Rules 1–8 (§3.4.1, pp. 48–49)

| Rule | Requirement | p. |
|---|---|---|
| 1 | Retrain each quarter; forecast at the empirically validated lead time; stage all outputs for **mandatory review before publication** | 48 |
| 2 | One LightGBM evaluated across lead times; adopt the furthest reliable lead as the operational horizon | 48 |
| 3 | **No look-ahead bias:** every feature from data available before the forecast period | 48 |
| 4 | Province first; municipal rankings apply PSA weights to **validated** province forecasts only | 48 |
| 5 | LIMITED_SIGNAL badge below the minimum article threshold, propagated to all 142 LGU outputs | 48 |
| 6 | Every forecast has an explicit **horizon label, confidence statement and verification date** | 49 |
| 7 | Alert when a province's forecast **exceeds the rolling historical threshold**; **human confirmation before DSWD 4A is notified** | 49 |
| 8 | Every municipal index carries a **disaggregation_label** (higher uncertainty than province level) | 49 |

### A8. Equations (§3.4.2, pp. 49–55)

| Eq. | Content | p. |
|---|---|---|
| 1 | Spatial bias weight | 49 |
| 2 | FSSI | 50 |
| **3** | stress(p,t) = sws_hunger(t) + 2 × (food_cpi_yoy(p,t) − regional_mean_food_cpi_yoy(t)); y = 1 if stress > median(stress). Table 3.4.2.3: "**global_median** … across **all 120** province-quarter pairs; guarantees a 50/50 class balance". sws_hunger(t) = "SWS quarterly hunger prevalence **at regional level**". | 51–52 |
| **4** | Secondary robustness check: y(p,t+1) = 1 if CPI(p,t+1) > CPI̅(p,24) + σ_p for two consecutive quarters (no variable legend given) | 51 |
| 5 | Forecast function: ŷ(p,t+h) = F[FSSI_t, FSSI_t−1, FSSI_t−2, ΔFSSI_t, trigger_t, CPI_dev_t, unemp_t, rice_change_t]; **CPI_dev = food CPI deviation from the rolling provincial mean** | 52–53 |
| 6 | Disaggregation (as Algorithm 5) | 54 |
| 7 | SHAP TreeExplainer: f(X) = φ0 + Σ φj | 55 |

Also: §3.4.3 (p. 55): "F … the 45 candidate features **before selection**, d and M for the **12 features actually used**".
§3.4.4 (pp. 57–58): the 75% / F1 0.75 / AUC 0.80 thresholds; "Any lead time or model configuration that does not
clear these thresholds **will not be published** to the dashboard".

### A9. Operational framework, use cases and respondents (§3.5–3.7, pp. 58–68)

| Item | Requirement | p. |
|---|---|---|
| Schedule | APScheduler, 02:00 PHT on the **15th** of Jan, Apr, Jul and Oct | 59 |
| Relevance | Core food score ≥ 0.30 **and** margin over the non-food hypotheses ≥ 0.20; an article enters the FSSI set **only after a reviewer has read it** | 59, 65 |
| Panel | **9 news features** + food CPI deviation, unemployment, rice price change → **135-row** panel | 59 |
| Model in service | Optuna-tuned LightGBM; decision cutoff from walk-forward out-of-fold scores; tested once on the last 4 quarters; a "**candidate blend**" replaces the served model only if F1 ≥ 0.75 and AUC ≥ 0.80, otherwise the current model stays | 59–60, 65 |
| Review | Each province-quarter seeded as **STAGED**; DA administrator approves or rejects with a logged reason; a rejected forecast is withheld from map, rankings and regional mean | 60, 66 |
| State diagram | PENDING → STAGED → PUBLISHED (visible) or back to PENDING; ARCHIVED next quarter. Alerts: STAGED → confirmed (shown) or dismissed (kept for audit). "No forecasts or warnings appear on the public dashboard without human decision-making" | 66–67 |
| Actors | DA Administrator (from the 50 DA personnel), Automated Scheduler, User (public) | 61–62 |
| Respondents | **50 DA Region IV-A** personnel, purposive sampling; **single evaluator group** covering functional suitability, accuracy, reliability **and usability** (learnability, operability, interface clarity, accessibility); also "domain expert annotators … to label and verify training data"; one Google Form, the **aiPHeed Post-Survey Questionnaire** (closed, open and Likert items) | 67 |
| Ethics | Informed consent, confidentiality, voluntary participation, non-maleficence, beneficence, transparency, RA 10173 | 68 |

### A10. The Chapter III conceptual framework (§3.2, pp. 29–31)

- Corpus of **6,085** articles; text truncated to **250** characters.
- **371-article** audited CALABARZON set.
- **135 rows × 12 features**, 27 quarters (**2020-Q1..2026-Q3**).
- **Stage 4 model is a blend:** 0.4 × Optuna LightGBM (12 features) + 0.4 × logistic regression on the 3 government features + 0.2 × logistic regression on the climate, fish-kill and OFW triggers; HIGH when the blend ≥ **0.712**.
- Blind holdout **2025-Q4..2026-Q3**.
- 50 DA evaluators.

---

## B. Contradictions inside the paper (each needs your decision)

For each one I give a recommendation. **Nothing is decided until you answer.**

| # | Topic | Statement 1 (p.) | Statement 2 (p.) | My recommendation |
|---|---|---|---|---|
| C1 | **FNRI validation years** | Obj 5: "NNS **2019** and 2023" (13) | Ch 3: "NNS **2021** and NNS 2023" ENNS FIES (51) | Use **NNS 2023** (19.1%, verified). Report 2019 as unusable (HFIAS, different scale, your earlier decision). Ask whether to look for a verified **2021 ENNS** regional FIES figure; it was removed earlier as unverifiable. |
| C2 | **Number of comparators** | Obj 4: **4** baselines (13) | RQ3 and H3: **6** (10, 11) | Run all **6** (they include the 4). Report Obj 4 on its 4 and H3 on all 6. |
| C3 | **Evaluator groups** | RQ5: DA = system evaluators, **DEPDev = usability** evaluators (11) | §1.7, H5, §3.7: **50 DA only**, one group covering usability too (15, 12, 67) | Prepare both instruments as you asked in Step 3. **Ask:** is DEPDev in or out? H5 names DA only. |
| C4 | **Study window** | §1.7: news **2021–2025** (15) | §3.3.1.1: news Jan **2020**–Dec 2025 (31); §3.3.2.6: **120 rows, 2020-Q1..2025-Q4** (36); §3.2 and §3.5: **135 rows, 2020-Q1..2026-Q3** (30, 59); holdout 2025-Q4..2026-Q3 (31) | **Ask.** "2021–2025 + 120 province-quarters" (your task text) equals 24 quarters only if it is 2020-Q1..2025-Q4. 2021-Q1..2025-Q4 is 20 quarters = 100 rows. And 2021–2025 leaves no room for the 2025-Q4..2026-Q3 holdout. |
| C5 | **Feature count** | **45** features (36–37, 42, 44; your task text) | **12** "actually used" after selection (55, 30, 59, 65); Eq. 5 lists 12 | **Ask.** The paper's model is 45 candidates → **selection** → 12. The selection rule is not specified beyond "correlation filtering and SHAP-ranked reduction" (56). |
| C6 | **Model** | One default LightGBM (Alg 3), one Optuna LightGBM (Alg 4), Rule 2 "One LightGBM model" (41–48) | A **blend** 0.4 LGBM + 0.4 LR(gov) + 0.2 LR(triggers), cutoff 0.712 (30, 59, 65) | **Ask.** I recommend the single LightGBM of Algorithms 3–4 (Objectives 2 and 4 name "the proposed LightGBM"), with the blend reported as a secondary result. |
| C7 | **Label threshold vs Rule 3** | Eq. 3: **global median over all 120 pairs** (51–52) | Rule 3: no look-ahead (48) | As you specified: the origin-specific training median is primary, the global median a sensitivity. Note: the global median uses future outcomes, so it makes the label itself leaky. |
| C8 | **CPI deviation definition** | Eq. 3: food CPI YoY minus the **cross-province mean of the same quarter** (51–52) | Eq. 5: food CPI deviation from the **rolling provincial mean** (53) | Label uses Eq. 3 as written. **Ask** which definition the feature CPI_dev uses. I recommend Eq. 5's (rolling provincial mean, past quarters only), so the feature is not the label's own term. |
| C9 | **Relevance rule** | Alg 1: drop < 0.30 only (37–38) | §3.5: ≥ 0.30 **and** margin ≥ 0.20, **and** reviewer-read (59, 65) | Use the §3.5 rule, which is the existing classifier v2 behaviour. **Ask** about "reviewer-read": no reviewer log exists for the corpus. |
| C10 | **Truncation** | **512** characters (33, 37) | **250** characters (30, 65) | Use 512 (Algorithm 1 is the normative algorithm). |
| C11 | **Corpus size** | 17,791 (31) | 6,085 (30); 371 audited (30) | Report what exists (9,667 headlines in the current store). Not a modelling choice. |
| C12 | **Trigger categories** | Alg 2: market, climate, employment, ofw_remittance, fish_kill (35, 39) | Alg 1 hypothesis themes: food supply disruption, economic hardship, climate damage, displacement, OFW remittance loss (37) | Not a true conflict: the two are different layers. Use Algorithm 2's five for triggers. |
| C13 | **Population density year** | 2020 census (45–46, 60) | Vulnerability data "PSA RSSO IV-A (2025)" (46); the backend uses POPCEN **2024** | **Ask.** The paper says 2020. The authorized input table holds 2024. |
| C14 | **Review before publication** | Rule 1: "mandatory review **before publication**" (48); state diagram: only PUBLISHED is visible (66–67) | §3.5 and §3.6: STAGED forecasts "**remain visible** on the dashboard until" approved or rejected (60, 66) | Follow Rule 1 and the state diagram: STAGED is not public. |
| C15 | **Alert recipient** | Rule 7: human confirmation before **DSWD 4A** is notified (49) | Use case: admin confirms before alerts are **displayed on the dashboard** (62, 67) | Do both: confirmation gates display, and DSWD 4A notification is a separate, manual action. No automatic external message. |
| C16 | **Zero-filling** | §3.3.2.6: remaining gaps **zero-filled** (37) | §3.6: gaps "left missing rather than filled with zeros" (65) | Leave missing (p. 65). Zero-filling turns "no data" into "0% inflation", a defect found and removed before (`risk_score_v2.py`). |
| C17 | **Annotators** | §3.7: DA evaluators "label and verify training data" (67) | Eq. 3: the label is a formula, not human annotation (51) | Report that labels are formula-based. Human annotation is not part of the label. |
| C18 | **Eq. 4** | "CPI̅(p,24) + σ_p for two consecutive quarters" (51) | No legend defines CPI̅(p,24) or σ_p | **Ask.** I would read it as: mean and SD of the province's food CPI YoY over the trailing 24 months, computed from data before t. |
| C19 | **Rule 7 threshold** | "rolling historical threshold" (49) | Not defined anywhere | **Ask.** I would propose: the province's forecast probability exceeds the 75th percentile of its own past published forecasts (trailing 8 quarters), fixed in PLAN.md. |
| C20 | **"Validated" forecasts for Obj 3 and Rule 4** | Rankings only from validated forecasts (13, 46, 48) | §3.4.4: unvalidated configurations "will not be published" (57–58) | If no lead passes Algorithm 3, the paper's own rule says **no province forecast and no LGU ranking is published**. The rankings would be produced for the record but marked "not validated". |

---

## C. What was already tried: E99 ran this pipeline (not on this branch)

E99 (commits `37e0f88` protocol, `6da1054` results, branch `origin/e99-chapter3-evaluation`, **not merged into this
branch**) ran **the Chapter III pipeline as written**:
- the Eq. 3 label with the global median;
- the 12 features;
- Algorithm 3;
- Algorithm 4 with the 2025-Q4..2026-Q3 holdout;
- the six comparators on identical folds.

From its `REPORT.md`:

| Result | Value |
|---|---|
| Algorithm 3 at k = 1, default LightGBM | Mean fold accuracy **0.30**; persistence **0.70** → **Maximum Reliable Lead = 0** |
| Algorithm 4 at k = 2 (report-only) | Holdout accuracy 0.45, weighted F1 0.53, AUC 0.61 → **not accepted** |
| H1, H2, H3 | Not rejected (food CPI deviation ranked 3rd in SHAP, best FSSI feature 4th; LightGBM lost to persistence, McNemar p = 0.0003) |
| H4, H5 | Blocked (no evaluator responses) |
| Root cause | One regime switch: the Eq. 3 label is LOW in almost all of 2021–23 and HIGH in almost all of 2024–26. About 19 labelled quarters; 6 folds at k = 1. Models trained on the LOW years keep predicting LOW. |

**What this means for PAPER_ALIGNED.** Running the paper exactly again, on the same data, should be expected to
reproduce E99's failure. Your plan differs in some places:
- the origin-specific median, which is stricter than E99's global median;
- 45 features instead of 12 (if C5 is decided that way);
- 2020-Q1 start (if C4 is decided that way).

None of these addresses the root cause: one regime switch in a short window. I will run it honestly if you want, but
the likely outcome is the same. **Ask:** proceed as specified, or first bring E99's branch results in as the reference
to reproduce?

---

## D. Why the served system stopped using `backend/app/ml/features/label_generator.py`

`label_generator.py` implements Eq. 3 with the **global median over all labelled quarters**. Git history shows:

| Commit | What happened |
|---|---|
| `9ed80c0` | "per-quarter regional rank labeling so AUC is statistically meaningful" |
| `bd28fc8` | "revert: restore global stress threshold + pure F1 objective (best result was F1=0.84/AUC=0.70)" |
| `f354e0e`, `dba1be8` | FIES removed from the label; column renamed `label_stress` ("composite SWS+PSA stress label, no FIES involvement") |
| `0b22d1c` (2026-09-02) | "remove four fabricated data sources and three silent failures": hard-coded "curated" reference tables, including SWS hunger values, contradicted their stated sources |
| E29, decision D9 (`backend/app/ml/features/label_guard.py`, brought onto this branch in `2b1f65a`) | **"The legacy label path is leaky":** labelling HIGH above the median over all labelled quarters makes "every training label depend on test-period outcomes". `generate_labels()` now raises `LeakyLabelError` unless `AIPHEED_ALLOW_LEGACY_LEAKY_LABELS=1`, and outputs made that way "remain LEGACY". |
| `risk_score_v2.py` (S1 candidate) | Documents a second defect: **"label_generator fills a missing CPI value with 0.0, which reads 'no data' as '0% food inflation' and shifts the regional mean."** The replacement uses NaN for missing values, requires all five provinces for the regional mean, and uses a frozen point-in-time threshold (10.843 as of 2023-10-01; 14.345 once all 2021–2025 labels are published). |

After that, the served system moved to:
- the Chapter I combined proxy (T43c: hunger > 11.3% AND a provincial price condition, with frozen 2021–22 thresholds);
- later the P0H4 hybrid.

**So "reuse label_generator.py" (your Step 1) conflicts with its own guard.** Reusing it as-is means the legacy, leaky
path with zero-filled CPI. I recommend:
- reuse its Eq. 3 **formula**, through `risk_score_v2.py`, which is the same Eq. 3 with weight 2;
- missing values stay NaN;
- the threshold is the training-quarter median at each origin, as you specified.

`label_generator.py` itself would be called only to reproduce the paper's global-median sensitivity, under the explicit
opt-in.

---

## E. Data feasibility notes for Step 1 (facts, not decisions)

- **BSP remittances:** automated download returned HTTP 403 (HISTORY_RETRAIN, 2026-11-02). Without a file placed by
  you, E2 / OFW features cannot be built.
- **SWS hunger is regional** (Balance Luzon), one value for all five provinces. Eq. 3 makes provinces differ only
  through the CPI term. Its "sws_hunger(t) … at regional level" (p. 52) says so too.
- **Missing SWS quarters:** 2020-Q1, 2021-Q1, 2022-Q1 and 2025-Q1 have no non-commissioned round. 2025 has two rounds
  in Q2.
- **PSA provincial unemployment** (Eq. 5 `unemp`): the held LFS file is national. Provincial quarterly unemployment
  must be checked before it can be a feature.
- **PhilRice Ricelytics** covers 2022–2025 only (p. 32).
- **Human review:** no log exists of reviewers reading articles (C9) or approving forecasts (C14). Rule 1 can be built
  as a workflow, but past outputs cannot claim review.

---

## F. Questions for you before Step 1

1. **C4 window:** 2020-Q1..2025-Q4 (120 rows, as Eq. 3's legend says), or 2021-Q1..2025-Q4 (100 rows, §1.7), or 2020-Q1..2026-Q3 (135 rows, §3.2)? And where is the 4-quarter holdout?
2. **C5 features:** 45 candidates → selection → 12 (the paper's design), or all 45 into the model?
3. **C6 model:** the single LightGBM (recommended), or the blend as the served candidate?
4. **C8:** the CPI_dev feature as in Eq. 5 (rolling provincial mean; recommended), or as in Eq. 3?
5. **C3:** is DEPDev in scope (RQ5), or 50 DA only (H5, §1.7, §3.7)?
6. **C13:** 2020 census density (paper), or POPCEN 2024 (the authorized input)?
7. **C18 and C19:** approve my readings of Eq. 4 and the Rule 7 threshold, or give yours.
8. **C1:** NNS 2023 only, or should I look for a verified 2021 ENNS regional figure?
9. **Label code:** Eq. 3 through `risk_score_v2.py` (NaN-safe) with `label_generator.py` only for the global-median sensitivity, or `label_generator.py` as-is?
10. **E99:** proceed knowing E99 already ran this pipeline and failed (k* = 0), or first bring its results in as the reference?

Other contradictions (C2, C7, C9–C12, C14–C17, C20) follow my recommendation unless you say otherwise.
