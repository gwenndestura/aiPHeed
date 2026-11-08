# E110 Thesis objective assessment (Chapter I §1.5.2)

| Objective (abridged) | Status after E110 | Evidence |
|---|---|---|
| 1. NLP pipeline (FSSI-v3, BERTopic) | **Partially achieved** | It runs and is one of the 12 families. FSSI-v3 is sparse, gets a small SHAP share (0.02 at Lead 1) and does not measurably improve hunger forecasts. |
| 2 I–IV. LightGBM accuracy, precision/recall, F1, AUC | **Partially achieved** | Computed for research-defined binary readings and for continuous error. They are regional (no provincial outcome), and on 5–10 quarters. No binary reading meets the rule. |
| 2 V. Furthest reliable horizon (walk-forward, expanding window) | **Not demonstrated** | Lead 1: not reliable (no method beats the latest reading). Lead 2: not reliable (gains do not generalize). Leads 3–6: insufficient evidence. **No reliable lead time established.** |
| 3. Municipal rankings from validated province forecasts | **Not achieved** | No validated provincial or municipal hunger forecast exists. LGUs are marked "insufficient local evidence". |
| 4. Comparison with baselines (persistence, PSA-only, NLP-only, logistic) | **Achieved as a comparison** | Persistence (the latest reading) is the best method. Indicator-based models are not better: NAT-R is clearly worse, and LGBM-R / RIDGE-R have insufficient evidence. |
| 5. Dashboard, ISO 25010, FNRI face validity | **Not in E110 scope** | The dashboard is unchanged. Read-only `/api/v1/e110/*` exists. |
| Brief: 12 families in LightGBM | **Achieved** | LGBM-R uses all 13 columns (test `test_lgbm_r_uses_all_12_families`). |
| Brief: hunger, not food prices | **Achieved** | The target is SWS Total Hunger; price pressure is used only as a predictor. |
| Brief: generalization across quarters | **Not achieved** | Two regimes (the 2024 surge and the 2025–26 oscillation); no method works in both. |

## Final answers

1. **Hunger or food prices?** The final forecast is SWS experienced hunger (Balance Luzon), a direct hunger measure. It is regional, not provincial.
2. **Does it beat persistence out of sample?** No, not at Lead 1. At Lead 2, smoothing beats it on average (COMB p = 0.098), but not in rising periods or the early third, and not within the Balance Luzon accuracy bound.
3. **Does performance generalize across quarters?** No.
4. **Which indicator families demonstrably improve forecasting?** None.
   - National C1, E1 and E2 made pooled forecasts worse.
   - For the CALABARZON families there are too few quarters to tell (5 evaluable).
   - The price projection (A1) carries most of LightGBM's attention, but the model is not better than the latest reading.
5. **Maximum reliable lead time:** none established. The maximum lead tested is 6 quarters, and there is no provisional lead.
6. **Objectives:** see the table above.
7. **Limitations from the 2021+ data:**
   - 20 outcome quarters, of which 8–10 are evaluable at Leads 1–2 and 1–6 at Leads 3–6;
   - a survey-design change in 2025;
   - SWS sampling noise of ±4–6 points;
   - the publication lag makes "Lead 1" two quarters ahead;
   - no provincial outcome.
8. **Simplest credible methodology:** report the latest published SWS Balance Luzon reading with its margin and an empirical ±6-point interval, as an unvalidated one-quarter outlook. Present the 12 indicators as context. Score the sealed forecasts as SWS publishes them.

## Suggested Chapter IV wording

> Using SWS Total Hunger for Balance Luzon (2021–2026) as the outcome, and the other three SWS areas as a generalization panel, no model forecast hunger more accurately than the latest published SWS reading one quarter ahead. This held for noise-aware smoothing, for forecast combinations, for regressions on national indicators, and for LightGBM using all twelve aiPHeed indicators.
>
> Two quarters ahead, smoothing recent readings reduced average error in all four areas, but this advantage disappeared during the 2024 surge in hunger. With twenty outcome quarters, of which six or fewer were available for evaluation beyond two quarters, a reliable forecasting horizon could not be established.
