# E99: Chapter III evaluation, evidence completion and production lock (thesis evidence report)

**Branch.** `e99-chapter3-evaluation`, from `e98-acceptance-gate` (a42de8c).
**Protocol.** `PROTOCOL.md` (SHA-256 in `PROTOCOL.sha256`), committed 37e0f88 before any scoring.
**Run.** `runs/20261022T092721Z/`: `e99_results.json`, predictions, Optuna trials, `lgbm_best_k2.pkl`, seal.
**Console.** `console.txt`.
**Gate.** `release_gate.json`.
**Manifest.** `release_candidate_manifest.json`.
**Tests.** `backend/tests/integration/test_e99_chapter3.py`.

**Production: unchanged.** `final-system-v2` stays at 053a95d on origin. Nothing was merged into it, and no Render or
Vercel deployment was triggered.

## 1. Summary

- **E99 ran, for the first time, the pipeline the thesis itself specifies** (Chapter III):
  - the Eq. 3 composite label: SWS hunger + 2 × provincial food-CPI deviation, above the global median;
  - the 12 Chapter III features;
  - Algorithm 3 lead-time discovery;
  - Algorithm 4 Optuna TPE with the blind 2025-Q4..2026-Q3 holdout and the F1 ≥ 0.75 / AUC ≥ 0.80 acceptance;
  - the six Chapter I comparators, on identical folds.
- **The pipeline fails its own criteria.**
  - Algorithm 3: mean fold accuracy at k = 1 is **0.30** (persistence 0.70), so the **Maximum Reliable Lead Time is
    k\* = 0**. Both sensitivity runs agree.
  - Algorithm 4 at the dashboard horizon k = 2 (report-only): holdout accuracy 0.45, weighted F1 0.53, AUC 0.61, so it
    is **not accepted**.
- **The cause is structural, not tuning.** About 15 labelled development quarters span one regime switch. Models
  trained on 2021–23, when 86% of labels are LOW (43 of 50 rows), keep predicting LOW in the 2024–26 high-hunger regime. Persistence,
  which simply carries the regime, beats every learned model.
- **Hypotheses.**
  - H1 is not rejected: food CPI deviation ranks 3rd by SHAP, the best FSSI feature 4th.
  - H2 is not rejected (k\* = 0).
  - H3 is not rejected: LightGBM does not beat persistence; McNemar p = 0.0003 in persistence's favour.
  - H4 and H5 are **blocked**: there are no evaluator responses.
- **On the same Eq. 3 label at k = 2,** the served FIRI v2 scores 0.90 on the development folds and 0.85 on the
  holdout. This is regime-following: balanced accuracy is 0.47 and it misses every LOW row. It does not beat
  persistence on the holdout (0.90).
- **FIRI v2 therefore remains the best defensible regional index.** No E99 model is promoted or served.
- **Fixed on this branch only:**
  - the province detail and plain-language evidence no longer present the price-pressure output as a "% chance" (G6);
  - the LGU ranking method no longer calls the province index a "probability".
- **Seals.** The FIRI v2 seal (2026-Q4 and 2027-Q1) and the new E99 research seal (2026-Q4) verify, and are
  **PENDING**: no 2026-Q4 outcome has been published.
- **Release gate:** G1, G2, G4 and G9 fail. **Do not deploy.**

## 2. Root causes (why the objectives cannot yet be shown as met)

1. **One regime switch in the authorized window.** The Eq. 3 label is LOW in almost every 2021–23 quarter and HIGH in
   almost every 2024–26 quarter. A walk-forward learner sees the switch only after it has happened.
2. **Little data.**
   - About 19 labelled quarters in total.
   - Algorithm 3 at k = 1 has 6 development folds; at k = 2, 4.
   - The holdout has 2 LOW rows out of 20, so its AUC is very fragile.
3. **No legitimate extra history.** Pre-2021 data is excluded by the study-window rule. New collection is excluded by
   the deadline rule (2026-10-22). No provincial measured outcome exists (`PROVINCIAL_OUTCOME_FEASIBILITY.md`).
4. **News coverage in the training years is too thin** for FSSI or the triggers to carry signal. NLP-only arms are the
   weakest, and four of five triggers have zero SHAP importance.
5. **The evaluations with people (H4, H5) have not been administered.**

## 3. Label and data (§1–§3 of the protocol)

**Eq. 3 label.**
- 95 province-quarters, 19 quarters (2021-Q2..2026-Q3, excluding 2022-Q1, 2025-Q2 and 2025-Q3, which have no
  `definition_A` SWS round).
- Global median 15.473; 49.5% HIGH.
- **A proxy:** measured regional hunger plus provincial price deviation.

