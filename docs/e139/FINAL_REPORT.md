# aiPHeed final system: E139 consolidated report (2026-11-05)

**Run record.**
* Protocol E139-P1 (`PROTOCOL.md`), locked before any fit on real outcomes. The pre-lock smoke test used shuffled
  labels.
* One tuning-and-validation run, then one final audit.
* Results files: `backend/data/e139/out/results.json` (sha256 `7a5f2a6a…`), `provinces_live.json`,
  `lgus_calabarzon.csv`, `sealed_prediction.json` (sha256 `0bcb5584…`), `model_artifact.json`.

**Decision: NOT APPROVED for production.**
* The candidate `e139-lgbm-1.0` is **rejected** by its pre-registered gate.
* Registry `production` stays `null`.
* The public outlook still answers `validation_pending`.
* The dashboard is unchanged. Candidate outputs are on admin routes only.

All results are **development evidence**: every HFIAS row was examined earlier (hfias-1.0, E137, E138).

---

## 1. What was wrong with the earlier LightGBM methodology

| Problem | Evidence |
|---|---|
| Tree-only LightGBM on 125 rows (62 decisive), for a relation that is close to linear in poverty | E137: overfitting gap 0.07–0.08. E138: stump LightGBM was the worst indicator model (LORO AUC 0.69). |
| No structured measured history. The region's and the province's earlier surveys are the strongest information. | E138: the regional base rate under LOPO reached AUC 0.96. Only poverty + a region effect beat it. |
| Noise groups diluted the trees | E138: market and climate added nothing in any nested test |
| Earlier systems (CH1/P0H4, FI-series) used price-pressure or regional SWS targets | Forensic audit 11-03: evidence class B/C, not provincial food insecurity |

## 2. What was changed and why

1. **Linear-prior LightGBM.**
   * A weighted ridge on poverty + measured history is LightGBM's `init_score`.
   * Conservative trees (3 leaves, depth 2, ≥ 15 rows per leaf, L2 10, feature subsample 0.7) then learn what the
     prior misses, from all groups.
   * Inner grouped CV chooses the number of trees from {0, 30, 100}.
   * Why: it lets LightGBM add non-linear and cross-group structure without forcing step functions onto a linear
     signal. It also lets the data say "no trees".
2. **A new measured-history feature: `a_region_prev`.** The region's mean measured position in the previous survey.
   It is past information only (missing for 2015 rows).
3. **Validation covers time as well as place.** The strictly forward test TFWD (2015 + 2018 → 2019) was added to
   LORO, LOPO, ISLAND and V2.
4. **A compact, frozen grid.** No search beyond {alpha} × {0, 30, 100 trees}.

## 3. Target and data

**Target (E137 audit, unchanged).**
* Measured HFIAS moderate-or-severe food insecurity relative to the national value of the same survey, as a
  continuous relative logit with its survey SE.
* Rounds: FNRI 2015 (78 provinces) and ENNS 2018/2019 (pooled 2018–2019 reference, 42.8 %).
* 125 rows with a value: 40 ELEVATED, 22 LOWER, 63 not distinguishable or wide.
* Output: P(elevated) = Φ(ŷ/σ).

**Why regression.** It keeps the magnitude of every measured row. E137 also showed it beats soft-label
classification.

**Data sources (manifests with sha256 in `data/e137/raw`, `data/e138/raw`, `data/e139/raw`).**
* **PSA OpenSTAT:**
  * poverty, subsistence, poverty gap and food threshold, 2006–2023;
  * provincial CPI, 2012=100 and 2018=100;
  * quarterly palay/corn and fisheries, 2012–2026;
  * censuses 2010–2024.
* NASA POWER monthly rainfall at 81 province centroids, 2000–2026.
* NOAA IBTrACS v04r01.
* FNRI FSS 2015 and ENNS 2018/2019 reports.

## 4. Final LightGBM configuration

