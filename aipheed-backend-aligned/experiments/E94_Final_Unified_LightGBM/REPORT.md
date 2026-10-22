# E94: final unified LightGBM optimization (report)

**Branch.** `e94-final-unified-lgbm`, from `e93-lead2-breakthrough`. Not pushed. E93 is preserved. Production is
unchanged.

**Evidence.**
- Protocol: `PROTOCOL.md`, frozen at c135124. Deviation D1 (`DEVIATIONS.md`): a crash fix made before any metric
  existed.
- Run: `runs/20261022T061502Z/`:
  - `metrics.json` and `predictions_k{1..4}.csv`;
  - `components.csv`: the framework's out-of-sample component forecasts at every origin and K;
  - `diagnostics.json`, `power_k1.json`.
- Tests: `backend/tests/integration/test_e94_final_unified_lgbm.py`.
- Rows: 65 per K, the same targets at every K.

These are **development evidence**. The 13 quarters have been examined in E83–E93, and only the sealed 2026-Q4..2027-Q2
quarters are unseen.

## 1. The single unified model

**M-U94 = E93 M-U93-LINDIR**, reproduced exactly (maximum difference 8e-17). It is one framework. At every forecast
origin, two cooperating LightGBM components are fitted once on the pooled training pairs of all horizons, with the
horizon K as an input:

| Component | Model | Inputs |
|---|---|---|
| Hunger change | Linear-tree LightGBM regression; P(regional SWS hunger > 11.3%) from a normal around the forecast | Hunger level, change and age; direction and acceleration of prices, employment, remittances, climate; **the ten news indicators and their changes** |
| Price condition | LightGBM classifier | Food and gap level, change and acceleration; base-effect and structural projections (inputs only); rice, world prices, policy; **news** |

The forecast is P(hunger) × P(price) for K = 1, 2, 3 and 4.

**Selection.** E94's frozen rule (mean Brier, K = 1..3, targets 2023–24) kept it ahead of every new reliability
variant:

| Variant | M-U94 | M-U94-OOS | M-U94-CAL | M-U94-OOS-CAL | M-U94-STK |
|---|---|---|---|---|---|
| Selection Brier | **0.1562** | 0.1563 | 0.1600 | 0.1601 | 0.1951 |

## 2. Horizon table (unified model; unissued rows count as wrong)

| K | Accuracy | Balanced | Precision / recall | TP / FP / FN / TN | Brier | Calibration-in-the-large | Holm p vs persistence / climatology / always-HIGH | PASS | Unmet |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **0.846** | **0.814** | 0.67 / **0.75** | 12 / 6 / 4 / 43 | 0.142 | −0.138 | 0.105 / 0.177 / 0.000 | No | Brier significance only |
| 2 | 0.692 | 0.564 | 0.36 / 0.31 | 5 / 9 / 11 / 40 | 0.215 | −0.079 | 0.081 / 0.467 / 0.004 | No | accuracy, balanced accuracy, Brier, recall |
| 3 | 0.646 | 0.513 | 0.27 / 0.25 | 4 / 11 / 12 / 38 | 0.191 | −0.085 | 0.006 / 0.292 / 0.003 | No | all four |
| 4 | 0.585 | 0.493 | 0.24 / 0.31 | 5 / 16 / 11 / 33 | 0.255 | −0.111 | 0.051 / 0.669 / 0.005 | No | all four |

**Maximum validated K = 0.** The best candidate is the unified model at K = 1, which misses only the significance of its
Brier improvement.

**Comparisons at the same rows** (accuracy, HIGH caught, Brier):

| K | E92 DEC-S | S-COV | Persistence | Always-LOW |
|---|---|---|---|---|
| 1 | 0.785, 5/16, 0.136 | 0.815, 8/16, 0.141 | 0.723, Brier 0.277 | 0.754, Brier 0.246 |
| 2 | 0.754, 2/16, 0.204 | 0.800, 5/16, 0.177 | 0.646, Brier 0.354 | 0.754, Brier 0.246 |

Quarter-level, province-level and confirmation-block results of this model are identical to E93 (E93 REPORT §3):
- K = 1: 85% correct-majority quarters; early / late accuracy 0.90 / 0.76; 5 / 2 / 6 against persistence.
- Rizal 1.00 (no HIGH rows); Cavite and Laguna 0.85; Quezon and Batangas 0.77.

## 3. The K = 1 reliability failure: what was tried and what it showed

**Where the Brier test is lost.** Per-quarter Brier gains against climatology:
- **Losses:** 2025-Q4 (−0.353), 2023-Q2 (−0.164), 2024-Q1 (−0.109), 2026-Q3 (−0.103).
- **Mean gain:** +0.066 (SD 0.247) against climatology; +0.135 (SD 0.276) against persistence.

2025-Q4 holds three confident false HIGH (p 0.68–0.82). Rice was deflating while hunger stayed above 20%: a hunger/price
conflict.

**Fixes tried** (all training-only; same rows; K = 1):

| Fix | Result | Verdict |
|---|---|---|
| Walk-forward Platt recalibration on the model's own past forecasts (CAL) | Brier 0.147, recall 0.62 | Worse. Too few past HIGH outcomes to learn a correction; active at only 62% of origins. |
| Out-of-sample hunger uncertainty (OOS) | Brier 0.141 vs 0.142 | No material change. The in-sample RMSE was not the binding problem. |
| Learned LightGBM combination of the two components (STK) | Predicts LOW everywhere; 0/16 caught | Rejected. Too few past outcomes. |
| News × indicator interactions (NEWSX) | 0.141, identical classifications | No gain |

**Statistical power** (`power_k1.json`). If future quarters showed the same gain distribution as these 13:

