# E128 SHAP explanations (LightGBM, model influence, not causation)

**Method.** TreeExplainer on each walk-forward fold's LightGBM, applied to its unseen origin row. Values are in log-odds. Shares are mean |SHAP| per feature, divided by the total.

**Files.** `out/shap_outer_rows.csv`, `out/shap_feature_summary.csv`, `out/shap_group_shares.csv`.

**Read with care.** These models failed every reliability criterion. SHAP shows what the models used, not what drives hunger.

## Group shares of model influence

| Target | Lead | Market and food | Climate | Employment / OFW | News / NLP | Hunger history | Poverty |
|---|---|---|---|---|---|---|---|
| T1 | 1 | 0.25 | 0.35 | 0.05 | 0.30 | 0.05 | — (no feature) |
| T1 | 2 | 0.12 | **0.77** | 0.00 | 0.08 | 0.04 | — |
| T1 | 3 | 0.31 | 0.27 | 0.03 | 0.15 | 0.25 | — |
| T1 | 4 | 0.08 | 0.01 | 0.00 | 0.11 | **0.80** | — |
| T4 | 1 | **0.55** | 0.03 | 0.05 | 0.19 | 0.18 | — |
| T4 | 2 | **0.58** | 0.14 | 0.04 | 0.04 | 0.20 | — |
| T4 | 3 | 0.31 | 0.00 | 0.04 | 0.00 | **0.66** | — |
| T4 | 4 | 0.30 | 0.00 | 0.01 | 0.00 | **0.69** | — |

## Strongest single features (T1 share)

| Feature | Lead 1 | Lead 2 | Lead 3 | Lead 4 |
|---|---|---|---|---|
| ONI (El Niño index) | 0.30 | **0.76** | 0.20 | 0.00 |
| Farmgate palay YoY | 0.19 | 0.01 | 0.19 | 0.03 |
| GDELT assistance-news share | 0.19 | 0.07 | 0.14 | 0.00 |
| Mean of last 4 hunger readings | 0.02 | 0.02 | 0.03 | **0.79** |
| Latest hunger reading | 0.03 | 0.00 | 0.19 | 0.00 |

## Stability across leads

**The strongest predictor is not stable.**
- T1 moves from ONI (Leads 1–3) to hunger history (Lead 4).
- T4 moves from market (Leads 1–2) to hunger history (Leads 3–4).

**ONI's influence is a coincidence of timing.**
- 2021–2023 had La Niña to neutral conditions and lower hunger; 2023–24 had El Niño and rising hunger.
- With about 20 quarters, the trees use ONI as a marker of the period, not a mechanism.
- The same ONI level, about −0.4, pushed the 2025-Q3 forecast toward LOW and the 2026-Q3 forecast toward HIGH, in different folds. That is the signature of a spurious split.

## Explaining individual predictions (plain language, for DA Region IV-A staff)

**Forecast issued 1 July 2026 for July–September 2026 (Lead 1, T1)**
- Probability of high hunger: **0.88**. Actual: 23.6 %, HIGH, so correct.
- The model's main reasons:
  - the El Niño index in the latest quarter (−0.40), +0.92;
  - the national share of job and income news, +0.28;
  - a small fall in food inflation (−0.44 points), +0.18;
  - rising national unemployment (+1.3 points YoY), +0.11.
- The forecast was right, but mostly for a reason (ONI) that does not hold up across folds.

**Forecast issued 1 July 2025 for July–September 2025 (Lead 1, T1)**
- Probability: **0.06**. Actual: 23.8 %, HIGH, so **missed**.
- The model pushed toward low hunger because:
  - the farmgate palay price was 29 % below a year earlier (−1.55);
  - ONI was −0.37 (−0.92);
  - assistance-news share (−0.43).
- In the training years, falling palay prices came with low hunger. In 2025 they did not: lower farmgate prices hurt farm incomes while hunger rose.
- **This is why model use is not cause.**

**Forecast issued 1 April 2026 for July–September 2026 (Lead 2, T1)**
- Probability: 0.95, correct.
- Almost all of it from ONI (+2.14).

## Conclusion

- **No feature group shows stable, causal-looking influence.**
- **SHAP confirms the overfitting and regime-proxy findings.** It is not evidence that the five trigger groups predict food insecurity.
