# Methodology Review: Why aiPHeed Does Not Reach 75% Accuracy

Prepared 2026-10-08 for the researchers and their adviser. Chapter III is not
edited here; every proposed correction below needs the adviser's approval
before it changes the served system. All figures are reproducible:

```bash
python -m scripts.supplementary.experiment_reliability          # designs E0-E4 and references
python -m scripts.supplementary.experiment_reliability more     # designs E5-E9
```

Test setting for every figure: one quarter ahead (features at t, label at t+1,
Rule 3), walk-forward expanding window, minimum 8 training quarters, the same
55 test rows (11 quarters x 5 provinces), 60% of them HIGH.

---

## 1. What limits accuracy

### 1.1 The label is mostly a regional number the model never sees

Equation 3 is stress = SWS hunger + 2 x provincial CPI deviation. SWS publishes
Balance-of-Luzon figures only, so the first term is one number per quarter.
**66% of the variance of the stress score lies between quarters**, and 7 of the
19 labelled quarters are entirely HIGH or entirely LOW. Predicting the label is
mostly predicting next quarter's regional hunger level.

Equation 5 contains no predictor of that level. SWS was excluded from the
features to prevent label leakage, which is correct for a same-quarter estimate
but not for a forecast: last quarter's published SWS figure is past data and
Rule 3 allows it.

### 1.2 The HIGH/LOW line drifts against the training data

The global-median threshold (stress 14.6) is set over the whole 2020-2025
window. Regional hunger was low in 2021-2023 and high in 2024-2025, so the
early training quarters are mostly LOW and the later test quarters mostly
HIGH. With `class_weight="balanced"` the model learns a boundary for the old
prior and under-predicts HIGH in the new one. AUC (ranking) holds up; accuracy
at the 0.50 cut-off does not. The threshold also uses information from the
future of every test quarter, which a forecasting label should not.

### 1.3 There is very little to learn from

95 labelled province-quarters over 19 quarters (five quarters had no SWS
round), against twelve features. Each walk-forward fold tests five rows, so one
misclassified province moves fold accuracy by 20 points.

### 1.4 The 75% criterion does not require skill

Section 3.4.4 accepts a lead time when mean fold accuracy reaches 75%. On this
label a rule with no skill can do that: repeating last quarter's label scores
**0.80** here, and predicting HIGH everywhere scored 0.77 in an earlier fold
layout. A model that clears 75% may still be worse than doing nothing.

### 1.5 Other gaps found in the approved methodology

| Gap | Effect |
|---|---|
| Section 3.3.2.7 (feature selection) is cited but missing from the manuscript | The procedure and Equation 5 disagree on which twelve features to use |
| Equation 5's CPI_dev legend leaves the rolling window unstated | Implemented as four prior quarters (2026-10-08) |
| Algorithm 4 tunes at gap = Maximum Reliable Lead Time; at 0 that is a same-quarter estimate | Conflicts with Rule 3 and Section 3.4.4's no-publication rule |
| Equation 4's CPI robustness label compares the CPI level, which rises steadily, against a 24-quarter mean | Later quarters are positive almost automatically, so high accuracy on it would be trivial |
| Unemployment is published nationally only | The strongest SHAP feature cannot separate provinces |
| The FSSI has news in only part of the 120 province-quarters | The rest are filled under Section 3.3.2.6 |

---

## 2. What was tested

| Design | Accuracy | AUC-ROC | Change it needs |
|---|---:|---:|---|
| **References** | | | |
| Always HIGH | 0.600 | - | none |
| Repeat last quarter's label (persistence) | **0.800** | - | none |
| Stress at t above the threshold | 0.800 | 0.868 | none |
| **Approved** | | | |
| E0 Equation 5, default LightGBM | 0.618 | 0.789 | none |
| **Corrections** | | | |
| E1 + last published SWS hunger and its change | 0.709 | 0.849 | add a feature (Equation 5) |
| E2 E1 + last observed label | 0.691 | 0.838 | add autoregressive term |
| E5 Equation 5 + last stress score + SWS terms | **0.745** | 0.828 | add autoregressive term |
| E8 logistic on last stress, SWS change, CPI_dev, FSSI | 0.727 | 0.831 | change algorithm |
| R2 LightGBM regression of next-quarter stress, classified at 14.6 | **0.745** | **0.884** | change model output |

No design reached 75%, and none matched persistence. The best learned designs
(E5, R2) sit at 0.745, about one province-quarter short of 75%, and still five
points below repeating last quarter's label. They do rank better than
persistence (AUC 0.88), which is evidence the features carry signal, but not
enough to call a quarter HIGH or LOW more reliably than the previous quarter
already does.

---

## 3. Proposed corrections (adviser approval required)

1. **Add last quarter's published SWS hunger and its change to Equation 5**
   for forecast horizons of one quarter or more. It is the only predictor of
   the label's dominant term, uses only past data, and raised accuracy from
   0.618 to 0.709 and AUC from 0.789 to 0.849.
2. **Make the reliability criterion require skill.** Accept a lead time only
   when mean fold accuracy is at least 75% **and** higher than persistence on
   the same folds. Without this, 75% can be met by a rule with no skill.
3. **Fix the HIGH/LOW line without using the future.** Set the threshold from
   the quarters available at training time (for example an expanding median),
   or justify the global median explicitly as a fixed reference value.
4. **Lengthen the history.** Within 2020-2025 the row count is fixed, so more
   history is the only route that adds labelled rows. The SWS series on file
   runs from 2020-Q2 to 2026-Q2 (the 2026 quarters are outside the approved
   window). Whether earlier SWS releases, provincial PSA food CPI and news can
   be collected for the years before 2020 has not been verified. This is the
   correction most likely to lift accuracy, and it needs data collection before
   it can be tested.
5. **Replace or remove Equation 4**, or document that it is a trend indicator.
6. **Restore Section 3.3.2.7** to the manuscript, or name Equation 5's list as
   final.

## 4. What should not be done

Choosing the decision cut-off on the holdout, adding the current quarter's SWS
or label as a feature, or re-running the tuner until a favourable split appears
would each produce a number above 75% that does not mean the system forecasts
reliably.
