# News features and their contribution

**Bottom line.**
- The news pipeline now produces dated, de-duplicated, gap-aligned indicators that are known at each issue date.
- Disaster and agriculture news **track** hunger in the same period.
- **None of it improves a forecast:**
  - removing news does not hurt;
  - real news does no better than shuffled news;
  - the one strong leading association does not replicate in two independent sources.
- News is therefore usable as **descriptive evidence on the dashboard**, not as a validated predictor.

## 1. Audit of the existing NLP components

| Component | Status | Decision |
|---|---|---|
| XLM-RoBERTa zero-shot → FSSI-v3 (`app.news.pipeline_v3`) | Runs. Sparse: 46% of scored origins have no value, because fewer than 5 admitted headlines exist in 2021–22. | Kept as column `N1`, the family's own indicator. Not rebuilt. |
| BERTopic (E64/E75) | 152 topics; 39.7% outliers; about a third of topics are place names (E75); topics are not stable across refits. | Not used as a model input. It cannot give a dated, consistent quantity per issue date. Kept as a descriptive display only. |
| E112 six-category title lexicon (English + Filipino) | Transparent. The disaster category was validated against typhoon counts (ρ = 0.81). | Reused unchanged. |
| `pipeline_v3.dedupe` (syndicated copies) | Works | Reused |

## 2. What is new in this pipeline (`runner/news_features.py`)

1. **Repeated coverage of one event is removed.** Within one category, a headline whose word set has Jaccard similarity ≥ 0.5 with a kept headline of the previous 7 days is dropped. This removed 138 corpus headlines and 8,601 GDELT GKG documents.
2. **Anticipatory vs reporting.** A food-event headline is *anticipatory* if it uses forward-looking wording ("expected", "braces for", "warns", "threat", "seen to", "inaasahan", "nagbabala", …). Otherwise it is *reporting*. 212 of 3,069 food-event headlines are anticipatory, about 7%.
3. **Gap-aligned windows.** Earlier experiments used calendar quarters. Here the window W runs from the newest survey's fieldwork end to the issue date: it is the news the latest SWS reading has not yet "seen".
   - The feature is the category share in W minus the same share one year earlier, which removes seasonality and corpus growth.
   - At least 30 headlines are required in each window.
4. **Availability.** Only headlines published before the issue date can enter W. The newest headline used is recorded per prediction (`news_latest_published`) and tested to be before the issue date.
5. **Geography.** Model features are regional (CALABARZON news). No event is assigned to a province that its article does not name: the province code comes from the existing tagger, and only 33% of headlines carry one.

**Columns in the model:** `N1`, `NC_gap_{price, shortage, disaster, agri_supply, jobs_income, assistance}` and `NC_ant`. In 2022+ they have 0% missing.

## 3. Controlled comparisons (same rows, same LightGBM configuration)

**FIL (12 families including news) vs FIL-NONEWS** (`out/results_news.json`)

| Lead | Rows | Accuracy with news | Accuracy without | ΔBrier (with − without) | p (two-sided) | Holm p |
|---|---|---|---|---|---|---|
| 1 | 44 | 0.318 | 0.409 | +0.005 | .48 | 1.0 |
| 2 | 40 | 0.400 | 0.425 | 0.000 | .89 | 1.0 |
| 3 | 36 | 0.444 | 0.444 | −0.006 | .54 | 1.0 |
| 4 | 32 | 0.500 | 0.531 | 0.000 | .92 | 1.0 |

**News-focused LightGBM (hunger history + news) vs hunger history only**

| Lead | Accuracy H+N | Accuracy H | ΔBrier | Holm p |
|---|---|---|---|---|
| 1 | 0.568 | 0.500 | −0.034 | .92 |
| 2 | 0.450 | 0.450 | +0.022 | .92 |
| 3 | 0.389 | 0.500 | +0.019 | 1.0 |
| 4 | 0.531 | 0.531 | +0.005 | 1.0 |

**NLP-only logistic regression (Objective 4):**

| Lead | Accuracy | Balanced accuracy |
|---|---|---|
| 1 | 0.318 | 0.371 |
| 2 | 0.300 | 0.346 |
| 3 | 0.417 | 0.460 |
| 4 | 0.469 | 0.516 |

At Leads 1–3 this is below always-ELEVATED (0.59–0.65).

**Placebo** (100 refits with the news columns permuted across issue quarters)

| Lead | Real Brier | Mean permuted Brier | Share of permutations ≤ real |
|---|---|---|---|
| 1 | 0.298 | 0.291 | 0.93 |
| 2 | 0.313 | 0.312 | 0.53 |
| 3 | 0.307 | 0.307 | 0.48 |
| 4 | 0.297 | 0.300 | 0.30 |

Real news is no better than shuffled news at any lead. At Lead 1 it is slightly worse.

**Long history** (GDELT DOC national news, 2018+ targets, 124 rows per lead)

