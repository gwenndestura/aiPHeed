# E165: final optimisation and validation. Protocol and acceptance gates fixed before results.

Written 2026-11-06. **This is the final model experiment.** It is evaluated once. Whatever the gates say is the result.

## 1. Audit of E164 AUTO for hidden test influence
| Step | Uses test outcomes? | Finding |
|---|---|---|
| Anchors (H, RP, OH, RSS) | No | As-of; corruption test 0.0 |
| Imputation, scaling | No | Training median and sd inside each fit |
| Learner hyperparameters | No | Inner region folds on training rows |
| Model and anchor selection | No | Inner weighted SSE on training rows |
| Calibration | No | Inner cross-fitted |
| Threshold | No | Fixed at 50 % (mu ≥ 0) since E151 |
| **Feature list** | **Yes** | `income_growth` and `income_rel` were added in E157/E158 **after ranking 5 sources on these same 72 rows.** **Corrected below: removed.** |
| **Menu design** | **Indirectly** | The OH and RSS anchors and the regularised learners were designed after E159–E163 results on the same rows. **This cannot be removed; it is measured by sensitivity S-H (below).** |

## 2. AUTO-FINAL (the single final candidate, fixed now)
The E164 procedure, with three changes:
1. **Features:** the E151 columns `Pv.GNT_COLS`, without the two E157 consumption columns.
   - FULL = GNT_COLS.
   - GOV = GNT_COLS minus news.
2. **Selection score:** the inner **Brier score of the calibrated probability** against `q_true`, replacing the inner logit SSE. The deliverable is a probability, so calibration must be judged on probabilities.
3. **Calibration options inside the inner selection**, all cross-fitted on inner folds of the training rows:
   - **id:** `Φ(mu/sd)`, with sd from the gap-dependent error model;
   - **lin:** mu' = a + b·mu, then `Φ(mu'/sd')`;
   - **platt:** L2-regularised logistic (C = 1) on mu, with soft labels `q_true` (rows duplicated with weights q and 1 − q).

   Isotonic calibration is excluded: about 700 correlated training rows from 1–3 rounds cannot support it.

**Unchanged from E164:**
- anchors {H, RP, OH, RSS};
- learners {NONE, RIDGE, ENET, RF, LGBM};
- region GroupKFold(5);
- **threshold P(HIGH) ≥ 0.5.** It stays fixed because HIGH ≥ 50 % is the definition, and moving it on these rows would be tuning.

E164 AUTO is kept unchanged as the comparator. E158 is the production benchmark.

## 3. Sensitivities (reported; never used to choose)
- **S-H:** AUTO-FINAL restricted to the H anchor (E158's), which existed before the ranking work. It measures menu optimism.
- **S-NONEWS:** official inputs only.
- **S-NONAT:** national-only columns removed (`group_audit.csv` granularity "national/constant").
- **Group shuffles:** each of the 5 groups shuffled across provinces within survey-lead (seeds 1–3), then all groups together.
- **Training-only threshold:** Youden-optimal on inner out-of-fold probabilities, as a sensitivity only.
- **Leakage:** unreleased-round corruption.

## 4. Statistics
- **Paired comparison with E158:**
  - Brier difference with the region-cluster bootstrap (`E7.diff_ci`, 2,000 draws). Region clusters hold every round of their provinces, so repeated provinces are accounted for.
  - **Exact McNemar test** on paired correct/incorrect classifications.
- **Per round and per island:** accuracy, Brier and signed error.
- **Probability calibration:** the logistic slope and intercept of `y_high` on logit(p), with a region-bootstrap CI. Reliability is reported by probability band, with the 0.4–0.6 band highlighted.
- **Prevalence-level calibration:** E156 C4 (slope of `y_true` on mu).

## 5. Final acceptance gates (AUTO-FINAL, Lead 1 unless stated)
| # | Gate | Rule |
|---|---|---|
| F1 | No leakage | Corruption change < 1e-9 |
| F2 | No advantage from shuffled provinces | Real − all-groups-shuffled Brier: 95 % CI upper bound < 0 |
| F3 | Non-inferior to E158 | Brier point estimate ≤ 0.1344, **and** the CI upper bound of AUTO-FINAL − E158 < +0.02 (non-inferiority margin) |
| F4 | HIGH and LOW performance | HIGH recall ≥ 0.75, LOW recall ≥ 0.65, balanced accuracy ≥ 0.76 |
| F5 | No material bias | Overall mean signed error within ±3 points, **and** no island mean outside ±5 points |
| F6 | Defensible probabilities | Logistic calibration slope 95 % CI includes 1 |
| F7 | Generalises across periods | Accuracy ≥ E158 − 5 points in each round, **and** Brier ≤ E158 in at least 2 of 3 rounds |
| F8 | Retained provincial features contribute | Same evidence as F2, plus each group reported individually |
| F9 | Ordering supported, if displayed | Display ranks only if within-region concordance CI lower bound > 0.5 **and** P(highest) ≥ 0.80. Otherwise ranks are not displayed and the gate is met by not displaying them |
| F10 | Reliable Lead 1 | E156 C1–C6 all pass. Lead 2 is evaluated separately and reported as an extra capability only if it also passes |

- **Validated (F1–F10 all pass):** freeze AUTO-FINAL and seal the 2027-Q1 forecast. Deployment to the API and dashboard **then needs the owner's explicit go-ahead** (production change).
- **F1–F9 pass but F10 fails:** "improved retrospective classifier, Lead 1 not validated as reliable". Freeze and seal, **no deployment**, and E158 stays in production.
- **Any of F1–F9 fails:** E158 stays. Record the failure.

**Development targets** (not gates): accuracy > 73.6 %, balanced accuracy ≥ 0.76, Brier < 0.1344, improved macro F1.
