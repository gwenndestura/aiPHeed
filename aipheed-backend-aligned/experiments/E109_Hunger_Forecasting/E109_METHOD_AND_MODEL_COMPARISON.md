# E109 Method and model comparison

## 1. The simple workflow (as implemented)

1. **Collect** SWS Balance Luzon hunger (non-commissioned rounds) and the 12 FIRI indicator families.
2. **Check** sources, geography and publication dates. 12 SWS values were re-verified, and the commissioned and respondent-base issues were flagged.
3. **Build** features from data published before each issue date (day 1 of the quarter): E107's 13 columns, averaged over the five provinces.
4. **Train** on past quarters whose hunger outcome had been published (the real-time vintage).
5. **Predict** Balance Luzon hunger 1–4 quarters ahead, with an 80% interval and P(hunger above a threshold).
6. **Compare** with simple baselines on identical quarters, one row per quarter.
7. **Decide** the maximum reliable lead with the frozen rule.
8. **Explain** with LightGBM SHAP shares (associations, not causes).
9. **Publish** the forecast, its interval, data freshness and validation status (read-only API; dashboard unchanged).

**What the evidence changes.** Steps 4–5 add nothing over the latest published SWS reading (section 3). The simplest credible method is therefore: *report the latest SWS Balance Luzon reading as the one-quarter outlook, with an interval of about ±6 points (80%), and mark longer horizons as unvalidated.*

## 2. Candidates and baselines

| Name | What it does | Parameters fitted |
|---|---|---|
| RW | latest published reading | none |
| MEAN | mean of all published quarters | none |
| MA2 | mean of the last two published quarters | none |
| SEAS | same quarter one year earlier (else RW) | none |
| LL | Kalman local level; observation noise from SWS's ±4% margin; state noise from training data | 1 |
| RIDGE | RW + ridge regression of the change on the 13 regional columns (α = 10) | 13 |
| **LGBM (primary)** | RW + LightGBM (depth 1, 25 or 75 trees, min leaf 3) on the change, all 12 families eligible | trees chosen by inner MAE |

## 3. Results on the primary series (identical quarters; development evidence)

**Lead 1: 9 quarters (2024-Q2..2026-Q3).** MAE and RMSE are in percentage points. Skill = 1 − MAE/MAE_RW.

| Method | MAE (block 95% CI) | RMSE | Bias | Skill | Last 4 MAE | Within ±4 | DM p vs RW |
|---|---|---|---|---|---|---|---|
| **RW** | **3.72 (1.94–5.65)** | 4.74 | −1.38 | 0 | **0.94** | 56% | — |
| LGBM | 4.04 (1.99–6.57) | 5.40 | −0.10 | −0.09 | 1.38 | 56% | 0.72 |
| MA2 | 4.46 (3.32–5.81) | 4.84 | −1.67 | −0.20 | 3.36 | 44% | — |
| RIDGE | 4.49 (2.14–7.06) | 5.94 | −1.44 | −0.21 | 1.77 | 56% | 0.85 |
| LL | 4.53 (2.33–6.97) | 5.77 | −2.86 | −0.22 | 1.05 | 44% | 0.80 |
| SEAS | 5.29 | 6.43 | −2.26 | −0.42 | 2.84 | 44% | — |
| MEAN | 6.98 | 7.77 | −6.98 | −0.87 | 5.58 | 33% | — |

**In simple language.** One quarter ahead, the latest SWS reading misses the next reading by about 3.7 points on average, roughly the survey's own margin of error. No model, including LightGBM with all 12 indicators, is closer. LightGBM is about 0.3 points worse on average, and the difference is not statistically meaningful (p = 0.72).

**Quarter by quarter, Lead 1** (forecast vs observed hunger, %):

