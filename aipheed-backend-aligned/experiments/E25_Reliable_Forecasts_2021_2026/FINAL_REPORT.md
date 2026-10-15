# E25 Final Report: reliable, useful and accurate forecasts (2021–2026 data only)

**Date and data.**

- Report date: 2026-10-14.
- Forecast target: 2027-Q1.
- Data: 2021-Q1 to 2026-Q2, plus January–June 2026 as authorized. No pre-2021 value is used.

**Where the work lives.**

- Everything is in `aipheed-backend-aligned/experiments/E25_Reliable_Forecasts_2021_2026/`, with isolated `backend_dev/` and `dashboard_dev/` copies.
- `backend/`, `frontend/` source, deployed models and the thesis chapters were not modified.
- E17, E18, E23, E24 and E24v2 were verified against their hash lists before any work: **0 content differences** (`docs/READONLY_VERIFICATION.md`).
- Nothing was committed, pushed, merged or deployed.

**Branch note.** The working tree is on `ui/no-data-quarters-risk-band`. The complete earlier experiments exist only in commit 5113ae5 (branch `e25-window-2021-2026`); they were read through a read-only `git archive` extract. The earlier, never-run E25 draft protocol was superseded before any model was fitted, and its 4 candidates are kept.

**Runs and seals.**

| Item | Record |
|---|---|
| Frozen protocol | `FROZEN_EVALUATION_PROTOCOL.md`, SHA-256 `694a757082e3…` (in `runner/PROTOCOL_SHA256.txt`), frozen before any model was fitted |
| Primary run | `runs/20261014T002026Z` |
| Repeat run | `runs/20261014T002520Z`, byte-identical |
| Monthly evaluation | `runs/MONTHLY_20261014T002535Z` |
| Prospective seal | `runs/SEAL_E25_20261014T002548Z` |

**Every result on 2021–2026-Q2 is development evidence**: those quarters were examined in E9–E24v2.

---

## Direct answers

### 1. Which ideas were tried, how many candidates in total, and which were kept?

**19 ideas were implemented or analyzed; 6 more were considered and set aside with reasons** (`IDEA_LOG.md`). Part 1 of the log, with the synthetic power for each idea, was frozen before any model ran.

**Candidates.**

- E25: **16 forecasting candidates** (10 for the approved label T1, 6 for the exploratory provincial target T2) plus **2** for the monthly provincial evaluation.
- Lineage counted for multiplicity: E24's 16 arms and E24v2's 6 in-window arms. **About 40 candidates have been examined on these quarters since E24.**

**Kept (frozen before running; not selected on results):**

- **PCF21 = FINAL_T1.** Regional hunger forecast by a local-level model with SWS sampling noise, plus provincial D by least squares on 2021+ pairs, combined into P(S1 > τ).
- **M4_21 = FINAL_T2.** P(D > 0) from the latest two months of provincial CPI and last quarter's D.
- **AR_M** (monthly) as supporting evidence.

**Not kept**, because none improved on PCF21:

- PCF21 variants with Dnow, supplementary rounds, hierarchical D, mean reversion or a leading indicator;
- calibration, ensemble and the persistence gate;
- every hierarchical D model for T2.

### 2. Did the proposed model beat each baseline and calibrated persistence?

**Not on accuracy, and not after Holm adjustment on any metric that matters for the goal.**

Approved label (T1), FINAL_T1 = PCF21. One-sided exact sign-flip over forecast dates; Holm across B1–B6 (+ B1p for Brier).

| Versus | Lead 1 (8 dates, 37 HIGH / 3 LOW) | Pooled leads 1–6 (10 dates) |
|---|---|---|
| B1 naive persistence | Accuracy 0.875 vs 0.875 (difference 0, p = 1.0). Brier 0.101 vs 0.125, p = 0.109 (5 dates better, 3 worse). | Per-date Brier 0.122 vs 0.150, **p = 0.027** (8/2), **Holm 0.082** |
| B2 LR combined | Accuracy +0.250, p = 0.031 (Holm 0.164). Brier p = 0.027 (Holm 0.070). | Brier p = 0.001 (Holm 0.007) |
| B3 LR government | +0.275, p = 0.031 (Holm 0.164). Brier p = 0.016 (Holm 0.070). | p = 0.038 (Holm 0.082) |
| B4 LR news | +0.200, p = 0.062 (Holm 0.188). Brier p = 0.012 (Holm 0.070). | p = 0.001 (Holm 0.007) |
| B5 LightGBM government | +0.050, p = 0.25 (Holm 0.50). Brier p = 0.016 (Holm 0.070). | p = 0.033 (Holm 0.082) |
| B6 LightGBM news | +0.200, p = 0.027 (Holm 0.164). Brier p = 0.012 (Holm 0.070). | p = 0.002 (Holm 0.010) |
| **B1p calibrated persistence** | Accuracy equal. Brier 0.101 vs 0.162, p = 0.008 (Holm 0.055). | p = 0.007 (Holm 0.027) |
| REF always-HIGH (no data) | **Worse**: accuracy −0.050, Brier 0.101 vs 0.075 | **Worse**: 0.122 vs 0.090 |

