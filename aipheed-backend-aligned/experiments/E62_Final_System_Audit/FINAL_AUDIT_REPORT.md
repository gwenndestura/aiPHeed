# E62 final system audit of aiPHeed (2026-10-19)

**Scope:** the full data-to-dashboard path of the served Lead-2 model (E58 = E56-TUNED LightGBM plus the two-signal early warning), the improved news pipeline (E60), the dashboard, and the Chapter I objectives.

**Branch:** `e62-final-audit` (local), created from `e60-accuracy-optimization` at 88d5266. Committed locally at the user's request (2026-10-19). **Not pushed, deployed or switched.** The production default is still E38.

**Frozen evidence:** E56–E61 untouched. All 21 freeze records match (`out/r8_frozen_check.json`); E56–E58 and `backend/data/e56`, `e58` are clean against HEAD.

**Evidence status:**
- All 50 evaluation rows (targets 2024-Q2..2026-Q3) had been examined by earlier experiments, so **every accuracy figure here is development evidence**.
- E62 did not tune, select or refit any model.
- The independent test is prospective: 2027-Q1 onward.

## 0. Answers to the ten questions

**1. Does the drop to 2027-Q1 reflect real changes, a model weakness, an implementation defect, or a combination?**

It is mostly a real change in the observed inputs, read through a target with a known weakness. It was amplified at one earlier origin by model-configuration switching. No implementation defect caused it.

The 2027-Q1 value is **not** a sudden drop from the forecast before it. The region mean was 0.32 for the 2026-Q3 back-test, **0.079 for the 2026-Q4 forecast** (issued 2026-07-01) and **0.084 for 2027-Q1** (`tables/r3_chronology_region.csv`).

**The fall happened at 2026-Q4.** Its causes, decomposed exactly from the served record's TreeSHAP (`r3`):
- **The CPI projection.** At the 2027-Q1 origin, latest food inflation was 0.25–3.6% (to 2026-08), against province thresholds of 4.7–7.2%. Headline inflation was 4.4–6.9%, so the gap was −2.1 to −4.2 points against thresholds of −0.56 to +0.92.
- **A configuration switch** from 23 to 68. Its non-price trees moved the log-odds by about −1.9 in Batangas, Cavite and Rizal. At 2027-Q1 the switch back to configuration 23 reversed this (+1.6 to +1.8).

**The observed outcomes agree** with low values under this target: 1 HIGH in the last 20 observed province-quarters (2025-Q4..2026-Q3), recomputed from the raw PSA and SWS files.

**The weakness is the target, not the arithmetic.** The gap condition reads a non-food price surge as relief. In 2026-Q3 hunger was 23.6% and headline inflation 4.8–7.3%, yet the label is LOW. The low 2027-Q1 value is therefore well supported *as a forecast of this indicator*. It is **not** evidence that food stress or affordability improved.

**2. How often did similarly low forecasts turn out HIGH?** (`out/r2_metrics.json`)

| Forecast | Below 0.20 | Turned HIGH | Below 0.10 | Turned HIGH |
|---|---|---|---|---|
| P(HIGH) | 14 | **6** | 4 | 0 (Wilson CI 0–49%) |
| P_price | 11 | **3** | 3 | 0 |

The 2027-Q1 values are 0.04–0.15.

What the cases show:
- **Four of the six P(HIGH) misses are 2024-Q2.** The hunger reading was stale (10.3% posted vs 19.6% actual). The hunger part, not prices, made those forecasts low, which does not apply in 2027-Q1 (P_hunger 0.96).
- **The three P_price misses had specific causes:**
  - 2024-Q4 Cavite and Laguna: the gap rose after the issue date, during the October–November 2024 typhoons.
  - 2026-Q2 Cavite: food YoY 4.73 vs threshold 4.71, a knife-edge.
- **Reading:** low values were usually right, but about a quarter of P_price values below 0.20 were followed by HIGH. That figure is quoted in the dashboard text.

