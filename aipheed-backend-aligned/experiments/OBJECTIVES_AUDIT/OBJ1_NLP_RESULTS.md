# Objective 1: NLP validation results

Pre-registration `OBJ1_PREREGISTRATION.md` (`c263c36e…d131`).
Runner `runner/obj1_nlp.py`; outputs in `out/obj1_*`; annotation tooling in `annotation/`.

## 1. Pipeline verified

- **XLM-RoBERTa scores are real model outputs.** Every stored score is from `joeddav/xlm-roberta-large-xnli`. None
  comes from the keyword fallback.
- **Issue-date cut:** the FSSI and news features use only items published before O(t). This was checked by
  perturbation in IMPROVE_V2 and NEWS_V2.

## 2. Coverage, geography and source balance (`out/obj1_coverage.json`)

| Measure | Value |
|---|---|
| Corpus | 9,667 headlines, 2021-Q1..2026-Q3, 37 outlets |
| Relevant (classifier v2), after removing syndicated copies | 695 (2 copies dropped) |
| With a CALABARZON province | **296 (43%)**; 399 relevant headlines name no province |
| By province | Cavite 99, Batangas 72, Laguna 47, Quezon 41, Rizal 37 |
| Province-quarters with ≥ 5 articles (FSSI SUFFICIENT) | **20 of 120 (16.7%)**; 46% have zero |
| By year | 2021: 0, 2022: 1, 2023: 2, 2024: 7, 2025: 4, 2026: 6 |
| Source concentration | Top 5 outlets = 69% of the corpus (Inquirer, GMA, Manila Bulletin, Philstar, DA); HHI 0.12 |

**Why coverage is low:**
- Headlines rarely name a province (57% of relevant ones do not).
- The corpus is a 2021+ RSS collection, dominated by national outlets.
- Cavite's coverage is 2.7 times Rizal's (geographic bias). The Eq. 1 bias weight down-weights heavily covered
  provinces, but it cannot create evidence where there is none.

## 3. Why FSSI has ≈0% SHAP and changes no classification

| Cause | Evidence |
|---|---|
| **Temporal availability** | The FSSI anomaly exists at 0% of the 1998–2009 training origins and at 17% of the evaluated origins (from 2023-Q2) (`out/obj2_predictor_availability.json`). The model learns almost entirely from rows without news |
| **Geographic mismatch** | The target is Balance Luzon; the news is CALABARZON-tagged |
| **Weak signal** | No news signal anticipates the direction of hunger change (§4) |
| **Construction** | Level FSSI drifted with corpus growth (removed by the anomaly). Every construction that let news carry weight lost accuracy (REF+news, C-a, GDELT) |

**Conclusion:** the near-zero influence is a property of the data available, not a coding error. Forcing weight onto
news would be manipulation.

## 4. Pre-registered early-warning test (`out/obj1_earlywarning.json`)

Spearman between each signal at origin t and the next hunger change H(t+1) − h_last; 10,000 permutations; Holm over
6 tests.

| Signal | n | ρ | raw p | Holm p |
|---|---|---|---|---|
| FSSI anomaly (z_N1R) | 10 | +0.44 | 0.100 | 0.60 |
| ΔFSSI | 10 | −0.13 | 0.65 | 1.00 |
| Price share | 20 | −0.11 | 0.68 | 1.00 |
| Shortage share | 20 | −0.33 | 0.92 | 1.00 |
| Disaster share | 20 | +0.04 | 0.44 | 1.00 |
| Jobs and income share | 20 | −0.24 | 0.85 | 1.00 |

**No news signal has early-warning value for hunger changes** (n is small: 10–20).

## 5. Issue-date-safe BERTopic (`out/obj1_topics.json`)

**Fit:** at each of 19 origins (2022-Q1..2026-Q3), BERTopic was refitted with the served settings on headlines
published before O(t) only. This removes the temporal leakage of the all-quarter model.

| | All-quarter model (leaky) | Time-safe fits (mean) | Pre-registered rule | Result |
|---|---|---|---|---|
| Topics | 146 | 17 → 151 (grows with the corpus) | — | — |
| Outlier share | 37% | 30–41% | — | — |
| NPMI coherence | −0.37 | **−0.47** | > 0 | **Fail** |
| Place-name topics | 55% | **53%** | < 50% | **Fail** |
| Stability (ARI, consecutive fits) | — | **0.44** | ≥ 0.30 | Pass |

- **Decision (pre-registered):** the topics are **not eligible as forecast features**. They remain descriptive, used
  for monitoring and explanation.
- **Interpretation:** headlines are 8–15 words, so topic words rarely co-occur in one document, which drives NPMI
  negative. Topics also cluster by place name rather than food-insecurity theme.
- **Deviation recorded:** the stop words are English only, as in the served code. The plan text had wrongly said
  English and Filipino.

## 6. Human-labelled validation set (prepared; not yet labelled)

- **Sample:** 300 headlines (seed 2036) in four strata. The system outputs are sealed in `system_outputs_SEALED.csv`
  for blind annotation.
- **Guide:** `annotation/ANNOTATION_GUIDE.md`.
- **Next step:** two team members label `labels_annotator_A.csv` and `labels_annotator_B.csv` independently, then run
  `obj1_nlp.py score`. It reports:
  - κ;
  - relevance precision and recall;
  - geocoder accuracy;
  - XLM-R AUC against food stress.
- **No label was generated.** Relevance and geocoding accuracy remain unmeasured until the team labels the sheets.

## 7. What NLP contributes (honest statement for the thesis)

| Value | Status |
|---|---|
| **Predictive value** (forecast) | None measured |
| **Early-warning value** (hunger changes) | None measured |
| **Monitoring value** | Disaster coverage tracks typhoon counts (ρ 0.81, both corpora); topics describe what the news reports per quarter |
| **Explanation value** | Headlines and FSSI shown as context beside the forecast |
