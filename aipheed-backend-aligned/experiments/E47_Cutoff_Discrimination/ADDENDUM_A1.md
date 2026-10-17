# E47 addendum A1: price-signal logistic in the product structure (frozen before any A1 score)

**Written:** 2026-10-17, after the single E47 run (`runs/20261017T031323Z`, protocol commit 2afd9cd).
**Freeze:** SHA-256 (LF) in `runner/ADDENDUM_A1_SHA256.txt`, committed with code and tests before A1 is fitted. Run once, then a byte-identical repeat.

## 0. What the E47 run showed

| Arm | Accuracy | AUC | Note |
|---|---|---|---|
| SL-P | 0.343 | 0.12 | |
| SL-5T | 0.429 | 0.18 | |
| LGBM-C | 0.400 | 0.30 | |
| I7-E | 0.800 | 0.722 | the same as I7 |

The selection rule picked I7, which fails A2 (HIGH recall 0.44).

A1 is designed from that result, so **it is hindsight-informed development evidence**. Acceptance stays prospective.

## 1. Diagnosis: D7, an additive model of a conjunctive target

**Why an additive model fails here:**
- T43 = hunger condition AND price signal.
- In the training quarters before 2023-Q4, hunger was ≤ 11.3, so the label was LOW whatever the prices were.
- Those were also the quarters of the highest food inflation (2022–2023).
- An additive model of T43 therefore learns "high price margin → LOW", which is the reverse of the target's own rule.
- This is confounding by the conjunction, not a tuning problem. No additive or tree model fitted on T43 labels from this period can escape it.

**The correct structure:**
- Keep E44/E46's product of components: p = P(hunger) × P(price signal).
- Fit each component on **its own outcome**.
- The price signal `ps = food YoY > c_food OR food − headline > c_gap` is observed for every quarter with complete CPI (2022-Q1 onward, 2025-Q2/Q3 included), whatever SWS shows. That gives about twice as many labelled rows as T43, and no hunger confounding.

## 2. A1 arms (everything not listed follows PROTOCOL.md)

- **PS-P (price only):** L2 logistic (C = 1) of `ps` at t+2 on the four as-of price margins (`mF1`, `mF0`, `mG1`, `mG0`).
  - **Training pairs:** origins t′ with t′ + 2 ≤ t − 1 and `ps` observed in the CPI published before O(t), i.e. through month 3 of t − 1.
- **PS-5T (five-trigger):** PS-P inputs + the PROTOCOL SL-5T trigger inputs (`rice_whsl_yoy`, `brent_yoy`, `tc_count`, `enso`, `palay_yoy`, `fish_yoy`, `ur_yoy`, `remit_php_yoy`, `fx_yoy`); C = 0.1.
- **Hunger component:** E46 I7's as-of P(H > 11.3), taken from the committed I7 run for the same origin. It is unchanged, so A1 exists for origins from 2023-Q4 (targets from 2024-Q2).
- **Probability:** p = P(hunger) × P(ps).
- **Decision:** HIGH iff P(hunger) ≥ 0.5 **and** P(ps) ≥ τ_ps.
  - τ_ps is chosen on the price-signal labels inside training only: embargoed forward chaining (the fold at q is fitted on targets ≤ q − 3, last 6 folds), pooled balanced accuracy over {0.15, …, 0.60}, ties to the cut closest to 0.5.
  - τ_ps = 0.5 if the pooled out-of-fold set has < 3 of either class.
- **Preprocessing:** fitted on training rows only, as in PROTOCOL section 3.

## 3. Evaluation, selection, criteria

**Evaluation rows:** two sets, each with all A1 arms, I7, I7-E, I8, I2 and the baselines present:
- E47 rows (targets 2024-Q3..2026-Q3);
- the extended rows (2024-Q2 added).

**Selection:** the five-trigger arm with the lowest Brier on the labelled targets ≤ 2026-Q2 among {I7, I7-E, PS-5T} (PROTOCOL section 5).

**Development criteria:** PROTOCOL section 6, applied to the selected arm on the E47 rows. If it meets them, it is served behind `AIPHEED_LEAD2_MODEL=e47`; otherwise nothing new is served.

**Price-signal accuracy:** also reported, on all producible quarters including 2025-Q2/Q3.

**Prospective freeze:** `frozen/E47_A1_PROSPECTIVE_2027Q1.json`.
