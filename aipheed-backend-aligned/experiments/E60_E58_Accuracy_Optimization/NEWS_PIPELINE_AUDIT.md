# News pipeline audit (E60)

**Sources:**
- `runner/n1_corpus_audit.py` → `out/corpus_audit.json`;
- `runner/n2_collect_triggers.py` (E60 store);
- `runner/n4_classifier.py` (classifier v2);
- `runner/n5_features.py` → `out/news_feature_summary.json`;
- annotation: `NEWS_ANNOTATION_PROTOCOL.md` → `NEWS_CLASSIFICATION_EVALUATION.csv`.

## 1. The corpus behind E40–E59 news features (E31 store)

| Property | Finding |
|---|---|
| Size | 8,320 articles, 2021-01-01..2026-10-14 |
| Source | Google News RSS only. **Titles, publisher domain, publisher publication date. No body text.** |
| Collection | **Retrospective, in one day (2026-10-14).** Articles carry true publication dates, but the set is what the search index still returned in October 2026, so coverage at each historical issue date is not reproducible. |
| Queries | 6 templates per province: food, shocks, assistance, Filipino general, plus 2 regional. **No query asked about OFW remittances, employment or layoffs, or fisheries.** "fish kill" appears only inside the shocks query. |
| Domain policy | Credible-domain list v1. 10,341 items were rejected, including all `.gov.ph` items (policy v2 = adviser decision D8, pending). |
| Cap | at most 100 items per query window; the collector splits windows at the cap. |
| Province attribution | Geocoder on the title: **2,820 / 8,320 (34%)**. On DEV annotations the geocoder was correct for 20 of 22 province-specific titles. The unattributed 66% are mostly national stories with no CALABARZON place. |
| Deployed trigger keywords (v1), attributed articles | market 10, climate 164, employment 1, **OFW 0**, fish kill 17. 107 of 147 keywords never matched an attributed title. |
| Model feature `news_<trigger>` = hits ÷ articles per province-quarter | nonzero province-quarters out of 105: OFW 0, employment 1, market 6, fish kill 7, climate 44 (E59) |

**Root causes of the "zero" news signal:**
1. **Retrieval:** the corpus was never queried for three of the five triggers.
2. **Keywords:** v1 uses bare topic words. They match generic weather bulletins ("typhoon", "habagat") and flood-control politics ("flood"), but rarely match food-stress mechanisms in titles.
3. **Titles only:** mechanisms stated in body text are invisible.
4. **Attribution:** national stories (most rice and price measures) cannot be attributed to a province.

## 2. E60 corrections

- **Retrieval (N2).** Six trigger-specific query templates per province, in English and Filipino, run with the unchanged project collector into a **new store**:
  - covering monthly windows 2021-01..2026-09;
  - with policy v1, the project geocoder, and the `authorized_through` limit of 2026-10-14;
  - query plan in `data/news_e60/query_plan.json`.
  - Totals are recorded in section 4.
- **Classifier v2 (N4).**
  - Triggers fire on **mechanism phrases** (price hike/freeze/ceiling, NFA rice release, crop damage, state of calamity, flood + affected families, fish kill/red tide/fishing ban/oil spill, layoffs/retrenchment/TUPAD, OFW/remittance/repatriation).
  - **Exclusion families** come from DEV errors: flood-control politics, crime, sports, business openings, promotions and recipes, cosmetics, festivals.
  - **Weather items count only if they name a CALABARZON place.**
  - Developed on the DEV annotation half only. Frozen by sha256 (`runner/CLASSIFIER_V2_SHA256.txt`) before the EVAL half was scored.
- **Features (N5).**
  - Shares and changes relative to each province's own coverage, so more coverage does not mean more risk.
  - Regional shares for national triggers.
  - Distinct-event counts (near-duplicate titles merged).
  - Only articles published in quarter t, before the issue date O(t).

## 3. Collection results (N2)

