# E191: exhaustive synthetic-data search for E184 with fully nested selection. Fixed before any E191 output.

Written 2026-11-10 at the owner's request ("just do all of it continuously"). **Local only.** Not committed, not
pushed. The SHA-256 of this file is logged before the run.

## Principle
The 72 outer rows per lead have been used since E151. Choosing among about 50 configurations on them would almost
certainly produce a lucky winner, so:
- **Every choice is made per outer job, inside that job's own training rows.** This covers which generators to
  expand, which ratio, which combination, which model and the final pipeline.
- **Scoring is on the real-row inner out-of-fold forecasts only.** They come from region GroupKFold(5) and are scored
  by weighted SSE, the same score E168/E184 use.
- **The outer rows are touched once,** after all selections. Each configuration's outer score is also reported
  descriptively, with multiplicity adjustment.

## Fixed parts (exactly E184)
- **Frames.** `RT.build` (E168's task up to `run_proc`).
- **Selection.** E168 Stage A for anchor, feature set, pruning and HPO, on real rows.
- **Calibration and synthetic rows.**
  - `RT._calibrate`, with its three layers, on real inner OOF.
  - Synthetic rows are generated per inner fold and for the final fit, from that fold's or job's training rows only.
- **Draws.** Generator seeds 17901–17905; stochastic generators are averaged over the 5 draws.
- **Reproduction checks:**
  - configuration `none` must equal E168;
  - configuration `e184` must equal the stored E184 rows (maximum |Δp| = 0).
- **Leads.** Training rows are identical across some leads (the same released rounds). Leads with identical training
  frames are run as one job, with their test rows stacked. All calibration steps are row-wise.

## Stage 2: generators (each at 50/50, weight 1.0, unless stated)
| Family | Configuration | Definition |
|---|---|---|
| Baselines | `none` | Real rows only (= E168) |
| | `e184` | E184's jitter: inputs ± 0.5 SD, y + N(0, se), boundary focus, minority-first allocation |
| Bootstrap | `boot_row` | Uniform row bootstrap (exact copies) |
| | `boot_class` | Class-conditional bootstrap with E184's allocation (random oversampling) |
| | `boot_prov` | Province-cluster bootstrap: whole provinces (all their rounds and snapshots) resampled |
| | `undersample` | No synthetic rows; majority-class real rows randomly dropped from the fit set to parity |
| Minority (imbalanced-learn 0.14) | `smote` | E178 SMOTE (same class and lead) |
| | `bsmote` | Borderline-SMOTE-1 |
| | `adasyn` | ADASYN |
| | `svmsmote` | SVM-SMOTE |
| | `kmsmote` | KMeans-SMOTE |
| | | The imbalanced-learn methods work on standardized, median-imputed continuous inputs, y, se, gap_q and the anchors. Discrete inputs, lead, region and the missing-value pattern come from the nearest real row of the same class. |
| Multivariate | `gauss` | Per-class multivariate normal (Ledoit-Wolf covariance) |
| | `kde` | Per-class Gaussian KDE (smoothed bootstrap, Scott bandwidth) |
| | `gmm` | Per-class Gaussian mixture (diagonal, k = 1–3 by BIC) |
| | `copula` | E185 class-conditional Gaussian copula |
| | `vae` | Conditional VAE pilot (PyTorch; latent 4, hidden 32, 300 epochs) |
| Temporal | `traj` | Trajectory-consistent jitter: one province-round (all its lead snapshots) gets one shared input-noise vector and one shared outcome draw |
| Feature space | `mixup` | Within class, same lead, same island; λ ~ Beta(0.4, 0.4) |
| | `corrnoise` | Correlation-preserving noise: N(0, 0.25 Σ_class) in standardized space, then y + N(0, se) |
| Boundary | `hard` | Jitter with parents weighted by the in-sample residual of the real-only E168-configured model |
| Weighting | `classw` | No synthetic rows; balanced class weights |
| | `hybrid` | E184 synthetic rows plus balanced class weights |

- **Rejected without running:**
  - CTGAN: 156–532 rows are too few to train a GAN stably.
  - Block, circular and stationary bootstrap: each province has at most 4 survey-to-survey changes.
  - Focal loss: the model is a regression on the change.
  - SMOTENC: there are no categorical inputs.
  - XGBoost: replaced by CatBoost, which is installed.

## Stage 3: ratios
- **Which generators.** The 3 best Stage-2 generators by inner SSE, per job, among those with a ratio.
- **Ratios.** r ∈ {0.111, 0.25, 0.429, 0.667, 1.5, 2.333, 4}, which is 10, 20, 30, 40, 60, 70 and 80 % synthetic.
  50 % is already in Stage 2.

## Stage 4: combinations
- Every pair of the 3 Stage-3 generators.
- Each pair is used at the better of the two generators' best ratios, with half the synthetic rows from each.

## Stage 5: model interaction
- **Configuration.** The best configuration so far (inner SSE).
- **Models.** Refitted with ridge (alpha ∈ {1, 10, 100}), random forest (min leaf ∈ {5, 20}) and CatBoost
  (depth ∈ {4, 6}, 400 iterations, learning rate 0.03).
- **Settings.** Each model's setting is chosen by real-only inner SSE on E168's selected anchor, feature set and
  pruning.

## Stage 6: final selection per job
- **E191.** Pick the configuration with the lowest inner SSE across Stages 2–5. Prefer it to `e184` only if its
  improvement exceeds one region-cluster standard error of the paired difference (the one-SE rule). Otherwise keep
  `e184`.
- **E191_min.** The pure minimum, reported as a secondary arm.
- **Family-best arms (nested).** The lowest inner SSE within each family, per job.

## Evaluation
- **Rows.** 72 real outer rows per lead (Leads 1–3; E191 also at Leads 4–6).
- **Metrics:**
  - accuracy (Wilson CI), balanced accuracy, precision, recall, specificity, F1, false positives, false negatives;
  - Brier, ROC-AUC, PR-AUC;
  - calibration intercept and slope, and confusion matrices;
  - results by round, and per-seed results for E191.
- **Comparisons with E184:**
  - exact McNemar, Holm-adjusted over the three leads;
  - Brier difference with a 2,000-draw region-cluster CI.
  - Descriptive Stage-2 generators are Benjamini–Hochberg adjusted.
- **Controls:**
  - Leakage: the corrupted-unreleased frames must equal the main frames exactly.
  - Shuffled triggers (shuf1–3) at Lead 1 for E191's selected configuration.
- **Synthetic-data quality** (final fit, seed 17901): median KS, maximum standardized Wasserstein, Spearman-correlation
  drift, exact duplicates, near-duplicates (< 0.05 × the median real nearest-neighbour distance), synthetic and
  combined HIGH share, and class flips.

## Decision
- **E191 replaces E184 only if both hold:**
  - at Leads 1–3, accuracy ≥ E184's, Brier ≤ E184's + 0.002, balanced accuracy ≥ E184's − 0.02 and false alarms
    ≤ E184's;
  - at least one lead has a Holm-adjusted McNemar p < 0.05, or a Brier CI entirely below 0.
- **80 % target.** Reported separately.
- **Scope.** Nothing is staged or deployed.
