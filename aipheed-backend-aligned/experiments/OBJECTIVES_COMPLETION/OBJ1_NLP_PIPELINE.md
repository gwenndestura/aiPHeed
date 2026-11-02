# Objective 1: the two-tier NLP pipeline, end to end

> "To design a two-tier pipeline combining zero-shot XLM-RoBERTa Filipino-English sentiment extraction and BERTopic
> unsupervised topic modeling to produce the bias-corrected Food Stress Sentiment Index and latent food insecurity
> risk patterns per province-quarter from a Filipino-English news corpus." (Chapter I §1.5.2)

**Status: Partially achieved.**
- The pipeline is built and produces both outputs (the bias-corrected FSSI and BERTopic patterns).
- Coverage per province-quarter is thin.
- The news signals did not improve the food-insecurity forecast.

Measured numbers come from `runner/measure.py` → `out/obj1_news_measures.json`. They are read-only; no model was fitted.

## 1. The pipeline

| Stage | Implementation (code) | Measured output |
|---|---|---|
| **Corpus** (Filipino-English) | RSS headlines from Philippine outlets, English and Filipino (E31 + E60 stores, `backend/app/news/pipeline_v3.corpus`); GDELT GKG CALABARZON documents as an independent source (E85) | **9,667** headlines, 2021-Q1..2026-Q3; 58,576 GDELT documents |
| De-duplication | Same normalised title within 3 days, any outlet (`pipeline_v3.dedupe`) | Syndicated copies counted once |
| Relevance | Classifier v2 (`backend/app/news/classifier_v2.py`) | **695** relevant headlines admitted, of which **296** carry a CALABARZON province |
| **Tier 1: zero-shot XLM-RoBERTa** | `joeddav/xlm-roberta-large-xnli` (`backend/app/ml/nlp/classifier.py`). Natural-language inference: the headline is the premise, and each food-stress hypothesis is scored **in English and in Filipino**, keeping the higher P(entailment). No labelled training data (zero-shot). | Intensity in [0, 1] stored for every province-attributed admitted headline (296) |
| **Bias-corrected FSSI (FSSI-v3)** | `pipeline_v3.fssi_v3` (Equation 2): FSSI = bias weight × mean intensity. The bias weight is log(1 + median n) / log(1 + n), with the median taken over the provinces' article counts that quarter, so a province is not called "stressed" just because it is covered more. Status is SUFFICIENT with ≥ 5 articles, else LIMITED_SIGNAL or NO_USABLE_EVIDENCE; missing is never zero. | Provincial FSSI-v3 over **115 province-quarters** (5 × 23): **20 SUFFICIENT (17%)**, 42 limited, 53 with no usable evidence |
| Regional FSSI (N1R) | Mean intensity of all items of the quarter published before the issue date, ≥ 5 items (FIRI_V2 Addendum 2) | Available in **16 of 23** quarters; mean 0.23 (range 0.05–0.50) |
| **Tier 2: BERTopic** | `backend/app/news/topics.py`, `backend/app/ml/nlp/topic_model.py`: multilingual embeddings `paraphrase-multilingual-MiniLM-L12-v2`, UMAP (random_state 42), HDBSCAN, minimum topic size 10, KeyBERT-inspired labels; titles only | **152 topics**, outlier share 39.7%, topic proportions for **120 province-quarters** (`backend/data/news_v3/topics_manifest.json`, `article_topics.csv`) |
| Event categories (E112) | Fixed English and Filipino title lexicon: price, shortage, disaster, agricultural supply, jobs and income, assistance; shares per quarter; cut at the issue date | 0% missing at every evaluated origin, 2021-Q1..2026-Q3 |
| Issue-date cut-off | Only items published before the forecast issue date (`pipeline_v3.asof`) | Tested by perturbation in IMPROVE_V2 (randomizing later FSSI items changed nothing) |

## 2. Do the signals measure what they claim? (validation, no hunger data used)

From `E112_Food_Insecurity_Forecasting/E112_NEWS_EVALUATION.md` §2 (Spearman, one-sided):

| Check | Corpus ρ (p) | GDELT ρ (p) | Valid? |
|---|---|---|---|
| Disaster share vs typhoon count | **0.81 (< .001)** | **0.73 (< .001)** | **Yes, in both sources** |
| Price share vs headline inflation | −0.13 (.72) | −0.03 (.56) | No |
| Agricultural supply vs fisheries drop | 0.38 (.059) | 0.36 (.070) | Borderline |
| Jobs and income vs unemployment change | 0.28 (.13) | 0.34 (.087) | No |

Disaster news is a validated signal. Price news does not track measured inflation.

## 3. "Per province-quarter": the coverage limit

- Only 296 of the 695 relevant headlines (43%) name a CALABARZON province.
- So a provincial FSSI has enough evidence (≥ 5 articles) in only **17%** of province-quarters.
- Coverage grows over time: no sufficient province-quarter in 2021–2022, and up to 4 of 5 provinces in 2025-Q3 and 2026-Q3.

This is a limit of the corpus, not of the code. A fuller per-province FSSI needs more province-tagged Filipino-English
news (category (b)).

**BERTopic produces patterns for 120 province-quarters, but they are descriptive.**
- The topic model is fitted once on all quarters, so later articles shape earlier topics. The code therefore labels the topics "descriptive latent patterns; not a forecast feature".
- Many topics are named after places (`docs/final_system/THESIS_OBJECTIVE_ASSESSMENT.md`).

## 4. Does news improve the food-insecurity forecast? (the honest result)

From IMPROVE_V2 (`RESULTS.md` §7), the food-insecurity LightGBM with and without the news columns, on the same
quarters:

| Result | Evidence |
|---|---|
| Adding news to the reference | Brier **worse**: +0.008 at Lead 1 (p 0.82), +0.015 at Lead 2 (p 0.96) |
| Best case for news | I2 at Lead 1: −0.002, p 0.11 (not significant) |
| News-only logistic regression | Worst model: Brier 0.353 (Lead 1) and 0.434 (Lead 2) on the news era |
| News-only LightGBM (H3 comparator) | Brier 0.307 / 0.310; worse than the reference (Holm p 0.014 at Lead 1, 0.061 at Lead 2) (`OBJ4_H3_COMPARISON.md`) |
| SHAP share of the news group | 0.8–4.1% of the model's influence |

**News did not improve the forecast.**

## 5. Null hypothesis H1 (SHAP)

> "The Food Stress Sentiment Index (FSSI) and food CPI deviation will not be among the strongest predictors of food
> insecurity risk in CALABARZON when examined through SHAP feature attribution."

SHAP group shares of the food-insecurity LightGBM with news (IMPROVE_V2 REF+news, Lead 1, 62 quarters):
- SWS hunger history: 64.3%;
- world prices: 21.2%;
- CALABARZON food and headline prices: 6.1%;
- news (FSSI and categories): 2.8%;
- rice: 2.5%;
- climate: 1.9%.

FSSI and food CPI are **not** among the strongest predictors. **H1 is not rejected.**

## 6. What can and cannot be claimed

**Can be claimed:**
- A working two-tier Filipino-English pipeline: zero-shot XLM-R intensities and a bias-corrected FSSI-v3, plus BERTopic patterns.
- Every item is dated and cut at the issue date.
- Disaster coverage is validated against the typhoon record (ρ = 0.81).

**Cannot be claimed:**
- That FSSI exists for most province-quarters (17%).
- That BERTopic patterns are forecast features.
- That news improves the food-insecurity forecast.
