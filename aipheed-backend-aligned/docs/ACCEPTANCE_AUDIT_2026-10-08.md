# Acceptance Audit: Does the Timing-Valid 76.4% Pass?

Prepared 2026-10-08. Source: *THESIS 2 (9).pdf* (1 October 2026), Chapters I and
III; line numbers refer to the extracted text. Production (MODEL-A), Chapter III
and the repository are unchanged. No new model was fitted for this audit; all
figures come from the preserved runs in `evidence/2026-10-08_model_b/` and
`data/supplementary/`.

---

## A. The exact 75% requirement

| Where | Wording |
|---|---|
| Algorithm 3 (lines 1399-1405) | "A default LightGBM classifier will be fitted and evaluated per fold ... If **mean fold accuracy** meets the 75% threshold, k will be recorded and the search will advance. When accuracy first drops below 75%, the search will halt and return the last passing k as the Maximum Reliable Lead Time." |
| Algorithm 3 architecture (1412-1413) | "Compute **mean fold accuracy across all folds** and compare against the 75 percent threshold." |
| Section 3.4.4 (1859-1861) | "The 75% mean accuracy threshold used in Algorithm 3 to discover the Maximum Reliable Lead Time, and the F1 >= 0.75 and AUC-ROC >= 0.80 targets used in Algorithm 4 to accept the final tuned model" |
| Section 3.4.4 (1888) | "requiring the model to be right three times out of four before a lead time is trusted operationally" |
| Section 3.4.4 (closing) | "Any lead time or model configuration that does not clear these thresholds will not be published to the dashboard" |
| Algorithm 4 (1443, 1475) | best parameters "evaluated once on the last four holdout quarters ... targeting F1 >= 0.75 and AUC-ROC >= 0.80" |
| Rule 2 (1550-1554) | the furthest lead time "at which the model achieves reliable classification performance ... will be adopted as the operational forecast horizon" |
| Objective 2.V (lines ~395-397) | "to empirically determine the furthest horizon at which reliable forecasting is achievable" |
| H2 (lines 323-328) | "aiPHeed will reliably classify ... across multiple forward-looking lead times" |

**Meaning.** The 75% is **A: the mean of fold accuracies across all
walk-forward folds at a given lead time** (Algorithm 3). It is not per year (B),
not every horizon (C: the search stops at the first failing k), and not holdout
accuracy (D). Chapter III adds a separate acceptance rule for the final model
(E): holdout F1 >= 0.75 **and** AUC-ROC >= 0.80 (Algorithm 4), and Section 3.4.4
withholds publication from any configuration that misses its thresholds.

## B. Validity of the 76.4% result

- **Aggregation.** Each fold tests one quarter of five provinces, so all 11
  folds have equal weight; mean fold accuracy and pooled accuracy are both
  0.7636. This is exactly the statistic Algorithm 3 names.
- **Yearly results** are not an acceptance criterion in Chapter III. 2024's
  0.60 (strict timing) is a diagnostic result and should be reported as a
  limitation, not as a failure of the Algorithm 3 criterion.
- **Verdict under Algorithm 3: PASS at k = 1** (0.764 >= 0.75; two quarters
  ahead scored 0.70-0.72 in the timing runs made, so the Maximum Reliable Lead
  Time is 1) - **but only under the 45-feature reading** (Section C). Under Equation 5's twelve features the same procedure
  gives 0.618 and a lead time of 0.
- **Verdict under Algorithm 4 / Section 3.4.4: FAIL.** Timing-valid holdout
  (2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4; 20 rows, 2 LOW): weighted F1 0.80 (met),
  AUC-ROC 0.50 (not met). The model is not degenerate (195 trees, 539 splits);
  it scored the two LOW rows 0.98 and 0.76, above several HIGH rows. Read
  literally, Section 3.4.4 bars this configuration from publication.

## C. 45 versus 12 features

| Evidence | Location | Says | Applies to |
|---|---|---|---|
| "45-column candidate matrix that is reduced to 12 final features through the selection process described in Section 3.3.2.7" | Sec. 3.2, line 1164 | 12 | Final model features |
| "120-row x 45-column matrix" incl. "SWS hunger" | Sec. 3.3.2.6, lines 1281-1283 | 45 | Fused matrix |
| Section 3.3.2.7 | cited at 1164 and 1818 | - | **Absent from the manuscript** |
| Eq. 5: F[FSSI(t), FSSI(t-1), FSSI(t-2), dFSSI(t), trigger(t), CPI_dev(t), unemp(t), rice_change(t)] | Sec. 3.4.2, line 1685 | 12 | Forecast function |
| "Input - 45-feature matrix, 120 rows" | Algorithm 3, line 1418 | 45 | Lead-time discovery |
| "Input - 45-feature matrix with Maximum Reliable Lead Time k" | Algorithm 4, line 1462 | 45 | Tuning and final model |
| "M: total number of features in the fused feature matrix" | Eq. 7 legend, line 1775 | 45 | SHAP |
| "d and M for the 12 features actually used for training and SHAP attribution" | Table 3.4.3.1 notes, 1781-1782 | 12 | Training and SHAP |
| "reduction from 45 candidates to 12 final features (Section 3.3.2.7)" | Table 3.4.3.1, 1817 | 12 | Selection |
| "LightGBM Training ... on the 12-feature, 120-row matrix" | Table 3.4.3.1, 1825 | 12 | Training |
| "fused with government indicators into a 45-column training matrix" | Sec. 3.5, line 1930 | 45 | Training matrix |

