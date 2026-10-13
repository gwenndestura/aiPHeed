# E24v2 Final Report: making aiPHeed's forecasting reliable, useful and accurate

**Date:** 2026-10-14.

**Folder:** `aipheed-backend-aligned/experiments/2026-10-14_E24v2_Reliable_Forecasting/`. E23 and E24 are preserved; their hash lists were verified with 0 differences.

**Isolation:**

- `backend_dev/` and `dashboard_dev/` are isolated copies.
- `backend/`, `frontend/`, E17 and E18 are unchanged.
- Nothing was committed, pushed, merged or deployed.

**Sources:**

- **Chapter I only**: the thesis PDF SHA-256 `88dd0b62…` was re-verified; the extraction in `thesis_source/` is identical to E23's.
- Authorized data only, plus **public pre-2026 PSA tables acquired in this experiment** (basis in `DATA_ACQUISITION_REGISTER.md`; please confirm, checklist A6).
- No 2026-H2 outcome, 2026 news or SWS web page was opened.

## Bottom line

**The forecasting goal is NOT met.** E24v2 solved the parts of the problem that data allowed. It also built the machinery that can settle the rest.

**What is now demonstrated on quarters no experiment had seen:**

- The **provincial part** of the approved label (relative food inflation) can be forecast better than persistence.
- The evidence is a frozen, pre-registered test on **94 unseen quarters (1997–2020)**.
- Lead 1: accuracy **0.713 vs 0.617**, Brier **0.186 vs 0.240** (calibrated persistence). All four confirmatory hypotheses hold after Holm correction, in both halves of the period.
- Reliable lead time: **up to 5 quarters** under the E23 rule, and **2 quarters** under a stricter rule.

**What is still not demonstrated:**

- The **approved composite forecast (T1)** is not shown to beat persistence on unseen quarters.
- On the 8 development quarters, the new forecaster (PCF) scores **0.900** vs persistence **0.875** and always-HIGH **0.925**: one more correct row, p = 0.50.
- **Why:** T1's label changes are driven by **regional SWS hunger movements**. These are real (not survey noise) and 2–3 quarters ahead of the newest published round. The authorized 2021–2025 history (20 rounds) is too short to learn them.
- **How it can be settled:**
  - **Two blind prospective seals** (2026-Q3, 2026-Q4, 2027-Q1) now exist, made before any of those outcomes was opened;
  - a **pre-registered T1 back-cast** is ready to run the moment you supply SWS 1998–2020 history.

## Answers to the required questions (Section 10 of the task)

| Question | Answer | Evidence |
|---|---|---|
| **Classification accuracy > 75%?** | **Approved target T1:** 0.900 on development rows (8 quarters, 37 HIGH / 3 LOW). Always-HIGH reaches 0.925 on the same rows, so accuracy alone is uninformative. **Provincial price pressure (exploratory T2):** 0.836 on development rows, but **0.713 on 94 unseen quarters, below 75%**. | `BASELINE_COMPARISON.csv` |
| **Better than persistence and the strongest baseline, on identical rows?** | **T1: no** (C2 not met: +0.025, p = 0.50). Its Brier beats calibrated persistence (0.104 vs 0.162, p = 0.016), but on development rows only. **T2 component: yes, on unseen quarters** (accuracy p_Holm = 0.0006; Brier p_Holm < 0.0001 vs calibrated persistence). | `runs/DEV_…/results_dev.json`, `runs/BX_…/results_BX.json` |
| **Robust across independent quarters; generalizes to unseen quarters?** | **T1: not assessable yet**; the prospective seals are pending your authorization of outcomes. **T2 component: yes**, on 94 quarters never examined, with the same sign in 1997–2008 and 2009–2020. | Seals; HB1–HB4 |
| **Value beyond carrying forward the last published label?** | **T1: not demonstrated.** It anticipated 1 of 5 label changes with 0 new errors (C5 met), which is not significant. **T2 component: yes**: the nowcast uses CPI months already published at the origin. | `PREDICTIONS_BY_QUARTER.csv` |
| **A lead time meeting the reliability requirements?** | **T1: none**: no lead has ≥ 5 LOW test rows, so none is evaluable. **T2 component:** leads 1–5 (E23 rule), 1–2 (stricter rule). | `results_BX.json` → `lead_time` |
| **Provincial forecasts defensible, rather than a repeated regional value?** | **Only as relative food-price pressure.** 65% of the label is the shared regional SWS value. The label's provincial ordering does **not** follow PSA-measured provincial poverty (n = 5, descriptive: Spearman −0.67). Measured provincial subsistence incidence overlaps within CIs in 2023. | `runs/provincial_validity.json` |
| **LGU rankings supported by LGU-level data?** | **No, for 126 of 142.** Without municipal poverty, their within-province order is density only. Density runs **opposite** to poverty where both are known (ρ = −0.76). The ranking is computed correctly and labelled honestly, but it is not a vulnerability ranking for those LGUs. | `LGU_RANKING_VALIDATION.csv`, `runs/lgu_analysis.json` |
| **Correct cutoff, authorization and versioning rules in the pipeline?** | **Yes** (tested). The live 2027-Q1 cycle is **INSUFFICIENT_DATA** with every missing input named. A replay of the 2026-Q3 cycle on real authorized inputs reproduces the research seal to 1e-12. | `QUARTERLY_PIPELINE_AUDIT.md` |
| **Consistent and reproducible?** | **Yes.** API, dashboard and PDF share one record. Development re-run: max diff 0.0. Seals recompute byte-identically. Back-cast re-run: see `TEST_RESULTS.md`. 68 Python + 21 frontend tests pass. | `TEST_RESULTS.md` |

