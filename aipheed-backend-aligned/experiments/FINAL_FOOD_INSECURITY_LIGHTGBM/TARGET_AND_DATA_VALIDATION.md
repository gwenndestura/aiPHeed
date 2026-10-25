# Target and data validation

**Rules:** `FINAL_PROTOCOL.md` (sha `86de5c8c…`, frozen 2026-10-25T12:15Z), §2, §3 and §8.5.

**Records:** every source file is listed with its SHA-256 in `data/data_sources.csv`. Every model column is listed in `data/feature_map.csv`, with its source, geographic level, period, availability rule and missingness.

## 1. SWS quarterly hunger (the outcome)

| Item | Finding |
|---|---|
| Measure | SWS involuntary ("Total") hunger: the % of families who experienced hunger at least once in the past 3 months. Moderate and severe are frequency categories, not risk thresholds. |
| Primary file | `data/sws_area_rounds_2021.csv`: 23 non-commissioned rounds, 2021-Q2 … 2026-Q3. This is the E110 file, with every Balance Luzon value checked against SWS. |
| Independent check | Every 2021+ row is identical to E114's series, which was read from SWS's own media-release tables (14 Oct 2026). Values and publication dates were checked programmatically. |
| Excluded | The March 2025 Stratbase-SWS round (commissioned, registered voters) and the April 2025 voter round. Both are listed in `sws_area_rounds_2021_excluded.csv`. |
| Geographic coverage | 4 areas: NCR, Balance Luzon (BL), Visayas, Mindanao. **No province or municipality.** BL contains CALABARZON. |
| Sample sizes and margins | BL n = 300–1,080, margin ±3 to ±6 points. Other areas ±5 to ±6. 2025–26: 1,500-respondent rounds (BL ±4) in March, April and September; 1,200-respondent rounds (BL ±6) in June and November. |
| Method change | The respondent base was household heads until December 2024 and adults from April 2025 (7 of the 23 rounds). There is no bridging round, so this is a known break. |
| Survey timing | Quarterly. 2021-Q1, 2022-Q1 and 2025-Q1 have no usable round. 2021-Q2, 2022-Q2 and 2025-Q2 have two rounds each; the quarter value is their mean. |
| Publication delay | 17–99 days after fieldwork ends (median 42, mean 45). |
| Real-time rule | A round enters a forecast only if it was published before the issue date (vintage). Example: the 2024-Q3 round, published 17 Oct 2024, is **not** used at the 1 Oct 2024 issue. |
| Source quality | 14 of 23 rounds are read from SWS releases. The 2021–22 rounds come from news reports or search summaries of SWS releases, because the old sws.org.ph pages return 404. They were cross-checked against SWS's own 2026 tables (E114). |

**Not done.** SWS regional values are never treated as provincial or municipal rates.

### Secondary-arm series (flagged for adviser approval)

- **Content:** `data/long/sws_area_rounds_full.csv`, from SWS's own tables: 115 rounds from 1998-Q3.
  - 92 rounds are before 2021: 89 face-to-face and 3 mobile-phone rounds in 2020.
  - 36 of 36 values matched news reports (`sws_news_crosscheck.csv`).
  - 1 table conflict and 6 rounding notes are recorded (`sws_extraction_checks.csv`).
- **Publication dates:** pre-2021 dates are set to label month end + 60 days. This is conservative: 10 dated releases show 2–43 days (`sws_release_date_evidence.csv`).
- **Margins:** set to ±6 for every pre-2021 area.

## 2. The prediction target

**Continuous target.** H(a, q), hunger in area a at quarter q, in percentage points. It is scored with MAE and RMSE.

**Classification target: ELEVATED**
- **Definition:** ELEVATED(a,q) = 1 if H(a,q) is above the mean of the area's readings in the four previous quarters (at least two are needed).
- **Meaning:** "Hunger is worse than this area's average over the past year."
- **Status:** researcher-defined. It is not an official SWS or PSA classification.

**Why a new label was needed**
- Chapter I Objective 2 asks for accuracy, precision, recall, F1 and AUC.
- Fixed thresholds are one-class after 2023. Every evaluated quarter is above 11.3%, so those metrics are degenerate (E109).
- The Chapter I §1.7 rule "SWS > 11.3 AND price pressure" (T43) has the same problem, and is partly a price label (E107–E108).
- ELEVATED stays two-class across the 2024 level shift (base rate 0.57 over 2021+) and uses no pre-2021 data.

**It was fixed before scoring.** No other label was tried for the verdict.

**Issue date and horizon**
- Forecasts are issued on the first day of each quarter.
- At Lead k the target is the k-th quarter from the origin. At Lead 1, the target quarter starts on the issue date.
- Because SWS publishes 1–3 months after fieldwork, the newest reading at the issue date is usually two quarters before the Lead-1 target. The true horizon is therefore 2 (`MAXIMUM_RELIABLE_LEAD_TIME.md`).

**Reference (REF) at the issue date**
- REF uses the readings known at that date.
- Quarters after the newest reading are filled with the newest reading (persistence).
- REF is a decision boundary and a feature, never the label.

## 3. PSA provincial food CPI deviation (economic access)

| Item | Finding |
|---|---|
| Source | PSA OpenSTAT provincial CPI, 2018 = 100, for the 5 CALABARZON provinces: food (01.1) and all items. PSA-published year-on-year (YoY) rates are used (E40 file). |
| Base period | 2018 = 100 throughout 2021–2026, so there is no base mixing. YoY rates for 2021 months use 2020 months; this is the label's own definition and is allowed by the study-window rule. |
| Coverage | 115 province-quarters, 2021-Q1 … 2026-Q3. No missing months. |
| Publication delay | PSA releases month m around the 5th of month m+1. At a first-of-quarter issue date the newest usable month is month 2 of the previous quarter (rule from E41). |
| Revisions | Year-on-year rates are taken as published. PSA did not rebase within the window. |

