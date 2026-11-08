# FINAL protocol: aiPHeed food-insecurity forecasting with LightGBM

**Branch:** `aiPHeed/final-food-insecurity-lightgbm`, from `1baca5e`. That commit contains the verified E111 state plus E112, E113 and the unscored E114 data work, so all of E107–E114 are preserved.

**Status when frozen:** no model in this protocol has been fitted or scored. Its SHA-256 is written to `runner/PROTOCOL_SHA256.txt` before the first scoring run. Any later change goes in a numbered addendum, and the original text is never edited.

**What has been seen before freezing (disclosure).**
- Every 2021–2026 SWS reading, and the E107–E113 results on those quarters. All 2021+ results here are therefore **development evidence**, not untouched confirmation.
- The ELEVATED label's base rate per area (§2.3). This is a property of the label, not of any model; no model was run.
- No forecasting result on pre-2021 SWS data has ever been computed (E114 collected the data but scored nothing).

## 1. Why this protocol exists (what E107–E113 established and what is new)

**What earlier experiments established**

| Finding (E107–E113) | Consequence for this design |
|---|---|
| The only measured food-insecurity outcome is SWS involuntary hunger: 4 areas, 23 rounds in 2021–2026, ±4–6 point margins. | The outcome stays SWS hunger. Provincial and municipal hunger is not observed, and is not invented. |
| Fixed thresholds (11.3, 15, 20) are one-class after 2023, so accuracy, precision, recall and AUC are degenerate (E109, E112). | A two-class label is defined relative to each area's own recent level (§2.3). |
| LightGBM was fitted to one series (Balance Luzon, about 20 pairs per lead) and lost to persistence (E109–E112). | One pooled LightGBM is fitted on 4 areas × 4 leads (§4.1). |
| News was aligned to calendar quarters, not to the gap between the latest survey and the issue date. Coverage was sparse in 2021–22. | News and price change are measured *since the last survey* (§3.3). Anticipatory and reporting news are separated, and repeated event coverage is removed (§3.4). |
| All 2021+ quarters have been seen. | Pre-2021 SWS history (E114) is used in a separate secondary arm, as the only untouched evaluation (§7). Prospective seals cover the future (§9). |

**Accuracy target.** The 75% target comes from the user's directive and from the original Algorithm 3. Chapter I §1.5.2 itself states no threshold. It is evaluated exactly as defined in §6, and is never redefined after results are seen.

## 2. Outcomes

### 2.1 Primary outcome: SWS involuntary ("Total") hunger

- **What it is:** the percentage of families who experienced involuntary hunger at least once in the past three months.
- **Areas:** NCR, Balance Luzon (BL), Visayas (VIS), Mindanao (MIN).
- **Data:** `data/sws_area_rounds_2021.csv`, the 23 non-commissioned rounds from 2021-Q2 to 2026-Q3. This is the E110 file; every value was checked against SWS. The commissioned March 2025 voter round is excluded.
- **Quarter value:** H(a,q) is the mean of the rounds of quarter q.
- **Vintage rule:** at issue date O, the known value of a quarter is the mean of its rounds published before O.

### 2.2 Geography

- BL contains CALABARZON, so BL is the geography relevant to DA Region IV-A.
- The other three areas are pooled for training and used to test generalization.
- No SWS value is treated as a provincial or municipal hunger rate.

### 2.3 Classification label: ELEVATED hunger

**Definition.** ELEVATED(a,q) = 1 if H(a,q) > REF(a,q), else 0.
- REF(a,q) is the mean of the final H(a,x) over the quarters x in q−4 … q−1 that have a reading.
- At least two such quarters are required; otherwise the label is undefined.

**Meaning.** "Hunger in this area is above its average of the previous year." It is a deterioration-type risk label, the framing used by anomaly-based early-warning systems.

**Not an official classification.** It is researcher-defined: neither SWS nor PSA uses it.

**Why this definition**
1. Chapter I Objective 2 requires accuracy, precision, recall, F1 and AUC, so a two-class outcome is needed.
2. Fixed hunger thresholds are degenerate in 2021–2026 (§1).
3. A label relative to each area's own recent level stays two-class across the 2024 level shift, and uses no pre-2021 data.

