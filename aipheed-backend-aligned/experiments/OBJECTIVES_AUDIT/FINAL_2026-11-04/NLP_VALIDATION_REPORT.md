# NLP validation report (Objective 1)

## Status

| Part | Status |
|---|---|
| Technical implementation | **Completed** |
| Temporal safeguards | **Completed** |
| Human validation | **Pending external action:** 0 of 300 headlines labelled |
| Predictive value | **Not achieved:** measured, no material value |

## 1. Pipeline audit (`OBJ1_NLP_RESULTS.md`, 2026-11-03, plus today's checks)

| Component | Finding |
|---|---|
| XLM-RoBERTa | Every stored score comes from `joeddav/xlm-roberta-large-xnli` (zero-shot NLI); none from the keyword fallback |
| Filipino-English | The multilingual model scores titles as-is; Taglish is not translated. BERTopic stop words are English only, as served (recorded deviation) |
| Relevance and duplicates | Classifier v2 admits 695 of 9,667 headlines; 2 syndicated copies removed |
| Geographic attribution | 296 of 695 (43%) name a CALABARZON province: Cavite 99 … Rizal 37 (2.7× imbalance) |
| Issue-date cut | Only items published before O(t) are used. Verified by perturbation (IMPROVE_V2, NEWS_V2) |
| FSSI and bias correction | Eq. 1 weights down-weight heavily covered provinces. The anomaly form `z_N1R` removes corpus-growth drift |
| BERTopic | Refitted at 19 origins on past headlines only; not eligible as features (`BERTOPIC_TEMPORAL_VALIDATION.md`) |
| Coverage | 20 of 120 province-quarters have ≥ 5 articles; 46% have none |

## 2. Predictive contribution (identical origins; `out/obj4_table.json`, `out/ce5_results.json`)

| | L1 Brier | L2 Brier | L1 accuracy | L2 accuracy | Quarters |
|---|---|---|---|---|---|
| Government-only LightGBM | 0.233 | 0.240 | 0.677 | 0.597 | 62 |
| Government-only logistic (PSA-only) | 0.208 | 0.239 | 0.726 | 0.677 | 62 |
| NLP-only LightGBM | 0.307 | 0.310 | 0.600 | 0.526 | 20 / 19 |
| NLP-only logistic | 0.353 | 0.434 | 0.450 | 0.421 | 20 / 19 |
| **Government + NLP (C-E2)** | **0.188** | **0.188** | **0.774** | **0.758** | 62 |
| C-E2 without NLP (ablation) | 0.189 | 0.189 | 0.774 | 0.758 | 62 |

- **The combined model is best.** Its gain comes from SWS persistence and the price inputs, not from news.
- **News improves Brier by 0.0014 / 0.0011** and changes 0 of 62 classifications.

## 3. Why news adds little (`out/obj1_fssi_redundancy.json`)

- **It is available at 12 of 113 origins.** Only 10 have a known label (2023-Q3..2026-Q3).
- **Its link to next-quarter hunger is not significant:** ρ 0.45 (p 0.19, n = 10).
- **It is redundant with price and climate inputs:** ρ 0.78 with world crude oil, 0.76 with rice inflation, 0.71 with
  ONI.
- **No early-warning value:** Holm p ≥ 0.60 for all 6 news signals (`out/obj1_earlywarning.json`).

## 4. Human validation

- **Prepared:** `HEADLINE_ANNOTATION_PACKAGE.md`.
- **Blocker:** the two team members' labels. No label was generated.
