# aiPHeed provincial forecasting: consolidated final report v2 (2026-11-05)

**What it supersedes.** This report supersedes `PROVINCIAL_FORECASTING_FINAL_REPORT.md` (E141) wherever they
differ.

**New in this round.**
* E141 audit from its locked outputs.
* Survey-timing evidence.
* E142, a survey-anchored provincial risk-state model (protocol E142-P1, locked before scoring, run once).
* FSSI v2 volume correction.
* Corrected labels on the price-pressure explanation panel.
* Scorer confidence intervals and confirmation rule.
* A fifth prospective seal.

**Unchanged:** E137–E141 code, locks, results and seals. All six locks verify.

## 1. Final provincial target

* **What is predicted:** for Cavite, Laguna, Batangas, Rizal and Quezon separately, P(the province's household food
  insecurity, HFIAS moderate-or-severe as published by FNRI, is above the national value) in the target quarter.
  * The target quarter is the quarter after the viewing quarter.
  * The issue is at the start of the viewing quarter.
  * Only information public before the issue is used.
* **How it is measured:** HFIAS 9 items, 30-day recall, household, in three FNRI rounds: 2013 (78 provinces), 2015
  (78) and ENNS 2018/2019 (47 provinces). Relative logit with survey SE.
* **What it is not:** a share of households, a measured status, or a price index.

## 2. E141 audit (reproduced from its locked out-of-fold files; nothing re-run)

**Why its gate failed.**
* LightGBM's pooled EB of 0.194 sits within sampling noise of persistence (−0.013 [−0.040, +0.014]).
* The region's previous level is slightly better (0.190).
* With only 125 targets in 16 regional clusters, a CI half-width of about 0.03 is the binding limit.

**What the models actually learn.**

| Finding | Value |
|---|---|
| Between-province ranking | Spearman with the measured position 0.53 (LightGBM), 0.55 (persistence), 0.56 (region's previous level) |
| Within-province change | 41 of 125 changes exceed survey error (16 up, 25 down). Predicted-minus-persistence correlates with the measured change: LightGBM 0.39, linear prior 0.41, region's previous level 0.25. |
| Class flips | Only 2 of 26 provinces decisive in both rounds changed class |

The change signal is mean reversion toward a structural level, not quarterly shocks. All quarterly indicators add 0.

**Why origin O1 is weakest.** Its training round (2013) has no earlier survey, so no model can learn how much the
previous round should count. Persistence wins there.

**Calibration on 2013 (ECE 0.139).** LightGBM was underconfident at the top: it predicted 0.47 / 0.69 / 0.86 where
the measured soft labels were 0.63 / 0.80 / 0.99. The 2013 relative positions are more extreme than in its training
rounds.

**Stability across origins.**

| Origin | Tree type selected |
|---|---|
| O1 | linear × 30 |
| O2 | constant-leaf × 300 |
| O3 | constant-leaf × 100 |

The structure is not stable across origins. Poverty and island group carry the largest (non-significant) ablation
effects.

## 3. Data recovery (this round)

| Source | Result |
|---|---|
| FNRI NNS 2013 provincial HFIAS | Recovered in E141 (Appendix 33). Design-based SEs are not printed (E141 approximation kept and flagged). |
| ENNS 2018/2019 fieldwork months | **Not printed** in any monograph or deck. The documents state only that provinces were assigned to yearly replicates (2018, 2019, 2021), each "to gain efficiency in the generation of national level estimates for a given year", with about 1,536 households targeted per province. |
| ENNS 2021 provincial | Not public online or archived (FNRI eNutrition and main-site archives, 15,602 + 1,947 URLs checked). Prepared request: `DATA_REQUEST_FNRI_PROVINCIAL_HFIAS.md` (not sent; owner rule). |
| 2023 NNS | regional only |
| PSA FIES | regional 2023 only. Kept separate (agreement only). |

## 4. Survey alignment and its effect

* **Reference quarter:** Q3 of each survey year.
  * 2013 fieldwork: June–December 2013 (+ Feb–Apr 2014).
  * 2015 fieldwork: July–November.
  * ENNS: months unknown.
* **Effect of the assumption (E142 timing sensitivity):** moving the issue to Lead 0 or Lead 3 changes STATE-LGBM's
  EB from 0.193 to 0.193 / 0.205, and E141 LightGBM's from 0.194 to 0.193 / 0.196. Persistence and the region's
  previous level do not change.
* **Conclusion:** the conclusions are robust to a ±1–2 quarter error.

## 5. Province-quarter panel

* **Implementation:**
  * `app/e141/panel.py`: one row per province and measured round, with features as of the issue date.
  * `app/e139/live.py`: live rows at any issue date.
* **Each row records:**
  * province and key;
  * survey and reference quarter;
  * issue date (Lead k);
  * the previous round and its position;
  * features, with E137's release rules (CPI 15 Feb of the next year; poverty round R from 1 Jan R+2; production
    +45 days; NASA +30 days; cyclones in real time);
  * missing values kept as missing.