**3. Are the probabilities statistically reliable and correctly interpreted?**

They are not reliable as precise probabilities.
- E56 calibration slope 0.55 (CI 0.17–1.49, E61); calibration-in-the-large +0.07.
- Brier 0.214 [quarter-cluster CI 0.149–0.298] on 50 rows, 10 quarters.
- The product is not a joint probability (section 4). The dashboard calls it a "model score … not a tested probability", which is correct.
- The two parts are reported separately (E61 K3).

**4. Are the data, features, labels, calculations and processing correct?**

| What | Result |
|---|---|
| Labels | Recomputed from raw PSA CPI YoY and SWS rounds with my own code: **0 mismatches** in 90 E58 event rows and 115 E61 rows (`r1`). |
| Back-test probabilities | The served record equals the sealed E57 file (max difference 5e-5, which is rounding; 0 configuration mismatches). |
| Attribution | Adds up to P_price at every origin (max error 6e-5). |
| Served values | Equal the record (`r6`). |
| No-leakage evidence | E59/E61 truncation tests, and E62's own news timing check (`r5`): 0 date or quarter errors; E60 features recomputed exactly. |
| New or remaining weaknesses | Approved-only hunger input vs all-rounds label (W5); configuration switching (W3); hunger over-prediction (W4); remittances missing in 2027-Q1 (W8). |

**5. Did the improved news reach training and inference, and did it help?**

- **Training and inference:** it reached E60's experimental training and evaluation, **not** the served model. The served schema uses only the old E40 keyword shares.
- **Ablation, reproduced independently on the same 50 rows (`r2`):**
  - government-only (E60-A) Brier 0.212;
  - government + original news (E56) 0.214;
  - government + improved news (E60-C) 0.215;
  - improved news only (E60-B) 0.445.
- **No candidate is significantly different.** C vs A: +0.003; the warning-form difference is −0.002 [−0.019, +0.013], sign test p = 0.51.
- **News reduced false alarms** (LOW recall 0.875 vs 0.81) but missed 3 more HIGH cases (recall 0.61 vs 0.78).
- **Improved news did not improve prediction.** It did improve classification (F1 0.38 → 0.83 on AI-annotated titles). Those are separate achievements.
- **E61's `NEWS_PIPELINE_USE_AUDIT.md` ("not evaluated") is superseded** by E60's later run, which E62 reproduced.

**6. Are the provincial forecasts, LGU outputs, SHAP explanations, news and dashboard consistent with the backend?**

Yes, after the three fixes (`r6`, browser check):
- 5/5 province scores equal the record;
- the region score is the mean of the five provinces (documented);
- 12/12 series points per province equal the record;
- 142/142 LGUs, unique and finite;
- the trigger contributions equal the record's grouped TreeSHAP;
- the sentence's figures equal the record's observations.

Defects found and fixed:
- **D-E62-1:** the unemployment caveat was missing for Rizal and Batangas.
- **D-E62-2:** the 2026-Q4 forecast's "supporting news" was published after its issue date.
- **D-E62-3:** the back-test news timing note was wrong.

Remaining issue: news **leads are empty** (titles only, disclosed; W6).

**7. Is the dashboard fast enough, and what was measured?** (`out/r7_performance.json`, local, same machine)

The E61 record cache was measured before and after by E62's own runner:

| E58 mode | Before | After |
|---|---|---|
| Fresh server, until the forecast is in | 9.3 s | **1.8 s** |
| Fresh server, until all 12 requests are in | 11.4 s | **1.8 s** |
| Warm server, all requests | 9.3 s | **0.14 s** |

- E38 default: about 2.2 s fresh and 0.08 s warm, unchanged.
- News requests run in parallel with the forecast and do not block it.
- E62's fixes add no measurable cost.
- **The deployed site was not measured** (not reachable from here).

