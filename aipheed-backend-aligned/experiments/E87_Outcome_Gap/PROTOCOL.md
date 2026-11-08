# E87 protocol: the five mandatory drivers against the binding constraint (frozen before scoring)

Branch `e84-objective-continuation`. This file is hashed into `PROTOCOL.sha256` and committed before any E87 arm is
scored.

## 1. Driver framework (user directive, 2026-10-21)

There are exactly five drivers: **Market/Prices, Employment, Climate Stress, OFW Remittances, Fish Kill**. News and
NLP are evidence-gathering methods, not a driver.

| Driver | Regional representation at O(t) (only data published before O(t)) |
|---|---|
| Market/Prices | mean of F_now, rice_yoy_now and the S-COMP projected food YoY over the five provinces |
| Employment | ur_last, ur_yoy, under_last (PSA LFS; national: the only series available) |
| Climate Stress | mean tc_count and tc_max_signal (IBTrACS, quarter t), ENSO phase (t−1) |
| OFW Remittances | remit_usd_yoy, fx_yoy (BSP; national) |
| Fish Kill | count of news-reported CALABARZON fish kills first reported in quarter t before O(t) (`data_derived/fishkill_events.csv`, kind = reported_kill); count of all fish-kill news events; mean fish_yoy and aqua_yoy (PSA production) |

## 2. Hypothesis

E84 showed that T43 fails at Lead 2 because the regional hunger crossing (SWS > 11.3%) is not anticipated (HIGH
recall 0.31; with oracle hunger it would be 0.81).

**H1:** at least one driver's regional representation improves the two-quarter hunger forecast beyond the latest
posted SWS reading.

## 3. Arms (Leads 1–3, on the E84 rows; Lead 2 primary)

| Arm | Hunger component | Price component |
|---|---|---|
| HUN-RW | random walk (= S-COMP) | S-COMP |
| HUN-{MKT, EMP, CLIM, OFW, FISH} | ridge (α = 1, standardised) of H(t'+k) on H_last plus that driver's features | S-COMP |
| HUN-ALL5 | ridge on H_last plus all five drivers | S-COMP |

- **Fitting.** Each ridge is fitted on origins whose target round was posted before O(t), with at least 8 pairs;
  otherwise it uses the random walk.
- **Probability.** P(H > 11.3) = Φ((Ĥ − 11.3) / max(the random-walk sd, the training RMSE)).
- **Combined forecast.** p = P(H > 11.3) × S-COMP P(price).

## 4. Learner ablation (secondary; issued rows only)

Constrained LightGBM and L2 logistic regression on the E43 five-trigger groups. The Fish Kill group adds the event
counts above. Each group is run alone and dropped one at a time, with the same eligibility rule as E83.

## 5. Rules

- **Driver value** for the forecast is claimed only if a HUN-driver arm beats HUN-RW on paired per-date Brier at
  Lead 2 (sign-flip, one-sided p < 0.10) **and** has higher HIGH recall.
- **Separate scorecards.** Results on the regional hunger outcome (H-BIN, H-RISE; 13 quarters) are reported apart from
  T43.
- **Pass rule.** The E83 PASS rule applies to T43.
- **Small-sample caveat.** There are 12–13 independent target quarters, so a single quarter moves accuracy by 7–8
  points, and sign-flip p-values cannot go below 1/2^12.
