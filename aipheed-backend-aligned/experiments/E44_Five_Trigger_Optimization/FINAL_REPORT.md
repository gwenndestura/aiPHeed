# E44 (with the second E43 brief): five-trigger Lead-2 optimization, final report

**Date:** 2026-10-16.
**Branch:** `e43-five-trigger-risk` (local, not pushed).

**Experiment folders**, all preserved:

| Folder | Status |
|---|---|
| E41 | preserved, unchanged |
| E42 | preserved, unchanged |
| E43 | preserved; byte-identical repeat verified |
| E44 (this report) | `aipheed-backend-aligned/experiments/E44_Five_Trigger_Optimization/` |

## Acceptance decision

| Requirement | Status |
|---|---|
| All five trigger groups in training **and** inference of the final model | **MET**: code, tests and frozen feature lists (section 5) |
| ≥ 75% Lead-2 accuracy with balanced HIGH/LOW discrimination (gates A1 + A2) | **NOT MET**. The best five-trigger candidate (I2) reaches 0.686 accuracy (balanced 0.716). |
| Beats always-LOW and persistence on Brier (A3) | MET by I2 (point estimates; not significant with 7 quarters) |
| Calibration-in-the-large (A4) | MET by I2 |
| Leakage-safe, chronological evaluation (A0) | MET (E44 tests) |
| Software (backend, API, dashboard, tests) | **Complete and tested** behind `AIPHEED_LEAD2_MODEL=e44`. The production default (E38) is unchanged. |
| DA IV-A participant validation | **Not done; not claimed** |

**The forecasting objective is not complete.** The final candidate is served as "FORECASTING ACCEPTANCE NOT MET". Section 7 documents the blocker with evidence.

---

## 1. Root causes of the previous failures

| # | Cause | Evidence |
|---|---|---|
| R1 | The served v1 label is **relative** (trailing median) and drifts with regional hunger: 90–95% HIGH in 2024–26. The old 0.95 scores were probabilities of that label. | E41–E43 audits |
| R2 | The Chapter I target **T43** (SWS hunger + PSA price signal, E40 thresholds, single quarter) is rare per province-quarter: 19% HIGH, 16 HIGH rows in 12 quarters. Direct classifiers have 3–16 HIGH training rows. | E43 |
| R3 | Since 2023-Q4, approved SWS hunger is above 11.3 in every quarter, so T43 is mostly a **provincial price event** in the evaluation window. | `sws_rounds.csv` |
| R4 | `scale_pos_weight` inflated E43's LightGBM: calibration-in-the-large −0.40. | E43 |
| R5 | **National employment and OFW levels act as time proxies:** masking employment moved E43 LightGBM probabilities by −0.54. | E43 |
| R6 | Few independent outer quarters (7 here), all seen before; the E40 holdout is exposed (E41 C-1). | – |
| R7 *(found in E44)* | Blocked leave-one-quarter-out inner validation on an autocorrelated series favours flexible models that do not hold forward in time. | I2/I4 selection logs (LightGBM with 4 leaves at every origin) |

## 2. What was changed to resolve them (five pre-registered iterations, all reported)

**Freezing:** every iteration was frozen before it was scored. `PROTOCOL.md` (I1–I3, sha in `runner/PROTOCOL_SHA256.txt`), `ADDENDUM_I4.md` and `ADDENDUM_I5.md`.

**Outer set S44:** 2024-Q3..2026-Q3, **7 quarters, 35 province-quarters, 9 HIGH**. The rows are identical for every arm.

| Iteration | Substantive change (and why) | Accuracy (95% CI) | Balanced | HIGH / LOW recall | Brier | AUC | Gates |
|---|---|---|---|---|---|---|---|
| I1 | Nested-tuned classifiers: 132 configurations (LightGBM and LR × class weight × three five-trigger feature sets × window). Inner leave-one-quarter-out, Platt, threshold. Employment/OFW levels replaced by YoY changes (R4, R5). | 0.257 (0.09–0.46) | 0.209 | 0.11 / 0.31 | 0.375 | 0.27 | fail |
| **I2** | **Five-trigger component model:** P = P(H > 11.3) × P(price signal). The price signal comes from a base-effect projection plus a five-trigger residual model trained on all CPI quarters, about 5 times more observations (R2, R3). Hunger comes from a ridge on regional trigger signals. | **0.686 (0.46–0.89)** | **0.716** | 0.78 / 0.65 | **0.181** | 0.60 | A1 fail; A0, A2, A3, A4 pass |
| I3 | I2 plus the SWS supplementary rounds as extra hunger observations (more valid observations) | 0.600 | 0.658 | 0.78 / 0.54 | 0.177 | 0.63 | fail |
| I4 | Joint food/gap predictive distribution: corrects I2's uncertainty structure for the "food minus headline" signal | 0.543 | 0.438 | 0.22 / 0.65 | 0.191 | 0.51 | fail |
| I5 | I4 with forward-chaining inner validation everywhere, plus a stronger ridge option (R7) | 0.400 | 0.451 | 0.56 / 0.35 | 0.262 | 0.44 | fail |

