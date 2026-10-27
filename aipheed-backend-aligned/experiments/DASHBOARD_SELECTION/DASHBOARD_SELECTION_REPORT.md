# Which aiPHeed implementation should power the dashboard? Four-candidate audit

**Branch:** `aiPHeed/final-architecture` (local only, not pushed).

**Served throughout:** P0H4. Nothing merged, pushed or deployed. No frozen artefact was overwritten.

**Evidence status.** All 2023–2026 results below are **development evidence**: these quarters shaped earlier designs. **No untouched outcome exists yet.** Prospective seals are listed in §8.

## 1. Candidates, commits and what each actually is

| Candidate | Commit | What it is | Output | Leads |
|---|---|---|---|---|
| **Main** | `main` `0239273` | **Serves FIRI v2** (Dockerfile `AIPHEED_LEAD2_MODEL=thesis`; no Chapter I engine on main). Its FIRI v2 history (`backend/data/thesis/firi2_history.csv`) is **identical** to the current branch's (same commit `2b1f65a`). | 0–1 index, HIGH at 0.50, "a proxy composite, not a probability" (`thesis_system.py`) | Lead 2 only (target = origin + 2) |
| **FIRI v2** | `firi.score_v2` (same code and history on main and current) | Weighted mean of 6 domain scores (A, V, C, E, N, H); indicator percentiles vs prior history; ≥ 4 domains | index | Lead 2 |
| **P0H4** | served from `aiPHeed/lead2-optimization` `a1ce8ce`; this branch `001eb0c` | **Hybrid:** one LightGBM (all leads, 12 families) for the price condition × a closed-form SWS hunger probability | probability of T43c | 1–15 (reliable: 1) |
| **S3** | LEAD2_ONE_MODEL `40ea4d9` = FINAL_ARCHITECTURE candidate C | **One LightGBM** on T43c, all leads, 12 families + hunger inputs; structural price baseline as `init_score` | probability of T43c | 1–15 (reliable: 1) |

**Consequence.** **Main and FIRI v2 give the same forecasts.** They differ only in surrounding code: the current branch adds the Chapter I engine, `final_engine` and experiment APIs. **The news-processing code `backend/app/news/*` is byte-identical on main and current** (`git diff main HEAD -- backend/app/news` is empty).

**Working tree:**
- untracked E114 GDELT files, `node_modules/` and `docs/aiPHeed_Complete_System_Guide.docx`, untouched;
- seals `fcc4130d` (UNI-FINAL), `a498b5ef` (P0H4) and the FIRI v2 forecast rows unchanged.

## 2. Authoritative objectives and SOP

**Source.** `FINAL_THESIS_OBJECTIVES/sources/chapter1_THESIS2_11_extract.txt` §1.3–1.7.

**Target as written.** SWS quarterly hunger + PSA food prices determine risk (§1.7). Implemented as T43c:
- BL hunger > 11.3 (2021–22 P60) **and**
- province food or gap YoY > its 2021–22 P60.

Verified from raw data (100 labels, 20 hunger quarters). It is a **combined proxy**: one regional hunger value is shared by 5 provinces.

**Achievement levels:** F = fully achieved, P = partial, N = not achieved, n/a = not applicable.

**Evidence levels:**
- I = implemented;
- C = functionally correct (tested);
- E = predictive performance demonstrated by experiment;
- R = real-world validity.

