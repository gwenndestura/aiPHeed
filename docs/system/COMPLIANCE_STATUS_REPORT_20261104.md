# aiPHeed objective compliance and one-quarter-ahead forecasting status

**Audit date:** 2026-11-04, about 09:00 PHT (Asia/Manila)

**Repository state:** branch `pfi/survey-anchored-final` at `87b3f0eb` (E143).

**Deployed state:**
* `render.yaml` deploys branch `main` = `0239273d` (2026-10-22), which is 216 commits behind HEAD.
* The live API at `https://aipheed-api.onrender.com` was read with GET requests only.

**What was exercised:**
* the local API in the deployment configuration (`.claude/launch.json` "api": `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1`, port 8000);
* the local dashboard (`npm run dev`, port 8080) in the browser;
* the code paths, artifacts and tests cited below.

**Nothing was changed.** No model, production pointer, dashboard or historical evidence was altered. This report is the only new file.

---

## 1. Executive verdict

**Overall result: NOT COMPLIANT.**

aiPHeed does **not** currently deliver a validated food-insecurity risk forecast for each CALABARZON province one quarter ahead of the quarter viewed on the dashboard.

* **The deployed public system** (Render, `main`) serves **FIRI v2**, an "estimated food-insecurity risk index".
  * Its own definition says it is a proxy composite, "not a probability and not a measured food-insecurity rate", and that it cannot be validated as one.
  * It shows all five provinces HIGH (0.71–0.80) for 2027-Q1.
* **The current code** (HEAD, thesis mode) serves the **CH1 / P0H4 price-pressure risk index**.
  * It is labelled honestly as "not a food-insecurity forecast".
  * It opens on the **current** quarter (2026-Q4), not the target (2027-Q1).
  * Its value for the target quarter is a **Lead-2 output that failed its reliability test**.
  * It shows all five provinces LOW (0.03–0.10) for 2027-Q1.
* **The only food-insecurity forecasts** (HFIAS relative risk, E142/E143) exist as **admin-only candidates**. They target the right quarter (2027-Q1), but **every one failed its pre-registered gate**.
  * They are validated survey-to-survey only, on re-used development folds.
  * No quarterly provincial food-insecurity measurement exists to validate quarter-to-quarter forecasting.
* **Thesis objectives:** none is fully achieved. All five are partially achieved, and parts of Objective 5 are not achieved (section 8).

## 2. Central forecasting requirement

| Requirement | Deployed (`main`, FIRI v2) | Current code (HEAD, thesis mode, CH1/P0H4) | Admin candidate (E143 C2) | Evidence |
|---|---|---|---|---|
| Output is food-insecurity risk (not price, poverty or vulnerability) | **No.** Proxy composite of price, poverty, climate, national labour, news and regional hunger; "not a measured food-insecurity rate" | **No.** "Price-pressure risk index … not a food-insecurity forecast"; `is_food_insecurity_measurement: False` | **Yes** (HFIAS moderate-or-severe above national) | `GET /api/v1/config` (live); `app/ml/inference/ch1_system.py: INDICATOR`; `data/e143/out/issue/forecast_next_quarter.json` |
| Forecast of a future quarter | Yes (Lead 2, 2027-Q1) | Default view is the **current** quarter (2026-Q4, Lead 1). 2027-Q1 is Lead 2 | Yes (2027-Q1) | `/api/v1/quarters` → `current: 2026-Q4` (local) / `2027-Q1` (live); `data/ch1_engine/rows.csv` (lead 1 rows: issue quarter = target quarter, verified for all) |
| Target = viewing quarter + 1 | Yes (2027-Q1) | Only if the user moves the slider to Q1 2027 | Yes | Browser: the dashboard opens on "Q4 2026 … Forecast", with "Today" on Q4 2026 |
| Uses only information available at issue | Not re-verified on `main` | Yes. Cutoff 2026-10-01: SWS 2026-Q2 published 2026-08-24; CPI to 2026-08; news to 2026-09-30 | Yes (E141 panel as-of; E143 lock) | `rows.csv` columns `sws_newest_published`, `psa_newest_month`, `news_latest_published` |
| Distinct provincial result from provincial evidence | Distinct values; regional hunger and national labour are shared | Provinces differ **only through the price part**; the hunger part is identical (0.810). Cavite = Quezon = 0.1015 | Distinct values, but the LightGBM level is identical (−0.26). Differences come only from each province's HFIAS rounds | `rows.csv` `pi_hunger`, `pi_price`; E143 issue `structural_level_logit` |
| Probability or category plus uncertainty | Index, no interval | Probability and class, **no interval** | P, refit range, 90 % PI, class | `/api/v1/provinces` (`confidenceInterval: None`) |
| Dashboard shows province, issue quarter, target, issue date, result | Not verifiable (Vercel URL unknown) | Province, value and class are shown. The **issue date and the "Lead-2 failed" note are not shown** in the Q1 2027 panel | Not on the dashboard (admin only, by rule) | Browser page-text search for "Lead" and "experimental": no matches |
| Produced by the served model, not hardcoded | Not verifiable | Rows come from a **static export** sealed `a498b5ef…` (issued 2026-10-01); there is no runtime inference | Issued by `app/e143/issue.py`, sealed | `ch1_system.py` reads `data/ch1_engine/rows.csv` |