**The Chapter I proposed model (LightGBM on news + government, masked):** lead-1 accuracy 0.825, Brier 0.133, AUC 0.658.

- It is **worse than persistence** (accuracy −0.050; Brier p = 0.61) and beats no baseline after Holm.
- On T2 its accuracy is 0.509.

**The exploratory provincial target (T2, D > 0), FINAL_T2 = M4_21, lead 1 (11 dates, 24 HIGH / 31 LOW):**

- Accuracy 0.764 vs persistence 0.655: p = 0.031, Holm 0.062.
- Brier 0.186 vs 0.345: p = 0.003, Holm 0.012.
- After Holm it beats every one of B1–B6 on Brier (Holm p ≤ 0.017).
- On accuracy, after Holm, it beats B2, B3, B4 and B6, but not B1 or B5 (Holm p = 0.062 each).
- On pooled leads it does **not** beat calibrated persistence (p = 0.38).

### 3. Is accuracy above 75%, and does that mean anything given always-HIGH accuracy?

**Yes, and no.** PCF21 scores **0.875** and the proposed LightGBM **0.825** at lead 1. But:

- **always-HIGH**, a rule that uses no data, scores **0.925**;
- **persistence** scores 0.875;
- 37 of the 40 lead-1 rows are HIGH.

Accuracy above 75% therefore carries no information about skill here. Always-HIGH also has the lowest Brier of any non-oracle forecaster (0.075 at lead 1; 0.090 pooled).

### 4. Which criteria are met, which are unreachable on this data, and which await adviser approval?

**Original C1–C9** (E24 definitions; FINAL_T1, lead 1):

| Criterion | Status |
|---|---|
| C1 accuracy > 0.75 | **Met** (meaningless; see answer 3) |
| C2 beats the strongest baseline | **Not met** (ties persistence). **Mathematically reachable at lead 1 only for a perfect model** (best p = 2^-5 = 0.031). **Unreachable at leads 3–6** (best p ≥ 0.0625). |
| C3 not explained by HIGH dominance | Not met |
| C4 defensible across dates | Not met |
| C5 information beyond persistence | Not met (0 of 5 label changes anticipated) |
| C6 reliability rule | **Unreachable** (every lead has ≤ 3 LOW rows; 5 are required) |
| C7 no leakage | Met |
| C8 reproducible | Met |
| C9 generalizes to unseen quarters | **Not assessable** |

**Proposed P1–P9: pending adviser approval** (`ADVISER_APPROVAL_REQUEST.md`). These are a proper scoring rule on pooled leads.

| Criterion | Status |
|---|---|
| P1 beats the no-skill references | **Not met** (always-HIGH is better) |
| P2 beats the strongest baseline on pooled Brier | Met on the raw p (0.027 vs persistence); not after Holm (0.082) |
| P3 = C3 | Not met |
| P4 defensible across dates | **Met** |
| P5 = C5 | Not met |
| P6 reliability | **Not met** (lead 1: p = 0.109; calibration-in-the-large −0.18) |
| P7, P8 | Met |
| P9 | Not assessable |

**→ The T1 forecasting goal is NOT met under either set.**

T2 (exploratory, never a substitute for T1): C1–C8 met at lead 1; C9 not assessable.

### 5. Is the 2027-Q1 forecast complete and valid?

**No.** The pipeline record (`backend_dev/data/quarterly_runs/2027-Q1/forecast_record.json`, SHA-256 `6c4f4c9e…`) is **INSUFFICIENT_DATA**, with no forecast attached.

**Missing inputs and who must supply them:**