**Chosen deviation measure: FPD**
- **Definition:** FPD(p,q) = province food YoY − province all-items YoY, as the quarter mean. It measures food prices rising faster than general prices.
- **Why this measure**
  1. It needs no pre-2021 trend window; a "deviation from trend" measure would need history before 2021.
  2. Its threshold, zero, is a natural reference, not a fitted percentile.
  3. It measures an access squeeze rather than general inflation.

**Food-price squeeze = FPD > 0**
- **Rates:** 54% of province-quarters overall. By province: Laguna 70%, Batangas 65%, Cavite 52%, Quezon 48%, Rizal 35%.
- **Not used:** a squeeze is **not** labelled food insecurity, and PSA CPI is never used as evidence that hunger was predicted.

**Results** (`out/results_psa.json`)

| Check | Result |
|---|---|
| Squeeze sign forecastable by persistence? | Lead 1: 0.70 (n = 105). Lead 2: 0.63. Leads 3–4: 0.48 and 0.47 (no skill). |
| Concurrent link with BL ELEVATED (CALABARZON mean FPD) | ρ = 0.14, p = .59 (18 quarters). Squeeze with elevated hunger: 8 quarters; squeeze without: 4; elevated hunger without squeeze: 2. |
| FPD known at issue vs later BL hunger anomaly (Leads 1–4) | ρ from −0.17 to 0.20; every Holm p = 1 |

**Role of the two sources**
- SWS is the outcome.
- PSA is (i) the input families A1–A3, and (ii) a separate province-level economic-access indicator that can be shown one quarter ahead by persistence. It does not validate hunger forecasts.

## 4. News data

| Source | Content | Timestamp | Role |
|---|---|---|---|
| Project RSS headline corpus (E31 + E60) | 9,659 CALABARZON headlines, 2021-01 … 2026-10, after syndication de-duplication. 150–880 per quarter, growing about 4× over the window. 33% carry a province code from the E31 tagger. | PH-local publication date; date-only items stamped 16:00 PHT. 0% mismatch with `ph_date`. | Model input (N family) |
| GDELT GKG (E85) | 58,576 CALABARZON-located documents with themes; 2021-01 … 2026-10-14 | GDELT processing time, recorded in real time | Replication |
| GDELT DOC 2.0 (E114) | Daily national volume share for 4 categories (shortage, agri_supply, jobs_income, assistance), 2017–2026. The price and disaster series were not collected (rate limit). | Day d is usable after day d | Long arm and Addendum 2 replication |

**Collection limitation.** The corpus was collected retrospectively. Publication dates come from the feeds and are verifiable through each item's link, but the corpus is not a real-time archive. GDELT is the real-time check.

## 5. The 12 indicator families

Every column is computed at the issue date. Coverage and missingness are in `data/feature_map.csv`; missingness is measured on the scored origins.

| Family | Columns | Geography | Missing (scored) | Note |
|---|---|---|---|---|
| A1 Food-price pressure | `A1_food`, `A1_gap`, `A_since` (new) | Province → CALABARZON mean | 0% | `A_since` = food YoY change since the last survey |
| A2 Headline inflation | `A2` | Province | 0% | |
| A3 Wholesale rice | `A3` | Province | 0% | From 2022-Q2 |
| V1 Poverty and density | `V1` | Province (static) | 0% | Constant over time, so it can never split a tree in a regional model (SHAP 0) |
| C1 El Niño alert | `C1` | National | 0% | |
| C2 Typhoons within 300 km | `C2` | Province | 7.7% | 2026-Q3 not yet complete |
| C3 Palay/corn drop | `C3` | Province | 0% | |
| C4 Fisheries drop | `C4` | Province | 0% | |
| E1 Unemployment change | `E1` | National | 0% | |
| E2 Remittance decline | `E2` | National | 15.4% | Not acquired after 2025-Q4 |
| N1 News | `N1` (FSSI-v3) + `NC_gap_*` (6) + `NC_ant` (new) | CALABARZON news | N1 46%, NC_* 0% | NC_* are NaN only in 2021 (no year-earlier window) |
| H1 Regional hunger | `H1` + `h_last`, `h_anom`, `h_chg`, `h_age_q` | SWS area | 0% | |

**Shared context.** The 12-family values are CALABARZON indicators, given unchanged to all four SWS areas' rows. They are geographically exact for BL. The sensitivity run FIL-BL (BL rows only) had too few rows to evaluate: 2–5 per lead.

## 6. Leakage checks

**Leakage audit** (`out/leakage_audit.json`): **passed.**
- At 10 origins, FIL, PERSIST and LOGIT forecasts were identical after two perturbations: every SWS round published on or after the issue date was replaced with random values (52 rounds at the first origin), and the categories of every later headline were shuffled (6,939 headlines).
- **Negative control:** perturbing *earlier* rounds did change the forecasts, so the test can detect leakage.

**E107 feature cut-offs:** audited in E107 and E113 (passed).

**Window assertion:** the primary loader raises an error on any pre-2021 row.

**Tests:** `backend/tests/unit/test_final_fi_lgbm.py` checks every row's bookkeeping:
- the SWS publication date is before the issue date;
- the newest news item is before the issue date;
- the true horizon is at least the lead.
