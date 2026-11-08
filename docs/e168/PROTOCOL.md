# E168: LightGBM-only nested procedure. Fixed before results.

Written 2026-11-06. **Owner requirement:** the final predictive model must be LightGBM.

## Honesty statement
- The 72 outer rows (2018, 2019, 2021) have been read in E151–E167.
- The diagnosis (`docs/e166/C1_C4_ANALYSIS.md`) found C4 driven by round-level shifts that the training data at the 2018/2019 origins could not contain.
- **This run tests whether a LightGBM-only procedure, with every choice made on training rows, does better. It is run once; the result is reported whatever it is.**

## Structure: baseline plus change
- **Survey baseline (anchor):** a fixed statistical component chosen by inner selection from:
  - **H:** E158's Hier2 anchor;
  - **OH:** own survey history, shrunk;
  - **RSS:** relative state space.
- **LightGBM** predicts the change e = y_true − baseline. **LightGBM is the only learned predictive model.**
- **The calibration layer** converts LightGBM's forecast into P(HIGH).

## LightGBM search (inner selection only)
| Setting | Values |
|---|---|
| `num_leaves` | {3, 7} (with `max_depth` = −1, capped by leaves) |
| `min_child_samples` | {10, 40} |
| `reg_lambda` | {5, 20} |
| `n_estimators` | {150, 400} |
| Fixed | `learning_rate` 0.02, `feature_fraction` 0.8, `bagging_fraction` 0.8, `bagging_freq` 1, `min_split_gain` 0, `reg_alpha` 0, monotone constraints from `Pv.SIGN`, sample weight 1/(se² + 0.05), seed 168 |
| Feature sets | {GOV, FULL} (E151 columns; GOV = without news) × {without, with regional consumption}. Each set also has a **training-fold-only** pruning option: drop columns whose absolute Spearman correlation with an earlier-listed column exceeds 0.95 in the training rows |
| Class weighting | **None.** HIGH ≥ 50 is a definition, and HIGH recall was already 0.84–0.92. Weighting would only trade false alarms for recall |
| Threshold | P(HIGH) ≥ 0.5, fixed |

- **Inner validation:** region GroupKFold(5) on training rows. The score is weighted logit SSE, which picks the anchor, feature set and LightGBM parameters.
- **Calibration layer:** {raw, linear, Platt (soft, L2)}, each cross-fitted on the inner out-of-fold LightGBM forecasts. The primary layer is the one with the lowest inner Brier. **All three are also reported on the outer rows, descriptively, for comparison.**
- **Isotonic and hierarchical (round-pooled) calibration: not run.** There are 1 to 3 training rounds and about 46 effective rows, so they are not estimable.

## Validation and controls
- **Outer:** chronological, ENNS2018, 2019 and 2021 at Leads 1 and 2. Longer leads only if Lead 1 passes.
- **Controls at Lead 1:**
  - all trigger inputs shuffled across provinces (seeds 1–3);
  - unreleased-round corruption (leakage).
- **Trigger-group ablation:** on the frozen selected configuration, drop each group, at Lead 1.

## Acceptance (unchanged definitions)
**ACCEPT** requires all of:
1. **E156 C1–C6 at Lead 1** (official C4 = logit-level slope).
2. **Leakage** change < 1e-9.
3. **Real − shuffled Brier** interval entirely below 0.
4. **Non-inferior to E158:** Brier difference CI upper bound < +0.02.

Outcomes:
- **IMPROVED BUT NOT ACCEPTED:** better than E158 on point estimates but fails any of these.
- **INSUFFICIENT EVIDENCE:** fails C1 or C4 because of sample or round limits.
- **E158 stays in production** unless the result is ACCEPT.
