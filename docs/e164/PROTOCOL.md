# E164: nested automatic model selection. Protocol and acceptance gates fixed before results.

Written 2026-11-06.

## Why this experiment is different
In E151–E163, **every adoption decision was made by the analyst after seeing the 72 test rows.** Here the whole choice is made by a fixed procedure, **AUTO**, using only the training rows available at each forecast issue date:
- the anchor;
- the learner;
- the feature set;
- the calibration.

The outer test rows are never used for selection. The score of AUTO is therefore the score of the complete selection procedure.

## Honesty statement
- The outer rows (2018, 2019 and 2021) have been read by earlier work, and **the candidate menu below was designed knowing those results.** That residual optimism cannot be removed.
- **No untouched final holdout exists.** The 2027 seal is the only independent test.

## Outer validation (chronological, unchanged)
- Targets ENNS2018, ENNS2019 and ENNS2021 at Leads 1–4. Lead 1 is primary.
- **Training rows** are the E158 as-of error rows from released rounds only (RQ + 6 ≤ issue).
- At the 2018 and 2019 issues only 2013 and 2015 are released, so training holds one target round (2015). At 2021, training holds 2015, 2018 and 2019.

## Inner validation (training rows only)
- **Region GroupKFold (5 folds)** inside the training rows. Inner validation by survey round is impossible at the 2018 and 2019 issues, which have one training round.
- For anchor-only configurations, the inner prediction is the anchor itself, which is already an as-of forecast.
- Scaling, median and sd, and hyperparameters are fitted inside each inner training fold.

## Menu (fixed)
**Anchors:**
- **H:** E158's Hier2 anchor.
- **RP:** latest survey shifted by the change in the national level.
- **OH:** own history, shrunk.
- **RSS:** E163 C1.

**Residual learners on e = y − anchor (logit), weighted by 1/(se² + 0.05):**
| Learner | Settings |
|---|---|
| NONE | |
| RIDGE | alpha {1, 10, 100, 1000} |
| ENET | ElasticNet, l1_ratio 0.5, alpha {0.001, 0.01, 0.1} |
| RF | 300 trees, max_depth 3, min_samples_leaf 20, max_features 0.3, seed 164 |
| LGBM | `Res2`, the E158 settings with its own inner tree grid |

Every learner's internal grid is chosen by inner folds.

**Feature sets:**
- **GOV:** the five-group official columns plus `gap_q` and `lead`, with no news.
- **FULL:** `E158.COLS`, including news inside the groups.

**Calibration:**
- identity; or
- linear y ≈ a + b·mu, fitted on the inner out-of-fold predictions of the chosen configuration and used only if it lowers the inner weighted SSE.

The intercept can absorb the drift of the national level between rounds, which is a known source of bias.

**Selection score:** inner weighted SSE of y_true on the logit scale. The lowest score wins. This gives 4 anchors × (1 + 4 learners × 2 feature sets) = 36 configurations, each with 2 calibrations.

**Probability:** `Φ(mu/sd)`. sd is a function of `gap_q`, fitted on the inner out-of-fold errors of the chosen configuration (the `Res2.scale` method, with a conformal 90 % interval). **HIGH = mu ≥ 0, that is, 50 %, unchanged.**

## Controls
1. **AUTO-SHUF:** the whole procedure with all five-group and news inputs shuffled across provinces within survey-lead, in both training and test. Seeds 1–3, Lead 1.
2. **AUTO-NONEWS:** the procedure restricted to the GOV feature set and anchor-only configurations. **AUTO-NEWSONLY:** anchors + news columns only. Both at Lead 1.
3. **Leakage:** unreleased-round `y` set to random values. AUTO must change by < 1e-9 at Lead 1.
4. **Fixed configurations:** the outer result of each configuration (anchor × learner × feature set, identity calibration) is reported **descriptively and never used for selection.**

## Baselines in the comparison
- **Always-LOW:** probability = the training base rate, class LOW.
- **PERS** (persistence).
- **H anchor only** (E151 ANCHOR).
- **RP, RSS.**
- **E158.**

## Measures (Lead 1, and Leads 2–4 for the horizon)
- **Class:** accuracy, balanced accuracy, HIGH and LOW precision and recall, F1, ROC-AUC, PR-AUC, Brier.
- **Calibration:** slope and intercept (y_true on mu), and the reliability table (5 probability bins).
- **Error:** MAE in points, false-alarm rate, missed-HIGH rate.
- **Ranking:** within-region concordance, Spearman and Kendall (E162 code).
- **Lead reliability:** E156 C1–C6 and the maximum reliable lead.
- **Bias:** by island, observed class and CALABARZON row.

## Acceptance gates for AUTO over E158 (Lead 1)
| ID | Gate |
|---|---|
| A1 | Brier ≤ E158's 0.1344, and the interval of AUTO − E158 is not entirely above 0 |
| A2 | AUTO − AUTO-SHUF Brier interval is not entirely above 0. Real inputs must not be worse than shuffled ones. **Separately, the five groups count as "contributing" only if the interval is entirely below 0** |
| A3 | AUTO Brier ≤ E158 in at least 2 of 3 rounds, and accuracy is never more than 10 points below E158 in any round |
| A4 | HIGH and LOW recall ≥ 0.5, and missed HIGH ≤ E158's 4 + 1 |
| A5 | Calibration slope CI includes 1, or the slope is no further from 1 than E158's |
| A6 | Maximum absolute island mean signed error ≤ E158's 5.5 + 1 |
| A7 | Leakage control passes |
| A8 | Within-region concordance ≥ 0.55 |

- **If all pass:** AUTO becomes the **release candidate**. It is sealed for 2027-Q1 and not deployed until the prospective score exists.
- **If any fails:** E158 remains.
- Nothing is changed after results.

## Registry
Every experiment from E151 to E164 is listed in `docs/EXPERIMENT_REGISTRY.md`, with its hypothesis, data, result and decision.