**I2 detail:**
- Confusion matrix: TP 7, TN 17, FP 9, FN 2. Precision 0.44; F1 0.56; PR-AUC 0.51 (prevalence 0.26).
- Log loss 0.54. Calibration-in-the-large −0.08 (CI −0.27..0.16).
- **By quarter:**

| Quarter | Accuracy | HIGH rows |
|---|---|---|
| 2024-Q3 | 0.8 | 1 |
| 2024-Q4 | 0.6 | 3 |
| 2025-Q1 | 0.8 | 4 |
| 2025-Q4 | 0.2 | 0 |
| 2026-Q1 | 1.0 | 0 |
| 2026-Q2 | 0.4 | 1 |
| 2026-Q3 | 1.0 | 0 |

- **Longer history** (2024-Q2..2026-Q3, 8 quarters): 0.625 / balanced 0.603.

## 3. Target definition and rationale

**T43, unchanged from E43:**
- **Rule:** a province-quarter is HIGH if SWS Balance Luzon hunger is above 11.3 **and** the province's food YoY is above its frozen 2021–22 P60 (or food minus headline is above its P60), in the target quarter.
- **Why:**
  - it uses Chapter I §1.7's two sources;
  - its references are frozen, so it does not drift;
  - its meaning was fixed before any model.
- **What it is not:** an independently verified provincial food-insecurity outcome. No such series exists.
- **Approval needed:** it drops E40's sustain-2 rule, so it needs adviser approval.
- **Not re-selected after seeing results:** alternatives (v1, E40 sustain-2, hunger only, L4) are in E43 §3. Changing the target now would be redefining success after seeing results.

## 4. Data and features for all five triggers

**Feature code:**
- `runner/e44_classifiers.py::features` and `F5_GROUPS`;
- `runner/e44_components.py::features`, `PRICE_GROUPS` and `HUNGER_GROUPS`;
- built on E43's `e43_lib.features`/`cut_extra` and E41's `e41_lib.features`.

| Trigger | Official source, level | Features (as of origin O(t)) | Timing logic |
|---|---|---|---|
| **Market** | PSA CPI food/headline (published YoY and index), province; PSA wholesale rice, province | F_hat_M1 (base-effect projection), F_now, D_now, gap_now, rice_whsl_yoy | CPI months ≤ month 2 of t; rice ≤ t−1 (`e41_lib.Data.cut`, `e43_lib.cut_extra`) |
| **Climate** | NOAA IBTrACS typhoon tracks within 300 km, province; NOAA CPC ONI; PSA palay/corn production, province | tc_count (t), tc_count_l1 (t−1), enso (t−1), enso_l2 (t−2), palay_yoy, corn_yoy; interactions enso×mom3, tc_l1×palay | typhoons ≤ t, ENSO ≤ t−1 (`cut_extra`); production ≤ t−1 |
| **Fish Kill** | PSA fisheries and aquaculture production, province | fish_yoy, aqua_yoy | ≤ t−1 |
| **Employment** | PSA LFS unemployment and underemployment, **national** | ur_yoy, under_yoy (levels removed per R5) | months of quarters ≤ t−1 |
| **OFW Remittance** | BSP cash remittances (curated, **national**, to 2025-Q4); ECB USD/PHP | remit_usd_yoy, remit_php_yoy, fx_yoy | ≤ t−1 |
| News (all five) | E31 province-attributed titles | five trigger shares, news_n | quarter ≤ t |

**Data obstacles that remain** (searched in E42–E44; PSA OpenStat catalogue checked):
- no PAGASA in-window provincial series (NOAA used and labelled as such);
- no BFAR fish-kill event series;
- no regional or provincial quarterly LFS;
- no regional remittances; BSP blocks programmatic re-download;
- news is titles only.

