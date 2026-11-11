# E185: E184 tuned with a new synthetic generator (Gaussian copula), selected on training folds only. Fixed before results.

Written 2026-11-10 at the owner's request ("improve it more, tune it with synthetic data"). Committed before any E185
output existed.

## Honesty statement
- **What the 72 rows are.** They have been read by every experiment since E151. E185's scores on them are reported
  whatever they are; the target of 80 % is not a criterion.
- **How the setting is chosen.** Only on inner region folds of each outer job's training rows, against E184's setting.
  The 72 rows are used once, at the end.
- **Deployment.** E185 is a candidate; nothing is staged or deployed without the owner's instruction.

## New generator: Gaussian copula (option (b) of the original brief)
For each class (HIGH, LOW) of the rows it is given (one training fold):
1. **Variables.** Every model input column, plus `y_true`, `se_true`, `gap_q` and the three anchors (H, OH, RSS).
2. **Normal scores.** Each variable with at least 3 distinct non-missing values is turned into normal scores
   Φ⁻¹((rank − 0.5) / n). Missing values are scored 0 for the correlation estimate.
3. **Correlation.** The rank-correlation matrix of the normal scores is shrunk toward the identity: Σ = 0.8·R + 0.2·I.
4. **Sampling.** Draws come from N(0, Σ). Each variable is mapped back through its empirical quantiles, so marginals are
   preserved and values stay within the class's observed range. Variables with fewer than 3 distinct values are drawn
   from their empirical distribution.
5. **Missing values, lead and region.** A real "parent" row is drawn from the same class (uniformly, or with the
   boundary weight exp(−|y|/0.5) under the boundary focus). It supplies the missing-value pattern, `lead` and `region`.
6. **Derived values.** `gap_q` is rounded, and q = Φ(y/se).

Class balancing (minority class first), labels (`is_synthetic`, `scenario_id`, `generator_seed`) and "synthetic rows
are never scored" are as in E178–E184.

## Candidate settings (18)
- **Base:** E184's setting: jitter, r = 1, weight 1.0, 0.5 SD, boundary.
- **Copula:** r ∈ {0.5, 1, 2} × weight ∈ {0.5, 1.0} × focus ∈ {uniform, boundary}, which is 12 settings.
- **Jitter (0.5 SD, boundary):** r ∈ {0.5, 2} × weight ∈ {0.5, 1.0}, which is 4 settings.
- **None:** no synthetic rows (E168), recorded for reference.

## Selection (per outer job and generator seed)
- **Stage A.** E168's selection, unchanged.
- **Stage B.** Every setting is scored by region GroupKFold(5) on the training rows: synthetic rows from each fold's
  real training rows, in its fit set only, and weighted logit SSE on the real held-out rows.
- **One-standard-error rule against E184's setting.** A setting is eligible only if its mean per-fold SSE difference
  from E184's setting, plus one standard error, is below 0. The lowest-SSE eligible setting is chosen. If none is
  eligible, **E185 = E184** for that job and seed.
- **Forecast.** E185's forecast is the mean over generator seeds 17901–17905 of the chosen settings' forecasts.

## Evaluation (as E184)
- **Rows and metrics.** The 72 real outer rows at Leads 1, 2 and 3: accuracy, balanced accuracy, HIGH recall and
  precision, macro-F1, AUC, Brier and calibration slope.
- **Comparisons.** Paired region-cluster bootstrap Brier CIs against persistence, E168 and **E184**; exact McNemar tests
  against E184.
- **Controls at Lead 1.** Shuffled triggers (×3) and corrupted unreleased rounds on the main random streams, each a
  five-seed mean.
- **Selection record.** Which setting was chosen per job and seed, and how often copula was chosen.

## Decision (fixed now)
- **Better than E184** only if both hold:
  - the upper bound of the Brier CI against E184 is below 0 at Leads 1, 2 **and** 3;
  - accuracy is ≥ E184's at each lead.
- **Also required:** the owner's deployment rule (≥ 75 % and Brier CI vs persistence < 0 at each lead) and leakage
  below 1e-9.
- **Otherwise:** "the new synthetic generator did not improve E184", and E184 stays the synthetic-data candidate.

## ENNS 2022 seal
- **Construction.** As E184: frames from `app.e168.enns2022_seal`; the E168 part must match its seal.
- **Where.** Written once to `backend/data/e185/out/sealed_enns2022.json`.

## Outputs
- `backend/data/e185/out/` and `docs/e185/REPORT.md`.
