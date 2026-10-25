# E112 Chapter I objectives: requirements, past failures and evidence

**Requirement basis.** Chapter I §1.5.2 of `THESIS 2 (11).pdf` (13 Oct 2026), the wording quoted in `../Lead1_Objectives_Assessment/LEAD1_OBJECTIVES_1_4_ASSESSMENT.md`. Chapter I sets no accuracy threshold. The objectives were not replaced by easier targets.

## 1. Objectives map

| Objective (Chapter I) | What it requires | Why E107–E111 fell short | Evidence needed | E112 evidence | **Status** |
|---|---|---|---|---|---|
| **1.** Two-tier NLP pipeline (zero-shot XLM-R + BERTopic): bias-corrected FSSI and latent food-insecurity patterns per province-quarter | A working pipeline producing measurable news signals | FSSI-v3 is sparse (56% missing) because the relevance filter admitted 2–7 headlines per quarter in 2021–22; no forecast gain | Dense, dated, validated news measures and a test of their forecast value | Pipeline intact (FSSI-v3, BERTopic). New dense event indicators: 0% missing; disaster category validated (ρ = 0.81 with typhoon counts). One unreplicated advance association (agri_supply, Holm p = .074). **No forecast gain** (N1, N2 and N3 all Holm p = 1). | **Partially achieved.** Produced and measurable; predictive value not demonstrated. |
| **2 I–IV.** LightGBM accuracy, precision/recall, F1, AUC-ROC | Metrics of the proposed LightGBM on a food-insecurity outcome | Binary readings of the only outcome are one-class: every evaluated BL quarter is above 11.3%, so accuracy is trivially 1.0 and AUC undefined (E109) | A two-class outcome with enough quarters | Continuous metrics reported (MAE, RMSE, bias, 80% coverage; `results.json`). Classification metrics are reported in E109 and are degenerate. | **Partially achieved.** Computed; the classification metrics are uninformative on this outcome. |
| **2 V.** Walk-forward expanding window to find the furthest reliable horizon | A horizon passing a reliability rule | No lead passed (E111). Lead 1 = true horizon 2. | Pre-registered rule, true horizons, prospective confirmation | Walk-forward done; true horizons reported; rule frozen. **No reliable or provisional lead.** | **Not demonstrated** |
| **3.** Municipal/city risk rankings from **validated** province-level forecasts, weighted by poverty and density | Validated provincial forecasts and an LGU outcome to check against | No provincial food-insecurity outcome exists. Forecasts are regional, so rankings reflect the weights only. | CBMS 2024 LGU food-security aggregates; provincial FIES | Rankings exist (FIRI v2, unchanged). They are labelled vulnerability rankings; no validated forecast feeds them. | **Not achieved** as specified (data gap documented) |
| **4.** Compare the proposed LightGBM with naive persistence, PSA-only, NLP-only and logistic regression baselines | The comparison, on the same rows | E109–E111 lacked an explicit PSA-only arm and had no well-defined LR on a one-class outcome | All four arms, same rows, tested | All four (Addendum 1: PSA-R; linear regression RIDGE13, since logistic regression is undefined on a one-class outcome). LightGBM loses to persistence at every lead. It beats PSA-only at Leads 2–4 and linear regression at Leads 1, 2 and 4, in point estimates only (Holm p ≥ .82). | **Achieved** (the comparison). The proposed model is not superior. |
| **5.** Dashboard, ISO/IEC 25010, DA evaluation | — | — | — | Out of E112 scope. Dashboard design unchanged; only read-only API routes added. | Not assessed here |

## 2. What would move each objective forward

| Objective | Next evidence |
|---|---|
| 1 | Prospective test of the news indicators (sealed with this run) |
| 2 V | Score the E109–E112 seals as SWS publishes 2026-Q4 onward |
| 3 | CBMS 2024 LGU food-security aggregates (E87 request A) |
| 2 I–IV | A two-class outcome with both classes present, e.g. a provincial FIES series |
