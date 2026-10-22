# E92: LightGBM-only Lead-2 model with news as a required input (report)

**Branch.** `e92-lightgbm-lead2`, from `e91-unified-horizon-model`. Not pushed. Production unchanged.

**Evidence.**
- Protocol: `PROTOCOL.md`, frozen at dac8c0b. Amendment A1 (news required, the user's instruction) was made before
  any result was seen.
- Pre-registered run: `runs/20261022T055421Z/`.
- Post-hoc round 2: `round2_posthoc.json` and `predictions_round2_k{k}.csv` in the same folder.
- Rows: the same 65 per lead (13 target quarters 2023-Q1..2026-Q3 × 5 provinces, 16 HIGH, target T43).
- Rules: the E83 PASS rule, unchanged.

## 1. Answer

| Question | Answer |
|---|---|
| Is it now fully machine learning (LightGBM)? | **Yes.** Every forecast comes from LightGBM: a hunger-condition model × a price-condition model, trained on pooled horizons. Where a part has too little history (8–15% of origins at Lead 2), it outputs its own training-label frequency. No simulation probability is issued; the structural projections enter only as two input features. |
| Is news an input? | **Yes, required** in every part: the ten news-pipeline indicators, including FSSI-v3 and the market, climate, fish-kill, employment and national signals. |
| Did Lead-2 accuracy improve? | **Over the LightGBM hybrid, yes:** 0.554 → **0.754**. **Over the best Lead-2 model, no:** S-COV, which is not ML, stays at 0.800. 0.754 equals always-LOW. |
| PASS at Lead 2? | **No.** It catches 2 of 16 HIGH, and its balanced accuracy and Brier don't beat the baselines. |
| Promotion over S-COV? | **No:** Brier 0.204 vs 0.177, recall 0.12 vs 0.31. |

## 2. Lead-2 results (65 rows; unissued rows count as wrong)

| Model | ML? | News? | Accuracy | Balanced | TP / FP / FN / TN | Brier | Failed criteria |
|---|---|---|---|---|---|---|---|
| **M-LGB-DEC-S (selected)** | LightGBM | yes | **0.754** | 0.542 | 2 / 2 / 14 / 47 | 0.204 | balanced accuracy, Brier significance, recall |
| M-LGB-DEC | LightGBM | yes | 0.754 | 0.542 | 2 / 2 / 14 / 47 | 0.210 | same |
| M-LGB-STACK | LightGBM | yes | 0.738 | 0.490 | 0 / 1 / 16 / 48 | 0.221 | all four |
| M-LGB-LIN (post-hoc, linear trees) | LightGBM | yes | 0.754 | 0.584 | 4 / 4 / 12 / 45 | 0.196 | Brier significance, recall |
| *News ablation:* M-LGB-DEC-S without news | LightGBM | no | 0.769 | 0.552 | 2 / 1 / 14 / 48 | 0.190 | balanced accuracy, Brier significance, recall |
| S-COV (current best Lead 2) | no (simulation) | no | **0.800** | 0.636 | 5 / 2 / 11 / 47 | **0.177** | Brier significance, recall |
| HYB-GBA-SIM (E83) | partly | no | 0.554 | 0.494 | 6 / 19 / 10 / 30 | 0.347 | all four |
| E91 U-GB | partly | no | 0.738 | 0.574 | 4 / 5 / 12 / 44 | 0.190 | all four |
| Always-LOW | — | — | 0.754 | 0.500 | 0 / 0 / 16 / 49 | 0.246 | — |
| Persistence | — | — | 0.646 | 0.555 | — | 0.354 | — |

**Selection.** The rule picked M-LGB-DEC-S (selection-block Brier 0.2336) over M-LGB-DEC (0.2337) and M-LGB-STACK
(0.2531).

**Generalization.** "Partially generalized": early accuracy 0.75, late 0.76, quarters won/lost against persistence
5/1.

## 3. The same LightGBM model at Leads 1 and 3 (reported only)

| Model | Lead 1 accuracy / recall / Brier | Lead 3 accuracy / recall / Brier |
|---|---|---|
| M-LGB-DEC-S (selected, news) | 0.785 / 0.31 / 0.136 | 0.708 / 0.12 / 0.186 |
| M-LGB-LIN (post-hoc, news) | **0.815 / 0.62 / 0.124**; fails only Brier significance (Holm 0.084 / 0.118) | 0.708 / 0.31 / 0.161 |
| S-COV | 0.815 / 0.50 / 0.141 | 0.754 / 0.12 / 0.147 |
| HYB-GBA-SIM | 0.877 / 0.75 / 0.101 (PASS, post-hoc) | 0.400 |

At Lead 1, the all-LightGBM M-LGB-LIN with news is as accurate as S-COV and has better recall and Brier. Because it was
built after seeing results, it is a candidate, not a validated model.

## 4. What news contributes

| Lead | Brier with news | Brier without news | Reading |
|---|---|---|---|
| 1 | 0.136 (DEC-S), 0.133 (DEC) | 0.148, 0.147 | **News helps a little** |
| 2 | 0.204, 0.210 | 0.190, 0.194 | **News hurts a little** |
| 3 | 0.186, 0.194 | 0.197, 0.207 | News helps a little |

None of these differences is large enough to change a pass/fail outcome. News is kept as a required input, as
instructed, and its effect is reported as is.

## 5. Why LightGBM cannot reach a reliable Lead 2

1. **The hunger onsets are outside the training data.** A tree model predicts within the range it has seen. Before
   2023-Q4, every training quarter had hunger below 11.3%, so the hunger classifier predicts LOW for the 2023-Q4 and
   2024-Q2 onsets.
   - Linear trees (post-hoc) extrapolate a little: recall rises from 2 to 4 of 16.
   - The onsets are still missed, because no input anticipated them (E90).
2. **Too few labelled quarters.** The direct T43 LightGBM (STACK) could be fitted at only 54% of Lead-2 origins.
   Splitting the target raised fitted coverage to 85–92%, but the number of distinct events is unchanged.
3. **The simulation beats learned trees on prices.** The structural price simulation projects inflation paths, which
   trees cannot learn from about 20 quarters (also seen in E89).

## 6. Conclusion for the thesis

> A fully machine-learning LightGBM model was built for Lead 2, with news indicators as required inputs: one
> hunger-condition model and one price-condition model, each trained on pooled forecast horizons. It issues every
> forecast and reaches 75.4% accuracy at two quarters ahead, up from 55.4% for the earlier LightGBM hybrid. That equals
> always-LOW, and it detects only 2 of 16 high-risk cases, so it does not meet the study's criteria.
>
> The best Lead-2 accuracy remains the non-ML structural model (80.0%), which also fails the high-risk recall
> requirement. News helped slightly at Leads 1 and 3 and slightly hurt at Lead 2.
>
> The limiting factor is that the 2023–2024 hunger surges lay outside the range of any earlier training data and were
> not signalled by any available indicator. No reliable Lead-2 forecast was achieved, by machine learning or otherwise.