* **Coverage:**
  * 203 measured province-rounds.
  * Feature coverage 0.91–1.00 per survey.
  * Measured history is absent for 2013 by construction.

## 6. Methodology selected: E142 STATE-LGBM (risk-state model)

**Model.**
* **Latent state:** the province's true relative logit.
* **Observation:** each survey, with its SE.
* **Transition:** AR(1) toward a LightGBM structural level from indicators. The level excludes measured history and
  is computed out-of-fold.
* **φ and τ²** are estimated by method of moments from measured transitions only.
* **φ is not identified without a transition.** In O1, φ = 0, so the model is structural only.
* **Forecast:** structural level + φ^h × filtered deviation at the last survey. The variance grows with h.
* **Estimates:** φ ≈ 0.93–0.94 per quarter. A survey's weight halves in about 10 quarters.

**Why this model.**
* It is the only formulation with an **identifiable**, data-estimated link between surveys and later quarters.
* It uses the measured change signal (mean reversion) explicitly.
* It quantifies how uncertainty grows with time since the last survey.

**Stated assumption:** the quarterly form of the transition. Only 8-, 12- and 16-quarter gaps are observed.

## 7. Model comparison (identical E141 folds; 125 targets; Lead 1)

| Model | EB | AUC | Accuracy | HIGH recall | Precision | ECE | Change ρ [95 % CI] |
|---|---|---|---|---|---|---|---|
| **STATE-LGBM (E142)** | **0.193** | 0.956 | 0.887 | **0.950** | 0.884 | 0.053 | **0.44 [0.32, 0.59]** |
| LightGBM (E141) | 0.194 | **0.964** | **0.903** | 0.875 | **0.972** | 0.040 | 0.39 [0.25, 0.53] |
| LGBM + Platt calibration | 0.195 | 0.964 | 0.887 | 0.875 | 0.946 | **0.034** | 0.42 [0.31, 0.54] |
| Region's previous level | **0.190** | 0.926 | 0.806 | 0.825 | 0.868 | 0.063 | 0.25 [0.13, 0.38] |
| STATE-RIDGE | 0.202 | 0.912 | 0.790 | 0.825 | 0.846 | 0.066 | 0.38 [0.20, 0.56] |
| Linear prior | 0.203 | 0.917 | 0.774 | 0.775 | 0.861 | 0.085 | 0.41 [0.26, 0.56] |
| Ridge, all | 0.203 | 0.930 | 0.806 | 0.750 | 0.938 | 0.072 | 0.33 |
| PSA-only | 0.206 | 0.908 | 0.790 | 0.800 | 0.865 | 0.066 | 0.42 |
| Persistence | 0.207 | 0.856 | 0.806 | 0.850 | 0.850 | 0.131 | — |
| Logistic, all | 0.229 | 0.898 | 0.758 | 0.700 | 0.903 | 0.155 | 0.26 |
| National base rate | 0.250 | 0.451 | 0.645 | 1.000 | 0.645 | 0.069 | — |

**STATE-LGBM − reference, EB [95 % CI].**

| Reference | Difference |
|---|---|
| Persistence | −0.014 [−0.039, +0.009] |
| Region's previous level | +0.003 [−0.031, +0.038] |
| E141 LightGBM | −0.001 [−0.010, +0.008] |
| STATE-RIDGE | −0.009 [−0.030, +0.013] |

**By origin (EB).**

