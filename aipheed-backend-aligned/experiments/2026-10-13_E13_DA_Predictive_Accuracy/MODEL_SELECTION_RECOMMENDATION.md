# Model Selection Recommendation (E13)

## 1. Decision by target

| Target | What it measures | Rule outcome (protocol §4) | Recommendation |
|---|---|---|---|
| Provincial **food insecurity** | — | **Not evaluable** (no outcome) | **No defensible improvement can be established.** No model is selected for this purpose. |
| **A**: regional hunger | SWS Balance Luzon | No model met the rule. Both ridge models were **worse** than carry-forward: MAE 6.57 and 6.58 against 4.77; the interval for the difference is entirely above 0. | **Keep carry-forward** of the latest published round, shown as regional context with its age and date. **No model selected.** |
| **B1**: provincial food inflation | Food-price pressure | No model met the rule. The best model (ridge, MAE 2.52) was slightly worse than carry-forward (2.44). | **Keep carry-forward** of F(T−2), labelled as price pressure. **No model selected.** |
| **B2**: relative provincial price pressure | Relative price pressure | `B2_ridge_DP` **met all four conditions**: MAE 1.180 against 1.355; difference −0.175 [−0.287, −0.049]; Holm p = 0.038; LOQO 11/11. | **Not selected for use.** Recorded as a **candidate for prospective testing** (see §2). |
| **S1**: constructed indicator | Internal consistency | Covered by E9–E12 | No change. S1 remains the documented thesis indicator, with its limits (`CURRENT_MODEL_DIAGNOSIS.md`). |

## 2. Why B2_ridge_DP is not selected, despite meeting the rule

The frozen rule was met. These caveats are disclosed, not used to override that result:

1. **The quarters are not new.** All 11 B2 test quarters were seen in E12. 7 of them were E9–E12 test quarters.
2. **The hypothesis came from the same data.** E12 observed that shrinking the latest provincial deviation improved next-quarter S1 forecasts on overlapping quarters. E13 tested a version of that idea on a partly overlapping period. That is **consistency, not independent confirmation.**
3. **The result is not robust to the period.** On the 7 E9–E12 quarters (S-B1), the best baseline is "no difference" (MAE 1.42). B2_ridge_DP scores 1.23, a difference of −0.19 with an interval of [−0.68, 0.28]. Under the same rule it would not pass.
4. **The model's logic is period-specific.** It weights each province's own long-run deviation **negatively** (−0.34 to −0.59). That reflects the 2023–2024 reversals (Quezon, Rizal, Batangas), not a known mechanism.
5. **The practical gain for DA is small.** It changes 3 of 55 sign calls (2 better, 1 worse), and Kendall τ rises from 0.40 to 0.45.
6. **It forecasts price pressure, not food insecurity.**

**What would justify adopting it:** pre-registering it now (it is fixed by this protocol) and scoring it on **new quarters** against carry-forward and zero. That means 2026-Q3 onward, once those quarters are published and the protected-period rules allow scoring.

## 3. What the evidence does support

1. **Two layers, not one combined provincial HIGH/LOW** (this agrees with E12):
   - a regional hunger layer, using carry-forward of the latest published round, its date and trend;
   - a provincial price-pressure layer: F and D, with D's ranking when all five provinces are available.
2. **Plain baselines are as good as or better than the trained models** for every target except B2. On B2 the gain is small and not yet confirmed.
3. **LightGBM and the earlier 45-feature model are not recommended.** No target had the sample size, and E9 and E11 found no reliable gain.
4. **No threshold change is recommended.** Re-anchoring τ would need an outcome to validate it. A threshold chosen to reduce HIGH labels would be fitted to the label distribution.

## 4. Statement for the record

> No defensible improvement in **provincial food-insecurity** prediction has been established, because no independent provincial food-insecurity outcome exists for 2021–2025. For **regional hunger** and **provincial food inflation**, no model improved on carry-forward. For **relative provincial food-price pressure**, one compact shrinkage model met the pre-specified rule on reused quarters. It is recorded as a candidate for prospective testing and is not selected for use.

**Production, the served model, the dashboard and the thesis methodology were not changed.**
