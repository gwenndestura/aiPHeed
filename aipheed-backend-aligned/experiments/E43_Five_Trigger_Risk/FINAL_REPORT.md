# E43: five-trigger food-insecurity-risk forecasting at Lead 2

**Date:** 2026-10-15.
**Branch:** `e43-five-trigger-risk` (local, not pushed), cut from the E42 state (`bd4038f`). E41 and E42 are preserved as audit evidence.

**Order of work (each step committed before the next):**

| Step | Commit |
|---|---|
| Protocol and label diagnostics frozen before any model | `dbb8bf6` |
| Code and tests | `bafc013` |
| Run, record, backend/frontend and this report | final commit |

**Decision:**
- **Ready for a controlled system demonstration** as an experimental, five-trigger, evidence-first food-stress view.
- **Lead-2 operational forecasting remains experimental.** No model met the evaluation gates, and the 75% target is not met in any meaningful way: an always-LOW rule already gets 0.80, so accuracy alone says nothing here.

---

## 1. The five approved triggers (exact definitions recovered)

Chapter I does not list the triggers. It refers to "trigger composition scores" and to data from "PSA, DOST-FNRI, SWS, PAGASA, PhilRice, BSP, and DOE" (§1.7). The definitions live in the repository:

| Trigger | Key | Definition (`backend/app/ml/nlp/trigger_classifier.py`, HungerGist 8+2 taxonomy) | Government features in the existing design (`e20_forecast.DRIVER_GROUP_FEATURES`; P45 candidates) |
|---|---|---|---|
| Market / Prices | `market` | food prices, rice, supply disruption (T1) | provincial food CPI, rice price |
| Climate Stress | `climate` | typhoons, rainfall, ENSO, drought (T2/T6/T7) | P45: tc_count, rainfall anomaly, drought alert, ENSO |
| Fish Kill | `fish_kill` | aquaculture collapse, Laguna/Taal fish deaths (T1b) | none in the original design |
| Employment | `employment` | joblessness, retrenchment, livelihood loss (T4/T8) | unemployment rate |
| OFW Remittance | `ofw_remittance` | OFW income, remittances, foreign employment (T9) | P45: OFW remittance YoY |

**Taxonomy defect, reported but not changed:** the employment keyword list contains "gutom" (hunger), "kahirapan" (poverty) and "economic hardship".

## 2. Official-data inventory and coverage (2021-01..2026-09; no pre-2021 value loaded)

| Trigger | Source (level) | Coverage | Timing at origin O(t) | Quality |
|---|---|---|---|---|
| Market | PSA CPI food and headline, published YoY and index (province); PSA wholesale rice price (province) | 2021-01..2026-09; rice 2021-Q1..2026-Q3 | CPI months ≤ month 2 of t; rice ≤ t−1 | Index vs published YoY within 0.05 points (570 province-months) |
| Hunger (target component) | SWS approved rounds, Balance Luzon (**region**) | 19 labelled quarters; 2021-Q1, 2022-Q1, 2025-Q2 and 2025-Q3 have no approved round | posted before O(t) | Never provincial |
| Climate | NOAA IBTrACS typhoon tracks within 300 km (province); NOAA CPC ONI ENSO; PSA palay/corn production (province) | 2021-Q1..2026-Q3 (production to 2026-Q2) | typhoons ≤ t; ENSO and production ≤ t−1 | **NOAA, not PAGASA.** The file is misnamed `pagasa_climate.parquet`. PAGASA's own rainfall file starts in 1991 and is refused before loading. |
| Fish Kill | PSA fisheries and aquaculture production (province) | 2021-Q1..2026-Q2 | ≤ t−1 | No BFAR fish-kill event series exists in-window |
| Employment | PSA LFS unemployment and underemployment (**national**) | 2021-01..2026-08 | ≤ t−1 | No provincial or regional quarterly series in OpenStat |
| OFW Remittance | BSP cash remittances (**national**, curated in `bsp_macro.parquet`); ECB USD/PHP | remittances 2021-Q1..2025-Q4; FX to 2026-Q3 | ≤ t−1 | bsp.gov.ph refuses programmatic re-download, so the values are unverified. No regional remittance series exists (OpenStat checked). |
| News (all five) | E31 Google News titles (province-attributed), trigger shares, FSSI-v2 | 2021-Q1..2026-Q4 | ≤ t | Titles only, collected retroactively. FSSI-v2 is missing in 79% of province-quarters. |