**Features.** The 12 Chapter III features from `features_fused.parquet`, with food CPI deviation from
`psa_indicators.parquet`.
- Unemployment and rice change are taken from t − 1, because their last month is not published by the 15th issue date
  (disclosed deviation).
- Missing values are never zero-filled (disclosed deviation).

**Leakage audit (test `test_training_uses_only_labels_posted_before_issue`).** Every training pair's SWS round was
posted before the issue date, its target quarter is ≤ the origin, and every fold has ≥ 8 training quarters.

## 4. Algorithm 3: lead-time discovery (development folds 2023-Q4..2025-Q1, k = 1)

30 rows: 24 HIGH, 6 LOW.

| Model | Mean fold accuracy | Balanced accuracy | Weighted F1 | AUC | TP/FP/FN/TN |
|---|---|---|---|---|---|
| **LightGBM (default), 12 features** | **0.300** | 0.500 | 0.285 | 0.60 | 4/1/20/5 |
| Naive persistence | **0.700** | 0.813 | 0.730 | 0.81 | 15/0/9/6 |
| LR combined | 0.367 | 0.604 | 0.353 | 0.65 | 5/0/19/6 |
| LR government-only | 0.267 | 0.542 | 0.194 | 0.80 | 2/0/22/6 |
| LR NLP-only | 0.233 | 0.458 | 0.179 | 0.67 | 2/1/22/5 |
| LightGBM government-only | 0.300 | 0.563 | 0.251 | 0.55 | 3/0/21/6 |
| LightGBM NLP-only | 0.300 | 0.563 | 0.251 | 0.71 | 3/0/21/6 |
| Prevalence | 0.200 | 0.500 | 0.067 | 0.81 | 0/0/24/6 |

**k = 1 fails (0.30 < 0.75), so the search halts: k\* = 0.**
- S1 (median from development rows only): k\* = 0.
- S2 (holdout folds included, 10 folds): k = 1 accuracy 0.36, k\* = 0.

## 5. Algorithm 4 at k = 2 (report-only: the dashboard horizon; k\* = 0)

**Optuna.**
- 100 TPE trials on the 4 development folds (2024-Q2..2025-Q1). Best mean weighted F1: 0.326.
- Best parameters: `num_leaves` 19, `max_depth` 2, `learning_rate` 0.165, `n_estimators` 311, `min_child_samples` 8,
  `subsample` 0.75, `colsample_bytree` 0.94, `reg_alpha` 0.0034, `reg_lambda` 0.124.

**Blind holdout** (2025-Q4..2026-Q3; 20 rows, 18 HIGH / 2 LOW):

| Model | Accuracy | Balanced | Precision / Recall (HIGH) | F1 (HIGH) | Weighted F1 | AUC | Brier |
|---|---|---|---|---|---|---|---|
| **LightGBM tuned (proposed)** | 0.450 | 0.694 | 1.00 / 0.39 | 0.56 | **0.531** | **0.611** | 0.497 |
| LightGBM default | 0.550 | 0.750 | 1.00 / 0.50 | 0.67 | 0.631 | 0.667 | 0.385 |
| Naive persistence | **0.900** | 0.722 | 0.94 / 0.94 | 0.94 | **0.900** | 0.722 | **0.100** |
| LR combined | 0.200 | 0.556 | 1.00 / 0.11 | 0.20 | 0.200 | 0.611 | 0.628 |
| LR government-only | 0.250 | 0.583 | 1.00 / 0.17 | 0.29 | 0.278 | 0.667 | 0.515 |
| LR NLP-only | 0.250 | 0.361 | 0.80 / 0.22 | 0.35 | 0.325 | 0.306 | 0.356 |
| LightGBM government-only | 0.650 | 0.583 | 0.92 / 0.67 | 0.77 | 0.719 | 0.583 | 0.354 |
| LightGBM NLP-only | 0.300 | 0.389 | 0.83 / 0.28 | 0.42 | 0.388 | 0.458 | 0.370 |
| Prevalence | 0.100 | 0.500 | — / 0.00 | 0.00 | 0.018 | 0.500 | 0.341 |
| FIRI v2 (served index) | 0.850 | 0.472 | 0.89 / 0.94 | 0.92 | 0.827 | 0.556 | 0.189 |
| Chapter III blend (cutoff 0.712) | 0.200 | 0.556 | 1.00 / 0.11 | 0.20 | 0.200 | 0.694 | 0.425 |

**Acceptance (weighted F1 ≥ 0.75 and AUC ≥ 0.80): NOT ACCEPTED** (0.531 / 0.611).