| Missing input | Needed by | Supplier |
|---|---|---|
| SWS **September 2026** round and its publication date | FINAL_T1 | Researcher authorizes; source SWS |
| Provincial food CPI YoY **July–September 2026** with release dates | FINAL_T1 | Researcher; PSA |
| Provincial food CPI YoY **October–November 2026** | FINAL_T2 only | Researcher; PSA |
| **2026-Q4 news** and 2026 government indicators | Chapter I feature baselines only | Researcher; aiPHeed fetchers |
| The **cutoff 2026-12-31 23:59:59 PHT** | All | Time; cannot be produced earlier |

The dashboard shows 2027-Q1 as **MISSING INPUTS — not a low-risk state**.

**What was sealed instead.** A lead-2 forecast for 2027-Q1, from authorized data only (origin O(2026-Q3) = 2026-10-01), is sealed for evaluation. It is **not** the operational forecast and is indicative only. FINAL_T2 could not be sealed: it needs July–August 2026 CPI, which is not authorized.

### 6. Is the data complete for 2025-Q1 to 2027-Q1? Every gap

**No.** Details per province, quarter and input are in `DATA_COMPLETENESS_MATRIX.csv`.

| Quarter | Gap |
|---|---|
| 2025-Q2, 2025-Q3 | **No production SWS round.** Only supplementary rounds exist, and their quarter assignment is disputed, so there is **no approved label** (reading A). Readings B/C add a label (reported both ways). |
| 2026-Q1, 2026-Q2 | SWS values present. **Publication dates unverified** (only an upper bound, 2026-09-10). **No authorized 2026 news or 2026 government indicators.** |
| 2026-Q3 | SWS round, provincial CPI (July–September), Dnow, news and government indicators all **protected** (not authorized; never opened). The label is therefore unavailable. |
| 2026-Q4 | Not yet published (SWS December round; CPI from early November). News incomplete until the cutoff. |
| 2027-Q1 | Future |
| Static (all quarters) | **126 of 142 LGUs lack a PSA municipal poverty estimate** (labelled province-mean substitute). PSA publishes no confidence interval for provincial CPI. The FNRI anchor in the authorized file is NNS 2025 at 22.6% (regional, secondary reporting, no CI). |
| Within the window | 2021-Q1 and 2022-Q1 have no SWS round. 2021 Dnow is not computable in window. |

### 7. Which hypotheses are testable, supported, not supported, or awaiting participants?

| Hypothesis | Status |
|---|---|
| H1 | **Not testable.** No lead has ≥ 5 LOW rows. Descriptively, FSSI ranks 5th by mean \|SHAP\| (in the top 5 on 50% of dates), but permuting it does not raise the Brier score (ΔBrier −0.002; CI −0.005 to +0.000). cpi_dev ranks 19th (0% of dates; ΔBrier +0.0002). |
| H2 | **Not testable** (no evaluable lead). Reliable leads under E23's rule or P6: **none**. |
| H3 | **Not testable** (no evaluable lead). Descriptively, the proposed LightGBM does not beat persistence. |
| H4 | **Awaiting participant data** (50 DA Region IV-A evaluators; instruments ready) |
| H5 | **Awaiting participant data** |

None is supported or rejected.

### 8. What may the thesis claim, and what must it not claim?

See `THESIS_SAFE_WORDING.md`.

**May claim:**

- A probabilistic, interval-bearing, regional/provincial-decomposed quarterly forecast exists.
- On development quarters it had a lower Brier than persistence with leads pooled (p = 0.027, not significant after Holm) but no accuracy gain.
- Always-HIGH was best on these high-hunger quarters.
- The regional SWS level carries the forecast error (oracle diagnostic: 97.5% accuracy if it were known).
- The exploratory provincial price-pressure indicator beat persistence at lead 1 on development data.
- 142 deterministic LGU rankings, with 126 density-only substitutes disclosed.
- Forecasts for 2026-Q4 and 2027-Q1 are sealed.

**Must not claim:**

- any accuracy as evidence of skill;
- beating the baselines (unqualified);
- a reliable lead time;
- that any of H1–H5 is supported or rejected;
- generalization;
- the score as a measured food-insecurity rate;
- municipal poverty data for all 142 LGUs;
- an available 2027-Q1 forecast;
- anything from the 1995–2020 back-cast.

---

## Chapter I traceability

Exact wording is from `thesis_source/CHAPTER_I_verbatim.txt` (the PDF hash matches the file on disk). The SOP Q5 clause naming a withdrawn second evaluator group is redacted per your instruction.

### Specific objectives

