# Rolling-Origin Backtest at the Required Horizon (h = 5), Baseline Comparison and Feature Ablation

**Sources:**

- run `runs/20261013T035829Z/` (replicate `runs/20261013T035855Z/`, byte-identical):
  - `rolling_origin_predictions.csv` (sealed before scoring)
  - `scored_predictions.csv`
  - `per_origin_errors.csv`
  - `metrics.json`
- `METRICS_SUMMARY.csv`

**Information set at each origin:** observations of quarters ≤ T − 5, the same construction as the 2027-Q1 forecast. All candidates are compared on the **same common origins**.

## 1. Regional hunger H at h = 5 (primary)

| Item | Value |
|---|---|
| Valid common origins | **3**: 2025-Q2, 2025-Q3, 2025-Q4 |
| Evidence label | **Exploratory only** (fewer than 8). Two of the three are the disputed supplementary-round quarters. |
| Statistical tests | None presented as evidence |

**Absolute error by origin** (percentage points):

| Candidate | 2025-Q2 | 2025-Q3 | 2025-Q4 | MAE | RMSE | Bias |
|---|---|---|---|---|---|---|
| **C1 Carry-forward** (baseline) | 0.85 | 4.20 | 1.40 | **2.15** | 2.60 | −1.22 |
| C2 Historical mean | 4.56 | 11.55 | 4.00 | 6.70 | 7.53 | −6.70 |
| C3 Drift | 0.87 | 2.43 | 2.46 | **1.92** | 2.06 | −0.28 |
| C4 Ridge AR(1), existing | 5.46 | 16.63 | 7.37 | 9.82 | 10.96 | −9.82 |
| C5 Ridge AR, two lags (new) | 1.51 | 17.95 | 7.94 | 9.13 | 11.37 | −9.13 |
| C6 Damped Theil–Sen trend (new) | 0.92 | 0.55 | 5.14 | 2.20 | 3.03 | +1.84 |
| C7 Ridge + regional food inflation + unemployment (new) | 3.65 | 12.40 | 4.32 | 6.79 | 7.87 | −6.79 |

**The frozen rule against carry-forward:**

| Candidate | (1) Lower MAE | (2) Wins in a strict majority | (3) Later half not worse | (4) No single-quarter dependence | Passes? |
|---|---|---|---|---|---|
| C3 Drift | Yes (1.92 vs 2.15) | **No** (1 of 3) | Yes | **No** | **No** |
| C6 Damped trend | No | No (1 of 3) | No | No | No |
| C2, C4, C5, C7 | No | No | No | No | No |

**No candidate satisfies the frozen rule, so carry-forward is kept.** Drift's lower MAE comes from one quarter (2025-Q3); in the other two quarters it is no better.

**Feature ablation at h = 5** (same 3 origins; diagnostics, not selectable):

| Configuration | MAE |
|---|---|
| C1 Carry-forward | **2.15** |
| C4 H only (AR1) | 9.82 |
| C7a H + regional food inflation | 11.62 |
| C7b H + unemployment | 3.53 |
| C7 H + food inflation + unemployment | 6.79 |

**Reading the ablation:**

- **Regional food inflation makes the AR model worse,** as in E13.
- **Unemployment reduces the AR model's error a lot** (9.82 → 3.53).
- **No feature group brings a fitted model near carry-forward.** On three origins these differences cannot be told apart from noise.

**Why the fitted models fail at h = 5:**

- They train on 6–9 pairs drawn mostly from the calm 2021–2023 period, so they predict a return toward about 10%.
- They have a large negative bias (−6.7 to −9.8 points) during the 2024–2025 high period.

## 2. Provincial food inflation F at h = 5 (secondary)

**5 common origins** (2024-Q4..2025-Q4), 25 province rows. **Exploratory only.**

| Candidate | MAE | RMSE | Bias | Early MAE | Late MAE |
|---|---|---|---|---|---|
| **F1 Carry-forward** | **2.95** | 3.81 | +1.41 | 3.98 | 2.27 |
| F2 Pooled mean | 3.38 | 3.53 | +2.84 | 2.90 | 3.69 |
| F3 Province mean | 3.59 | 3.98 | +2.84 | 3.45 | 3.69 |
| F4 Ridge AR (existing) | 4.25 | 4.47 | +3.94 | 3.24 | 4.93 |

**F4 fails the rule against all three baselines.** Carry-forward is kept.

## 3. Relative pressure D at h = 5 (secondary)

**5 common origins**, 25 province rows. **Exploratory only.**

| Candidate | MAE | RMSE | Early MAE | Late MAE |
|---|---|---|---|---|
| D1 Carry-forward | 2.37 | 3.09 | 3.27 | 1.76 |
| **D2 Zero** ("no provincial difference") | **1.27** | 1.78 | 1.96 | 0.81 |
| D3 Province mean | 2.01 | 2.56 | 2.64 | 1.59 |
| D4 Ridge shrink (existing) | 1.51 | 2.09 | 2.30 | 0.98 |
| D5 Ridge D + province mean (existing) | 1.59 | 2.17 | 2.36 | 1.08 |

**Against each baseline:**

- D4 and D5 pass all four conditions against carry-forward (5 of 5 origins) and against the province mean.
- Both **fail against the zero baseline** (0 of 5 and 1 of 5 origins).

**No model is selected,** because the frozen rule requires beating every baseline. Five quarters ahead, the best forecast of relative price pressure is "**no difference from the regional average**".

## 4. Diagnostics at shorter horizons (not validation of h = 5)

**MAE on each horizon's own common origins:**

| Target | h | Origins | Best baseline | Best fitted model |
|---|---|---|---|---|
| H | 1 | 10 | C1 4.29 | C7 4.13 (C3 4.49, C6 4.49) |
| H | 2 | 8 | C1 4.32 | C6 4.64, C3 4.66 |
| H | 3 | 7 | C1 5.46 | C6 6.40, C3 6.24 |
| H | 4 | 5 | C1 7.49 | C6 8.04 |
| F | 1–4 | 13, 11, 9, 7 | F1 2.00 / 2.44; F2 3.03 / 3.10 at h = 3–4 | F4 2.24 / 2.52 / 2.81 / 3.28 |
| D | 1–4 | 13, 11, 9, 7 | D1 0.90 at h = 1; D2 1.29 / 1.37 at h = 3–4 | D5 0.88 (h = 1); D4 1.19 (h = 2) |

**These numbers are not an evaluation of h = 5.** The rule was not applied to them.

- **h = 1:** C7 is marginally below carry-forward for H (4.13 vs 4.29), and D5 is marginally below carry-forward for D (0.88 vs 0.90).
- **h = 2:** the D ridge models (1.18–1.19) are below every D baseline (best 1.36).
- **h = 3:** F4 (2.81) is below every F baseline (best 3.03).
- **h = 4:** the baselines are best for all three targets.
- **Regional hunger:** carry-forward is best at h = 2–4.

The pattern changes from horizon to horizon, which is itself a sign of instability.
