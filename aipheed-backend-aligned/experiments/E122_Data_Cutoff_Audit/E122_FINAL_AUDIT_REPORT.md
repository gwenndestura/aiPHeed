# E122 final audit report: FIRI3 2021–2026 cutoff and point-in-time

**Scope.** Every dataset, feature, indicator and score of FIRI3.

**Method.** The audit is proven from the records, not the protocol:
1. 38 source files were read directly.
2. 18 change-type series were re-derived independently from their raw levels using only 2021+ data.
3. FIRI3 was rerun, and every score was traced back to the observations behind it: current values, percentile references and comparison bases.

**Rerun:** `python runner/audit.py` (stops if any check fails).

## Answers

**1. Does every FIRI3 feature use only data from 2021-01-01 onward?**
- **Yes, after the correction.** For all 34 features, the earliest underlying period (current value, references and comparison base) is 2021-Q1 or later (`E122_FEATURE_CUTOFF_AUDIT.csv`).
- Every computed score's earliest input is ≥ 2021-Q1 (`E122_FINAL_SCORE_TRACEABILITY.csv`).
- No input period is after 2026.

**2. Did any pre-2021 observation enter feature engineering, lagging, rolling calculations or normalization?**
- **Yes, before this audit: one case (V1).** The PSA-published 2021 provincial CPI YoY values compare each 2021 month with the same month of 2020. They were admitted as current values (2021 quarters) and as percentile references for later quarters, through E119's declared exception.
- **Now:** 40 rows are rejected before scoring and normalization (Amendment 1).
- **No other case was found:**
  - all 18 re-derivable change series match the pipeline exactly from 2021+ levels (max |Δ| 5e-8, no extra rows);
  - level series (cyclones, FSSI, GDELT) have no history;
  - annual features use the latest published year only.

**3. Which datasets contain pre-2021 records?** 24 of the 38 audited files (records counted, never used):
- **CPI:** the regional CPI index (1,944 pre-2021 records).
- **E118 tables:** retail poultry, livestock and fish; farmgate cereals; palay/corn production (from 1987); vegetables and root crops; fisheries; NASA POWER (from 1981).
- **Context tables:** bottom-30% CPI, retail cereals, wholesale cereals and fish, aquaculture, retail vegetables and root crops, farmgate livestock.
- **National and other:** cyclones in PAR (from 1996), national LFS (from 2005), GDELT (from 2017), ONI (from 1950).
- **SWS:** from 1998 (the target, not an input).

See `E122_DATASET_CUTOFF_AUDIT.csv`.

**4. When does each feature first become computable?** By first scored origin; the delay comes from the 2021+ base plus 8 earlier references.

| Year | Features |
|---|---|
| 2021 | CEC_cyclones_100km (2021-Q4) |
| 2022 | FMA_food_cpi, FMA_headline_cpi (2022-Q4, after the correction; was 2021-Q4); FMA_chicken, pork, tilapia; CEC_rain_departure, CEC_heat; EHS unemployment and underemployment (provincial annual) |
| 2023 | FMA_rice_wholesale; AFP palay, corn, vegetables, root crops, fisheries; CEC_cyclones_R; FIS_shortage_news_R |
| 2024 | All other regional features: FMA ×3, AFP ×5, CEC rain/heat, EHS unemployment change, remittance decline |
| 2025 | AFP_chicken, AFP_livestock (series start 2023); PSV_poverty (2025-Q3, release rule); FIS_fssi (2025-Q4, ≥ 5 articles) |
| 2026 | none new |

**5. Which features are unavailable because they lack sufficient post-2021 history?**
- **None is permanently unavailable.** Every feature becomes computable once it has a 2021+ base and 8 earlier references.
- **Before that point**, each feature is reported `insufficient_history`, never filled. For example:
  - regional features until 2024;
  - chicken and livestock production until 2025.
- **Other non-scored rows** are `missing`, `stale`, `unavailable_at_issue` or `incomplete_year` (EHS 2025, DI-3).

**6. Which publication dates remain unverified?** (`E122_PUBLICATION_DATE_AUDIT.csv`)
- **Verified and eligible (4):** cyclones within 100 km, cyclones in PAR, FSSI-v3 and the GDELT shortage share. All have dated real-time sources.
- **Provisionally eligible (30):** every other feature, which rests on a documented release rule:
  - CPI: day 10 of m+1, with 32 province-months archived;
  - retail and farmgate: day 15 of m+1;
  - production and wholesale rice: start of q+2;
  - LFS: m+3;
  - NASA POWER: m+2;
  - provincial employment: 30 June Y+1;
  - poverty: the 2025-07-01 V1 rule;
  - remittances: 25% dated reports.
- **No publication date was invented.**
- **Ingestion.** Every input was ingested 2026-10-25..31, after almost every issue date. All historical scores are retrospective reconstructions.

**7. Are all provincial and regional geographic assignments correct?** **Yes** (`E122_GEOGRAPHIC_AUDIT.csv`, 34 of 34 PASS).
- **Provincial features:** only the five provinces, no duplicates, no wrong units.
- **No national or regional copies:** no provincial feature equals its Region IV-A or national series in any period. The cyclone count within 100 km is identical across provinces in 82% of quarters, but these are genuine zero counts from per-centroid tracks.
- **Regional features:**
  - Region IV-A rows as published;
  - the CALABARZON rainfall and heat proxy is the mean of the five province points (approved);
  - national series are labelled PHILIPPINES.

**8. Are all historical FIRI3 scores point-in-time valid?**
- **Yes, on the observation dates.**
  - every contributing value and every percentile reference was available before its issue;
  - none was observed after its origin;
  - none is more than 3 quarters old.
- **Provisional on publication dates** for 30 features (question 6), and computed from the current data vintage (W4).

**9. How many scores remain valid after the strict cutoff?**
- **Provincial:** 75 of 115 (2023-Q1+): 54 on 4 indicators, 13 on 5, 8 on 6.
- **Regional:** 10 of 23 (2024-Q2+).
- **The correction lost no score.** 73 provincial scores changed (mean |Δ| 0.0032, max 0.0125), with no band change.

**10. Did the audit require corrections?** **Yes, two:**
- **V1** (cutoff): Amendment 1;
- **C2** (geography check order): no effect on results.

See `E122_CORRECTIONS_REPORT.md`.

**11. Do all automated tests pass?** **Yes:** 1129 passed, 18 skipped, including 33 new E122 tests.

**12. Is FIRI3 ready for prospective validation?**
- **The mechanism is ready**, for the cutoff and point-in-time requirements.
- **First prospective origin:** 2026-Q4 (issue 2027-01-01), after the inputs are refreshed with that quarter's releases.
- **Open design issues:** DI-1 to DI-7 from E121 remain open, and publication dates remain mostly rule-based.

## Integrity

- **Unchanged:** FIRI v2 (`firi.py` and its data, by SHA-256), production, the dashboard, and the E118–E121 outputs.
- **Amended FIRI3 results** are in `out/` and in write-once `snapshots/` (23 retrospective).
- **No model was trained, and SWS was not used.** SWS appears only in the dataset audit, as the target.
