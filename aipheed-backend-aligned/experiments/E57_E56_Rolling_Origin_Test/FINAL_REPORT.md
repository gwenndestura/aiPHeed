# E57: does E56 forecast food-insecurity risk reliably across quarters?

**Date:** 2026-10-18. **Branch:** `e46-lead2-policy`, not pushed.

**Procedure**
- Evaluation only: no tuning, no new model.
- `PROTOCOL.md` was frozen at 8baf6d3 before any score.
- Forecasts were sealed (39725f0, sha `4d52b1f3…`) before any label was read.
- The sealed forecasts reproduce the committed E56 predictions exactly (max difference 0.0).

## 1. Answer

**No. E56 cannot yet be called reliable for future two-quarter forecasting.** Across every eligible quarter it scores **0.720** (36/50 province-quarters), and all three pre-registered reliability conditions fail:

| Condition | Result |
|---|---|
| Pooled accuracy ≥ 0.75 | **0.720**, fails |
| Quarter-cluster 95% lower bound ≥ 0.75 | **0.58** (moving-block: 0.60), fails |
| ≥ 75% of quarters at accuracy ≥ 0.75 | **6 of 10 (60%)**, fails |

**Why this differs from E56's 0.778:**
- E56's figure used 45 rows. It left out target 2024-Q2 only because the E38-framework baselines could not forecast it.
- Including that quarter, where E56 scored 1/5, gives the full-period figure.
- Every quarter that can be evaluated is included here. Nothing was retuned.

**What E56 does reliably:**
- It beats naive persistence and the training-majority rule on Brier, with CIs excluding 0.
- It is right when food stress is falling or stable.

**Where it fails:**
- It misses rises in risk: HIGH recall 0.40 in rising-stress quarters.
- It misses rises in regional hunger (2024-Q2).
- These are the cases an early-warning system exists for.

## 2. Eligible quarters

**Rolling origins:** 2023-Q4..2026-Q1, each issued on day 1 of the following quarter, with only data published by then.

**Targets:** exactly two quarters ahead, **2024-Q2..2026-Q3**: 10 quarters × 5 provinces = 50 rows, 18 HIGH.

**Not evaluable** (no labels invented):

| Targets | Reason |
|---|---|
| 2022-Q2..2023-Q4 | labelled, but too little training history at the origin (data start 2021; fewer than 6 price-training quarters) |
| 2024-Q1 | fewer than 6 regional hunger training pairs |
| 2022-Q1 | no SWS round |
| 2026-Q4, 2027-Q1 | outcomes not yet observed |

## 3. Quarter-by-quarter results (E56; `tables/quarter_by_quarter.csv`)

| Issue | Target | n | Actual H/L | Pred H/L | Correct | Acc | Bal | Prec H | Rec H | Prec L | Rec L | Brier | AUC | Persist acc | Majority acc | Data status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2023-Q4 | **2024-Q2** | 5 | 4/1 | 0/5 | 1 | **0.20** | 0.50 | – | 0.00 | 0.20 | 1.00 | 0.53 | 0.25 | 0.2 | 0.2 | complete |
| 2024-Q1 | 2024-Q3 | 5 | 1/4 | 3/2 | 3 | 0.60 | 0.75 | 0.33 | 1.00 | 1.00 | 0.50 | 0.17 | 1.00 | 0.6 | 0.8 | poverty in config |
| 2024-Q2 | 2024-Q4 | 5 | 3/2 | 1/4 | 3 | 0.60 | 0.67 | 1.00 | 0.33 | 0.50 | 1.00 | 0.32 | 0.67 | 0.4 | 0.4 | complete |
| 2024-Q3 | 2025-Q1 | 5 | 4/1 | 3/2 | 4 | 0.80 | 0.88 | 1.00 | 0.75 | 0.50 | 1.00 | 0.16 | 1.00 | 1.0 | 0.2 | complete |
| 2024-Q4 | 2025-Q2 | 5 | 3/2 | 4/1 | 4 | 0.80 | 0.75 | 0.75 | 1.00 | 1.00 | 0.50 | 0.19 | 0.83 | 0.6 | 0.4 | complete |
| 2025-Q1 | 2025-Q3 | 5 | 2/3 | 4/1 | 3 | 0.60 | 0.67 | 0.50 | 1.00 | 1.00 | 0.33 | 0.22 | 0.83 | 0.8 | 0.6 | poverty in config |
| 2025-Q2 | 2025-Q4 | 5 | 0/5 | 0/5 | 5 | 1.00 | – | – | – | 1.00 | 1.00 | 0.08 | – | 0.2 | 1.0 | poverty in config |
| 2025-Q3 | 2026-Q1 | 5 | 0/5 | 0/5 | 5 | 1.00 | – | – | – | 1.00 | 1.00 | 0.09 | – | 0.4 | 1.0 | poverty in config |
| 2025-Q4 | 2026-Q2 | 5 | 1/4 | 0/5 | 4 | 0.80 | 0.50 | – | 0.00 | 0.80 | 1.00 | 0.19 | 0.25 | 0.4 | 0.8 | complete |
| 2026-Q1 | 2026-Q3 | 5 | 0/5 | 1/4 | 4 | 0.80 | – | 0.00 | – | 1.00 | 0.80 | 0.18 | – | 1.0 | 1.0 | complete |