**ADVISER DECISION REQUIRED.** The manuscript states both, sometimes for the
same component (SHAP's M is 45 in the Eq. 7 legend and 12 in Table 3.4.3.1;
training is a 45-column matrix in Section 3.5 and a 12-feature matrix in Table
3.4.3.1). The section that would reconcile them is missing. The text does not
resolve it, and the higher accuracy of one reading is not a reason to choose it.

## D. Forecast timing

Rule 3: "All features will derive exclusively from data **available before the
forecast period**." Equation 5 forecasts quarter t+h from the vector "at quarter
t", and Equation 7 calls the output "the predicted food insecurity risk
probability at quarter t+1". The forecast period is therefore quarter t+1, and a
feature must be available before t+1 begins. **Chapter III supports the strict
reading (T2).** Delayed issuance (T1) is not described anywhere. Both give
0.764 overall here; under T2 the years are 0.80 / 0.85 / 0.60 / 0.90.

## E. Leakage audit (strict reading, T2)

Forecast for quarter t+1 is made before t+1 starts.

| Feature family | Source | Reference period used | Typical release | Available before t+1? |
|---|---|---|---|---|
| FSSI, FSSI lags/accel | News corpus (RSS, Google News, GDELT), scored by the system | t, t-1, t-2 | Continuous (articles dated within the quarter) | Yes |
| Five trigger proportions | Same corpus, Algorithm 2 | t | Continuous | Yes |
| Food CPI level, YoY, lag, accel; CPI_dev; food-minus-headline gap; headline CPI | PSA OpenStat 2018-based CPI, monthly | t-1 (and earlier) | Early the following month | Yes (one quarter of margin) |
| Rice price level, lag, accel | PSA OpenStat retail/wholesale RMR, monthly | t-1 | Within weeks of the month | Yes |
| Commodity prices (5) | PSA NRP to 2021; extrapolated from food CPI afterwards | t-1 | As CPI | Yes (note: post-2021 values are derived, not observed) |
| Unemployment rate, lag, accel | PSA Labor Force Survey (national) | t-1 | About six weeks after the reference month | Yes |
| OFW remittance YoY, lag, accel | BSP (hand-curated) | t-1 | About six to seven weeks | Yes |
| USD/PHP | ECB reference rate via Frankfurter | t-1 | Daily | Yes |
| Diesel, gasoline, lags/accel | DOE weekly Oil Monitor (hand-curated) | t-1 | Weekly | Yes |
| Brent | US EIA via FRED | t-1 | Daily | Yes |
| ENSO (ONI) | NOAA CPC | t-1 | Early the following month | Yes |
| Typhoon count, severe flag, drought alert | PAGASA | t-1 | Real time | Yes |
| Rainfall anomaly, lag, accel | Measured provincial rainfall | t-1 | Within the month | Yes |
| SWS hunger | SWS releases (dates from the article timestamps) | Latest round released before t+1 starts | 2-12 weeks after fieldwork | Yes (per-quarter dates in `timing_audit.csv`) |
| Poverty incidence | PSA Full Year Official Poverty Statistics | Latest survey released before t+1 | 2021 survey: 15 Aug 2022; 2023 survey: Aug 2024 | Yes (2018 survey to 2022-Q3, 2021 to 2024-Q3, 2023 after) |
| Label (Eq. 3) | SWS + PSA CPI | t+1 | - | Target only, never a feature |

The T2 configuration has no feature that was unavailable at prediction time.
Release lags other than SWS and poverty are typical publication practice and
should be confirmed against the agencies' release calendars before final
submission; with one full quarter of margin, none is close to the boundary.
Remaining data-quality notes (not leakage): unemployment is national; DOE and
BSP series are hand-curated; commodity prices after 2021 are derived from CPI.

## F. Persistence

H3 (lines ~331-339): "The LightGBM model that combines news signals and
government data **will outperform all six comparison models, naive
persistence**, ..." Beating persistence is therefore a hypothesis, not the 75%
acceptance criterion and not a condition of any objective. Correct statement:

> **The model achieves 76.4% mean walk-forward accuracy one quarter ahead but
> does not outperform the persistence baseline (80.0%) on the same folds; H3 is
> not supported.**

## G. Objective-by-objective status