**Verdict on the central requirement: NOT MET.**

## 3. Current-quarter and target-quarter verification

**The clock is correct and dynamic.**
* `app/quarterly/target.py: forecast_target()` uses Asia/Manila time: target = `shift(calendar_quarter, 1)` and origin = quarter start.
* Checked on 144 timestamps (2025–2028, three per month): **0 mismatches**.
* UTC 16:30 on 31 Dec maps to Manila 1 Jan, giving target 2027-Q2.
* The API reports `forecastTarget.target_quarter = 2027-Q1` today.

**The dashboard does not open on that target in the deployment configuration.**
* Thesis mode: `/api/v1/quarters` → `current: "2026-Q4"`. The browser opens on "Q4 2026 October–December 2026 · Forecast".
* Default (non-thesis) mode opens on 2027-Q1, the E38 lead-2 preview (`app/quarterly/preview.py: default_quarter`). The two modes disagree.

**"Lead 1" is not "one quarter after the viewing quarter".**
* CH1 Lead 1 = the quarter in which the forecast is issued: the 2026-10-01 issue targets 2026-Q4.
* The dashboard target (viewing quarter + 1) is **Lead 2**.

**Stale forecasts after turnover.** Tested with `AIPHEED_NOW=2027-01-01T00:30`:
* The default view stays on **2026-Q4**.
* The target 2027-Q2 is served from the **2026-10-01** issue (Lead 3).
* The top-level indicator for 2027-Q2 changes to **"Food Insecurity Risk Probability"**, the E36 definition, while the rows are CH1 price-pressure. Cause: `app/services/dashboard.py: indicator_for` returns the default `INDICATOR` when `E41L2.serves(quarter)` is false.
* Nothing re-issues the CH1 export at quarter start. It is written by an experiments runner.

**Same target quarter across provinces:** yes, all five share each quarter's target.

**Backtests:** CH1 `evaluation.json` uses the same lead definition. Its Lead 1 backtests are issue-quarter forecasts, not viewing-quarter + 1.

## 4. Food-insecurity target and label verification

| Question | Answer (evidence) |
|---|---|
| 1. What does the served public model predict? | CH1: P(T43c HIGH) = P(SWS Balance Luzon hunger > 11.3 %) × P(provincial food inflation above its 2021–22 60th percentile) (`ch1_system.py` docstring; `evaluation.json: model`). Deployed FIRI v2: a 0–1 index |
| 2. What establishes the outcome? | **Public: no food-insecurity measurement.** The label combines one regional hunger value (SWS Balance Luzon, identical for all five provinces) with provincial food prices. Candidates: FNRI HFIAS moderate-or-severe (2013, 2015, 2018/2019) |
| 3. Are labels actual food-insecurity measurements? | Public: no; the hunger part is regional SWS. Candidates: yes (HFIAS) |
| 4. Are HFIAS observations used correctly? | Yes in E137–E143: relative logit vs the same-round national value, with survey SE, soft labels, no interpolation (`app/e141/panel.py`; `docs/e143/PROTOCOL.md`) |
| 5. Are FIES and HFIAS kept separate? | Yes. FIES is never used as an HFIAS label. The 2023 NNS is FIES and is agreement-only (`docs/system/DATA_REQUEST_FNRI_PROVINCIAL_HFIAS.md`) |
| 6. Is a regional estimate shown as provincial? | The public CH1 hunger condition is regional SWS applied to every province. It is disclosed ("provinces differ only through food prices"). FIRI v2 on `main` also uses regional hunger |
| 7. Measured outcome, relative state or latent estimate? | Public: a price/regional-hunger composite class. Candidates: a latent relative-risk state (structural level + survey anchor) |
| 8. Future prediction or carried-forward history? | Candidates: mainly **carried-forward survey history** (63–73 % weight on own rounds) plus a structural level. No quarterly dynamics are identified (E143 audit: AR(1) contradicted) |
| 9. What does the probability mean? | CH1: the chance the price-plus-hunger condition is HIGH. E143: the chance that provincial HFIAS moderate-or-severe is above national. Neither is a prevalence |
| 10. Is it legitimately a "provincial food-insecurity risk forecast"? | **Public: no.** Candidate: a *candidate* estimate of next-quarter relative risk, **not validated** |

