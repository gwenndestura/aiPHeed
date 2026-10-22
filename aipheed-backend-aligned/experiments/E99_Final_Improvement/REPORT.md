# E99 (final improvement): outcome reliability, simple baselines, provincial data, labels, evaluation packages and production lock

**Branch.** `e99-final-improvement`, from `e98-acceptance-gate` (a42de8c).
**Protocol.** `PROTOCOL.md` (SHA-256 in `PROTOCOL.sha256`), committed 74884d8 before any scoring.

**Other E99.** `e99-chapter3-evaluation` (6da1054, pushed earlier, untouched) ran the Chapter III pipeline as written and
failed its own criteria (k\* = 0). It is cited, not repeated.

**Production: unchanged.** `final-system-v2` stays at 053a95d on origin. Nothing was merged, no production artifact was
changed, and no Render or Vercel deployment was triggered.

**Evidence status.** All historical results are **development evidence**: every SWS quarter to 2026-Q3 was examined
before E99.

**Files.**

| What | Where |
|---|---|
| Forecast evidence | `runs/*_forecast/` |
| Provincial data and Lucena | `runs/*_provincial/` |
| E98 reproduction | `runs/repro_e98/` |
| Label audit | `label_audit_before.json`, `label_audit_after.json` |
| Version manifest | `release_candidate_manifest.json` |
| Evaluation packages | `evaluation/` |
| Sealed-forecast scorer | `prospective/` |
| Gate | `release_gate.json` |
| Tests | `backend/tests/integration/test_e99_final_improvement.py` (16) |

## 1. Summary

1. **The regional outcome is itself survey-dependent.** SWS and OCTA hunger, two independent Balance Luzon surveys,
   agree on HIGH/LOW in only **3 of 7** common quarters (κ = 0.0).
   - Their levels move together (Spearman 0.77), but OCTA reads about 4.9 points lower.
   - They disagree exactly in 2023-Q4 to 2024-Q3, the onset period.
   - So "when food insecurity became elevated" depends on the survey, and any accuracy against either one is
     survey-specific.
2. **A trivial rule also clears 75%.** A 2-quarter moving average of posted SWS readings reaches **0.80** at Lead 2
   (FIRI v2: 0.933; persistence: 0.667).
   - The 75% threshold by itself therefore does not show FIRI's value.
   - FIRI's real advantage is in the **5 transition quarters**: FIRI 4/5, moving average 2/5, persistence 1/5. In
     regime quarters all of them score 10/10 or 9/10.
   - No model qualified for promotion (rule D), so FIRI v2 stays the best defensible index.
3. **No provincial food-insecurity outcome can be built from local data.** The PSA FIES 2021/2023 public-use files have
   no food-insecurity-experience module. Provincial food expenditure share and subsistence incidence do not order the
   provinces as FIRI does (n = 5, descriptive only).
4. **Lucena is ranked most vulnerable in Quezon on a weak substitute.** Its 16.8% poverty input is a province value.
   PSA's own municipal estimates for Lucena are 3.6–8.8% (2018: 6.5%). With its own 2018 value it ranks 14th, not 1st.
   FIRI is unaffected. **Not changed: needs your approval.**
5. **Probability wording fixed on this branch.** The price score, the hunger outlook, FIRI and the LGU index are no
   longer presented as probabilities. The audit went from **217 hits to 0** across every endpoint the frontend calls.
   Production still shows the old wording.
6. **Evaluation packages are ready; no responses exist.**
   - ISO/IEC 25010 scorer v2 with eligibility rules.
   - A new **H4 ranking-agreement task** with a pre-registered decision rule.
   - Both return NO_RESPONSES.
7. **Independent validation is PENDING.**
   - Both sealed FIRI v2 forecasts are HIGH (2026-Q4 regional mean 0.749; 2027-Q1 0.744).
   - **A 75% independent claim needs at least 12 scored quarters,** even if all are correct.
8. **The deployed model is the evaluated model.** All 8 model artifacts are byte-identical (LF-normalised) to production.
9. **Release gate: FAILED** (G1, G2, G4, G8, G9). **No deployment.**

## 2. What can genuinely improve forecasting (Question 1 of the brief)

