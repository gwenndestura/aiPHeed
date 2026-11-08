# E119 final preprocessing report

**Scope.** Preprocessing only. No model was trained. Production, dashboard, raw files and FIRI v2 definitions are unchanged. Nothing was pushed or deployed.

**Frozen protocol.** `E119_PREPROCESSING_PROTOCOL.md` (commit d6e1ac0). Its hash is checked at every run.

**Rerun:**

```
cd runner
python preprocess.py   # datasets + PIT rows + per-indicator outputs; stops if a leakage check fails
python reports.py      # report tables
```

## 1. Result in one paragraph

The data are clean, aligned and point-in-time documented. All leakage checks pass.

- **Regional.** 39 forecasting rows have a target (SWS Balance Luzon hunger), with 24 features. 29 rows are complete on every feature.
- **Provincial.** 115 province-quarter rows (5 × 23), with 27 features and **no food-insecurity label**. 85 rows are complete on the 24 non-sparse features.

Every one of the 12 FIRI v2 indicators has a cleaned output. Most values are `rule_unverified`, because the release dates come from documented rules, not archived releases. A strict, verified-only model has 10 regional and 4 provincial features.

## 2. Exact usable observations and features

### A. Regional forecasting dataset (`E119_REGIONAL_MODELING_DATASET.csv`)

| Item | Count |
|---|---|
| Rows (origins 2021-Q1 to 2026-Q3 × leads 1, 2) | 46 |
| Rows with a published target | **39** (Lead 1: 20, Lead 2: 19) |
| Target origins | 2021-Q1 to 2026-Q2 |
| Predictor features | **24** |
| Rows with target and every feature present | **29** (Lead 1: 15, Lead 2: 14) |
| Strict (verified-only) features | 10: H1 latest, previous, change and staleness; C1; PAR typhoons; GDELT shares ×4 |
| Columns in file | 74 (each feature has `__status` and `__period` where it applies) |

**The 24 predictors:**
- **H1 ×4:** latest, previous, change, staleness.
- **A1/A2:** Region IV-A CPI food YoY and headline YoY.
- **A3 support:** farmgate palay YoY (PSA Region IV-A value).
- **C3, C4**, aquaculture YoY, vegetables YoY (PSA Region IV-A values).
- **C1**, ONI quarter mean.
- **Weather:** PAR typhoons; rainfall total and anomaly (CALABARZON mean of 5 centroids); temperature anomaly.
- **E1:** unemployment change and unemployment rate.
- **E2:** remittance decline.
- **GDELT category shares ×4.**

**Size warning.** 39 labelled rows is very small for LightGBM, and fewer than 2 rows per feature at each lead. This matches E109–E117, where nothing beat the latest SWS reading at Lead 2.

### B. Provincial vulnerability dataset (`E119_PROVINCIAL_VULNERABILITY_DATASET.csv`)

| Item | Count |
|---|---|
| Rows (5 provinces × 23 origins, 2021-Q1 to 2026-Q3) | **115** |
| Features | **27** |
| Non-sparse features (≤ 35% missing) | 24 |
| Rows complete on all 27 features | 39 |
| Rows complete on the 24 non-sparse features | **85** (17 per province) |
| Sparse features | N1 FSSI-v3 (56.5% missing: fewer than 5 admitted articles); chicken and livestock production YoY (60.9%: series start 2023) |
| Strict (verified-only) features | 4: C2, local typhoons within 100 km, N1 FSSI, N1 article count |
| Label | **none** (no repeated provincial food-insecurity measure exists; E118) |

**Annual provincial table** (`E119_PROVINCIAL_ANNUAL_INDICATORS.csv`, 68 rows), kept at its own frequency:
- V1 profile (5);
- subsistence incidence 2021 and 2023 (10);
- FIES 2023 food share (5);
- owner-file annual unemployment and underemployment 2021–2025 (48; 2024 unemployment derived as 100 − employment rate, flagged).

## 3. The 12 FIRI v2 indicators

From `E119_INDICATOR_PREPROCESSING_REPORT.csv`; each has `out/indicators/<code>/observations_clean.csv`.

