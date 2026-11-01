# Phase 2, Addendum C: a parsimonious continuous world-price model (Y11)

**Status.** Frozen (SHA-256 in `common/PLAN2C_SHA256.txt`) before Y11 is run.

**Motivation (Y10).** The two logistic classifiers on world prices failed the gate (Brier +0.055 vs PERS-PROB). But the descriptive full-period correlations between 6-month world price changes and the coming change in Region IV-A food inflation are positive and sizeable:

| Series | Correlation |
|---|---|
| Palm oil | 0.46 |
| Wheat | 0.42 |
| Crude oil | 0.39 |
| Rice, urea, maize | 0.22–0.23 |

Two diagnoses:

1. A classifier with 8–14 features and 20–70 training rows overfits.
2. The signal is about the **change** in inflation. A continuous model of target-quarter food inflation uses it directly. The 0/1 condition discards it.

**Disclosed multiplicity.** Y11 is the 5th model family scored on the 2002–2020 price-development rows (after AR, LOGX, LOGW and LOGW2). A gate pass is weaker evidence for that reason, and the confirmation on 2021+ provincial rows is what counts.

## Y11 design

Target, rows, training-window rule, development period, comparators and gate are **identical to Addendum A**.

**Candidate WAR.** At each origin, using training rows only:

1. Rank the 12 world features (6- and 12-month log changes of rice, crude, urea, maize, wheat, palm) by |correlation| with (F_tgt − F3). Keep the top 3.
2. Fit OLS F_tgt ~ F3 + F_base + top-3.
3. Fit OLS G_tgt ~ G3 + G_base, with no world features.
4. Use Gaussian predictive distributions with residual σ. Then P_F = Φ((μ_F − 6.25)/σ_F), P_G = Φ((μ_G − 0.48)/σ_G), and P = 1 − (1 − P_F)(1 − P_G).

**Ablation WAR0.** The same model with no world features. It is the continuous persistence analogue and is reported for attribution, not as a candidate.

The confirmation rule is as in Addendum B.
