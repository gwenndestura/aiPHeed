# Objective completion audit (Phase 0, read only)

**Written:** 2026-11-03. Nothing was trained, changed, committed or pushed. This folder holds the only new files.

**Authoritative objectives:** `C:\Users\User\Downloads\THESIS 2 (18).pdf` (2026-10-30, 73 pp.), §1.5.2, pp. 12–13,
re-read for this audit.
- `#THESISDEFENDED.pdf` is the older Thesis 1 version (May 2026); its objective text differs and was not used.
- Contradictions inside the paper are listed in `PAPER_ALIGNED/STEP0_REQUIREMENTS.md` §B (C1–C20). They are still
  open where marked "Ask".

## 0. Repository state at the audit

| Item | State (verified) |
|---|---|
| Branch | `aiPHeed/system-fixes`; HEAD `3e15c3e` (NOISE_W results) |
| Uncommitted | `SENIOR_REVIEW/runner/{prospective_lib,seal_next,score_prospective}.py` (Phase C registry expansion, verified in dry runs); `NEW_MODEL/ALLBASE/` (Phase A–C, untracked); an old `.pyc` |
| Main model | C-b (NEWS_V2, team decision pending adviser). Seal `NEWS_V2/sealed_prospective_CB.csv`, SHA-256 `67baec66…1015` (hash re-checked) |
| Prospective ledger | `SENIOR_REVIEW/prospective/SEAL_LEDGER.md`: no seal row; real sealing not active |
| Deployed configuration | `render.yaml`/`Dockerfile`: `AIPHEED_LEAD2_MODEL=thesis`, branch `main`. The **map default is the FIRI v2 food-price-pressure score**; C-b is served only with `AIPHEED_MAP_MODEL=foodinsecurity` (not set in `render.yaml`) |
| Backend tests | 1014 passed, 18 skipped (run during this audit) |

## 1. Objective-by-objective audit

| Objective | Thesis requirement | Current implementation | Evidence | Remaining gap | Required work | Completion test |
|---|---|---|---|---|---|---|
| **1 NLP** | Two-tier pipeline: zero-shot XLM-RoBERTa (Filipino-English) + BERTopic → bias-corrected FSSI and latent risk patterns **per province-quarter** | RSS + GDELT corpus; classifier v2 relevance; real `joeddav/xlm-roberta-large-xnli` scores (verified: all stored scores are NLI, none keyword fallback); FSSI-v3 with Eq. 1 bias weight and LIMITED_SIGNAL status; BERTopic (multilingual MiniLM, UMAP, HDBSCAN) | `OBJECTIVES_COMPLETION/OBJ1_NLP_PIPELINE.md`; `backend/app/news/pipeline_v3.py`; `backend/data/news_v3/` (9,667 headlines, 152 topics, 39.7% outliers); E112 validation: disaster share vs typhoons ρ = 0.81 | (a) FSSI sufficient in only **17%** of province-quarters. (b) BERTopic fitted **once on all quarters**, so it is not issue-date safe and is descriptive only; many topics are place names. (c) No human-labelled check of relevance and geocoding accuracy. (d) News adds **no forecast value** (C-b: 0 calls changed; SHAP 0.0% overall, 15.8% within the news era for REF+news, which lost accuracy). (e) Corpus 9,667 vs the paper's 17,791; titles only vs title + summary | Coverage audit and a labelled validation sample; issue-date-safe BERTopic; a fair news-era test of early-warning value (see roadmap) | Pipeline accuracy measured on a labelled sample (precision/recall of relevance and geocoding); FSSI/topic features issue-date safe; a pre-registered test of predictive or early-warning value reported, whatever the sign |
| **2 Model and reliability** | Accuracy, precision/recall, F1, AUC of **province-level** high/low; walk-forward expanding window → furthest reliable lead (Alg. 3, 75%); Alg. 4 holdout F1 ≥ 0.75, AUC ≥ 0.80 | C-b: LightGBM, walk-forward from 1998-Q3, publication-date cut-offs, Leads 1–8 | `NEWS_V2/RESULTS.md`, `out/results_cb.json`; `ALLBASE/PHASE_A_AUDIT.md`, `PHASE_C_RESULTS.md`. Lead 1/2: acc 0.790, P 0.812, R 0.907, F1 0.857, AUC 0.702/0.704, Brier 0.187/0.184; **MRLT 2** | (a) **AUC 0.70 < 0.80**. (b) R7 fails (2015–2020: 0.571). (c) The forecast is **regional (Balance Luzon)**, not province-level: SWS has no provincial series. (d) Alg. 4 untestable until four 2027 quarters are labelled (about 2028). (e) All 62 quarters are development evidence. (f) 13 rescue attempts are recorded; none improved C-b under fixed rules | One or two genuinely new, pre-registered hypotheses (roadmap R2.1–R2.2); activate the prospective registry; adviser decision on the regional wording (Option C) | MRLT by Alg. 3 (done: 2). Alg. 4 on sealed 2027 quarters. R1–R7 reported. A candidate adopted only under the pre-registered rule |
| **3 Province and LGU outputs** | LGU rankings from **validated** province forecasts, weighted by PSA poverty incidence and population density | Regional P × province poverty factor → 5 province scores; 142 LGUs: 0.6 × poverty_norm + 0.4 × density_norm (min-max within province) × province score; `disaggregation_label` on each row | `NEWS_V2/out/cb_province_2026-10-01.csv`, `cb_lgu_2026-10-01.csv`; `backend/data/foodinsecurity_engine/lgu_vulnerability.csv` (142 rows: Quezon 41, Batangas 34, Laguna 30, Cavite 23, Rizal 14; no missing values) | (a) **Density and poverty are negatively correlated** (Spearman −0.53 across 142 LGUs; −0.45 Cavite, −0.55 Laguna), so the 40% density weight ranks dense, lower-poverty towns highest region-wide (Taytay: poverty 9.8%, first; Quezon towns at 30% rank below). (b) Province score = P × poverty / max(poverty): **not in the paper**, and the most-poor province always equals P. (c) Lucena uses a different source (FIES Table 2a, whole per cent) from the other 141 (SAE 2021). (d) 25 LGUs have SAE CV > 20%. (e) Density year 2024 vs the paper's 2020 (C13). (f) No independent validation; H4 needs DA evaluators. (g) "Validated" province forecasts do not exist (regional; R7 fails) | Formula and provenance audit; weight sensitivity and rank-stability analysis; uncertainty from SAE CVs; H4 ranking task in the questionnaire; adviser decision on the weight direction | Every LGU's value reproduced from source; sensitivity/uncertainty reported; H4 tested with DA responses |
| **4 Baselines** | Proposed LightGBM vs naive persistence, PSA-only, NLP-only, logistic regression (Obj 4: four; RQ3/H3: six incl. two LightGBM ablations) | All six plus always-HIGH and CLIM, stored walk-forward, the same quarters and publication cut-offs; paired Brier, cluster bootstrap, Holm | `NEWS_V2/ALIGNMENT_CB.md` §2; `OBJECTIVES_COMPLETION/OBJ4_H3_COMPARISON.md`; `ALLBASE/PHASE_A_AUDIT.md` §2 (implementations verified); `PHASE_C_RESULTS.md` (42-test family) | The comparison is complete and correct. **Superiority is not established** over the PSA-only and combined logistic regressions (C-b Lead 1 Δ −0.005, needs about 16,000 quarters). Logistic Lead-1 AUC 0.759 > C-b 0.702 | Prospective sealed comparison (built, needs commit authorization); report H3 as not rejected | Done as a comparison. Superiority only from the prospective family (≥ 20 quarters per lead, about 2032) |
| **5 Dashboard, ISO/IEC 25010, FNRI** | Public geospatial dashboard with forecast maps and early-warning alerts; ISO/IEC 25010 with **50 DA Region IV-A** evaluators; face validity vs DOST-FNRI NNS **2019 and 2023** | React dashboard; FastAPI; review workflow PENDING → STAGED → PUBLISHED (`backend/app/services/review.py`); staged alert candidates (Rule 7); PDF report; FNRI 2023 regional FIES 19.1% verified | `backend/data/e22/nns_fies_verified.json`; `frontend/meeting-materials/aiPHeed_PostTesting_Questionnaire_Draft.docx` | (a) **The deployed default does not serve the main model**: the map shows the FIRI v2 food-price score. (b) **Hardcoded, inconsistent frontend content** (below). (c) The questionnaire draft targets **DOST staff and the general public (~30)**, not 50 DA personnel; it covers only functionality and usability, not all 25010 characteristics; no reliability analysis plan. (d) **No 2019 CALABARZON FIES figure exists** in DOST-FNRI publications (rolling ENNS sample); only 2023 regional plus 2021 Batangas and Cavite. (e) No responses collected. (f) Deployment needs authorization | Served-model alignment (frontend/API changes need your approval); a new ISO/IEC 25010 instrument for 50 DA evaluators with H4 items; an analysis plan; the FNRI face-validity method | Dashboard shows exactly the served model; the instrument approved; 50 valid responses analysed (α, descriptives); FNRI comparison reported with construct caveats |