| Objective / SOP (exact requirement, abridged) | Main = FIRI v2 | S3 | P0H4 | Evidence and remaining gap |
|---|---|---|---|---|
| **SOP 1 / H1.** Variables that most predict risk, via SHAP. H1: FSSI and food CPI deviation will *not* be among the strongest. | P (I): exact domain shares of an index, not model attribution | P (I, C): SHAP of the full probability; the price baseline must be added to Market (not yet built) | P (I, C, E): SHAP of the price part. A1 (food CPI projection) 42% of attribution; FSSI near 0. | **H1 partly rejected:** food CPI deviation is the strongest predictor (ablation: Lead-1 Brier +0.05 to +0.08 without it); FSSI is not. |
| **SOP 2 / H2 / Obj 2-V.** Furthest reliable lead by walk-forward | **N.** No Lead-1 history; Lead 2 fails (26/65 = 0.400, below always-LOW 0.738) | F (E): **Lead 1** (R1–R7 + later block) | F (E): **Lead 1** | Development evidence only (§8) |
| **SOP 3 / H3 / Obj 4.** Combined LightGBM vs persistence, 3 logistic variants, 2 single-source LightGBMs | n/a (index) | P (E): beats persistence and LR-COMB/GOV/NLP and LGBM-NLP at Lead 1. **Not** the government-only LightGBM (0.914 vs 0.857; Brier p = .13). | P (E): same; **significantly worse** than the per-lead government-only/CH1 LightGBM at Lead 1 (Brier p = .027) | **H3 not rejected** against LGBM-GOV at Lead 1 |
| **Obj 2 I–IV.** Accuracy, precision/recall, F1, AUC | reported (§3) | reported | reported | – |
| **SOP 4 / H4 / Obj 3.** LGU rankings from validated province forecasts (PSA poverty + density) reflect relative vulnerability | P (I) | P (I) | P (I, C): 142 LGUs, labelled as a priority ranking | **No municipal outcome;** the DA evaluator post-survey is not yet run |
| **Obj 1.** Two-tier XLM-R + BERTopic → bias-corrected FSSI and latent patterns | P (I) | P (I) | P (I) | Runs. Independent review: v3 relevance precision 0.63, recall 0.22 (§5). FSSI on 17% of Lead-2 rows. No forecast gain shown. |
| **SOP 5 / H5 / Obj 5.** Dashboard, ISO/IEC 25010 evaluation by DA IV-A (SOP text also names DEPDev; you removed DEPDev on 10-10); FNRI NNS face validity | P (I) | P (I): not served | P (I, C): served | **ISO evaluation not yet conducted.** NNS face validity: regional 19.1% (2023), provinces 2021 only (`E87_Outcome_Gap`); not a formal check |

## 3. Matched evaluation

**Script:** `runner/compare.py` → `out/comparison.json`, `out/quarter_table_lead*.csv`.

**Rows:** Lead 1 = 70 rows, 14 target quarters, 17 HIGH. Lead 2 = 65 rows, 13 quarters, 17 HIGH. 90% CIs from a cluster bootstrap by quarter.

### Lead 1

| Model | Accuracy | Bal | Precision | Recall | F1 | FN / FP | Brier | AUC | Onsets | Pre / post 2025-Q2 | LOQO min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **S3** | **60/70 = 0.857** [0.77, 0.93] | 0.786 | 0.73 | 11/17 | 0.69 | 6 / 4 | **0.112** | 0.83 | 4/10 | 0.85 / 0.87 | 0.85 |
| **P0H4** | 59/70 = 0.843 [0.76, 0.93] | 0.776 | 0.69 | 11/17 | 0.67 | 6 / 5 | 0.132 | 0.87 | 4/10 | 0.82 / 0.87 | 0.83 |
| Main = FIRI v2 | **not applicable** (no Lead-1 history) | | | | | | | | | | |
| *Reference: CH1-LGBM, per-lead (earlier served)* | 64/70 = 0.914 | 0.883 | 0.82 | 14/17 | 0.82 | 3 / 3 | 0.087 | 0.92 | 7/10 | 0.93 / 0.90 | 0.91 |
| *LGBM-GOV, per-lead (no news)* | 64/70 = 0.914 | 0.883 | 0.82 | 14/17 | 0.82 | 3 / 3 | 0.086 | 0.92 | 7/10 | – | – |
| LR-GOV | 56/70 = 0.800 | 0.688 | 0.62 | 8/17 | 0.53 | 9 / 5 | 0.179 | 0.73 | 3/10 | – | – |
| LR-COMB | 54/70 = 0.771 | 0.629 | 0.55 | 6/17 | 0.43 | 11 / 5 | 0.192 | – | – | – | – |
| LR-NLP | 48/70 = 0.686 | 0.693 | 0.41 | 12/17 | 0.52 | 5 / 17 | 0.212 | – | – | – | – |
| LGBM-NLP | 49/70 = 0.700 | 0.522 | 0.30 | 3/17 | 0.22 | 14 / 7 | 0.214 | – | – | – | – |
| PERSIST-SI | 52/70 = 0.743 | 0.670 | 0.47 | 9/17 | 0.50 | 8 / 10 | 0.257 | – | – | – | – |
| always-LOW | 53/70 = 0.757 | 0.500 | – | 0/17 | – | 17 / 0 | 0.243 | – | – | – | – |

