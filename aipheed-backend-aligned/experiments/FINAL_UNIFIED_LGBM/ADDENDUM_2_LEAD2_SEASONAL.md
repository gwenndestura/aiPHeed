# FINAL_UNIFIED_LGBM Addendum 2: one arm aimed at Lead 2 (post-hoc; hashed before scoring)

**When.** 2026-10-27, after the frozen UNI-FINAL run and Addendum 1. Every quarter has been seen, so the result is **post-hoc development evidence**, whatever it is. The reliability rule R1–R7 is unchanged. A pass would not be a confirmed result until SWS 2026-Q4 onward.

## Diagnosis that motivates the arm (computed before writing this file)

Lead 2 fails R3 (balanced accuracy 0.635), R5 and R6 (HIGH recall 0.35). There are two causes:

1. **Hunger term.** In 2023-Q4 and 2024-Q2 the price model flagged pressure, with a mean price probability of 0.77 for 2024-Q2. But π_H was only 0.26–0.29, because the newest SWS reading at issue was 10.3%, below 11.3%, and the 2024 surge had not begun. This loses 7 of the 17 Lead-2 HIGH rows. It is not forecastable from 2021+ hunger history (E90, E111).
2. **Price term.** With the hunger condition replaced by its true value (an oracle, diagnostic only), Lead 2 would reach only accuracy 0.677, balanced accuracy 0.648 and precision 0.42. Price discrimination at Lead 2 (AUC 0.73 when hunger is high) is also too weak.

**The arm below addresses only cause 2.** Passing would need cause 1 to resolve as well, which is not expected. This is stated before scoring.

## The arm

**U6:** UNI-FINAL (U2) with `A1_food` and `A1_gap` replaced by their **seasonal-projection** versions.

| Item | Rule |
|---|---|
| Projection | The current A1 projection holds the latest published CPI index (month m0) flat through the target months. U6 instead projects index(m) = index(m0) × exp(s̄(m0 → m)). |
| Seasonal path s̄ | The mean log change from the calendar month of m0 to the calendar month of m, over earlier years in which both months were published before O(t) (2021-01 or later), per province and per commodity (food, all items) |
| Fallback | With no earlier year available, s̄ = 0, i.e. the current flat projection |
| Features | A1_food_s and A1_gap_s use the same thresholds, YoY bases and averaging over target months as A1_food and A1_gap |
| Unchanged | Monotone constraints (+1 on A1_food_s, A1_gap_s, A_mom); every other column; grid; inner validation; π_H; cutoff 0.50 |

## Adoption rule

**Development comparison.** U6 replaces UNI-FINAL only if its mean development Brier on T43c (targets ≤ 2024-Q4, Leads 1–4) is lower.

**If adopted, it is served only if:**
- it is reliable at Lead 1;
- the maximum reliable lead does not shrink.

**Reporting.** Whatever the outcome, the full per-lead R1–R7 verdicts of U6 are reported next to UNI-FINAL.
