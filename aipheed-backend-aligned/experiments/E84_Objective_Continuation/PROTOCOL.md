# E84 protocol: leading information for the two-quarter forecast (frozen before any E84 score)

Branch `e84-objective-continuation` (from E83 at 17de2c6). This protocol is hashed into `PROTOCOL.sha256` and
committed before any E84 arm is scored. Changes after that are recorded in `DEVIATIONS.md`.

## 1. Unchanged from E83

The following are reused exactly:

- **Target T43** and its frozen thresholds.
- **Evaluation rows:** targets 2023-Q1..2026-Q3, 65 rows per lead.
- **Origin timing:** O(t) is the first day of quarter t+1.
- **Leads 0–3**, with Lead 2 primary. **Success requires Lead 2 or beyond**; Lead 1 is not a substitute.
- **Baselines:** B-PERSIST, B-STATE, B-MAJ, B-CLIM, B-AH, B-AL, B-PSA, B-NLP.
- **The PASS rule:** all four of
  1. accuracy > 0.75 with unissued rows counted as wrong;
  2. balanced accuracy > every baseline;
  3. Brier better than B-PERSIST, B-CLIM and B-AH, sign-flip by date, Holm p < 0.10;
  4. HIGH recall ≥ 0.5.
- **TARGET** = PASS with accuracy ≥ 0.80.

## 2. Diagnosis that motivates E84 (from E83, not from new scores)

- Since 2023-Q4, T43 has equalled the provincial food-price condition, because hunger stayed above 11.3% in every
  quarter.
- Lead-2 errors came from price movements the 12-month-drift projection could not see:
  - the 2023-H2 rice spike, which followed world rice prices (India's export restriction, July 2023);
  - the 2024-Q4 typhoon-season jump;
  - the 2025 fall after the tariff cut.
- The projection treated food as one index. Rice is 23–26% of food in these provinces (PSA 2018 weights) and moves
  differently from the rest.

## 3. New information (all fetched 2026-10-21; only 2021+ rows requested; see `data_acquired/provenance.csv`)

| Input | Source | Available at O(t) |
|---|---|---|
| Provincial CPI subgroups, monthly: rice, corn, meat, fish, oils, fruits, vegetables, sugar, food, all items | PSA OpenStat 0012M4ACP22 | months ≤ m0 = month 2 of quarter t (same as E41 CPI) |
| PSA 2018 CPI weights by province and subgroup | PSA OpenStat 0012M4ACP25 | static |
| World prices, monthly: rice (Thai 5%), maize, wheat, palm oil, sugar, IMF food index | IMF PCPS via FRED | month m usable at O(t) only if m ≤ month(O(t)) − 4. Conservative: the series is published with a lag of about 2.5–3 months; July 2026 was the latest value on 2026-10-21. |

## 4. Arms (pre-registered)

### Primary

**S-COMP** — component structural simulation.
1. Each subgroup's log index is simulated forward from m0 with seasonal monthly means (calendar-month means of earlier
   in-window changes) and the joint covariance of the deseasonalised changes of all subgroups (last 24 months, or as
   many as are available, at least 12).
2. **Rice pass-through.** Rice's mean change adds β × (log change of the world rice price in PHP, months m−6..m−3,
   spread evenly). β comes from an in-origin OLS over all five provinces' monthly rice changes on that lagged world
   change, using only months ≤ m0, and is shrunk toward 0 by n/(n + 24).
3. **Aggregation.** Food = the PSA-weighted sum of the subgroup indices, rescaled to the published food index at m0;
   the residual group carries the rest of food. Headline = the all-items index with its own seasonal drift.
4. **Hunger component** = the S-SIM random walk.
5. **Output.** P(HIGH) = mean of 1[H > 11.3] × 1[F > thrF or F − G > thrG] over 20,000 draws.

**S-COMP-THR** — S-COMP with the decision threshold chosen inside each origin. This is the E83 D2 rule (grid
0.10–0.60, chosen on earlier origins only).

### Secondary

| Arm | Description |
|---|---|
| S-COMP-NOW | S-COMP without rice pass-through (isolates the value of world prices) |
| M-LR-W, M-GB-W | E83 learners plus the new features: rice YoY now, rice 3-month momentum, the projected rice component, world rice / food-index lagged changes |
| HYB-W | M-GB-W where eligible, else S-COMP |

### Price-component diagnostic (not a pass criterion)

- **Question:** does each arm's P(price condition) predict the price condition itself?
- **Rows:** 75, covering all quarters 2023-Q1..2026-Q3, including quarters without an SWS round.

## 5. Alternative outcomes (reported beside T43, never replacing it)

| Outcome | Description |
|---|---|
| H-BIN | SWS Balance Luzon hunger > 11.3%, regional, 13 quarters |
| H-RISE | Hunger at t+2 above the latest posted reading by more than 3 points (deterioration) |

Both are scored for persistence, always-HIGH and a ridge model on lagged rice inflation and world food prices.

## 6. Prospective seal

S-COMP and S-COMP-THR forecasts for 2026-Q4, 2027-Q1 and 2027-Q2 from origin 2026-Q3 are written to `sealed/` before
any of those outcomes exists.
