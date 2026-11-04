# E142: survey-anchored provincial risk-state model. Protocol E142-P1

**Code and lock.**
* Code: `backend/app/e142/` (`model.py`, `evaluate.py`).
* Lock: `backend/data/e142/out/PROTOCOL_LOCK.json`, written before scoring. The pre-lock smoke test used shuffled
  labels only.
* E137–E141 are imported unchanged. The rows, folds, Lead-1 features and metrics are E141's.

## 1. Why this model (from the E141 audit, computed on E141's locked out-of-fold predictions)

* **Real change exists.** 41 of 125 target rows (33 %) changed beyond survey error between rounds (16 up, 25 down).
  Only 2 of 26 provinces that were decisive in both rounds changed class.
* **The models already predict change, through mean reversion.** Each model's predicted change against persistence
  correlates with the measured change: E141 LightGBM ρ 0.39, linear prior 0.41, region's previous level 0.25. The
  signal is regression toward a structural level.
* **The E141 models used this implicitly, with no explicit uncertainty model.**
  * Persistence ignores the structural pull.
  * The structural models ignore how stale the last survey is.
  * E141 LightGBM was underconfident at the top on 2013 (predicted 0.47–0.86 where soft labels were 0.63–0.99).

## 2. Model (`model.py`)

* **State:** the province's true relative logit in a quarter.
* **Observation:** each HFIAS round, with its survey SE.
* **Transition:** AR(1) toward the structural level mu(x).
  * The quarterly persistence φ and the stationary deviation variance τ² are estimated by method of moments.
  * **Only measured survey transitions in the training set are used**, so independent survey errors do not bias the
    cross-product.
  * **φ is not identified without a transition in training.** In origin O1 (training = 2013 only), φ = 0 and the
    model is structural only.
* **Structural level mu(x):**
  * STATE-LGBM (primary): E140 LGBM-AUTO without the measured-history group.
  * STATE-RIDGE (reference): ridge without history.
  * mu is out-of-fold for every training deviation.
* **Forecast** for a target h quarters after the last survey:
  * point: mu(x) + φ^h × filtered deviation;
  * variance: φ^(2h) P0 + τ²(1 − φ^(2h));
  * P(elevated) = Φ(ŷ/√V).
  * The variance grows with time since the last survey. There is no separate calibrator.
* **Calibration comparison:** LGBM-PLATT, the E141 LightGBM plus a Platt calibrator fitted on inner out-of-fold
  predictions of the training rows only.

**Assumption, stated.** Only multi-year survey gaps are observed: 8, 12 and 16 quarters. The *quarterly* form of the
transition (one φ per quarter) is an assumption. The data identify only the multi-year persistence.

## 3. Tests (identical to E141 R)

* **Rolling origins O1–O3**, Lead 1, 125 target rows. References: every E141 model.
* **Change test:** Spearman(predicted logit − persistence logit, measured change), region-bootstrap CI.
* **Untouched 2013:** structural level only, because 2013 has no earlier round.
* **Timing sensitivity:** the reference-quarter assumption (ENNS fieldwork months are not printed) is shifted by
  re-running at Lead 0 and Lead 3. Reported only.

## 4. Pre-registered gate (STATE-LGBM)

| Check | Rule |
|---|---|
| S1 | Beats persistence: EB 95 % CI upper bound < 0 (pooled) |
| S2 | Beats the region's previous level: CI upper bound < 0 |
| S3 | ECE ≤ 0.10, both pooled and on the untouched 2013 round |
| S4 | AUC ≥ 0.75, HIGH recall ≥ 0.60, precision ≥ 0.60 |
| S5 | Predicts change: change-ρ 95 % CI lower bound > 0 |
| S6 | EB below persistence at O2 and at O3 |
| S7 | The LightGBM level is not worse than the ridge level by more than one bootstrap SE |

**Decision.**
* All pass → **survey-to-survey provincial forecast validated (development evidence)**, with the quarterly
  transition stated as an assumption.
* Otherwise → the candidate is sealed for the next measured round.

In either case, quarter-to-quarter change is **not** validated, because no quarterly provincial measurement exists.