| Target | Observed | RW | LGBM | LL | RIDGE |
|---|---|---|---|---|---|
| 2024-Q2 | 19.6 | 14.3 | 15.5 | 11.4 | 15.9 |
| 2024-Q3 | 18.1 | 15.3 | 15.4 | 12.3 | 15.9 |
| 2024-Q4 | 25.3 | 19.6 | 20.5 | 13.9 | 20.0 |
| 2025-Q2 | 16.2 | 25.3 | 28.7 | 21.9 | 28.2 |
| 2025-Q3 | 23.8 | 17.0 | 17.2 | 18.4 | 13.7 |
| 2025-Q4 | 16.7 | 16.2 | 16.3 | 17.7 | 12.2 |
| 2026-Q1 | 22.4 | 23.8 | 25.5 | 22.1 | 23.8 |
| 2026-Q2 | 17.3 | 16.7 | 19.3 | 18.0 | 16.5 |
| 2026-Q3 | 23.6 | 22.4 | 23.7 | 21.4 | 23.8 |

- **2024 surge:** every method lagged the rise from 14% to 25%.
- **2025 drop:** after the respondent-base change, hunger fell from 25.3% to 16.2%, and every method overshot.
- **Zig-zag since then:** 2025-Q2 onward alternates between about 16–17% and 22–24%. The swings exceed the ±4–6 margin, but six quarters are not enough to establish a seasonal pattern.

**Leads 2–4 (5–7 quarters each, below the 8-quarter minimum).**

| Lead | Quarters | RW | MA2 | LL | RIDGE | LGBM |
|---|---|---|---|---|---|---|
| 2 | 7 | 4.77 | **3.92** | 4.73 | 7.45 | 5.62 |
| 3 | 6 | 4.08 | **3.26** | 3.73 | 3.87 | 4.49 |
| 4 | 5 | 3.25 | **3.19** | 3.86 | 8.53 | 4.04 |

- LightGBM never beats the best baseline.
- MA2 (the average of the last two readings) is best at Leads 2–4 but cannot be judged on 5–7 quarters.

**Binary readings, Lead 1** (research-defined thresholds; accuracy / balanced accuracy / Brier):

| Rule | HIGH quarters | LGBM | RW (persistence) | Status |
|---|---|---|---|---|
| B1 > 11.3% | 9 of 9 | 1.00 / — / 0.01 | 1.00 / — | insufficient evidence (one class) |
| B2 > 15% | 9 of 9 | 1.00 / — / 0.09 | 0.89 / — | insufficient evidence (one class) |
| B3 > 20% | 4 of 9 | **0.78 / 0.78 / 0.23** | 0.67 / 0.65 / 0.22 | LGBM and RIDGE meet the binary rule ("provisional"), on a 7/9 vs 6/9 difference |
| B4 rise > 4 pts | 3 of 9 | 0.67 / 0.50 / 0.29 | 0.67 / 0.50 / 0.27 | not reliable |

B3 is one of four sensitivity thresholds, and its advantage over persistence is a single quarter. It is reported, not relied on.

**Sensitivity series.** Lead-1 MAE for RW / LGBM:

| Series | RW | LGBM |
|---|---|---|
| S-ALL (with the commissioned round) | 3.81 | 4.31 |
| S-PROD (the E107/E108 series) | 3.80 | 4.51 |
| S-HH (household heads only) | 3 quarters | 3 quarters |

**The ranking is the same under every series.**

## 4. Selection rule and choice

- **Pre-registered rule:** LGBM is primary. LL or RIDGE would replace it only by passing more criteria **and** being better at p < 0.10. Neither does, so the protocol's candidate remains LGBM.
- **The evidence-based recommendation:** for practical use, the **latest published SWS reading (RW)** is the forecast to report.
  - It is simpler, at least as accurate at Lead 1, and best on the last four quarters (MAE 0.94).
  - LightGBM is retained as the required 12-indicator research model. Its value over RW is **not demonstrated**.

## 5. Why the E108 models do not transfer

The E108 LightGBM and the price-only logistic forecast **provincial food-price pressure**, multiplied by a hunger outlook. Their Lead-1 skill came from the CPI base-effect projection. That projection predicts prices, not hunger: in E109 the A1 price family carries 36% of LightGBM's explanation, but the model still does not beat RW on hunger.

**Food-price pressure is not a forecast of hunger** in these data.