## 5. Five-province results (as served or issued on 2026-11-04; current quarter 2026-Q4; target 2027-Q1)

**A. Current code (HEAD, thesis mode)**
* **Model:** CH1 P0H4 price-pressure risk index, Lead 2, seal `a498b5ef…`.
* **Issue date:** 2026-10-01. **Cutoff:** 2026-10-01 00:00 PHT (exclusive).
* **Latest outcome used:** SWS 2026-Q2 (published 2026-08-24).

| Province | P(HIGH) | Class | Interval | One quarter ahead of viewing quarter? | Independently validated? | Status |
|---|---|---|---|---|---|---|
| Cavite | 0.1015 | LOW | NOT AVAILABLE | Target yes; **Lead 2 failed reliability** | No | NOT A FOOD-INSECURITY FORECAST |
| Laguna | 0.0530 | LOW | NOT AVAILABLE | same | No | same |
| Batangas | 0.0415 | LOW | NOT AVAILABLE | same | No | same |
| Rizal | 0.0257 | LOW | NOT AVAILABLE | same | No | same |
| Quezon | 0.1015 | LOW | NOT AVAILABLE | same | No | same |

**B. Deployed public API (`main`, FIRI v2)**
* **Horizon:** "Lead 2 (2027-Q1), issued 2026-10-01".
* **Evidence status:** EXPERIMENTAL.

| Province | Index | Class |
|---|---|---|
| Laguna | 0.803 | HIGH |
| Cavite | 0.757 | HIGH |
| Rizal | 0.725 | HIGH |
| Quezon | 0.723 | HIGH |
| Batangas | 0.712 | HIGH |

* Interval NOT AVAILABLE. **Validation: none possible** (its own caveat).

**C. Food-insecurity candidate (admin only)**
* **Model:** `e143-re-lgbm-1.0` (C2).
* **Issue date:** 2026-10-01. **Gate:** failed (S1, S2).

| Province | P(HFIAS above national) | Refit range | Class | Last measured round |
|---|---|---|---|---|
| Batangas | 0.064 | 0.015–0.371 | LOW | FNRI 2015 |
| Cavite | 0.124 | 0.041–0.529 | UNCERTAIN | FNRI 2015 |
| Laguna | 0.075 | 0.026–0.224 | LOW | ENNS 2018 |
| Quezon | 0.165 | 0.082–0.579 | UNCERTAIN | ENNS 2019 |
| Rizal | 0.191 | 0.087–0.427 | LOW | ENNS 2019 |

**The three outputs disagree completely:** all HIGH (deployed), all LOW (current code), mixed LOW/UNCERTAIN (candidate).

**Are the provincial differences genuine?**
* **CH1:** only through provincial food prices. The hunger factor is one regional number, and Cavite and Quezon tie.
* **E143:** only through each province's own HFIAS history. The structural level is identical for all five, and the final fit cannot separate a province-specific lasting difference from the region's (σ_G² = σ_A²).

## 6. One-quarter-ahead evaluation