**Development folds at k = 2 (20 rows, 19 HIGH / 1 LOW):** tuned LightGBM 0.25, persistence 0.55, FIRI v2 0.90.

**McNemar (pooled development + holdout, 40 rows), tuned LightGBM vs each comparator:**

| Comparator | LightGBM only correct | Comparator only correct | Exact p |
|---|---|---|---|
| Persistence | 1 | 16 | **0.0003** (persistence better) |
| LR combined | 7 | 5 | 0.77 |
| LR government-only | 8 | 4 | 0.39 |
| LR NLP-only | 8 | 1 | 0.039 |
| LightGBM government-only | 4 | 5 | 1.0 |
| LightGBM NLP-only | 10 | 3 | 0.092 |

## 6. SHAP (SOP 1 / H1)

Final tuned k = 2 model, retrained on all 90 labelled k = 2 pairs. Mean |SHAP| rank:

| Rank | Feature | Rank | Feature |
|---|---|---|---|
| 1 | unemployment_rate (t − 1) | 7 | FSSI |
| 2 | rice price change (t − 1) | 8 | trigger_climate |
| **3** | **food CPI deviation** | 9–12 | trigger OFW remittance, employment, market, fish kill (all exactly 0) |
| **4** | **FSSI lag 1** (best FSSI) | | |
| 5 | FSSI acceleration | | |
| 6 | FSSI lag 2 | | |

- **H1 rule** (best FSSI feature and food CPI deviation both in the top 3): **not rejected**. FSSI is 4th.
- **Stability** (median rank over the development fold models): rice change 1.0, food CPI deviation 2.5, FSSI_accel
  3.5, unemployment 3.5.
- **Disclosure:** food CPI deviation also enters the Eq. 3 label, so part of its strength is construction and
  autocorrelation. And because the model itself fails (§4–§5), these attributions explain an unreliable model.

## 7. Hypothesis decisions (pre-registered rules, §8)

| Hypothesis | Decision | Basis |
|---|---|---|
| H1 FSSI and food CPI deviation not among the strongest predictors | **Not rejected** (borderline: ranks 4 and 3) | §6 |
| H2 not reliable across multiple lead times | **Not rejected** | k\* = 0; no accepted model |
| H3 combined LightGBM will not outperform the six comparators | **Not rejected** | Below persistence (significant), below LightGBM government-only on the holdout; better than LR NLP-only only |
| H4 LGU rankings not consistent with DA evaluators | **Blocked** | No rankings collected (package ready, §10) |
| H5 no favourable ISO/IEC 25010 ratings | **Blocked** | 0/50 responses |

Failing to reject a null hypothesis is a valid thesis finding. It answers SOP 1–3 as worded.

## 8. Best defensible candidate

| Candidate | Target | Lead-2 evidence | Status |
|---|---|---|---|
| Chapter III LightGBM (Algorithms 3–4) | Eq. 3 proxy, province | Holdout 0.45, not accepted; below persistence | **Rejected** under the thesis's own criteria |
| **FIRI v2 (served)** | Regional SWS hunger (E97/E98); Eq. 3 proxy (E99) | Regional 0.933 (15 quarters). Eq. 3: development 0.90, holdout 0.85, balanced 0.47, below persistence on the holdout | **Best defensible index.** Development evidence only; not a probability. |
| Persistence | Either | Strongest baseline everywhere | Benchmark |

## 9. Independent evaluation (sealed forecasts)

`prospective/score_sealed.py` scores only when the outcome is published, with no retraining, recalibration or
threshold change. Status on 2026-10-22: `prospective/status_20261022.json` (**PENDING**).

**Seals:**

| Seal | Target(s) | Issued | Rule | Verification |
|---|---|---|---|---|
| S-FIRI2, `FINAL_Thesis_System/out/firi2_sealed_prospective.csv` (151887c, 2026-10-20) | 2026-Q4, 2027-Q1 | 2026-07-01, 2026-10-01 | Regional mean FIRI ≥ 0.5 vs SWS H > 11.3% | SHA-256 `e2bef0b2…` on LF-normalised content ✓ |
| S-E99, `runs/20261022T092721Z/sealed_prospective_2026Q4.csv` | 2026-Q4 | 2026-07-15 (k = 2 from origin 2026-Q2) | p_high ≥ 0.5 vs Eq. 3 label with the **frozen** median 15.473 | SHA-256 `5a9e24c8…` ✓ (reproduced exactly by the rerun) |

- **Sealed values.**
  - S-FIRI2, 2026-Q4: regional mean 0.749 (HIGH).
  - S-E99: all 5 provinces HIGH (p 0.88–0.995).
  - S-E99 comes from a model that **failed** acceptance. It is a research seal and is not published.
