# E189: audit of E184, then one model-family test. Fixed before any E189 candidate output.

Written 2026-11-10 under the owner's E185/E189 brief. Local only (not committed, not pushed). The ID E185 was already
used (the copula experiment), so this work is E189. The SHA-256 of this file is logged before the run.

## Step 1: audit (no training) - `app/e189/audit.py` → `data/e189/audit/`
- **Recomputed from stored rows** for E184, E168 and the earlier variants at Leads 1–3:
  - accuracy (Wilson CI), balanced accuracy, precision, recall, specificity, F1, FPR, FNR, Brier, ROC-AUC, PR-AUC;
  - calibration intercept and slope, and confusion matrices;
  - results by survey round and by island;
  - label uncertainty, the rows every variant gets wrong, and power.

## Step 2: candidate E189, the model family chosen in inner CV (the only hypothesis E179–E188 did not test)
- **Hypothesis.** A different learner on the same E168 features and anchors (a regularized linear model or a random
  forest) generalizes better than LightGBM on this small data.
- **Families**, all predicting the change from the anchor, with E168's sample weights:
  - **LightGBM:** E168's 16 HPO settings, unchanged.
  - **Ridge:** alpha ∈ {1, 10, 100}. Training-fold median imputation and standardization; no sign constraints.
  - **Random forest:** 300 trees, min_samples_leaf ∈ {5, 20}, max_features 0.33, random_state 189, with training-fold
    median imputation.
- **Selection.** The grid is anchors {H, OH, RSS} × E168 feature sets × prune {off, on} × family settings, scored by
  weighted SSE of real-row OOF predictions with region GroupKFold(5). This is E168's Stage A, with families added.
- **Synthetic data.** Exactly E184: jitter, 50/50, weight 1.0, 0.5 SD, boundary focus, seeds 17901–17905. Synthetic rows
  are generated inside each inner fold and in the final fit from that outer job's training rows only. Calibration and
  OOF scores use real rows only.
- **Arms:**
  - **E189**, the primary arm (inner-selected family);
  - E189_ridge and E189_rf, descriptive arms (the best configuration of that family);
  - E184, re-run in the same job (the best LightGBM configuration), which must equal the stored E184 rows.
- **Validation.** E184's origin-based protocol, unchanged:
  - Outer jobs ENNS2018, ENNS2019 and ENNS2021 at Leads 1–3, each trained only on outcomes released by its issue
    quarter (`M.released`). These are three chronological origins.
  - 72 real rows per lead. The denominator and labels are unchanged.
- **Decision. A candidate is recommended only if all of these hold:**
  1. Accuracy ≥ 80 % at Leads 1, 2 and 3.
  2. At each lead, balanced accuracy is no worse than E184's minus 0.02.
  3. At each lead, HIGH recall is no worse than E184's minus 0.04 (one province).
  4. At each lead, Brier is no worse than E184's plus 0.005.
  5. Leakage control (corrupted unreleased rounds) is 0. This is run only if 1–4 pass.
- **Significance, reported separately.**
  - Exact McNemar against E184 per lead, Holm-adjusted over the three leads.
  - Brier difference against E184 with a 95 % region-cluster CI.
  - "Statistically supported" only if a Holm-adjusted p < 0.05 or a Brier CI lies entirely below 0.
- **Known limitation, stated in advance.** The 72 rows per lead have been used for model comparison since E151, so
  they are not an untouched holdout. The ENNS 2022 seals are the only untouched check, and they need labels that are
  not yet available.
