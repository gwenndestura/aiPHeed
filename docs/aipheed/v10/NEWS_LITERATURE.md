# v10 Stage 1: Literature on news for food-insecurity prediction

**Levels:** FULL (text read), PARTIAL (abstract or excerpt only), UNVERIFIED-CITATION (not confirmed; **Gate 1: no technique adopted from it**). Fetched 2026-11-02.

## Evidence table

| Item | Balashankar et al. 2023, Sci. Adv. 9(9) eabm3449 ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9984173/)) | Ahn et al. 2023, HungerGist ([arXiv 2311.10953](https://arxiv.org/html/2311.10953)) |
|---|---|---|
| Level | FULL (main text; supplement not read) | FULL |
| Text and volume | 11.2 M articles, 5,421 sources (Factiva), 1980–2020 | 53,266 articles (GDELT) |
| Languages | English only | English and French (French machine-translated) |
| Filter, geolocation | Factiva region tags; frame-semantic parse; district, province, country levels | GDELT themes; **country level only** |
| Features | 1,949 candidates reduced to 167 by Granger tests, in 12 clusters | Sentence embeddings with attention; multi-task |
| Normalization | **Share of a month's district-mentioning articles that mention the feature**; first-differenced if non-stationary | Bootstrap pseudo-articles per country-month |
| Timing | 6 months of lagged news; all predictors at least 3 months old at prediction | 1 month ahead |
| Target | IPC phase; outbreak = phase ≥ 3 for two periods after ≤ 2 | Food Crisis Index (IPC, interpolated to monthly) |
| Sample | 40,952 district-quarters, 1,162 districts, 21 countries | 2,340 train samples, 9 countries |
| Model | Random forest | Attention network |
| Validation | 10 temporal folds; feature selection on **fold 1 only**; Diebold-Mariano | Temporal hold-out |
| Gain over no-news | RMSE at 3 months: traditional 0.1486, news 0.0989, both 0.0819. Recall at 80 % precision: 1,145, 1,432, 1,677 of 1,852 | RMSE 1.074 baseline to 0.790 |
| Where it did not help | Weaker where coverage is thin; removing the top 10 sources raised RMSE 39 % | **Baseline wins in Niger and Burkina Faso** |
| Stated limits | English-only, coverage bias, source dependence; 6- and 12-month numbers only in supplement (**not read**) | Country level; translation; source quality not evaluated |

**Citation note.** The 2021 arXiv version (15 states, 915 districts) differs from the published paper. Only the published figures are used.

## Other sources

| Source | What it shows | Level |
|---|---|---|
| Foini et al. 2023 ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10038988/)) | No news. Permutation-entropy predictability low; **ML beats last value only with long history** | FULL |
| Andrée et al. 2020 | No news. Non-news baseline for food-crisis prediction | FULL |
| Carneiro et al. 2025 ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12540806/)) | FEWS NET report text, not news; not a forecast | FULL |
| van Wanrooij, Cruijssen, Olier 2024, Decision Sciences 55(6) ([DOI](https://onlinelibrary.wiley.com/doi/10.1111/deci.12653)) | BERTopic on news; existence and method confirmed. **Numeric gain not read** (publisher blocks fetch) | PARTIAL |
| Nowcasting commodity prices using social media, PeerJ CS 2017 ([article](https://peerj.com/articles/cs-126/)); UN Global Pulse ([summary](https://www.unglobalpulse.org/document/nowcasting-food-prices-in-indonesia-using-social-media-signals/)) | Bahasa Indonesia tweets, 15 months, daily prices for 4 foods. **A nowcast, not a lead** | PARTIAL |
| XLM-R NLI model card ([HF](https://huggingface.co/joeddav/xlm-roberta-large-xnli)) | Fine-tuned on 15 languages; **Tagalog not among them**; base pre-trained on 100 | FULL |
| Zero-shot POS tagging for Filipino, FieldMatters 2024 ([ACL](https://aclanthology.org/2024.fieldmatters-1.9.pdf)) | XLM-R transfers to Filipino for POS, not for this task | PARTIAL |
| Lentz 2019; Westerveld 2021 | No news features in what was read | PARTIAL |
| GDELT food-price-spike study; FAO, WFP, FEWS NET media monitoring; humanitarian low-resource zero-shot | **None found in these searches** | UNVERIFIED-CITATION |

## Findings that contradict the project's own text

1. **Hypotheses are not from HungerGist.** `app/ml/nlp/classifier.py` says "Ten bilingual HungerGist hypotheses (Ahn et al., 2023 + PH extensions)". The paper uses **no zero-shot, NLI or hypothesis list** (VERIFIED, targeted re-fetch). The hypotheses are this project's own design and should be cited as such.
2. **No published zero-shot validation on Filipino food-news headlines was found.** So the Chapter I method has no direct precedent; a local labelled sample is the only possible validation.
3. **Chapter I's "months ahead" claims rest on panels of tens of thousands of rows.**

## What transfers to CALABARZON and what does not

| Technique | Transfers? | Reason |
|---|---|---|
| Share of articles normalization | **Yes** | Directly removes coverage growth (Balashankar). Adopted as N1 |
| Coverage as a stated limit | **Yes** | Both papers show thin coverage hurts; adopted as N7 |
| Temporal folds; feature selection on past data only | **Yes** | Adopted |
| Publication-lag gate | **Yes** | Adopted through `as_of` |
| First-differencing non-stationary news | **Yes** | Adopted as N4 |
| Granger filtering of ~2,000 candidates | **No** | 10–20 effective quarters cannot support it |
| Deep models on raw text | **No** | No labels at this resolution |
| Random forest on 40,000 rows | **No** | Sample ratio about 800:1 against this panel |
| IPC targets | **No** | None exist here |
| District-level gain | **No** | Corpus gives a median of 0 relevant headlines per province-quarter |
| Body-text frame parsing | **No** | Corpus holds headlines only |

**Expectation, stated before any test (INFERRED):** the literature gives no reason to expect a detectable gain with this corpus and sample. A `NEWS_NO_GAIN` or `NOT_YET_TESTABLE` result would be consistent with it, not a failure of the method.

## Gate 1

**PASSED:** the techniques adopted come from FULL sources. Nothing from an UNVERIFIED-CITATION source is adopted.