- **Procedure.**
  1. When SWS posts 2026-Q4 (expected about January 2027), add the round to `data/inputs/sws_rounds.csv` with its
     posting date.
  2. When PSA 2026-Q4 food CPI is in `psa_indicators.parquet`, run the scorer.
  3. Report the result as the first independent evidence.
  4. Repeat for 2027-Q1.
- **Line endings.** The FIRI seal was hashed on LF content and the working copy has CRLF (git autocrlf). The scorer
  accepts either encoding of the same content. Values are unchanged since 151887c.

## 10. Dashboard labels (development branch only; production untouched)

**Changes** (`app/ml/inference/thesis_system.py`, `app/quarterly/lgu_audit.py`):

| Where | Before | After |
|---|---|---|
| Province confidence statement | "The LightGBM food-price-pressure forecast is 7%." | "… food-price-pressure score is 0.07 (0-1; not a calibrated probability)." |
| Indicator list (A1) | "7% chance of food-price pressure" | "food-price-pressure score 0.07 (0-1, not a calibrated probability)" |
| Plain-language evidence (A1) | "The price model gives a 7% chance that food prices … rise faster than usual" | "The price model rates food-price pressure for … at 0.07 on a 0-1 scale (… a rating, not a calibrated probability)". The plain-language rule of no "score" or model terms is kept. `test_e83_plain_explanations` now checks the 0–1 value instead of a percentage. |
| LGU `rankingMethod` | "risk_index = province probability x vulnerability" | "risk_index = province estimate (the served province score) x vulnerability" |

**Audit through the API (thesis mode):**

| Output | Label |
|---|---|
| Province score | `scoreType` food_insecurity_risk_index; "FIRI v2 … (0-1), not a probability" |
| LGU outputs | "Indicative, relative ordering … not a measured municipal food-insecurity rate" |
| Regional hunger outlook | Labelled Balance Luzon |

- No "% chance" remains in the province payload.
- No frontend file was changed (approved-UI rule).

## 11. Objective 3: LGU rankings

The E97 audit stands and its tests pass on this branch:
- 142/142 LGUs join their map shapes;
- 141 municipal SAE values;
- the Lucena substitute is disclosed;
- the ranking is robust to nearby weightings, and sensitive to Lucena's density in Quezon.

**New in E99.** The served top 5 per province, which H4 will be compared against:

| Province | Served top 5 |
|---|---|
| Batangas | Lipa, Bauan, San Pascual, Taal, San Jose |
| Cavite | Gen. Mariano Alvarez, General Emilio Aguinaldo, Cavite City, Tagaytay, Mendez |
| Laguna | Siniloan, San Pedro, Biñan, Cabuyao, Santa Cruz |
| Quezon | **Lucena** (substitute poverty value), San Francisco, Macalelon, San Andres, Infanta |
| Rizal | Taytay, Antipolo, Cardona, Morong, San Mateo |

## 12. Objective 5: evaluation package and DOST-FNRI

**`evaluation_package/`:**
- **Eligibility:** the exact option "DA Regional Field Office IV-A".
- **Export validation:** invalid exports are rejected, never partially scored.
- **ISO/IEC 25010 scoring:** items 1–15; favourable at ≥ 3.41; COMPLETE at 50.
- **New H4 ranking task:** top 5 LGUs per province, Borda aggregation vs the served top 5.
  - H4 rejected iff ≥ 4 scorable provinces and overlap ≥ 3/5 in ≥ 4 of them.
  - The chance probability of each overlap is reported.
- **Status: NO_RESPONSES** for both. Nothing is scored.

**DOST-FNRI** (unchanged from E97/E98, repository sources only):
- NNS 2019 has **no** CALABARZON regional figure.
- ENNS 2021 provincial (Batangas, Cavite, Lucena) CIs overlap.
- 2023 → 2025 regional FIES direction agrees with SWS and FIRI (descriptive).

**Document change for the adviser.** Objective 5 should cite ENNS 2021 + NNS 2023, as Chapter III already does.

## 13. Objective-to-evidence matrix