Missing values stay missing: LightGBM receives NaN; ridge and LR get median imputation plus missing indicators.

## 5. Evidence that all five triggers reach training and inference

**Tests** (`tests/test_e44.py`, 16 passing):

| Test | Checks |
|---|---|
| `test_every_candidate_feature_set_covers_the_five_triggers` | every I1 set, and both I2 components, have features from all five groups; employment and OFW levels are excluded |
| `test_five_triggers_reach_training_and_inference` | the fitted I2 price model's columns and its per-feature contributions at inference include all five groups; the hunger model's columns include all five |
| `test_i4_ignores_post_origin_data_and_uses_five_triggers`, `test_i5_forward_inner_validation_and_leakage` | the same for I4/I5, plus leakage |
| `test_prospective_freeze_intact` | the frozen 2027-Q1 record lists I2's price features covering all five groups |

**Served-model attribution at the 2027-Q1 origin** (`backend/data/e44/e44_record.json` → `fiveTriggerContributions`):

| Trigger | Price (food-YoY points) | Hunger (H points) | Status |
|---|---|---|---|
| Market | −0.04 to +0.10 | −1.41 | contributes |
| Climate | +0.13 to +0.29 | +3.84 | contributes |
| Fish Kill | 0.00 | −0.36 | contributes |
| Employment | −0.35 | −6.07 | contributes |
| OFW | +0.01 to +0.03 | +0.82 | contributes |

All five are above the 0.1-point "contributes" rule. **Caution:** the hunger contributions rest on about 16 regional observations, and the employment term is national, so they are fragile.

## 6. Five-trigger value: comparison with market-only, add-one and drop-one

All on S44, same rows.

| Model | Accuracy | Balanced | Brier |
|---|---|---|---|
| **I2 (all five + news)** | **0.686** | **0.716** | **0.181** |
| I2-MKT (market only, random-walk hunger) | 0.314 | 0.248 | 0.405 |
| market + climate | 0.600 | 0.404 | 0.263 |
| market + fish | 0.514 | 0.382 | 0.271 |
| market + employment | 0.371 | 0.432 | 0.339 |
| market + OFW | 0.257 | 0.246 | 0.301 |
| market + news | 0.371 | 0.286 | 0.289 |
| I2 − market | 0.686 | 0.643 | 0.187 |
| I2 − climate | 0.457 | 0.489 | 0.288 |
| I2 − fish | 0.543 | 0.438 | 0.235 |
| I2 − employment | 0.714 | 0.553 | 0.230 |
| I2 − OFW | 0.457 | 0.380 | 0.319 |
| I2 − news (= GOV) | 0.571 | 0.603 | 0.192 |
| NLP only | 0.571 | 0.421 | 0.278 |

**What this shows:**
- The five-trigger model is clearly better than the market-price-only model: Brier gain +0.225, Holm p = 0.18.
- Removing climate, OFW or fish worsens it most.
- Removing employment raises accuracy but halves balanced accuracy.
- News adds a little: balanced 0.716 vs 0.603 without it.

These are 7-quarter results and are not significant after correction.

## 7. Baselines, uncertainty and the blocker

**Baselines and comparators on S44:**

| Model | Accuracy | Balanced | HIGH recall | Brier | AUC |
|---|---|---|---|---|---|
| Always-LOW | 0.743 | 0.50 | 0.00 | 0.220 | – |
| Persistence | 0.543 | 0.583 | 0.67 | 0.457 | – |
| Climatology | 0.743 | 0.50 | – | 0.210 | – |
| SIM-0 | 0.771 | 0.628 | 0.33 | 0.176 | 0.70 |
| SIM-5T (no fish input, so not five-trigger) | 0.743 | 0.682 | 0.56 | 0.174 | 0.73 |
| E41-M1 (price only) | 0.771 | 0.592 | 0.22 | 0.164 | 0.70 |
| E38-served (scored on T43) | 0.143 | – | – | 0.653 | – |
| E43 LGBM-COMB (on its 5-quarter subset) | 0.56 | – | – | 0.275 | – |

On that same 5-quarter subset, I2 scores 0.68 (Brier 0.179).

**Uncertainty:** with 7 quarters, I2's accuracy CI is 0.46–0.89, and no paired Brier difference is significant after Holm correction.

