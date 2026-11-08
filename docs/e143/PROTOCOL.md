# E143: cross-fitted, survey-anchored provincial risk models. Protocol E143-P1

Locked before any E143 candidate is scored (`data/e143/out/PROTOCOL_LOCK.json`). E137–E142 are not modified.

## 1. What the E142 audit found (`python -m app.e143.audit`, `data/e143/out/audit.json`)

**The anchor was computed from in-sample residuals.**
* E142 estimated φ and τ² from out-of-fold deviations.
* Its forecasts, however, computed the last-survey deviation y_prev − μ(x_prev) with the full-training level μ.
* That level had already been fitted on the province's own previous row.
* Training-only check: the in-sample deviation variance is 0.15–0.17. The out-of-fold variance is 0.24–0.31. The level absorbs about 40 % of each province's own deviation.
* At O2 and O3, E142's anchor therefore added nothing: φ = 0 scores better than the fitted φ in both origins.

**The AR(1) (Markov) transition is contradicted by the measured rounds.**
* Deviation correlations by gap:

  | Gap (quarters) | 8 | 12 | 16 | 20 | 24 |
  |---|---|---|---|---|---|
  | Correlation | 0.61 | 0.61 | 0.35 | 0.67 | 0.53 |

* Under AR(1), corr(2013, 2018) = corr(2013, 2015) × corr(2015, 2018) = 0.37. The measured value is 0.67, and 2013→2019 shows the same excess.
* A permanent province component fits better than exponential decay (weighted SSE 1.38 permanent+AR, 1.62 constant, 3.43 AR(1)).
* The live 2027-Q1 forecasts extrapolate AR(1) to 30–46 quarters, beyond any observed gap (maximum 24). That extrapolation sets the weight on the last survey to 0.05–0.13. A permanent component implies about 0.5.

**Other audit findings.**
* **O1:** a model trained on 2013 alone cannot estimate any persistence. O1 holds 78 of the 125 rows, and its structural-only forecast is worse than persistence (+0.008) and the region's previous level (+0.009).
* **Power:** the minimum detectable difference vs persistence is 0.034 (80 % power). The observed −0.014 would need about 5.8 times the current evidence.
* **Noise:** 40 % of the variance of measured between-round change is survey error. The noise floor of expected Brier (EB) is 0.072 of the 0.193.
* **Reference quarter:** shifting the ENNS reference quarter by ±2 changes φ by at most 0.005 and the O3 EB by at most 0.001.
* **Features:** no between-round feature change tracks the measured change robustly. Of 12 tests, 3 are nominally non-zero, about 0.6 is expected by chance, and the signs are inconsistent.

## 2. Hypothesis

A survey-anchored forecast whose structural level never saw the target province's region (cross-fitted), and whose anchor uses honest out-of-fold deviations, forecasts the next measured round better than persistence and the region's previous level. The tested anchor forms are AR(1), a permanent province effect, and a hierarchical region + province effect.

## 3. Target, rows, folds, cutoffs (identical to E141/E142)

* **Target:** HFIAS moderate-or-severe relative logit vs the same-round national value, with soft label q = Φ(y/se).
* **Rows and folds:** E141 panel at Lead 1. The rolling origins are:

  | Origin | Train | Predict | Rows |
  |---|---|---|---|
  | O1 | NNS2013 | FNRI2015 | 78 |
  | O2 | 2013 + 2015 | ENNS2018 | 22 |
  | O3 | 2013 + 2015 + 2018 | ENNS2019 | 25 |

* **Untouched round:** NNS 2013 (78 rows). The training rows are E140's (2015/2018/2019). No anchor is used there, because every other round is later than 2013.
* **No new feature or outcome source** is used.

## 4. Candidates (all share the E142 level learners; nothing is tuned on targets)

**Cross-fitted level μ̃ (all four candidates).**
* For any province, the level comes from the fold model whose training excluded that province's region: GroupKFold(5) by region inside the training set.
* A region absent from training uses the full model.
* Training deviations d = y − μ̃ are out-of-fold. Target deviations are relative to the same fold model.
* τ² = mean(d² − se²), with a floor of 0.01. It includes the level's out-of-sample error.

