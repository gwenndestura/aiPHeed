# Objective 1 pre-registration: news early-warning test and issue-date-safe BERTopic

**Fixed before any computation:** written and hashed on 2026-11-03.

## 1. Early-warning test (does news anticipate the direction of hunger change?)

**Outcome:** Δ(t) = H(t+1) − h_last(t). H(t+1) is the Balance Luzon SWS quarter mean of the target quarter; h_last(t)
is the newest reading published before O(t). This is the change C-b fails to anticipate (reversals).

**Signals:** all at origin t, from items published before O(t):

| ID | Signal | Source |
|---|---|---|
| EW1 | `z_N1R`: FSSI anomaly (C-b's NLP input) | `NEW_MODEL/NEWS_V2/out/news_anomalies.csv` |
| EW2 | ΔN1R = N1R(t) − N1R(t−1): change in the regional FSSI | `IMPROVE_V2/out/table_pooled.csv` |
| EW3 | Price share of news | Same table |
| EW4 | Shortage share | Same table |
| EW5 | Disaster share | Same table |
| EW6 | Jobs-and-income share | Same table |

**Hypothesis per signal:** higher news stress → a rise in hunger.

**Test:**
- Spearman ρ(signal, Δ) over origins with both values (news era 2021-Q1 to 2026-Q2).
- One-sided permutation p, 10,000 permutations, seed 2036.
- **Holm across the 6 tests**, α = 0.05.

**Secondary (descriptive):** direction hit rate. Sign(signal − its median) vs sign(Δ), against 50%.

**Reported whatever the result.** n is about 20, so power is low and this is stated. A pass would justify a future
pre-registered model test; it is not a forecast-improvement claim.

## 2. Issue-date-safe BERTopic

**Encoder:** the pretrained `paraphrase-multilingual-MiniLM-L12-v2` is frozen. Embedding a headline uses no corpus
information, so it is not leakage.

**Leakage-safe fit:** at each origin t from 2022-Q1 to 2026-Q3, the topic model is fitted only on headlines published
before O(t). The headlines of quarter t are assigned with `transform`.
- **Settings:** the served settings, unchanged: UMAP random_state 42, n_neighbors 15, n_components 5, cosine;
  HDBSCAN min_cluster_size 10; CountVectorizer with English and Filipino stop words.

**Metrics** (for each fit, and for the existing all-quarter model):
- number of topics;
- outlier share;
- **NPMI coherence** of each topic's top 10 words, over the fitted documents (sliding document co-occurrence; mean
  over topics);
- **place-name share:** topics whose top 3 words include a CALABARZON province, city or municipality name or
  "calabarzon";
- **stability:** adjusted Rand index of topic assignments between consecutive fits, on documents in both.

**Decision:** temporal topic proportions become eligible as future model features only if:
- mean NPMI > 0;
- the place-name share is < 50%;
- mean consecutive ARI ≥ 0.3.

Otherwise topics stay descriptive (monitoring and explanation only). **No forecasting model is fitted here.**
PLAN-SHA256: c263c36ee7e5a557268831e0605e202b41df93cc964d7eece41bfd2300acd131