| Setting | Value |
|---|---|
| Features (15) | poverty, subsistence, poverty gap, density; food CPI YoY, rice CPI YoY, food-threshold ratio; rainfall z, cyclones (4 quarters), cyclone climatology, agriculture per capita, agriculture YoY, fisheries YoY; `a_prev_y`, `a_region_prev` |
| Linear prior | ridge on poverty (3) + history (2), with missing-history flags |
| Trees | regression, num_leaves 3, max_depth 2, min_child_samples 15, reg_lambda 10, learning_rate 0.05, subsample 0.8, colsample 0.7 |
| **Final fit (all rows)** | **0 trees** (inner CV), base alpha 10, σ = 0.348 |

**What "0 trees" means.**
* Inner validation chose **0 trees in all 16 LORO folds**, in the V2 and TFWD fits, and in 72 of 78 LOPO folds.
  It chose 100 trees in 2 of the 3 ISLAND folds, where transfer is weakest.
* So the deployed function is its linear prior. Its standardised coefficients:

| Feature | Coefficient |
|---|---|
| poverty | +0.30 |
| subsistence | −0.09 |
| poverty gap | +0.08 |
| region's previous level | +0.19 |
| own previous level | −0.03 |

* **The LightGBM tree component did not add validated predictive value at this sample size.** That is a finding,
  not a configuration choice.

## 5. Training and independent validation results

LightGBM (final candidate). EB = expected Brier score; BSS = Brier skill vs climatology.

| Scheme | n (decisive) | EB | BSS | AUC [95 % CI] | PR-AUC | Accuracy [95 % CI] | BA | Recall | Precision | ECE | Train gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LORO, unseen region | 125 (62) | 0.192 | 0.21 | 0.915 [0.78, 0.98] | 0.958 | 0.774 [0.66, 0.86] | 0.723 | 0.900 | 0.783 | 0.066 | 0.018 |
| LOPO, unseen province | 125 (62) | 0.188 | 0.23 | 0.932 | 0.966 | 0.823 | 0.781 | 0.925 | 0.822 | 0.064 | 0.016 |
| ISLAND, unseen island group | 125 (62) | 0.240 | 0.01 | 0.692 | 0.758 | 0.758 | 0.710 | 0.875 | 0.778 | 0.095 | 0.096 |
| V2, 2015 → ENNS | 47 (38) | 0.177 | 0.25 | 0.840 | 0.925 | 0.684 | 0.668 | 0.720 | 0.783 | 0.098 | — |
| TFWD, 2015 + 2018 → 2019 | 25 (19) | 0.148 | 0.35 | 0.857 | 0.953 | 0.842 | 0.764 | 0.929 | 0.867 | 0.105 | — |

**LORO confusion matrix (decisive rows):** TP 36, FN 4, FP 10, TN 12.
* Specificity is 0.55: the model over-flags LOWER provinces.

**The 75 % objective.**
* Classification is an evaluation view of the selected regression.
* LORO accuracy on decisive rows is **77.4 %** (95 % CI 65.6–86.0 %, n = 62).
* The point estimate reaches 75 %, but **the interval does not exclude values below 75 %**, so the objective is not
  established with confidence. The target, split and threshold were fixed before the run.

## 6. Comparison with reference models (identical rows and folds)

**LORO (EB / AUC), with the EB difference for LightGBM minus the reference [95 % cluster-bootstrap CI].**

| Reference | EB / AUC | LightGBM − reference |
|---|---|---|
| RR-F, ridge, all features | 0.193 / 0.941 | −0.001 [−0.019, +0.018] |
| LR-F, logistic, all features | 0.212 / 0.900 | −0.020 [−0.048, +0.009] |
| RR-P, ridge, poverty only | 0.211 / 0.848 | −0.019 [−0.044, +0.008] |
| LR-P, logistic, poverty only | 0.212 / 0.851 | −0.019 [−0.050, +0.012] |
| HIER-P | 0.217 / 0.828 | −0.024 [−0.054, +0.005] |
| NAT, national base rate | 0.258 | **−0.066 [−0.110, −0.026]** |
| REGPREV, region's previous level | 0.218 / 0.632 | −0.026 [−0.067, +0.013] |
| PERS, previous survey (ENNS rows) | 0.195 / 0.766 | see G3 |

