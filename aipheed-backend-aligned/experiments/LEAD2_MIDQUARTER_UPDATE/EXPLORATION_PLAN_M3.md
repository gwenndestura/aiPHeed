# LEAD2_MIDQUARTER_UPDATE: exploration of M3 decision rules (plan, fixed before any result)

**EXPLORATORY.** This uses the same closed 2023–2026 rows as `RESULTS.md`, which have now been examined many times. Its only purpose is to choose **at most one** HIGH/LOW rule for M3, to be pre-registered and judged on sealed 2027+ updates. Nothing served, sealed or pre-registered changes.

## Data

`out/rows.csv` (65 rows), with these columns:

- hunger part `pi_H4_m3`;
- price part `P0_price_m3`;
- baselines `PERSIST_m3` and `CLIM_m3`;
- label `y`.

Nothing is refitted.

## Search (the same grids as `LEAD2_EXPLORATION`)

| Family | HIGH when | Grid |
|---|---|---|
| F1 | h × p ≥ c | c ∈ {0.20, 0.25, …, 0.60} |
| F2 | h ≥ a **and** p ≥ b | a ∈ {0.5, 0.6, 0.7, 0.8, 0.9}, b ∈ {0.30, 0.35, …, 0.60} |

**Probabilities.** AUC, Brier and R5 always use h × p.

**Honest estimate (nested leave-one-quarter-out).** For each held-out quarter, the grid point is chosen on the other 12 quarters by balanced accuracy, ties broken by precision, then by the grid order. The 65 out-of-sample decisions are scored with the frozen R1–R7.

## Selection

1. Rank F1 and F2 by:
   - the nested number of R2–R7 passed;
   - then nested balanced accuracy;
   - then Brier.
2. The top family's grid point is then fixed on all 13 quarters by the same choice rule. It is registered as the M3 alternative rule.
3. Its nested result is reported against M3 under the served rule (h × p ≥ 0.50, which passes 5 of 6 in-sample). An improvement is claimed only if the nested result passes more rules.

PLAN-SHA256: 7b78e9b8eef9e10e0b6674862dcb7b5b79fc3e964cc1ec181be5d5088fbae17c