| Objective | Required method | Current result | Meets requirement? | Reason |
|---|---|---|---|---|
| 1. NLP pipeline (FSSI + BERTopic) | Alg. 1-2, Eqs. 1-2, BERTopic | Built; reproducible; 66 topics | Yes | Independent of model accuracy |
| 2a. Five metrics | Alg. 3-4 evaluation | All computed | Yes | Objective requires evaluation, not a value |
| 2b. Furthest reliable horizon | Alg. 3, 75% mean fold | 1 quarter (45-feature); 0 (12-feature) | Yes either way as a determination | Value depends on Section C |
| Accuracy >= 75% (Alg. 3) | Mean fold accuracy | 0.764 (45) / 0.618 (12) | 45: yes; 12: no | Section C |
| Final-model acceptance (Alg. 4, Sec. 3.4.4) | Holdout F1 >= 0.75, AUC >= 0.80 | F1 0.80, AUC 0.50 | No | AUC on a 2-LOW holdout |
| Provincial ranking | Order of province probabilities | Served | Yes | |
| 3. Municipal ranking | Alg. 5 on validated province forecasts | 142 LGUs ranked | Partially | "Validated" depends on Sec. 3.4.4 |
| Explainability | SHAP, Eq. 7 | Served | Yes | |
| Alerts | Rule 7 with review | Implemented | Yes | |
| 4. Baseline comparison | Six baselines, same folds | Done | Yes (H3 not supported) | |
| 5. Dashboard | Public geospatial dashboard | Runs locally; public deployment not current | Partially | Deployment outstanding |
| 5. ISO/IEC 25010 | 25 DA + 25 DEPDev evaluators | Not yet conducted | No (pending) | Needs participants |
| 5. NNS face validity | NNS 2019 and 2023 | Values unverified | No (pending) | Needs DOST-FNRI tables |

## H. Why 2024 is weak (diagnosis only)

Training windows for the 2024 folds are 28-41% HIGH, while the 2024 test
quarters are 60-100% HIGH: regional hunger rose from about 11% to 25% within a
year. Under strict timing the model sees SWS one to two quarters late (each
round is published weeks into the next quarter), so it cannot see the upturn
when it starts. This is forecast timing and a real distribution shift, not an
implementation error; it cannot be corrected without changing Chapter III, and
nothing was tuned on 2024.

## I. Path A - keep the approved methodology

- **75% criterion:** met (0.764 at k = 1) **if** the adviser confirms the
  45-feature reading; not met (0.618) under the 12-feature reading.
- **2024:** reported as a limitation; Chapter III sets no per-year criterion.
- **Final-model acceptance:** not met (AUC 0.50), so Section 3.4.4, read
  literally, bars publication of MODEL-B's forecasts.
- **Objectives achieved:** 1, 2 (as evaluation and determination), 4 (as
  comparison), provincial ranking, SHAP, alerts. Pending: ISO evaluation, NNS
  face validity, public deployment.
- **MODEL-B acceptable?** Its accuracy can be reported as passing Algorithm 3,
  but it cannot be published as the operational model under Section 3.4.4.

## J. Path B - minimum necessary change (not implemented)

**Problem.** Section 3.4.4's AUC >= 0.80 is evaluated on a four-quarter holdout
that, after 2024's rise in hunger, contains only 2 LOW rows of 20. AUC from two
negatives is not a stable measurement: moving one LOW row changes AUC by up to
0.5. The walk-forward evaluation on the same configuration uses 55 rows, 22 of
them LOW, and gives AUC 0.824 and F1 0.765.

**Smallest change (Option B, clarification).** Evaluate Algorithm 4's
acceptance targets on the out-of-sample walk-forward predictions at the
discovered lead time, keeping the four-quarter holdout as an additional
reported check, and state a minimum number of each class required for an AUC
to count. Paired with the adviser's answer to Section C.

| Item | Detail |
|---|---|
| Expected effect | The tuned model's walk-forward F1 and AUC (not yet computed for the tuned model) would decide acceptance; the default-model values are 0.765 and 0.824 |
| Justification | Evaluates the same quantity on a sample in which both classes exist; uses no future data |
| Effect on objectives | Objective 2 unchanged (same five metrics); acceptance becomes measurable |
| Chapter III sections | Algorithm 4 (holdout evaluation), Section 3.4.4 (acceptance), and the Section C sentences |
| Leakage risk | None, if Algorithm 4's search remains nested inside each walk-forward step |
| Reproducibility | Deterministic; scripts preserved |
| Approval | Required |

Other options, ranked: (A) implementation fixes already identified - poverty
publication timing, default LightGBM in Algorithm 3, forward pairing in
Algorithm 4 - needed under any path; (C) SWS timed by release date - already
in Section 3.3.2.6, adds nothing measurable; (D) new predictor or target -
not recommended; (E) pre-2020 history - the only route likely to improve 2024
and skill over persistence, but needs data collection and approval.

## K. Single recommended next step

Put three questions to the adviser, with Sections C, D and J as evidence:
(1) are Algorithms 3 and 4 trained on the 45-feature matrix or on the 12
features; (2) is the strict timing reading of Rule 3 correct; (3) may Section
3.4.4's AUC target be assessed on the walk-forward predictions when the
four-quarter holdout has fewer than a stated number of LOW cases.
