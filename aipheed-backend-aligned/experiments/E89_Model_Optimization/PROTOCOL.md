# E89 protocol: targeted fixes for the diagnosed Lead-1 and Lead-2 errors (frozen before scoring)

**Branch.** `e89-model-optimization` (from e84-objective-continuation at e10c927).

**Freezing.** This file is hashed into `PROTOCOL.sha256` and committed before any E89 arm is scored. Later changes go
to `DEVIATIONS.md`.

## 1. Error anatomy that motivates E89 (from existing E83/E84 predictions; no new scores)

### Lead 2, S-COMP (18 of 65 wrong)

| Errors | Cause |
|---|---|
| 5 | Unissued. Target 2023-Q1, origin 2022-Q3, had only 4 posted SWS quarters, and the simulation requires 5. Unissued rows count as wrong. |
| 7 | The 2023-Q4 and 2024-Q2 hunger onsets. The latest posted hunger was 8.7–10.3%, so P(hunger > 11.3%) was 0.29–0.41, even though P(price condition) was 0.5–0.84. |
| 6 | Price-side errors: 2024-Q3 Quezon, 2024-Q4 Cavite/Laguna, 2025-Q4 Laguna, 2026-Q2 Cavite, 2026-Q3 Quezon |

### Lead 1, S-SIM (10 of 65 wrong)

| Errors | Cause |
|---|---|
| 3 | The 2023-Q4 hunger onset |
| 7 | Price-side: four HIGH rows missed with P(price) 0.13–0.60, and three Quezon false HIGHs in 2025-Q4, 2026-Q2 and 2026-Q3 |

The repeated Quezon false HIGHs suggest a systematic province-level bias in the structural price probability.

## 2. New information used

The **provincial food-price condition** is food YoY > P60, or food − headline > P60, with the frozen E40 thresholds.
It needs only PSA CPI, so its label exists for **every** quarter whose CPI is complete. That includes quarters without
an SWS round. It gives several times more training labels than T43 itself.

**Label availability at O(t):** price-condition labels for quarters ≤ t−1 (CPI through month 3 of t−1 is published
before O(t)).

## 3. Arms (Leads 1 and 2; all walk-forward)

| Arm | Definition |
|---|---|
| COV (coverage fix) | S-COMP, but the hunger random walk runs with at least 3 posted SWS quarters instead of 5. Only the origins that were previously unissued change. |
| PCAL | Price-condition calibration. At each origin t, an L2 logistic regression (C = 0.5, standardised) on logit(S-COMP P(price)), logit(S-SIM P(price)) and five province indicators. It is trained on pairs (X(t'), price-condition(t'+k)) with t'+k ≤ t−1, and needs at least 6 quarters and at least 4 positive and 4 negative labels; otherwise it uses S-COMP's P(price). P(T43 HIGH) = P(hunger > 11.3) from COV × calibrated P(price). |
| PCAL-GB | Like PCAL, with a constrained LightGBM (depth 2, 4 leaves, 60 trees, lr 0.05, min_child 5, λ = 5) boosted from the same logit inputs plus the prices (F_now, gap_now, mom3, rice_mom3) relative to their thresholds. |

## 4. Evaluation (unchanged rules)

**Rows.** The same 65 rows per lead. Scored with:
- the E83 PASS rule;
- the Lead-1 generalization criteria (`Lead1_Objectives_Assessment/GENERALIZATION_CRITERIA.md`), applied to both
  leads;
- a price-condition scorecard on every quarter.

**Comparisons.**
- current models: S-SIM at Lead 1, S-COMP at Lead 2, and the E83 hybrid;
- persistence, climatology and always-LOW.

**Promotion.** An arm counts as an improvement only if it is not worse in quarter-by-quarter comparison against the
current model **and** improves pooled Brier.

**Caveat.** The 13 quarters have been examined before, so any gain is development evidence. The arms are sealed for
2026-Q4, 2027-Q1 and 2027-Q2.