**Base rates (2021+):** NCR 0.50, BL 0.67, VIS 0.56, MIN 0.56.

**Issue-time reference.** REF̂(a,q | O) is the mean over the same quarters x ∈ q−4 … q−1:
- quarters already known at O use their vintage values;
- quarters after the newest known quarter are filled with the newest known value (persistence fill);
- quarters before the newest known quarter that have no reading are skipped.

REF̂ is a feature and a decision boundary. It is never the label.

## 3. Time rules and features

### 3.1 Issue dates and leads

- **Quarter index:** qi = year·4 + quarter − 1.
- **Issue date:** origin quarter t is issued at O(t) = 00:00 on the first day of quarter t+1.
- **Lead:** at Lead k the target quarter is t+k. At Lead 1, the target quarter begins on the issue date; its SWS fieldwork usually falls in its last month.

**Recorded for every prediction**
- the issue date;
- the newest SWS quarter known, with its fieldwork end and publication date;
- the newest PSA CPI month used;
- the newest news publication date used;
- the target quarter;
- the actual lead in days (issue date to the end of the target quarter);
- the true horizon (target quarter minus the newest known SWS quarter);
- the age of the newest SWS reading (issue date minus its fieldwork end, in days).

### 3.2 The 12 indicator families

The 12 families are the FIRI v2 indicators (`backend/app/ml/inference/firi.py` LABELS), built by E107 `feature_table(k)` with its verified issue-date cut-offs. For the region, each feature is the mean over the five provinces.

| Code | Family | Columns |
|---|---|---|
| A1 | Food-price-pressure forecast (PSA CPI) | `A1_food`, `A1_gap` |
| A2 | Headline inflation above usual (PSA CPI) | `A2` |
| A3 | Wholesale rice price change (PSA) | `A3` |
| V1 | Poverty and population density (PSA) | `V1` |
| C1 | PAGASA El Niño alert in force | `C1` |
| C2 | Typhoons within 300 km (IBTrACS) | `C2` |
| C3 | Palay/corn production drop (PSA) | `C3` |
| C4 | Fisheries production drop (PSA) | `C4` |
| E1 | Unemployment change (PSA LFS) | `E1` |
| E2 | Remittance decline (BSP) | `E2` |
| N1 | Food Stress Sentiment Index (FSSI-v3, XLM-R) | `N1` |
| H1 | Regional hunger outlook (SWS) | `H1` |

**Columns added inside existing families.** Each uses only data published before O(t).

| Family | Column | Definition |
|---|---|---|
| H | `h_last` | Newest known H(a) |
| H | `h_anom` | h_last − REF̂ of the target quarter |
| H | `h_chg` | h_last minus the previous known quarter's value |
| H | `h_age_q` | True horizon |
| H | `area` | Categorical |
| — | `lead` | k |
| A | `A_since` | CALABARZON food CPI YoY (mean of the five provinces) in the newest month published at O(t), minus the same in the month containing the newest SWS round's fieldwork end; NaN if either is unavailable |
| N | `NC_gap_<cat>` (6), `NC_ant` | §3.3–3.4 |

**Shared context.** The 12-family values are CALABARZON indicators. They are given unchanged to all four areas' rows as shared context; the main families (CPI, El Niño, unemployment, remittances, national news) move together nationally. BL is the area where they are geographically exact. Sensitivity FIL-BL (§5) trains on BL rows only.

### 3.3 Gap-aligned news (new)

**Corpus.** The project RSS headline corpus of CALABARZON news (E31 + E60 stores; `app.news.pipeline_v3.corpus`), with PH publication times. Syndicated copies are removed by `pipeline_v3.dedupe`.

**Event de-duplication.** Within one category, a headline whose word set has Jaccard similarity ≥ 0.5 with an earlier headline published in the previous 7 days is treated as repeated coverage of the same event and dropped.

**Categories.** The six E112 title-lexicon categories, unchanged: price, shortage, disaster, agri_supply, jobs_income, assistance.

**Windows**
- W(t) = [the fieldwork end of the newest SWS round known at O(t), plus 1 day; O(t)): the news published since the latest survey.
- W'(t) = the same window shifted back 365 days.

