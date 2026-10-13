# E10: Model-Selection Recommendation (from the existing E9 evidence; nothing retrained)

**Options compared:**

- **S1 formula rule (E9 arm B3):** latest published SWS + 2 × latest published provincial gap. A rule, not a learned model.
- **Regional hunger only (B2).**
- **Carry-forward (B1).**
- **Core LightGBM (M1):** experimental.

**Common basis:** the same 35 province-quarters, 7 test quarters (2023-Q4 to 2025-Q4), the S1 target, and τ0 = 10.843.

## 1. Evidence table

| Measure | S1 rule (B3) | Regional (B2) | Carry-forward (B1) | Core LightGBM (M1) |
|---|---|---|---|---|
| Stress MAE, all 7 quarters | 4.55 | **4.47** | 5.22 | 4.54 |
| Stress MAE, final 2 quarters | 4.25 | **4.10** | 6.60 | 5.87 |
| Mean difference vs carry-forward (bootstrap 95% interval; quarters better) | −0.67 [−2.01, 0.00]; **1/7** (identical in 6) | −0.75 [−2.28, 0.20]; 3/7 | — | **−0.68 [−1.11, −0.20]; 6/7** |
| Mean difference M1 − option | −0.01 [−1.09, 1.53] | +0.07 [−1.10, 1.78] | −0.68 | — |
| Balanced accuracy (event at τ0) | 0.939 | 0.689 | 0.939 | 0.970 (stress) / 0.985 (prob.) |
| Recall LOW (2 cases, both Quezon) | 2/2 | 1/2 | 2/2 | 2/2 |
| Recall HIGH (33 cases) | 0.879 | 0.879 | 0.879 | 0.939 / 0.970 |
| Within-quarter ranking (concordant share) | **0.614** | 0.500 (none by design) | **0.614** | 0.536 |
| Provincial spread, 2024-Q2 onward (true 6.5–14.7) | 6.5–12.6 (carries the latest gap) | 0 | 6.5–14.7 | **0.0–2.1** |
| Needs training | No | No | No | Yes (16 quarters; uncalibrated probabilities) |

## 2. Answers

**Which has the strongest evidence for forecasting accuracy?**

- **No clear winner.** B2, B3 and M1 are statistically indistinguishable on stress error: mean differences under 0.1 point, wide intervals.
- **The only consistent advantage is M1 over carry-forward** (6 of 7 quarters). But M1 was worst of the three at the one turning point (2025-Q4), and it does not beat the simple rules.
- The data cannot separate these approaches on accuracy. Seven reused quarters are too few.

**Which best preserves provincial differences?**

- **The S1 formula rule** (and carry-forward, which it equals historically). It keeps the latest published provincial food-price gap, so its province ordering is the best available (concordant share 0.614), and it identified both Quezon LOW cases.
- Regional-only has no provincial information by construction.
- M1 compresses all five provinces to nearly the same value from 2024-Q2 onward.

**Which is easiest to justify and most useful to DA?**

- **The S1 formula rule:**
  - it is the thesis's own Equation 3 applied to the newest published SWS and PSA data;
  - it needs no training;
  - every number traces back to a published source;
  - it shows DA *why* a province is high (regional hunger level plus its relative food-price pressure).
- Its accuracy is in the same range as the alternatives.

## 3. Recommendation

1. **Primary forecasting approach: the S1 formula rule.**
   - Report it as a formula-based forecast, not a learned model.
   - Show the regional hunger level and the provincial price-pressure component separately, as E6 designed.
2. **Core LightGBM: an experimental comparator,** not the primary method.
   - Its only established result is beating carry-forward.
   - Incremental value over the S1 rule is **not established**, and it erases provincial differences.
   - This changes the earlier working framing ("LightGBM primary"); **you and your adviser need to confirm it**, because the thesis text may present LightGBM as the method.
3. **Disclose the limits of the S1 rule:**
   - historically it equalled carry-forward in 6 of 7 quarters, so its advantage over carry-forward rests on one quarter (2025-Q4);
   - it inherits the regional dominance, so in high-hunger periods almost every province is HIGH.

## 4. Why accuracy is misleading here

**The imbalance:** 33 of the 35 outcomes are HIGH.

- A rule that always says HIGH scores **94.3%** accuracy while having **zero** ability to recognize a LOW quarter.
- Every option, including the weakest, exceeds 75% accuracy, so the 75% figure cannot distinguish a useful forecaster from a useless one.

**Metrics to prioritize:**

- **Balanced accuracy** and **class-specific recall.** Even these rest on two LOW cases in one province.
- **Stress error** (MAE, regional-level error).
- **Within-quarter ranking.**
- **Comparison against the simple baselines.**

**Under these measures, no option has demonstrated skill clearly beyond the simple rules.** Nothing was optimized toward the 75% figure.