**→ Forecasting goal: NOT MET.** For T1, C2 and C6 are not met and C9 is not assessable. Meeting C1, C3, C4 and C5 on development rows is not enough.

## Results by Chapter I objective, SOP question and hypothesis (exact wording)

### General Objective

> "To develop, validate, and deploy aiPHeed: A Geospatial Food Insecurity Forecasting System for DA Region IV-A Using NLP and Machine Learning."

| Part | Status |
|---|---|
| **Developed** | Isolated copy, working end to end |
| **Validated** | Partly: the provincial component is validated on unseen quarters; the composite is not |
| **Deployed** | Not deployed: no model qualifies, and deployment needs your approval |

### Specific objectives

| # | Exact objective (abridged only where marked …) | Status | Evidence |
|---|---|---|---|
| 1 | "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | **Implemented (E23/E24, unchanged).** E24v2 finds no predictive value in the news signals, so its forecaster uses none. News is shown as context only. | E24 `QUARTERLY_PIPELINE_AUDIT.md`; ablations |
| 2 | "To evaluate the performance of the proposed LightGBM forecasting model using … Accuracy … Precision and Recall … F1-Score … AUC-ROC … Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | **All metrics computed**, for every model, lead 1–8, on identical rows (plus balanced accuracy and Brier). **Furthest reliable horizon for the approved target: none established.** | `BASELINE_COMPARISON.csv` |
| 3 | "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | **Produced for all 142** (approved formula, deterministic ties, missing ≠ zero). **Not from *validated* forecasts**; 126 LGUs lack PSA municipal poverty. The density-vs-poverty conflict is documented (adviser decision B9). | `LGU_RANKING_VALIDATION.csv` |
| 4 | "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | **Done** (E23/E24 rows, re-used from seals). The proposed LightGBM (0.825) **does not** beat persistence (0.875). E24v2 adds calibrated persistence as a stricter baseline. | `BASELINE_COMPARISON.csv` |
| 5 | "To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor." | **Dashboard improved** (dev copy, not deployed). It shows probability, interval, signal, component split, evidence status, measured PSA provincial values, seals and caveats. **ISO 25010 evaluation awaits the 50 DA Region IV-A evaluators.** NNS 2023 regional figure verified (E23); NNS 2019 not verifiable. | `dashboard_dev/`, `instruments/` |

### Statement of the Problem

