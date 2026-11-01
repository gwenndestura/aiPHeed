# LEAD2_EXPLORATION: plan (fixed before any result is computed)

**EXPLORATORY.** Every number this study produces comes from the closed 2023–2026 quarters, which were already examined. None of it is evidence that Lead 2 is reliable, and none of it may be reported as such.

**Its only purpose:** to choose at most two decision rules for a pre-registered addendum (`backend/seals/PREREG_LEAD2_ADDENDUM_1.md`). Those rules are then judged only on sealed, on-time 2027+ quarters.

**Not changed by this study:**

- the served system;
- `PREREG_LEAD2.md` (sha `91fe94e0…`): its candidates, rules and primary hypothesis (M0 under D0);
- the seals and the ledger.

## 1. Data

The 65 official Lead-2 rows (13 quarters, 2023-Q2..2026-Q3, target T43c) in `LEAD2_POST_SWS_PRICE/out/eval_rows.csv`.

| Column | What it is |
|---|---|
| `pi_H4` | Hunger part at O(t) |
| `pi_H4_post` | Hunger part at O'(t) |
| `P0_price` | Served price part |
| `P0_price_post` | Price part with the post-SWS CPI cutoff |
| `PERSIST-SI_p`, `CLIM_p` | Baselines at O(t) |
| `PERSIST_post`, `CLIM_post` | Baselines at O'(t) |

Nothing is refitted. Only the way the existing parts are turned into HIGH/LOW is explored, so any rule found can be applied to the parts already stored in every seal.

## 2. Search space (fixed)

**Part sets:**

| ID | Hunger part | Price part |
|---|---|---|
| S0 | `pi_H4` | `P0_price` (served P0H4) |
| S1 | `pi_H4_post` | `P0_price` (M0) |
| S2 | `pi_H4_post` | `P0_price_post` (M2) |
| S3 | `pi_H4_post` | mean(`P0_price`, `P0_price_post`) |

**Rule families:**

| ID | HIGH when | Grid | Combinations |
|---|---|---|---|
| F1 | hunger × price ≥ c | c ∈ {0.20, 0.25, …, 0.60} | 9 |
| F2 | hunger ≥ a and price ≥ b | a ∈ {0.5, 0.6, 0.7, 0.8, 0.9}, b ∈ {0.30, 0.35, …, 0.60} | 35 |

**Probabilities:** the probability is always hunger × price. The probability metrics (AUC, Brier) and R5 use it unchanged; a rule changes only the HIGH/LOW decision. For S0, the baselines are taken at O(t); otherwise at O'(t).

## 3. Honest estimate: nested leave-one-quarter-out

For each part set and family, and for each of the 13 quarters:

1. choose the grid point on the other 12 quarters by balanced accuracy (ties: precision, then the smaller c or a, then the smaller b);
2. apply it to the held-out quarter.

The 65 out-of-sample decisions are scored with the frozen R1–R7 (`P0H4_LEAD12_REVIEW/runner/reproduce.rules`): classification rules on the decisions, R5 on the product. The in-sample best grid point is also reported, labelled optimistic.

## 4. Selection for the addendum (fixed)

**Ranking.** The 8 part-set × family combinations are ranked by their nested out-of-sample result:

1. the number of R2–R7 passed;
2. then balanced accuracy;
3. then Brier.

**Choosing.** The top combination is chosen. A second is chosen only if it uses a different part set and passes at least as many rules. Each chosen combination's grid point is then fixed by the same rule applied to all 13 quarters.

**If nothing improves.** If no combination's nested result passes more rules than M0 under D0 does in-sample (6 of 6 for R2–R7 except R6, i.e. 5), the addendum still registers the top one as exploratory. It says plainly that the exploration found no improvement that survives cross-validation.

PLAN-SHA256: b96368fdc54518a90035672fd9d2d72fdff1539f7a2b5880c7893e25b064cc6b