| Objective (exact wording) | Status | Evidence |
|---|---|---|
| **1.** "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity risk patterns per province-quarter from a Filipino-English news corpus." | **Implemented earlier; outputs used, not re-run.** FSSI and trigger features (2021–2025) enter the feature baselines and the proposed model. Two triggers are constant over 2021–2025. 2026 news is not authorized. | `BUG_FIXES.md` R1; E23/E24 pipeline audit |
| **2.** "To evaluate the performance of the proposed LightGBM forecasting model using the following metrics: I. Accuracy … II. Precision and Recall … III. F1-Score … IV. AUC-ROC … V. Forecast performance across multiple lead times via walk-forward expanding-window cross-validation to empirically determine the furthest horizon at which reliable forecasting is achievable" | **Computed** for every model at leads 1–6 (7–8 have no dates), with balanced accuracy, Brier and log score, and HIGH/LOW counts beside every metric. **Furthest reliable horizon: none** (no lead evaluable). | `BASELINE_COMPARISON.csv`, `runs/20261014T002026Z/metrics_all.csv`, `tests_all.csv` |
| **3.** "To produce spatially disaggregated municipal and city food insecurity risk rankings from validated province-level forecasts, using PSA published poverty incidence and population density as vulnerability weights." | **Produced for all 142 LGUs** with the approved formula. Deterministic; identity-checked. 126 province-mean substitutes labelled. Density opposite to poverty (ρ = −0.76). **Province forecasts are not validated**, so the rankings are indicative. | `LGU_RANKING_VALIDATION.csv`, `runs/lgu_validation.json` |
| **4.** "To compare the effectiveness of the proposed LightGBM forecasting model against the following baseline approaches: I. Naive persistence baseline II. PSA-only indicator baseline III. NLP-only sentiment baseline IV. Logistic regression baseline" | **Done** on identical rows (mapping I→B1, II→B3, III→B4, IV→B2; plus B5/B6 from SOP Q3). The proposed model beats none of them after Holm, and loses to persistence. | Answer 2 |
| **5.** "To deploy a public geospatial dashboard presenting forecast maps and early-warning alerts, evaluate it under the ISO/IEC 25010 software quality model with DA Region IV-A evaluators, and validate its forecasts against DOST-FNRI NNS 2019 and 2023 CALABARZON prevalence figures as a face-validity anchor." | **Dashboard:** the isolated development copy (`/forecast-timeline`) works and is tested; **not deployed** (needs your approval). **ISO/IEC 25010:** instruments ready; awaiting the 50 DA evaluators. **FNRI anchor:** NNS 2023 (19.1%, verified in E23) and NNS 2025 (22.6%, secondary) are regional; NNS 2019 was not verified. A regional prevalence cannot validate provincial forecasts (face validity only). | `TEST_RESULTS.md`, `instruments/` |

### Statement of the problem

| SOP question (exact wording) | Answer |
|---|---|
| **Q1.** "What variables most significantly predict food insecurity risk across the provinces of CALABARZON, as identified through SHAP feature attribution?" | Descriptive only (H1 not testable). Top mean \|SHAP\| for the proposed LightGBM at lead 1: food_cpi (index level), lead, fruit/vegetable and leafy-vegetable prices, FSSI (5th), headline CPI. The oracle diagnostic shows the regional SWS level is what forecasts would need. |
| **Q2.** "What is the furthest lead time at which aiPHeed can reliably forecast province-level food insecurity risk across CALABARZON?" | **None can be established** (no lead evaluable; E23 rule and P6 both give none) |
| **Q3.** "How does the LightGBM model combining NLP-derived news signals and government statistical indicators compare against six baseline approaches, naive persistence, three logistic regression variants (combined features, government indicators only, and NLP features only), and two LightGBM ablation variants trained on each data source separately, in classifying provincial food insecurity risk?" | Lead 1: accuracy 0.825 vs persistence 0.875; AUC 0.658 vs 0.779. Better than the LR variants on Brier before Holm only. Not better than either LightGBM variant. Answer 2 has the full table. |
| **Q4.** "How effectively do the city- and municipality-level food insecurity risk rankings derived from province-level forecasts reflect relative vulnerability across CALABARZON?" | Needs the DA evaluators' assessments (H4). Mechanically the rankings are exact and deterministic, but 126 of 142 order by density only, and density runs opposite to poverty. |
| **Q5.** "How do DA Region IV-A personnel, as system evaluators, [withdrawn second group redacted], assess aiPHeed under the ISO/IEC 25010 software quality model, in terms of functional accuracy and ease of use respectively?" | **Awaiting participant data** |

### Hypotheses (exact wording) — status as in answer 7