**LOPO (same-survey neighbours known).**
* REG: 0.177 / 0.963 (LightGBM − REG: +0.011 [−0.020, +0.040]).
* HIER-P: 0.166 / 0.975.

**TFWD.**
* HIER-P: 0.139 / 0.943.
* RR-F: 0.128 / 0.871.
* REGPREV: 0.161 / 0.836.
* PERS: 0.188 / 0.814.

**Reading.**
* LightGBM equals the best linear benchmark.
* It clearly beats the national base rate.
* It does **not** beat what is already known from earlier surveys of the region (REGPREV) or the province (PERS)
  with confidence.
* Where same-survey neighbours are known, the region-aware models (REG, HIER) are better.

## 7. Overfitting, leakage, bias, calibration, generalisation

* **Overfitting:** training gap 0.016–0.018 (LORO/LOPO).
* **Leakage:**
  * no identifier features;
  * history features come only from earlier surveys (tested);
  * every feature follows its release rule (live check: 2026-Q3 production is excluded at the 2026-10-01 issue);
  * the shuffled-label smoke test shows no signal.
* **Calibration:** ECE 0.066 (LORO).
* **Generalisation:**
  * unseen province or region: strong;
  * unseen island group: weaker (AUC 0.69, EB skill about 0);
  * forward in time: AUC 0.86 on n = 25.
* **Bias:** the model over-flags LOWER provinces (specificity 0.55).
* **Sensitivity:** any-level outcome AUC 0.911; round-printed reference 0.940.
* **Missing data:** masking market or climate changes nothing; masking history adds +0.018.

## 8. The five indicator groups

**Ablation:** the group is removed from both the prior and the trees. Change in LORO expected Brier score vs the full
model (0.192); positive means the group helped.

| Group | Data | LORO change [CI] | TFWD | Verdict |
|---|---|---|---|---|
| Poverty and social vulnerability | PSA, national | +0.012 [−0.029, +0.054] | removal *improves* (0.135 vs 0.148) | Main structural signal (E138: masking +0.042), but not significant once history is present |
| Measured history (not one of the five groups) | FNRI/ENNS | +0.020 [−0.009, +0.043] | removal worsens (0.199 vs 0.148) | Strongest for forecasting the next survey |
| Market and food affordability | PSA CPI, national | 0.000 | 0.000 | **No incremental information** |
| Climate and agriculture | NASA, IBTrACS, PSA production | +0.007 [0.000, +0.020] | 0.000 | **No incremental information** |
| Employment and purchasing capacity, incl. OFW remittances | no provincial series 2014–2019 (OpenSTAT LFS is national; BSP remittances are national) | not testable | — | **Context only.** Not a model input. |
| News and NLP | the FI6-N archive was collected with CALABARZON-only queries; GDELT starts in 2017 | not testable nationally; regional Lead-0 Brier gain only (FI6-N) | — | **Context only.** Not a model input. |

**Why the employment and news groups cannot contribute.** There is **geographic mismatch**: the indicators exist
only nationally or only for CALABARZON, while the labels are national provincial rows. There is also **historical
coverage** mismatch: news starts in 2017 or 2021. Within CALABARZON alone there are 8 measured rows, which cannot
validate any group.

## 9. Maximum validated forecasting horizon: **none**

| Lead | Passes | Fails |
|---|---|---|
| 0 | G1, G5, G6, G9 | **G2** (vs REGPREV on ENNS rows: [−0.054, +0.069]) and **G3** (vs PERS: CI upper +0.022 > 0.02) |
| 1–4 | same | same |

* All lead-independent checks (G4, G7, G8, G10, G11) pass.
* Leads 1–4 change only the quarterly inputs, which carry no information. AUC is the same (0.90–0.92) at every lead,
  so the leads show **no quarterly forecasting skill**.
* Regional timing (FI6, locked) has no lead either.
* No output may be labelled a forecast.

## 10. CALABARZON coverage and examples (issue 2026-10-01; candidate, not served)