| Model and target | Horizon actually tested | Result | Evidence |
|---|---|---|---|
| CH1 P0H4, price/hunger composite | Lead 1 = **issue quarter** (14 quarters, n = 70, 2023–2026) | acc 0.843 [90 % 0.757–0.929], recall 0.65, precision 0.69, F1 0.67, AUC 0.867, Brier 0.132; always-LOW 0.757, persistence 0.743. Development, not untouched | `data/ch1_engine/evaluation.json → leads["1"]` |
| CH1 P0H4 | **Lead 2 = dashboard target** (n = 65) | acc 0.769, **HIGH recall 0.35**, precision 0.60, F1 0.44, AUC 0.625, Brier 0.194; always-LOW 0.738. **Fails R3, R5, R6** | `evaluation.json → leads["2"]`, `max_reliable_lead: 1` |
| E36 LightGBM, S1 composite (default mode) | Lead 1 = issue quarter (n = 65) | acc 0.815 [0.738, 0.892] = always-HIGH 0.815 < persistence 0.877; no baseline beaten significantly | `/api/v1/config → modelPerformance` (default mode) |
| E38 LightGBM-NQ (default-mode 2027-Q1 map) | Lead 2 | development acc 39/55 = 0.709 | `data/e36/e36_record.json → next_quarter_model` |
| E142 / E143, HFIAS relative risk | **Survey-to-survey** (8–16 quarters), 125 rows, 16 region clusters; untouched 2013 round | C4: EB 0.190, AUC 0.984, accuracy 0.903, recall 0.90, precision 0.95, F1 0.92, ECE 0.098; vs persistence −0.017 [−0.044, +0.012], vs region's previous level +0.000 [−0.032, +0.030]. **Gate failed** | `data/e143/out/results.json`; report v3 section 8 |

* **Quarterly validation of food insecurity:** impossible with current data. There is no quarterly provincial food-insecurity measurement.
* Multi-year survey transitions are **not** counted here as quarterly validation.
* The E142 AR(1) quarterly form was shown to be unsupported (E143 audit, Markov test).

## 7. Five contributor groups (served CH1 model; mean |SHAP| share of the price part for 2027-Q1)

| Group | Indicators in the served model | Coverage | Available at issue | Contributes? | Measurable predictive value | Dashboard |
|---|---|---|---|---|---|---|
| Market & prices | A1 food CPI, A2, A3 rice | provincial, 2021+ | yes (CPI to 2026-08) | **53 % + 4 %** | Lead-1 skill exists for the *price* label; none shown for food insecurity (E141/E143 ablation: none) | Bar 64 % |
| Climate & agriculture | C1–C3, C4 fisheries | provincial / regional | yes | about 1 % | none demonstrated | Bars 0–1 % |
| Employment & OFW remittances | E1 national unemployment, E2 national remittances | **national only** (data audit 2026-10-30: class C) | yes | **E1 31 %**, E2 0 % | **not validated.** E1 is a national series and cannot be a provincial driver | **"Employment 34 %"** bar. This implies a provincial employment effect that has no provincial data behind it |
| News & NLP | N1 (FSSI) | CALABARZON; 95 % one outlet | yes | 1.5 % | not demonstrated (report v3 section 12) | not a bar ("other") |
| Poverty & vulnerability | V1 static profile | provincial | yes | 9 % | largest structural contributor for HFIAS (E141 ablation +0.020) | not a bar ("other") |

* The dashboard's "Relative model influence" presents feature attributions of the price model, not validated contributions to food insecurity.
* The Employment bar is the clearest overstatement.

## 8. Thesis objective compliance matrix

Objectives are quoted from the manuscript extract (`aipheed-backend-aligned/experiments/FINAL_THESIS_OBJECTIVES/sources/chapter1_THESIS2_11_extract.txt`, §1.5.2).

