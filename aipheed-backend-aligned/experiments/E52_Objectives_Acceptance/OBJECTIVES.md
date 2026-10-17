# Chapter 1 objective-to-test mapping (from `THESIS 2 (11).pdf`, §1.3–1.5)

**General objective:** develop, validate and deploy aiPHeed, a geospatial food insecurity forecasting system for DA Region IV-A using NLP and machine learning.

| # | Specific objective (Chapter 1) | Measurable acceptance test | Evidence location | Status (see `FINAL_REPORT.md` for the latest) |
|---|---|---|---|---|
| 1 | Two-tier NLP pipeline (zero-shot XLM-RoBERTa sentiment + BERTopic topics) → bias-corrected FSSI and latent risk patterns per province-quarter | FSSI produced for every province-quarter; relevance filter precision and recall on a held-out sample; topic output per province-quarter | `backend/app/ml/nlp/*`, `fssi_builder.py`, E31 record (R1 holdout P 0.85, R 0.40) | built; recall limited |
| 2 | Evaluate the LightGBM model with accuracy, precision and recall, F1, AUC-ROC, and lead time via walk-forward expanding-window CV (75% reliability threshold for the maximum reliable lead time, Chapter III) | Lead-2 accuracy ≥ 0.75 with balanced accuracy ≥ 0.70 and both recalls ≥ 0.60, on chronological rows; all listed metrics reported | E36/E38/E46/E51/E52 runs | see the E52 report |
| 3 | Municipal and city risk rankings from validated province forecasts, weighted by PSA poverty incidence and population density | all 142 LGUs ranked; weights from PSA SAE 2021 and POPCEN 2024; labelled as derived prioritisation, not a municipal forecast | API `/provinces/{id}/municipalities`, E36 record `lgu_ranking`, tests | built; "validated forecasts" depends on objective 2 |
| 4 | Compare the model against naive persistence, PSA-only, NLP-only and logistic regression baselines | the candidate beats every baseline on Brier and balanced accuracy on identical rows (E52 A3, A4) | E52 `runs/` | see the E52 report |
| 5 | Public geospatial dashboard with forecast maps and early-warning alerts; ISO/IEC 25010 evaluation by DA IV-A; face validity against DOST-FNRI NNS 2019/2023 | dashboard serves maps, alerts (admin-confirmed), explanations; survey results; FNRI comparison | `frontend/`, `backend/`, live checks | dashboard built; **survey and FNRI check not done** (they need respondents and NNS figures) |

**Hypotheses H1–H5** correspond to objectives 2, 2, 4, 3 and 5. H5 needs the ISO/IEC 25010 survey.

**Target note:**
- Chapter III Eq. 3 defines the label as SWS hunger + 2 × the province's food-CPI deviation, above the median.
- E51 showed it is saturated in 2024–2026 by the SWS level shift: 40/45 rows are HIGH.
- Using PS (provincial food-price pressure) or RQ as the provincial target is a **decision for the adviser**.
