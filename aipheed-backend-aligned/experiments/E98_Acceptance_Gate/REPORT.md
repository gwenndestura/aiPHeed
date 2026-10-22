# E98: direct food-insecurity target, acceptance gate and objective status (thesis evidence report)

**Branch.** `e98-acceptance-gate`, from `e97-validation-completion` (060fceb).
**Protocol.** `PROTOCOL.md` (SHA-256 in `PROTOCOL.sha256`), frozen and committed (f162987) before any E98 scoring.
**Runs.**
- `runs/*_direct/`: Question D
- `runs/*_diag_repro/`: Questions P and R
- `runs/repro_e97/`: fresh E97 re-runs

**Gate.** `release_gate.json`.
**Tests.** `backend/tests/integration/test_e98_acceptance_gate.py` (5).

**Release decision: DO NOT DEPLOY.** 5 of 12 gate criteria fail (G1, G2, G4, G6, G9).
- Production is unchanged: `final-system-v2` stays at 053a95d on origin.
- Nothing was merged, and no Render or Vercel deployment was triggered.

## 1. Requirement-to-evidence matrix (Chapter I objectives)

| Objective | Implemented | Partially validated | Demonstrably fails | Missing evidence | Completable now? |
|---|---|---|---|---|---|
| General: develop, validate, deploy | Yes (thesis system; Render/Vercel deployment of `final-system-v2`) | Development-only validation | — | Unseen-quarter validation | No: needs SWS 2026-Q4 and later |
| 1. NLP pipeline → FSSI and topics | Yes (classifier v2 F1 0.83, FSSI-v3, BERTopic) | Classification metrics | Forecast gain from news (E96, E97 Q3/Q5) | Fuller 2021–23 text archive | No: new collection out of scope |
| 2. LightGBM metrics I–V | Yes (both leads) | Lead 1 on T43 | Lead-2 T43 ≥ 75% (0.72) | Provincial measured outcome; unseen quarters | No |
| 2 (regional measured outcome) | FIRI v2 at Lead 1 and 2 | 0.875 / 0.933 (development) | — | Unseen quarters | No: wait for SWS |
| 3. LGU rankings | Yes, 142/142 | Sensitivity (E97) | — | LGU outcome to validate weights; Lucena PSA value | Lucena value needs a PSA HUC table |
| 4. Baselines (persistence, PSA-only, NLP-only, LR) | Yes, same origins (E97 Q5) | — | LightGBM not significantly better than climatology; PSA-only better on its own rows | — | Done |
| 5. Dashboard, ISO/IEC 25010, DOST-FNRI | Dashboard yes; ISO instrument and scorer; FNRI direction check | FNRI descriptive | — | 50 DA responses; NNS 2019 regional figure (does not exist) | No: needs participants |

## 2. Root causes (cumulative E83–E98, verified here)

1. **The intended outcome does not exist at the intended resolution.**
   - The only quarterly measured food-insecurity series is SWS hunger for Balance Luzon.
   - Every provincial "accuracy" is therefore against a proxy (T43 = price pressure) or against the shared regional value.
2. **About 15 labelled regional quarters, mostly one regime switch.**
   - 2022–23 LOW, 2024–26 HIGH, driven by one episode (the 2023–24 El Niño and production shock).
   - Supervised models trained on the early quarters cannot learn the switch before it happens (E98 D, E90).
3. **The price-pressure model's memory of past inflation** both detects the 2023–24 rise and causes the 2025–26 false
   alarms (E95). That is also why PSA-only beats it on its eligible rows (E98 P, below).
4. **News coverage is too thin in the training years** to add forecast value (E96).
5. **The ISO/IEC 25010 evaluation has not been administered.** The draft also targeted the wrong agency (DOST).

## 3. Experiments run in E98

### Question D: models trained directly on the measured outcome R (walk-forward, regional)

**Lead 2** (15 quarters, 10 HIGH / 5 LOW):

| Arm | Accuracy (Wilson 95%) | Balanced | Precision / Recall (HIGH) | F1 | AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|
| **FIRI v2 (served)** | **0.933** [0.70, 0.99] | **0.950** | 1.00 / 0.90 | 0.95 | **0.92** | 0.190 | 9/0/1/5 |
| H1 persistence outlook | 0.667 [0.42, 0.85] | 0.600 | 0.73 / 0.80 | 0.76 | 0.75 | **0.183** | 8/3/2/2 |
| D1 LR(H_last) | 0.467 | 0.450 | 0.63 / 0.50 | 0.56 | 0.45 | 0.360 | 5/3/5/2 |
| D2 LR(H_last, C_reg) | 0.467 | 0.450 | 0.63 / 0.50 | 0.56 | 0.45 | 0.331 | 5/3/5/2 |
| D3 LR(H_last, C_reg, E_reg) | 0.667 (all values are H1 fallbacks: E_reg is missing at early origins) | 0.600 | 0.73 / 0.80 | 0.76 | 0.75 | 0.183 | 8/3/2/2 |
| Always HIGH | 0.667 | 0.500 | 0.67 / 1.00 | 0.80 | 0.50 | 0.333 | 10/5/0/0 |

