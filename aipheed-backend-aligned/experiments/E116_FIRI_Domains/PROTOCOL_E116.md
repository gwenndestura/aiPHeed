# PROTOCOL_E116: do the FIRI domains carry information about future hunger? (frozen 2026-10-30, before any fit)

**Hash.** This file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt`; both are committed before `runner/run_e116.py` runs.

**Unchanged.**
- The served model, dashboard, API, map colours and approved design.
- E114's protocol and results.
- E115 is **suspended** at the owner's instruction (2026-10-30). No forecast was issued or sealed under it.

## 1. Why E114's indicators could not contribute (the diagnosis this experiment tests)

| Suspected cause | Evidence before this run |
|---|---|
| **Resolution mismatch** | In E114, market, employment and climate inputs were national: one value per quarter, shared by four SWS areas, so they could not explain differences between areas. In the provincial T43c design, the target is one regional hunger value copied to five provinces. |
| **Coverage** | Fish (C4) and OFW remittances (E2) existed in the repository only from 2020-21, so neither was in E114. News starts in 2018. No dated poverty series exists. |
| **Target circularity (T43c)** | T43c's price component is computed from the same provincial CPI as indicators A1/A2. "Market contributes" there is partly the target predicting itself. T43c is therefore **not** used here. |
| **Target scope** | SWS hunger is experienced hunger, the severe end of food insecurity, regional and quarterly. No broader food-insecurity series exists over time. FNRI FIES (ENNS 2021: 2 provinces and 1 HUC; NNS 2023: region) and PSA subsistence incidence (provincial 2021 and 2023) are cross-sectional snapshots. CBMS 2024 is a single window, not in the repository. |
| **Signal vs survey noise** | Balance Luzon margin of error is ±4 pp, comparable to the quarter-to-quarter change. |

**What this experiment changes.**
- **Area-level inputs** where official series exist (`data/area_cpi.csv`, `data/area_fish.csv`, `data/area_palay.csv`, from PSA OpenSTAT, fetched 2026-10-30, hashes in `data/fetch_log.json`).
- **A long-history fish production series** (1993+).
- **An explicit, separate test of each domain.**

## 2. Target

- **Outcome:** SWS Total Hunger by area (NCR, Balance Luzon, Visayas, Mindanao), 1998-2026, from `../E114_Final_Run/data/sws_area_rounds_full.csv`.
- **What it is:** observed experienced hunger, regional. It is **not** called provincial food insecurity, and it is not built from any predictor.
- **Leads and issue date:** as E114. Issue O(t) = day 1 of quarter t+1; Lead k targets quarter t+k.
- **SWS availability:** only rounds published before O(t) are used.

## 3. Domains and features (all point-in-time)

| Domain (FIRI indicators) | Features (area-level unless stated) | Availability rule |
|---|---|---|
| Base: hunger history (H1) | h_last, MR (h_last − known mean), d_last, staleness, lead, area | SWS published < O(t) |
| Market and food prices (A1, A2, A3) | area food CPI YoY (2-month mean, newest months); area food − all-items YoY; 1-year change of area food YoY; national rice CPI YoY | month m usable from day 10 of m+1 |
| Fish production (C4) | area fisheries production YoY (quarter t−1); its change vs 4 quarters earlier | quarter t−1 at O(t) (assumed; S-LAG sensitivity) |
| Climate (C1, C2, C3) | ONI (newest); El Niño flag (ONI ≥ 0.5); typhoon count change (PAR, national); area palay YoY (t−1; none for NCR) | ONI day 10; typhoons quarter t; palay t−1 |
| Employment (E1) | national unemployment change (1 year) | LFS month m usable from m+3 |
| OFW remittances (E2) | **not testable over 1998-2026.** BSP blocks automated access (HTTP 403, not circumvented). The repository holds 2021+ only. Reported as a data gap. | — |
| News / NLP (N1, other input) | GDELT supply and assistance YoY (2018+) | quarter after its end |
| Poverty (V1, other input) | no dated time-varying series: not representable | — |

**Missing values** use LightGBM's native NaN handling. Nothing is imputed or scaled.

## 4. Variants (each fitted by E114's unified LightGBM recipe: target = change; grid depth {1,2} × trees {100,300}, lr 0.03, min_child 20, λ 5, seed 114; configuration chosen by the last 4 inner chronological folds at each origin)

| Code | Features |
|---|---|
| V1 BASE | base |
| V2 +MARKET | base + market |
| V3 +FISH | base + fish |
| V4 +CLIMATE | base + climate |
| V5 +EMPLOYMENT | base + employment |
| V6 ALL5 | base + market, fish, climate, employment (OFW unavailable) |
| V7 ALL5-ADD | as V6, with LightGBM interaction constraints: no cross-domain interactions |
| V8 FULL | V6 + news |
| X1 market × employment | base + market + employment + product (area food YoY × unemployment change) |
| X2 fish × climate | base + fish + climate + product (fish YoY × ONI) |
| X3 climate × market | base + climate + market + product (ONI × area food YoY) |

- **Pairs that cannot be tested:** market × poverty and employment × OFW. Their data do not exist over time.
- **Comparators:** RW (latest reading) and DAMP (E114's damped mean reversion), reported for reference only.

## 5. Evaluation

**Periods.**

| Period | Targets | Role |
|---|---|---|
| **DEV** | 2003-Q1 to 2012-Q4 | primary evidence for contributions |
| **TEST** | 2013-Q1 to 2020-Q4 | confirmation. Scored once before by E114 with national covariates, so it is a second use: confirmation only, nothing selected on it |
| **SECONDARY** | 2021-Q1 to 2026-Q3 | inspected before |

**A domain "adds information"** at lead k only if both hold:
- Δ MSE (V2-V5 vs V1, area-pooled, averaged by target quarter) is negative on DEV, with the quarter-block bootstrap 90% CI below 0 and Holm-corrected p < 0.10 across the 4 testable domains;
- the sign is the same on TEST.

**Complementarity.** V6 vs the best single domain, and V6 vs V7 (the value of cross-domain interactions). X1-X3 vs their no-product counterparts.

**Also reported for V1, V6 and V8:**
- **Grouped permutation importance.** Each domain's columns are permuted within the scored rows at every origin; 20 permutations, seed 116; Δ MSE.
- **SHAP.** Mean |SHAP| by domain, as description only.
- **Leave-one-area-out:** Δ MSE vs V1 per area.
- **Train vs test MSE.**
- **"Above usual" metrics** (as E114): accuracy, balanced accuracy, precision, recall, F1, Brier, calibration slope.
- **S-LAG:** the fish and palay lags shifted one quarter later.

## 6. Decision (no integration in any case)

**The finding for each domain is one of three:**
- adds information;
- not established;
- possible noise (CI above 0).

**Inclusion is not presented as contribution.** No group weight is inflated.

**A recommendation is written only after these results.** Any change to the served system needs the owner's approval.
