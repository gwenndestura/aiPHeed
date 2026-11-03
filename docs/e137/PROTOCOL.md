# E137 SARF: survey-anchored food-insecurity risk model. Protocol E137-P1

* **Experiment ID:** E137. **Candidate:** `e137-sarf-1.0`. **Code:** `backend/app/e137/`. **Data:** `backend/data/e137/`.
* **Lock:** the lock file `backend/data/e137/out/PROTOCOL_LOCK.json` holds the sha256 of this file, of the four code
  modules and of the threshold table. It is written before any E137 model is fitted to real outcomes. `run` refuses
  to start if any hash differs.
* **Pre-lock check:** before the lock, the pipeline was run only on **shuffled** outcomes, as a smoke test.
* **Owner decisions applied (2026-11-03):**
  * D-1: the proposed national reference was approved by "proceed with the proposed two-layer methodology".
  * D-2: moderate-or-severe is the primary outcome; "any food insecurity" is a sensitivity analysis.
  * D-3: ENNS 2018/2019 may be used as **development evidence only**.
* **Honest history:**
  * hfias-1.0 used the same HFIAS rows (as a prevalence target) and scored the 2019 ENNS provinces once.
  * Before writing this protocol, the outcome table was inspected descriptively (spread, persistence, status
    counts).
  * Therefore **no E137 result on these rows is a confirmatory test.**

## 1. Purpose

* **What it estimates:** food-insecurity **risk**, defined as the probability that a province's household food
  insecurity is above the national level of the same survey. The estimate comes from indicators available at the
  issue date.
* **What it does not do:** it does not predict prevalence, and it does not create quarterly food-insecurity labels.

## 2. Outcome (audit: `OUTCOME_AUDIT.md`)

**Instrument and population.**
* Instrument: HFIAS (9 items, 30-day recall, FNRI categories after Coates et al. 2007).
* Unit: household.
* Surveys: FNRI 2015 FSS, all 78 provinces; ENNS 2018 and 2019 provincial reports (HUCs and NCR towns excluded).

**Primary outcome.** Moderate-or-severe food insecurity = moderate + severe.
* 2015 SE: design-effect method, capped at the conservative sum of the printed SEs.
* ENNS SE: conservative sum of the printed SEs.

**Secondary outcome.** Any food insecurity = 100 − secure.

**Reference.**
* For 2015 rows: the 2015 national value (mod-sev 53.8 %).
* For ENNS rows: FNRI's **pooled 2018–2019 national** value (mod-sev 42.8 %; any level 56.0 %).
  * The round-printed "Philippines" values (2018 subset and 2019 subset) are the sensitivity reference.
  * Reason: they are estimates for each round's own subset of provinces. Their difference (53.9 → 64.1 % any level)
    is not a national change.

**Target.**
* y = logit(p) − logit(reference).
* se_y by the delta method (reference SE 0.5 pp added in quadrature).
* Soft label q = Φ(y / se_y) = P(true relative logit > 0 | survey).

**Status of each row.**

| Status | Rule |
|---|---|
| ELEVATED | z ≥ 1.96 |
| LOWER | z ≤ −1.96 |
| NOT_DISTINGUISHABLE | \|z\| < 1.96 |
| INSUFFICIENT | No category breakdown (5 headline-only 2019 decks), or 95 % half-width of p > 10 pp |

**How uncertain rows are used.** No row is forced into HIGH or LOW.
* Every row with a value is trained on, and scored through its soft label q.
* Only ELEVATED and LOWER rows enter the class metrics (AUC, balanced accuracy, recall, precision, F1).
* Rows with no value at all are dropped.

Counts (primary outcome): 125 rows with a value, of which 62 are decisive (40 ELEVATED, 22 LOWER), 38 are
NOT_DISTINGUISHABLE and 25 are wide-interval INSUFFICIENT. The 5 headline-only rows are dropped.

## 3. Lead and issue date

* Each survey's reference quarter is Q3 of the survey year. The 2015 fieldwork ran July–November. The ENNS fieldwork
  months are not printed, so mid-year is assumed.
* Lead k means the features are frozen at the start of the reference quarter minus k quarters (Leads 0–4).
* In operation, a forecast viewed in quarter Q has Lead 0 = Q, Lead 1 = Q+1, and so on. All are computed from
  information public at the issue date.

## 4. Features (`features.py`; release rules in its docstring)

| Group | Features | National provincial source 2012–2019 |
|---|---|---|
| Market and affordability | food CPI YoY, rice CPI YoY, per-capita food threshold relative to national | PSA annual provincial CPI (2012=100); PSA food threshold |
| Climate and agriculture | rainfall anomaly over the last 6 months (z vs 2000–2009), tropical cyclones within 150 km in the last 4 quarters, cyclone climatology 1990–2009, palay+corn per capita, palay+corn YoY, fisheries YoY | NASA POWER; IBTrACS v04r01; PSA quarterly production; census |
| Poverty and vulnerability | poverty incidence, subsistence incidence, poverty gap, population density | PSA official poverty statistics; census |
| Outcome history (anchor) | previously measured relative position (ENNS rows only) | FNRI 2015 |
| Employment and purchasing capacity | **not available**: PSA OpenSTAT LFS is national only before 2021 | — |
| News and NLP | **not available nationally**: the FI6-N archive was collected with CALABARZON-only queries | — |