**Brier tests** (cluster bootstrap):

| Comparison | Difference [90% CI] | p |
|---|---|---|
| S3 − P0H4 | −0.020 [−0.060, +0.025] | .43 |
| P0H4 − CH1-LGBM | +0.045 [+0.014, +0.079] | **.027** |
| S3 − CH1-LGBM | +0.025 [−0.002, +0.053] | .13 |

### Lead 2 (65 rows)

| Model | Accuracy | Bal | Recall | FN / FP | Brier | AUC | Onsets | Post 2025-Q2 accuracy |
|---|---|---|---|---|---|---|---|---|
| **P0H4** | **50/65 = 0.769** | 0.635 | 6/17 | 11 / 4 | **0.194** | 0.62 | 0/10 | 0.87 |
| S3 | 48/65 = 0.738 | 0.633 | 7/17 | 10 / 7 | 0.232 | 0.51 | 0/10 | 0.80 |
| **Main = FIRI v2** | **26/65 = 0.400** | 0.518 | 13/17 | 4 / **35** | n/a (index) | 0.52 | 7/10 (by calling almost everything HIGH) | **0.20** |
| always-LOW | 48/65 = 0.738 | 0.500 | 0/17 | 17 / 0 | 0.262 | – | – | – |
| PERSIST-SI | 44/65 = 0.677 | 0.591 | 7/17 | 10 / 11 | 0.323 | – | – | – |

**On the 60 rows where all comparators exist:**
- P0H4 0.750 (Brier 0.21) and S3 0.717 (0.251);
- always-LOW 0.717; CH1-LGBM 0.583; LGBM-GOV 0.700;
- LR-COMB 0.483, LR-GOV 0.567, LR-NLP 0.433, LGBM-NLP 0.400; FIRI v2 0.383.

**No candidate is reliable at Lead 2** (R3, R5, R6 fail for all).

## 4. Generalisation and reliability

| Candidate | Lead-1 stability | Lead 2 |
|---|---|---|
| S3, P0H4 | Similar: thirds ≥ 0.76; LOQO min 0.85 / 0.83; pre/post SWS design change 0.85/0.87 vs 0.82/0.87; one quarter below 0.6 each | Fails at onsets (0/10). Its later-period accuracy reflects sustained hunger after 2025-Q2. |
| FIRI v2 | – | Unstable: post-2025-Q2 accuracy 0.20; 8 quarters below 0.6 |

**Untouched evidence: none.** Generalisation is **inconclusive between S3 and P0H4** (development stability only). FIRI v2 generalises worst.

**Over-prediction / calibration:**
- P0H4 over-predicts Rizal (+0.19 at Lead 1); S3 does not (0.05);
- P0H4 over-predicts the 2025–26 period (+0.16 at Lead 2).

## 5. News and NLP

**Pipelines compared:**
- **v3, the model pipeline** (Main and current; identical code): classifier v2 relevance + XLM-R intensity → FSSI-v3 (N1).
- **The current branch's dashboard feed** (`final_engine.py`, `data/final_engine/news_events.csv`, 1,043 headlines from 2025–26, categories and event/forecast kind).

**Independent review** (`NEWS_ANNOTATION_GUIDE.md`; `out/news_review_*`):
- **Sample:** 126 headlines, stratified (50 v3-relevant by trigger, 40 v3-not-relevant, 36 feed by category), blind to pipeline labels.
- **Reviewer:** **single AI reviewer, headlines only**, two passes. Pass-to-pass κ = 0.95 (relevance), 0.99 (type). This is **not** independent two-person agreement. Four disagreements were adjudicated by the guide.

