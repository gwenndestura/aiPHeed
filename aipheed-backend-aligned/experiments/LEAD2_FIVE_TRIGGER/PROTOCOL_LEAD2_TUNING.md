# LEAD2_TUNING protocol: structured LightGBM tuning and feature-form review (frozen before scoring)

**Branch:** `aiPHeed/lead2-lgbm-tuning`, created from `a6d6614`. **Written:** 2026-10-28. The SHA-256 of this file goes in `runner/TUNING_SHA256.txt`. Both are committed before `runner/tune.py` scores anything.

**Unchanged:**
- the T43c target and labels;
- S-AB timing (Lead 1 issued at quarter start; Leads ≥ 2 re-issued after the SWS release);
- the evaluation rows (Leads 1-4: 70/65/60/55);
- R1-R7, the 0.50 cut, and the adoption rule of PROTOCOL_LEAD2_FINAL §5 (`final.adoption_rule`);
- one unified LightGBM over all leads (× π_H), with all 12 indicator families and the five trigger groups;
- the served P0H4 (seal a498b5ef) and P0H4-U (bd6572e1).

## 1. Audit findings that shape the campaign (before scoring)

| Item | Finding |
|---|---|
| Served P0H4 vs research P0H4-U | The same LightGBM price model. P0H4-U only re-issues Leads ≥ 2 after the SWS release. Lead 2: P0H4 0.769 (TP 6, FP 4), P0H4-U 0.800 (TP 10, FP 6). |
| Tunable now | The P0H4-U grid has only 8 configurations: depth 1/2, 50/150 rounds, class weight none/balanced; fixed min_child 15, L2 5, learning rate 0.05, and no feature or row sampling, L1 or split-gain penalty. |
| Not tunable here | The hunger part π_H (from SWS, not LightGBM), the product rule, the target, the timing |
| **Ranking headroom** | **No cut on P0H4-U's (or K1's) Lead-2 probabilities meets R6.** Any threshold or calibration keeps the order, so a Lead-2 pass needs a **better ordering** of HIGH vs LOW. Lead 1 meets R6 at 0.50. |
| Structural cap | 3 of the 7 Lead-2 misses have π_H = 0.50 (P < 0.50 whatever the price model). The attainable recall is ≤ 14/17. |
| Code check | `tune_lib.nested` restricted to the P0H4-U subset reproduces P0H4-U to 4.9e-7 on all 250 rows |
| Already tested (not repeated) | Recency weighting (B2/B3); trigger changes and durations (B4); price momentum, acceleration and volatility (FR-II); risk history and transitions (C2); forced class balance alone (C4); Platt calibration (C5); validation thresholds (Addendum 2); subgroup composition (K1/K2); poverty re-construction (D1/D2); missing-value repair of N1 (C1). Missing-data indicators add nothing for trees, because LightGBM already routes NaN to a learned side. |

## 2. Search space (`runner/tune_lib.py`)

**72 structures**, each fitted to 300 rounds at learning rate 0.05 and read at **25, 50, 100, 150, 300 rounds**. Choosing the round count on chronological validation is early stopping. Learning rate and rounds trade off, so one rate with five round checkpoints covers that axis without an extra grid dimension.

| Parameter | Values |
|---|---|
| (max_depth, num_leaves) | (1, 2), (2, 4), (3, 8) |
| min_data_in_leaf | 15, 5, 40 |
| (feature_fraction, bagging_fraction), bagging_freq 1 | (1.0, 1.0), (0.7, 0.8) |
| (L1, L2, min_split_gain) | (0, 5, 0), (1, 20, 0.05) |
| class weight | none, balanced |

The seed (2027), deterministic mode and the monotone directions (A1_food, A1_gap, A_mom +1) are those of P0H4-U.

## 3. Candidates

| ID | Features | Selection of hyperparameters |
|---|---|---|
| **N0** | P0H4-U columns (U2) | **Nested:** at each origin, the configuration with the lowest price-label log loss on that origin's own inner chronological folds (last 4 training origins). No evaluation row is ever used. |
| **N1** | U2 + F1 `XV_food`, `XV_gap` (A1 × V1: market pressure × vulnerability) | nested, as N0 |
| **N2** | U2 + F2 `OWN_food`, `OWN_gap` (newest 3-month y/y as an SD deviation from the province's own earlier y/y) | nested, as N0 |
| **G0** | U2 | **Development-global:** one fixed configuration, the one of 360 with the lowest Lead-2 DEV T43c Brier (targets ≤ 2024-Q4), among those whose Lead-1 DEV Brier is ≤ B0 + 0.005. This uses DEV evaluation rows, so its DEV figures are optimistic. |

**Feature rationales** (`runner/features_v5.py`; cut-off months only):
- **F1.** Depth-1 stumps, which P0H4-U often selects, cannot let the same price pressure matter more in poorer provinces.
- **F2.** The frozen 2021-22 thresholds do not say how unusual current pressure is for that province. Unusually high pressure should revert, which bears on the 3 false alarms where above-threshold pressure fell back.
- Both are highly correlated with existing columns (|r| 0.86-0.94 with A1 or the current-price excess). That is disclosed; if they carry no new ordering, the result will show it.

## 4. Selection and adoption (frozen)

1. Among N0, N1, N2 and G0, the candidates eligible under rule 1b (Lead-1 DEV Brier ≤ B0 + 0.005) are ranked by Lead-2 DEV Brier. The best is the **strongest candidate**.
2. It is **adopted** only if `final.adoption_rule` (PROTOCOL_LEAD2_FINAL §5) passes against B0 = P0H4-U on identical rows.
   - **If it is G0, in addition:** its CONF Lead-2 Brier must be ≤ B0's and its CONF Lead-2 accuracy ≥ B0's. CONF = targets 2025-Q2..2026-Q3, never used by any selection. This guards against overfitting the DEV quarters.
3. **Lead 2 is called reliable only if R1-R7 all pass.** 80% accuracy is a goal, not a criterion.
4. If nothing is adopted, P0H4-U is retained, and the strongest candidate is reported with every unmet criterion.

## 5. Reported for every candidate (Leads 1-4)

- Accuracy and its 90% CI, balanced accuracy, HIGH precision, recall, TP/FP/FN/TN, Brier.
- Baselines: persistence, climatology, always-LOW.
- Thirds and leave-one-quarter-out; DEV and CONF blocks.
- By province (13 Lead-2 rows each; descriptive only).
- Bootstrap Brier difference vs P0H4-U and vs the served P0H4.
- The ranking headroom: whether any cut meets R6.
- The configurations chosen per origin.

**Diagnostics (DEV only, not selection):**
- the effect of class weighting (matched pairs of configurations) on Lead-2 recall and Brier;
- the label audit: class balance by lead, labels within ±0.10 / ±0.50 of the price threshold, and hunger readings within 1 SE of 11.3.

## 6. Not allowed

- Changing the target, timing, rows, R1-R7 or the rule.
- Selecting anything on CONF rows.
- Adding configurations or features after scoring.
- Pre-2021 data or new data.
- Changing served artifacts or seals; pushing, merging or deploying.