**Requests:** 2,070 (6 templates × 5 provinces × 69 months).
- Status: 1,486 OK, 584 empty, 0 at the 100-item cap, 0 failures.
- Collected 2026-10-18/19. Publication dates span 2021-01..2026-09.

**Articles:**
- Admitted under policy v1: 2,132; rejected: 6,154 (domain policy).
- **New unique articles: 1,347.** The rest duplicate the E31 store.

**New articles by query:**

| Query | Articles | Relevant under v2 |
|---|---|---|
| fish | 519 | 84 |
| OFW | 409 | 31 |
| market | 170 | 51 |
| climate | 169 | 21 |
| employment | 63 | 27 |
| Filipino | 17 | 2 |

**Precision of trigger retrieval is low.** Most "OFW" results are crime, deaths abroad and human-interest stories. Most "fish" results are marine conservation and reclamation stories.

**Province attribution of new articles: 27%.** OFW and employment stories are almost all national.

## 4. Classifier evaluation (EVAL half, `NEWS_CLASSIFICATION_EVALUATION.csv`, `out/classifier_eval.json`)

**Sample:** 77 titles (1 "cannot tell" excluded), 16 relevant. Annotator: Claude (AI), pending human verification.

| Classifier | Relevance precision | Recall | F1 | Trigger correct on relevant titles |
|---|---|---|---|---|
| v1 (deployed keywords) | 0.28 (9 TP, 23 FP) | 0.56 | 0.38 | 9 / 16 |
| **v2 (E60)** | **0.92** (12 TP, 1 FP) | **0.75** | **0.83** | 12 / 16 |

**Geocoder:** 27 of 27 province-specific titles correct; 2 non-province titles wrongly attributed.

**Error patterns:**
- **v1 false positives:** typhoon and habagat bulletins, flood-control politics, transport and power news.
- **v2 misses:** "flooding in Cabuyao" (impact verb absent), farm-gate pricing, 4Ps support, and "affected by Kristine receive food packs" with two provinces named.
- **v2 false positive:** NFA rice arriving in Cebu (non-CALABARZON).
- **In production use, v2 also counted** "Laguna city under state of calamity due to pertussis" (a health story) as climate.

**Small support.** With 16 relevant EVAL titles, the 95% interval for v2 recall is roughly 0.48–0.93.

## 5. News features (N5, `out/news_feature_summary.json`)

**Corpus used:** E31 + E60 = 9,667 titles; 697 relevant under v2.

| Trigger | Relevant titles | Province-quarters with a nonzero share (of 105) | Before E60 (v1) |
|---|---|---|---|
| market | 253 | 18 | 6 |
| climate | 189 | 38 | 44 |
| fish kill | 169 | 22 | 7 |
| employment | 50 | 13 | 1 |
| OFW | 36 | 0 | 0 (entered as a regional share only) |

Of the 697 relevant titles, 297 are province-attributed.

**Timing tests pass** (`tests/test_e60.py`): features rebuilt from articles published before the issue date are identical, and perturbing articles of quarter t+1 changes nothing at origin t.

## 6. Does better news make better forecasts? (`NEWS_ABLATION_RESULTS.csv`)

**No, not measurably.**

| Comparison | Result |
|---|---|
| C (government + news) vs A (government only), paired Brier of P(HIGH), quarter bootstrap | **+0.003 [−0.018, +0.027]**. By quarter, C has the lower Brier in 6 and the higher in 3 (sign test p = 0.51), but its mean Brier is slightly higher. |
| Decisions where C and A differ | 5 of 50: news removed 2 false alarms and 3 correct warnings (net −1); C's warning catches 6 of 10 onsets, A's 7 |
| B, news only | accuracy 0.36–0.40, ROC-AUC 0.48–0.58, Brier 0.41–0.45: no usable signal about food-price pressure two quarters ahead |

**Conclusion:** the classifier is much better than before (F1 0.38 → 0.83), but the better news features do not improve the two-quarter-ahead forecast. The improvements to classification and to forecasting are separate questions, and only the first is supported.
