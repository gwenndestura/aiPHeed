# LEAD2_POST_SWS_ISSUE: results

**Protocol:** `PROTOCOL.md`, SHA-256 `1328f059c3c058bf83c3973f656c296fdc8c08e4b2b79f2b088a9d596cd933fe`, frozen 2026-10-31T12:23:31Z, before any scoring. The runner checks it.

**Outputs:**

- `out/results.json`
- `out/log.txt`
- `out/evalA_rows.csv`
- `out/evalB_rows_main.csv`, `out/evalB_rows_sensitivity_plus30d.csv`

**Reproduce:**

```
python -B runner/audit_dates.py
python -B runner/score.py
```

## Decision: (C) Lead 2 is still not reliable, but the post-SWS issue date brings it much closer

The served model issued after the SWS release (**M0**) passes **six of the seven** rules on the official rows. It **fails R6: recall 0.588**, i.e. 10 of 17 high-risk province-quarters, against the required 0.60. The one pre-listed variant (M1, Kalman hunger term) fails R5 and R6. M0's independent-years check cannot be passed by construction: its hunger part *is* persistence (protocol §7). M1's check passes on the main dates but fails under the later-date sensitivity. **By the frozen rule the answer is (C).**

**Why, in plain words:**

- **The fresher survey fixes the hunger problem.** The 2023-Q4 hunger surge is now visible in time for the 2024-Q2 target, and 4 of 10 onsets are anticipated (0 before).
- **All seven remaining misses come from the food-price part**, which by protocol was left exactly as served. It still uses CPI only up to the old issue date, while the baselines were given the fresher CPI.
- **The passes are fragile.** Three of the misses sit at coin-flip values (hunger 0.50 × price 0.495). M0's R2 and R3 passes depend on one borderline label (2023-Q2, exactly 11.3%).

## 1. Checks before scoring (all passed)

| Check | Result |
|---|---|
| Baseline reproduction | P0H4 Lead 2 **6/4/11/44**, Lead 1 **11/5/6/48**, as required |
| Parity at the original issue date: recomputed vs served (max abs. difference) | H4 4.7e-7; Kalman 0; climatology 3.3e-7; persistence 0 |
| Leakage audit at O'(t) (every row; the runner stops on any violation) | Newest SWS round published before O'(t); newest CPI month available at O'(t); P0_price issued at O(t) ≤ O'(t); Kalman inputs published before O'(t). **Passed.** |

## 2. Issue dates and information (official origins)

| Origin → target | O(t) | **O'(t)** | Newest SWS used (published, BL %) | True horizon | CPI to | Lead days (was) |
|---|---|---|---|---|---|---|
| 2022-Q4 → 2023-Q2 | 2023-01-01 | 2023-01-20 | 2022-Q4 (2023-01-19, 11.3) | 2 | 2022-11 | 161 (180) |
| 2023-Q1 → 2023-Q3 | 2023-04-01 | 2023-05-12 | 2023-Q1 (2023-05-11, 8.7) | 2 | 2023-03 | 141 (182) |
| 2023-Q2 → 2023-Q4 | 2023-07-01 | 2023-08-03 | 2023-Q2 (2023-08-02, 11.3) | 2 | 2023-06 | 150 (183) |
| 2023-Q3 → 2024-Q1 | 2023-10-01 | 2023-11-21 | 2023-Q3 (2023-11-20, 10.3) | 2 | 2023-09 | 131 (182) |
| **2023-Q4 → 2024-Q2** | 2024-01-01 | **2024-01-23** | **2023-Q4 (2024-01-22, 14.3)**, the surge | 2 | 2023-11 | 159 (181) |
| 2024-Q1 → 2024-Q3 | 2024-04-01 | 2024-05-01 | 2024-Q1 (2024-04-30, 15.3) | 2 | 2024-03 | 152 (182) |
| 2024-Q2 → 2024-Q4 | 2024-07-01 | 2024-07-24 | 2024-Q2 (2024-07-23, 19.6) | 2 | 2024-05 | 160 (183) |
| 2024-Q4 → 2025-Q2 | 2025-01-01 | 2025-01-15 | 2024-Q4 (2025-01-14, 25.3) | 2 | 2024-11 | 166 (180) |
| 2025-Q1 → 2025-Q3 | 2025-04-01 | 2025-04-01 | 2024-Q4 (2025-01-14, 25.3) | 3 | 2025-02 | 182 (182) |
| 2025-Q2 → 2025-Q4 | 2025-07-01 | 2025-08-16 | 2025-Q2 (2025-08-15, 16.15) | 2 | 2025-06 | 137 (183) |
| 2025-Q3 → 2026-Q1 | 2025-10-01 | 2025-11-06 | 2025-Q3 (2025-11-05, 23.8) | 2 | 2025-09 | 145 (181) |
| 2025-Q4 → 2026-Q2 | 2026-01-01 | 2026-01-15 | 2025-Q4 (2026-01-14, 16.7) | 2 | 2025-11 | 166 (180) |
| 2026-Q1 → 2026-Q3 | 2026-04-01 | 2026-05-13 | 2026-Q1 (2026-05-12, 22.4) | 2 | 2026-03 | 140 (182) |