| Origin | STATE-LGBM | Persistence | Region's previous level |
|---|---|---|---|
| O1 | 0.221 | 0.214 | 0.212 |
| O2 | 0.151 | 0.207 | 0.140 |
| O3 | 0.141 | 0.187 | 0.164 |

**Untouched 2013 (structural only, since there is no earlier round).**

| Model | EB | AUC | ECE |
|---|---|---|---|
| STATE-LGBM | 0.155 | 0.936 | 0.106 |
| STATE-RIDGE | 0.147 | 0.990 | 0.044 |

**NLP-only:** not constructible provincially. There is no news outside CALABARZON for 2013–2019.

**Gate E142-P1.**
* **Passed:**
  * S4 (classes);
  * S5 (predicts change);
  * S6 (beats persistence at O2 and O3);
  * S7 (LightGBM level not worse than the ridge level).
* **Failed:**
  * S1 vs persistence;
  * S2 vs the region's previous level;
  * S3 (2013 ECE 0.106 > 0.10).
* **Decision: not validated. Sealed as the primary candidate.**

## 8. Provincial outputs (candidate, 2027-Q1, issued 2026-10-01, admin route `e142-state-lgbm-1.0`)

| Province | P(elevated) | Model-refit range | Class | Last survey | Quarters since | Weight on last survey |
|---|---|---|---|---|---|---|
| Batangas | 0.074 | 0.08–0.39 | LOW | 2015 | 46 | 0.05 |
| Cavite | 0.073 | 0.08–0.73 | UNCERTAIN | 2015 | 46 | 0.05 |
| Laguna | 0.070 | 0.07–0.33 | LOW | 2018 | 34 | 0.10 |
| Quezon | 0.264 | 0.21–0.57 | UNCERTAIN | 2019 | 30 | 0.13 |
| Rizal | 0.231 | 0.12–0.72 | UNCERTAIN | 2019 | 30 | 0.13 |

* **Class rule:**
  * HIGH if P ≥ 0.80 and the whole model-refit range (30 region-bootstrap refits) is ≥ 0.5.
  * LOW if P ≤ 0.20 and the whole range is < 0.5.
  * Otherwise UNCERTAIN.
  * Cavite's point P is low, but its refit range reaches 0.73, so it is shown as UNCERTAIN.
* **Explanations:** exact decomposition = base + TreeSHAP of the structural level by group + the decayed survey-anchor
  term.
  * Poverty contributes −0.19 to −0.46 and geography about −0.24 for every province.
  * Climate is about −0.08; market and history are small.
* **What this shows:** because the surveys are 7–11 years old, the forecast is now mostly structural. The model makes
  that visible rather than hiding it.

## 9. Quarterly forecasting evidence

* **Validated:** survey-to-survey prediction of the next measured round, with change-direction skill
  (ρ 0.44 [0.32, 0.59]). The skill over persistence is not significant.
* **Not identifiable: quarter-to-quarter change.**
  * There is no quarterly provincial measurement.
  * The time-varying indicators add nothing measurable (E138, E140, E141 ablations).
  * The quarterly transition is therefore an assumption applied to multi-year persistence.
* **What would identify it:** a provincial food-insecurity measurement at least every quarter, or at least several
  annual provincial rounds. None exists.

## 10. The five contributor groups

| Group | Provincial features | Evidence | Status |
|---|---|---|---|
| Poverty and social vulnerability | poverty, subsistence, poverty gap, density | largest contribution (E141 ablation +0.020, n.s.; E138 masking +0.042) | model input; structural, not quarterly |
| Market and food prices | food and rice CPI YoY, food-threshold ratio | no incremental information (E138–E141) | model input with no measured value; small contribution shown honestly |
| Climate and agriculture | rainfall z, cyclones, cyclone climatology, palay/corn, fisheries | no incremental information | model input with no measured value |
| Employment and OFW remittances | **none provincial** (OpenSTAT LFS and BSP remittances are national) | not testable | context only |
| News and NLP | FSSI v2 (CALABARZON only) | not testable provincially | context only |

The CH1 price-pressure panel now states, in its existing text fields, that it explains the price-pressure index and
not provincial food-insecurity risk.

## 11. NLP / FSSI