**8. Which Chapter I objectives are met?** See `OBJECTIVE_COMPLIANCE_MATRIX.md`.

| Objective | Status |
|---|---|
| General objective: develop | met |
| General objective: validate | **not met** |
| General objective: deploy | partially met |
| Obj 1 (NLP pipeline, FSSI) | partially met |
| Obj 2 (metrics I–IV) | met, development only |
| Obj 2 V (multiple lead times, furthest reliable horizon) | **not met** |
| Obj 3 (LGU rankings) | partially met (province forecasts not validated) |
| Obj 4 (baseline comparison) | met as a comparison; superiority not statistically established |
| Obj 5 (dashboard) | partially met |
| Obj 5: ISO/IEC 25010 evaluation | not yet verifiable |
| Obj 5: FNRI face validity | not met |

**9. Which defects were fixed and verified?** D-E62-1, D-E62-2 and D-E62-3. Each has a regression test, and D-E62-1 was also checked in the live local dashboard. Backend suite: **423 passed, 18 skipped** (414 / 18 before). Detail in `DEFECTS_AND_CHANGES.md`.

**10. What prevents calling this a validated food-insecurity forecasting system?**
1. **No provincial food-insecurity outcome exists in the data** (no CBMS or provincial FIES). SWS is regional, so in 2024–26 the target's provincial variation is CPI price pressure only.
2. **The target's gap rule** treats faster non-food inflation as lower risk.
3. **The evaluation base is small:** 50 development rows, 10 quarters, one hunger regime, no unseen quarter yet.
4. **The probabilities are not calibrated precisely**, and the product is not a joint probability.
5. **Only one lead time was evaluated.**
6. **News adds no measured predictive value**, and the leads are missing.
7. **No ISO/IEC 25010 or DA evaluation has been run**, and there is no FNRI face-validity check.

## 1. Backend processing audit, stage by stage

| Stage | What was checked | Result |
|---|---|---|
| 1–2 Sources and collection | PSA OpenSTAT 0012M4ACP22/23 (CPI), SWS rounds with posting dates, PSA LFS and production, NOAA IBTrACS/ONI, BSP remittances, Google News RSS titles | Traceable files in E40 `data_acquired`, `backend/data/inputs/sws_rounds.csv` and the E31/E60 stores. **No pre-2021 row** (asserted in `r1`, `r5`). The news is retrospective: 2,118 of 2,132 E60 articles were first seen after their quarter's issue date (`r5`), so coverage at past issue dates cannot be reproduced. |
| 3–5 Parsing, dates, quarters, units, locations | CPI YoY in %, the gap in percentage points, SWS H in %; GMT→PH date for news | No duplicate CPI rows. PH date = GMT + 8 h for all 2,132 E60 articles; quarter = quarter(PH date) for all 9,667 classified titles (`r5`). Province codes map to 5 provinces and 142 LGUs (`r6`). |
| 6 Missing values | LightGBM `missing_type = NaN`; the ridge (hunger part) uses median plus indicator | Not zero-filled. Remittances are missing at 2027-Q1 and disclosed (W8). Rice is missing for 11 of 95 province-quarters before 2022. |
| 7 Deduplication | article_key unique in both stores; syndicated copies | 2 syndicated duplicate groups among relevant attributed titles (`r5`); `nz_events` counts distinct titles. |
| 8 Features, windows, lags | CPI to month 2 of t; SWS posted before O(t); production, LFS and remittances to t−1; news of quarter t | E59/E61 truncation tests passed (40/40 identical). The E62 news recompute is exact. The hunger input is approved rounds only (W5). |
| 9–10 Training, selection | Nested per-origin selection, 72 configurations | Configuration varies by origin (9 distinct of 12), which causes forecast jumps (W3). |
| 11 Inference | Served record vs sealed E57 vs artifacts | Equal (5e-5). E61 a1 reproduced the 2027-Q1 value four ways (3.7e-7). |
| 12 Calibration / post-processing | None (product of the two parts) | The product is not a joint probability (section 4). |
| 13 SHAP | Exact TreeSHAP; the record's `checks.treeshap_reconstruction_error` | Sums to P_price at every origin (`r3`); served contributions equal the record (`r6`). |
| 14 Serialization and caching | Record cache per (path, mtime, size); dashboard lru caches keyed by mode | Serving does not mutate the cached record (deep hash before and after, test). A changed file is re-read (E61 test). |
| 15 Frontend | The approved components render the backend fields | Browser check: Rizal 0.05; region 0.08; sentence with caveat. **No component or style changed.** |