* **Directions.** Monotone directions were set from theory before any fit (`features.MONOTONE`).
* **Missing values.**
  * LightGBM handles missing values natively.
  * The logistic baselines impute the training-fold median.
  * Missing cells: renamed or split provinces (Compostela Valley, North Cotabato, Maguindanao); Mindoro and
    Mountain Province CPI.

## 5. Models (`model.py`)

**LightGBM formulations.**
* **REL:** regression on y, weighted by 1/(se_y² + τ²). P = Φ(ŷ/σ), with σ from inner cross-validation, survey
  error removed.
* **SOFT:** cross-entropy on q.
* **Settings:** shallow grid A–D (depth ≤ 3, min_child_samples ≥ 10, L2 5–10, bagging 0.8), with monotone
  constraints. The configuration is chosen by inner grouped 5-fold cross-validation (by region) on training rows
  only.

**Baselines (same rows and folds).**
* **B0:** base rate.
* **B1:** persistence. The previous measured position, with change variance taken from training rows.
* **B2:** PSA-only logistic regression on poverty, subsistence and poverty gap.
* **B3:** logistic regression on all features, with soft labels.
* **NLP-only:** not evaluable in Layer S (no national news).

## 6. Formulation choice (frozen rule)

* Compare REL and SOFT on the scheme V1 expected Brier score at Lead 0 for the primary outcome.
* SOFT is chosen only if it is lower by more than 0.005. Otherwise REL is chosen, because it is continuous and uses
  more information.
* Both formulations are reported at every lead.

## 7. Evaluation schemes

* **V1 (development):** all rows pooled, leave-one-region-out over the 16 regions that have provinces. A province's
  2015 and ENNS rows are always in the same fold.
* **V2 (out-of-round, development):** train on 2015 rows, predict ENNS rows. The anchor feature is unavailable in
  training, so it is excluded.
* **Metrics:**
  * expected Brier score E[(P − Y)²] with Y ~ Bernoulli(q);
  * AUC, balanced accuracy, accuracy, recall, precision, F1 and the confusion matrix (decisive rows, threshold 0.5);
  * soft calibration error (ECE, 5 bins);
  * Spearman correlation between ŷ and y;
  * mean P on NOT_DISTINGUISHABLE rows.
* **Uncertainty:** cluster bootstrap by region (2,000 replicates).
* **Contributors:** grouped TreeSHAP on out-of-fold rows. Share = |SHAP| of the group / |SHAP| of all groups (anchor
  excluded).

## 8. Revised risk gate (development checks; thresholds in `evaluate.THRESHOLDS`, hashed in the lock)

Applied per lead to the chosen formulation, primary outcome, scheme V1 unless stated otherwise.

| Check | Rule |
|---|---|
| S1 | Expected Brier better than B0, B2 and B3 (point estimate), **and** the 95 % cluster-bootstrap upper bound of (LGBM − B0) and (LGBM − B2) is below 0 |
| S2 | AUC ≥ 0.70 and 95 % lower bound ≥ 0.60 |
| S3 | Balanced accuracy ≥ 0.70, recall (elevated) ≥ 0.60, precision (elevated) ≥ 0.50 |
| S4 | ECE ≤ 0.10 |
| S5 | AUC ≥ 0.60 in each island group with at least 3 rows of each class (at least 2 groups needed) |
| S6 | V1 expected Brier minus training expected Brier ≤ 0.05 |
| S7 | On ENNS rows, expected Brier better than B1 persistence |
| S8 | V2 AUC ≥ 0.65 |
| S9 | Sensitivity runs (any-level outcome; round reference): AUC ≥ 0.65 |
| S10 | Median largest-group share ≤ 0.80. The model is not rebalanced if it fails; failing means it is not approved. |
| S11 | External check, run once after the development run. The final Lead-0 model is applied to 2023-Q3 features for all provinces and aggregated to regions (population-weighted). The Spearman correlation with PSA FIES 2023 regional moderate-or-severe must be ≥ 0.40 with p < 0.05. FIES is a different instrument, so this is agreement, not accuracy. |
| S12 | Confirmatory test on unseen measurements (a new FNRI round, PSA 2026 FIES, or a sealed future outcome). **Pending.** |

**Maximum reliable lead.** The largest k such that S1–S10 pass at k and at every lead below it.

**Gate outcome.**
* **APPROVED-PROVISIONAL (development evidence):** S1–S11 all pass. S12 stays pending, and the dashboard must
  label the result as provisional.
* **REJECTED:** any of S1–S11 fails.
* Promotion to the dashboard also needs the owner's approval in the registry.

## 9. Layer T (timing)

* **Source:** the timing evidence is the locked FI6/FI6-N study. Its issue is at quarter end, so FI6 Lead k+1 is this
  protocol's Lead k. It is **not re-run**, because those quarters have already been scored.
* **Rule:** Layer T enters the provincial score only if LightGBM passed FI6's locked reliability rule at that lead.
  * **FI6 recorded no passing lead for LightGBM.** Naive persistence passed at FI6 Lead 1, which is this protocol's
    Lead 0.
  * **Therefore Layer T is not part of the E137 score.**
  * Regional SWS hunger stays as separate regional context and is never copied into provinces.
  * The employment and news groups are assessed only in Layer T (FI6-N: news gives a Brier gain at Lead 0 only, no
    class gain).

## 10. Outputs

* `results.json`: every metric, both formulations, every lead, sensitivity runs, group shares, gate checks.
* `oof_predictions.csv`: out-of-fold predictions.

Live CALABARZON scores are produced only if the gate approves. They would need the same features for 2024–2026
(data to be acquired after this run).
