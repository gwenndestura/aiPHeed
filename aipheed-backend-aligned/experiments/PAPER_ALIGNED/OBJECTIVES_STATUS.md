# Objectives status: the paper's Chapter III pipeline (plain words)

**Basis.** This status follows decision 9: the paper's own pipeline, as run by E99 and **reproduced exactly** here on
2026-11-03 (`E99_REPRODUCTION.md`). Paper: `THESIS 2 (18).pdf`, Chapter I §1.3–1.5 and Chapter III. Evidence is
**development evidence**: every quarter scored had been looked at before.

**Categories.**
- **Achieved:** the objective's work was done as written. The result may still be negative, and is then stated.
- **Not achieved:** the objective's condition was not met.
- **Waiting for evaluators:** it needs DA Region IV-A respondents.

## Specific objectives (§1.5.2, pp. 12–13)

| Objective | Status | What a panel can read | Evidence |
|---|---|---|---|
| **1** Two-tier NLP pipeline (XLM-RoBERTa + BERTopic) producing the bias-corrected FSSI and latent patterns per province-quarter | **Achieved, with a coverage limit** | The pipeline runs end to end and produces both outputs. Only 17% of province-quarters have enough province-tagged news (≥ 5 articles) for a full FSSI, and the news features added no forecasting value (4 of 5 triggers had zero SHAP influence). | `../OBJECTIVES_COMPLETION/OBJ1_NLP_PIPELINE.md`; `E99_REPRODUCTION.md` (SHAP) |
| **2 I–IV** Accuracy, precision/recall, F1, AUC of province-level high/low classification | **Achieved (measured); the result is poor** | On the four blind 2025-Q4..2026-Q3 quarters, the tuned LightGBM scored accuracy 0.45, weighted F1 0.53 and AUC 0.61. Copying the previous quarter scored 0.90. | `E99_REPRODUCTION.md`; `E99_reference/runs/20261102T222949Z_reproduction/e99_results.json` |
| **2 V** Walk-forward expanding-window CV to find the furthest reliable horizon | **Achieved (determined); the answer is "none"** | Algorithm 3 stopped at the first horizon: one quarter ahead, mean fold accuracy was 0.30, below the paper's 0.75. The Maximum Reliable Lead Time is 0. | `E99_REPRODUCTION.md` |
| **3** Municipal and city rankings from **validated** province forecasts (PSA poverty 60%, density 40%) | **Not achieved** | The 142 rankings can be computed, but no province forecast passed validation. Under Rule 4 and §3.4.4, the rankings must be marked "not validated" and not published as forecasts. | `E99_reference/REPORT.md` §11; `../OBJECTIVES_COMPLETION/OBJ3_LGU_RANKINGS.md` |
| **4** Compare the proposed LightGBM with persistence, PSA-only, NLP-only and logistic regression | **Achieved (compared); the proposed model does not outperform them** | All comparators were run on the same folds. Persistence was significantly better than the proposed model (McNemar p = 0.0003). The proposed model was significantly better only than the NLP-only logistic regression (p = 0.039). | `E99_REPRODUCTION.md` |
| **5** Public dashboard with forecast maps and early-warning alerts; ISO/IEC 25010 evaluation by DA Region IV-A; FNRI face validity | **Waiting for evaluators** | The dashboard is deployed with maps and alerts, but it serves a different model (P0H4), because the paper's model was not accepted. The ISO/IEC 25010 survey (50 DA evaluators) has 0 responses. FNRI face validity is below. | `E99_reference/evaluation_package/`; FNRI row below |

## Research questions (§1.3, pp. 10–11)

| RQ | Answer (plain words) | Status |
|---|---|---|
| **RQ1** Which variables most predict risk (SHAP)? | In the final model, the top three were unemployment (previous quarter), rice price change (previous quarter) and food CPI deviation. The best news feature (FSSI lag 1) ranked 4th. These explain a model that failed its tests, so treat them as descriptive. | Answered |
| **RQ2** Furthest reliable lead time? | None. One quarter ahead already fails the paper's 75% rule (0.30). | Answered: no reliable lead |
| **RQ3** Combined LightGBM vs the six baselines? | It loses to persistence (significantly) and to the government-only LightGBM on the holdout (0.45 vs 0.65). It beats only the NLP-only logistic regression significantly. | Answered |
| **RQ4** Do LGU rankings reflect relative vulnerability? | Cannot be judged yet. It needs DA evaluators' rankings, and the province forecasts are not validated. | Waiting for evaluators |
| **RQ5** How do DA (system) and DEPDev (usability) evaluators rate aiPHeed under ISO/IEC 25010? | DA: no responses yet. DEPDev: out of scope for now (decision 5); its questionnaire will be prepared as optional. | Waiting for evaluators |

## Null hypotheses (§1.4, pp. 11–12)

| H | Decision | Plain words |
|---|---|---|
| **H1** FSSI and food CPI deviation not among the strongest predictors | **Not rejected** (borderline) | Food CPI deviation ranked 3rd, but FSSI ranked 4th, so both are not in the top three |
| **H2** Not reliable across lead times | **Not rejected** | No lead passed (k\* = 0) |
| **H3** Combined LightGBM will not outperform the six comparators | **Not rejected** | It did not beat persistence or the government-only models |
| **H4** LGU rankings not consistent with DA evaluators | **Waiting for evaluators** | Ranking task ready; no responses |
| **H5** No favourable ISO/IEC 25010 ratings from DA evaluators | **Waiting for evaluators** | Questionnaire ready; 0 of 50 responses |

## FNRI face validity (decision 8; never a label)

| Source | 2023 figure |
|---|---|
| DOST-FNRI 2023 National Nutrition Survey, Food Security (regional map) | **CALABARZON 19.1%** of households moderately or severely food insecure (95% CI 17.0–21.1); Philippines 31.4% |
| Eq. 3 label, 2023 (E99 data) | HIGH in **2 of 20** province-quarters; mean SWS Balance Luzon hunger 11.2% |

**Reading.**
- FNRI places CALABARZON well below the national figure in 2023.
- The paper's label is mostly LOW in 2023 and switches to mostly HIGH from 2024.
- The two do not contradict each other, but they measure different things: household food-insecurity experience vs SWS hunger plus price deviation, relative to a median.
- A single FNRI year cannot validate a quarterly forecast. This is a face-validity note only.

## What this means

**The paper's pipeline, run as written, does not meet its own acceptance rules:**
- no reliable lead (Algorithm 3);
- tuned model not accepted (Algorithm 4: F1 0.53 < 0.75, AUC 0.61 < 0.80).

Failing to reject H1–H3 is a valid thesis result. Under §3.4.4, nothing from this model may be published as a forecast.
Objective 3 therefore cannot be completed with validated forecasts. Objective 5's evaluations (H4, H5) still need
respondents.

**The cause is the data, not the tuning:**
- about 19 labelled quarters;
- one regime switch, from LOW in 2021–23 to HIGH in 2024–26;
- the models learn the LOW years and keep predicting LOW.

A possible amendment is described in `ADVISER_NOTE.md`.
