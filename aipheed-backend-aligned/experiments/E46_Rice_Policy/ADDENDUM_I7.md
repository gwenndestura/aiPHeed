# E46 addendum: iteration I7, the defect-corrected component model (frozen before any I7 score)

**Written:** 2026-10-17, after the E46 run (`runs/20261016T225203Z`) and its byte-identical repeat (`runs/20261016T234337Z`, commit 98c819c). I6 = I2 (0.686) and I6b (0.686, balanced 0.679) both failed A1.
**Freeze:** SHA-256 of this file (LF) in `runner/ADDENDUM_I7_SHA256.txt`, committed with the I7 code and tests before I7 is fitted. Run once, then a byte-identical repeat.

## 0. Evidence status, stated before any I7 result

I7 is designed from error analyses of the same quarters it is scored on, so **every historical I7 score is hindsight-informed development evidence**.

What I examined before writing this addendum (all on targets 2022-Q1..2026-Q3):
- the I6, I4 and I5 outer predictions;
- the structural base-effect price signal: no learning, decision = `base_F > c_food OR base_F − base_HL > c_gap`, at a fixed drift multiplier m.

Accuracy of that structural signal against the province price-signal label (no SWS condition):

| rows | m = 1.0 | m = 0.5 | m = 0.0 | always-LOW |
|---|---|---|---|---|
| all 95 rows (19 quarters) | 0.705 | 0.716 | 0.695 | 0.568 |
| 45 rows, 2024-Q3..2026-Q3 (incl. 2025-Q2/Q3) | 0.733 | 0.800 | 0.733 | 0.689 |
| 50 rows before 2024-Q3 | 0.68 | 0.64 | 0.66 | 0.46 |

On S44 every quarter has H > 11.3, so T43 equals the price signal there. On S44's 35 rows the structural signal scores m = 1.0: 0.743 (26/35), m = 0.5: 0.829 (29/35), m = 0.0: 0.771 (27/35).

**I7 does not pick m from these numbers.** m is selected at every origin by inner validation (section 2). Even so, this is at least the eighth look at S44. Acceptance stays prospective only (section 6).

## 1. Diagnosis: three defects in the I2/I4/I5/I6 price and decision layers

### D1: inconsistent gap (I2, I6)

- **Configuration:** I6 selected drift multiplier 0 plus a LightGBM residual at every origin from 2023-Q4 to 2026-Q3.
- **Food correction:** the residual raised projected food YoY by +2.6 points on average.
- **Headline, uncorrected:** the headline projection it is compared with stayed at m = 0, a bias of −1.95 points.
- **Result:** the implied gap F̂ − ĤL is biased +3.07 points, against +0.45 for the uncorrected bases. The gap thresholds are 0.6–0.9, so P(price signal) sat at 0.5–1.0 almost everywhere.
- **Cause:** a mathematical inconsistency, not a tuning choice. One quantity is corrected and the other is not.

### D2: unstable decision rule (I2, I4, I5, I6)

- **What happens:** at every origin, Platt scaling and the operating threshold are refitted on out-of-fold training predictions that contain 3–9 HIGH labels.
- **Consequence:** the same probability maps to different decisions at different origins. In I4, p = 0.21–0.23 gave HIGH for 2026-Q2 while p = 0.40 gave LOW for 2024-Q3.
- **Effect:** decisions stopped tracking the model's own ranking.

### D3: residual intercepts that do not transfer (I4, I5)

- **What happens:** the gap residual models learned a positive level from 2022–2024, when food inflation exceeded headline. They applied it in 2025–2026, when rice prices fell under the tariff cut and the import suspension.
- **Effect:** gap bias of +0.98 (I4) and +0.92 (I5) on 2024-Q3..2026-Q3.
- **Why selection missed it:** leave-one-quarter-out selection trains on later quarters, so it cannot detect a level that fails to carry forward in time.

## 2. I7 (everything not listed is unchanged from E46 I6)