**Correction to E41/E42:** both said climate and OFW data were unobtainable in-window. In-window NOAA climate and curated BSP national remittance files already existed in the repository.

## 3. Target labels: original and corrected (`runs/labels/label_diagnostics.json`)

| Label | Meaning | HIGH share | Problem |
|---|---|---|---|
| v1 (served): S1 = H + 2D > trailing median | relative composite | 67% (2024–26: 90–95%) | It is HIGH whenever regional hunger is above a slowly rising median: 83% HIGH when H is above its 2021–22 median, 24% otherwise. 50% of HIGH rows have food inflation below 4%, and 40% of HIGH quarters had hunger *falling*. It cannot recognize calm periods. |
| E40 (sustain-2) | both signals in two consecutive quarters | 5% (5/95; 3 quarters; 0 in 2026) | Too rare to learn: no HIGH before 2024, and the provinces are identical in 16 of 19 quarters. |
| Hunger only | H > 11.3 | 63% | Identical for all provinces. |
| **T43 (chosen; = E40 signals, single quarter)** | regional hunger above 11.3 **and** provincial food price above its 2021–22 P60 (or food minus headline above its P60) | **19%** (2021 13%, 2022 0%, 2023 15%, 2024 40%, 2025 40%, 2026 7%) | Provinces differ in 7 of 19 quarters. The only change from E40 is dropping sustain-2, which needs adviser approval. |
| L4 (sensitivity) | H > 11.3 and food YoY > 4% | 23% | – |

**Why T43:**
- It uses exactly the two sources §1.7 names.
- It uses frozen references rather than a drifting median.
- It keeps the researcher's E40 thresholds.
- It separates "hunger high and prices high" (HIGH) from "only one signal" (WATCH), which is shown to DA as an observed category.

It was chosen **before** any model was fitted. It is an **exploratory food-stress outcome**, not verified household food insecurity.

**Circularity:** lagged components of the target are predictors, as in any forecast of an observable indicator. This is why every model is judged against persistence and the base rate.

## 4. Feature-to-trigger map and missing data

The full map is in `PROTOCOL.md` §3.

| Group | Features |
|---|---|
| Market | F_last, F_now, gap_now, mom3, F_hat_M1, D_now, rice_whsl_yoy |
| Climate | tc_count, tc_max_signal, tc_severe, enso, palay_yoy, corn_yoy |
| Fish | fish_yoy, aqua_yoy |
| Employment | ur_last, ur_yoy, under_last |
| OFW | remit_usd_yoy, fx_yoy |
| Hunger history | H_last, H_chg, H_age |
| News | one share per trigger, news_n, fssi_v2, fssi_admitted |

- **Missing share:** fssi_v2 79%; remit_usd_yoy 24%; rice_whsl_yoy 20%; YoY production and labour features 14% (no 2020 base); H_chg 5%.
- **Missing values stay NaN** for LightGBM. Logistic models get median imputation plus missing indicators.
- **Missing data is not neutral.** Masking a group at prediction time shifts LightGBM-COMB probabilities by −0.54 (employment) and −0.14 (climate).

## 5–6. Lead-2 results, baselines, ablation (T43; development evidence)

**Common set S-C:** 2025-Q1..2026-Q3, 5 quarters, 25 province-quarters, 5 HIGH. This is all the data allow once a model needs 5 HIGH training rows and labels are counted only after their SWS round was posted.

