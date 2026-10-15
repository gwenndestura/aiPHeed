# E38 protocol: diagnosis-driven, nested tuning of the next-quarter (lead 2) LightGBM

**Status: FROZEN after the verification and diagnosis (`runs/e38_verification_diagnosis.json`) and before any tuned configuration was scored.** SHA-256 in `runner/PROTOCOL_SHA256.txt`. Written 2026-10-15.

## 1. Starting point (verified)

- E37 reproduces byte-identically: predictions sha `e8ec326e…`; E36-LGBM 39/55 and persistence 44/55.
- The E37 `select()` correction changed only the displayed prior-date labels. Choices and scores are identical.
- Outer rows: 11 target quarters (2023-Q3..2026-Q3), 55 rows, 49 HIGH / 6 LOW, 11 independent regional observations.
- **These dates have been examined in E25, E32, E35 and E37.** Whatever E38 reports on them is development evidence, not independent validation.

## 2. Diagnosed causes the tuning may address (and only these)

| Cause (evidence) | Correction allowed |
|---|---|
| Base-rate drift: the label is relative to a trailing median; training sets at early origins are LOW-rich, while later outcomes are 89% HIGH; calibration-in-the-large −0.24; 12 of 16 errors are HIGH called LOW | **Prior-shift adjustment:** shift the model's log-odds by logit(r_recent) − logit(r_train). r_recent = Laplace HIGH share of the labels of the **4 latest quarters posted before the origin**; r_train = Laplace HIGH share of the training rows. Uses only labels published before the origin. |
| Complexity vs. 10–75 training rows; unstable selection path | Two extra regularized LightGBM settings (G5, G6 below) |
| Redundant / sparse inputs (H_last ≈ H_margin, r = 0.998; FSSI 80% zeros) | Feature sets already include COMPACT. The five-trigger representation is tested (§3) because the thesis defines it, despite its sparsity. |
| Threshold | Inner-only rule (§4); the diagnostic sweep on outer rows is never used |

**Not allowed:** changing the target, τ, labels, evaluation dates, the six baselines, or any choice made by looking at E37/E38 outer outcomes.

## 3. Pool for the proposed (combined) model

**Feature sets**
- COMPACT (6);
- COMB (13);
- **COMB_T5** = COMB + the five trigger proportions of quarter t:
  - computed with the existing `app/ml/nlp/trigger_classifier.py` on the in-window, province-attributed news titles **published in quarter t**;
  - proportion = matching titles / attributed titles; 0 when there are none.

**LightGBM settings**
- G1 (stumps, E36);
- G3 (depth 2, λ = 5, E36);
- **G5:** stumps, `n_estimators` 60, `learning_rate` 0.05, `min_child_samples` 10, `reg_lambda` 5, `reg_alpha` 1;
- **G6:** stumps, `n_estimators` 100, `learning_rate` 0.05, `min_child_samples` 5, `reg_lambda` 1, `subsample` 0.8 with `subsample_freq` 1, `colsample_bytree` 0.8, seed 36.

**Adjustment:** none, or prior-shift (§2).

**Pool size:** 3 × 4 × 2 = **24 configurations**.

**Inner selection** at each origin:
- lowest mean per-date Brier on the eligible prior dates (lead-2 targets posted before the origin);
- fewer than 3 such dates → COMB × G1 × none (the E37 default);
- ties within 0.002 → simpler, in the order: no adjustment before prior-shift; COMPACT < COMB < COMB_T5; G1 < G5 < G6 < G3.

## 4. Threshold rule (inner only)

At each origin, take the chosen configuration's predictions on the eligible prior dates.
- If they contain **at least 3 LOW rows**, pick the threshold in {0.3, 0.4, 0.5, 0.6, 0.7} with the highest balanced accuracy on those prior rows. Ties → closest to 0.5.
- Otherwise use 0.5.
- The threshold is fixed before the origin's own outcome is used.

**Calibration** (beyond the prior shift) is **not** used: fewer than 10 LOW rows exist in any inner set.

## 5. Outer evaluation and the six baselines

- Same 11 outer dates as E37.
- The six thesis baselines are exactly E37's definitions, recomputed in the same run.
- Supplementary diagnostics (always-HIGH, climatology) are kept apart.
- Metrics as E37 §5, plus the threshold path:
  - date-cluster bootstrap;
  - per-date paired tests;
  - Holm correction over the six.

## 6. Adoption rule (decided now)

**The E38 procedure ("E38-LGBM") replaces the E37 procedure for the next-quarter forecast only if, on the outer rows:**
1. its accuracy ≥ E37's (0.709), **and**
2. its balanced accuracy ≥ E37's (0.544), **and**
3. its mean per-date Brier ≤ E37's (0.2156).

Otherwise E37 stays.

**Validation status** (same rule as E37 §6):
- **RELIABLE** needs a date-bootstrap lower bound ≥ 0.75, no significant loss to any baseline, and a prospective confirmation.
- Otherwise **NOT DEMONSTRATED**, or **INCONCLUSIVE** when LOW < 5 or dates < 8.

**Any 75% statement is about development dates** and is never called validation.

## 7. Integrity

- Fixed seeds; a repeated run must be byte-identical.
- E36/E37 artifacts are not modified.
- Deviations go to `DEVIATIONS.md`.
- No pre-2021 data.