| Possible source of improvement | Finding | Action |
|---|---|---|
| More legitimate history | Pre-2021 data excluded (study-window rule); new collection excluded (deadline rule). Local files hold no extra quarterly outcome. | None possible |
| A second outcome | OCTA Tugon ng Masa, 8 quarters (from E73, commit 0029bca). It disagrees with SWS on the class 4 of 7 times. | Used to show the outcome is survey-specific (§3) |
| Simpler forecast | MA2 clears 75% at Lead 2 but is below FIRI on transitions; MA4 is worse (0.533) | Not promoted (§4) |
| Better feature timing | Checked in E97 (Q1b–d) and in the other E99 (t − 1 for late releases) | No change needed |
| Better target | No provincial measured outcome; FIES PUF lacks an experience module (§5) | Target stays regional SWS |
| More model search | 13+ experiments on the same 13–17 quarters (E83–E99) | Not done: it would fit the examined quarters, not generalise |

## 3. Q1: reliability of the regional outcome (SWS vs OCTA, Balance Luzon)

| Quarter | OCTA % | SWS % | SWS > 11.3 | OCTA > 11.0 | FIRI Lead 2 |
|---|---|---|---|---|---|
| 2023-Q4 | 11 | 14.3 | HIGH | LOW | 0.40 (LOW) |
| 2024-Q1 | 9 | 15.3 | HIGH | LOW | 0.52 |
| 2024-Q2 | 11 | 19.6 | HIGH | LOW | 0.57 |
| 2024-Q3 | 7 | 18.1 | HIGH | LOW | 0.54 |
| 2024-Q4 | 23 | 25.3 | HIGH | HIGH | 0.58 |
| 2025-Q2 | 7 | — (no `definition_A` round) | — | LOW | 0.54 |
| 2026-Q1 | 16 | 22.4 | HIGH | HIGH | 0.58 |
| 2026-Q3 | 27 | 23.6 | HIGH | HIGH | 0.59 |

- **Agreement:** 3/7, κ = 0.0. The result is the same at an OCTA threshold of 11.3.
- **Levels:** Spearman ρ = 0.77; mean gap SWS − OCTA = +4.9 points.
- **On the 7 common quarters:**

  | | vs SWS | vs OCTA |
  |---|---|---|
  | FIRI | 0.857 | 0.571 |
  | Persistence (H1) | 0.714 | 0.714 |

**Conclusion.** The regional "measured outcome" is reliable in level trends, not in threshold crossings. FIRI's high
accuracy is accuracy against **SWS specifically**.

## 4. Q2–Q3: simple baselines and robustness (same quarters as E98 D)

**Lead 2** (15 quarters, 10 HIGH / 5 LOW):

| Arm | Accuracy | Balanced | AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|
| **FIRI v2** | **0.933** | **0.950** | **0.92** | 0.190 | 9/0/1/5 |
| MA2 | 0.800 | 0.850 | 0.70 | 0.200 | 7/0/3/5 |
| H1 (latest reading) | 0.667 | 0.600 | 0.75 | **0.183** | 8/3/2/2 |
| MA4 | 0.533 | 0.500 | 0.64 | 0.208 | 6/3/4/2 |
| Always HIGH | 0.667 | 0.500 | 0.50 | 0.333 | 10/5/0/0 |

**Lead 1** (16 quarters):

| Arm | Accuracy | Brier |
|---|---|---|
| FIRI | 0.875 | 0.191 |
| MA2 | 0.813 | **0.136** |
| H1 | 0.688 | 0.137 |
| MA4 | 0.688 | 0.156 |

At Lead 1, MA2 beats FIRI's Brier: −0.055, CI [−0.101, −0.003], sign p 0.004. FIRI is an index, not a probability, so
the Brier comparison is not like for like.

**Paired comparisons, Lead 2:**

| Comparison | Accuracy difference [CI] | Discordant quarters | Brier difference [CI] |
|---|---|---|---|
| MA2 − FIRI | −0.133 [−0.33, 0] | 0 / 2 | +0.009 [−0.09, 0.13] |
| MA2 − H1 | +0.133 [−0.13, 0.40] | 3 / 1 | — |

**Robustness of FIRI at Lead 2** (report only; the threshold stays 0.5):
- 5 of 15 quarters lie within ±0.05 of the threshold. The smallest margin is 0.019.
- Accuracy by threshold:

  | Threshold | 0.45 | 0.475 | **0.50** | 0.525 | 0.55 |
  |---|---|---|---|---|---|
  | Accuracy | 0.80 | 0.933 | **0.933** | 0.867 | 0.733 |