| SOP | Exact question | Answer |
|---|---|---|
| 1 | "What variables most significantly predict food insecurity risk across the provinces of CALABARZON, as identified through SHAP feature attribution?" | **Descriptive only.** In the proposed LightGBM, price-level features dominate SHAP, and FSSI ranks about 7th of 44 (E23/E24). In E24v2's PCF, the contribution split is exact: the **regional SWS hunger level** sets the level for all provinces, and **provincial food CPI deviation** is the only source of between-province differences. No predictor was shown to anticipate label changes. |
| 2 | "What is the furthest lead time at which aiPHeed can reliably forecast province-level food insecurity risk across CALABARZON?" | **None for the approved risk label** (not evaluable: ≤ 3 LOW rows at every lead). For the provincial price-pressure component: 5 quarters (E23 rule) or 2 quarters (strict rule), on unseen quarters. |
| 3 | "How does the LightGBM model combining NLP-derived news signals and government statistical indicators compare against six baseline approaches, naive persistence, three logistic regression variants (combined features, government indicators only, and NLP features only), and two LightGBM ablation variants trained on each data source separately, in classifying provincial food insecurity risk?" | **It does not outperform them.** At lead 1 it scores 0.825, below persistence (0.875), on the identical 40 rows. The H3 null is not rejected (E23/E24 tests on the sealed predictions). |
| 4 | "How effectively do the city- and municipality-level food insecurity risk rankings derived from province-level forecasts reflect relative vulnerability across CALABARZON?" | **Limited for 126 of 142 LGUs**: their order reflects density, which is inversely related to poverty. **Final answer needs** the PSA SAE workbook and the DA evaluators' assessments (H4). |
| 5 | "How do DA Region IV-A personnel, as system evaluators, […] assess aiPHeed under the ISO/IEC 25010 software quality model, in terms of functional accuracy and ease of use respectively?" | **Awaiting genuine responses** from the 50 DA Region IV-A evaluators. Nothing is simulated. |

### Hypotheses (null hypotheses, exact wording)

| H | Exact null hypothesis | Decision |
|---|---|---|
| H1 | "The Food Stress Sentiment Index (FSSI) and food CPI deviation will not be among the strongest predictors of food insecurity risk in CALABARZON when examined through SHAP feature attribution." | **Not testable** under the frozen rule (no evaluable lead). Descriptively, FSSI is not among the strongest. Food CPI deviation is the only provincial term of the label, and its forecast is validated on unseen quarters. That validation concerns the label's construction, not a SHAP ranking. |
| H2 | "aiPHeed will not reliably classify whether a CALABARZON province is at high or low food insecurity risk across multiple forward-looking lead times." | **Not rejected.** No lead is evaluable on the approved label. The exploratory price-pressure component is reliable at leads 1–5, but that is not the approved high/low risk classification. |
| H3 | "The LightGBM model that combines news signals and government data will not outperform the six comparison models, naive persistence, three logistic regression variants (news-only, government data-only, and combined), and two LightGBM variants trained on only one data source at a time, in classifying provincial food insecurity risk across CALABARZON." | **Not rejected** (E23/E24; unchanged). |
| H4 | "The vulnerability-weighted spatial disaggregation of province-level forecasts will not produce municipal and city risk rankings that are consistent with DA Region IV-A evaluators' assessments of relative food insecurity vulnerability across CALABARZON, as evaluated through the aiPHeed Post-Survey Questionnaire." | **Awaiting participant data** (the 50 DA Region IV-A evaluators) |
| H5 | "aiPHeed will not receive favorable functional suitability, accuracy, and usability ratings from DA Region IV-A evaluators under the ISO/IEC 25010 software quality model." | **Awaiting participant data** |

## What E24v2 changed, and the evidence for each change

### 1. Diagnosis

**Noise ceiling** (`ROOT_CAUSE_ANALYSIS.md` §2):

- 4 of the 5 T1 label changes are real hunger movements (z ≥ 2.75), not sampling noise;
- survey noise alone explains about 1 of 40 rows.

**The binding limit** is information about regional hunger 2–3 quarters ahead.

### 2. Long provincial history acquired

PSA OpenSTAT 2018-based provincial CPI, 1994–2025:

- public data;
- no 2026 values requested;
- raw responses hashed.

It reproduces the approved D values to 0.039 percentage points (comparability gate, defined before download).

### 3. Information-timing fix

E23/E24 ignored provincial CPI months already published at the origin. **Dnow** uses them.

### 4. New forecaster (PCF)

| Component | Model |
|---|---|
| H | Local-level model with SWS sampling error (one parameter) |
| D | Least-squares model on long history |

**Output:** a calibrated probability, an 80% interval, a STRONG/MODERATE/UNCERTAIN signal and an exact regional-vs-provincial split.

