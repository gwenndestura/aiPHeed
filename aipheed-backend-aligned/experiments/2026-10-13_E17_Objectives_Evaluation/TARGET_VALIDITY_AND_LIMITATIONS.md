# Target Validity and Methodological Limitations (E17)

## 1. What the model actually learns to predict

**The current implementation's target** (`config/governing_model.json`) is the composite label from Eq. 3:

> HIGH if S1 = H + 2 × D > 14.6

| Term | Meaning |
|---|---|
| **H** | SWS **Balance-Luzon** involuntary hunger: one value per quarter, shared by all five provinces |
| **D** | The province's food inflation minus the unweighted five-province mean |
| **14.6** | The median of the 2020–2025 composite scores |

So the model predicts **whether regional hunger plus twice the province's relative food-price pressure exceeds a fixed level**. Chapter I calls this a "composite food stress label" (1.2), and it is a **constructed** indicator:

- It is **not an independently measured provincial food-insecurity outcome.**
- Its HIGH/LOW status in 2024–2025 is driven mainly by the regional hunger level (E12/E13). In the test quarters, 86–92% of rows are HIGH.
- Agreement with this label is **internal consistency with the label's own inputs.** It is not evidence about real provincial food insecurity.

## 2. What the evaluation can and cannot support

| Claim | Supported? |
|---|---|
| The model forecasts the **constructed label** better than simple baselines | **No** (Objectives 2 and 4 results) |
| The model forecasts **regional hunger** or **provincial food prices** | Not tested by the classifier. Separate continuous tests show no gain over carry-forward, except D shrinkage (`SUPPORTING_HORIZONS.md`). |
| The model forecasts **actual provincial food insecurity** | **Cannot be evaluated.** No independent provincial outcome exists (E13 audit). |
| Municipal rankings reflect real municipal food insecurity | **No evidence.** The rankings are province scores × static weights. Poverty and density are not independent evidence that the forecasts are correct. |

## 3. Limitations

1. **Few independent quarters:**
   - 16 labelled quarters in total;
   - 7 and 5 test quarters at k = 1 and 2;
   - 5 and 2 LOW cases.
2. **A structural shift:** training is 2021–2023 (mostly LOW at 14.6); testing is 2024–2025 (mostly HIGH).
3. **A full-sample threshold:** 14.6 is the median of all 2020–2025 scores, so the label definition uses the whole period. This is kept because it is the implementation's definition.
4. **Zero-filled features:** `features_fused` zero-fills gaps, and imputed zeros cannot be told apart from true zeros. Two trigger features are always zero.
5. **Unverified timing:**
   - provincial CPI dates are proxies;
   - `poverty_incidence` does not follow its release dates, so it was excluded;
   - news features were curated in 2026 (development reconstruction).
6. **Departures from the recorded configuration (D1–D5):** a timing-valid training rule, no poverty, no zero-fill, a 2021+ window, verified SWS dates. The recorded 0.818 was not reproduced. Under the recorded rule on 2021+ data (R0), accuracy is 0.700.
7. **No new quarters:** every quarter was examined in earlier experiments.

## 4. Decisions for your adviser (Chapter I leaves these open)

1. **A reliability criterion** for Objective 2-V: the metric, the threshold, the minimum number of quarters and the minimum per class.
2. **Whether the composite label may be presented as "food insecurity risk",** or as a constructed stress indicator. A label-validity statement is needed in the thesis either way.
3. **A face-validity anchor,** because NNS 2019 and 2023 regional figures are not available in the project (Objective 5).
4. **Whether to keep the 14.6 full-sample threshold,** or move to a threshold set from training data only. That would be a methodology change and must be decided **before** any further evaluation, not after seeing results.
5. **How to obtain an independent provincial outcome.** Options: FNRI provincial FIES/HFIAS microdata, CBMS food-shortage items, or a DA- or LGU-run FIES module.