- Regime quarters (10, outcome class = latest reading's class): FIRI 10/10, MA2 10/10, H1 9/10.
- **Transition quarters** (5: 2022-Q4, 2023-Q1, 2023-Q4, 2024-Q1, 2024-Q2): **FIRI 4/5**, MA2 2/5, H1 1/5, MA4 0/5.

**Reading.**
- FIRI's genuine early-warning content is 4 transitions out of 5, in one episode, and it is sensitive to the
  threshold.
- That supports "promising regional early-warning index", not "validated".
- **Decision rule D:** no arm beats FIRI's Lead-2 accuracy, so nothing is promoted.

## 5. Q4: provincial measured data from existing local files

**PUF content.** FIES 2021 has 87 columns and FIES 2023 has 90. Neither has a food-insecurity-experience item (worried,
skipped meals, ran out of food, hungry). **So no provincial food-insecurity outcome can be derived.**

| Province | FIRI 2023 mean | Food share 2023 (RFACT-weighted) | Households with food share ≥ 0.65 | Subsistence incidence 2023 (CV) |
|---|---|---|---|---|
| Cavite | **0.544** | 0.408 | 1.3% | 0.8% (62%) |
| Quezon | 0.495 | **0.512** | **14.1%** | 0.9% (40%) |
| Rizal | 0.403 | 0.429 | 3.1% | 2.6% (25%) |
| Batangas | 0.389 | 0.392 | 0.7% | 1.4% (34%) |
| Laguna | 0.389 | 0.431 | 1.9% | 1.3% (35%) |

- **Correlation with FIRI** (Spearman, n = 5): food share 0.0, subsistence incidence −0.6.
- On economic access, Quezon is by far the most food-stressed province. FIRI ranks Cavite highest, through density and
  price pressure.
- Descriptive only: n = 5, annual data, and the CVs are high.
- Partly circular: V1 uses SAE poverty, which is modelled from FIES.
- **Conclusion.** The province-level differences FIRI shows are not supported by provincial welfare data. Province
  values must be read as regional risk with provincial modifiers, not as a provincial ranking of food insecurity.

## 6. Q5: Lucena substitute (Objective 3)

**Workbook** (`2018 - 2021 SAE_with PSGC_noHUC.xlsx`, sheets 2000–2018 and 2018–2021):
- The 2021 table excludes Lucena (a highly urbanized city).
- Lucena's own estimates:

  | 2003 | 2006 | 2009 | 2012 | 2015 | 2018 |
  |---|---|---|---|---|---|
  | 8.79% | 5.35% | 3.60% | 6.56% | 5.89% | **6.50%** (CV 17%) |

**Served value.** 16.8%: a stored province value, 2.6× Lucena's own 2018 estimate. It is not even the mean of Quezon's
2021 municipal estimates (20.3%).

**Effect.**
- Lucena ranks **1st** of 41 in Quezon (5th in the region) with the substitute, and **14th** with its own 2018 estimate.
- Other Quezon ranks are barely affected (ρ 0.984).
- **FIRI is unaffected:** `firi.vulnerability()` averages only LGU-specific estimates.

**Recommended change (needs your approval).** Use Lucena's 2018 PSA SAE, labelled "PSA 2018 SAE (latest municipal
estimate; the 2021 table excludes HUCs)". It is a one-value change in `data/inputs/lgu_vulnerability.csv`
(`poverty_value_used`, `poverty_source`). It touches only the LGU ranking and the H4 set.

## 7. Q6: probability wording (G6), development branch only

**Code changes:**
- `thesis_system.py`: province statement, A1 indicator, plain-language A1 card, regional hunger outlook, and a new
  `score_text()` that rewrites stored record texts.
- `dashboard.py`: thesis-mode heads, hunger and price parts, low-score back-test note, early-warning texts.
- `lgu_audit.py`: ranking-method text.

The other modes keep their wording. No frontend file was changed (approved-UI rule).

