# E70 protocol: bounded, pre-registered Lead-2 improvement attempt and objective completion checks

**Frozen:** 2026-10-20, before any E70 forecast is computed. The sha256 of this file (LF line endings) is in `runner/PROTOCOL_SHA256.txt`; `e70_predict.py` refuses to run if it differs.
**Branch:** `e70-objectives-completion` (from `final-system-v2` @ 2c88d9f).
**Model library:** read-only, from `git archive 089bdf2` (`origin/final-thesis-system`) of `aipheed-backend-aligned/experiments`, `backend/data` and `backend/config`, passed as `AIPHEED_EXP`. Nothing is read from the main checkout.

## 1. Evidence class (stated before running)

Every target quarter 2023-Q4 … 2026-Q3 has already been examined in about 30 earlier experiments (E38–E69, FINAL audit). **All E70 historical results are development evidence, not held-out evidence.** The E70 arms are motivated by weaknesses the audit measured on these same quarters, so any gain is partly selection on the evaluation period. The only untouched outcomes are 2026-Q4 and 2027-Q1, which are not published; E70 seals forecasts for them (§8).

## 2. Targets

| Name | Definition | Class | Use |
|---|---|---|---|
| **T43** (primary, unchanged) | HIGH iff SWS hunger quarter mean (all rounds) > 11.3 AND (province food CPI YoY > its 2021–22 P60 OR food-minus-headline YoY > its P60); E40 `label_spec.json` | Proxy label of food-insecurity risk (Chapter I §1.7: SWS hunger + PSA food prices). Price-dominated in practice, see §2.1 | Lead-1/2/3 scoring |
| T43-approved | Same, approved SWS rounds only | Proxy (sensitivity) | Sensitivity |
| **DIRECT-R** | Regional SWS hunger quarter mean > 11.3 at the target quarter | Direct outcome, **regional only**, one value per quarter | Scored on quarters, never per province |
| PS | The price condition alone | Food-price pressure | Dominance test |

No threshold, label or observation is changed in E70.

### 2.1 Dominance test (pre-specified)

`e70_target_audit.py` reports, for every evaluated row, whether the hunger condition was binding (T43 ≠ PS), and the share of rows on which T43 = PS under hunger thresholds equal to the 2021–2022 approved-round P25, P50, P60, P75 and P90 and 11.3. If T43 = PS on all evaluated rows under every 2021–22-anchored threshold, the result is reported as "price-dominated in this period"; the label is **not** revised, because the only threshold that would bind (> 14.3) would be chosen from the evaluation period.

## 3. Rows

Identical to the sealed E63 rows (`E63_Lead_Time_Study/sealed/predictions.csv`): Lead 1 = 60 rows (12 target quarters), Lead 2 = 50 rows (10 quarters, 2024-Q2 … 2026-Q3), Lead 3 = 45 rows (9 quarters). Same origins, issue dates and as-of baselines. Objective 4 comparisons additionally use the 45 E55 baseline rows (targets 2024-Q3 … 2026-Q3).

## 4. Arms

All arms keep the I7 regional hunger component and the product P = P_hunger × P_price unchanged, and the decision threshold 0.50. They differ only in the price component.