| Result (weighted to corpus or feed proportions) | v3 (model input) | Feed (current) |
|---|---|---|
| Precision (food-security relevant) | **0.63** [0.51, 0.76] | 0.53 (unweighted 21/36) |
| Recall | **0.22** [0.15, 0.39] (most relevant articles are rejected) | ≈ 0.55 (12/22 v3-sampled relevant 2025–26 headlines appear in the feed; different corpora, indicative only) |
| F1 | 0.33 | ≈ 0.54 |
| Category correctness | "market" right 1/10 (it sweeps in fuel, gold and coffee prices); climate 10/10; employment 8/10; remittance 8/10; fish kill 7/10 | price 2/6; disaster 3/6; assistance 5/6; jobs 4/6; agri 3/6; shortage 3/6 |
| **Direct food insecurity identified** | 0 | 1 (the only DIRECT headline in the sample, "Fishers … warn of hunger", is a warning, not an event) |

**Reading.**
- **Direct food-insecurity reporting is rare** (1/126). Most "relevant" news is about prices, supply, livelihoods, disasters or aid: indirect risk, not outcomes.
- Neither pipeline should be described as detecting food insecurity.
- **The feed classifies better (F1)** but covers only 2025–26.

**News forecasting contribution** (matched rows):

| Model | With vs without news | Placebo |
|---|---|---|
| Main / FIRI v2 | News domain present on **4 of 65** Lead-2 rows; identical accuracy without it | shuffled p = .45 |
| P0 (UNI-FINAL / P0H4 price model) | Lead-1 Brier −0.012 (Holm .86) | p = .05 at Lead 1, .95 at Lead 2 |
| S3 | *worse* with news (+0.0009, Holm .60) | p = .65 |
| CH1-LGBM vs LGBM-GOV | identical (0.914 / 0.914) | – |

**News improves forecasts in no candidate.** It is descriptive context only. Coverage (17% of Lead-2 rows) limits the test.

**Timing.** v3 admits articles published (PH time) before the issue date (`pipeline_v3.asof`), de-duplicates syndicated copies within a window, and never uses a later update time. The future-perturbation audits shuffled all news after the issue date with identical forecasts (UNI, LEAD2, LEAD2_ONE_MODEL, FINAL_ARCHITECTURE). BERTopic is not a model input in these candidates.

## 6. Indicator families (summary of matched ablations)

| Finding | Evidence |
|---|---|
| **Market (A1) is essential** | Single model: removing it fully costs Lead-1 Brier +0.083 [0.044, 0.128]. Served model: +0.052. Partly structural (the target uses the same CPI). |
| **Climate:** no demonstrated value | One El Niño episode in the window; the improved representation failed its placebo (p = .55) |
| **E1, E2:** none or noise | E1 is a calendar-time confound |
| **V1:** a province identifier | static |
| **N1:** none | 17% coverage |
| **H1:** decisive in P0H4; joint in S3 | removing all hunger information from P0H4: Lead-1 accuracy 0.843 → 0.686 |
| **FIRI v2:** domains are equal-weight composites | not learned from outcomes; their weights are not predictive evidence |

## 7. Explanations

| Candidate | What the bars are | Reproducible? | Credibility |
|---|---|---|---|
| Main / FIRI v2 | Exact shares of a weighted index (index − 0.5 split by domain) | Yes (arithmetic) | Faithful to the **index**, but the index does not forecast the outcome (§3) |
| P0H4 | SHAP of the LightGBM price part, 8 groups (no hidden "other"); notes give the hunger condition and its value; "relative model influence" | Yes (exported with the forecast; tests) | **Best currently available**, with the stated limits |
| S3 | Tree SHAP of the full probability | Yes | **Incomplete until the structural price baseline is added to Market** (its tree SHAP alone puts Market at ~2%, but removing price information costs +0.083 Brier) |

**LGU outputs** are labelled as priority rankings in all three.

## 8. Verdicts