| Hypothesis | Status |
|---|---|
| **H1.** "The Food Stress Sentiment Index (FSSI) and food CPI deviation will not be among the strongest predictors of food insecurity risk in CALABARZON when examined through SHAP feature attribution." | Not testable |
| **H2.** "aiPHeed will not reliably classify whether a CALABARZON province is at high or low food insecurity risk across multiple forward-looking lead times." | Not testable |
| **H3.** "The LightGBM model that combines news signals and government data will not outperform the six comparison models, naive persistence, three logistic regression variants (news-only, government data-only, and combined), and two LightGBM variants trained on only one data source at a time, in classifying provincial food insecurity risk across CALABARZON." | Not testable |
| **H4.** "The vulnerability-weighted spatial disaggregation of province-level forecasts will not produce municipal and city risk rankings that are consistent with DA Region IV-A evaluators' assessments of relative food insecurity vulnerability across CALABARZON, as evaluated through the aiPHeed Post-Survey Questionnaire." | Awaiting participants |
| **H5.** "aiPHeed will not receive favorable functional suitability, accuracy, and usability ratings from DA Region IV-A evaluators under the ISO/IEC 25010 software quality model." | Awaiting participants |

---

## What E25 found that matters most

1. **The approved label is almost always HIGH on the evaluation quarters.** These were high-hunger quarters, so accuracy, and even Brier against always-HIGH, cannot show skill. This was established before any model ran (`docs/REACHABILITY.md`).
2. **Even a perfect model could only just reach p < 0.05 against persistence at lead 1 (0.031); at longer leads it could not reach it at all.** Persistence is wrong on only 5 dates, and on its right dates every scoring rule gives it zero loss. Pooling leads is the only design with power. There, PCF21 beats persistence before multiplicity adjustment (p = 0.027), not after (0.082).
3. **The forecast error is regional.** If the target quarter's SWS level were known, accuracy would be 97.5%. No tested input anticipates SWS moves: news, government indicators, regional food inflation and label history all fail. Some changes are partly survey noise (noise ceiling: about 1 expected sampling flip in 40 rows).
4. **The provincial layer has real signal, on development data.** The latest two months of provincial CPI forecast relative price pressure better than persistence (lead 1: 0.764 vs 0.655). The monthly evaluation agrees weakly (Brier p = 0.035 vs sign persistence; not significant vs calibrated persistence).
5. **The proposed LightGBM does not beat persistence.** 22 of its "provincial" features are identical for all provinces in ≥ 90% of quarters.

## Deliverables

| File | Content |
|---|---|
| `IDEA_LOG.md` | 19 ideas + 6 set aside; power; results; kept or rejected |
| `DATA_COMPLETENESS_MATRIX.csv` | 760 cells: 25 quarters (2021-Q1…2027-Q1) × 5 provinces × 6 inputs, + 10 static LGU cells |
| `AUTHORIZATION_REQUEST.md` | Exact files needed from you |
| `FROZEN_EVALUATION_PROTOCOL.md` | Hashed in `runner/PROTOCOL_SHA256.txt` |
| `ADVISER_APPROVAL_REQUEST.md` | Original vs proposed criteria; decisions D1–D7 |
| `BASELINE_COMPARISON.csv` | Every model, target, row set and lead (+ pooled), with paired tests vs FINAL |
| `PREDICTIONS_BY_QUARTER.csv` | Lead-1 back-test predictions of every model + every sealed forecast |
| `FEATURE_ABLATION_RESULTS.csv` | H1 ablations, SHAP ranks, permutation importance, PCF component ablations, oracle diagnostics |
| `LGU_RANKING_VALIDATION.csv` | 142 LGUs |
| `QUARTERLY_PIPELINE_AUDIT.md`, `BUG_FIXES.md`, `TEST_RESULTS.md`, `REPRODUCE.md`, `THESIS_SAFE_WORDING.md` | As named |
| `ADVISER_AND_AUTHORIZATION_CHECKLIST.md` | One page |
| `docs/REACHABILITY.md`, `docs/POWER_SIMULATION.md`, `docs/READONLY_VERIFICATION.md` | Analyses run before the protocol |
| `instruments/` | Consent, questionnaire, facilitator guide, decision rules, scorer (DA Region IV-A only) |
| `dashboard_dev/` (`/forecast-timeline`), `backend_dev/` (`/api/v1/quarterly/e25-timeline`) | Isolated copies reading one record (SHA-256 shown on the page and in the PDF) |
| `E25_FILES_SHA256.txt` | Hash of every E25 file |
