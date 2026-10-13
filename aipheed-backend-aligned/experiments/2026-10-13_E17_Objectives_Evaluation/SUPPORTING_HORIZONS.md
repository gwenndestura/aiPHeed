# Supporting Analysis: Forecast Horizons for Regional Hunger, Provincial Food Inflation and Relative Price Pressure

**What this answers:** your earlier request for a "Forecast Accuracy and Reliable Forecast Horizon" table, using the same origin convention as the main evaluation (start of quarter t+1; target t+k).

**These are continuous targets. They are not the Chapter I classification target, and none of them is food insecurity.**

**Sources:**

- `SUPPORTING_HORIZONS.csv`
- `runs/supporting_20261013T034830Z/` (forecasts and per-quarter and per-province errors); replicate byte-identical

**Methods compared:**

| Role | Method |
|---|---|
| Baseline | Carry-forward of the latest available value |
| Model | Ridge (the E13 compact model) |

**Status rules:** "insufficient" means fewer than 5 test quarters. "Beats baseline" means the bootstrap interval of the MAE difference is below 0 **and** the model is better in at least 2/3 of quarters.

**Operational reliability is "not determinable" everywhere.** Neither Chapter I nor the project records give a defensible error tolerance.

## 1. Summary table

| Target | k | Test quarters | Rows | Model MAE / RMSE | Baseline MAE / RMSE | Model − baseline MAE (95% interval) | Quarters model better | Status |
|---|---|---|---|---|---|---|---|---|
| Regional hunger H (points) | 1 | 9 | 9 | 6.57 / 7.39 | **4.77** / 5.22 | +1.81 (+0.20, +3.33) | 3/9 | Does not beat baseline |
| | 2 | 7 | 7 | 8.78 / 10.21 | **4.28** / 5.66 | +4.50 (+1.67, +7.39) | 2/7 | Does not beat baseline |
| | 3 | 6 | 6 | 10.51 / 11.02 | **7.33** / 7.69 | +3.18 (+1.45, +4.88) | 1/6 | Does not beat baseline |
| | 4 | 4 | 4 | 11.34 / 12.25 | 4.04 / 5.35 | +7.30 | 0/4 | **Insufficient** |
| Food inflation F (points) | 1 | 11 | 55 | 2.52 / 2.82 | **2.44** / 3.19 | +0.08 (−0.42, +0.58) | 4/11 | Does not beat baseline |
| | 2 | 9 | 45 | 2.81 / 3.16 | 3.27 / 4.18 | −0.46 (−1.87, +0.84) | 3/9 | Does not beat baseline |
| | 3 | 7 | 35 | 3.28 / 3.85 | 3.20 / 4.13 | +0.08 (−1.74, +1.77) | 2/7 | Does not beat baseline |
| | 4 | 5 | 25 | 4.25 / 4.47 | **2.95** / 3.81 | +1.30 (−0.41, +2.92) | 1/5 | Does not beat baseline |
| Relative pressure D (points) | 1 | 11 | 55 | 1.19 / 1.62 | 1.36 / 1.85 | −0.17 (−0.37, +0.05) | 8/11 | Does not beat baseline |
| | 2 | 9 | 45 | **1.39** / 1.93 | 1.89 / 2.51 | **−0.50 (−0.75, −0.23)** | 8/9 | **Beats baseline** |
| | 3 | 7 | 35 | **1.60** / 2.21 | 2.50 / 3.20 | **−0.91 (−1.12, −0.71)** | 7/7 | **Beats baseline** |
| | 4 | 5 | 25 | **1.51** / 2.09 | 2.37 / 3.09 | **−0.86 (−1.15, −0.58)** | 5/5 | **Beats baseline** |

**Cross-check:** the k = 1 rows equal E13's v1 results exactly (H 4.77 / 6.57; F 2.44 / 2.52; D 1.355 / 1.189).

**Provincial rows are not independent.** The five provinces in a quarter are related, and D sums to zero. Intervals are bootstrapped by quarter, and the "test quarters" column is the effective sample.

## 2. Reading the D result honestly

- **The comparison is with carry-forward only.** The ridge forecast shrinks the latest D toward 0. As the horizon grows, the last observed D becomes stale, so a forecast near 0 beats it easily.
- **E13 Amendment 1 found** that a plain "no difference" forecast (D = 0) was as good as the ridge model on 2023-Q4..2025-Q4 at k = 1.
- **So this result shows that relative pressure regresses toward the regional average within 2–4 quarters.** It does not show skill at predicting **which** province will be above or below average. The quarters were also examined before.

## 3. Direct answers to the horizon questions

| Question | Answer |
|---|---|
| **Which target can aiPHeed forecast better than a simple baseline?** | Only **relative price pressure D**, and only against carry-forward at 2–4 quarters ahead, by shrinking toward the average. **Not** regional hunger. **Not** provincial food inflation. **Not** the Chapter I risk label (`BASELINE_COMPARISON.md`). |
| **What is the longest horizon with credible evidence of useful performance?** | **No horizon has credible evidence of operationally useful performance.** The D result reaches k = 4 (5 test quarters) against carry-forward, but it amounts to predicting no provincial difference, and no tolerance exists to judge it useful. |
| **How much historical evidence supports that?** | 5–11 test quarters per target and horizon (2023–2025), all previously examined. Only 16–20 quarters of history exist in total. |
| **Which targets or horizons remain exploratory?** | All of them. H at k = 4 is insufficient. Every D and F result is also exploratory because provincial CPI release dates are proxies. |
| **Can any result be described as a validated forecast of provincial food insecurity?** | **No.** No independent provincial food-insecurity outcome exists. |
