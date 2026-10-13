# E13 Protocol Amendment 1 (frozen before any amendment computation)

## Status

**When it was written:** 2026-10-13 at about 11:05. That is after E13 v1 was completed and its results were seen, and **before any Amendment-1 (A1) analysis was computed.**

**How it is frozen:** its SHA-256 is stored in `runner/PROTOCOL_AMENDMENT_1_SHA256.txt`, and `runner/run_amendment1.py` refuses to run if the hash differs.

**What stays fixed:**

| Item | Status |
|---|---|
| `EXPERIMENT_PROTOCOL.md` | **Unchanged** (frozen 10:24:32, `c379c039…`). It was frozen before the v1 comparison. Editing it now would erase the record of what was decided before the results were seen. |
| `runner/e13_lib.py`, `runner/run_e13.py` | **Unchanged.** E15's frozen prospective protocol pins them by hash. |
| `runs/20261013T022702Z/` | **Unchanged.** It is the sealed v1 record, and E15 reads it. |

**Why A1 exists:** the brief of 2026-10-13 ("Complete the DA-Relevant Prediction Improvement Experiment") asks for analyses that v1 did not contain:

- a target and timing audit;
- trend baselines;
- a fair LightGBM check;
- feature-increment tests;
- prediction intervals;
- stability checks;
- an uncertainty-aware official comparison.

**Status of the results:**

- **All A1 results are post hoc** relative to v1.
- **New candidate models added in A1 cannot be selected.**
- **New baselines can only make the v1 rule stricter.** A v1 candidate must now also beat them.

## 1. Timing classification (details in `TARGET_AND_TIMING_AUDIT.md`)

| Input or target | Timing evidence | Classification |
|---|---|---|
| SWS rounds (Task A target and H_last) | Publication date per round: 18 verified, 3 verified-single | **Established** |
| Provincial F, D, mean5 at quarter T−1 | The quarter's last month ends the day before origin(T), so it cannot be published before the origin | **Certainly unavailable.** Never used. |
| Provincial F, D, mean5 at quarter T−2 | Proxy date (national release + 14 days). Verified only for 2024-Q4. Margin to origin(T) of about 10 weeks. | **Not established.** Every Task B result, and A_ridge_HF, is labelled **exploratory (timing)**. |

**Sensitivity S-T3 (Task B).** Inputs **and** training targets are restricted to quarter T−3 and earlier, which gives a margin of about 5 months.

- **Arms:** the v1 B arms (except the trees) and the A1 baselines.
- **Test quarters:** 2023-Q4..2025-Q4 (9), the first with at least 6 training quarters under this rule.
- **Comparison:** the primary T−2 results on the same 9 quarters.

## 2. Added baselines (training-only)

| Arm | Definition |
|---|---|
| `A_drift` | H_last + g × H_age. g = (H of the last fully published quarter − H of the first fully published quarter) ÷ the number of quarters between them. Only quarters fully published before origin(T) are used. |
| `B1_drift` | F[p,T−2] + 2 × g_p. g_p = (F[p,T−2] − F[p,2021-Q1]) ÷ the number of quarters between them. |

No drift baseline is defined for D. D sums to zero in every quarter, so a province drift would duplicate the province-mean baseline. All other baselines are those of v1:

- carry-forward;
- historical means computed from training data only (`A_mean`, `B1_mean`, `B1_pmean`; `B2_zero`, which equals the pooled training mean of D; `B2_pmean`);
- `B1_regional`.

The S1 origin rule is represented by the carry-forward of its components (`A_cf`, `B2_cf`). It is the only compatible use of the existing indicator.

## 3. Added exploratory candidates (reported only; cannot be selected)

**`B1_lgbm` and `B2_lgbm`:** LightGBM regressors with a fixed configuration and no tuning.

| Setting | Value |
|---|---|
| Features | Those of `B1_ridge_FR` and `B2_ridge_DP` |
| `n_estimators` | 100 |
| `learning_rate` | 0.05 |
| `num_leaves` | 4 |
| `min_child_samples` | 5 |
| `reg_lambda` | 0 |
| `subsample`, `colsample_bytree` | 1 |
| `random_state` | 0 |
| Determinism | `deterministic=True`, `n_jobs=1`, `verbose=-1` |

**What is not added:**

- **No LightGBM for Task A** (6–14 training points).
- **No new autoregressive model.** v1's `A_ridge_H` is the (lightly regularized) AR(1) on the latest published value. Its stationarity assumption is checked descriptively.

## 4. Re-check of the v1 rule with the enlarged baseline set