| Indicator | Domain | Clean obs (2021+) | Geography | Period | Verified | Eligibility |
|---|---|---|---|---|---|---|
| A1 food-price pressure | market | 1,224 | province; region | 2021-Q1 – 2026-Q3 | 0% | provisional |
| A2 headline inflation above usual | market | 134 | province; region | 2021-Q1 – 2026-Q3 | 0% | provisional |
| A3 rice wholesale change | market | 913 | province | 2021-Q1 – 2026-Q3 | 0% | provisional |
| V1 poverty and density | other input | 20 | province (annual) | 2021 – 2023 | 75% | annual profile only |
| C1 El Niño advisory | climate | 46 | national | 2021-Q1 – 2026-Q3 | 50% | provisional |
| C2 typhoons within 300 km | climate | 239 | province; national | 2021-Q1 – 2026-Q2 | 100% | strict and provisional |
| C3 palay/corn drop | climate | 618 | province | 2021-Q1 – 2026-Q3 | 0% | provisional |
| C4 fisheries drop | fish | 588 | province | 2021-Q1 – 2026-Q2 | 0% | provisional |
| E1 unemployment change | employment | 42 | national | 2021-Q1 – 2026-Q3 | 0% | provisional |
| E2 remittance decline | OFW | 40 | national | 2021-Q1 – 2026-Q2 | 10% | provisional |
| N1 FSSI-v3 | other input | 227 | province; national | 2021-Q1 – 2026-Q3 | 100% | strict and provisional |
| H1 regional hunger | target component | 23 rounds-quarters | Balance Luzon | 2021-Q2 – 2026-Q3 | 100% | strict and provisional |
| Unassigned (domain support) | — | 960 | province (incl. centroid points) | 2021-Q1 – 2026-Q2 | 0% | provisional |

**Unassigned support data:** rainfall, temperature, vegetables, chicken and livestock. They match no FIRI definition, so they were not forced into one.

**FAO dimensions** are given as a secondary label only (`E119_FAO_DIMENSION_MAPPING.csv`).

**Domain coverage** (`E119_DOMAIN_COVERAGE_REPORT.csv`). Market, fish and climate have genuine provincial data. Employment and OFW remittances are national only, plus the owner's annual provincial employment file.

## 4. Point-in-time and leakage

- **Point-in-time rows.** `E119_POINT_IN_TIME_VALIDATION.csv` records the observation period, availability date, issue date, target quarter, lead and status for every value used.
- **Leakage checks.** All 9 pass (`E119_LEAKAGE_TEST_REPORT.md`).
- **Date restriction.** Computed YoY starts in 2022, because a 2021+ base is required. PSA-published 2021 CPI YoY is kept as a declared exception.

## 5. Deliverables

| File | Content |
|---|---|
| E119_PREPROCESSING_PROTOCOL.md | Frozen rules |
| E119_DATA_CLEANING_REPORT.md | Cleaning, 34 outliers kept, redundancy |
| E119_TEMPORAL_ALIGNMENT_REPORT.csv | Per feature: aggregation, rule, lag at issue, verified share |
| E119_GEOGRAPHIC_ALIGNMENT_REPORT.csv | Per feature: resolution, units, no copying across provinces |
| E119_MISSING_DATA_REPORT.csv | Count, %, reason, usability per feature |
| E119_FEATURE_ENGINEERING_DICTIONARY.csv | Definition, formula, source, availability rule |
| E119_POINT_IN_TIME_VALIDATION.csv | One row per value used |
| E119_LEAKAGE_TEST_REPORT.md | 9 checks, all pass |
| E119_REGIONAL_MODELING_DATASET.csv | Dataset A |
| E119_PROVINCIAL_VULNERABILITY_DATASET.csv | Dataset B (+ `E119_PROVINCIAL_ANNUAL_INDICATORS.csv`) |
| E119_12_INDICATOR_DATA_MAPPING.csv | Every dataset → indicator, direct or supporting, with redundancy notes |
| E119_INDICATOR_PREPROCESSING_REPORT.csv | One row per indicator |
| E119_INDICATOR_COVERAGE_REPORT.csv | Per indicator × dataset × feature coverage |
| E119_DOMAIN_COVERAGE_REPORT.csv | Five domains + other inputs |
| E119_FAO_DIMENSION_MAPPING.csv | Secondary FAO labels |
| E119_UNIFIED_12_INDICATOR_DATASET.csv | Long format: 3,013 values; national and regional values once, under their own unit |

## 6. What this does not solve

- **Neither dataset is large enough to expect a reliable Lead-2 model.** E119 cleans data; it adds no new signal.
- **A strict view needs archived PSA release calendars** for prices, production and LFS.
- **Provincial food-insecurity validation** still depends on CBMS 2024 or FNRI requests (E118). These need the owner's signature.

## 7. Reproducibility note

One input, `experiments/E114_Final_Run/data/cov_gdelt_doc.csv` (the GDELT shares), is in the working folder but **not tracked by git**. It was already untracked before E119. Its SHA-256 is logged in `out/manifest.json`. On a fresh clone, the 4 GDELT features cannot be rebuilt until the file is committed or fetched again.