| Arm | Price component | Leads | Role |
|---|---|---|---|
| **R0** | E56-TUNED (`e63_lib.tuned_forecast_h`) | 1, 2, 3 | Reference; must reproduce E63 sealed within 1e-9 or nothing is written |
| **A1 STABLE** | E56 search space; configuration = argmin of the mean inner log-loss over all eligible origins t′ ≤ t of the same lead (each t′ scored on its own training data only); E56 tie-break | 1, 2, 3 | Candidate (addresses configuration instability) |
| **A2 SHRINK** | R0's configuration; logit shrinkage z′ = z₀ + b(z − z₀), z₀ = logit(training PS rate, clipped to [0.02, 0.98]); b = unpenalised logistic slope of the training-fold OOF predictions of that configuration (`folds_h`), clipped to [0.25, 1]; b = 1 if the OOF set has < 10 rows or one class | 1, 2, 3 | Candidate (addresses over-confidence) |
| S0 STRUCT | Base-effect CPI projection probability only (no trees); m ∈ {1.0, 0.5, 0.0} chosen by inner log-loss | 1, 2, 3 | Price-projection-alone reference |
| ABL−g | E56 search with group g removed, g ∈ {climate, fish_kill, employment, ofw_remittance, news, policy, poverty} | 2 | Ablation |
| ONLY-g | Offset-free LightGBM (binary; 2 leaves, depth 1, 40 trees, lr 0.05, min_child 10, λ₂ 10), group g's columns only, g ∈ {market, climate, fish_kill, employment, ofw_remittance, news} | 2 | Single-group baselines |
| Baselines | Persistence, majority, climatology, province climatology (E63 as-of); Obj 4 I–IV from E55 `rows_baselines.csv` | as available | Baselines |

No other arm will be run. Any additional analysis is labelled exploratory in the report.

## 5. Metrics

Accuracy (Wilson 95% and quarter-cluster bootstrap CI), precision/recall/F1 for HIGH and LOW, balanced accuracy, AUC-ROC, within-quarter AUC, Brier, log-loss, confusion matrix, calibration (logistic slope/intercept, ECE, 10 bins), ICC and effective n, per quarter and per province. Paired tests vs R0 and vs every baseline: Δ Brier with quarter-cluster bootstrap 95% CI (B = 4000, seed 2026), two-sided quarter sign test, exact McNemar; Holm over the comparisons of one family.

## 6. Decision rules (fixed now)

1. **Candidate improvement.** A1 or A2 is an improvement over R0 only if, at Lead 2: Δ Brier (arm − R0) CI upper < 0, AND Holm-adjusted (over {A1, A2}) two-sided quarter sign p < 0.05, AND HIGH recall ≥ R0's, AND at Lead 1 and Lead 3 its Δ Brier CI lower bound is ≤ 0 (not credibly worse).
2. **Serving.** Only an arm passing rule 1 may be served, and only behind a new flag (`AIPHEED_LEAD2_MODEL=e70`); the default does not change.
3. **The 80% goal.** Reported as MET only if the arm selected by rules 1–2 (R0 if none passes) has Lead-2 accuracy ≥ 0.80 on the 50 rows with HIGH recall ≥ 0.50 and balanced accuracy ≥ 0.70, and even then described as development evidence pending prospective confirmation. An arm that reaches 0.80 without passing rule 1 is reported as **not demonstrated** (best-of-k selection on reused quarters).
4. **Evidence group value.** Group g adds value only if ABL−g worsens Lead-2 Brier vs R0 with CI lower bound > 0.
5. **Furthest reliable horizon.** The E63 §8 criterion, unchanged (paired Brier better than persistence and climatology, each CI < 0 and two-sided sign p < 0.05).

## 7. Leakage checks

`e70_leak.py` randomises every raw value not available at the issue date (the E57/FINAL corruption scheme) and re-runs R0, A1, A2 and S0 at origins 2023-Q4, 2025-Q1 and 2026-Q1 (Lead 2). Pass = every forecast unchanged (max |Δ| ≤ 1e-12).

## 8. Prospective seal

Before any 2026-Q4 or 2027-Q1 outcome exists, `e70_predict.py --prospective` seals R0, A1, A2 and S0 forecasts for 2026-Q4 (Lead 2 from 2026-Q2; Lead 1 from 2026-Q3) and 2027-Q1 (Lead 2 from 2026-Q3) in `sealed/prospective.csv` with its sha256.

## 9. Reproduction

`REPRODUCTION.md` re-runs `e70_predict.py` from a fresh `git archive` of this branch plus the pinned library export; pass = byte-identical `sealed/predictions.csv`.
