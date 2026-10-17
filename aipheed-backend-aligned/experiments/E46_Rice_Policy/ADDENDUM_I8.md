# E46 addendum: iteration I8, I7 issued at the deployed system's own issue time (frozen before any I8 score)

**Written:** 2026-10-17, after the single I7 run (`runs/i7_20261017T000111Z`, addendum commit 7a2c31a).
**Freeze:** SHA-256 of this file (LF) in `runner/ADDENDUM_I8_SHA256.txt`, committed with code and tests before I8 is fitted. Run once, then a byte-identical repeat.

## 0. Evidence status

I7 result (S44, 35 rows):
- accuracy 0.800 (A1 passes);
- balanced accuracy 0.684 and HIGH recall 0.44 (A2 fails);
- EXT accuracy 0.725.

So I7 is not the final candidate. I examined I7's row-level errors before writing this addendum:
- **Missed HIGHs:** the 5 misses are food-minus-headline gaps forecast below threshold, plus one food value 0.02 points above threshold.
- **False alarms:** both are Quezon.

**I8 is therefore hindsight-informed.** Its historical scores are development evidence only, and acceptance stays prospective (PROTOCOL section 5).

## 1. Diagnosis: D4, the backtest is issued earlier than the deployed system issues its forecast

- **Research convention (E41–E46 I7):** the origin O(t) is 00:00 on day 1 of quarter t+1. CPI is cut at month 2 of t, because month 3 is published a few days after day 1.
- **Deployed issue time:** the quarterly pipeline `backend/app/tasks/scheduler.py` (E34, commit c720f71) runs at 03:00 on the 15th of January, April, July and October, "once the source agencies have published that quarter's releases".
- **The mismatch:**
  - every backtest has had one month less CPI than the live forecast it is meant to represent;
  - the latest "completed" quarter was only two-thirds observed;
  - SWS rounds posted between the 1st and the 14th were ignored (e.g. the 2024-Q4, 2025-Q4 and 2026-Q3 rounds, posted 2025-01-14, 2026-01-14 and 2026-10-14).
- **Release evidence:**
  - PSA national CPI is released around the 5th–7th of the next month (E41 PROTOCOL section 2);
  - RSSO IV-A provincial releases follow within days, e.g. February 2024 CPI on 2024-03-07 and March 2024 CPI on 2024-04-08 (https://rsso04a.psa.gov.ph).
  - The 15th leaves at least a week's margin.

## 2. I8 (everything not listed is I7 exactly)

**Issue time:** O'(t) = 00:00 on the 15th of the first month of quarter t+1.

**What enters, as of O'(t):**

| Source | Rule |
|---|---|
| CPI index and published YoY (food, headline) | months ≤ month 3 of t |
| SWS approved rounds | posted before O'(t) |
| Rice-policy events | announced before O'(t) |
| Production, LFS, ENSO, remittances, FX, wholesale rice | unchanged, ≤ t−1 (releases 5–8 weeks after the reference period) |
| Typhoons and news | unchanged, ≤ t |

**Unchanged:**
- **Training pairs:** targets ≤ t−1, the same as I7.
- **Thresholds:** frozen 2021–2022 thresholds.
- **Lead:** 2 quarters from the latest completed quarter t. The target is t+2, about 2.5 months after O'(t).
- **Implementation:** `e41_lib.m0_of` → month 3 of t and `e41_lib.origin` → the 15th, set in `runner/e46_i8.py` before any data are loaded. All E41/E43/E44/E46 cuts read these two functions.

## 3. Arms

- **I8** (primary).
- **I8-BASE:** no residual.
- **I8-MKT:** market + policy residual inputs.
- **BASE-m1.0, BASE-m0.5, BASE-m0.0:** structural signals at O'.
- **B-persist-O':** the latest T43 label available at O'(t), as a decision.
- **Comparators:** I7 and the committed comparators (at O(t)).

## 4. Evaluation, final-candidate rule and prospective rule

Identical to ADDENDUM_I7 sections 4–6, with I8 in place of I7. Two additions:
- the prospective record is `frozen/E46_I8_PROSPECTIVE_2027Q1.json`, issued as of O' = 2026-10-15;
- the final-candidate rule additionally requires I8's S44 Brier score to be no worse than B-persist-O's.

**If I8 passes:**
- it is served behind `AIPHEED_LEAD2_MODEL=e46`;
- `issuedAt` is shown as 2026-10-15;
- production stays E38 until the user decides.

`forecasting_acceptance_met` stays false.
