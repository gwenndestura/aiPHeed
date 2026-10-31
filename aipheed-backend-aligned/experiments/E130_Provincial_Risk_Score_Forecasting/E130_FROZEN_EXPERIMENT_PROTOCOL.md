# E130 frozen experiment protocol

This protocol was frozen **before** E130 searched for any new provincial data, scored any forecast, or fitted any model. Its SHA-256 is in `runner/PROTOCOL_SHA256.txt`.

## 0. Scope and starting state

**Offline research only.** E130 does not change any of the following:
- the served model, the forecast endpoints or the dashboard;
- FIRI v2, or the frozen FIRI3 v1.3 method;
- any historical experiment record.

Nothing is pushed, merged or deployed.

**Starting state.** Branch `aiPHeed/corrected-data-pipeline`, commit `99358f0` (E129). Input hashes, library versions and the untracked files from other sessions (left untouched) are in `out/e130_manifest.json`.

**What E130 adds** (none of this repeats an experiment that has already failed):

| # | New element | Why it is not a repeat |
|---|---|---|
| 1 | A numerical provincial reference score (PFDR v1) with a measurement-based tolerance, decided before any evaluation | E128/E129 had no numerical provincial target definition |
| 2 | An operational (dashboard) lead definition and an exact issue-date mapping for the five provinces | Resolves the E128/E79 issue-date mismatch |
| 3 | A sealed survey-year forecast of the next PSA provincial round, frozen before searching for that round | The first blind provincial numerical forecast in the project |
| 4 | A search for provincial food-insecurity data published since E129 | New data is the only thing that can change E129's gate result |
| 5 | A planning simulation that turns "≥ 75 % within tolerance at Lead 2" into data requirements | Answers "what must be obtained" quantitatively |
| 6 | An execution-ready quarterly provincial protocol (sections 5, 8, 9) | It runs unchanged once a valid target exists; nothing is fitted now |

**Not repeated:** E128's regional five-model run. Its 20 quarters, target and models are unchanged, and E128 recorded that re-running variants on them adds forking paths, not evidence.

## 1. Target gate (before any training)

A candidate target must pass **all** of the following:

| # | Criterion |
|---|---|
| G1 | Measures household food insecurity or food deprivation, not prices and not an index built from the predictors |
| G2 | Observed separately for each of the five provinces |
| G3 | Repeated at least 10 times within 2021–2026 (R1 needs 10 target quarters) |
| G4 | Dated publication, so it can be used point-in-time |
| G5 | Held, or obtainable under current authority |
| G6 | Not constructed from the predictors |
| G7 | Numerical, with documented sampling uncertainty |
| G8 | Supports quarterly evaluation at operational Lead 2 (needs G2, G3 and quarterly frequency) |

**Decision rule:**
- Quarterly provincial training is authorized only if at least one candidate passes G1–G8.
- A candidate that passes G1, G2 and G4–G7 but fails G3/G8 is a **survey-year reference**. It may be used for validation and for the survey-year seal (section 7), never as a quarterly label.

**Result at freeze.** This depends only on the data inventory, not on any outcome. It is in `out/gate.json` and `out/gate_candidates.csv`:
- **No candidate passes. Quarterly provincial model training is BLOCKED.**
- PSA subsistence incidence (C1) passes G1, G2 and G4–G7. It fails G3 (2 rounds) and G8.

**Re-check after the search.** The gate is re-run once after the new-data search (section 6). Any newly found source is added as a candidate under the same criteria.

## 2. Reference score: PFDR v1 (Provincial Food-Deprivation Reference)

| Item | Definition |
|---|---|
| Measure | PSA subsistence incidence among the population: the share whose per-capita income is below the provincial food threshold (the cost of a basket meeting minimum food needs) |
| Owner role | Provincial food-deprivation reference (owner, 2026-10-31; E129 Addendum 1) |
| Scale and direction | % of population, 0–100; higher means more food deprivation. Kept on its own scale with no rescaling, because a 0–1 rescaling would need anchors the data do not give. |
| Geography | Province, as published by PSA (Quezon excludes Lucena City) |
| Frequency | FIES survey years: 2021 and 2023 held. The next round is expected for survey year 2025 or later. |
| Independent observations | 10 (5 provinces × 2 rounds); 5 changes |
| Uncertainty | SE = value × published CV. A 90 % sampling interval is kept with every value (`E130_REFERENCE_SCORE_DATA.csv`). |
| Vintage | Both rounds as published 2024-08-15. The original 2021 release is not held. |

**Overlap with the predictors.** The food threshold is priced at provincial food prices, so the food CPI partly enters the reference mechanically. This is controlled in two ways:
- the PSA-only arm, which contains CPI, must be beaten before any model can claim to learn more than price indexation;
- CPI is never the target.

**What PFDR v1 is not:**
- **Not a composite.** FNRI FIES (2 provinces, 1 round) is a construct cross-check only. Averaging percentages from different constructs, frequencies and units (households vs population) has no defensible basis.
- **Not linked to SWS.** SWS Balance Luzon hunger stays a separate regional reference and is never copied into provincial rows.
- **Not FIRI.** FIRI v2, FIRI3 and the food CPI are not targets.

