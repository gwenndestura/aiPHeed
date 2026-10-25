# E109 Thesis objective assessment (Chapter I §1.5.2)

**Status labels:** Achieved · Partially achieved · Not achieved · Insufficient evidence. All E109 results are development evidence (no unseen quarter yet).

| Objective (abridged) | Status | Evidence and reason |
|---|---|---|
| **1.** Two-tier NLP pipeline (XLM-RoBERTa sentiment, BERTopic) producing FSSI and risk patterns per province-quarter | **Partially achieved** | The pipeline exists, and FSSI-v3 is one of the 12 families. It has values for only 17% of province-quarters. It received no split in the Lead-1 hunger model and only a minor share at Lead 2. News counts are not measurements of hunger. |
| **2 I–IV.** Accuracy, precision/recall, F1, AUC of the LightGBM model on high/low province-level classification | **Partially achieved** | The metrics are computed (`E109_METHOD_AND_MODEL_COMPARISON.md` §3). They are **regional, not provincial**, because no provincial hunger outcome exists. At the only informative threshold (> 20%, research-defined), Lead-1 accuracy is 0.78 over 9 quarters. At 11.3% and 15% all quarters are HIGH, so these metrics cannot measure skill. |
| **2 V.** Furthest horizon at which reliable forecasting is achievable, by walk-forward expanding-window evaluation | **Not achieved / insufficient evidence** | Lead 1: not reliable (no model beats the latest SWS reading). Leads 2–4: insufficient evidence (5–7 quarters). **No reliable lead time is established.** |
| **3.** Municipal and city risk rankings from **validated** province-level forecasts | **Not achieved** | There is no validated province-level hunger forecast. All 142 LGUs are reported as "insufficient local evidence", with PSA SAE poverty as context only. |
| **4.** Comparison with baselines (persistence, PSA-only, NLP-only, logistic) | **Achieved (as a comparison); LightGBM is not better** | On hunger, persistence (RW) is the best method at Lead 1. LightGBM (4.04), ridge (4.49) and the local-level filter (4.53) are all worse than RW (3.72). The PSA-only and NLP-only variants are in the E108 composite study, not in the hunger study. |
| **5.** Dashboard, ISO/IEC 25010 evaluation with DA IV-A, and validation against FNRI NNS 2019/2023 | **Not achieved in E109 (out of scope)** | The dashboard is unchanged, and E109 is exposed through read-only `/api/v1/e109/*`. FNRI NNS 2019 is before the study window; only a single press-reported 2025 CALABARZON FIES value (22.6%) is in the project. |

## Direct answers

1. **Does the final model forecast an actual food-insecurity or hunger outcome?** Yes, **experienced hunger** (SWS Balance Luzon Total Hunger), which is directly observed. It is regional, not provincial, and it is one dimension of food insecurity, not the FIES scale.
2. **Exact definition of LOW and HIGH.** SWS publishes none, so every binary rule is **research-defined**: B1 > 11.3% (E40: P60 of 2021–22), B2 > 15%, B3 > 20%, B4 a rise of more than 4 points (the SWS-published Balance Luzon margin). SWS Moderate and Severe are frequency categories, not prevalence thresholds.
3. **Best model in a fair chronological comparison.** The latest published SWS reading (RW) at Lead 1. MA2 is best at Leads 2–4, but on too few quarters to judge.
4. **Does the model outperform simple baselines?** No. LightGBM's Lead-1 MAE of 4.04 is above RW's 3.72 (DM p = 0.72).
5. **Maximum reliable lead time.** None established, under criteria C1–C6 (`E109_LEAD_TIME_RELIABILITY_REPORT.md`).
6. **Confirmed on unseen outcomes?** No. The sealed forecasts await SWS 2026-Q4 (expected around January 2027).
7. **Objectives:** see the table above.
8. **Simplest credible methodology.** Report the latest SWS Balance Luzon hunger reading as the one-quarter outlook, with its survey margin and an empirical ±6-point (80%) interval. Show the 12 indicators as context, labelled as drivers, not as a forecast of hunger. Mark every horizon "not validated" until the sealed forecasts are scored.
9. **Limitations to disclose to DA IV-A, DEPDev IV-A and the panel:**
   - no provincial or municipal hunger outcome exists;
   - Balance Luzon covers more than CALABARZON;
   - the 2025 respondent-base change and the commissioned 2025 round;
   - only 20 outcome quarters;
   - survey noise of ±4–6 points per reading;
   - no model beats the latest reading;
   - food-price pressure is not hunger;
   - all results are retrospective;
   - LGU rankings are not validated forecasts.

## Suggested Chapter IV wording

> The forecasting target was the SWS Balance Luzon Total Hunger rate, the proportion of families that experienced involuntary hunger at least once in the past three months. It is the only repeatedly and directly observed food-insecurity measure available for the study area, and it is published for Balance Luzon as a whole rather than by province.
>
> Under walk-forward evaluation from 2024 to 2026, a LightGBM model using all twelve aiPHeed indicators forecast the next quarter's hunger rate with a mean absolute error of 4.0 percentage points. Simply carrying the latest published reading forward did better (3.7 points), and the difference was not statistically significant.
>
> Two to four quarters ahead, fewer than eight quarters could be evaluated. A reliable forecasting horizon therefore could not be established with the 2021–2026 data. SWS does not define low or high hunger levels, so the classification results use research-defined thresholds and are reported as sensitivity analyses.