| Thesis objective | Required evidence | Actual implementation | Test or validation evidence | Status |
|---|---|---|---|---|
| 1. Two-tier pipeline: zero-shot XLM-RoBERTa sentiment + BERTopic → bias-corrected FSSI and latent risk patterns per province-quarter | Working pipeline; bias correction shown; province-quarter patterns; sentiment accuracy | XLM-R scoring, BERTopic topics, FSSI v2/v3 per province-quarter (`app/e142/fssi.py`; `data/fi6/news_archive`) | Volume dependence 0.44 → 0.05; cyclone convergence p < 0.001 (`data/e142/out/fssi_v2_validity.json`). Sentiment accuracy **unverified**; 95 % one outlet | **PARTIALLY ACHIEVED** |
| 2. Evaluate LightGBM: accuracy, precision/recall, F1, AUC-ROC, walk-forward expanding window across lead times, furthest reliable horizon | Metrics on genuine forecasts; walk-forward; a reliable horizon for the food-insecurity risk class | All metrics computed (CH1, E36, E141–E143); walk-forward done | CH1 reliable only at Lead 1 = issue quarter, on a price/regional-hunger label. **Food-insecurity target: no reliable horizon** | **PARTIALLY ACHIEVED** |
| 3. Municipal and city risk rankings from **validated** province forecasts, with PSA poverty and density weights | 142 LGU rankings derived from validated province forecasts | 142 LGUs (public from CH1; candidate from E143) with SAE 2021 poverty + POPCEN 2024 density | Province forecasts **not validated** (public = price index) | **PARTIALLY ACHIEVED** |
| 4. Compare LightGBM vs naive persistence, PSA-only, NLP-only, logistic regression | All four baselines on identical rows for the proposed model | E36: all six Chapter I baselines (none beaten significantly; persistence better). E141–E143: persistence, PSA-only, logistic, ridge (NLP-only not constructible). **Served CH1 compared only with persistence, climatology and always-LOW** | `/api/v1/config → modelPerformance.baselines`; `data/e143/out/results.json` | **PARTIALLY ACHIEVED** |
| 5. Deploy a public geospatial dashboard with forecast maps and early-warning alerts; ISO/IEC 25010 evaluation with DA IV-A evaluators; validate forecasts against FNRI NNS 2019 and 2023 CALABARZON figures (face validity) | Live dashboard; alerts; completed ISO evaluation; face-validity comparison | Dashboard deployed (Render + Vercel config; live API answers). Alerts implemented (`app/api/v1/alerts.py`; threshold 0.6) | **No ISO/IEC 25010 evaluation results in the repository. No NNS 2019/2023 face-validity comparison performed** (`docs/final_system/THESIS_OBJECTIVE_ASSESSMENT.md` lists both as outstanding). The deployed build lags HEAD by 216 commits | **PARTIALLY ACHIEVED** (deployment); ISO evaluation **NOT VERIFIABLE**; face validity **NOT ACHIEVED** |

**Were all objectives achieved?** No.

| Status | Objectives |
|---|---|
| Fully achieved | none |
| Partially achieved | 1, 2, 3, 4, 5 |
| Not achieved | the NNS face-validity part of 5 |
| Cannot be verified from the repository | the ISO/IEC 25010 evaluation |

## 9. Dashboard → API → model audit (discrepancies)

| # | Finding | Evidence |
|---|---|---|
| D1 | **Deployed ≠ current code.** Live `main` serves FIRI v2 "food-insecurity risk index", all five HIGH. HEAD serves the CH1 price-pressure index, all five LOW. The live API lacks the release-gate routes (`/final/model-registry`, `/final/food-insecurity/outlook` → 404) | live GETs; `git log main` = `0239273d`, 216 commits behind |
| D2 | Default view = current quarter (2026-Q4) in thesis mode; target (2027-Q1) in default mode | `/api/v1/quarters`; browser |
| D3 | "Lead 1" = issue quarter; the dashboard target is Lead 2, which failed its reliability test | `rows.csv`; `evaluation.json` |
| D4 | The Q1 2027 province panel shows no issue date, interval or "Lead-2 failed" note, although the API sends `horizonLabel` with it | browser page text; `/api/v1/provinces?quarter=2027-Q1` |
| D5 | After quarter turnover, forecasts go stale (2026-10-01 issue reused; the default stays on 2026-Q4) and the indicator falls back to "Food Insecurity Risk Probability" | `AIPHEED_NOW=2027-01-01T00:30`; `dashboard.indicator_for` |
| D6 | The model depends on configuration. Started without `AIPHEED_LEAD2_MODEL=thesis` (this worktree has no `backend/.env`), the API serves the E36/E38 record titled "Food Insecurity Risk Probability" (Cavite/Laguna/Rizal/Quezon all 0.9521). Strict mode in `render.yaml` prevents this in deployment | default-mode `/api/v1/provinces` |
| D7 | The `thesis_system.py` docstring says the map is the E56-TUNED record. The served map is CH1 P0H4 | `app/ml/inference/thesis_system.py` vs `ch1_system.active()` |
| D8 | The "Employment" influence bar (34–48 %) comes from a national series | `rows.csv shap_E1`; data audit 2026-10-30 |
| D9 | No candidate is exposed publicly. The production pointer is null. Admin routes require auth (401/403). **No mismatch between candidate and public outputs, because the public dashboard does not show the candidate** | `tests/unit/test_e143.py::test_admin_route_only`; `/api/v1/final/food-insecurity/outlook` |
| D10 | No training at page load. The public map reads a sealed export; candidates are pre-issued files | `ch1_system.py`; `app/e143/serve.py` |

## 10. Failed tests, missing evidence, unresolved issues

**Tests run** (2026-11-04, HEAD `87b3f0eb`):

