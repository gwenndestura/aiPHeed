# E110 Model experiments and comparisons

**Protocol:** `PROTOCOL.md`, sha `97f7493d…`, frozen 2026-10-25 09:08 UTC, before scoring.

**Scoring commit:** `ec3f29a` plus the JSON-boolean fix (two crash fixes after freezing, both made before any result was written). The runner was clean (`results.json` → `run`).

**Status of the evidence.** Every quarter evaluated here had been examined in earlier experiments, so all results are **exploratory / development evidence**. None is confirmatory.

## 1. Experiments

| ID | Hypothesis | Exact change | Eligible rows | Baseline | Status |
|---|---|---|---|---|---|
| X1 | more outcome data | 4-area SWS panel (in-window) | panel Leads 1–6 | RW | development |
| X2 | noise-aware level | LLR: published round margins, pooled Q | same | RW, MA2, MEAN | development |
| X3 | forecast combination | COMB = (RW + LLR)/2 | same | RW | development |
| X4 | national indicators | NAT-R: ridge on LLR residual with C1, E1, E2, pooled | same | RW, LLR | development |
| X5 | 12 FIRI families (required LightGBM) | LGBM-R: LightGBM on the Balance Luzon LLR residual, 13 columns | Balance Luzon Leads 1–4 | RW, LLR | development |
| X6 | linear 12 families | RIDGE-R: the same with ridge | same | RW, LLR | development |
| S-VOTERS | survey comparability | add the April 11–15, 2025 registered-voter round | panel Leads 1–2 | — | sensitivity |
| S-R4 | value of published margins | constant ±4% instead of round margins | panel Leads 1–2 | — | sensitivity |

## 2. Continuous results: 4-area panel

MAE in points; quarter-cluster block 95% CI for RW and LLR.

| Lead | Quarters (area-rows) | RW | MA2 | MEAN | LLR | COMB | NAT-R |
|---|---|---|---|---|---|---|---|
| 1 | 10 (40) | **5.26** (3.86–6.77) | 5.48 | 7.42 | 5.46 (3.50–7.83) | **5.25** | 7.45 |
| 2 | 8 (32) | 6.12 (3.30–9.00) | 5.53 | 8.45 | **5.39** (2.56–9.09) | 5.69 | 8.47 |
| 3 | 6 (24) | 4.04 | **3.34** | 7.44 | 3.52 | 3.69 | 7.56 |
| 4 | 5 (20) | 3.77 | **3.32** | 8.13 | 3.95 | 3.62 | 7.93 |
| 5 | 3 (12) | 4.40 | 4.00 | 8.32 | **3.65** | 4.02 | 10.13 |
| 6 | 1 (4) | 5.38 | 5.74 | 8.34 | 3.87 | 4.62 | 14.23 |

**Balance Luzon alone (panel rows).**

| Lead | RW | MA2 | LLR | COMB |
|---|---|---|---|---|
| 1 (10 quarters) | **3.85** | 4.46 | 4.66 | 4.09 |
| 2 (8 quarters) | 4.65 | **4.16** | 4.65 | 4.62 |

**By area, Lead 1** (RW / LLR / COMB):

| Area | RW | LLR | COMB |
|---|---|---|---|
| Metro Manila | 3.06 | 3.41 | 3.17 |
| Balance Luzon | 3.85 | 4.66 | 4.09 |
| Visayas | 6.48 | 6.68 | 6.58 |
| Mindanao | 7.66 | 7.09 | 7.15 |

**By area, Lead 2** (RW / LLR):

| Area | RW | LLR |
|---|---|---|
| Metro Manila | 3.60 | 3.45 |
| Balance Luzon | 4.65 | 4.65 |
| Visayas | 6.86 | 6.43 |
| Mindanao | 9.38 | 7.02 |

**Paired tests** (mean quarter difference vs RW; one-sided HLN-DM p):

| Method | Lead 1 | Lead 2 |
|---|---|---|
| LLR | +0.20 (p = 0.64) | −0.74 (p = 0.13) |
| COMB | −0.02 (p = 0.48) | −0.44 (p = 0.098) |
| MA2 | +0.22 | −0.60 (p = 0.22) |
| NAT-R | +2.18 | +2.35 |

## 3. Balance Luzon indicator models (required 12-family LightGBM)

| Lead | Quarters | RW | LLR | COMB | LGBM-R | RIDGE-R | NAT-R |
|---|---|---|---|---|---|---|---|
| 1 | 5 (2025-Q3..2026-Q3) | 2.11 | 2.07 | **1.76** | 2.46 | 3.74 | 3.69 |
| 2 | 2 | 6.70 | 4.50 | 5.60 | 6.05 | 4.03 | 4.86 |

- **All are insufficient evidence** (fewer than 8 quarters).
- **Family ablation of LGBM-R, Lead 1** (MAE, full model 2.46):
  - removing A1 (price projection) → 2.76;
  - removing H1 → 2.16 (better);
  - removing E1, E2 or N1 → 2.49–2.53;
  - the other families are never split (no change).
- **SHAP shares, Lead 1:** A1 0.43, H1 0.24, E2 0.13, E1 0.10, C4 0.07.

## 4. Binary readings (research-defined; SWS has no official threshold)

| Lead | B3 (> 20%): RW / LLR, accuracy (balanced) | B4 (rise > own margin) |
|---|---|---|
| 1 | 0.65 (0.67) / 0.60 (0.62) | 0.75 accuracy, balanced 0.50 for all methods: no rise is ever predicted, so all 10 rises are missed |
| 2 | 0.44 / 0.53 | — |
| 3–6 | insufficient | insufficient |

- **The 75% figure at B4 means nothing:** it equals the share of no-rise quarters.
- **Every binary reading is not reliable or has insufficient evidence.**

## 5. Sensitivities

- **S-VOTERS** (add the April 11–15, 2025 voter round): same conclusions (Lead-1 panel MAE RW 5.27, COMB 5.27, LLR 5.51; Lead 2 LLR 5.42 vs RW 6.16).
- **S-R4** (constant ±4% margin): Balance Luzon Lead-1 LLR 3.84, COMB 3.79 vs RW 3.85, better than with the published margins (4.66). The published ±6% margin of the June and November rounds makes the filter discount exactly the low readings, which then recur. This is post hoc and is not adopted.

## 6. Comparison with earlier models (Balance Luzon, Lead 1)

| Model | MAE | Quarters |
|---|---|---|
| E109 RW | 3.72 | 9 |
| E109 LightGBM | 4.04 | 9 |
| E110 RW | 3.85 | 10 (panel-eligible) |
| E110 COMB | 4.09 | 10 |
| E110 LLR | 4.66 | 10 |

E107/E108 forecast a different target (the composite / price pressure), so they are not comparable.

**Verdict:** the latest published SWS reading remains the best one-quarter forecast. No E110 method is an improvement at Lead 1 or a generalizing improvement at any lead.