### Frontend content that does not match the main model (Objective 5)

| File | Content | Problem |
|---|---|---|
| `frontend/src/pages/Landing.tsx:347–355` | Hardcoded Brier table: served LightGBM 0.132, persistence 0.257, government-only LightGBM 0.086 | From an earlier FIRI evaluation ("70 province-quarters"); not C-b's numbers (C-b 0.187; persistence 0.339) |
| `Landing.tsx:228` | "gives the chance that the province's food prices rise unusually fast" | Describes the FIRI price model, not the food-insecurity model |
| `frontend/src/components/AboutModal.tsx:75, 178` | "One LightGBM model using all 12 indicator families"; "risk = hunger condition × food-price condition" | The FIRI / P0H4 description |
| `frontend/src/components/RegionSidebar.tsx:154–159` | "LightGBM + SMOTE + Optuna (100 trials, 5-fold CV)", F1 0.82, ROC-AUC 0.87, **SUS 78** | Unsupported numbers; no SUS survey exists. The component is not imported anywhere (dead code), but it is in the repository |

## 2. Status per objective

| Objective | Status | One-line reason |
|---|---|---|
| 1 NLP | **Partially achieved** | Pipeline built and real; coverage thin, BERTopic not issue-date safe, accuracy unmeasured, no measured predictive value |
| 2 Model and reliability | **Partially achieved** | Metrics and MRLT 2 measured; AUC below target, R7 fails, regional not provincial; Alg. 4 blocked until 2028 |
| 3 Province and LGU | **Implemented, not validated** | 5 + 142 outputs exist and are labelled; weighting direction questionable; no validation; depends on "validated" province forecasts that the data cannot give |
| 4 Baselines | **Partially achieved** | Fair, complete comparison done; superiority over the logistic regressions not established (power) |
| 5 Dashboard / ISO / FNRI | **Blocked by external dependency, and implemented, not validated** | Respondents and deployment authorization needed; served default and frontend text do not match the main model; 2019 FNRI figure does not exist |

**No objective is "Achieved with sufficient evidence" today.** Objective 4's comparison itself is complete. What is
missing is the superiority the proposal hypothesised (H3), and H3 being "not rejected" is a valid scientific answer.
