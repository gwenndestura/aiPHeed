# E93 protocol: one unified, news-informed LightGBM for K = 1..4 (frozen before scoring)

**Branch.** `e93-lead2-breakthrough`, from `e92-lightgbm-lead2`. Production unchanged. E92 results are preserved and
compared as they are.

**Freezing.** This file and `runner/run_e93.py` are hashed into `PROTOCOL.sha256` and committed before the run.

## 1. Diagnosis that motivates E93 (from E92 predictions and the posted SWS series; descriptive)

**The SWS hunger series (Balance Luzon) and the 11.3% line.**
- 2021-Q2 15.3, 2021-Q3 10.3, 2021-Q4 9.2, 2022-Q2 11.8, 2022-Q3 9.6, 2022-Q4 11.3, 2023-Q1 8.7, 2023-Q2 11.3,
  2023-Q3 10.3, then 14.3 to 25.3 from 2023-Q4 on.
- Before 2023-Q4 the hunger condition flickers around the line: 11.3 twice, 11.8 once. With a Balance Luzon sample
  of roughly 600, the sampling SE near 11% is about 1.3 points (95% interval ±2.5), so those labels are within
  sampling error.
- T43 HIGH quarters after 2021-Q2: 2023-Q4, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2026-Q2. 2024-Q1 is LOW despite
  hunger of 15.3, because the price condition was off.

**E92 Lead-2 misses by component:**

| Target | Hunger part | Price part | Reading |
|---|---|---|---|
| 2024-Q2 (4 HIGH) | LightGBM classifier 0.06 (random walk 0.41) | 0.75–0.95, correct | The classifier is overconfidently LOW; it can't represent "rising" |
| 2024-Q4, 2025-Q1 (Cavite, Laguna) | fine | 0.13–0.32 | Rice YoY was 17–21% at the origin, but food YoY only 3.5–4.2 |
| 2023-Q4 | 0.09 | — | Last hunger 8.7, rice YoY 0.2–7.6, no ENSO advisory: no visible signal |

**Structural limit.** Because T43 is a product, P(T43) ≤ P(hunger). When the last posted hunger is below 11.3, a HIGH
call needs evidence that hunger will **rise**, i.e., information about direction, not level.

## 2. Hypotheses tested

| ID | Hypothesis |
|---|---|
| H-A | Direction, acceleration and cumulative features let the unified model separate "staying LOW" from "turning HIGH". |
| H-B | A linear-tree LightGBM regressor of the hunger *change*, which can extrapolate, detects onsets better than a hunger classifier. |
| H-C | Class weighting of the price part and recency weighting of the hunger part, each chosen by inner chronological validation on training data only, improve HIGH detection without excess false alarms. |
| H-D | News changes and short news accumulations carry a leading signal beyond news levels. |

## 3. The unified framework (every arm)

**Structure.** P(T43 HIGH at t+K) = P(regional hunger > 11.3 at t+K) × P(provincial price condition at t+K). Both
parts are LightGBM models fitted **once per origin** on pooled training pairs for K = 1..4, with K as an input, and
issue K = 1..4 from that one fit.
- Labels: every training label is posted or published before O(t), as in E92.
- Training: no test quarter, threshold or class weight is ever used in training.

**News.** The ten N3 news indicators are required inputs in every selectable arm.

**Structural projections.**
- Inputs only: the simulated mean food and gap at the target, computed from data at O(t). They are absent (NaN) at
  K = 4, where the base quarter is unpublished.
- LightGBM classifiers use native missing-value handling. The linear-tree regressor uses training-median imputation.

**Direction features** (from the same origin-time tables at origins t−1..t−3, all ≤ O(t)):
- changes in food and gap YoY over 1 and 2 quarters; rice acceleration; 4-quarter cumulative food YoY;
- changes in unemployment and remittances; ENSO and typhoon 3-origin runs; change in last hunger;
- rice × hunger-gap and ENSO-run × rice interactions;
- news: the change and 2-origin sum of the market, climate, employment, fish-kill, FSSI and coverage indicators.

**Hunger-part regional rows.** Province means; one row per origin and horizon.

**Arms:**

| Arm | Hunger part | Price part | Weighting | News |
|---|---|---|---|---|
| **M-U93-DIR** | LightGBM classifier | LightGBM classifier | — | yes |
| **M-U93-LINDIR** | Linear-tree LightGBM regression of hunger change, P = Φ((Ĥ − 11.3) / s), s = max(residual RMSE, random-walk sd for the gap) | LightGBM classifier | — | yes |
| **M-U93-LINDIR-W** | as LINDIR, with recency half-life ∈ {none, 4 quarters} chosen by inner validation on the last 3 training label quarters (RMSE) | LightGBM classifier with scale_pos_weight ∈ {1, 2, 4} chosen by inner validation on the last 3 training label quarters (log-loss) | inner-chosen | yes |

All arms use direction features.

**Ablations (never selectable):**
- M-U93-LINDIR-W-NONEWS: no news levels or changes.
- M-U93-LIN-W-NODIR: no direction features.

**Fallbacks.** Too little training data → the part's label frequency (classifiers), or the mean change (regressor).
Shares are reported.

## 4. Selection, K and comparisons (rules unchanged)

**Selection.** Lowest mean Brier over K = 1..3 on targets 2023-Q1..2024-Q4. K = 4 is excluded from selection because
E92 and S-COV do not issue it.

**PASS.** The E83 PASS rule, applied to every K separately.

**Validated K.** The largest K with PASS and temporal generalization at every horizon 1..K (E91 rule).

**Comparisons.**
- E92 M-LGB-DEC-S (pre-registered).
- E92 M-LGB-LIN (post-hoc, exploratory).
- S-COV, persistence, always-LOW and all E83 baselines.

**Reported.** Everything required by E91 §6. In addition:
- missed-HIGH lists, false-negative counts and calibration;
- the inner-validation choices;
- the hunger part alone against the regional SWS hunger outcome (one row per target quarter), compared with hunger
  persistence. This answers "food insecurity or price pressure".

**Disclosure.** All 13 target quarters were examined in E83–E92. Only the sealed quarters are unseen.
