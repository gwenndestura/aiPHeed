# LEAD2_OPTIMIZATION protocol (frozen before any arm below is scored)

**Date:** 2026-10-27.

**Branch:** `aiPHeed/lead2-optimization`, from `c18008f`.

**Base system:** UNI-FINAL (FINAL_UNIFIED_LGBM, protocol `889e55e8…`).

**Evidence status.** Every quarter 2021–2026-Q3 has already been examined by earlier experiments. All results here are **development evidence**. No unseen outcome exists before SWS 2026-Q4. The frozen selection rule below limits, but does not remove, the risk of choosing an arm that is best by chance.

## 1. What was established before this protocol (diagnosis on saved UNI-FINAL predictions only)

**Reproduction.** `runner/reproduce.py` recomputes every reported metric independently from `FINAL_UNIFIED_LGBM/out/predictions.csv`. Lead 2: 65 rows, 13 target quarters (2023-Q2..2026-Q3), 17 HIGH, accuracy 0.769, balanced 0.635, precision 0.60, recall 0.353, F1 0.444, AUC 0.588, Brier 0.206. No duplicated rows.

**Causes:**

| # | Mechanism | Evidence |
|---|---|---|
| M1 | **Recall cap from the product rule.** P = π_H × π_P ≤ π_H. | In 2023-Q4 (π_H 0.26) and 2024-Q2 (π_H 0.29), 7 of the 17 HIGH rows can never reach 0.50. Maximum recall is 10/17 = 0.588 < 0.60 (R6), for any price model. |
| M2 | **π_H overconfident after the calm 2021–23 period** | σ of latest-reading errors at true horizon 3 was 1.8–1.9 points (from 2021–23 pairs) at the onset origins. From 1998–2020 BL hunger was above 11.3 in 66% of quarters, against 22% in 2021–2023-Q3. |
| M3 | **Two-quarter price discrimination is weak** | Price-condition AUC at Lead 2 is 0.67. With the hunger condition known exactly (oracle), π_P ≥ 0.5 gives precision 0.42 and 14 false alarms. |
| M4 | **The binary price label discards information** | The price condition is a threshold on continuous food YoY and the food-minus-headline gap. The classifier sees only 0/1. |

## 2. Fixed elements (unchanged from UNI-FINAL)

| Element | Value |
|---|---|
| Target | T43c, Chapter I: BL hunger(q) > 11.3 (2021–22 P60) AND province food YoY or gap > its 2021–22 P60 |
| Rows and origins | Eligible origins from `FINAL_UNIFIED_LGBM/out/testability_unified.json`; leads 1–15 stacked; issue date O(t); all issue-date cut-offs |
| Families | All 12 FIRI v2 families, `lead`, Pink Sheet world prices, news columns |
| Decision rule | HIGH at P ≥ 0.50 (the approved dashboard rule) |
| Reliability rule | R1–R7 (FINAL_THESIS_OBJECTIVES §7, `ch1_lib.decide`); maximum reliable lead = consecutive passes from Lead 1 |
| Baselines | ALWAYS-LOW, PERSIST-SI, CLIM (`uni_lib.baselines`) |

## 3. Arms

### Price term π_P (one unified LightGBM across leads, 12 families)