| | Verdict |
|---|---|
| **A. Best overall dashboard candidate** | **P0H4** (keep served). It has the best Lead-2 probabilities, is reliable at Lead 1, has the corrected explanations, and is sealed. |
| **B. Best at the thesis objectives and SOP** | **S3** for methodology alignment: one unified LightGBM (SOP 2/3 wording) at equivalent Lead-1 performance. **Neither fully meets the SOP:** H3 is not rejected against the government-only LightGBM; SOP 4/5 (LGU validity, ISO evaluation) are not yet evaluated. |
| **C. Best generalisation** | **Inconclusive** between S3 and P0H4: development stability only, no untouched outcomes. FIRI v2 is clearly worst. |
| **D. Most reliable Lead-1 model** | **S3 ≈ P0H4** (0.857 vs 0.843, same 11/17 recall; Brier difference n.s.). The earlier *per-lead* CH1-LGBM (0.914) is better but violates the one-model requirement. |
| **E. Most reliable Lead-2 model** | **None meets the reliability rule.** P0H4 has the best Lead-2 accuracy (0.769) and Brier (0.194) as an experimental forecast. |
| **F. Best HIGH-risk detection** | Lead 1: S3 = P0H4 (11/17, onsets 4/10; S3 has 1 fewer false alarm). FIRI's high recall comes with 35/48 false alarms and has no value. |
| **G. Best probability quality** | Lead 1: S3 (0.112); Leads 2–3: P0H4 (0.194, 0.183). FIRI v2 is not a probability. |
| **H. Best news classifier** | **The current branch's feed** by F1 on the independent review (≈ 0.54 vs 0.33). Single AI reviewer, headlines only; neither detects direct food insecurity. |
| **I. Best news forecasting contribution** | **None demonstrated** in any candidate |
| **J. Best methodology for the defense** | **S3:** one unified LightGBM, documented baseline, all leakage audits, replay, sealed (`cdf001f2`). Its weaker longer-lead probabilities must be disclosed. |
| **K. Best explanation** | **P0H4's corrected relative-influence bars** for the current dashboard. S3's need the baseline attribution before use. |

**L. Deployment:**
- **Now:** **P0H4 stays served.** S3 stays experimental (seal `cdf001f2`, issued 2026-10-01, Leads 1–15).
- **Not as the dashboard forecast:** **Main/FIRI v2.** It may be shown only as a descriptive indicator index, never as a forecast.
- **To replace P0H4 with S3, all of these are needed:**
  1. your approval of the one-model requirement as binding for the dashboard;
  2. the Market-baseline attribution implemented and tested;
  3. prospective scoring of seals `a498b5ef` (P0H4) and `cdf001f2` (S3) on SWS 2026-Q4 (about Jan 2027) and 2027-Q1, with the comparison rule fixed beforehand.

**If the one-model requirement is binding for the thesis now,** S3 is the defensible choice (equivalent at Lead 1, the only reliable horizon).

## 9. Limitations and next steps

- **Data:** 13–14 independent hunger outcomes; 2 hunger onsets; a shared regional outcome; no provincial or municipal food-insecurity outcome; utilization not measured.
- **News review:** a single AI reviewer on headlines. A human second annotator would turn κ into real inter-annotator agreement (the guide and blind file are ready).
- **Thesis evaluations not yet run:** the ISO/IEC 25010 DA evaluation and the LGU-ranking post-survey (SOP 4/5).

## 10. Reproduce

From `aipheed-backend-aligned/experiments/DASHBOARD_SELECTION/runner`, using `C:/Users/admin/aipheed/backend/venv/Scripts/python.exe`:

| Step | Command | Output |
|---|---|---|
| Matched comparison | `python compare.py` | `out/comparison.json`, quarter tables |
| Lead-1 tests, Lead 2 on 60 rows, FIRI news | `python extras.py` | `out/extras.json` |
| S3 prospective seal (refuses to overwrite) | `python seal_s3.py` | `out/sealed_prospective_S3.csv` |
| News sample (blind + key) | from `backend/`: `python ../aipheed-backend-aligned/experiments/DASHBOARD_SELECTION/runner/news_sample.py` | `out/news_review_*` |

**Inputs:** `FINAL_ARCHITECTURE/out/predictions.csv` (S3 = `C_p`, P0H4 = `P0H4_p3`), `FINAL_VERIFICATION/out/horizon_predictions_lead{1,2}.csv` (comparators), `backend/data/thesis/firi2_history.csv` (FIRI v2), `backend/data/final_engine/news_events.csv` (feed), `app.news.pipeline_v3.corpus()` (v3).