| Where | Before | After |
|---|---|---|
| Province statement | "The LightGBM food-price-pressure forecast is 7%." | "… food-price-pressure score is 0.07 (0-1; not a calibrated probability)." |
| Factor evidence (A1) | "7% chance of food-price pressure" | "food-price-pressure score 0.07 (0-1, not a calibrated probability)" |
| Plain card (A1) | "The price model gives a 7% chance that food prices … rise faster than usual" | "The price model rates the pressure of food prices … rising faster than usual … at 0.07 on a 0-1 scale (a rating, not a calibrated probability)" |
| Narrative | "model score 4%", "hunger part gives 96%", "(4%)", "price-pressure probabilities below 20%" | 0.04, 0.96, (0.04), "price-pressure scores below 0.20" |
| Early warning (stored text) | "food-price pressure 4%, HIGH-risk probability 4%" | "food-price pressure 0.04, HIGH-risk score 0.04" |
| Regional hunger outlook | "88% chance above 11.3%" | "outlook score 0.88 for hunger above 11.3% (0-1 … not a calibrated probability)" |
| LGU `rankingMethod` | "province probability x vulnerability" | "province estimate (the served province score) x vulnerability" |

**Audit** (`runner/label_audit.py`): 71 payloads, covering config, quarters, provinces, ranking, municipalities,
explainability, forecast, timeseries, report data and news, for 2027-Q1, 2026-Q3 and 2024-Q2.
- **217 → 0 hits.**
- Kept: PAGASA's own ENSO probabilities, quoted as PAGASA's.

**Found in the frontend.** `src/lib/pdfReport.ts` and `src/components/ForecastBanner.tsx` contain hard-coded mock
figures. Examples: "612K residents at heightened risk", "households requiring supplementary feeding", "Forecast
Probability".
- Neither is imported anywhere, and their text is absent from the built bundle, so they are **not shipped**.
- Recommended: delete them (needs your approval; not done under the approved-UI rule).

## 8. Tests and reproduction

- **Backend full suite:** **613 passed, 18 skipped, 0 failed.**
  - It includes 16 E99 tests.
  - The E98 version test was updated to exempt the three files E99 changed on purpose.
  - `test_e83_plain_explanations` was updated to check the 0–1 rating instead of a percentage.
- **Frontend:** vitest 15 files / 75 tests passed. `vite build` succeeded (local, not deployed).
- **Reproduction:** the E98 Question D rerun is identical to its committed run (`runs/repro_e98/repro_check.json`).
- **Version identity** (`release_candidate_manifest.json`):
  - All 8 model artifacts are identical to E98 and to production 053a95d. These are the FIRI history, evaluation,
    reference and anchors, the final evaluation, the E58 record, the SWS rounds and the LGU table.
  - Code differs from production only in `thesis_system.py`, `dashboard.py`, `lgu_audit.py` (E99 wording) and
    `e41_lead2.py` (E97 rollover fix).
- Passing tests show the software behaves as specified. They are **not** evidence of forecasting validity.

## 9. Independent evaluation (sealed forecasts)

**Status** (`prospective/score_sealed.py`; `prospective/status_20261022.json`):

| Target | Issued | Regional mean | Forecast | Status |
|---|---|---|---|---|
| 2026-Q4 | 2026-07-01 | 0.749 | HIGH | PENDING |
| 2027-Q1 | 2026-10-01 | 0.744 | HIGH | PENDING |

- Seal `e2bef0b2…` verifies (LF-normalised content).
- **Scoring procedure, unchanged:**
  1. When SWS posts the 2026-Q4 round, add it to `data/inputs/sws_rounds.csv` with its posting date and
     `definition_A`.
  2. Run the scorer: regional mean ≥ 0.5 vs H > 11.3%.
  3. No retraining, recalibration or threshold change.
  4. Repeat for 2027-Q1 and every later sealed quarter.
- **How much evidence is enough:** 12/12 correct is the minimum for a Wilson 95% lower bound above 0.75. While the
  outcome stays HIGH, persistence makes the same call, so each quarter tests little beyond the regime. Report OCTA
  alongside SWS whenever both are published.

## 10. Objective-to-evidence matrix (Chapter I)

