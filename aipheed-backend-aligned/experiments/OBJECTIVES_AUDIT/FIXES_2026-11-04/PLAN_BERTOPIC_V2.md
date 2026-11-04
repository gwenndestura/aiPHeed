# BERTopic topic-quality fix (T2): pre-registration (fixed before any fit, 2026-11-04)

**Scope:** Objective 1 topic quality only. No forecasting model is fitted or rescored. The forecast inputs are not
changed by this plan.

## Why the served topics fail (from `out/obj1_topics.json`, before this plan)

| Rule (OBJ1_PREREGISTRATION.md §2) | Served, time-safe mean | Result |
|---|---|---|
| NPMI coherence > 0 | −0.47 | fail |
| Place-name share < 50% | 53% | fail |
| ARI ≥ 0.30 | 0.44 | pass |

Diagnosis, stated before fitting:
1. **Geography drives clustering.** Headlines name a town or province, and the frozen encoder embeds that name. Similar
   headlines from one place cluster together, so topics become places. Geography is already measured by the geocoder,
   so the topic model should see themes only.
2. **KeyBERTInspired picks words that rarely co-occur.** It selects words close to the topic embedding, not words
   that appear together in headlines. Pairs that never co-occur score NPMI −1.
3. **Filipino function words were never removed.** The OBJ1 plan named English and Filipino stop words; only English
   was used (recorded deviation).

## Candidate T2 (exactly one)

Served settings (`runner/obj1_nlp._fit`) **unchanged** except these three changes:

1. **Place-name masking before embedding and vectorizing.** Remove every whole word (case-insensitive, with an optional
   trailing `'s`) in G = `obj1_nlp._names()` ∪ {"lucena"} − {"pila"}. ("pila" is excluded because it is also the
   Filipino word for a queue, a food-access theme.) Multiple spaces are collapsed. The encoder then embeds the masked
   headline.
2. **Stop words:** scikit-learn English ∪ this fixed Filipino list: ang, ng, sa, na, mga, at, ay, para, si, ni, kay,
   ito, iyan, yan, may, mayroon, hindi, din, rin, lang, lamang, po, ba, pa, nang, kung, pero, dahil, kasi, siya, sila,
   kami, tayo, natin, namin, nila, niya, ko, mo, ka, ako, ikaw, ating, aming, kanilang, kanyang, mula, hanggang,
   tungkol, bilang, upang, o, kina, nina, sina, ngayon, raw, daw, naman, pala, bawat, iba, ibang, isang, ayon, habang,
   pag, kapag, nito, doon, dito, roon, rito, ano, saan, bakit, paano, sino, kaya, muna, pati, ilang, lahat, wala,
   walang, ating, kanila, sa, ni, nag, mag, mas, pang.
3. **Representation:** BERTopic's default c-TF-IDF (no `KeyBERTInspired`).

**Unchanged:** encoder `paraphrase-multilingual-MiniLM-L12-v2` (frozen); UMAP (n_neighbors 15, n_components 5,
min_dist 0, cosine, random_state 42); HDBSCAN (min_cluster_size 10, eom); CountVectorizer n-grams (1, 2), min_df 2;
top_n_words 10; corpus `pipeline_v3.corpus()`; origins 2022-Q1..2026-Q3, each fitted only on headlines published
before O(t); ARI between consecutive fits.

## Metrics (definitions unchanged)

- **NPMI:** `obj1_nlp._npmi` on each topic's top 10 words split into unigrams, over the token sets of the fitted
  headlines (as fitted, i.e. masked for T2); mean over topics, then mean over origins.
- **Place-name share:** topics whose top 3 words contain a word of the original `obj1_nlp._names()` set.
- **ARI:** as served.
- **Added, stricter (because masking alone could make the place-name share pass by construction):** the
  **geography-driven share.** Among headlines with a geocoded `province_code`, for each non-outlier topic with at
  least 10 such headlines, compute the share from its most common province. A topic is geography-driven if that share
  is ≥ 0.80. Report the share of evaluated topics that are geography-driven (mean over origins).

The served model (T0) is refitted with the same harness at the same origins, so T0 and T2 are compared on identical
code. T0 must reproduce the stored summary (NPMI, place-name share and ARI within 0.01) or the run stops.

## Decision (fixed)

Topic quality is **achieved** only if T2's means satisfy all four: NPMI > 0; place-name share < 0.50; ARI ≥ 0.30;
geography-driven share < 0.50. Then time-safe T2 topic proportions become **eligible** as future descriptive or
model inputs (any model use needs its own pre-registration). Otherwise topics stay descriptive and **no further
variant is tried.**

**Descriptive ablations (run only after the T2 decision is written; never used for the decision):** A1 = T0 +
masking only; A2 = T0 + c-TF-IDF only.

**Reported whatever the result.**
PLAN-SHA256: 036676491f1f92c7945af7d1c6e5565943e643503b05513933770d3088f7e16f