| Objective | Classification | Exact reason |
|---|---|---|
| 1. NLP pipeline (XLM-RoBERTa, BERTopic, FSSI) | **Implemented, not independently validated**; forecast value not supported | Classifier F1 0.83 (E60); FSSI/topics served. In the Chapter III models NLP-only is the weakest arm and 4 of 5 triggers have zero SHAP importance (E99); E96 matched ablation shows no gain. |
| 2. LightGBM performance I–V | **Evaluated; criteria not met** | Accuracy, P/R, F1 and AUC reported (§4–§5). V: Maximum Reliable Lead Time **k\* = 0** under Algorithm 3. Algorithm 4 model not accepted. |
| 3. LGU rankings | **Met as relative ranking; H4 blocked** | 142/142 integrity, sensitivity, disclosure. Consistency with DA evaluators needs the ranking task. |
| 4. Baseline comparison (six models) | **Met as a comparison; superiority not met** | All six on identical folds (§4–§5); persistence is significantly better than LightGBM. |
| 5. Dashboard, ISO/IEC 25010, DOST-FNRI | **Dashboard implemented** (dev fixes pending approval); **ISO blocked** (0/50); **FNRI descriptive only** | §10–§12 |

## 14. Release gate

`release_gate.json`. A partial criterion counts as failed.

| Criterion | Result |
|---|---|
| Target and scope match the claims (G1) | **FAIL**: Chapter I claims province-level food-insecurity classification; only a proxy (Eq. 3) and a regional outcome exist |
| Lead-2 ≥ 75% on the approved target, defensible design (G2) | **FAIL**: Eq. 3 Lead 2, Chapter III model holdout 0.45. FIRI v2 0.85 is development-only, below persistence and not the Chapter III model. |
| Leakage and alignment (G3) | PASS |
| Generalisation evidence present (G4) | **FAIL**: seals PENDING |
| Fair baselines (G5) | PASS |
| Probabilities calibrated or not presented as such (G6) | PASS **on this branch** (wording fixed); production still shows the old wording |
| Feature groups assessed (G7) | PASS |
| 142-LGU and labels correct (G8) | PASS (dev branch) |
| ISO/IEC 25010 and FNRI evidence (G9) | **FAIL**: 0/50 responses |
| Backend and frontend tests (G10) | PASS: 603/0 backend, 75/0 frontend, build OK (§15) |
| Same version across artifact, evaluation and report (G11) | PASS (`release_candidate_manifest.json`) |
| Reproducible (G12) | PASS: rerun identical, seal hash reproduced |

**Deploy: NO.**

## 15. Tests

- **Backend full suite:** **603 passed, 18 skipped, 0 failed** (`backend_test_log.txt`).
  - Includes E97 (10), E98 (5) and E99 (6).
  - The first run failed 1 test, `test_e83_plain_explanations`, which required the price output as a percentage. It
    was resolved by the G6 rewording above.
  - The E98 version-identity test now checks E98's own commit blobs, so later branches can change serving files.
- **Frontend:** vitest 15 files / 75 tests passed. `vite build` succeeded locally (`frontend_test_log.txt`). Built,
  not deployed.
- **Passing software tests are not evidence of forecasting validity** (G2 and G4 still fail).

## 16. Remaining blockers and exact next steps

1. **G4 and G2:** score the seals with `prospective/score_sealed.py` when SWS 2026-Q4 is posted (about January 2027),
   then 2027-Q1. Do not retrain before scoring.
2. **G9 and H5:** build the Google Form from E98's DA questionnaire plus E99 Changes 1–2. Collect 50 eligible
   responses, export them to the templates, and run `score_evaluation.py`.
3. **H4:** the same form's Section 7, with at least 3 rankings in at least 4 provinces.
4. **G1:** either (a) obtain a provincial outcome (CBMS 2024 LGU food-shortage tables, via a PSA request), or (b) with
   your adviser, state in Chapter IV that provincial results are proxy-based (Eq. 3) and the measured validation is
   regional.
5. **Production, only with your authorization:**
   - port the E97 rollover fix (before 2027-01-01);
   - port the E99 wording fixes (G6).

   Neither changes a model.
6. **Document fixes for your adviser:**
   - window 2020–2025 → 2021–2026;
   - remove DEPDev (SOP 5);
   - NNS 2019 → ENNS 2021;
   - Algorithm 5 cites 2020 census density; the system uses POPCEN 2024.

## 17. Reproduction (from `backend/`)

```
py -3.13 ../aipheed-backend-aligned/experiments/E99_Chapter3_Evaluation/runner/chapter3_eval.py
py -3.13 ../aipheed-backend-aligned/experiments/E99_Chapter3_Evaluation/prospective/score_sealed.py
py -3.13 ../aipheed-backend-aligned/experiments/E99_Chapter3_Evaluation/evaluation_package/score_evaluation.py <iso.csv> <h4.csv>
<backend venv python> -m pytest tests/integration/test_e99_chapter3.py
```

- **Seeds:** LightGBM 99, Optuna TPE 99, bootstrap 99.
- **Determinism:** a full rerun reproduced every metric and the seal hash.