Every evaluated origin had complete inputs: remittances (quarter t−1) run to 2025-Q4, and the gap affects only the operational origins 2026-Q2/Q3. No protocol deviation occurred.

**What the quarters show:**
- **2024-Q2:** regional hunger jumped from 10.3% to 19.6%. Only the 2023-Q3 round had been posted at the issue date, so the hunger gate was 0.21 and all four HIGH provinces were missed.
- **2025-Q4 and 2026-Q1:** perfect, but only because nothing was HIGH. Always-LOW does the same.

**Quarter accuracy summary:**

| Statistic | Value |
|---|---|
| mean | 0.72 |
| median | 0.80 |
| min | 0.20 (2024-Q2) |
| max | 1.00 |
| quarters ≥ 0.75 | 6 / 10 |

## 4. Pooled results and baselines (identical 50 rows, two quarters ahead)

| Model | Acc | Cluster CI | Block CI | Bal | Rec H | Rec L | Brier |
|---|---|---|---|---|---|---|---|
| **E56-TUNED** | **0.720** | 0.58–0.84 | 0.60–0.88 | **0.684** | 0.556 | 0.812 | **0.214** |
| E55-LGBM | 0.680 | 0.54–0.82 | 0.60–0.82 | 0.641 | 0.500 | 0.781 | 0.221 |
| Persistence | 0.560 | 0.38–0.74 | 0.42–0.70 | 0.535 | 0.444 | 0.625 | 0.440 |
| Training majority (always LOW) | 0.640 | 0.46–0.82 | | 0.500 | 0 | 1 | 0.360 |
| Climatology (probability) | 0.640 | | | 0.500 | 0 | 1 | 0.304 |
| Province climatology | 0.640 | | | 0.500 | 0 | 1 | 0.293 |
| E38 (production; Eq. 3 target, **non-equivalent**, 40 rows) | 0.175 | | | 0.229 | 0.385 | 0.074 | 0.628 |

**Does E56 add value consistently?**

| Comparator | Quarters with better Brier | Sign test p | Paired Brier [95% CI] | Reading |
|---|---|---|---|---|
| persistence | 7 of 10 | 0.34 | −0.22 [−0.41, −0.06] | better |
| training majority | 7 of 10 | 0.34 | −0.13 [−0.29, −0.01] | better, just |
| climatology | 5 of 10 | 1.0 | −0.08 [−0.19, 0.001] | not demonstrated |
| E55-LGBM | 5 of 9 (1 tie) | 1.0 | [−0.024, 0.007] | no difference |

The accuracy advantage over E55 (+2 rows) is not meaningful.

**Calibration:**
- CITL −0.03; slope **0.55** (over-confident).
- Reliability: forecasts in 0.0–0.2 were HIGH 43% of the time (the 2024-Q2 misses); in 0.2–0.4, 7%; in 0.8–1.0, 83%.

## 5. Performance across conditions (`tables/strata.csv`)

| Stratum | n (HIGH) | E56 acc | Bal | Rec H | Brier | Persistence | Majority |
|---|---|---|---|---|---|---|---|
| Early (2024-Q2..2025-Q2) | 25 (15) | **0.60** | 0.62 | 0.53 | 0.28 | 0.56 | 0.40 |
| Late (2025-Q3..2026-Q3) | 25 (3) | 0.84 | 0.77 | 0.67 | 0.15 | 0.56 | **0.88** |
| Food stress **rising** | 15 (10) | **0.53** | 0.60 | **0.40** | 0.35 | 0.40 | 0.33 |
| Food stress falling | 25 (4) | 0.80 | 0.78 | 0.75 | 0.15 | 0.48 | 0.84 |
| Food stress stable | 10 (4) | 0.80 | 0.79 | 0.75 | 0.17 | 1.00 | 0.60 |
| Regional hunger up | 25 (12) | 0.60 | 0.59 | 0.42 | 0.28 | 0.64 | 0.52 |
| Regional hunger down | 25 (6) | 0.84 | 0.84 | 0.83 | 0.15 | 0.48 | 0.76 |