| Lead | Accuracy with news | Accuracy without | ΔBrier | p |
|---|---|---|---|---|
| 1 | 0.476 | 0.556 | +0.016 | .015 |
| 2 | 0.508 | 0.556 | +0.013 | .019 |

Here news made FIL-LONG **significantly worse** at Leads 1–2.

**Contribution (SHAP).** News columns hold 3% of FIL's attribution at Lead 1. The ablation and placebo above show that this nonzero share carries no predictive value.

## 4. Early warning: does any news category lead hunger?

**Leading association.** Each column at the issue date is correlated with the realised hunger anomaly in the target quarter (4-area mean per origin; 14–17 origins per lead). Holm correction runs over 7 columns × 4 leads.

| Column | Lead | ρ | p | Holm p | ρ (BL only) |
|---|---|---|---|---|---|
| `NC_gap_agri_supply` | 1 | **0.74** | .001 | **.018** | 0.78 |
| `NC_gap_price` | 3 | −0.73 | .002 | .052 | −0.56 |
| `NC_gap_agri_supply` | 2 | 0.64 | .008 | .21 | 0.33 |
| All other columns × leads | | | ≥ .02 | ≥ .56 | |

**Replication of the agri-supply signal** (Addendum 2, frozen before it was run)

| Source and period | ρ | p (one-sided) | Origins |
|---|---|---|---|
| GDELT GKG CALABARZON themes, 2021+ (same period, other source) | 0.16 | .26 | 17 |
| GDELT DOC national, 2018–2020 (untouched period) | 0.06 | .44 | 10 |
| GDELT DOC national, 2021+ | −0.32 | — | 20 |

**Not replicated.** E112 had reported the same corpus association, which then failed in GDELT (E113). The signal appears specific to the RSS corpus's composition.

**Concurrent association** (reporting). This is the quarter's own news category share, compared year on year, against the same quarter's hunger anomaly (17 quarters).

| Category | ρ | p |
|---|---|---|
| Disaster | 0.66 | .004 |
| Agri-supply | 0.55 | .022 |
| Assistance | 0.41 | .10 |
| Price | 0.05 | .84 |
| Shortage | −0.29 | .26 |
| Jobs and income | −0.35 | .17 |

**Anticipatory vs reporting.** Quarterly year-on-year shares are compared with the hunger anomaly (16–17 quarters, unadjusted).

| News share | Concurrent | One quarter earlier | Two quarters earlier |
|---|---|---|---|
| Reporting food events | **ρ = 0.66 (p = .004)** | 0.42 (p = .10) | 0.54 (p = .03) |
| Anticipatory food events | 0.01 | −0.29 | −0.57 (p = .02) |

**Reading these results**
- Reporting news tracks hunger: disasters and supply problems are written about in the same quarters that hunger is high.
- Anticipatory headlines do **not** precede hunger rises. If anything, the sign is negative: warnings ("brace for El Niño") are often followed by mitigation or by events that did not hurt hunger.
- With about 17 quarters, none of these associations is strong enough to become a forecast. The model-based tests in §3 confirm that.

**Example: the 2024 surge, BL at Lead 1**

| Issue date | Latest BL reading → actual | News since the last survey |
|---|---|---|
| 2024-01-01 | 10.3 → 15.3 | Agri share +5.6 points; anticipatory +5.0 |
| 2024-04-01 | 14.3 → 19.6 | Disaster +8.0 |
| 2024-07-01 | 15.3 → 18.1 | Disaster +7.5, agri +6.0 |
| 2024-10-01 | 19.6 → 25.3 | Disaster +8.7, assistance +4.2 |

The direction is suggestive. However, comparable news increases also occurred in quarters without hunger rises, and FIL did not convert them into ELEVATED calls.

## 5. Why news does not help (causes investigated)

| Cause | Evidence |
|---|---|
| Too few independent outcome quarters | About 17 issue dates in 2021+. The 4 areas share the same news value (one regional feed). Any 13-column news block is fitted to roughly 15 independent points. |
| Geographic resolution | One CALABARZON feed is used against 4 SWS areas. Only BL is geographically matched. Province codes are on 33% of headlines. |
| Timing | Gap alignment fixed the calendar mismatch. Reporting news is concurrent, not leading. |
| Relevance | Category shares are noisy: the anticipatory share rests on about 10 headlines per window. |
| Retrospective collection | Corpus composition varies by outlet over time, which is one plausible reason the corpus-only association did not replicate. |
| Outcome noise | Even a perfect forecaster reaches at most 0.58–0.64 on ELEVATED one quarter ahead (`LIGHTGBM_MODEL_AND_METRICS.md` §5). Any news gain must fit inside that small margin. |

**Conclusion.** News value was not demonstrated by valid comparisons, so it is not claimed.

**Supported uses for DA IV-A**
- A dated, de-duplicated news-evidence panel showing what has happened since the last survey (disaster, supply, assistance).
- Validated as tracking typhoons (E112) and concurrent hunger (above).
