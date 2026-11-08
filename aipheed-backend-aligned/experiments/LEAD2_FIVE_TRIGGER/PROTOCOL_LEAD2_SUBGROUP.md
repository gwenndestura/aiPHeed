# LEAD2_SUBGROUP protocol: the independent subgroup signal only (frozen before scoring)

**Branch:** `aiPHeed/forecast-research`, continuing from `6febd22` / `00028d0`. **Written:** 2026-10-28. The SHA-256 of this file goes in `runner/SUBGROUP_SHA256.txt`. Both are committed before `runner/subgroup_k2.py` scores anything.

**Unchanged:** the target (T43c), the timing (S-AB), the evaluation rows, R1-R7, the 0.50 cut, P0H4-U as the baseline (B0), and the adoption rule of PROTOCOL_LEAD2_FINAL §5, applied exactly (`final.adoption_rule`).

## 1. Findings that motivate the test (`runner/subgroup_diag.py`; `out/subgroup_diag.json`, `out/subgroup_cases.csv`)

| Question | Finding |
|---|---|
| Does K1 order the missed HIGH cases better? | Yes, modestly. Lead-2 T43c AUC 0.760 → 0.797. The 7 missed HIGH cases rise from the 49th to the 59th percentile of LOW rows; the hits stay at about 94%. |
| Could any cut or monotone calibration convert that? | **No.** 15 LOW rows still score above the best missed case (K1 0.370). Recall ≥ 0.60 (11/17) needs a cut ≤ 0.309, where precision is 0.39 (TP 11, FP 17). A threshold or calibration rule preserves the order, so it cannot meet R6 whatever validation data selects it. This uses the evaluation rows only to rule the method out; no cut is chosen from them. |
| Are the K columns independent of the aggregate price columns? | K_core: R² 0.79 on the 12 aggregate price columns. K_fresh_gap: R² 0.74. Both are **mostly duplicates**. **K_diff: R² 0.34, mostly independent.** The residual separation (HIGH vs LOW) is 0.27, −0.23 and 0.24. |
| Was there a strong early warning the model failed to use? | **No.** A 10-nearest-neighbour vote in subgroup space flags all 7 misses (0.7-1.0), but it is just as high on LOW rows (0.66 vs 0.76 at Lead 2). It separates the price condition worse than the model does (AUC 0.64 vs 0.75). At the 2023-Q4 origins only 5-30 training rows had subgroup values. |
| Hunger-capped misses | 3 of 7 (2023-Q4: π_H = 0.50, so P ≤ 0.50 × π_P < 0.50). No price feature can recover them. |

## 2. Hypothesis and the one candidate

**Hypothesis.** K1's Brier gain comes from the independent breadth signal (K_diff). Its regressions (Lead-1 DEV Brier +0.0057, Lead-1 R6 lost, Lead-2 DEV balanced accuracy −0.021, 2 new false alarms) come from the two redundant columns. They duplicate the aggregate projection with extra noise, and they add a second, separately constrained copy of the same information to a small training set.

**K2** = B0 + `K_diff` only (monotone +1, as fixed in PROTOCOL_LEAD2_FINAL). Everything else is identical to K1 and B0: one unified LightGBM over all leads, all 12 indicator families, the same grid, inner chronological selection, seed, training rows, origins and S-AB hunger term. There is no second variant, no threshold and no calibration.

## 3. Evaluation and adoption

- The same metrics as PROTOCOL_LEAD2_FINAL §4, by lead, with B0 taken from `out/final_rows.csv` (P0H4-U, reproduced there to 5e-7).
- Adoption uses PROTOCOL_LEAD2_FINAL §5, unchanged.
- Lead 2 is called reliable only if R1-R7 all pass.
- **This is the last candidate.** If K2 is not adopted, P0H4-U is retained and the subgroup line of work is closed.

## 4. Not allowed

Changing the target, timing, rows, R1-R7 or the rule; any other column set after scoring; pre-2021 data; new data; changing served artifacts or seals; pushing, merging or deploying.
