# E100: why is the Market / Prices trigger low? Pre-registered protocol

**Date:** 2026-10-23. **Branch inspected:** `main` @ `0239273` (served configuration `AIPHEED_LEAD2_MODEL=thesis`).
**Freezing:** this file is hashed (`runner/PROTOCOL_SHA256.txt`, LF-normalised) before any arm below is scored. The runner refuses to run if the hash differs.
**Production is not changed.** Every output is written to `out/` in this folder only. No served file, record, model or evaluation is overwritten.

**Already examined before this protocol (disclosed):**
- `backend/data/thesis/firi2_evaluation.json` (C0–C3 results, already published);
- the 2027-Q1 FIRI breakdown for Laguna and the region (dashboard bars: Market / Prices 4%);
- `firi2_reference.json` weights (affordability weight at the shrink floor at 2026-Q3).

No ablation, single-indicator, price-level or contribution result below has been computed before this file was frozen. All outcomes (SWS 2022-Q2..2026-Q3) were already seen during the FIRI v2 work, so every result is **development evidence**.

## 1. Questions

Q1. What number is the dashboard's "Market / Prices" bar, and why is it small?
Q2. Does the affordability domain (A1, A2, A3) carry information about the regional food-insecurity outcome under the served evaluation design?
Q3. Is the small bar caused by the data (prices did not track hunger), by the weighting rule, by cancellation inside the group, or by the display?
Q4. Does a price-LEVEL indicator (cumulative food price increase since 2021-Q1) track the outcome better than the served price-CHANGE indicators?

## 2. Data (local files only; 2021-Q1 onward; no new data)

- `backend/data/thesis/firi2_history.csv`: the served FIRI v2 Lead-2 rows (domain scores, indicator scores, weights) for targets 2022-Q2..2027-Q1, five provinces.
- `backend/data/inputs/sws_rounds.csv`: outcome R = mean of all SWS Balance Luzon rounds of the target quarter (the FIRI v2 evaluation's `outcome_series`); y = 1 if H > 11.3. Posted-before-issue rounds (`definition_A` True, `published` < issue) for the walk-forward weights and the climatology baseline, as `thesis_system._posted`.
- `backend/data/processed/cpi_full.parquet`, read with the filter `year >= 2021` (rows before 2021 are never loaded): quarterly provincial food (`cpi_food_nab`) and all-items (`cpi_all_items`) index levels.
- `backend/data/e58/e58_record.json`: the served LightGBM record (TreeSHAP contributions of past forecasts).

## 3. Arms (Lead 2; regional mean of the five province values per target quarter)

Shared: domain scores and indicator scores are the stored v2 values (percentile against strictly earlier origins). Walk-forward evidence weights are recomputed exactly as `firi2_evaluate.evidence_weights` (commit `151887c`, branch `final-thesis-system`): Spearman of the regional mean domain score at past origin t' with the observed hunger level at t'+2, only outcomes posted before the issue date, max(ρ, 0), normalised, shrunk to equal with k = 8, ≥ 6 pairs, mean 1; a domain absent from the weights gets 1. Province index needs ≥ 4 available domains (arms that drop one domain keep the same ≥ 4 rule over the remaining five). HIGH at ≥ 0.5.

| Arm | Definition |
|---|---|
| FULL | The served C3, recomputed. **Reproduction check:** max abs difference from the stored FIRI < 1e-6 on every row, else the run stops. |
| NO-A | Domain A removed; weights recomputed over the remaining domains |
| A-ONLY | Index = regional mean of the A domain score |
| A1-ONLY, A2-ONLY, A3-ONLY | Index = regional mean of that indicator's score |
| EQ-A | Domain A kept but excluded from evidence weighting (weight 1, as if no evidence); other domains as FULL |
| NO-V, NO-C, NO-E, NO-N, NO-H | One other domain removed, weights recomputed |
| LVL-ONLY | Index = regional mean of the percentile score of the price-level indicator L (section 4) |
| FULL-LVL | FULL with A2's score replaced by L's score inside domain A; weights recomputed |
| Baselines | ALWAYS (1.0), H1 alone (regional H1 = domain H score), CLIM (share of posted rounds > 11.3 before the issue) |

## 4. Price-level indicator L (Q4)

At origin t (issue = first day of t+1), quarter t−1 is the latest complete CPI quarter. L(p, t) = 100 × (food index of province p at t−1 / food index of p at 2021-Q1 − 1): the cumulative food price increase since the start of the study window. Score = mid-rank percentile among L values of all provinces at strictly earlier origins (≥ 8, else missing), as FIRI v2. A secondary descriptor R(p, t) = relative food price level (food / all-items index at t−1, over the same ratio at 2021-Q1) is reported only, not used in an arm.

## 5. Metrics

Accuracy (Wilson 95% CI), balanced accuracy, precision, recall, F1 (HIGH), AUC-ROC, Brier (index as a score, not a calibrated probability), Spearman with the observed hunger level, confusion matrix; per-quarter correctness. Paired quarter Brier difference vs FULL with a bootstrap 95% CI (2,000 draws, seed 2026) and a two-sided sign test. All arms are compared on the quarters where FULL and the arm are both computable; the count is reported.

## 6. Contribution diagnostics (Q1, Q3)

- The dashboard bar for every served quarter (2024-Q2..2027-Q1), region scope, from the served code (`thesis_system.firi_drivers`, `dashboard._integer_shares` rule).
- For every served province row: weight × (score − 0.5) / n per indicator (= exact SHAP); per group the signed sum and the absolute sum; the cancellation ratio |Σ signed| / Σ |signed| for Market / Prices.
- The walk-forward ρ of each domain at every origin (the input of the weights).
- LightGBM (A1): mean absolute TreeSHAP log-odds share per group over the record's past forecasts (the model's own attribution, a different method from the FIRI bars; reported separately, never compared as the same quantity).

## 7. Interpretation rules (fixed now)

- "Affordability adds information to FIRI under this protocol" only if NO-A has a higher Brier than FULL with the paired CI above 0 **and** sign p < 0.05.
- "Affordability alone tracks the outcome" only if A-ONLY's AUC > 0.5 with Spearman > 0 and its accuracy exceeds ALWAYS.
- "The weighting rule explains the small bar" if the affordability weight is at the shrink floor (ρ_A ≤ 0) at the served origin and EQ-A raises the regional Market share materially (reported, no threshold claimed).
- "Price level tracks the outcome better than price change" only if LVL-ONLY beats A2-ONLY on Brier with the paired CI below 0 and sign p < 0.05; otherwise "not demonstrated".
- 17–18 quarters give low power: "no significant difference" is never read as "no effect". Ablation results are statements about this index and this outcome, not about whether prices matter for food security.

## 8. Not done

No served file is changed. No threshold other than 0.5. No arm is tuned. No LightGBM retraining (the training panel `aipheed-backend-aligned/data/processed/` is not on `main`). No pre-2021 data. No new data collection.
