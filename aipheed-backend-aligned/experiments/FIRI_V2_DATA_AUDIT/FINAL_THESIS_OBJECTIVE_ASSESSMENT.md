# Final thesis objective assessment (Chapter I, audited inputs)

Judged against Chapter I of `THESIS 2 (11).pdf` only (extract: `../FINAL_THESIS_OBJECTIVES/sources/chapter1_THESIS2_11_extract.txt`). Numbers come
from the audited-input run (`out/rerun_results.json`), which governs under Addendum 1. Also kept as
`../FINAL_THESIS_OBJECTIVES/THESIS_OBJECTIVE_ASSESSMENT.md`.

| Objective | Status | What can be claimed | What cannot be claimed |
|---|---|---|---|
| **1** NLP pipeline turning news into food-insecurity signals (FSSI) | **Met as a pipeline; no predictive value shown** | News is collected, classified (FSSI-v3, XLM-R zero-shot) and dated; it enters the model as family N1 and is shown in the dashboard as context with its kind (price, supply, assistance…) | That news improves the forecast: no gain at Leads 0–1, significantly worse at Leads 2–3 (Holm p .032, < .001); regional FSSI with full coverage also no gain |
| **2 I–IV** accuracy, precision, recall, F1 of province-level high/low classification | **Met at Lead 1** | Lead 1: accuracy 0.914 (90% CI 0.843–0.971), balanced 0.883, precision 0.82, recall 0.82, F1 0.82, AUC 0.923, on 70 province-quarters from 14 quarters, 2023–2026, issued before each quarter began | That the 70 rows are 70 independent outcomes (≈ 14 independent quarters); any accuracy beyond Lead 1 |
| **2 V** maximum reliable forecast horizon | **Determined: 1 quarter** | Lead 1 passes all seven frozen reliability rules; Leads 2, 3, 4 fail (0.583, 0.520, 0.575, all below always-LOW) | A two-quarter or longer warning. Under the stricter variant (balanced accuracy above every baseline) no lead qualifies |
| **75% accuracy target** | **Reached at Lead 1 only** | 0.914 ≥ 0.75, lower bound 0.843 also ≥ 0.75; beats always-LOW (0.757) and same-information persistence (0.743) | 75% at Lead 2 or beyond |
| **3** municipal priority rankings from validated province forecasts, with poverty and density | **Ranking delivered; quality not yet evaluated** | 142 LGUs ranked within each province: province probability × (0.6 poverty + 0.4 density), from a province forecast validated at Lead 1 | Measured municipal food insecurity; any municipal accuracy. Hypothesis 4 is judged by DA evaluators' assessments, which have not been collected |
| **4** compare against LR and LightGBM on government and NLP data | **Mostly met; H3 not rejected** | At Lead 1 CH1-LGBM has a significantly lower Brier score than PERSIST-SI, LR-COMB, LR-GOV, LR-NLP and LGBM-NLP (Holm p < 0.001) | Superiority over LGBM-GOV (tie, p 0.83), so "better than all six" fails |
| **5** dashboard, ISO 25010 evaluation, FNRI face validity | **Dashboard and face validity done; ISO 25010 pending** | Dashboard serves the model, its tested accuracy, data freshness and provenance; FNRI FIES agrees in direction (2023 CALABARZON 19.1%; poor ≈ 2× non-poor) | The ISO 25010 results: the survey of DA evaluators has not been run |

## Hypotheses

- **H1–H2** (metrics / horizon): the Lead-1 model performs above chance and above the 75% target; the horizon test
  rejects reliability beyond Lead 1.
- **H3** (no difference from comparators): not rejected under the all-six rule because of the LGBM-GOV tie; rejected
  for five of six comparators individually.
- **H4** (rankings acceptable to DA evaluators): untested until the evaluation is held.

## What changed with the data audit

Three input defects were corrected (BSP remittances, typhoon counts, the partial 2026-Q3 rice quarter). No status
above changed. The limits are outcome count and forecastability, not data quality.
