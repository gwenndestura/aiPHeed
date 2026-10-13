# Thesis-Ready Findings Summary (E17): Objectives of the Study

**Basis:**

- **Objectives:** Chapter I (`OBJECTIVES_EXTRACTION.md`).
- **Model:** the current implementation's model and target, on eligible 2021–2025 data, with timing-valid walk-forward validation.
- **Evidence status:** all quarters were examined before, so this is not an independent test.

## 1. Status of each objective

| Objective | Status | Evidence |
|---|---|---|
| **General:** develop, validate and deploy aiPHeed | **Partially achieved** | Developed and running locally. Not validated (Objectives 2 and 4). Current version not publicly deployed. |
| **1.** Two-tier NLP pipeline producing the FSSI and latent risk patterns per province-quarter | **Partially achieved** | FSSI in 96/100 and topic outputs in 96/100 province-quarters (2021–2025). Two of five trigger categories never fire. The FSSI rests on 69 articles. **No success criterion is stated.** |
| **2-I to 2-IV.** Accuracy, precision and recall, F1, AUC-ROC of the LightGBM model | **Measured; performance not satisfactory compared with the baselines** | k = 1: accuracy 0.629, precision 0.905, recall 0.633, F1 0.745, AUC 0.667. k = 2: accuracy 0.680, F1 0.800, AUC 0.522. **No thresholds are stated in Chapter I.** |
| **2-V.** Furthest horizon of reliable forecasting | **Inconclusive** | k = 1 and k = 2 are evaluable (7 and 5 test quarters); k = 3–5 have insufficient evidence; k = 6–8 are not evaluable. **"Reliable" is undefined in Chapter I.** No horizon outperforms baselines. |
| **3.** Municipal and city rankings from **validated** province forecasts | **Partially achieved** | Produced as specified. The precondition (validated province forecasts) is not met. The within-province order is static and largely density-driven (126 of 142 LGUs use province-mean poverty). |
| **4.** Comparison against the four baselines | **Achieved as a comparison; the model did not outperform** | Naive persistence and the PSA-only baseline match or exceed the LightGBM model at every evaluable lead time. It beats only the NLP-only sentiment baseline. |
| **5.** Public dashboard, ISO/IEC 25010 evaluation, NNS 2019 and 2023 face validity | **Not achieved** | Not publicly deployed; survey responses not collected; NNS 2019 and 2023 values unavailable |

## 2. Direct answers

1. **What are the exact objectives?** See `OBJECTIVES_EXTRACTION.md`: one general and five specific objectives, quoted verbatim.
2. **Status:**
   - **Partially achieved:** the General Objective, Objective 1, Objective 3.
   - **Comparison done, model not better:** Objective 4.
   - **Measured but not satisfactory:** Objective 2 (I–IV).
   - **Inconclusive:** Objective 2-V.
   - **Not achieved:** Objective 5.
3. **Measured accuracy at each valid lead time** (proposed LightGBM; S1 > 14.6):

   | Lead time | Accuracy | Balanced accuracy | F1 (HIGH) | AUC |
   |---|---|---|---|---|
   | k = 1 | **0.629** | 0.617 | 0.745 | 0.667 |
   | k = 2 | **0.680** | 0.598 | 0.800 | 0.522 |

   k = 3–5 rest on 1–3 quarters and are insufficient. k = 6–8 cannot be evaluated.
4. **How many quarters ahead can it reliably forecast?** **None can be established.** Chapter I defines no reliability criterion. The model does not beat baselines at k = 1 or 2. Longer horizons lack test quarters.
5. **Does it outperform the appropriate baseline?** **No.** Naive persistence is as good or better (k = 1: 0.686 against 0.629; k = 2: 0.720 against 0.680). The PSA-only baseline is best at k = 1 (0.714).
6. **What does it predict?** Whether **regional hunger + 2 × the province's relative food-price deviation** exceeds 14.6. That is a constructed composite label, mostly driven by the regional hunger level. **The available data cannot support claims about real provincial food insecurity.**
7. **What is still needed before the thesis can claim the objectives are fulfilled?**
   - a reliability criterion, decided with your adviser;
   - a label-validity statement or an independent provincial outcome;
   - a replacement face-validity anchor;
   - the ISO/IEC 25010 survey;
   - public deployment;
   - evaluation on new quarters (after 2025-Q4) under an approved protected-data procedure;
   - a decision on the 14.6 full-sample threshold, made before any re-evaluation.

## 3. Suggested thesis wording (results)

The proposed LightGBM model was evaluated with walk-forward expanding-window validation on 2021–2025 data, using only information available at each forecast origin:

- **One quarter ahead** (seven test quarters, 35 province-quarters): accuracy 0.63, precision 0.91, recall 0.63, F1 0.75, AUC-ROC 0.67.
- **Two quarters ahead** (five test quarters): accuracy 0.68.

Naive persistence (0.69 and 0.72) and a logistic regression on PSA indicators (0.71 one quarter ahead) performed as well as or better than the proposed model. At three or more quarters ahead, too few test quarters were available to evaluate performance.

The target is a composite of regional hunger and provincial food-price deviation. The results therefore describe forecasts of this constructed indicator, not of independently measured provincial food insecurity.
