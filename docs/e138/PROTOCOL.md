# E138: incremental value, WHERE vs WHEN, CALABARZON differentiation. Protocol E138-P1

* **Experiment ID:** E138. **Code:** `backend/app/e138/`. **Data:** `backend/data/e138/`.
* **Lock:** `backend/data/e138/out/PROTOCOL_LOCK.json` holds the sha256 of this file, of `models.py`, `where.py`,
  `when.py`, `evaluate.py` and of the threshold table. The lock is written before any E138 candidate is fitted to
  real outcomes. Before locking, the full run was executed once on **shuffled** labels as a smoke test.
* **E137 is preserved unchanged** (rejected; its lock and results are untouched). E138 imports E137's outcome and
  feature builders without modification.
* **Evidence status:** all 125 HFIAS rows were already examined in hfias-1.0 and E137. Every E138 number is
  **development evidence**. Independent confirmation can come only from (a) the sealed prediction in section 9,
  scored against the next provincial survey round, and (b) the sealed FI5/FI6 regional forecasts for 2026-Q4 onward.

## 1. Two questions, kept separate

* **WHERE.** Which provinces have structurally elevated relative risk, meaning HFIAS moderate-or-severe above the
  national level of the same survey? This is a between-province question. Its evidence is survey cross-sections.
* **WHEN.** Does risk rise or fall over time, and can indicators anticipate it?
  * The within-province evidence is the measured change 2015 → ENNS (section 7).
  * The regional evidence is the locked Layer T record (section 8).
* Structural poverty features are never presented as evidence of quarterly forecasting skill.

## 2. Data

* E137 primary rows: 125 rows with a value; 62 decisive (40 ELEVATED, 22 LOWER).
* Features at Lead 0 unless stated.
* Sensitivity runs: the any-level outcome, and the round-printed reference.

## 3. Candidates (`models.py`)

**Baselines.**
* NAT: national base rate.
* REG: regional base rate, shrunk with κ = 5.
* PERS: previous survey position.

**Linear models.**
* L2 logistic regression on soft labels (C chosen by inner grouped 5-fold cross-validation):
  * P1: subsistence only (a one-indicator scorecard);
  * P: poverty, subsistence, poverty gap;
  * PD: P + density;
  * PA: P + anchor;
  * PM: PD + market;
  * PC: PD + climate;
  * PMC: PD + market + climate;
  * ALL: PMC + anchor.
* Continuous relative-risk ridge regression: RR-P, RR-PMC, RR-ALL.
* Hierarchical logistic with an empirical-Bayes region intercept: HIER-P, HIER-PMC.

**LightGBM, strongly regularised and fixed (not tuned).** GB-PMC and GB-ALL: stumps, 60 trees, at least 20 rows per
leaf, L2 = 20, monotone constraints.

## 4. Schemes

| Scheme | Folds | Purpose |
|---|---|---|
| LORO | 16 regions | geographic transfer to an unseen region (**primary**) |
| LOPO | each province, both rounds together | information within a region; the only scheme where REG and HIER differ from NAT and LR |
| ISLAND | Luzon / Visayas / Mindanao | strong geographic transfer |
| V2 | train 2015 → predict ENNS | stability across surveys (anchor models excluded) |

## 5. Metrics and incremental value

* **Metrics:** E137's metric set.
  * Expected Brier score (primary).
  * AUC, balanced accuracy, recall, precision, F1 and the confusion matrix, on decisive rows.
  * ECE.
  * Training expected Brier and the overfitting gap.
* **Paired cluster-bootstrap differences** (by region, 1,000 replicates):
  * every candidate vs LR-P and vs NAT (LORO);
  * vs REG (LOPO);
  * vs PERS on ENNS rows.
* **Incremental information** from a feature group = the difference between nested sets on identical rows:
  * PM, PC, PMC vs PD;
  * PD vs P;
  * PA vs P.

## 6. Selection (frozen one-SE rule) and gate

* **Selection.**
  * Complexity order: NAT < LR-P1 < LR-P < LR-PA < LR-PD < RR-P < LR-PM < LR-PC < LR-PMC < RR-PMC < LR-ALL < RR-ALL < GB-PMC < GB-ALL.
  * "Best" = the lowest LORO expected Brier score.
  * Select the **simplest** candidate whose EB − EB(best) ≤ the bootstrap SE of that difference.
  * LightGBM is selected only if no simpler model comes within one SE of it.
* **Gate** (thresholds in `evaluate.THRESHOLDS`, hashed in the lock). Applied to the selected model.