| Model | Accuracy (95% CI) | Balanced | HIGH recall | LOW recall | Brier | ROC-AUC |
|---|---|---|---|---|---|---|
| **LGBM-COMB (primary: five-trigger LightGBM)** | 0.56 (0.32–0.80) | 0.725 | 1.00 | 0.45 | 0.275 | 0.845 |
| LGBM-GOV | 0.60 | 0.75 | 1.00 | 0.50 | 0.278 | 0.87 |
| LGBM-NLP | 0.56 | 0.575 | 0.60 | 0.55 | 0.231 | 0.655 |
| LR-COMB / LR-GOV / LR-NLP | 0.40 / 0.28 / 0.28 | 0.475 / 0.25 / 0.40 | – | – | 0.602 / 0.675 / 0.321 | 0.33 / 0.23 / 0.55 |
| SIM-0 (structural: SWS random walk × price path) | 0.80 (0.68–0.92) | 0.65 | 0.40 | 0.90 | 0.158 | 0.77 |
| SIM-5T (hunger path shifted by triggers) | 0.76 | 0.70 | 0.60 | 0.80 | 0.158 | 0.78 |
| B-maj (always LOW) | 0.80 | 0.50 | 0.00 | 1.00 | 0.177 | – |
| B-persist | 0.56 | 0.725 | 1.00 | 0.45 | 0.440 | – |
| B-clim | 0.80 | 0.50 | 0.00 | 1.00 | 0.179 | – |
| E38-served (v1 model, scored on T43) | 0.12 | 0.225 | – | – | 0.710 | – |
| E41-M1 (price-only, comparison) | 0.84 | 0.60 | 0.20 | 1.00 | 0.132 | 0.81 |

**Confusion matrices:**

| Model | TP | TN | FP | FN |
|---|---|---|---|---|
| LGBM-COMB | 5 | 9 | 11 | 0 |
| SIM-5T | 3 | 16 | 4 | 2 |
| SIM-0 | 2 | 18 | 2 | 3 |

**Primary vs baselines** (per-date Brier): −0.098 vs B-maj and +0.165 vs B-persist (Holm p = 1.0). It does not beat the base rate.

**Longer structural set S-SIM** (2023-Q2..2026-Q3, 12 quarters, 60 rows, 16 HIGH):

| Model | Accuracy | AUC | Brier |
|---|---|---|---|
| SIM-0 | 0.75 | 0.51 | 0.216 |
| SIM-5T | 0.68 | 0.57 | 0.223 |
| B-clim | 0.733 | – | 0.215 |
| B-maj | 0.733 | – | 0.231 |

**Over 12 quarters the structural models do not discriminate** (AUC about 0.5).

**L4 sensitivity** (S-C, 7 quarters, 35 rows, 10 HIGH): SIM-0 0.771 (Brier 0.163) vs B-maj 0.714 (0.210); LGBM-COMB 0.714 (0.212). Same picture.

**Government vs NLP:** adding news to government features changes Brier by +0.073 (LR, p = 0.31) and +0.003 (LightGBM, p = 0.81). **No measurable NLP value**, consistent with E38–E42 (titles only; FSSI missing in 79% of province-quarters).

**Trigger contributions** (S-C; secondary, nothing selected from them):

| Group | Permutation ΔBrier (LGBM / LR) | Mean \|SHAP\| (LGBM) | Single-group LGBM (bal / Brier / AUC) | Single-group LR (bal / Brier / AUC) | Reading |
|---|---|---|---|---|---|
| Climate | **+0.050 / +0.119** | 0.51 | 0.80 / 0.154 / 0.81 | **0.85 / 0.127 / 0.94** | The only trigger with a consistent signal. The El Niño of 2023–24 preceded the 2024 rice and hunger stress. But 25 rows cannot establish it: a candidate for prospective pre-registration, **not adopted**. |
| Market | +0.011 / −0.022 | 0.39 | 0.425 / 0.225 / 0.37 | 0.625 / 0.227 / 0.65 | weak at lead 2 |
| Employment (national) | 0.000 / −0.027 | **1.77** | 0.625 / 0.482 / 0.90 | 0.50 / 0.713 / 0.15 | **Spurious time proxy:** highest SHAP, yet masking it moves p by −0.54, and the series is province-invariant |
| OFW (national) | +0.003 / −0.003 | 0.23 | 0.50 / 0.468 | 0.50 / 0.493 | no signal; data stop at 2025-Q4 |
| Fish Kill | +0.002 / −0.001 | 0.04 | 0.35 / 0.304 | 0.50 / 0.279 | no signal (production proxy) |