**Categories.** No officially approved thresholds exist for PFDR. Secondary classification is therefore **not valid** until the owner approves thresholds. A proposal is recorded for the owner, but is **not applied**: three bands, defined as significantly below, within, or above the regional value at the 90 % level.

## 3. Operational lead, issue dates and information horizon

| Notion | Definition |
|---|---|
| Dashboard quarter | The calendar quarter in which the dashboard is viewed (`backend/app/quarterly/target.py`, Asia/Manila) |
| Issue date | 00:00 PHT on the first day of the dashboard quarter (the served rule) |
| **Operational Lead k** | Target = latest complete calendar quarter + k. **Lead 1 = the dashboard quarter itself** (under way, incomplete). **Lead 2 = the next quarter** (the dashboard's forecast target), the minimum operational horizon. |
| Internal model lead | E128 and E130 use the same origin and lead definitions, so the internal lead equals the operational lead |
| Information horizon | Target quarter minus the newest *published* observation of a given source at the issue date. It differs by source and is recorded per row. |
| Release-anchored issue (sensitivity only) | The day after the SWS release of the latest complete quarter (E80 ANC). Under it, the SWS information horizon is k instead of k + 1. |

**Reconciliation.** E128's "Lead 1 ≈ SWS horizon 2" is an *information* horizon at the quarter-start issue, not a different operational lead. E128 Lead k and dashboard Lead k name the same target quarter. The exact mapping is `E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv`. It reproduces the E128 target quarters and SWS horizons on all 92 E128 rows.

## 4. Numerical agreement tolerance (fixed before any evaluation)

**Tolerance.** For a reference value with sampling SE `s`, tol = 1.645 × s, the reference's own two-sided 90 % sampling half-width.

**Why.** A prediction inside it cannot be told apart from the reference by the reference's own precision. An oracle that knows the true value lands inside it 90 % of the time.

**Consequence (analytic).** At least 75 % within tolerance requires a forecast error (against the true value) with SD ≤ 1.022 × s. In words, the forecast must be about as precise as the measurement itself.

**Reporting.** Pass/fail uses only this tolerance. 0.5 × tol and 2 × tol are reported as information only.

## 5. Models

These are fitted only when a valid target exists. **None is fitted now.**

| Arm | Model | Features |
|---|---|---|
| M1 | LightGBM regression (L2 loss), the proposed model | All five groups (point-in-time) plus own-province lagged reference |
| M2 | Persistence | Each province's own latest reference value published before the issue date |
| M3 | PSA-only | Ridge on official statistics: CPI, prices, production, LFS, poverty/vulnerability, lagged reference |
| M4 | NLP-only | Ridge on FSSI v3, article volume, GDELT shares, lagged reference |
| M5 | Linear (ridge on all features) | The continuous counterpart of logistic regression. Logistic regression is used only for the secondary classification. |
| Reference | Climatology | Province training mean (the no-skill reference for N4) |

**LightGBM grid.**
- num_leaves {3, 7}, max_depth {2, 3}, learning_rate {0.03, 0.1}, n_estimators {50, 150}, min_child_samples {5, 10}, reg_lambda {1, 10}; feature_fraction 0.8.
- Inner selection by expanding-window CV inside the training rows only.
- Seeds 130–134 for sensitivity.

**No full-sample preprocessing.**
- LightGBM handles NaN.
- Ridge uses training-only median imputation and scaling.
- As-of transforms come from the E119 point-in-time panel.

**Ablation:** all groups, then each of the five groups removed.

**SHAP:** TreeExplainer on the outer-fold models, global, by province and by group.

## 6. New-data search (only after this freeze)

**Targets of the search:**
1. PSA FIES-based provincial subsistence or poverty for a survey year after 2023.
2. FNRI 2022 ENNS provincial FIES for Laguna, Quezon and Rizal.
3. CBMS 2024 provincial or LGU FIES tables.
4. NNC OPT Plus provincial 2021–2025.

**Rules:**
- Queries name explicit years ≤ 2025. No "latest", "current" or "release" queries for PSA, BSP or SWS series. sws.org.ph is not visited.
- Every query and URL is logged in `sources/SOURCES_LOG.md` as it is made.
- Any exposure is logged in `CONTAMINATION_LOG.md`.
- If a post-2023 PSA provincial subsistence round is found:
  - acquire only 2021+ rows;
  - hash the file before reading any values;
  - score the survey-year seal (section 7).

## 7. Survey-year seal

**File:** `sealed/E130_SURVEY_YEAR_SEAL.csv`, SHA-256 `94a08cd1d4b4497effbf95340f091eca46d2cc087d562a37ed134eb1b38593ed`, written by `runner/seal_e130.py`. The seal's target is the next PSA provincial subsistence round after 2023.

**Forecasters:**
- S1 persistence (the 2023 value);
- S2 two-round mean;
- S3 empirical-Bayes shrinkage of 2023 toward the cross-province mean.

90 % prediction intervals come from the 2021→2023 true-change variance plus sampling error. LightGBM, PSA-only, NLP-only and linear models are not fitted: there are 5 training rows, below the minimum of 20.

**Scoring.**
- MAE, RMSE and share within tolerance (tolerance = 1.645 × the new round's SE);
- PI90 coverage;
- direction for changes beyond 90 % sampling error;
- Spearman agreement.

Five provinces and one fold make this **descriptive only**. It cannot establish reliability or Lead 2.

## 8. Reliability rules

These are frozen and apply at every lead.

**Numerical task (primary).**

| # | Rule |
|---|---|
| N1 | At least 10 target quarters and 40 rows of distinct provincial observations (copies count once) |
| N2 | At least 75 % of out-of-sample predictions within tolerance (section 4) |
| N3 | MAE **and** RMSE lower than every applicable baseline (M2–M5), on identical rows |
| N4 | Squared error below persistence **and** below climatology, each with a one-sided paired cluster bootstrap p < 0.10 (clusters = target quarters) |
| N5 | Share within tolerance ≥ 0.60 in each third of the target quarters, and leave-one-quarter-out minimum ≥ 0.70 |
| N6 | No province with MAE skill below 0 against its own persistence |
| N7 | 80 % prediction-interval coverage between 0.70 and 0.90 |

**Classification task (secondary).** The frozen R1–R7 (`FINAL_THESIS_OBJECTIVES/FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7) apply, and only if the owner has approved category thresholds.

**Lead k is reliable** when N1–N7 pass, plus R1–R7 where classification is valid.

**Maximum reliable lead.** The furthest consecutive lead from Lead 1 that is reliable. An unreliable intermediate lead ends the run.

**Lead 2 operational success** requires all of:
- Lead 2 is reliable, as above;
- N3 against all four baselines;
- no leakage finding;
- overfitting gap and seed sensitivity reported, with no audit failure;
- at least 10 unseen target quarters.

A single fold never suffices.

**Verdicts:**
- Lead 2 status is one of **confirmed / provisional / inconclusive / failed**.
- The experiment outcome is one of **SUCCESS / PARTIAL SUCCESS / BLOCKED / INCONCLUSIVE**, as defined in the E130 brief, Part 19.

## 9. Walk-forward design (quarterly; for a valid target)

- **Origins:** t = 2021-Q1 … 2026-Q3.
- **Issue date:** first day of t + 1 (dashboard rule).
- **Leads:** Lead k targets t + k.
- **Training rows:** province × target-quarter rows whose reference was published strictly before the issue date. All provinces are cut at the same date.
- **Minimum:** 8 training target quarters.
- **Uncertainty:** cluster bootstrap by target quarter.
- **Persistence:** per province.
- **Province-held-out** runs are a supplement only. No random splits.

`E130_WALK_FORWARD_SPLITS.csv` lists every origin and lead, and states whether each is executable.

## 10. Diagnostics run now (Part 13 of the brief)

These need no target fit:

| # | Diagnostic |
|---|---|
| D1 | Gate |
| D2 | Change z-tests and heterogeneity (Cochran's Q) |
| D3 | Independent observations vs N1 |
| D4 | CPI variance decomposition and province-deviation autocorrelation |
| D5 | Provincial food inflation vs PFDR change, plus the regional SWS pattern (descriptive, N = 5) |
| D6 | Age of employment and poverty data at issue |
| D7 | Climate availability and provincial identity of typhoon counts |
| D8 | Geographic detail of remittances |
| D9 | News coverage by province |
| D10 | Period-marker share (quarter effect) of each predictor |
| D11 | Reference noise (CV, signal-to-noise) |
| D12 | Meaningful province differences |
| D13 | Lead-2 support |
| D14 | R1–R7 / N1–N7 attainability |
| D15 | Capacity: features vs observations |

## 11. Planning simulation (synthetic; labelled as such)

**Grid:**
- quarters {10, 20, 40}
- noise ratio r = SE / SD(true) ∈ {0.25, 0.5, 1, 2}
- persistence ρ ∈ {0.6, 0.9}
- predictable share of the true change R² ∈ {0, 0.25, 0.5, 0.75}
- information horizon h ∈ {2, 3}
- common share 0.74 (the CPI value)

**Settings:** 300 simulations and 400 bootstrap resamples per cell; seed 130 (`e130_lib.simulate_panel`).

**Output:** the probability of passing N2 and N4 for an idealized informed model, and N2 for persistence.

**It is never presented as model performance.**

## 12. Integrity

- Study window 2021+ (asserted on load).
- No SWS values copied to provinces.
- CPI, FIRI v2 and FIRI3 are never targets.
- No duplicated observations.
- Thresholds and tolerance fixed here.
- No result-driven changes. Any deviation goes to `DEVIATIONS.md` with its reason.
- Protected-exposure rules (no "latest" queries; log any exposure).
- Local commits only.