**Lead time:** median **152 days** (min 131, max 182), against **182** at the current issue date. That is about one month less warning.

**About 2025-Q1:** its only round is the commissioned Stratbase survey. It is published before the quarter ended and is excluded from the served (non-commissioned) hunger series, so O'(t) = O(t) and the true horizon stays 3.

## 3. Evaluation A: official rows (65 province-quarters, 13 quarters, 17 HIGH)

**Baselines are recomputed at the same O'(t).** The original-issue P0H4 is shown for comparison. 95% quarter-cluster bootstrap CIs.

| Forecast | Accuracy | Balanced | Precision | Recall | Specificity | AUC | Brier | TP/FP/FN/TN | Onsets | Rules failed |
|---|---|---|---|---|---|---|---|---|---|---|
| P0H4, original issue O(t) | 0.769 [0.63, 0.89] | 0.635 [0.48, 0.81] | 0.60 | 0.35 | 0.92 | 0.625 | 0.194 [0.12, 0.27] | 6/4/11/44 | 0/10 | R3, R5, R6 |
| **M0: P0H4 at O'(t)** | **0.800 [0.69, 0.89]** | **0.732 [0.55, 0.87]** | 0.625 | **0.588** | 0.88 | **0.760** | **0.167 [0.11, 0.23]** | 10/6/7/42 | **4/10** | **R6 only** |
| M1: Kalman hunger × P0 at O'(t) | 0.800 [0.69, 0.89] | 0.713 [0.57, 0.83] | 0.643 | 0.529 | 0.90 | 0.711 | 0.178 [0.13, 0.23] | 9/5/8/43 | 3/10 | R5, R6 |
| Persistence at O'(t) (PERSIST-SI') | 0.754 [0.63, 0.88] | 0.719 [0.53, 0.86] | 0.52 | 0.65 | 0.79 | 0.719 | 0.246 [0.12, 0.37] | 11/10/6/38 | 6/10 | – |
| Climatology at O'(t) (CLIM') | 0.738 | 0.500 | – | 0 | 1.00 | 0.356 | 0.229 [0.11, 0.36] | 0/0/17/48 | 0/10 | – |
| always-LOW | 0.738 | 0.500 | – | 0 | 1.00 | 0.500 | 0.262 | 0/0/17/48 | 0/10 | – |

**R1–R7 in detail:**

| Rule | P0H4 at O(t) | **M0 at O'(t)** | M1 at O'(t) |
|---|---|---|---|
| R1 ≥ 10 q and ≥ 40 rows | PASS (13 q, 65) | PASS | PASS |
| R2 accuracy ≥ 0.75 | PASS 0.769 | PASS 0.800 | PASS 0.800 |
| R3 balanced ≥ 0.70 | FAIL 0.635 | **PASS 0.732** | PASS 0.713 |
| R4 > always-LOW and > persistence | PASS (0.738 / 0.677) | PASS (0.738 / **0.754**) | PASS |
| R5 Brier < persistence and climatology (p < 0.10) | FAIL (climatology p 0.146) | **PASS** (−0.079, p 0.052; −0.062, p 0.067) | FAIL (climatology p 0.115) |
| R6 precision and recall ≥ 0.60 | FAIL (0.60 / 0.35) | **FAIL (0.625 / 0.588)** | FAIL (0.643 / 0.529) |
| R7 thirds ≥ 0.60 and LOQO ≥ 0.70 | PASS | PASS (0.84 / 0.65 / 0.90; LOQO 0.783) | PASS |