**A trigger without signal is not given artificial weight.** Where this comes from:
- **Data** (OFW and employment): national only, curated or ending early.
- **Feature design** (fish kill): production is not a kill-event series.
- **Sample:** 5 common quarters.

## 7. Leakage and timing (gate G0: pass)

`tests/test_e43.py` has 12 tests. They check:
- the study window, with parquet metadata checked before loading (the 1991-start rainfall file is refused);
- T43 equals E40's signals, and E40's label equals T43 held for two consecutive quarters;
- label availability by SWS posting date (2026-Q3 is not usable at 2026-10-01; 2026-Q2 is);
- perturbing every value published at or after O(t) leaves the five-trigger features, both simulations, the ridge hunger shift and the LR/LightGBM forecasts unchanged;
- the freeze.

**Lead 2:** O = 2026-10-01 → 2027-Q1, using CPI to 2026-08 and SWS to 2026-Q2.

**Exposure:** the E40 holdout (2025-Q4..2026-Q3) is exposed (E41 C-1), and every quarter has been seen by earlier experiments. All figures here are development evidence. The first blind outcome is 2027-Q1.

## 8–9. Gates, risk scores and calibration

**Gates for the primary (LGBM-COMB):**

| Gate | Result | Detail |
|---|---|---|
| G0 | **pass** | – |
| G1 (accuracy ≥ 0.75) | **fail** | 0.56 |
| G2 (balanced ≥ 0.70 and both recalls ≥ 0.60) | **fail** | LOW recall 0.45 |
| G3 (beats the base rate and persistence on Brier) | **fail** | – |
| G4 (calibration) | **fail** | calibration-in-the-large −0.40 (CI −0.55..−0.20); it over-predicts because of class weighting, although it ranks well (AUC 0.85) |

**Classification:** *insufficient evidence for Lead-2 operational use.*

**Served candidate** (pre-registered rule: the primary did not beat the base rate, so the better structural model on S-SIM is served): **SIM-0**. It is behind `AIPHEED_LEAD2_MODEL=e43`; the default stays E38.

**2027-Q1, P(T43 HIGH):**

| Province | SIM-0 (served) | Five-trigger LightGBM |
|---|---|---|
| Quezon | 0.30 | 0.20 |
| Cavite | 0.15 | 0.12 |
| Rizal | 0.07 | 0.06 |
| Batangas | 0.01 | 0.21 |
| Laguna | 0.004 | 0.54 |

- Regional mean (SIM-0): 0.11.
- The models agree on the low level overall but disagree on Laguna. Both values are shown.

**Interpretation:**
- Each value is a model probability of the defined exploratory event, from a structural model with calibration-in-the-large about 0 over 12 quarters but no discrimination.
- It is **not a calibrated probability of household food insecurity.**
- The old 0.95 scores were P(v1 relative label), not food insecurity, and are not repeated.

**Separate outputs per province** (`/api/v1/lead2/provinces/<id>`):
- forecast probability, its hunger and price components, and the band;
- observed SWS hunger (regional, with age);
- food price vs the province reference and vs 4%;
- climate: typhoons, ENSO, palay/corn;
- fisheries;
- employment (national);
- OFW (national, stale flag);
- news;
- latest observed Low/Watch/High;
- five-trigger LightGBM contributions, labelled as attributions, not causes;
- the development backtest against outcomes;
- warnings.

**No municipal probabilities** are produced.

## 10. Files changed and tests