## 2. Chronological forecast versus observation

Full table: `tables/r3_chronology_by_province.csv` (50 columns: P, the parts, configuration, as-of food, headline, gap, rice, unemployment, remittance availability, news shares, SWS value / quarter / posting date / age, observed outcome and inflation, and the change decomposition). Readable version: `tables/r3_chronology_compact.md`.

**Region view** (mean of the five provinces; `tables/r3_chronology_region.csv`):

| Target | Issued | Mean P(HIGH) | P_hunger | HIGH observed (of 5) | Food YoY at issue | Gap at issue | Configuration(s) |
|---|---|---|---|---|---|---|---|
| 2024-Q2 | 2024-01-01 | 0.19 | 0.21 | 4 | 4.27 | +0.29 | 46 |
| 2024-Q3 | 2024-04-01 | 0.50 | 1.00 | 1 | 0.85 | −1.57 | 27 |
| 2024-Q4 | 2024-07-01 | 0.26 | 1.00 | 3 | 4.75 | +1.00 | 41 |
| 2025-Q1 | 2024-10-01 | 0.55 | 1.00 | 4 | 4.49 | +0.66 | 41 |
| 2025-Q2 | 2025-01-01 | 0.70 | 1.00 | 3 | 3.57 | +0.91 | 37 |
| 2025-Q3 | 2025-04-01 | 0.62 | 1.00 | 2 | 5.41 | +2.45 | 68 |
| 2025-Q4 | 2025-07-01 | 0.24 | 1.00 | 0 | 2.44 | +0.70 | 61 |
| 2026-Q1 | 2025-10-01 | 0.30 | 1.00 | 0 | 2.06 | +0.03 | 54 |
| 2026-Q2 | 2026-01-01 | 0.21 | 1.00 | 1 | 1.26 | −0.76 | 50 |
| 2026-Q3 | 2026-04-01 | 0.32 | 0.95 | 0 | 0.60 | −1.58 | 23 |
| 2026-Q4 | 2026-07-01 | **0.079** | 1.00 | (not yet known) | 4.38 | −2.80 | 68 |
| 2027-Q1 | 2026-10-01 | **0.084** | 0.96 | (not yet known) | 2.44 | −3.28 | 23 |

**Large changes** (|ΔP| ≥ 0.25, 18 province-quarters, `out/r3_chronology.json`):

