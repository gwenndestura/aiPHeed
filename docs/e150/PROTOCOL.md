# E150: survey-anchored forecasting and calibrated risk scoring. Protocol E150-P1

Locked before any E150 metric is computed: `backend/data/e150/out/PROTOCOL_LOCK.json`. E147, E148 and E149 are preserved.

## 1. Fixed requirements

Five provinces; LightGBM primary; quarterly; Lead 1 = next calendar quarter; HIGH ≥ 50 %, LOW below 50 % (panel-approved); 142 LGU rankings. The measure stays any-level HFIAS, the corresponding measure of E148 and E149. **The panel's confirmation of that measure is still open.**

## 2. Evidence status

| Evidence | Status | Use |
|---|---|---|
| HFIAS 2013, 2015, 2018, 2019 | Seen | Training; development test on 2018 and 2019 |
| HFIAS 2021, 25 provinces | **Opened by E148 and E149. Never untouched** | Retrospective evaluation only; never for selection |
| HFIAS 2021, 12 other areas | **Unopened** (Bacolod, Batanes, Cebu City, Cotabato City, General Santos, Iligan, Lucena, Muntinlupa, Navotas, Pasay, Pasig, Valenzuela) | **Designated holdout, scored once after sealing** |
| Next FNRI and SWS releases | Future | Prospective: Q1 2027 forecast sealed by hash |

**Holdout limit, stated now.** These are mostly cities, without their own earlier surveys or provincial inputs. They test the shared level and structural placement, and they cannot test provincial differentiation or quarterly movement.

## 3. Candidates

**Approach A, prevalence** (`app/e150/model.py`):

| Arm | Definition |
|---|---|
| A-H | Shared level + cross-fitted LightGBM structural level + measurement-error-shrunk deviation |
| A-Hh | A-H + loading × SWS-learned quarterly response on province inputs |
| **A-G** | A-H + LightGBM residual on survey errors, monotone by theory, on all five groups + response signal; may learn no residual |
| A-GN | A-G + news v2 |
| A-frozen | A-G with quarterly inputs held at the anchor's release quarter |

**Approach B, risk score:** LightGBM classifier on the five groups, anchor and response signal, Platt-calibrated in region-grouped folds. Score = 100 × P(p ≥ 50).

**Baselines:** naive persistence, drift, always-HIGH, always-LOW, PSA-only logistic, NLP-only logistic, all-inputs logistic, and stored E147 and E149.

Settings are the fixed values in code, and no setting is tuned on any test row. At each issue date only released outcomes are used (reference quarter + 6 ≤ issue quarter).

## 4. Selection, on 2018 and 2019 only

**Primary arm:** lowest pooled lead 1 to 4 Brier among A-H, A-Hh and A-G. Ties within 0.001 go to A-G.

**News:** A-GN replaces the primary only if its lead 1 Brier difference has a 95 % region-bootstrap interval below 0.

**A or B:** A is a *prevalence* estimate only if, on development rows at lead 1, the calibration slope of measured on predicted logit has an interval including 1 and 90 % interval coverage lies in 0.80 to 0.98. Otherwise A's percentages are reported as a modelled estimate and classification uses B if B's Brier interval against A is below 0.

## 5. Gates, cumulative by lead

Computed on the retrospective pool (2018, 2019, 2021) and also on 2021 alone. Both are reported, and a lead is reliable only if the pool passes.

| Gate | Requirement |
|---|---|
| R1 | Accuracy ≥ 0.75 |
| R2 | AUC ≥ 0.70, region-bootstrap lower bound > 0.50 |
| R3 | HIGH recall and precision ≥ 0.50 |
| R4 | Brier below persistence, 95 % interval below 0 |
| R5 | ECE no higher than the 95th percentile under perfect calibration |
| R6 | Predicted and measured change correlate, lower bound > 0 |
| R7 | Accuracy above always-HIGH and always-LOW |
| R8 | LOW recall ≥ 0.50 |
| R9 | 90 % interval coverage 0.80 to 0.98 |

**Maximum reliable lead:** the largest h with every lead to h passing; 0 if lead 1 fails.

**System gates:** R1 to R9 at lead 1; quarterly response beats the SWS mean-reversion model on a held-out area (lead 1 interval below 0); A-Hh or A-G beats A-frozen on the pool; provincial differentiation (at least 2 of 10 province pairs separated beyond their standard errors); news claim (lead 1 Holm pass and placebo ≤ 5 %); holdout accuracy above always-majority; trigger groups disclosed by actual use.

## 6. Holdout rule

Issued as of 2021-04-01 using only rounds released by then (no 2021 row, including the 25 opened provinces).

* **City:** shared level + parent province's estimate + average city offset from released city rows.
* **NCR city:** shared level + mean relative position of released NCR rows.
* **Batanes:** shared level + its own 2013 and 2015 rows, shrunk.

σ comes from leave-one-out errors on released city rows. Baseline: shared level alone, the latest national level, and always-majority of the released rows. Predictions are hashed and committed before the labels are read.

## 7. Prohibited

No threshold change; no tuning on test rows; no 2021 row used for selection; no estimated label in training; no claim of news value without passing section 5.

## Deviation D1 (2026-11-05, fix-only)

The first holdout seal crashed on an indexing error before producing any prediction or reading any holdout label. One line changed in `seal_holdout`. The development results were already computed and are unaffected. Earlier lock: `PROTOCOL_LOCK_before_d1.json`.