| Suite | Result |
|---|---|
| Backend unit tests (`pytest tests/unit`) | **879 passed** |
| Frontend `tsc --noEmit` | clean |
| Frontend `vitest` | 88 passed |
| Audit-relevant subset, re-run (public API gate, v2 defects, system completion, v2 core, registry, E142, E143) | 79 passed |
| Backend integration, e2e and top-level tests | **732 passed, 18 skipped** |

* **No test covers D2, D4 or D5** (default view vs target, panel disclosure, turnover staleness and indicator fallback).
* That is why they pass unnoticed.

**Missing evidence:**
* a post-2019 provincial HFIAS round (FNRI 2021 ENNS);
* any quarterly provincial food-insecurity measure;
* ISO/IEC 25010 results;
* the NNS face-validity comparison;
* provincial employment and remittance series for the training years;
* a validated sentiment sample.


## 11. Final answers

1. **Is aiPHeed currently a food-insecurity risk forecasting system?** **No.** The public outputs are a price-pressure index (HEAD) or an unvalidated proxy index (deployed). The food-insecurity forecast is an admin-only candidate that failed its gate.
2. **Separate forecasts for the five provinces?** Yes, separate values exist in every output. In CH1 they differ only through food prices (Cavite = Quezon). In the candidate they differ only through each province's HFIAS history.
3. **Exactly one quarter ahead of the viewed quarter?**
   * The clock is correct (target = viewing quarter + 1, dynamic).
   * The deployed thesis-mode dashboard opens on the **current** quarter.
   * The target-quarter output is a Lead-2 value that **failed** reliability, and it goes stale after turnover.
4. **Food insecurity rather than price pressure or vulnerability?** **No** for the public outputs. Yes for the candidate (not served).
5. **One-quarter-ahead performance independently validated?** **No.** CH1 Lead 2 failed. The HFIAS candidates failed survey-to-survey, and quarterly validation is impossible with existing data.
6. **All five contributor groups genuinely represented and accurately explained?** **No.**
   * Employment and remittances are national.
   * Employment's 34 % bar overstates a provincial effect.
   * News (1.5 %) and poverty (9 %) are not shown as bars.
   * No group has validated incremental value for food insecurity.
7. **All thesis objectives achieved?** **No.** All five are partially achieved; none is fully achieved.
8. **Is the served model scientifically defensible and ready for thesis demonstration?**
   * As a **price-pressure index for the current quarter** (CH1 Lead 1), it is defensible and honestly labelled in HEAD.
   * As a **one-quarter-ahead food-insecurity forecast**, it is **not**.
   * The deployed build is not the defensible one: an unvalidated proxy named "food-insecurity risk index", all HIGH.
9. **Single most important remaining issue:** **No provincial food-insecurity outcome exists after 2019 against which a forecast could be trained or validated.** Until the FNRI 2021 ENNS provincial HFIAS round (or any later provincial food-insecurity measurement) is obtained, no model can be shown to forecast provincial food insecurity one quarter ahead.

## 12. Prioritized corrective actions (none applied in this audit)

1. **Deployment (owner decision):** the live site runs `main` (FIRI v2). Either deploy the reviewed HEAD build (honest price-pressure label, release gate) or add the HEAD caveats to `main`. **The current live state overstates.**
2. **Target-quarter display (D2/D4):** open the dashboard on `forecastTarget.target_quarter`, and show its issue date and the API's existing "Lead-2: tested and failed" `horizonLabel` in the province panel.
   * This uses existing UI text slots. No new design elements are needed (approved-design rule).
3. **Turnover (D5):**
   * re-issue the forecast at each quarter start, or withdraw rows whose issue quarter is not the current quarter;
   * fix `dashboard.indicator_for` so CH1 rows are never titled "Food Insecurity Risk Probability".
   * Add tests for D2, D4 and D5.
4. **Contributor display (D8):** label Employment and OFW as national series (or drop them from province bars). State that the bars are attributions of the price model.
5. **Objective 5:** run and record the ISO/IEC 25010 evaluation with DA IV-A evaluators. Perform the NNS 2019/2023 face-validity comparison, using HFIAS 2019 rows for Quezon and Rizal and the regional 2023 FIES figure as agreement only.
6. **Evidence:** obtain the FNRI 2021 ENNS provincial HFIAS round (request drafted, not sent, owner rule) and score the sealed E138–E143 predictions with `python -m app.registry.prospective_provincial score <file>`.