| Arm | Change from U2 | Mechanism |
|---|---|---|
| **P0** | U2 as served | – |
| **P1 (FE)** | + engineered dynamics, all computed from data published before O(t): F_ex and G_ex (latest 3 published months' food YoY and gap minus threshold); food-index log change over 1 and 6 months; food YoY acceleration (m0 vs m0−3); 6-month volatility of monthly food changes; momentum projections A1_food_d and A1_gap_d (index grown at its trailing 6-month mean monthly log change instead of held flat; monotone +1); Region IV-A rice CPI YoY and 3-month log change (PSA, from E114 `cov_cpi.csv`, month ≤ m0) | M3 |
| **P2 (FE+TUNE)** | P1 with a wider grid chosen by the same inner chronological validation (last 4 training origins, log-loss). Grid: 24 configurations drawn with seed 2028 from leaves {2,3,4,7} × learning rate {0.03,0.05,0.1} × trees {50,100,200,400} × min child {10,15,25} × subsample {0.8,1.0} (freq 1) × colsample {0.7,1.0} × L1 {0,1} × L2 {1,5,10} × class weight {none, balanced}, plus the 8 UNI configurations | M3 |
| **P3 (REG)** | P1 features. Two LightGBM **regressors** (UNI grid, inner validation on squared error) predict the continuous excesses F(q) − thr_food and (F − HL)(q) − thr_gap. Each is converted to a probability with σ = the RMSE of that regressor's inner-fold predictions (fallback 2.0), and the two are combined as P = 1 − (1 − Φ(ŷF/σF)) (1 − Φ(ŷG/σG)). Monotone +1 on A1_food, A1_gap, A1_food_d, A1_gap_d. | M4 |

### Hunger term π_H

| Arm | Definition | Mechanism |
|---|---|---|
| **H0** | π_H as served | – |
| **H1 (AR21)** | Direct regression at the true horizon h on BL quarters whose rounds were all published before O(t), 2021+ verified series: H(q+h) = a + b·H(q), b clipped to [0, 1]. P = 1 − T_{n−2}((11.3 − ŷ)/s_pred), with s_pred the prediction standard error (residual sd × √(1 + 1/n + (x − x̄)²/Sxx)). Fewer than 6 pairs → H0. | M1, M2 |
| **H2 (AR98)**, **sample b, sensitivity only** | As H1 on BL 1998+: E114 SWS tables, pre-2021 non-commissioned rounds with release date = label month end + 60 days (rule), plus the 2021+ verified series | M1, M2 |

## 4. Selection and serving (decided now)

**Primary arms:** {P0, P1, P2, P3} × {H0, H1} = 8 combinations, P = π_H × π_P.

**Selection.** The adopted arm has the lowest **Lead-2 development Brier** on T43c (targets ≤ 2024-Q4). Ties within 0.0005 go to the earlier arm in the order P0H0, P1H0, P2H0, P3H0, P0H1, P1H1, P2H1, P3H1.

**Sample b.** H2 is scored with P0 and with the selected price arm. It is reported separately and is never adopted or served without a formal scope revision by the user, because it uses pre-2021 data.

**Reporting for every arm.** Leads 1–15 R1–R7 verdicts, maximum reliable lead, Lead-2 metrics (accuracy, balanced accuracy, precision, recall, F1, AUC, average precision, Brier, confusion matrix, false negatives, per target quarter, rising and falling quarters, onsets) and a 90% cluster-bootstrap accuracy CI by quarter.

**Multiplicity.** The adopted arm's Lead-2 Brier is compared with P0H0 (one-sided cluster bootstrap), Holm-adjusted over the 7 non-baseline primary arms.

**Serving.** The adopted arm replaces UNI-FINAL on the dashboard only if all of the following hold:
- (a) it is reliable at Lead 1;
- (b) its maximum reliable lead is ≥ 1;
- (c) its Lead-1 Brier is not worse than UNI-FINAL at one-sided p < .10.

If its maximum reliable lead is ≥ 2, the dashboard states the new horizon. Otherwise Lead 2 stays experimental.

**Leakage audit before scoring.** At 6 origins (2023-Q2, 2023-Q4, 2024-Q2, 2024-Q4, 2025-Q3, 2026-Q2), randomize every value published on or after O(t) in the new inputs as well as the old ones: SWS rounds, CPI index/YoY, regional rice CPI, Pink Sheet and news. The P1–P3 and H1 forecasts at that origin must be identical.

## 5. After scoring

Post-hoc analyses (feature ablation by family, news ablation, permutation importance, calibration bins, chronological blocks, survey-design periods) are labelled post-hoc and cannot change the adopted arm.