**The blocker, demonstrated** (`runs/blocker/discrimination_ceiling.json`; a diagnostic, never used to select anything):
- **Even with the best threshold chosen in hindsight, no model reaches A1 + A2.** The closest is SIM-5T at 0.743.
- **The ranking quality needed is not there.** At this class balance (9 HIGH / 35), a binormal model needs AUC ≈ 0.78 to meet A1 + A2. The five-trigger candidates reach AUC 0.27–0.63, and the best model of any kind reaches 0.73.
- **The shortfall is in discrimination, not threshold or calibration.** Two quarters ahead, the provincial price signal and the regional hunger level are only weakly predictable with the official data available in-window.

**What would resolve it:**
1. More independent outcome quarters. Prospective scoring starts with 2027-Q1, frozen in `frozen/E44_PROSPECTIVE_2027Q1.json`.
2. A provincial hunger or FIES series, so provinces differ on hunger, not only on prices.
3. Provincial employment and remittance data, instead of national series.
4. PAGASA provincial rainfall and typhoon impact data, and BFAR fish-kill events.
5. Article-text news collected live.

None of these can be obtained from the repository or official open APIs today.

## 8. Risk-score calibration and realism

- I2's served value is a Platt-recalibrated probability of the T43 event, with calibration-in-the-large about 0 on S44.
- **For 2027-Q1 the probabilities are compressed (0.19–0.21).**
  - Hunger above 11.3% is likely: 0.96.
  - The price signals differ by province: Quezon 0.48, Laguna 0.30, Batangas 0.30, Cavite 0.26, Rizal 0.23.
  - The recalibration shrinks these toward the base rate.
- **Decisions at the training-selected threshold 0.2:** Quezon HIGH; the other four LOW.
- These are differentiated only modestly, which is what the evidence supports. **They are not household food-insecurity probabilities**, and the old 0.95 scores are not repeated.

## 9. Dynamic dashboard target (tested)

`backend/app/quarterly/target.py`: the viewing quarter q gives latest completed q−1, current q, and target q+1 (Lead 2 from q−1). Nothing is hard-coded.

`tests/integration/test_dynamic_target.py::test_dashboard_rule_table_e44` checks:

| Viewing | Latest completed | Current | Target |
|---|---|---|---|
| Q4 2026 | Q3 2026 | Q4 2026 | Q1 2027 |
| Q1 2027 | Q4 2026 | Q1 2027 | Q2 2027 |
| Q2 2027 | Q1 2027 | Q2 2027 | Q3 2027 |
| Q3 2027 | Q2 2027 | Q3 2027 | Q4 2027 |
| Q4 2031 | Q3 2031 | Q4 2031 | Q1 2032 |

- **On every Lead-2 response:** `/api/v1/lead2/*` returns `timing` = {originQuarter, currentQuarter, targetQuarter, leadFromOrigin: 2, issuedAt, convention}.
- **Expired forecasts:** an expired forecast returns 409, and an unforecast quarter returns 404. No stale substitution.

## 10. Files changed (E44 stage) and why

**Experiment:**

| File | Purpose |
|---|---|
| `PROTOCOL.md`, `ADDENDUM_I4.md`, `ADDENDUM_I5.md` (+ sha files) | pre-registration |
| `runner/e44_classifiers.py` | I1: features, the 132-configuration grid, nested selection |
| `runner/e44_components.py` | I2–I5: component models |
| `runner/e44_evaluate.py`, `runner/e44_evaluate_i4.py`, `runner/e44_evaluate_i5.py` | runners |
| `tests/test_e44.py` | 16 tests |
| `runs/20261015T150213Z`, `runs/i4_*`, `runs/i5_*` | runs and repeats |
| `runs/blocker/discrimination_ceiling.json` | blocker evidence |
| `frozen/E44_*PROSPECTIVE_2027Q1.json` | freezes |

**Backend:**

| File | Change |
|---|---|
| `app/ml/inference/e41_lead2.py` | e44 mode; `trigger_evidence()` |
| `app/services/dashboard.py` | `evidenceNote` per trigger |
| `app/schemas/public.py` | `Trigger.evidenceNote` |
| `app/api/v1/lead2.py` | `timing` block; optional record keys |
| `app/api/v1/insights.py` | candidate explainability note, so the text no longer says "only Market / Prices is an input" when all five are |
| `app/api/v1/dashboard.py` | `/config`, `/provinces` and municipalities use `indicator_for(quarter)` |
| `scripts/build_record_e44.py` | builds `data/e44/e44_record.json`; asserts the refit reproduces the frozen probabilities |
| `tests/integration/test_e44_final_candidate.py` | 6 tests |
| `tests/integration/test_dynamic_target.py` | +5 cases |