**C1 STATE-LGBM-X**
* E142's AR(1) form and φ estimator, with μ̃ and an out-of-fold last-survey deviation.

**C2 RE-LGBM-X (random effects, permanent province component)**
* d = a_p + b_t + e. The permanent component a_p has variance σ_A² = c·τ². The round shocks b_t are independent, with σ_b² = τ² − σ_A².
* c = mean over same-province, different-round training pairs of d_i·d_j, divided by τ², clipped to [0, 1].
* The forecast is the best linear unbiased predictor (BLUP) of the target deviation from **all** of the province's earlier measured rounds, each with its own survey error. Variance = τ² − (explained part).
* Not identified without a different-round training pair (O1): structural level only.

**C3 RE-RIDGE-X**
* C2 with the ridge level. This establishes LightGBM's contribution.

**C4 HRE-LGBM-X (hierarchical)**
* d = g_r + a_p + b_t + e, with σ_g² from different-province, different-round training pairs in the same region, clipped to [0, σ_A²].
* The BLUP uses the province's own earlier rounds and its region's other provinces' earlier rounds.

**Probability and interval (all candidates).**
* P(elevated) = Φ(ŷ / √V).
* The 90 % predictive interval of the measured relative logit is ŷ ± 1.645·√(V + se²).

**References** (read from the locked E142 out-of-fold files, same rows):

| Reference | Description |
|---|---|
| E142 STATE-LGBM | the E142 candidate |
| E141 LGBM | E141 LightGBM |
| linear prior | |
| ridge | |
| logistic | |
| PSA-only | |
| persistence (PERS) | |
| region's previous level (REGPREV) | |
| national base rate (NAT) | |

NLP-only is not possible: there is no provincial news series outside CALABARZON.

## 5. Metrics and uncertainty

* **Metrics:** expected Brier (primary), AUC with cluster-bootstrap CI, accuracy, HIGH recall, precision, F1, confusion matrix, ECE, change ρ, 90 % interval coverage, per-origin results and CALABARZON rows.
* **Inference:** cluster bootstrap by region, 2000 resamples.
* **Multiplicity:** four new candidates. S1/S2 use **Holm-adjusted** intervals. The best candidate is judged at the 98.75 % interval (α = 0.05/4), the second at 98.33 %, and so on.

## 6. Gate (thresholds identical to E142; S8 added; nothing relaxed)

| Check | Rule |
|---|---|
| S1 | Holm-adjusted CI upper bound of ΔEB vs PERS < 0 |
| S2 | Holm-adjusted CI upper bound of ΔEB vs REGPREV < 0 |
| S3 | pooled ECE ≤ 0.10 and untouched-2013 ECE ≤ 0.10 |
| S4 | AUC ≥ 0.75, HIGH recall ≥ 0.60, precision ≥ 0.60 |
| S5 | change-ρ 95 % CI lower bound > 0 |
| S6 | EB below PERS at O2 and at O3 |
| S7 | for LightGBM-level candidates: ΔEB vs C3 (ridge level) ≤ its bootstrap SE |
| S8 | 90 % predictive-interval coverage of the measured relative logit in [0.80, 0.98] |

**Adoption.**
* All checks must pass.
* If several candidates pass, the preference is: fewest variance parameters (C1 = C2 = C3 < C4), then LightGBM level, then pooled EB.
* A pass means **development evidence on folds that E141, E142 and this audit have already examined**. It is not a validated forecast. It is reported as "development-supported candidate". Validation requires an unseen provincial round, scored by the prospective register's confirmation rule.
* **The production pointer is never changed by E143.**

**Issue.**
* The adopted candidate is issued for the dashboard's display quarter (admin routes, sealed). If none is adopted, C2 is issued as the E143 candidate.
* C1, C3 and C4 are shown as model-selection spread.
* The uncertainty is decomposed into: survey error of the anchoring rounds, permanent-effect estimation, transitory shock, structural-level error (in τ²), parameter uncertainty (30 region-bootstrap refits), and transition-form uncertainty (AR(1) vs permanent).