**Lead 1** (16 quarters, 11 HIGH / 5 LOW):

| Arm | Accuracy | Balanced | AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|
| **FIRI v2** | **0.875** [0.64, 0.97] | **0.909** | **0.89** | 0.191 | 9/0/2/5 |
| H1 | 0.688 | 0.609 | 0.83 | **0.137** | 9/3/2/2 |
| D1 / D2 | 0.563 | 0.518 | 0.65 / 0.68 | 0.223 / 0.208 | 7/3/4/2 |
| Always HIGH | 0.688 | 0.500 | 0.50 | 0.313 | 11/5/0/0 |

**Paired comparisons, quarter bootstrap (seed 98):**

| Comparison | Accuracy difference [95% CI] | Discordant quarters | Brier difference [95% CI] |
|---|---|---|---|
| FIRI − H1, Lead 2 | +0.267 [0.07, 0.47] | 4 / 0 | +0.008 [−0.10, 0.10] |
| FIRI − H1, Lead 1 | +0.188 [0.00, 0.38] | 3 / 0 | +0.054 [0.004, 0.10] |
| D1 − H1, Lead 2 | — | — | +0.177 [0.005, 0.37]: worse than persistence |

**Rising stress.**
- Lead-2 onsets (2023-Q4, 2024-Q1, 2024-Q2): FIRI caught 2, H1 1, D1/D2 1.
- Lead-2 recoveries (2022-Q4, 2023-Q1): FIRI correct in 2, every other arm 0.

**Leakage audit.** Every training pair's outcome was posted before its issue date, at both leads.

**Decision rule D.** No direct arm passes. The fitted direct models are worse than persistence, because they learn from
7–8 mostly-LOW quarters and then meet the high regime.
- **FIRI v2 remains the best defensible regional model.**
- **No regional probability is offered.** FIRI stays labelled "not a probability".
- **75% Lead-2 on the intended outcome:** met as development evidence on the regional outcome (0.933 > 0.75, above H1
  and always-HIGH). **Not independently validated, and not at province level.**

### Question P: why PSA-only beat LightGBM on its eligible Lead-1 rows

- **Eligibility.** PSA-only issues only 2024-Q4..2026-Q3 (6 quarters, 30 rows). It needs complete price-driver history.
  2023-Q1..2024-Q3 are ineligible.

| Target | HIGH rows | PSA-only accuracy | LightGBM accuracy |
|---|---|---|---|
| 2024-Q4 | 3/5 | 0.6 | **0.8** |
| 2025-Q1 | 4/5 | 0.8 | **1.0** |
| 2025-Q4 | 0/5 | **1.0** | 0.4 |
| 2026-Q1 | 0/5 | 1.0 | 1.0 |
| 2026-Q2 | 1/5 | **0.8** | 0.6 |
| 2026-Q3 | 0/5 | **1.0** | 0.8 |

- LightGBM is better in the rising quarters. PSA-only is better in the falling-price 2025–26 quarters, where
  LightGBM's inflation memory (cumF4, E95) raises false alarms.
- **The PSA-only advantage is a regime effect on 6 quarters**, not evidence of a better general model. No arm was
  retuned.

### Question R: reproducibility and version identity

- Fresh re-runs of the E97 FIRI validation and Objective 4 scripts (`runs/repro_e97/`) are **identical** to the
  committed E97 outputs, excluding time stamps.
- **14 served artifacts and serving files are unchanged since 060fceb**, so the model version, the evaluation and the
  report all refer to the same files. Their SHA-256 values are in `diagnose_and_reproduce.json`. The 14 are:
  - FIRI history, evaluation, reference and anchors;
  - the final evaluation;
  - the E58 record;
  - the SWS rounds and the LGU table;
  - six serving modules.

### Objective 5 instruments

- `instrument/DA_ISO25010_Questionnaire.md`: retargeted from DOST to **DA Region IV-A**, 50 evaluators.
  - Items 1–15 keep their wording, so the E97 scorer applies unchanged.
  - Non-DA respondents are excluded from the Chapter I sample.
- **Responses on file: 0.** Nothing is scored.
- **DOST-FNRI** (repository sources only, no web collection):
  - NNS 2019 has no CALABARZON regional FIES. The 2019 round covered 2 provinces (E22).
  - 2021 provincial CIs overlap.
  - 2023 → 2025 direction agrees with SWS and FIRI (E97).
  - This is a descriptive comparison only. Direct validation is not possible with these data.

## 4. Best defensible model and its evaluation

**FIRI v2 (C3), as served.** Unchanged, because no E98 candidate qualified.

**Scope.**
- Regional food-insecurity risk index (SWS hunger > 11.3%), Lead 1 and Lead 2.
- Province values share the regional outcome and are not validated provincially.

