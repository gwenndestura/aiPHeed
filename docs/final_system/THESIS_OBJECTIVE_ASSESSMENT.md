# Thesis objective assessment (final system)

**Basis:** Chapter I §1.5.2, quoted from `aipheed-backend-aligned/experiments/Lead1_Objectives_Assessment/chapter1_1_5_2_extract.txt`.

Chapter I sets no accuracy threshold. The 75% target comes from the user's directive and the earlier Chapter III Algorithm 3. It is assessed with the frozen rule in `FINAL_MODEL_EVALUATION.md` §4.

## Summary

| # | Objective (Chapter I, shortened) | Status |
|---|---|---|
| 1 | Two-tier NLP pipeline (XLM-R + BERTopic) producing FSSI and latent food-insecurity patterns per province-quarter | **Partially achieved** |
| 2 I–IV | LightGBM accuracy, precision/recall, F1, AUC on high/low-risk classifications | **Partially achieved** |
| 2 V | Walk-forward cross-validation to find the furthest reliable horizon | **Partially achieved (method); not achieved (result)** |
| 3 | Municipal and city risk rankings from **validated** province-level forecasts, weighted by poverty and density | **Partially achieved** |
| 4 | Compare LightGBM with persistence, PSA-only, NLP-only and logistic regression | **Achieved** |
| 5 | Public geospatial dashboard; ISO/IEC 25010 evaluation with DA IV-A; FNRI NNS face validity | **Partially achieved** |

## Details

### Objective 1: NLP pipeline — Partially achieved

**Done**
- FSSI-v3 (XLM-R zero-shot) runs, and BERTopic produces topics.
- New in the final system:
  - six dated event categories;
  - removal of repeated reports of one event;
  - a reported-event vs possible-future-risk flag;
  - "change since the last survey" indicators, cut off at each issue date;
  - a news panel that shows each headline's kind and a context note.

**Not demonstrated**
- Predictive value. With vs without news: Holm p = 1. Real vs shuffled news: p = 0.39. The one strong association did not replicate.
- FSSI is missing for 56% of origins.
- BERTopic topics are largely place names, so they are descriptive only.

### Objective 2 I–IV: classification metrics — Partially achieved

**Done**
- Accuracy, precision, recall, F1, AUC, Brier and the confusion matrix are reported for every lead.
- They are measured on a real two-class hunger outcome (ELEVATED, regional).

**Not achieved**
- The 75% target: the best result is 0.61 at Lead 0.
- **Province-level** high/low classification cannot be scored, because no province is measured.

**Positive result:** the LightGBM is better than the latest reading on level error at Lead 0 (3.47 vs 4.19 points, p = .025). This is development evidence.

### Objective 2 V: reliable horizon — Partially achieved (method), not achieved (result)

**Done:** walk-forward evaluation at Leads 0–4, with publication-date cut-offs, true horizons, a frozen rule and a leakage audit.

**Result:** no lead passes.

**Cause (verified):**
- a validated simulation of the survey shows a 0.64 ceiling one quarter ahead;
- two same-quarter SWS rounds agree on the label only 3 times in 8.

### Objective 3: municipal and city rankings — Partially achieved

**Done:** all 142 LGUs are ranked within their province by FIRI v2 re-weighted by PSA poverty (2021 SAE) and density (POPCEN 2024). Each is labelled as a priority score, with "insufficient local outcome evidence" and poverty-precision notes.

**Not achieved:** the rankings do not come from *validated* province forecasts.
- No provincial or municipal food-insecurity outcome exists for 2021–2026.
- CBMS 2024 LGU results were turned over to LGUs from September 2025 but are not public (`aipheed-backend-aligned/experiments/FINAL_OBJECTIVE_ACHIEVEMENT/sources/LOCAL_DATA_SEARCH_LOG.md`).

### Objective 4: baseline comparison — Achieved

**Done:** all four Chapter I baselines are scored on the same rows at every lead, plus a moving average, climatology and always-ELEVATED.

**Result:** LightGBM is not superior in accuracy. The latest reading is the strongest baseline at Leads 0–2.

### Objective 5: dashboard and evaluation — Partially achieved

**Done**
- The public dashboard works: map, forecast panels, drivers, news, history and the new SWS and evaluation sections. The approved design is kept.
- Backend and frontend tests pass, and the production build succeeds.

**Not done in this work**
- The ISO/IEC 25010 evaluation with DA evaluators.
- FNRI NNS 2019/2023 face validity. NNS 2019 has no CALABARZON regional FIES; NNS 2023 is a single regional figure. These remain to be done or reported as limitations.

## What the system demonstrates, in one paragraph

> aiPHeed integrates SWS hunger surveys, PSA price and socio-economic indicators, climate records and dated news into one quarterly dataset. It trains a LightGBM model that forecasts regional hunger using only information available at each forecast date. Tested walk-forward on 2023–2026, the model improved on the latest survey reading only for the quarter whose survey had not yet been published (error 3.5 vs 4.2 points). It did not reach 75% accuracy at any horizon, and no horizon met the reliability criteria. A validated simulation of the survey shows that 75% exceeds what regional SWS data allow (about 64% one quarter ahead). News helped explain current conditions but did not improve forecasts. The province and municipal map is therefore presented as an indicator-based priority score for planning attention, not as a validated food-insecurity forecast.