- **v1 candidates:** v1's four conditions are re-applied with the "best baseline" chosen from the v1 baselines **plus** `A_drift` or `B1_drift`. Same test quarters. The Holm family stays the v1 candidates of each target.
- **LightGBM:** gets the same four conditions, with a Holm family that includes it. It is labelled exploratory and is **not eligible for selection**.
- **Outcome labels:** a v1 candidate that passed v1 but fails here is reported as **not robust to the added baselines**.

## 5. Feature increments (descriptive)

**Nested steps:**

| Target | Steps |
|---|---|
| A | `A_cf` → `A_ridge_H` → `A_ridge_HF` |
| B1 | `B1_cf` → `B1_ridge_F` → `B1_ridge_FR` → `B1_tree` / `B1_lgbm` |
| B2 | `B2_cf` → `B2_ridge_D` → `B2_ridge_DP` → `B2_tree` / `B2_lgbm` |

**Reported for each step:** ΔMAE, the quarter-cluster bootstrap 95% interval (10,000 draws, seed 20261013), and the number of quarters better.

## 6. Prediction intervals (80%, empirical, training-only)

- **Interval:** forecast + [10th, 90th percentile] of the arm's training errors (y − forecast) at that origin.
- **Arms covered:**
  - `A_cf`, `B1_cf`, `B2_cf`: their training errors are genuinely out of sample, because there is no fit.
  - `B2_ridge_D`, `B2_ridge_DP`: in-sample residuals, which are **optimistic**.
- **Reported:** test coverage against the nominal 80%, and the mean width.

## 7. Added secondary events (no quantile thresholds)

| Event | Realized | Predicted |
|---|---|---|
| B1 rising | F[p,T] > F[p,T−2] | forecast > F[p,T−2] |
| B2 rising | D[p,T] > D[p,T−2] | forecast > D[p,T−2] |
| A increase (from v1) | H[T] > H_last | forecast > H_last |

- **Carry-forward cannot predict a rise.** This is reported as degenerate.
- **Metrics:** the confusion matrix, balanced accuracy, and precision and recall by class.

## 8. Stability

- **MAE by half of the test period:**
  - A: the first 4 and last 5 quarters;
  - B: the first 5 and last 6 quarters.
  - Reported: whether each arm's ordering against carry-forward is the same in both halves.
- **Ranking stability:** the mean Kendall τ between consecutive quarters' forecast D rankings, and the same for realized D.

## 9. Regional against provincial signal

- **Correlation of H with regional food inflation:** across quarters, the Pearson and Spearman correlation between quarterly H (all rounds) and mean5 F at lags 0, 1 and 2, with n reported.
- **D carries no regional level:** this is stated by construction, because D sums to zero in each quarter.

## 10. Official outcome comparison (Task C; descriptive only)

1. **CI consistency check:** the reported 95% CI against p ± 1.96 × p × CV/100. A difference of more than 0.15 points is flagged.
2. **Pairwise distinguishability within each year:** z = (p_i − p_j)/√(se_i² + se_j²), with se = p × CV/100. A pair is distinguishable if |z| ≥ 1.96. Independence is assumed and there is no multiplicity adjustment, so this is descriptive.
3. **Concordance:** for the distinguishable pairs, how often the province with higher subsistence incidence also had a higher annual mean D (and mean F) in the same year.
4. **Spearman** (from v1) is restated.
5. **FIES 2025** (regional, one value) is shown beside the SWS 2025 rounds. They are not comparable measures.

**No training, no thresholds and no accuracy claims.** The regional FIES value is never assigned to provinces.

## 11. Order and seal

1. Verify the hashes of this amendment, the v1 protocol and the allowlist.
2. Read the v1 forecasts from the sealed `runs/20261013T022702Z/predictions.csv` (`868581d5…`), checking the hash.
3. Compute the A1 arms (new baselines, LightGBM, S-T3) from data available at each origin.
4. Run the future-perturbation check on every new arm.
5. Write `predictions_a1.csv` and record its hash in `SEAL_A1.json`.
6. Only then join the realized values and compute the metrics.
7. Run twice and confirm identical outputs.

## 12. Claims this amendment can support

| Kind of claim | Status |
|---|---|
| Regional hunger forecasting | Timing established; small sample; previously explored quarters |
| Provincial food-price-pressure forecasting | Exploratory (timing); previously explored quarters |
| Descriptive consistency with official indicators | Descriptive only |
| Actual provincial food-insecurity prediction accuracy | **Not evaluable** |