**Price signal:** two components, each = base-effect projection + residual.
- **F:** food YoY at t+2. Base: `base_m`.
- **G:** food − headline YoY at t+2. Base: `base_m − hl_m`, the same m within a component.
- **Residual:** ridge regression **without an intercept** on standardised inputs (median imputation + missing flags).
- **Residual inputs:** all five trigger groups plus news (E44 `PRICE_GROUPS`) and the E46 as-of policy block.
- **Grid per component:** m ∈ {1.0, 0.5, 0.0} × α ∈ {no residual, 1, 10, 100, 1000}, 15 configurations.

**Selection (per component, per origin):**
- **Method:** embargoed forward chaining.
- **Inner folds:** the last 6 training target quarters q that have ≥ 4 eligible earlier quarters.
- **Embargo:** the fold at q is fitted only on targets ≤ q − 3, the outcomes published before its own origin q − 2.
- **Criterion:** fold RMSE.
- **Ties:** no residual, then larger α, then m = 1.0, 0.5, 0.0.

**Uncertainty:**
- s_F, s_G = the selected configurations' inner RMSEs.
- ρ = correlation of their inner residuals.
- `P(price) = 1 − Φ2((c_food − F̂)/s_F, (c_gap − Ĝ)/s_G; ρ)`.

**Hunger:** E44 I2's component, unchanged (five-trigger ridge on regional signals, LOQO α).

**Decision:**
- `p = P(H > 11.3) × P(price)`.
- **HIGH iff p ≥ 0.5.**
- No Platt, no per-origin threshold.

**Eligibility:** as I2, plus at least one inner fold in each price component.

## 3. Diagnostics (reported; none can become the final candidate in this run)

- **I7-BASE:** the residual is forced to "no residual"; m is still selected by forward chaining.
- **I7-MKT:** residual inputs = market group + policy block only.
- **I7-INT:** residual ridge with an intercept (isolates D3).
- **I7-LOQO:** leave-one-quarter-out selection instead of forward chaining.
- **BASE-m1.0, BASE-m0.5, BASE-m0.0:** fixed structural signals AND I2's hunger p ≥ 0.5. Decisions only; their Brier score is not a probability score.
- **Comparators:** I2, I6, I6b, B-maj, B-persist, SIM-0, SIM-5T, E41-M1, E38-served (from the committed runs).

## 4. Evaluation sets

- **S44:** E44's 35 rows (7 quarters, 9 HIGH), identical rows. E44 gates A0–A4 apply. Paired date-level tests with Holm correction.
- **EXT:** every T43-labelled target ≤ 2026-Q3 for which I7, I2 and the baselines exist. This adds 2024-Q2 if I7 is producible there.
- **PRICE:** the province price signal alone, including 2025-Q2/Q3, where T43 is undefined (no approved SWS round). Decision `P(price) ≥ 0.5`.

**Reported for I7 and I2:**
- leave-one-quarter-out accuracy and its minimum;
- leave-one-province-out accuracy;
- per-province accuracy;
- confusion matrix, precision, F1, date-cluster bootstrap CIs.

## 5. Final-candidate rule (fixed now)

**I7 is E46's final candidate only if all three hold:**
1. it passes A0–A4 on S44;
2. EXT accuracy ≥ 0.75;
3. the minimum leave-one-quarter-out S44 accuracy ≥ 0.70.

**If it is the final candidate:**
- it is served behind `AIPHEED_LEAD2_MODEL=e46` (experimental);
- production stays E38 until the user decides;
- its status is "historical development criteria met; forecasting acceptance pending prospective validation".

**Otherwise:** it is not served, and I2 remains the `e44` experimental candidate.

`forecasting_acceptance_met` stays false in this run either way.

## 6. Prospective acceptance

- **Freeze:** I7's 2027-Q1 forecast, issued from O = 2026-10-01, goes to `frozen/E46_I7_PROSPECTIVE_2027Q1.json` (sha256), with its selections.
- **Rule:** the PROTOCOL section 5 rule applies to I7 unchanged. Acceptance requires the first 4 prospective target quarters (2027-Q1..Q4, 20 province-quarters) with:
  - accuracy ≥ 0.75;
  - balanced accuracy ≥ 0.70;
  - both recalls ≥ 0.60 when both classes occur;
  - Brier better than always-LOW and persistence.
- **Nothing is reselected on outcomes.**