| Main driver | Count | Cases |
|---|---|---|
| Change in the CPI projection | 13 | — |
| Hunger gate | 3 | 2024-Q3 (Cavite, Laguna, Quezon): the stale 2023-Q3 hunger reading was replaced |
| Tree contributions | 2 | Cavite 2024-Q4 (price-group trees −1.80); Cavite 2026-Q4 (configuration 68's non-price trees −1.87) |

- **Configuration changed** at 14 of the 18.
- **No large change** came from a serving or unit defect.

**Rolling-origin metrics** (independently re-scored, `tables/r2_model_comparison_50rows.csv`; CIs bootstrap whole quarters):

| Model | Correct /50 | Accuracy [CI] | Balanced | HIGH recall | HIGH precision | LOW recall | Brier [CI] | Log loss | Onsets | Quarters ≥ 0.75 |
|---|---|---|---|---|---|---|---|---|---|---|
| E56 (served P(HIGH)) | 36 | 0.72 [0.58, 0.84] | 0.684 | 0.556 | 0.625 | 0.812 | 0.214 [0.149, 0.298] | 0.623 | 3/10 | 6 |
| E58-EW (warning form) | 39 | 0.78 [0.70, 0.86] | 0.780 | 0.778 | 0.667 | 0.781 | 0.182 (P_price) | 0.562 | 7/10 | 7 |
| E60-A gov-only | 37 | 0.74 | 0.700 | 0.556 | 0.667 | 0.844 | 0.212 | 0.619 | 3/10 | 7 |
| E60-C gov + improved news | 37 | 0.74 | 0.675 | 0.444 | 0.727 | 0.906 | 0.215 | 0.634 | 3/10 | 7 |
| E60-B improved news only | 18 | 0.36 | 0.427 | 0.667 | — | 0.188 | 0.445 | 1.380 | 5/10 | 0 |
| Price projection only | 37 | 0.74 | 0.748 | 0.778 | 0.609 | 0.719 | 0.188 | 0.554 | 7/10 | 7 |
| Persistence | 28 | 0.56 | 0.535 | 0.444 | 0.400 | 0.625 | 0.440 | 6.08 | 0/10 | 3 |
| Majority (as of the issue date) | 32 | 0.64 | 0.500 | 0 | — | 1.000 | 0.360 | 4.97 | 0/10 | 5 |

- **By quarter:** E56 accuracy ranges from 0.2 (2024-Q2) to 1.0 (2025-Q4, 2026-Q1).
- **By province:** Cavite 4/10, Rizal 10/10 (no HIGH), Quezon 8/10 (`tables/r2_by_quarter.csv`, `r2_by_province.csv`).
- **Calibration bins:** `tables/r2_reliability_bins.csv`.

## 3. Forecast continuity

- **No smoothing, capping or averaging was applied or recommended.**
- **The jumps have identifiable sources:** projected CPI changes (legitimate), plus configuration switching between origins (W3, a modelling weakness).
- **A defensible monitoring diagnostic:** at each new issue, report the decomposition above. Δ log P_hunger, Δ CPI projection, Δ trees, and a "configuration changed" flag are all available from the record. Any |ΔP| ≥ 0.25 with a configuration change should be flagged for review.
  - This is a review step, not a change to the probabilities.
  - It is **proposed, not implemented**, because adding it to the dashboard would be a new UI element.

## 4. E58 probability construction and target validity

**Reproduction:** P(HIGH) = P_hunger × P_price, reproduced from the record at every origin (`r3`). The served values equal the sealed values.

**Independence** (`out/r4_joint_and_rice.json`, 105 province-quarters, 21 quarters):

| Measure | Result |
|---|---|
| P(PS ∣ H > 11.3) | 0.33 |
| P(PS ∣ H ≤ 11.3) | 0.69 |
| Fisher test, row level | p = 0.0008 |
| Quarter permutation (rows inside a quarter are not independent) | p = 0.039 |
| Quarter-level Spearman | −0.25, p = 0.28 |
| Hunger trend over time | ρ = 0.76, p = 0.0001 |

- **Reading:** the dependence is real but **entangled with time**. All 7 low-hunger quarters fall in 2021-Q3..2023-Q3, the high-food-inflation period.
- **The product is not a valid joint probability.** On the evaluation rows hunger was always above 11.3, so the relevant quantity is P(PS ∣ H high). The conditional model (K1) and the calibrated combination (K2) did not do better (E61). Reporting the two parts separately (K3) is the defensible presentation, and it is what the dashboard does.

**Target validity:**
- In 2024–26, T43 equals price pressure on all 50 rows.
- The gap rule counts a headline surge as relief (W1).
- No independent provincial food-insecurity outcome exists.
- **The model is not validated as a predictor of provincial food insecurity.** It forecasts an exploratory food-stress risk indicator whose provincial skill is in CPI price pressure.

## 5. Drift, rice and other features

**Flat-price drift (m = 0).** E62 confirmed that it is *selected* per origin (m = 0 at 8 of 12 origins, including 2027-Q1), not fixed.
- E61's drift alternatives D1–D3 raised 2027-Q1 to between 0.09–0.41 (D1) and 0.13–0.46 (D3, no projection), but did not forecast better (no supported difference).
- **The original is kept.** Adopting a variant would only raise the number.

**Rice wholesale** (`r4`, 74 pairs). Units are YoY % from PSA wholesale prices, quarter t−1. Missing in 11 of 95 rows before 2022.

| Measure | Result |
|---|---|
| Spearman vs food YoY two quarters later | 0.06 (p = 0.61) |
| Latest food YoY, same comparison | 0.39 (p = 0.0006) |
| Partial r of rice given the latest food YoY | 0.002 |
| Quarter level, n = 16 | −0.03 |
| AUC for the PS label | rice 0.64 vs latest food 0.75 |

- **No out-of-sample signal:** removing rice gives ΔBrier +0.004, no difference (E61).
- **2027-Q1:** rice wholesale was +11% to +29% YoY in 2026-Q2. The history says this does not anticipate food YoY two quarters later; in 2024, rice at +30% was followed by food at about 3%. So the zero weight is **not shown to be a defect**.
- The rice rebound is still worth showing as evidence in the trigger notes, and it is (Market card).

**Other features:**
- **News shares are mostly zero.** Served E40 shares are zero in 96–100% of the 50 rows for market, fish kill, employment and OFW (46% for climate). The E60 v2 features are zero in 56–100%, and 17 of 50 province-quarters have no relevant attributed article (`r5`).
- **The hunger part leans on total news volume:** without it, RMSE is 8.01 vs 8.24 (E61).
- **Unemployment** lowers the score in all provinces while unemployment rose. The explanation is now fixed (D-E62-1); the feature is kept (removing it gives ΔBrier +0.001).
- **Remittances:** missing value handled through a tree branch (W8).
- **Trend gap:** the current-condition feature C3 was rejected (E61).

## 6. News pipeline: step-by-step evidence

| Step | Status | Evidence |
|---|---|---|
| Collected | Done: 2,070 requests, 1,347 new titles; corpus 9,667 | E60 `runs.jsonl` COMPLETED 2026-10-19 08:52Z; `r5` |
| Filtered and classified (v2) | Done; frozen sha `327f9431…` before EVAL | E60; annotations by AI, **not human-verified** |
| Province attribution | 297 of 697 relevant titles attributed; geocoder 27/27 correct on the EVAL sample | E60, `r5` |
| Features | Built and recomputed exactly by E62 | `r5`: max difference 1e-16 |
| Training and evaluation | E60 candidates A/B/C/D on the same 50 rows; sealed | `r2` reproduces E60 |
| Served model / dashboard | **Not in the served model.** The dashboard feed uses the E45 pool (E31 store, v1 keywords + R1.1). The v2 feed (E60 proposal P1) is not applied. | `r5`, served schema |
| Leakage | Only articles of quarter t with PH date < O(t); PH date equals GMT + 8 h | `r5`; E60 tests |
| Remaining risk | Retrospective collection: coverage at past issue dates is unknown. The classifier was designed in October 2026 (design-time knowledge). | Documented |

## 7. Tests (full suites)

| Suite | Before E62 | After E62 |
|---|---|---|
| Backend `pytest` (all) | 414 passed, 18 skipped | **423 passed, 18 skipped** (3 warnings: scikit-learn unpickle version, W9) |
| New `test_e62_final_audit.py` | — | 9 passed |
| Frontend vitest | 46 passed | 46 passed (frontend unchanged) |
| Frontend `tsc --noEmit -p tsconfig.app.json` | 6 errors, all in `src/data/mockData.ts` | same (unchanged, pre-existing) |
| Production build | passes | passes (1.93 MB main chunk) |
| Freeze records E56–E61 | — | 21/21 match |

The 18 skipped tests are skipped by their own conditions: absent optional records, or modes without a governing record.

## 8. Remaining limitations and the evidence still needed

1. **Prospective scoring of the frozen 2027-Q1 forecast** (E56 manifest; E58 record) once the 2027-Q1 SWS round and the January–March 2027 CPI are published.
2. **A provincial food-insecurity outcome** (CBMS FIES or provincial FIES/NNS) to validate T43 or replace it.
3. **An adviser decision on the target's gap rule** (W1), scored prospectively only.
4. **An adviser decision on the issue date** (after each SWS release; E59 S1).
5. **A lead-time study** (Objective 2 V).
6. **Human verification of the news annotations**, and prospective news collection with collection timestamps.
7. **News leads** (W6): a lead dataset from publisher meta descriptions needs your go-ahead for the token-resolution step.
8. **The ISO/IEC 25010 evaluation with 50 DA IV-A evaluators**, plus the H4 ranking survey.
9. **The BSP 2026 remittance download** (manual).
10. **Deployment measurement** (Render/Vercel) once a URL is available.

## 9. Final recommendation

**Production:** keep **E38** as the default.
- E58 (E56 + early warning) stays an **experimental, historical-demonstration** model behind `AIPHEED_LEAD2_MODEL=e58`. Its explanations, series, news timing and speed are now consistent and tested locally.
- Do **not** switch production to a new model; no candidate (E60-A, E60-C, E61 C1–C4, D1–D3, K1–K2) is significantly better.
- Applying the E62 fixes and committing E59–E62 need your approval.

**Thesis:**
- Report E56/E58 as a **forecast of an exploratory food-stress risk indicator** (regional SWS hunger and provincial PSA food-price pressure), with development accuracy 0.72 (E56) and 0.78 (E58-EW warning form) on 50 rows.
- Say that the **75% development goal is not met by the probability forecast**; the warning form reaches it on development rows only.
- Say that **news improved classification but not forecasting**.
- Say that the **low 2027-Q1 value is supported by observed price data under the current target**, and that it is **not evidence of affordability**: hunger was 23.6% and headline inflation exceeded food inflation.
- Say that **validation, the lead-time study, ISO 25010 and FNRI face validity remain outstanding**.

## Reproduce

Run from `backend/` with `venv/Scripts/python.exe -B <script>`. Paths are relative to this folder.

| Script | Output |
|---|---|
| `runner/r1_labels_independent.py` | `tables/r1_labels_independent.csv`, `out/r1_labels_check.json` |
| `runner/r2_metrics_independent.py` | `tables/r2_*`, `out/r2_metrics.json` |
| `runner/r3_chronology.py` | `tables/r3_*`, `out/r3_chronology.json` |
| `runner/r4_joint_and_rice.py` | `tables/r4_rice_vs_food_by_quarter.csv`, `out/r4_joint_and_rice.json` |
| `runner/r5_news_timing.py` | `out/r5_news_timing.json` |
| `runner/r6_api_consistency.py` | `out/r6_api_consistency_e58.json`, `out/r6_sample_responses_e58.json` |
| `runner/r7_measure.py` (uses `r7_serve_variant.py`) | `out/r7_performance.json` |
| `runner/r8_frozen_check.py` | `out/r8_frozen_check.json` |
| `runner/serve_e62_stack.py` | local preview: API 8062 (E58 mode), frontend 8092 |

**Note on `out/r6_api_consistency_e58.json`:** this run was made **before** the fixes. Its three FAIL lines are:
- the clock fields (expected, not a defect);
- LGU rank ties (genuine ties, not a defect);
- D-E62-1, since fixed.

The checks are re-asserted after the fixes by `backend/tests/integration/test_e62_final_audit.py`.