**Features**
- NC_gap_<cat> = (share of W's de-duplicated headlines in the category) − (the same share in W').
- The year-earlier subtraction removes seasonality and corpus growth.
- NaN if either window has fewer than 30 headlines.

### 3.4 Anticipatory and reporting news (new)

**Rule.** A food-event headline (any category) is *anticipatory* if its title matches the forward-looking lexicon in `runner/news_features.py` (ANTICIPATORY). Otherwise it is *reporting*.

**Feature.** NC_ant = the anticipatory share of food-event headlines in W, minus the same share in W'.

**Purpose.** This separates "a problem is expected" from "a problem has happened" (§8.4).

**Replication sources (used in §8 only, not as model inputs)**
- GDELT GKG CALABARZON documents (`backend/data/gdelt_e85`; GDELT processing timestamps prove real-time availability): theme categories, plus the lexicon applied to URL slugs.
- The GDELT DOC national volume series (E114).

## 4. Model

### 4.1 The primary model: FIL (Food-Insecurity LightGBM)

**Structure:** one LightGBM regressor, refitted at every origin on the pooled panel of 4 areas × leads 1–4.
- **Target:** z = H(a,t+k) − REF̂(a,t+k | O(t)).
- **Level forecast:** Ĥ = REF̂ + ẑ.
- **Class:** ELEVATED if ẑ > 0.
- **Probability:** P = Φ(ẑ / σ̂). σ̂ is the RMSE of FIL's own earlier lead-k errors in z whose targets were published before O(t) (at least 6 errors); otherwise the SD of the training z.

**Training rows at origin t:** every (a, t′, k′) with t′ ≥ 2021-Q1 whose target t′+k′ was published before O(t) and whose features are computable at O(t′).

**Features:** all columns of §3.2–3.4. LightGBM handles missing values natively.

**Fixed settings:** learning_rate 0.03, min_child_samples 10, reg_lambda 5, feature_fraction 0.8, bagging off, deterministic, seed 2026, `area` categorical.

**Tuning grid (4 configurations):** {num_leaves 3, 7} × {n_estimators 100, 300}. The grid is tuned inside the training data only:
- the validation quarters are the 4 latest distinct target quarters in the training rows;
- for each validation quarter v, the model is fitted on rows with target ≤ v−2 (at least 25 rows) and scored on rows with target v;
- the configuration with the lowest MAE of z wins; ties go to fewer leaves, then fewer trees.

**Issuing rule:** FIL is issued only if training has at least 40 rows, at least 6 distinct target quarters, and at least 10 rows of each class.

### 4.2 Baselines (Objective 4 and simple alternatives)

All baselines are scored on exactly the rows where FIL is issued.

| ID | Baseline | Definition |
|---|---|---|
| PERSIST | Naive persistence | Ĥ = h_last; z = h_last − REF̂ |
| MA2 | Moving average | Ĥ = mean of the two newest known quarters |
| MAJ | Climatology | P = training base rate of ELEVATED; class = P > 0.5 |
| ALWAYS | Always ELEVATED | Always predicts ELEVATED |
| LOGIT | Logistic regression | L2, C = 1, on FIL's columns. Median imputation and standardisation are fitted on the training rows; `area` is one-hot encoded. |
| PSA-ONLY | PSA-only logistic | Logistic regression on PSA-derived columns only: A1_food, A1_gap, A2, A3, C3, C4, E1, A_since |
| NLP-ONLY | NLP-only logistic | Logistic regression on news columns only: N1, NC_gap_*, NC_ant |

For PERSIST and MA2, P = Φ(ẑ/σ̂), with σ̂ computed by FIL's rule. A logistic baseline falls back to MAJ when training has fewer than 5 rows of either class.

## 5. Candidates, ablations and sensitivities

**Verdict model.** FIL is the only model whose result decides the 75% target and the reliable lead. Every other entry is a pre-registered comparison, run with FIL's exact pipeline.

| Pre-registered model | Purpose |
|---|---|
| FIL-NONEWS | FIL without the news columns (N1, NC_*) |
| FIL-H | Hunger-history columns only (h_*, area, lead) |
| FIL-HN | Hunger history + news columns |
| FIL-drop-<family> | 12 runs, each dropping one family's columns (for H1 only the `H1` column); contribution test |
| FIL-BL | Trained on BL rows only (geography sensitivity) |
| FIL-LONG | §7 (secondary arm) |