| Lead | Quarters | Accuracy | Balanced | Precision (HIGH) | Recall (HIGH) | F1 | AUC | Brier (index as score) | vs H1 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 16 | 0.875 | 0.909 | 1.00 | 0.82 | 0.90 | 0.89 | 0.191 | 3 better / 0 worse |
| 2 | 15 | 0.933 | 0.950 | 1.00 | 0.90 | 0.95 | 0.92 | 0.190 | 4 better / 0 worse (sign p 0.125) |

All of these quarters were examined during development.

## 5. Objective classification

| Objective | Classification | Reason |
|---|---|---|
| 1. NLP pipeline | **Implemented but not yet independently validated** (forecast value: not met) | Pipeline built, classifier F1 0.83 on its own test set; matched ablations show no forecast gain |
| 2. Forecasting performance (Lead-2 ≥ 75%) | **Partially met** | Regional measured outcome: 0.933 at Lead 2 (development only). Province-level measured target unavailable. T43 proxy Lead 2: 0.72. No unseen quarter yet. |
| 3. LGU rankings | **Met with adequate evidence**, as a relative vulnerability ranking | 142/142 integrity and map join tested; sensitivity done; Lucena substitute disclosed; not a probability |
| 4. Baseline comparison | **Met** (comparison completed); superiority **not met** | Same-origin table; no significant gain over the strongest simple baseline on T43; FIRI beats persistence on the regional outcome, but the sign test is not significant |
| 5. Dashboard, ISO/IEC 25010, FNRI | **Blocked by participant responses** (ISO); FNRI **partially met** (descriptive only) | 0/50 DA responses; NNS 2019 regional figure does not exist |

## 6. Release gate

See `release_gate.json`. A criterion that is partial or cannot be verified counts as failed.

| Criterion | Result |
|---|---|
| G1 intended target | FAIL: province-level food-insecurity target unmeasurable; regional only |
| G2 Lead-2 ≥ 75% on approved target | FAIL: regional and development-only |
| G3 leakage | PASS |
| G4 generalisation evidence present | FAIL: no unseen quarter scored |
| G5 comparable baselines | PASS |
| G6 calibrated probabilities | FAIL: the price-pressure % shown in the province detail has no demonstrated probability quality (E56 Lead-2 vs climatology CI reaches 0) |
| G7 feature groups | PASS |
| G8 LGU integrity | PASS |
| G9 ISO/IEC 25010 and FNRI | FAIL: 0/50 responses |
| G10 tests | PASS |
| G11 version identity | PASS |
| G12 reproducible | PASS |

**Deploy: no.** E98 changed no production artifact and no serving behaviour. Its only code is experiment scripts and
tests. The E97 target-quarter fix remains on the development branches only.

## 7. Tests (this branch)

- **Backend full suite:** 597 passed, 18 skipped, 0 failed. This includes the E97 (10) and E98 (5) tests.
- **Frontend:** `vitest run` 15 files / 75 tests passed. `vite build` succeeded locally (built, not deployed).

## 8. Remaining blockers and exact next steps

1. **G4 and G2 (independent evidence).**
   - When SWS posts 2026-Q4 (expected about January 2027), score `FINAL_Thesis_System/out/firi2_sealed_prospective.csv`
     (issued 2026-07-01) by the E97 rule: regional mean ≥ 0.5 vs H > 11.3%.
   - Score 2027-Q1 when it is posted.
   - Do not retrain before scoring.
2. **G9.**
   - Convert `instrument/DA_ISO25010_Questionnaire.md` into the Google Form.
   - Collect 50 DA Region IV-A responses and export them to the template.
   - Run `score_iso25010.py`.
3. **G6.** Either remove the percentage wording of the price-pressure forecast from the province detail text, or show it
   as a "price-pressure score" without "%". This is a text change in `thesis_system.index_rows`; it needs your approval
   before it goes to production.
4. **G1.** A provincial food-insecurity outcome would be needed. Examples: PSA CBMS 2024 household food items, or FNRI
   provincial FIES for all five provinces. This is a data request, outside the deadline rule. Until then, Chapter IV
   must state that the conclusions are regional.
5. **Before 2027-01-01**, if production is to stay usable: the E97 rollover fix must be ported to `final-system-v2`
   with your approval. It is a correctness fix, independent of the model gate.

## 9. Reproduction (from `backend/`)

```
py -3.13 ../aipheed-backend-aligned/experiments/E98_Acceptance_Gate/runner/direct_target.py
py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/runner/firi_validation.py
py -3.13 ../aipheed-backend-aligned/experiments/E97_Validation_Completion/runner/objective4_t43.py
# move the two new E97 run folders into E98_Acceptance_Gate/runs/repro_e97/, then
py -3.13 ../aipheed-backend-aligned/experiments/E98_Acceptance_Gate/runner/diagnose_and_reproduce.py
<backend venv python> -m pytest tests/integration/test_e98_acceptance_gate.py
```