| Property | Result |
|---|---|
| Volume bias | Spearman with article count: raw 0.44, FI6-N shrinkage 0.43, **FSSI v2 0.05** (n.s.). FSSI v2 separates composition from attention (`app/e142/fssi.py`, as-of baselines). |
| Stability by volume tercile | means −0.10 / −0.43 / −0.11, SD 1.2–1.3 |
| Convergent validity | FSSI v2 vs cyclones ρ 0.22 (p < 0.001) |
| Coverage | 344 CALABARZON province-quarters; 95 % one outlet (outlet bias cannot be re-weighted) |
| Sentiment accuracy | not established (no human-labelled set; owner rule) |
| Forecasting contribution | not testable provincially |

## 12. LGU outputs

All 142 LGUs per candidate are an **LGU vulnerability-weighted priority ranking**:
* province P × (½ PSA SAE 2021 poverty percentile + ½ POPCEN 2024 density percentile, region-wide);
* with the model-refit range carried through;
* labelled as not a municipal measurement, status candidate.

## 13. Application changes

* **New:**
  * admin routes `/api/v1/admin/candidates/e142-state-lgbm-1.0/*`;
  * a gated production server entry;
  * catalog and registry entries (e142 rejected).
* **Changed:**
  * the CH1 contributor status notes (backend text only; no UI change);
  * the provincial scorer gains cluster-bootstrap CIs and a pre-stated `confirmed` flag;
  * the shared LGU function `app/e140/issue.lgu_priority` (output identical, verified).
* **Public dashboard:** unchanged. The outlook is `validation_pending`, and candidates are admin-only (owner rule: no
  candidate on the dashboard).

## 14. Tests

| Suite | Result |
|---|---|
| Full backend `tests/unit` | **872 passed**, 0 failed |
| Frontend `tsc --noEmit` | clean |
| Frontend `vitest` | **88 passed** (18 files) |
| E141/E142/system tests, re-run after the final class-rule change | **23 passed** |
| Protocol locks E137–E142 | all verify |

**New tests:** `tests/unit/test_e142.py` (7):
* lock;
* φ identification rules;
* variance growth;
* exact decomposition and class rule;
* FSSI v2 as-of and volume test;
* registry and route;
* CH1 label.

## 15. Thesis objective acceptance

| Objective | Status | Evidence |
|---|---|---|
| 1 NLP (XLM-R + BERTopic, bias-corrected FSSI, province-quarter patterns) | **PARTIALLY ACHIEVED** | Pipeline implemented. FSSI v2 removes volume dependence and keeps convergent validity. Sentiment accuracy unverified; provincial contribution untestable. |
| 2 LightGBM evaluation, walk-forward, furthest reliable horizon | Evaluation **ACHIEVED**; horizon **none validated** | E141/E142 rolling origins; E142 change skill; gate failures as listed |
| 3 LGU rankings from validated province forecasts | **PARTIALLY ACHIEVED** | 142 LGUs complete; province forecast not validated |
| 4 Baselines (persistence, PSA-only, NLP-only, logistic) | **PARTIALLY ACHIEVED** | Persistence, PSA-only and logistic on identical folds; NLP-only not constructible provincially (regional comparison in FI6) |

## 16. Production decision

**CANDIDATE IMPLEMENTED — VALIDATION PENDING.**
* The registry production pointer is `null`.
* E142, the primary candidate, is sealed (`data/e142/out/issue/sealed_prediction_2026-10-01.json`, in the
  register).

## 17. Remaining external dependencies

1. **DOST-FNRI provincial HFIAS after 2019** (2021 ENNS replicate; later NNS), with the fields in
   `DATA_REQUEST_FNRI_PROVINCIAL_HFIAS.md`.
   * Scoring: `python -m app.registry.prospective_provincial score <file>`.
   * Confirmation rule (pre-stated): n ≥ 20; EB below persistence and below the region's previous level, CI < 0;
     AUC ≥ 0.75.
2. **DOST-FNRI 2013 NNS design-based SEs** and **ENNS 2018/2019 fieldwork months by province.**
3. **A quarterly (or at least annual) provincial food-insecurity measure,** for any quarter-to-quarter claim.
   Responsible: PSA/FNRI. None exists today.
4. **Provincial labour or remittance series and national geocoded news** for the survey years. Needed before
   employment and news can be tested as provincial inputs.