**Frozen in advance:** `FROZEN_EVALUATION_PROTOCOL.md` (`c8bce7ce…`), with amendments in `PROTOCOL_AMENDMENTS.md` (`dd8a2208…`).

### 5. A stricter baseline

**Calibrated persistence (B1p).** The E23 Brier test against hard persistence is passed trivially by any calibrated model.

### 6. Confirmatory back-cast

94 unseen quarters; HB1–HB4 all supported (table below).

| Lead 1, T2 = 1[D > 0], 94 quarters | Accuracy | Balanced acc. | ROC-AUC | Brier |
|---|---|---|---|---|
| Persistence | 0.617 | 0.617 | 0.617 | 0.383 |
| Calibrated persistence | 0.609 | 0.609 | 0.595 | 0.240 |
| E24-frozen LR on label history (M1) | 0.670 | 0.672 | 0.742 | 0.209 |
| E24-frozen LightGBM on label history (M2) | 0.649 | 0.649 | 0.710 | 0.219 |
| **D nowcast model (M4)** | **0.713** | **0.713** | **0.792** (0.745–0.835) | **0.186** |

### 7. Prospective seals

- `SEAL_20261013T164218Z` (`ac8babbc…`)
- `SEAL_20261013T222814Z` (`356cc22f…`)

Both: origin 2026-07-01; targets 2026-Q3, 2026-Q4, 2027-Q1; authorized inputs only; recompute byte-identically. Scored by `runner/score_prospective.py`, which refuses unauthorized outcomes and any tampering.

### 8. Pre-registered T1 back-cast

Amendment A2 and `runner/run_bx_t1.py` are ready, tested on synthetic fixtures, and wait for your SWS 1998–2020 file.

### 9. Pipeline

- PCF forecaster wired in;
- news is non-blocking context;
- labelled REPLAY mode;
- live 2027-Q1 = INSUFFICIENT_DATA (correct);
- the 2026-Q3 replay equals the seal.

### 10. Usefulness for DA

**Shown on the dashboard and PDF:**

- forecast probability with its interval;
- signal strength;
- an "Indicative only — reliability not established" flag whenever the lead is not validated;
- the regional vs provincial split;
- PSA-measured provincial poverty and subsistence with CIs, labelled "measured";
- the prospective-seal ledger;
- explicit limitations.

**What it does not do:** force provincial differences, or present a model estimate as an official assessment.

### 11. LGUs

- per-LGU ranking basis;
- the density-vs-poverty finding;
- the SAE ingestion path made E24v2-safe.

### 12. Tests

- 68 Python tests (19 new);
- 21 frontend tests (7 new), plus type check and build.

## Development observations (not evidence; reported for completeness)

| Observation | Result |
|---|---|
| T1 lead 1, the PCF-with-supplementary-SWS variant (conceived after seeing E24's errors) | 0.900, Brier 0.103 |
| T1 lead 1, E24's LightGBM on label history | 0.925 |
| T1 lead 1, PCF_NOW | 0.875 |
| 2026-Q1/Q2 targets (viewed in E18; never used for selection), T1 lead 1, 10 rows | Persistence 10/10, PCF 9/10 |
| T2 lead 1 on development rows: M4 | 0.836 and C1–C6 met for T2. **The unseen-quarter accuracy (0.713) is the trustworthy number.** |

## External dependencies that remain (exact)

1. **SWS Balance Luzon hunger, 1998–2020** (you, browser download; checklist A1). Unlocks the T1 back-cast, the only near-term route to C9 for the approved target.
2. **Authorization of 2026-Q3/Q4 outcomes** (A2). Scores the seals. **≥ 8 scored origins are needed for a claim**, about 2 years of quarterly seals without the back-cast.
3. **PSA 2021 municipal SAE workbook** (A4). Gives the 126 LGUs real poverty values.
4. **Confirmation of the public-data authorization basis** (A6).
5. **Adviser decisions:**
   - reliability rule (B1, now with calibrated persistence);
   - provincial price pressure as a secondary indicator (B5);
   - PCF as forecaster (B8);
   - LGU density weight (B9);
   - B2–B4, B6, B7.
6. **Genuine responses from the 50 DA Region IV-A evaluators** (H4, H5).
7. **The E23 checkout edits** (A5) and **deployment approval** (D1).