**Experiment** (`aipheed-backend-aligned/experiments/E43_Five_Trigger_Risk/`):
- `PROTOCOL.md`, `DEVIATIONS.md` (D-1: optional component output added after the run; default output identical, tested);
- `runner/{e43_label_diagnostics,e43_lib,e43_evaluate}.py`;
- `tests/`;
- `runs/labels`, `runs/20261015T134756Z` (primary), the repeat run, `frozen/E43_PROSPECTIVE_2027Q1.json` + `.sha256`.

**Backend** (default E38 unchanged):

| File | Change |
|---|---|
| `app/ml/inference/e41_lead2.py` | e43 mode; score-type-agnostic `probability()`; record-stated `trigger_statuses()` and drivers |
| `app/services/dashboard.py` | `data_not_in_model` and `stale` statuses; record-stated statuses per province and region; `indicator_for` uses the record's own indicator |
| `app/api/v1/lead2.py` | generic summary (probability, scoreType) |
| `scripts/build_record_e43.py` | builds `data/e43/e43_record.json`; checks that the components reproduce the frozen probabilities |
| `tests/integration/test_e43_five_trigger.py` | 6 tests |

E42's fixes are retained: trigger status, `statusNote`, the indicator/score-type match, and `scoreType` per timeseries point.

**Frontend** (approved files, changed for the trigger-card defect as requested):
- `src/lib/apiTypes.ts` and `src/lib/driverCopy.ts`: neutral copy for `data_not_in_model` and `stale`;
- `src/test/driverCopy.test.ts`: 5 tests.

**Test results:**
- E43: 12 passed.
- Backend: **326 passed, 18 skipped** (the 18 are the long-standing superseded tests).
- Frontend: vitest **35/35**; `vite build` OK; `tsc` shows the same 6 errors as the approved baseline, none in the changed files.
- **Live check** (approved UI against the E43 API): Q1 2027, regional 0.11, provinces 0.30 / 0.15 / 0.07 / 0.01 / 0.00. Market contributes; the climate, fisheries, jobs and OFW cards read "data shown, not in the model".

**Reproduce:**
```
backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider aipheed-backend-aligned/experiments/E43_Five_Trigger_Risk/tests
cd aipheed-backend-aligned/experiments/E43_Five_Trigger_Risk && ../../../backend/venv/Scripts/python.exe -B runner/e43_evaluate.py
cd backend && venv/Scripts/python.exe -B scripts/build_record_e43.py && venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
```

## 11. Limitations and the evidence needed

| Limitation | Evidence that would resolve it |
|---|---|
| Few independent outcomes: 5 common quarters (5 HIGH), 12 for the structural models; HIGH quarters cluster in 2024–25 | Prospective scoring of 2027-Q1 onward; at least 8–12 more labelled quarters |
| SWS is regional, so provincial differences come only from prices | A provincial hunger or FIES series (DOST-FNRI provincial estimates, CBMS) |
| OFW and employment are national; OFW stops at 2025-Q4 and cannot be re-verified | BSP regional remittance or PSA SOF regional series; regional LFS quarterly estimates |
| No PAGASA series in-window (NOAA used); no BFAR fish-kill events | PAGASA in-window provincial rainfall and typhoon impact data; BFAR advisories |
| News is titles only, collected retroactively; FSSI-v2 is missing in 79% of province-quarters | Article text and a live-collected corpus |
| The primary over-predicts (class weighting) | A pre-registered, uncalibrated or recalibrated LightGBM, tested prospectively, not adopted after the fact |
| The target drops E40's sustain-2 rule | **Adviser approval of T43 (or another target)** |

## 12. Decision

- **Demonstration:** ready, as an experimental five-trigger evidence and forecast view behind `AIPHEED_LEAD2_MODEL=e43`, with every score labelled for what it is.
- **Lead-2 operational use:** remains experimental. No model, including the five-trigger LightGBM, beats the base rate on the Chapter-I-aligned target with the data available, and 75% accuracy is reached only by always predicting LOW.
- **Next scientific step:** pre-register the climate-informed model and an uncalibrated five-trigger LightGBM for prospective comparison from the 2027-01-01 origin, and score 2027-Q1 once its SWS round and CPI are released.
- **DA validation:** has not happened and is not claimed.