| Check | Rule |
|---|---|
| G1 | Beats NAT in LORO: 95 % CI upper bound of the EB difference < 0 |
| G2 | Beats REG in LOPO: CI upper bound < 0. Does it add anything beyond "which region"? |
| G3 | LORO AUC ≥ 0.75 and 95 % lower bound ≥ 0.60 |
| G4 | Balanced accuracy ≥ 0.70, recall ≥ 0.60, precision ≥ 0.60 |
| G5 | ECE ≤ 0.10 |
| G6 | ISLAND AUC ≥ 0.65 |
| G7 | Overfitting gap ≤ 0.05 |
| G8 | Non-inferior to persistence where a survey exists. The anchored variant's EB minus PERS has a CI upper bound ≤ 0.02. The anchored variant is the selected set plus anchor: LR-PA for P1/P/PD, otherwise ALL. |
| G9 | V2 AUC ≥ 0.70 |
| G10 | Sensitivity AUC ≥ 0.70 for both alternative definitions |
| G11 | Robust to a missing non-poverty group: setting the group missing at prediction time changes EB by ≤ 0.02 |
| G12 | Confirmatory test on the sealed prediction: **pending** |

**Gate outcome.**
* All of G1–G11 pass → **APPROVED-PROVISIONAL (structural WHERE layer only; development evidence)**.
* Promotion still needs owner approval. The dashboard would have to label it "structural risk (provisional)" and
  show no forecast lead.
* Any of G1–G11 fails → rejected.
* **Structural validity horizon.** The selected model is also scored at Leads 2 and 4 (LORO). V2 measures how long a
  2015-based estimate stays informative. These are reported as structural validity, **not** as a forecasting lead.

## 7. WHEN, within province (`when.py`)

* **Panel.** The 47 provinces measured in 2015 and in ENNS.
* **Target.** Δy = y_ENNS − y_2015, with its standard error.
* **Changes tested** (each feature at the ENNS issue date minus its 2015 value):
  * food, rice and threshold CPI;
  * rainfall anomaly;
  * agriculture and fisheries YoY;
  * poverty rounds;
  * cyclones per year between the two dates;
  * the 2015 position (regression to the mean).
* **Tests.**
  1. Spearman correlation with Δy, Holm-adjusted.
  2. LORO prediction of Δy by weighted ridge (α = 3) on the changes, against three baselines:
     * zero change;
     * mean change;
     * mean reversion.
* **Also reported:** the share of changes that lie inside survey error (|Δy/se| < 1.96).

## 8. WHEN, regional (Layer T)

* **Not re-run.** The locked FI6 and FI6-N results are summarised. FI6 Lead k+1 = Lead k here.
* **Independent evaluation is available only prospectively:** the sealed FI5 forecast (sha `350ffe4f…`) and the FI6
  forecast for 2026-Q4 onward, scored when SWS publishes them.
* **Rule.** Layer T enters a provincial score only if it shows incremental value over persistence. That has not
  happened.

## 9. CALABARZON differentiation and the sealed prediction

These steps run after the main run. Their procedure is fixed here.

1. **Measured differences.**
   * Pairwise z-tests and Cochran's Q among the five provinces on 2015 HFIAS moderate-or-severe (design-effect SE).
   * The ENNS rows (Laguna 2018; Quezon and Rizal 2019).
   * PSA subsistence and poverty incidence 2018/2021/2023, using the published SEs.
2. **Model uncertainty.**
   * Refit the selected model on 500 region-cluster bootstrap resamples.
   * Predict the five provinces from the latest public values of its features.
   * Report P(each province ranks first) and pairwise P(A > B).
   * A province is called **distinct** only if P(A > B) ≥ 0.95, or ≤ 0.05, against every other province.
3. **Sealed prediction.**
   * Fit the selected model on all rows.
   * Predict every province from the latest public features.
   * Write `sealed_prediction.json` with its sha256, before any new provincial round is seen.
   * The confirmatory metrics when that round appears: expected Brier score and AUC on decisive rows, against NAT,
     REG and PERS.

## 10. Five contributor groups

**Nationwide availability for the training years (2014–2019):**
* poverty and vulnerability: yes;
* climate and agriculture: yes;
* market: yes;
* employment: no (OpenSTAT LFS is national only; no provincial series before 2021);
* news: no (the archive was collected with CALABARZON-only queries; GDELT DOC starts in 2017).

**How groups are shown:**
* A group is shown as a model input only if it is in the selected model.
* A group counts as "contributing" only if its nested-set test (section 5) shows incremental value.
* Unavailable groups are reported as **evidence context only**, never as inputs.