| Comparison | 13 quarters | 20 | 24 | 30 |
|---|---|---|---|---|
| Persistence (Holm level) | 0.40 | 0.61 | 0.76 | 0.84 |
| Climatology | 0.18 | 0.32 | 0.38 | 0.42 |

**Conclusion on K = 1.** More quarters would likely settle the comparison with persistence. Against climatology the gain
is too small and uneven, so the model has to remove the conflict-driven false alarms, not just accumulate data.

## 4. K = 2: the two transitions analysed separately (diagnostic)

**Method.** Each regional origin-time feature is converted to a z-score against its own history at earlier origins,
which uses only information available at O(t). The table shows the largest z-scores.

| Transition | K = 2 origin | Unusual at the origin | Reading |
|---|---|---|---|
| **2023-Q4** | 2023-Q2 | Fisheries output YoY +47% (z 8.0); adverse supply and household news events (z ≈ 3.4); falling FSSI (z −5.6); rice not yet moving | **Not anticipated.** The signals are weak, mixed in direction and unlike any earlier pattern. Rice momentum became extreme only one quarter later (z 9.7 at the K = 1 origin). |
| **2024-Q2** | 2023-Q4 | Rice wholesale YoY 18.3% (z 12.8); rice acceleration (z 6.0); El Niño run × rice (z 5.7); rice retail YoY 10.5% (z 4.9) | **Signalled in available data but not learnable.** The framework had seen at most one comparable rise before this origin, so the learned hunger-change response stayed too small to cross 11.3% from 10.3%. At K = 1 it was caught in all four provinces. |

**Under the unchanged rules, K = 2 cannot be validated with the 2021+ data.** The available predictors did signal the
second transition, but only after the first transition supplied a training example. A reliable K = 2 needs either:
- **more transitions in the training history:** more quarters, or regional SWS microdata with provincial readings; or
- **an earlier hunger signal:** monthly or sub-quarterly food-access data, such as DSWD or LGU program caseloads.

Neither is in the repository.

## 5. Hunger versus price pressure

**Conflict rows** (hunger part ≥ 0.5 while food YoY is falling):

| K | Conflict rows | HIGH among them | False alarms there |
|---|---|---|---|
| 1 | 33 | 13 | **4 of the model's 6** |
| 2 | 23 | 4 | **8 of 9** |

**Recommendation for presentation.** When the two components conflict, the dashboard should report "hunger elevated,
price pressure easing: uncertain" rather than a confident HIGH.
- This is a presentation rule. It changes no score and is not part of the evaluation.
- Applying it would be a production change, which needs authorization.

**Complementary information.** The oracle decomposition (E93) shows:
- the hunger component carries the K = 1 food-insecurity signal: 0.923 against SWS hunger vs 0.846 for persistence;
- the price component causes most remaining errors.

**Alternative target, separate research.** The hunger component alone, scored against the regional SWS hunger condition
(E93 §6), is the only direct food-insecurity evaluation available. **T43 remains the approved target and was not
changed.**

## 6. News

News is a required input in every selectable arm. Controlled ablations:

| K | With news | Without news | Reading |
|---|---|---|---|
| 1 | Brier 0.141 | 0.142, same classifications | No value |
| 2 | 0.214 | 0.199; accuracy 0.723 vs 0.692 | **Hurts** |
| 3 | 0.184 | 0.171 | **Hurts** |
| 4 | 0.250 | 0.250 | No value |

News × indicator interactions add nothing.

**The one possible lead is in event news, not in the ten required indicators.** The pre-onset audit showed adverse
supply and household **event** news unusually high before 2023-Q4 (E85-style event features). That is one episode and
cannot be validated.

Better news coverage is the credible route: full-text sources and a longer archive, with more than 49 FSSI-admitted
quarters' worth of articles.

## 7. Thesis-ready conclusion

> The final aiPHeed forecasting model is a single unified LightGBM framework. At each forecast date, one linear-tree
> LightGBM model of the regional hunger change and one LightGBM model of provincial food-price pressure are trained on
> all horizons together, with the horizon as an input and the ten news indicators as required inputs. It forecasts one
> to four quarters ahead.
>
> One quarter ahead, it reached 84.6% accuracy, 81.4% balanced accuracy and 75% recall of high-risk province-quarters
> (12 of 16), including the 2024-Q2 surge. It met three of the four pre-registered reliability criteria. Its
> probability improvement over climatology was not statistically significant over 13 quarters (Holm p = 0.18), mainly
> because of confident false alarms when food inflation fell while hunger stayed high. Walk-forward recalibration,
> out-of-sample uncertainty and a learned component combination did not fix this.
>
> Two or more quarters ahead, recall stayed at or below 0.31. The 2023-Q4 transition was not signalled by available
> indicators. The 2024-Q2 transition was signalled by rice-price acceleration but could not be learned from the single
> earlier transition in the 2021–2026 window.
>
> **No horizon is validated under the unchanged criteria (K = 0).** The news indicators did not add measurable
> predictive value.
>
> Validation requires the sealed 2026-Q4–2027-Q2 outcomes, a CALABARZON-level hunger series, and an earlier
> food-access signal. Provincial results reflect food-price pressure under high regional hunger, not measured household
> food insecurity.

## 8. Why development stops here

E94 tested every reliability direction named in the directive:
- calibration, uncertainty and component combination;
- news timing and interactions;
- recency weighting and shared-horizon learning (E93).

None improved the pre-registered model. Further variants evaluated on the same 13 quarters would increasingly fit
those quarters rather than improve forecasting. The next informative evidence is new data: the sealed quarters and the
data sources in §4.