**Reading:**
- The late-period strength comes from a period with almost no HIGH rows. There, always-LOW does better.
- When risk was rising, the model detected 4 of 10 HIGH province-quarters.
- The rising-stress and hunger-up results are the clearest evidence against reliability for early warning.

## 6. Does E56 distinguish the provinces?

**Per province:**

| Province | Acc | Observed HIGH share | Mean forecast | Ranked highest |
|---|---|---|---|---|
| Quezon | 0.80 | 0.60 | 0.64 | 8 of 10 quarters |
| Rizal | 1.00 | 0.00 | 0.22 | 0 |
| Laguna | 0.70 | 0.50 | 0.38 | 1 |
| Batangas | 0.70 | 0.30 | 0.30 | 1 |
| **Cavite** | **0.40** | 0.40 | 0.40 | 0 |

**Within-quarter discrimination:**
- E56's within-quarter AUC is **0.706**, its mean Spearman correlation 0.31.
- **Province climatology**, each province's own past HIGH share and no model at all, reaches **0.765** (Spearman 0.42).
- Persistence reaches 0.647.

**Other checks:**
- E56 gives all five provinces the same decision in 4 of 10 quarters.
- Kendall's W of its province ranking across quarters is 0.50, a moderately stable ordering (Quezon usually highest).

**Conclusion:** E56 does produce different risks for different provinces, and its average levels match each province's observed share closely. But its within-quarter ranking adds nothing beyond knowing which provinces were historically more often under price pressure. Its genuine contribution is in timing (which quarters are HIGH), not in ranking provinces.

## 7. Limiting factors and what would resolve them

1. **Too few quarters.**
   - 10 evaluable quarters, two of them with no HIGH row.
   - Quarter accuracy ranges from 0.2 to 1.0, so any pooled figure moves by about ±0.13.
   - About 16 quarters would be needed even if the true accuracy were 0.85 (E55 sample-size table).
   - **Resolution:** the frozen 2027-Q1..Q4 forecasts, and continued quarterly scoring.
2. **The hunger part is not forecastable from the available data.**
   - Regional SWS hunger is one series. It changed regime once (2023-Q4 to 2024-Q2), and the posting lag hid that change at the issue date.
   - **Resolution:**
     - issue the forecast after the quarter's SWS release (E46 D4: the 15th-of-month issue time, an adviser decision);
     - or add a leading hunger indicator.
3. **Rising-risk quarters are under-detected** (HIGH recall 0.40).
   - The model starts from the CPI base-effect projection, which lags price surges.
   - Any correction would be a new tuning cycle on these same quarters, so none is made here (PROTOCOL section 6).
4. **No provincial food-insecurity outcome exists.**
   - Provincial differences come only from food prices.
   - **Resolution:** CBMS or provincial FIES data.

## 8. What this means for the thesis and the dashboard

**Thesis.** E56 can be presented as follows:
- the best available LightGBM forecaster of the T43 risk indicator;
- it beats persistence and the majority rule, with 0.720 two-quarter accuracy across all evaluable quarters (0.778 on the 45 rows shared with every baseline);
- **not** a reliable early-warning model yet: it misses rising risk, and its reliability rests on 10 quarters;
- the 75% goal is not met across all evaluable quarters.

**Production.** No change is recommended. The `e56` mode stays experimental. Its 2027-Q1 forecast (all provinces LOW) should be presented with that caveat.

**Independent test.** It remains pending: score the frozen 2027-Q1 forecast when the 2027-Q1 SWS round and March 2027 CPI are published.

## 9. Files

**Experiment folder** (`E57_E56_Rolling_Origin_Test/`):
- `PROTOCOL.md`; `sealed/predictions.csv` (+ sha256);
- `runner/e57_predict.py`, `runner/e57_score.py`;
- `runs/<stamp>/{rows.csv, results.json}`;
- `tables/`: `quarter_by_quarter.csv`, `pooled_models.csv`, `strata.csv`, `province_table.csv`;
- `runs_console.txt`.

**Code note.** `e55_lib.add_poverty` fails on an empty training frame, which only happens at ineligible origins. E57 checks eligibility without the poverty column first. No E55/E56 result is affected.

**Not changed:** models, serving, the production default (E38), the frontend.