**Stage 2 (pre-registered here, used only if FIL fails a criterion).**
- FIL-H, FIL-BL and FIL-LONG are evaluated as diagnostic alternatives.
- A Stage-2 model that passes on 2021+ data is reported as **exploratory**. It can be called confirmed only if it also passes on untouched data: the §7 pre-2021 evaluation (only FIL-LONG can be scored there), or prospective scoring.

## 6. Metrics, the 75% target and the reliability rule

**Classification metrics (per lead)**
- accuracy, balanced accuracy, precision, recall, F1;
- AUC (from ẑ, or P for the logistic models);
- Brier score;
- confusion matrix and base rate.

**Continuous metrics:** MAE, RMSE and bias of Ĥ, in percentage points. A point error is never converted into "% accuracy".

**Scoring set:** every (area, origin, lead) row with a defined label at which FIL is issued.
- **Primary:** the 4-area panel.
- **Also reported:** BL alone.

**Reliability rule at Lead k (all criteria must pass)**

| # | Criterion |
|---|---|
| R1 | At least 10 distinct target quarters and at least 30 rows |
| R2 | **Accuracy ≥ 0.75** (the target) |
| R3 | Balanced accuracy ≥ 0.70, and greater than the balanced accuracy of PERSIST, MA2, MAJ, LOGIT, PSA-ONLY and NLP-ONLY |
| R4 | Brier(FIL) < Brier(PERSIST) and < Brier(MAJ), each with a one-sided paired cluster-bootstrap p < 0.10 (target quarters resampled, 2,000 draws, seed 2026) |
| R5 | Precision ≥ 0.60 and recall ≥ 0.60 for ELEVATED |
| R6 | Accuracy ≥ 0.60 in each chronological third of the evaluated target quarters |
| R7 | BL accuracy ≥ 0.70 |
| R8 | MAE(FIL) ≤ MAE(PERSIST) |

**Maximum reliable lead:** the largest K such that Leads 1 … K all pass. If Lead 1 fails, no lead is reliable.

**Status of a pass**
- A pass on 2021+ data is **reliable on development evidence, confirmation pending**.
- A lead is **confirmed** only if it also passes on untouched data (§7, or the seals in §9).

## 7. Secondary arm: long history (flagged for adviser approval)

**Rule status.** The study-window rule keeps the primary at 2021+. The E114 brief authorised a full-history analysis as a separate arm. This arm never changes the primary verdict.

**Data:** `data/long/`, E114's SWS 1998–2026 area series (115 rounds, read from SWS's own tables; the 2021+ rows are identical to §2.1).
- Pre-2021 publication dates: label month end + 60 days.

**Long covariates** (publication rules as in E114 `collect_covariates.py`)

| Covariate | Source | When usable |
|---|---|---|
| CALABARZON food, all-items and rice CPI YoY | PSA | Month m from day 10 of month m+1 |
| ONI | NOAA | Season ending in month m from day 10 of month m+1 |
| Typhoons in the Philippine Area of Responsibility (PAR) | IBTrACS | Quarter t at O(t) |
| National palay YoY | PSA | Quarter t−1 at O(t) |
| Unemployment-rate change | PSA LFS | Round m from day 1 of month m+3; 2005+ |
| GDELT DOC volume: shortage, agri_supply, jobs_income, assistance | GDELT | Month m from day 1 of month m+1; gap-aligned YoY; 2017+ |

**Families covered:** this arm covers 9 of the 12 families (A1–A3, C1–C3, E1, N, H). V1, C4 and E2 do not exist before 2021.

**FIL-LONG:** FIL's exact pipeline, label, grid and rules, with training rows from 1998-Q3.

**Evaluation sets**
- (a) **Untouched:** targets 2003-Q1 … 2020-Q4.
- (b) Targets in 2021+, compared with FIL.

**Rules:** §6 applies to each set. Baselines are PERSIST, MA2, MAJ and LOGIT, the logistic model using the long columns.

