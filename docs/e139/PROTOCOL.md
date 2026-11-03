# E139: final aiPHeed LightGBM food-insecurity RISK system. Protocol E139-P1

**Code and lock.**
* Code: `backend/app/e139/`.
* Lock: `backend/data/e139/out/PROTOCOL_LOCK.json`, holding the sha256 of this file, `model.py`, `evaluate.py` and
  the threshold table.
* The lock is written before any E139 fit on real outcomes. The pre-lock smoke test used shuffled labels.

**Cycle.** One consolidated implementation, one locked tuning-and-validation run, then one final audit. There is no
retuning after the run.

**Earlier experiments are not modified.** E137 and E138 code, locks and results are imported read-only. Every HFIAS
row has been seen before, so all results are **development evidence**. Confirmation will come from the sealed
predictions (E138 `e324433c…`, plus E139's own seal), scored against the next provincial survey round.

## 1. Diagnosis: why earlier LightGBM failed (E137/E138 evidence)

1. **Too few rows for step functions.** 125 rows (62 decisive), while the measured signal is close to linear in
   poverty. Tree-only LightGBM approximated a linear relation with a few stumps. It overfit (E137 gap 0.07–0.08)
   and was the worst indicator model in E138 (LORO AUC 0.69).
2. **Measured history was missing as structured information.** Most of the signal is the region's measured level:
   in E138 the regional base rate under LOPO had AUC 0.96. The only family that beat it was poverty plus a region
   effect (HIER). E137/E138 LightGBM had no feature for the region's previous measured level.
3. **Noise inputs.** Market and climate added no information in any nested test (E138), but they diluted the trees.
4. **The binary label was not the problem.** E137's continuous relative-risk formulation (REL) beat soft-label
   classification. E138's continuous ridge was best under LORO.

## 2. Target (unchanged, E137 audit)

* **Outcome:** measured HFIAS moderate-or-severe food insecurity, as published by FNRI.
* **Rounds:** FNRI 2015 (78 provinces) and ENNS 2018/2019 (pooled national reference).
* **Target value:** continuous relative logit y with its survey SE, weighted by 1/(se² + τ²).
* **Output:** P(elevated) = P(true y > 0) = Φ(ŷ/σ), with σ from inner cross-validation (survey error removed).
* **Why regression, not classification:** it uses the magnitude of every measured row. The 38 NOT_DISTINGUISHABLE and
  25 wide rows inform the fit without being forced into a class. Class metrics use the 62 decisive rows.
* **Excluded:** FIES, SWS, poverty and CPI are never used as labels. No row is interpolated.

## 3. Features

All features are public before the issue date. E137's release rules apply.
* **Poverty and vulnerability:** poverty, subsistence, poverty gap, density.
* **Market:** food CPI YoY, rice CPI YoY, food-threshold ratio.
* **Climate and agriculture:** 6-month rainfall z, cyclones within 150 km (4 quarters), cyclone climatology,
  palay+corn per capita, palay+corn YoY, fisheries YoY.
* **Measured history:**
  * `a_prev_y`: the province's previous measured position;
  * `a_region_prev`: the mean measured position of the region's provinces in the previous survey (FNRI 2015, public
    from 2016; missing for 2015 rows).
* **Not included:**
  * **Employment and news:** no nationally comparable provincial series exists for 2014–2019. They are reported as
    context only.
  * **Identifiers:** no province, region or survey identifier is a feature.

## 4. Primary model: linear-prior LightGBM

1. **Base.** A weighted ridge on poverty + measured history (alpha from {1, 3, 10, 30} by inner grouped CV). Its
   prediction is LightGBM's `init_score`.
2. **Trees.** LightGBM regression on all features. Settings: num_leaves 3, max_depth 2, min_child_samples 15,
   L2 10, learning rate 0.05, row subsample 0.8, feature subsample 0.7.
3. **Number of trees.** Chosen from {0, 30, 100} by inner grouped 5-fold CV (by region) on expected Brier. Zero is
   allowed: if the trees add nothing, the model reports that.
4. **Explanations.** Exact linear terms plus TreeSHAP, summed by group.

## 5. References (same rows and folds)

* **Linear models:** RR-F (ridge, all features), LR-F (logistic, all), RR-P, LR-P (poverty only), HIER-P (E138).
* **Base rates and history:** NAT (national), REG (same-survey regional base rate, LOPO only), REGPREV (the region's
  previous measured level), PERS (the province's previous level).

## 6. Schemes

| Scheme | What it tests |
|---|---|
| LORO | unseen region (primary geographic test) |
| LOPO | unseen province |
| ISLAND | unseen island group |
| V2 | train 2015 → predict ENNS |
| **TFWD** | train 2015 + ENNS 2018 → predict ENNS 2019 (strictly forward in time) |

* **Bootstrap:** cluster bootstrap by region, 1,000 replicates.
* **Metrics:** expected Brier score, Brier skill vs climatology, ROC-AUC, PR-AUC, accuracy with Wilson CI, balanced
  accuracy, recall/precision for elevated, ECE, training gap.

## 7. Acceptance gate (thresholds in `evaluate.THRESHOLDS`)

**Lead-dependent checks.** Each is evaluated at Leads 0–4. Lead k means features are frozen k quarters before the
target survey's reference quarter.

| Check | Rule |
|---|---|
| G1 | LORO: beats NAT. 95 % CI upper bound of the expected Brier difference < 0. |
| G2 | **Beyond region.** On ENNS rows (LORO), beats REGPREV with CI upper bound < 0. |
| G3 | On ENNS rows, non-inferior to PERS: CI upper bound ≤ +0.02. |
| G5 | LORO AUC ≥ 0.75 with CI lower bound ≥ 0.60; balanced accuracy ≥ 0.70; recall ≥ 0.60; precision ≥ 0.60. |
| G6 | ECE ≤ 0.10. |
| G9 | TFWD AUC ≥ 0.70. |

**Lead-independent checks.**

| Check | Rule |
|---|---|
| G4 | Not worse than the best linear benchmark: LORO EB difference ≤ its bootstrap SE. |
| G7 | Overfitting gap ≤ 0.05. |
| G8 | ISLAND AUC ≥ 0.65. |
| G10 | Sensitivity (any-level outcome; round reference): AUC ≥ 0.70. |
| G11 | Masking market, climate or history at prediction time changes EB by ≤ 0.02. |

**Ablation.** Each group is removed from both the base and the trees, and reported for LORO and TFWD. A group
"contributes" only if removing it worsens EB with a CI that excludes 0.

**Maximum reliable lead.** The largest k such that all lead-dependent checks pass at k and at every lower lead, and
all lead-independent checks pass. Two caveats:
* The prediction target is the **next survey measurement** (survey-to-survey), not a quarterly change.
* Leads at which only unchanged structural features differ are not presented as quarterly forecasting skill.

**The 75 % objective.** Reported honestly as LORO accuracy on decisive rows, with a Wilson CI. It is not a
selection criterion.

**Decision.**
* All checks pass at Lead 0 → **APPROVED-PROVISIONAL** (development evidence; confirmatory test pending). The
  dashboard may then show only:
  * the structural risk estimate with its uncertainty;
  * the validated lead;
  * the municipal vulnerability ranking, labelled as vulnerability.

  Promotion also needs owner approval in the registry.
* Otherwise → **REJECTED**. The dashboard stays as it is, and candidate outputs are available on admin routes only.
