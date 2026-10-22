# E94 protocol: probability reliability of the unified news-informed LightGBM (frozen before scoring)

**Branch.** `e94-final-unified-lgbm`, from `e93-lead2-breakthrough`. E93 is preserved. Production is unchanged.

**Freezing.** This file and `runner/run_e94.py` are hashed into `PROTOCOL.sha256` and committed before the run.

## 1. Verified starting point (E93 artifacts, re-read)

**M-U93-LINDIR at K = 1.**
- Accuracy 0.846, balanced accuracy 0.814, 12/16 HIGH caught, Brier 0.142.
- PASS fails only Brier significance.
- The quarter sign-flip test against persistence gives one-sided p = 0.0525 (Holm 0.105); against climatology
  p = 0.1765.

**Where it loses Brier against climatology.**
- **2025-Q4 (−0.353):** three confident false HIGH (p 0.68–0.82) in Cavite, Laguna and Batangas, while rice
  deflated and hunger stayed high.
- **2023-Q2 (−0.164), 2024-Q1 (−0.109) and 2026-Q3 (−0.103):** LOW quarters given middling probabilities.

**Calibration.** Calibration-in-the-large is −0.14 (over-prediction). The 0.2–0.4 band had mean p 0.27 against an
observed 0.05.

**Why this points at the probabilities.** The failure is in the probabilities (overconfident and over-predicting), not
in classification. Two causes are visible in the code:
1. the hunger part's uncertainty uses the **in-sample** residual RMSE of the trees, which understates the forecast
   error;
2. the product of two components is never calibrated against T43 outcomes.

## 2. Candidates (one framework; components fitted once per origin on pooled K = 1..4; news required; K as input)

**Stage 1 (components).** The E93 LINDIR components are run at every origin from 2021-Q2 to 2026-Q3 for K = 1..4:
- the LightGBM price classifier;
- the linear-tree LightGBM hunger-change regressor.

This gives the framework its own earlier **out-of-sample** forecasts.

**Stage 2 (at origin t).** Uses only the earlier forecasts whose T43 label was complete and published before O(t),
pooled over K.

| Arm | Definition |
|---|---|
| M-U94 | E93 LINDIR, reproduced; must equal E93 |
| M-U94-CAL | M-U94 plus walk-forward Platt recalibration of logit p on past forecasts, shrunk toward the identity by n / (n + 20). Requires at least 15 past pairs with at least 3 of each class; otherwise identity. |
| M-U94-STK | Learned combination: a small LightGBM, monotone increasing in both component logits, with K as input, trained on past forecasts (at least 20 pairs and 5 of each class); otherwise the product |
| M-U94-OOS | The hunger part's s = max(random-walk sd, in-sample RMSE, inner out-of-sample RMSE on the last 3 training label quarters) |
| M-U94-OOS-CAL | M-U94-OOS plus walk-forward Platt |

**Ablations (never selectable):**
- **…-OOS(-CAL)-NONEWS:** no news levels or changes.
- **…-OOS(-CAL)-NEWSX:** adds four news × indicator interactions:
  - market news × rice acceleration;
  - climate news × ENSO run;
  - employment news × change in unemployment;
  - FSSI × change in food YoY.

## 3. Selection, K, comparisons (rules unchanged)

**Selection.** Lowest mean Brier over K = 1..3 on targets 2023-Q1..2024-Q4. Confirmation block 2025-Q1..2026-Q3.

**PASS.** The E83 rule, applied to every K separately.

**Validated K.** The E91 rule: PASS and temporal generalization at every horizon 1..K.

**Comparisons.** E93 LINDIR, E92 DEC-S, S-COV, persistence, always-LOW and all E83 baselines, on the same 65 rows per
K.

**Diagnostics (reported separately; they change no rule):**
- the K = 2 pre-onset feature audit for the 2023-Q4 and 2024-Q2 transitions: each origin-time feature's z-score against
  its own history up to the origin;
- the hunger/price conflict table (hunger high while the price signal is falling);
- per-quarter Brier gains.

**Disclosure.**
- These quarters have been examined through E83–E93; repeated development on the same 13 quarters inflates any gain.
- A PASS here would be development evidence only.
- Only the sealed 2026-Q4..2027-Q2 quarters are unseen.