## 8. News, PSA and surge analyses

### 8.1 News ablation (same rows)

- FIL vs FIL-NONEWS, and FIL-HN vs FIL-H, at each lead.
- Tests: difference in accuracy and Brier (two-sided paired cluster bootstrap) and McNemar; Holm correction across leads.

### 8.2 News placebo

- FIL is refitted 100 times, each with the news columns permuted across origin quarters (whole quarter blocks; seed 2026).
- p = share of permutations whose Brier ≤ the real FIL Brier, at each lead.

### 8.3 Contribution

- Mean |SHAP| share per family in the issued FIL forecasts.
- Drop-one-family ΔBrier, paired bootstrap, Holm over the 12 families at each lead.
- A nonzero importance is never presented as evidence of value.

### 8.4 Early warning: anticipatory vs reporting news

- **Leading association:** Spearman ρ between each news column at O(t) and the realised z at Leads 1–4, on the panel. Holm over 7 columns × 4 leads.
- **Concurrent association:** the same correlations against the hunger change measured in the window's own quarter.
- News counts as *early warning* only if its leading association survives Holm.
- **Replication:** the same columns from GDELT GKG.

### 8.5 PSA provincial food-CPI deviation (economic access, supporting)

**Definition.** FPD(p,q) = the mean over the quarter's three months of (food CPI YoY − all-items CPI YoY) for province p, from PSA's provincial CPI (2018 = 100).

**Classification.** A *food-price squeeze* is FPD > 0: food prices rising faster than general prices.
- The threshold is zero, a natural reference point, not a fitted percentile.
- A squeeze is not food insecurity.

**Analyses**
1. **Coverage:** missingness, publication timing and base-period checks.
2. **Forecastability:** persistence accuracy of the squeeze sign at Leads 1–4, at province level.
3. **Hunger link:**
   - concurrent: the CALABARZON mean FPD vs BL ELEVATED and BL z;
   - leading: FPD known at O(t) vs BL z at Leads 1–4 (Spearman, Holm).

PSA agreement is never used as evidence that hunger was predicted.

### 8.6 Generalization and surges

**Splits:** periods (targets ≤ 2023-Q4, 2024, ≥ 2025-Q1), areas, rising vs falling, true horizon.

**Sharp increase:** H(a,q) − h_last > the margin of the newest known round (E111 definition: BL ±4 or ±6, other areas ±6).

**Reported:**
- the number of sharp increases;
- FIL's ELEVATED recall on those rows;
- mean underprediction;
- PERSIST on the same rows.

## 9. Leakage audit and seals

### 9.1 Leakage audit (must pass before scoring)

At 10 origins, FIL, PERSIST and LOGIT forecasts must be identical after each of these perturbations:
1. every SWS round published on or after O(t) is replaced by random values;
2. every corpus headline published on or after O(t) has its category and anticipatory flags shuffled.

The E107 feature cut-offs are cited from E107/E113, whose audits passed.

### 9.2 Seals

- **Issue:** FIL and PERSIST (and FIL-LONG) forecasts at O(2026-Q3) = 2026-10-01, for targets 2026-Q4 … 2027-Q3.
- **Record:** written to `out/sealed_prospective.csv`, with SHA-256.
- **Scoring:** by `runner/score_prospective.py` once SWS publishes.

## 10. Deliverables

1. `FINAL_PROTOCOL.md`
2. `TARGET_AND_DATA_VALIDATION.md`
3. `NEWS_FEATURES_AND_CONTRIBUTION.md`
4. `LIGHTGBM_MODEL_AND_METRICS.md`
5. `GENERALIZATION_AND_SURGE_EVALUATION.md`
6. `MAXIMUM_RELIABLE_LEAD_TIME.md`
7. `THESIS_OBJECTIVE_ASSESSMENT.md`
8. `FINAL_SIMPLE_METHODOLOGY.md`
9. `FINAL_RECOMMENDATION.md`

**Also delivered**
- prediction-level CSVs;
- `data/feature_map.csv` and `data/data_sources.csv`;
- the runner;
- tests in `backend/tests/unit/test_final_fi_lgbm.py`.

**Constraints:** nothing is merged into `main`, deployed, or switched in production.
