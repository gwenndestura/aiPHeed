# PROTOCOL_LEAD2_BIAS_TRACK: one development candidate from the measured root cause (frozen 2026-10-29, before fitting)

**Branch:** `aiPHeed/lead2-rootcause-research`. This file's SHA-256 goes in `runner/BIAS_TRACK_SHA256.txt`; both are committed before `runner/bias_track.py` runs.

## Root cause it addresses (LEAD2_ROOTCAUSE_II)

- **The price part causes every B0 Lead-2 error.** It accounts for all 13; in 10 of them the price crossed its threshold after the issue.
- **The bias drifts by regime.** The error of the CPI base-effect projection has a mean that changes with the inflation regime, at Lead 2 by target year:

  | Year | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|
  | Mean error | +4.5 | +2.8 | +1.9 | +0.2 | +1.8 |

- **A model trained across regimes cannot know the current bias.** Pooled LightGBM sees the projection, but not how wrong that projection has been recently.
- **This was not tested earlier.**
  - IMPROVE B2 reweighted rows by recency.
  - B1 and CR-ANC changed the projection itself.
  - CANDIDATES C2 used lagged *labels*.
  - None gave the model the projection's own recent error.

## Candidate X1 (one; nothing else is scored)

**X1 = P0H4-U (B0) + two columns.** Everything else is frozen: the U2 columns, grid, seed, monotone constraints, rows, target and π_H.

| Column | Definition |
|---|---|
| `EF_recent` | realised food margin of quarter t−1, minus the lead-k food projection that was made for t−1 at origin t−1−k. That is, (F − TH_F) of t−1, minus `A1_food` of row (t−1−k, k, p). |
| `EG_recent` | the same for the gap margin. |

**Availability.**
- Quarter t−1 is complete in the CPI months ≤ m0 published before O(t).
- The projection for it was made earlier.
- No label is used. The margins are CPI quantities, and the thresholds are the frozen label constants already inside `A1_food` / `A1_gap`.
- The columns are NaN when either term is missing.

**Scope.** The columns are derived from indicator A1 (market group). The 12 indicators and the five groups are unchanged.

## Selection (development quarters only)

- **Development** = target quarters ≤ 2024-Q4 (`fr_lib.DEV_LAST`).
- **X1 is a development candidate only if all three hold:**
  - its Lead-2 development Brier is at least 0.005 lower than B0's;
  - its Lead-2 development balanced accuracy is not lower than B0's;
  - its Lead-1 development Brier is not worse than B0's by more than 0.005.
- **Secondary sensitivity (pre-declared).** The same columns on the verified-timing CR stack (X1-VER vs CR-VER), under the same rule.

## Reporting (once)

**Metrics, all 65 Lead-2 rows and the 2025-Q2+ confirmation quarters:**
- R1-R7;
- `final.adoption_rule` vs B0;
- accuracy, balanced accuracy, precision, recall, F1, Brier;
- calibration;
- false alarms and missed HIGH;
- quarter-cluster CIs and the R6 pass rate;
- comparison with the served P0H4, B0, CR/CR-ANC (verified and day-10) and the baselines.

**Labels.**
- The 65 evaluation rows have been inspected in earlier runs, so a pass here makes X1 a **development candidate, not a validated model**.
- Independent evidence needs quarters scored after this freeze.
- Nothing is adopted or served.