**Provincial risk estimates.** P(HFIAS moderate-or-severe above the national level), 90 % bootstrap interval.

| Province | P(elevated) | 90 % interval | Estimate |
|---|---|---|---|
| Quezon | 0.105 | 0.020–0.300 | not elevated |
| Laguna | 0.083 | 0.013–0.265 | not elevated |
| Cavite | 0.067 | 0.008–0.271 | not elevated |
| Batangas | 0.064 | 0.011–0.198 | not elevated |
| Rizal | 0.056 | 0.013–0.181 | not elevated |

* Quezon ranks highest in 58 % of refits. **No province is distinct.**
* **Explanation shown for each province:**
  * Poverty: "Lower poverty levels mean fewer households are likely to lack the money for enough food."
  * History: "Earlier food-security surveys found this area below the national level of food insecurity."
  * Market and climate: "not influential".
* **LGUs:** `lgus_calabarzon.csv` holds all **142 LGUs** (Batangas 34, Cavite 23, Laguna 30, Quezon 41, Rizal 14).
  * Each has PSA SAE 2021 poverty and POPCEN 2024 density, a vulnerability score and rank, and its province's
    structural estimate.
  * Each is labelled "municipal vulnerability …, not a municipal food-insecurity measurement".
  * No municipal outcome was created.

## 11. Tests executed

| Suite | Result |
|---|---|
| `tests/unit/test_e139.py` (8), `test_e138.py` (7), `test_e137.py` (10), `test_registry.py`, `test_pfi.py` | 56 passed |
| Full backend `tests/unit` | **843 passed**, 0 failed (3 min 10 s) |
| Frontend | unchanged (no frontend file modified) |

**What the E139 tests cover:**
* the lock;
* no identifier features;
* history from earlier surveys only;
* the zero-tree equivalence;
* TFWD strictly forward;
* live release dates;
* 142-LGU coverage and labelling;
* registry rejection;
* public outlook `validation_pending`;
* admin-only candidate routes (401/403 without admin; `CANDIDATE_NOT_APPROVED` with admin).

## 12. Files changed

* **New code:**
  * `backend/app/e137/`, `backend/app/e138/`, `backend/app/e139/`;
  * E139 modules: `model`, `evaluate`, `live`, `issue`, `serve`, `gate`.
* **New tests:** `backend/tests/unit/test_e137.py`, `test_e138.py`, `test_e139.py`.
* **Changed:**
  * `backend/app/api/v1/registry.py`: E139 candidate routes; production server entry, used only if approved;
  * `backend/app/registry/catalog.py`: entries for e137, e138 and e139;
  * `backend/data/registry/registry.json`: all three rejected.
* **New data:** `backend/data/e137/`, `e138/`, `e139/`. The 115 MB IBTrACS file is gitignored and re-downloadable.
* **New docs:**
  * `docs/e137/`, `docs/e138/`, `docs/e139/`;
  * `docs/reassessment/RISK_REASSESSMENT_20261103.md`;
  * `docs/release/MASTER_DIRECTIVE_REPORT_20261103.md`.
* **Commit:** see the commit on branch `pfi/survey-anchored-final` that adds this file.

## 13. Production decision

**Not approved.**

**What works and is validated (development evidence).**
* A leakage-safe, reproducible pipeline, trained on measured food-insecurity outcomes, that ranks provinces' relative
  food-insecurity risk well:
  * unseen region: AUC 0.92;
  * forward in time: 0.86.
* It is well calibrated (ECE 0.07) and does not overfit.

**Why it fails.**
* It does not show, with confidence, value beyond what earlier surveys of the same region and province already say
  (G2, G3).
* It has no forecasting lead.
* Its LightGBM trees were not selected (0 trees).

**What would change the decision.**
* The sealed predictions (`sealed_prediction.json`, `0bcb5584…`; and E138 `e324433c…`), scored against the next
  provincial HFIAS/FIES round, are the confirmatory test.
* A third provincial round would also double the number of survey-to-survey changes, which G2/G3 and any
  forecasting lead need.