**Frontend** (wording defects the user asked to fix):

| File | Change |
|---|---|
| `src/lib/driverCopy.ts`, `src/lib/apiTypes.ts` | model-attributed trigger shows "raises/lowers the forecast" plus the actual evidence |
| `src/components/LeftPanel.tsx` | the note no longer claims "PSA production data already published"; the LGU text no longer says "validated province forecast" |
| `src/test/driverCopy.test.ts` | test |

## 11. Test results and commands

| Suite | Result |
|---|---|
| E44 | 16 passed; every run repeated **byte-identically** (run 1 `20261015T215924Z`, I4 `i4_20261015T220557Z`, I5 `i5_20261015T221121Z`: same prediction and results hashes) |
| E43 | 12 passed |
| Backend | **337 passed, 18 skipped** (long-standing superseded tests) |
| Frontend | vitest **36/36**; `vite build` OK; `tsc` shows the same 6 errors as the approved baseline |

**Live check** (approved UI against the E44 API, Quezon, Q1 2027):
- note: "Lead 2: issued 2026-10-01 (latest completed quarter 2026-Q3) for 2027-Q1; experimental (E44)";
- trigger composition: Climate 50%, Employment 38%, Market 6%, OFW 5%, Fish 1%;
- each card reads "raises/lowers the forecast" with its official observation.

**Reproduce:**
```
backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider aipheed-backend-aligned/experiments/E44_Five_Trigger_Optimization/tests
cd aipheed-backend-aligned/experiments/E44_Five_Trigger_Optimization && ../../../backend/venv/Scripts/python.exe -B runner/e44_evaluate.py && ../../../backend/venv/Scripts/python.exe -B runner/e44_evaluate_i4.py && ../../../backend/venv/Scripts/python.exe -B runner/e44_evaluate_i5.py
cd backend && venv/Scripts/python.exe -B scripts/build_record_e44.py && venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
```

## 12. Limitations and final decision

**Limitations:**
- 7 outer quarters, five looks at them (I1–I5; disclosed).
- The target needs adviser approval.
- SWS is regional; employment and OFW are national.
- The served probabilities are compressed by recalibration.
- The hunger component's trigger effects rest on about 16 regional observations.

**Software readiness:**
- complete and tested;
- ready for a **controlled demonstration** behind `AIPHEED_LEAD2_MODEL=e44`.

**Forecasting readiness:**
- **acceptance NOT met** (A1);
- Lead-2 operational use remains experimental;
- the default stays E38 until a candidate passes the gates and you decide.

**Next:**
- score 2027-Q1 prospectively once its SWS round and CPI are released;
- pursue the data in section 7.

**DA validation:** has not happened and is not claimed.

---

## Correction (E46, 2026-10-17): defects found in the I2 price and decision layers

E46 found three defects in the I2 component model, which E44 serves behind `AIPHEED_LEAD2_MODEL=e44`. The scores reported above are correct measurements of the procedure as frozen; they are not changed. What changes is the interpretation.

| Defect | What happens | Effect |
|---|---|---|
| **D1 (I2, I3, I2 variants)** | The food residual model corrects projected food YoY (+2.6 points on average), but the headline projection it is compared with is not corrected (bias −1.95). | The implied food-headline gap is biased +3.07 points, which produces systematic false HIGHs through the gap rule. |
| **D2 (I2–I5)** | Platt scaling and the threshold are refitted at every origin on 3–9 HIGH out-of-fold labels. | The same probability maps to HIGH at one origin and LOW at another. |
| **D3 (I4, I5)** | The gap residuals learned a 2022–2024 level that did not carry into 2025–2026. | Gap bias of about +0.9. |

**Corrected model (E46 I7, same data, origins and S44 rows):**
- accuracy 0.800, against I2's 0.686;
- Brier 0.174 and AUC 0.735, against 0.181 and 0.603;
- 14 of 35 decisions change: false positives 9 → 2, false negatives 2 → 5.

I7 still fails the balanced-discrimination gate (HIGH recall 0.44). See `E46_Rice_Policy/FINAL_REPORT.md`. The served E44 record now carries a warning naming D1 and D2.