| Objective / hypothesis | Classification | Evidence and exact reason |
|---|---|---|
| General: develop, validate, deploy | **Implemented, not independently validated** | Deployed (prod 053a95d). Validation is development-only; prospective is PENDING. |
| Obj 1: NLP pipeline (FSSI, BERTopic) | **Implemented, not independently validated**; forecast value **not met** | Classifier F1 0.83 (own test set); no forecast gain in matched ablations (E96, E97, other E99) |
| Obj 2 / SOP 2 / H2: Lead-2 province-level ≥ 75% | **Partially met** | Regional SWS: 0.933 development, survey-specific (OCTA agreement 3/7), and MA2 also reaches 0.80. Province-level outcome unavailable. Chapter III pipeline: k\* = 0 (other E99). |
| SOP 1 / H1: SHAP top predictors | **Partially met** | The other E99: H1 not rejected (food CPI deviation 3rd, FSSI 4th), from a model that failed acceptance |
| Obj 3 / SOP 4: LGU rankings | **Met** as a relative ranking, **one input defect** | 142/142, sensitivity done; Lucena substitute weak (rank 1 → 14), fix pending your approval |
| H4: rankings consistent with DA evaluators | **Blocked by participant responses** | H4 task and rule ready (`evaluation/h4_ranking.py`); 0 evaluators |
| Obj 4 / SOP 3 / H3: baselines | **Met** (comparison done); superiority **not met** | FIRI > persistence and MA2 at Lead 2 (development; not significant by sign test); Chapter III LightGBM < persistence (other E99) |
| Obj 5 / SOP 5 / H5: ISO/IEC 25010 | **Blocked by participant responses** | 0/50 eligible DA responses; scorer v2 ready |
| Obj 5: DOST-FNRI NNS 2019/2023 | **Partially met** (descriptive) | NNS 2019 CALABARZON figure does not exist; 2023 → 2025 direction agrees (E97) |

## 11. Release gate (`release_gate.json`)

| Criterion | Result |
|---|---|
| G1 target and scope | **FAIL**: province-level outcome unmeasurable; regional outcome survey-specific |
| G2 Lead-2 on the approved outcome | **FAIL**: development-only, regional; 75% also cleared by MA2 |
| G3 leakage and alignment | PASS |
| G4 independent evidence | **FAIL**: 0 scored prospective quarters (12 needed) |
| G5 fair baselines | PASS |
| G6 probability labels | PASS on this branch (0 audit hits); production still shows the old wording |
| G7 feature groups | PASS |
| G8 142-LGU outputs | **FAIL**: Lucena input defect (fix ready, needs approval) |
| G9 evaluation evidence | **FAIL**: 0 ISO and 0 H4 responses |
| G10 tests | PASS (backend 613/0, frontend 75/75, build) |
| G11 version identity | PASS |
| G12 reproducible | PASS |

**Deploy: no.**

## 12. Remaining blockers and exact next steps

1. **G4 / G2 (independent evidence).**
   - Score 2026-Q4 when SWS posts it (expected about January 2027), then every later quarter, with
     `prospective/score_sealed.py`.
   - At least 12 scored quarters are needed for an independent 75% claim.
   - State in Chapter IV that the 75% result is development evidence.
2. **G9 (H4, H5).**
   - Administer the DA questionnaire and the H4 ranking task to 50 DA Region IV-A evaluators, following
     `evaluation/README.md`.
   - Export to the templates and run both scorers.
   - Fix SOP 5's DEPDev wording in the manuscript.
3. **G8.** Approve the Lucena change (§6). It is a one-value data change, then re-run the E97 LGU tests.
4. **G1.** A provincial outcome needs data not in hand. Examples: CBMS household food items, or FNRI provincial FIES for
   all five provinces. Until then, state that the findings are regional (Balance Luzon) and survey-specific (SWS).
5. **Production hygiene (needs approval):**
   - port the E97 rollover fix and the E99 wording to `final-system-v2` before 2027-01-01;
   - delete the two unshipped mock files.

## 13. Reproduction (from `backend/`)

```
py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/runner/forecast_evidence.py
py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/runner/provincial_lucena.py
py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/runner/manifest.py <out.json>
py -3.13 ../aipheed-backend-aligned/experiments/E99_Final_Improvement/prospective/score_sealed.py <out.json>
<backend venv python> ../aipheed-backend-aligned/experiments/E99_Final_Improvement/runner/label_audit.py <out.json>
<backend venv python> -m pytest tests/integration/test_e99_final_improvement.py
```

`provincial_lucena.py` reads the PSA files in the user's `Downloads` folder (local, not collected online).