**By third** (accuracy, recall):

| Third | P0H4 at O(t) | M0 | M1 |
|---|---|---|---|
| 2023-Q2 .. 2024-Q2 | 0.72, 0.00 | 0.84, 0.57 | 0.80, 0.43 |
| 2024-Q3 .. 2025-Q3 | 0.70, 0.67 | 0.65, 0.67 | 0.70, 0.67 |
| 2025-Q4 .. 2026-Q3 | 0.90, 0.00 | 0.90, 0.00 | 0.90, 0.00 |

**The 7 high-risk province-quarters M0 still misses** (descriptive, after scoring). All have a **price term below 0.5**:

| Target | Province(s) | Hunger term | Price term |
|---|---|---|---|
| 2023-Q4 | Laguna, Quezon, Batangas | 0.50 (reading exactly 11.3) | 0.495 |
| 2024-Q3 | Quezon | 0.82 | 0.43 |
| 2024-Q4 | Cavite, Laguna | 0.97 | 0.17 |
| 2026-Q2 | Cavite | 0.81 | 0.35 |

**Label-noise sensitivity** (borderline BL quarters 2023-Q2 = 11.3, 2023-Q3 = 10.3):

- **Flips:** flipping either one makes M0 (and M1) fail R2 and R3 as well.
- **Monte Carlo** (2000 draws of SWS sampling error), share of draws each rule passes:

| Model | R2 | R3 | R4 | R6 | R7 | All five classification rules |
|---|---|---|---|---|---|---|
| M0 | 0.41 | 0.38 | 1.00 | 0.06 | 0.82 | **0.06** |
| M1 | 0.41 | 0.33 | 1.00 | 0.05 | 0.82 | **0.05** |

**M0's passes on R2 and R3 are therefore not robust to the survey's sampling error.**

## 4. Evaluation B: independent years (regional TFI-2, BL hunger > 11.3; 74 quarters 2002–2020)

| Dates | Lead days (median) | Horizons | KAL Brier / bal | H1 (persistence probability) Brier / bal | PERSIST (binary) Brier / bal | CLIM Brier / bal | KAL − H1 (p iid; p block-4) | Gate (KAL) |
|---|---|---|---|---|---|---|---|---|
| Main (rule + 60 d) | 122 | h2: 72, h3: 2 | **0.186 / 0.634** | 0.207 / 0.625 | 0.338 / 0.606 | 0.236 / 0.582 | −0.021 (0.086; 0.106) | **passes** |
| Sensitivity (+30 d) | 116 | h2: 17, h3: 57 | 0.188 / 0.601 | 0.201 / 0.620 | 0.338 / 0.592 | 0.239 / 0.573 | −0.013 (0.212; 0.275) | **fails** |

- **M0's hunger component is the persistence probability itself, so it cannot beat persistence** (protocol §7).
- **M1's Kalman term beats persistence only under the main (+60-day) dates.** When pre-2021 releases are assumed 30 days later, most of its advantage disappears.

## 5. Variants run

| Variant | Lead-2 result |
|---|---|
| M0 (primary) | fails R6 |
| M1 (Kalman) | fails R5, R6 |

The baselines (persistence', climatology', always-LOW) were all recomputed at O'(t). Nothing else was run, and nothing was changed after scoring.

## 6. What would change this, and when

1. **A post-SWS price term.** Refit the served P0H4 price model with CPI as available at O'(t) (2 more months at most issues). All seven remaining misses are price-term misses, but this is a **new variant of the served pipeline**. The CPI cutoff is fixed inside `e41_lib.m0_of` / `origin`. It needs its own frozen protocol, and a pass would still be a development result on the same 13 quarters.
2. **Prospective quarters.** Any post-SWS Lead-2 claim needs sealed forecasts issued after each SWS release. With quarterly post-SWS seals from the first 2027 release, 10 Lead-2 targets (≥ 50 rows) resolve by about **late 2029**.
3. **More borderline-proof evidence.** With 2 of 5 LOW quarters on the 11.3% line, only more quarters can make R2, R3 and R6 robust.

**Unchanged by this study:** the served system, `backend/`, Lead 1, the seals (`a498b5ef`, `e2bef0b2`, Y16 `208b5754`), R1–R7, the 0.50 threshold, and the dashboard's "experimental" label for Lead 2.
