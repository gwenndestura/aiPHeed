# E128 previous experiment failure analysis

**Sources:** the E-series reports in `experiments/` and the git history of the aiPHeed branches. Every 2021–2026 quarter was inspected by these experiments, which is why E128's evaluation is labelled retrospective.

## 1. What earlier experiments found

| Experiment | Target and level | Lead 1 | Lead 2 | Stated cause |
|---|---|---|---|---|
| E25–E27 | Province labels, 2021+ | None qualifies | — | Target structure; always-HIGH best Brier |
| E41–E44 | T43 province-quarter | — | ≤ 0.69 | ≥ 75 % degenerate; AUC ~0.78 needed |
| E51 | Thesis label | — | — | **Label saturated** |
| E89–E95 | Unified LightGBM, T43 | 0.85 | 0.80, recall 0.31 | cumF4 regime memory; 2024-Q2 unlearnable |
| E108 / CH1 | T43c, 65 province rows | 0.89 to 0.91 | Below climatology | Price part unpredictable two quarters ahead |
| LEAD2 series | T43c Lead 2 | — | 0.80, recall 10/17; **fails R6** | All misses are price-part misses; 7 HIGH quarters; CPI timing |
| E109–E113 | SWS hunger level | Nothing beats the latest SWS reading | — | Hunger persistence |
| E114 | SWS change, 4 areas, pre-2021 test | Beats persistence on level | — | Damped mean reversion better still; triggers add nothing |
| E117 | 2003–26 pooled | Only palay/corn (C3) helps | Nothing | — |

## 2. Causes tested again in E128 (2021–2026, regional)

| Cause | Evidence in E128 | Verdict |
|---|---|---|
| **Insufficient sample** | 20 independent quarters in total; outer rows 13 / 8 / 7 / 6 at Leads 1–4; R1 needs 10 quarters **and** 40 rows | **Primary cause.** Structural; no model choice can fix it. |
| **Target definition / class imbalance** | T1: 11 HIGH quarters in a row since 2023-Q4; 2 LOW outer rows at Lead 1, 0 at Leads 2–4 | **Primary cause.** Balanced accuracy and AUC are not evaluable. |
| **Distribution shift** | Training quarters (2021–23) sit at 9–12 % hunger; later targets at 15–25 %. LightGBM at T1 Lead 4 learned "LOW" from the old regime: 0 / 6 correct, Brier 0.704. | **Major cause** at long leads |
| **Target noise** | SWS area margin of error ±6 points; median quarter change 2.35 | **Major for any change or relative target** (T4) |
| **Overfitting** | Training accuracy 0.86–1.00 vs outer 0.00–0.88 (`E128_OVERFITTING_ANALYSIS.md`) | **Present** in every learned model |
| **Excess features for the sample** | 25 features vs 6–18 training rows per fold | Contributes to overfitting; nothing larger is supportable |
| **Feature relevance / trigger groups** | Ablation effects change sign across leads; no group helps consistently (`E128_FEATURE_GROUP_ABLATION.csv`) | **No demonstrated trigger value** |
| **Spurious regime proxies** | SHAP at T1 Lead 2 is 76 % ONI. ONI moved from La Niña to El Niño as hunger rose: one coincident episode, not a mechanism. | Present |
| **Geographic coverage** | Employment, remittance, ONI and GDELT are national; there is no provincial target | Limits interpretability; does not fail by itself |
| **Publication delays / staleness** | Features lag the issue by 1–2 quarters (production 2). The newest SWS quarter is usually t−1, so the true SWS horizon is k+1. | Shrinks the usable signal at every lead |
| **Unverified timing** | CPI release dates are partly rule-based (`rule_unverified`) | Known risk; E119 leakage checks passed |
| **Calibration** | Probabilities are miscalibrated at every lead (`E128_CALIBRATION_ANALYSIS.md`) | Present |
| **Model architecture** | LightGBM does not beat Logistic Regression, PSA-only or NLP-only at any lead (Holm) | Architecture is **not** the bottleneck |

## 3. Root cause, in order

1. **Fundamental limits of the observations.** One regional series, 20 quarters, about 2 regimes.
2. **Target definition.** The fixed threshold is saturated in the evaluable period. Relative definitions are dominated by sampling noise.
3. **Validation design is not the cause.** It is chronological, tuned inside folds, and identical across models. Weaker validation would only hide the problem.
4. **Data quality and feature relevance.** National or lagged inputs, with no consistent group contribution.
5. **Model architecture and class imbalance handling.** Least important: changing them cannot add independent quarters.

## 4. What was not repeated

- **No tuning against outer rows.** No model variants on the 65 province-quarter rows (LEAD2 root-cause II rule). No thresholds other than 0.50.
- **New in E128:**
  - a strictly regional target with no copied labels;
  - all five Chapter I models on identical rows;
  - Leads 3 and 4;
  - an explicit evaluability rule (not evaluable = not passed).
