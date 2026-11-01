# FIRI Lead 2 feasibility: result

**Protocol:** `PROTOCOL.md`, SHA-256 `3d6e6d0a…`, frozen 2026-10-29T09:35:07Z, before scoring.
**Runs (reproducible):**

- `runner/score_firi_l2.py` → `out/firi_l2_results.json`, `out/firi_l2_rows.csv`
- `runner/ew4_issue_audit.py` → `out/ew4_issue_audit.json`
- `runner/ew4_price_control.py` → `out/ew4_price_control.json`

**Decision: Outcome C, insufficient evidence.** All results are development evidence.

## 1. What FIRI v2 is and what it can be tested against

FIRI v2 is a 0–1 composite proxy index, not a probability. It is issued for t + 2 by construction:
`firi2_history.csv` stores only Lead-2 issues. There is no observed "future FIRI", so scoring FIRI against its own
later values would be circular. No provincial food-insecurity outcome exists. The only defensible target is **R**:
observed SWS Balance Luzon hunger above 11.3% in the target quarter. R is a regional outcome.

## 2. Baseline reproduction

The recomputed regional Lead-2 result equals `firi2_evaluation.json`:

| Measure | Value |
|---|---|
| Quarters | 17 (2022-Q3..2026-Q3) |
| TP / FP / FN / TN | 11 / 0 / 1 / 5 |
| Brier | 0.18871 (artifact) and 0.18871 (recomputed) |
| AUC | 0.933 |

## 3. FIRI v2 at Lead 2 against R (17 quarters: 12 HIGH, 5 LOW)

| | Accuracy | Balanced | Precision | Recall | Specificity | F1 | AUC | Brier | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|---|
| **FIRI v2** | **0.941** [0.730, 0.990] | 0.958 | 1.00 | 0.917 | 1.00 [0.57, 1.00] | 0.957 | 0.933 | 0.189 | 11/0/1/5 |
| Always-HIGH | 0.706 | 0.500 | 0.706 | 1.00 | 0.00 | — | 0.5 | 0.294 | 12/5/0/0 |
| Persistence (latest posted round) | 0.706 | 0.675 | — | — | — | — | — | 0.294 | 9/2/3/3 |
| H1 (probabilistic persistence) | 0.706 | 0.617 | — | — | — | — | — | **0.161** | 10/3/2/2 |
| Climatology | 0.471 | 0.508 | — | — | — | — | — | 0.295 | 5/2/7/3 |

**Accuracy by third:**

| Period | Accuracy |
|---|---|
| 2022-Q3..2023-Q4 | 0.833 |
| 2024-Q1..2025-Q2 | 1.000 |
| 2025-Q3..2026-Q3 | 1.000 |

## 4. Criteria (thresholds unchanged)

| Rule | Result |
|---|---|
| R1 as written (≥ 10 quarters and ≥ 40 rows) | **FAIL**: 17 rows, because a regional target has one row per quarter |
| R2 accuracy ≥ 0.75 | pass, 0.941 |
| R3 balanced accuracy ≥ 0.70 | pass, 0.958 |
| R4 accuracy > always-LOW and > persistence | pass, 0.941 vs 0.294 / 0.706 |
| R5 Brier below persistence (H1) and climatology | **FAIL**: worse than H1 (+0.027, p 0.73); better than climatology (−0.106, p 0.001) |
| R6 precision and recall ≥ 0.60 | pass |
| R7 each third ≥ 0.60 and LOQO minimum ≥ 0.70 | pass, LOQO minimum 0.938 |
| R1-q (adaptation: ≥ 10 quarters) | pass, 17 |
| R4-maj (adaptation: > always-HIGH) | pass, 0.941 vs 0.706 |
| S1 (≥ 3 class changes in the outcome) | **FAIL**: 1 change (LOW→HIGH at 2023-Q4), and FIRI and persistence **both missed it** |
| S2 (≥ 5 quarters of each class) | pass, exactly 5 LOW. Two of them (2022-Q4, 2023-Q2) are exactly 11.3%. |
| S3 (beats persistence, McNemar) | pass: 4 quarters to 0, p = 0.0625 |

**Why this is not a defensible Lead-2 forecast yet:**

- The outcome contains a single regime switch with no return to LOW. FIRI did not anticipate that switch.
- FIRI's advantage over persistence comes from four quarters near the switch, with index values of 0.43–0.57, close to
  the 0.50 line.
- As a probability, FIRI is worse than the hunger-persistence term.
- FIRI v2 (C3) was selected on these same outcomes.

## 5. Provincial level

There is no provincial outcome. The five provinces' FIRI values differ by 0.13 on average and split across the 0.50 line
in 8 of 17 quarters. Those differences cannot be validated with the authorised data.

## 6. EW4 issue-date check (forecast for the 2026-10-01 issue)

**Perturbation audit at origin 2026-Q3, P4 and P0.** All 32 values (prices, H1, H4) are identical after randomising
every input published on or after 2026-10-01:

- 4 SWS rounds, including 2026-Q3 (posted 2026-10-14);
- 246 GDELT records;
- CPI after Aug 2026;
- Pink Sheet and rice CPI after Aug 2026;
- LFS after Jun 2026;
- remittances and rice wholesale for 2026-Q3 and later.

**Positive controls:** perturbing data published before the issue changes H4 (SWS) and changes all 20 price values (CPI).

| Input | Newest period used | Publication evidence |
|---|---|---|
| CPI (A1, A2, A_mom) | Aug 2026 | PSA release calendar (early Sep); audit |
| SWS hunger (H1, H4) | 2026-Q2 round | stored date 2026-08-24; audit excludes 2026-Q3 (10-14) |
| News (N1, G_pri_yoy, NG_gap_price) | to 2026-09-30 20:15 | stored timestamps |
| Pink Sheet (W_*) | Aug 2026 | World Bank calendar (early Sep) |
| Rice wholesale (A3) | 2026-Q2 | stored fetch time 2026-09-09 |
| Remittances (E2) | 2026-Q2 row | stored fetch time 2026-09-09 (source note: curated to 2025-Q4) |
| Unemployment (E1) | LFS Jun 2026 | PSA calendar (early Aug) |
| Palay, corn, fisheries (C3, C4) | 2026-Q2 | **no stored publication or fetch date.** The file was committed 2026-10-20. PSA Q2 releases are normally Aug–Sep. **Not verifiable from stored evidence.** |
| Typhoons (C2) | 2026-Q3 | marked incomplete, so missing |
| El Niño (C1) | as of issue | hazard by issue date |
| Vulnerability (V1) | static | Amendment 1 |

**Seal timing.** None of these seals was literally issued on 1 October:

| Seal | Generated |
|---|---|
| FIRI `e2bef0b2` | committed 2026-10-20 |
| P0H4 `a498b5ef` | committed 2026-10-27 |
| P4H4 `881151a5` | generated 2026-10-29 |

They are forecasts from the 1 October information set, generated after the SWS 2026-Q3 release but before any
target-quarter outcome (2026-Q4, 2027-Q1). The audit shows the 2026-Q3 release does not enter them.
